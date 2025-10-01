import asyncio
import pytest

from src.adapters.services.dexscreener_batch_client import DexScreenerBatchClient


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json_data = json_data or []
        self.headers = headers or {}

    def json(self):
        return self._json_data


class DummyClient:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    async def get(self, url):
        self.calls.append(url)
        return self._responses.pop(0)

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_batch_fetch_and_cache(monkeypatch):
    mint1 = "Mint1"
    mint2 = "Mint2"

    responses = [
        DummyResponse(
            status_code=200,
            json_data=[
                {"baseToken": {"address": mint1}, "pair": "pair1"},
                {"baseToken": {"address": mint2}, "pair": "pair2"},
            ],
        )
    ]

    dummy_client = DummyClient(responses)
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: dummy_client)

    client = DexScreenerBatchClient(cache_ttl=5.0, max_batch_size=30)

    result = await client.get_pairs_for_mints([mint1, mint2])
    assert result[mint1] == [{"baseToken": {"address": mint1}, "pair": "pair1"}]
    assert result[mint2] == [{"baseToken": {"address": mint2}, "pair": "pair2"}]
    assert len(dummy_client.calls) == 1

    # Second call should hit cache (no new HTTP call)
    cached_result = await client.get_pairs_for_mints([mint1])
    assert cached_result[mint1] == result[mint1]
    assert len(dummy_client.calls) == 1

    await client.close()


@pytest.mark.asyncio
async def test_batch_handles_rate_limit(monkeypatch):
    mint = "MintRate"

    responses = [
        DummyResponse(status_code=429, headers={"Retry-After": "0"}),
        DummyResponse(
            status_code=200,
            json_data=[{"baseToken": {"address": mint}, "pair": "pair_rl"}],
        ),
    ]

    dummy_client = DummyClient(responses)
    async def noop_sleep(_):
        return None

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: dummy_client)
    monkeypatch.setattr("asyncio.sleep", noop_sleep)

    client = DexScreenerBatchClient(cache_ttl=0.1, max_batch_size=5)

    result = await client.get_pairs_for_mints([mint])
    assert result[mint][0]["pair"] == "pair_rl"
    assert len(dummy_client.calls) == 2  # retried once

    await client.close()


@pytest.mark.asyncio
async def test_batch_missing_token_returns_none(monkeypatch):
    mint = "MissingMint"

    responses = [DummyResponse(status_code=500)]
    dummy_client = DummyClient(responses)
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: dummy_client)

    client = DexScreenerBatchClient(cache_ttl=0.0, max_batch_size=10)

    result = await client.get_pairs_for_mints([mint])
    assert result[mint] is None
    assert len(dummy_client.calls) == 1

    await client.close()
