from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import httpx

from .dexscreener_client import DexScreenerClient
from .rate_limiter import AsyncRateLimiter

log = logging.getLogger("dex_broker")


TOKENS_V1_URL = "https://api.dexscreener.com/tokens/v1/solana/"

LANE_PRIORITY = {
    "activation": 4,
    "scoring_hot": 3,
    "scoring_cold": 2,
    "notarb": 1,
}


def _default_stats() -> dict:
    return {
        "batch_requests": 0,
        "fallback_requests": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "inflight_dedup_hits": 0,
        "request_failures": 0,
        "pairs_returned": 0,
        "empty_results": 0,
        "lane_requests": {
            "activation": 0,
            "scoring_hot": 0,
            "scoring_cold": 0,
            "notarb": 0,
            "scoring": 0,
            "other": 0,
        },
        "last_error": None,
    }


@dataclass
class _CacheEntry:
    value: Optional[list[dict]]
    expires_at: float


@dataclass
class _PendingRequest:
    mint: str
    lane: str
    future: asyncio.Future


class DexBroker:
    """
    Centralized DexScreener broker.

    Properties:
    - Batch source: /tokens/v1/solana/{mint1,...,mint30}
    - Fallback source: /token-pairs/v1/solana/{mint}
    - Hard budget: 240 rpm, degraded soft budget: 200 rpm
    - Coalescing: 200ms (within required 150-250ms)
    - In-flight dedup: per mint
    """

    def __init__(
        self,
        *,
        hard_rpm: int = 240,
        soft_rpm: int = 200,
        cache_ttl_sec: float = 3.0,
        coalesce_window_sec: float = 0.2,
        max_batch_size: int = 30,
        timeout_sec: float = 8.0,
    ) -> None:
        self.cache_ttl_sec = max(0.0, cache_ttl_sec)
        self.coalesce_window_sec = min(max(0.15, coalesce_window_sec), 0.25)
        self.max_batch_size = max(1, min(30, max_batch_size))

        self._cache: Dict[str, _CacheEntry] = {}
        self._cache_lock = asyncio.Lock()

        self._pending: Dict[str, _PendingRequest] = {}
        self._inflight: Dict[str, asyncio.Future] = {}
        self._pending_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

        self._fallback_client = DexScreenerClient(timeout=3.0)
        self._http = httpx.AsyncClient(timeout=timeout_sec)

        self._hard_limiter = AsyncRateLimiter(rate_per_sec=hard_rpm / 60.0, max_burst=8)
        self._soft_limiter = AsyncRateLimiter(rate_per_sec=soft_rpm / 60.0, max_burst=6)
        self._degraded_until = 0.0

        self._stats = _default_stats()

    async def close(self) -> None:
        await self._http.aclose()

    def _is_degraded(self) -> bool:
        return time.monotonic() < self._degraded_until

    async def _acquire_budget(self) -> None:
        if self._is_degraded():
            await self._soft_limiter.acquire()
        else:
            await self._hard_limiter.acquire()

    async def get_pairs_for_mints(
        self,
        mints: Sequence[str],
        *,
        lane: str = "scoring",
        fallback_on_empty: bool = False,
        force_fallback: bool = False,
    ) -> Dict[str, Optional[list[dict]]]:
        if not mints:
            return {}

        lane_key = lane if lane in self._stats["lane_requests"] else "other"
        self._stats["lane_requests"][lane_key] += 1

        unique_mints = list(dict.fromkeys([m for m in mints if m]))
        if not unique_mints:
            return {}

        if force_fallback:
            return await self._fetch_fallback_many(unique_mints, lane=lane)

        now = time.monotonic()
        result: Dict[str, Optional[list[dict]]] = {}
        futures: dict[str, asyncio.Future] = {}

        async with self._cache_lock:
            for mint in unique_mints:
                entry = self._cache.get(mint)
                if entry and entry.expires_at > now:
                    self._stats["cache_hits"] += 1
                    result[mint] = entry.value
                else:
                    if entry is not None:
                        self._cache.pop(mint, None)
                    self._stats["cache_misses"] += 1

        for mint in unique_mints:
            if mint in result:
                continue
            fut = await self._register_pending_request(mint=mint, lane=lane)
            futures[mint] = fut

        if futures:
            awaited = await asyncio.gather(*futures.values(), return_exceptions=True)
            for mint, value in zip(futures.keys(), awaited):
                if isinstance(value, Exception):
                    self._stats["request_failures"] += 1
                    self._stats["last_error"] = str(value)
                    result[mint] = None
                else:
                    result[mint] = value

        if fallback_on_empty:
            to_fallback = [
                mint
                for mint, pairs in result.items()
                if pairs is None or (isinstance(pairs, list) and len(pairs) == 0)
            ]
            if to_fallback:
                fallback_map = await self._fetch_fallback_many(to_fallback, lane=lane)
                result.update(fallback_map)

        for pairs in result.values():
            if pairs is None:
                self._stats["request_failures"] += 1
            elif len(pairs) == 0:
                self._stats["empty_results"] += 1
            else:
                self._stats["pairs_returned"] += len(pairs)

        return result

    async def _register_pending_request(self, *, mint: str, lane: str) -> asyncio.Future:
        async with self._pending_lock:
            pending = self._pending.get(mint)
            if pending is not None:
                # Keep the highest-priority lane for this mint.
                if LANE_PRIORITY.get(lane, 0) > LANE_PRIORITY.get(pending.lane, 0):
                    pending.lane = lane
                self._stats["inflight_dedup_hits"] += 1
                return pending.future

            inflight = self._inflight.get(mint)
            if inflight is not None:
                self._stats["inflight_dedup_hits"] += 1
                return inflight

            loop = asyncio.get_running_loop()
            future: asyncio.Future = loop.create_future()
            self._pending[mint] = _PendingRequest(mint=mint, lane=lane, future=future)

            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._flush_pending_batches())

            return future

    async def _flush_pending_batches(self) -> None:
        await asyncio.sleep(self.coalesce_window_sec)

        while True:
            async with self._pending_lock:
                if not self._pending:
                    return

                batch = list(self._pending.values())
                self._pending = {}
                for req in batch:
                    self._inflight[req.mint] = req.future

            # Process higher-priority lanes first.
            batch.sort(key=lambda req: LANE_PRIORITY.get(req.lane, 0), reverse=True)
            mints = [req.mint for req in batch]

            try:
                fetched = await self._fetch_tokens_many(mints)
            except Exception as exc:  # noqa: BLE001
                fetched = {mint: None for mint in mints}
                self._stats["request_failures"] += len(mints)
                self._stats["last_error"] = str(exc)

            async with self._pending_lock:
                for req in batch:
                    value = fetched.get(req.mint)
                    if not req.future.done():
                        req.future.set_result(value)
                    self._inflight.pop(req.mint, None)

    async def _fetch_tokens_many(self, mints: Sequence[str]) -> Dict[str, Optional[list[dict]]]:
        out: Dict[str, Optional[list[dict]]] = {}
        chunks = [mints[i : i + self.max_batch_size] for i in range(0, len(mints), self.max_batch_size)]

        for chunk in chunks:
            chunk_map = await self._fetch_tokens_chunk(chunk)
            out.update(chunk_map)

        await self._store_cache_entries(out)
        return out

    async def _fetch_tokens_chunk(self, chunk: Sequence[str]) -> Dict[str, Optional[list[dict]]]:
        if not chunk:
            return {}

        await self._acquire_budget()
        self._stats["batch_requests"] += 1

        url = TOKENS_V1_URL + ",".join(chunk)
        now_mono = time.monotonic()

        try:
            response = await self._http.get(url)
        except Exception as exc:  # noqa: BLE001
            self._degraded_until = now_mono + 60.0
            self._stats["request_failures"] += len(chunk)
            self._stats["last_error"] = str(exc)
            log.warning("dex_broker_http_error", extra={"extra": {"error": str(exc), "chunk_size": len(chunk)}})
            return {mint: None for mint in chunk}

        if response.status_code == 429 or response.status_code >= 500:
            self._degraded_until = now_mono + 60.0

        if response.status_code != 200:
            self._stats["request_failures"] += len(chunk)
            self._stats["last_error"] = f"status_{response.status_code}"
            log.warning(
                "dex_broker_unexpected_status",
                extra={"extra": {"status": response.status_code, "chunk_size": len(chunk)}},
            )
            return {mint: None for mint in chunk}

        try:
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            self._stats["request_failures"] += len(chunk)
            self._stats["last_error"] = str(exc)
            return {mint: None for mint in chunk}

        grouped: Dict[str, list[dict]] = {mint: [] for mint in chunk}
        if isinstance(data, list):
            chunk_set = set(chunk)
            for item in data:
                if not isinstance(item, dict):
                    continue
                base = item.get("baseToken") or {}
                base_address = str(base.get("address") or "")
                if base_address in chunk_set:
                    grouped[base_address].append(item)

        return grouped

    async def _store_cache_entries(self, fetched: Dict[str, Optional[list[dict]]]) -> None:
        if self.cache_ttl_sec <= 0:
            return
        exp = time.monotonic() + self.cache_ttl_sec
        async with self._cache_lock:
            for mint, pairs in fetched.items():
                self._cache[mint] = _CacheEntry(value=pairs, expires_at=exp)

    async def _fetch_fallback_many(self, mints: Sequence[str], *, lane: str) -> Dict[str, Optional[list[dict]]]:
        out: Dict[str, Optional[list[dict]]] = {}
        for mint in mints:
            await self._acquire_budget()
            self._stats["fallback_requests"] += 1
            try:
                pairs = await asyncio.to_thread(self._fallback_client.get_pairs, mint)
                out[mint] = pairs
            except Exception as exc:  # noqa: BLE001
                self._stats["request_failures"] += 1
                self._stats["last_error"] = str(exc)
                log.warning(
                    "dex_broker_fallback_error",
                    extra={"extra": {"mint": mint, "lane": lane, "error": str(exc)}},
                )
                out[mint] = None

        await self._store_cache_entries(out)
        return out

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "degraded_mode": self._is_degraded(),
            "cache_size": len(self._cache),
            "pending_requests": len(self._pending),
            "inflight_requests": len(self._inflight),
            "coalesce_window_ms": int(self.coalesce_window_sec * 1000),
            "max_batch_size": self.max_batch_size,
            "hard_rpm": 240,
            "soft_rpm": 200,
        }

    def reset_stats(self) -> None:
        self._stats = _default_stats()
        self._cache.clear()
        self._pending.clear()
        self._inflight.clear()
        self._degraded_until = 0.0


_broker: Optional[DexBroker] = None
_broker_lock = asyncio.Lock()


async def get_dex_broker() -> DexBroker:
    global _broker
    async with _broker_lock:
        if _broker is None:
            _broker = DexBroker()
        return _broker


async def close_dex_broker() -> None:
    global _broker
    async with _broker_lock:
        if _broker is not None:
            await _broker.close()
            _broker = None


def get_dex_broker_stats() -> dict:
    if _broker is None:
        return {
            **_default_stats(),
            "degraded_mode": False,
            "cache_size": 0,
            "pending_requests": 0,
            "inflight_requests": 0,
            "coalesce_window_ms": 200,
            "max_batch_size": 30,
            "hard_rpm": 240,
            "soft_rpm": 200,
        }
    return _broker.get_stats()


def reset_dex_broker_stats() -> None:
    if _broker is not None:
        _broker.reset_stats()
