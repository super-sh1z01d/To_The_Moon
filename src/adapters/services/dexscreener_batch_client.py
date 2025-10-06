"""Batch DexScreener client with shared rate limiting and caching."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence

import httpx

from .rate_limiter import AsyncRateLimiter

log = logging.getLogger("dexscreener_batch")


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: List[dict], expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at


class DexScreenerBatchClient:
    """Fetches multiple token pairs in a single call using /tokens/v1 endpoint."""

    BASE_URL = "https://api.dexscreener.com/tokens/v1"

    def __init__(
        self,
        chain_id: str = "solana",
        *,
        timeout: float = 5.0,
        max_batch_size: int = 30,
        cache_ttl: float = 3.0,
        rate_per_sec: float = 4.5,
        burst: int = 10,
        use_http2: bool = False,
    ) -> None:
        self.chain_id = chain_id
        self.timeout = timeout
        self.max_batch_size = max(1, min(max_batch_size, 30))
        self.cache_ttl = max(0.0, cache_ttl)
        self._rate_limiter = AsyncRateLimiter(rate_per_sec, burst)
        self._use_http2 = use_http2
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, _CacheEntry] = {}
        self._cache_lock = asyncio.Lock()
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.timeout, http2=self._use_http2)
            return self._client

    async def close(self) -> None:
        async with self._client_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def get_pairs_for_mints(self, mints: Sequence[str]) -> Dict[str, Optional[List[dict]]]:
        """Return mapping mint -> list of pairs (or None if failed)."""
        if not mints:
            return {}

        unique_ordered: List[str] = []
        seen = set()
        for mint in mints:
            if mint not in seen:
                seen.add(mint)
                unique_ordered.append(mint)

        cached: Dict[str, Optional[List[dict]]] = {}
        missing: List[str] = []
        now = time.monotonic()

        async with self._cache_lock:
            for mint in unique_ordered:
                entry = self._cache.get(mint)
                if entry and entry.expires_at > now:
                    cached[mint] = entry.value
                else:
                    if entry:
                        self._cache.pop(mint, None)
                    missing.append(mint)

        if not missing:
            return {mint: cached.get(mint, []) for mint in unique_ordered}

        fetched = await self._fetch_batches(missing)

        result: Dict[str, Optional[List[dict]]] = {}
        for mint in unique_ordered:
            if mint in fetched:
                result[mint] = fetched[mint]
            else:
                result[mint] = cached.get(mint)

        return result

    async def _fetch_batches(self, mints: Sequence[str]) -> Dict[str, Optional[List[dict]]]:
        grouped: Dict[str, Optional[List[dict]]] = {}
        chunks = [
            mints[i : i + self.max_batch_size]
            for i in range(0, len(mints), self.max_batch_size)
        ]

        client = await self._get_client()

        for chunk in chunks:
            await self._rate_limiter.acquire()
            url = f"{self.BASE_URL}/{self.chain_id}/" + ",".join(chunk)
            try:
                response = await client.get(url)
            except Exception as exc:  # noqa: BLE001
                log.warning("http_error", extra={"extra": {"chunk": chunk, "error": type(exc).__name__}})
                for mint in chunk:
                    grouped[mint] = None
                continue

            if response.status_code == 429:
                retry_after = self._resolve_retry_after(response.headers.get("Retry-After"))
                log.warning("rate_limited_batch", extra={"extra": {"chunk_size": len(chunk), "retry_after": retry_after}})
                await asyncio.sleep(retry_after)
                try:
                    response = await client.get(url)
                except Exception as exc:  # noqa: BLE001
                    log.warning("http_error_retry", extra={"extra": {"chunk": chunk, "error": type(exc).__name__}})
                    for mint in chunk:
                        grouped[mint] = None
                    continue

            if response.status_code != 200:
                log.warning(
                    "unexpected_status", 
                    extra={"extra": {"status": response.status_code, "chunk_size": len(chunk)}}
                )
                for mint in chunk:
                    grouped[mint] = None
                continue

            try:
                data = response.json()
            except Exception as exc:  # noqa: BLE001
                log.warning("non_json_response", extra={"extra": {"chunk": chunk, "error": type(exc).__name__}})
                for mint in chunk:
                    grouped[mint] = None
                continue

            pairs_map: Dict[str, List[dict]] = defaultdict(list)
            for item in data if isinstance(data, list) else []:
                base = (item.get("baseToken") or {}) if isinstance(item, dict) else {}
                base_address = str(base.get("address") or "")
                if base_address in chunk:
                    pairs_map[base_address].append(item)

            now = time.monotonic()
            expires_at = now + self.cache_ttl

            async with self._cache_lock:
                for mint in chunk:
                    value = pairs_map.get(mint, [])
                    grouped[mint] = value
                    if self.cache_ttl > 0:
                        self._cache[mint] = _CacheEntry(value, expires_at)

        return grouped

    @staticmethod
    def _resolve_retry_after(header_value: Optional[str]) -> float:
        if not header_value:
            return 1.0
        try:
            return max(0.5, float(header_value))
        except ValueError:
            return 1.0


_batch_client: Optional[DexScreenerBatchClient] = None
_client_lock = asyncio.Lock()


async def get_batch_client() -> DexScreenerBatchClient:
    global _batch_client
    async with _client_lock:
        if _batch_client is None:
            # Increased timeout and reduced batch size due to DexScreener API slowdown since Oct 4
            _batch_client = DexScreenerBatchClient(
                timeout=15.0,  # Increased from 5.0 to 15.0 seconds
                max_batch_size=20,  # Reduced from 30 to 20 tokens per batch
                cache_ttl=5.0  # Increased cache TTL to reduce API calls
            )
        return _batch_client


async def close_batch_client() -> None:
    global _batch_client
    async with _client_lock:
        if _batch_client is not None:
            await _batch_client.close()
            _batch_client = None
