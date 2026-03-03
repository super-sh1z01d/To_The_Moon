from __future__ import annotations

import asyncio

import pytest

from src.adapters.services.dex_broker import DexBroker


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeLimiter:
    def __init__(self):
        self.calls = 0

    async def acquire(self):
        self.calls += 1


@pytest.mark.asyncio
async def test_dex_broker_coalesces_and_dedups_inflight_requests():
    broker = DexBroker(cache_ttl_sec=0.0, coalesce_window_sec=0.2, max_batch_size=30)

    calls: list[str] = []

    async def fake_get(url: str):
        calls.append(url)
        # /tokens/v1/solana/{mint1,mint2}
        mints_part = url.rsplit("/", 1)[-1]
        mints = [m for m in mints_part.split(",") if m]
        payload = []
        for mint in mints:
            payload.append(
                {
                    "baseToken": {"address": mint},
                    "pairAddress": f"pair-{mint}",
                    "dexId": "raydium",
                }
            )
        return _FakeResponse(200, payload)

    broker._http.get = fake_get  # type: ignore[method-assign]

    r1_task = asyncio.create_task(broker.get_pairs_for_mints(["mint-a"], lane="scoring_hot"))
    r2_task = asyncio.create_task(
        broker.get_pairs_for_mints(["mint-a", "mint-b"], lane="activation")
    )

    r1, r2 = await asyncio.gather(r1_task, r2_task)

    assert len(calls) == 1
    assert isinstance(r1["mint-a"], list)
    assert isinstance(r2["mint-a"], list)
    assert isinstance(r2["mint-b"], list)
    assert broker.get_stats()["inflight_dedup_hits"] >= 1

    await broker.close()


@pytest.mark.asyncio
async def test_dex_broker_enters_degraded_mode_on_429():
    broker = DexBroker(cache_ttl_sec=0.0, coalesce_window_sec=0.2, max_batch_size=30)

    async def fake_get(_url: str):
        return _FakeResponse(429, {"pairs": []})

    broker._http.get = fake_get  # type: ignore[method-assign]

    result = await broker.get_pairs_for_mints(["mint-429"], lane="activation")
    stats = broker.get_stats()

    assert result["mint-429"] is None
    assert stats["degraded_mode"] is True
    assert stats["request_failures"] >= 1

    await broker.close()


@pytest.mark.asyncio
async def test_dex_broker_uses_soft_limiter_after_degrade():
    broker = DexBroker(cache_ttl_sec=0.0, coalesce_window_sec=0.2, max_batch_size=30)
    hard = _FakeLimiter()
    soft = _FakeLimiter()
    broker._hard_limiter = hard  # type: ignore[assignment]
    broker._soft_limiter = soft  # type: ignore[assignment]

    call_count = {"n": 0}

    async def fake_get(url: str):
        call_count["n"] += 1
        mints_part = url.rsplit("/", 1)[-1]
        mints = [m for m in mints_part.split(",") if m]
        if call_count["n"] == 1:
            return _FakeResponse(500, {"error": "upstream failure"})
        payload = [{"baseToken": {"address": mint}, "pairAddress": f"pair-{mint}", "dexId": "raydium"} for mint in mints]
        return _FakeResponse(200, payload)

    broker._http.get = fake_get  # type: ignore[method-assign]

    first = await broker.get_pairs_for_mints(["mint-a"], lane="scoring_hot")
    second = await broker.get_pairs_for_mints(["mint-b"], lane="scoring_hot")

    assert first["mint-a"] is None
    assert isinstance(second["mint-b"], list)
    # First call acquires hard budget, second call uses soft budget due to degraded mode.
    assert hard.calls >= 1
    assert soft.calls >= 1

    await broker.close()


@pytest.mark.asyncio
async def test_dex_broker_fallback_on_empty_results():
    broker = DexBroker(cache_ttl_sec=0.0, coalesce_window_sec=0.2, max_batch_size=30)

    async def fake_get(_url: str):
        # Empty tokens endpoint response => should trigger fallback.
        return _FakeResponse(200, [])

    broker._http.get = fake_get  # type: ignore[method-assign]
    broker._fallback_client.get_pairs = lambda mint: [{"baseToken": {"address": mint}, "pairAddress": "f"}]  # type: ignore[method-assign]

    result = await broker.get_pairs_for_mints(["mint-x"], lane="activation", fallback_on_empty=True)

    assert isinstance(result["mint-x"], list)
    assert len(result["mint-x"]) == 1
    assert broker.get_stats()["fallback_requests"] >= 1

    await broker.close()
