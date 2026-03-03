from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# Needed because pipeline worker imports DB layer at module import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

from src.pipeline.worker import (
    JOB_ACTIVATION,
    JOB_SCORING_COLD,
    JOB_SCORING_HOT,
    PipelineWorker,
    _is_transient_error,
)


@dataclass
class _Token:
    id: int
    status: str


class _FakeRepo:
    def __init__(self, monitoring: list[_Token], active: list[_Token]):
        self._monitoring = monitoring
        self._active = active

    def list_by_status(self, status: str, limit: int = 100):  # noqa: ARG002
        if status == "monitoring":
            return self._monitoring
        if status == "active":
            return self._active
        return []


class _FakeSettings:
    def get(self, _key: str):
        return None


class _FakeQueueRepo:
    def __init__(self):
        self.jobs = []

    def enqueue_many(self, jobs):
        self.jobs = list(jobs)
        return len(self.jobs)


class _BackoffQueueRepo:
    def __init__(self, backoff_until: datetime):
        self._state = SimpleNamespace(backoff_until=backoff_until)
        self.deferred = False
        self.acked = False

    def get_runtime_state(self, _token_id: int):
        return self._state

    def defer_job(self, *_args, **_kwargs):
        self.deferred = True
        return True

    def ack_job(self, *_args, **_kwargs):
        self.acked = True
        return True


class _ScoringQueueRepo:
    def __init__(self):
        self.touched = []
        self.acked = False

    def get_runtime_state(self, _token_id: int):
        return None

    def touch_runtime_state(self, **kwargs):
        self.touched.append(kwargs)

    def ack_job(self, *_args, **_kwargs):
        self.acked = True
        return True


class _DummySessionCtx:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _RunIterationQueueRepo:
    instances: list["_RunIterationQueueRepo"] = []

    def __init__(self, _db):
        self.rebalance_calls = 0
        self.cleanup_calls = 0
        self.claim_calls = 0
        self.__class__.instances.append(self)

    def rebalance_queue(self):
        self.rebalance_calls += 1
        return {"requeued_expired": 2, "boosted_retries": 1}

    def cleanup_finished_jobs(self, **_kwargs):
        self.cleanup_calls += 1
        return 1

    def claim_jobs(self, **_kwargs):
        self.claim_calls += 1
        return []

    def queue_health(self):
        return {
            "deadletter_rate": 0.0,
            "lag_seconds": 0,
            "due": 0,
        }


class _FlowQueueRepo:
    def __init__(self):
        self.touched = []
        self.acked = []

    def get_runtime_state(self, _token_id: int):
        return None

    def touch_runtime_state(self, **kwargs):
        self.touched.append(kwargs)

    def ack_job(self, job_id: int, **_kwargs):
        self.acked.append(job_id)
        return True


class _FlowTokenRepo:
    def __init__(self, token):
        self.token = token
        self.updated_pool_metrics = []
        self.timestamp_updates = 0
        self.saved_score = None

    def get_by_id(self, token_id: int):
        if token_id == self.token.id:
            return self.token
        return None

    def update_pool_metrics_only(self, token_id: int, metrics: dict):
        self.updated_pool_metrics.append((token_id, metrics))

    def update_token_fields(self, token, *, name=None, symbol=None):
        token.name = name
        token.symbol = symbol

    def set_active(self, token):
        token.status = "active"

    def set_monitoring(self, token):
        token.status = "monitoring"

    def update_token_timestamp(self, _token_id: int):
        self.timestamp_updates += 1


class _GuardQueueRepo:
    instances: list["_GuardQueueRepo"] = []

    def __init__(self, _db):
        self.rebalance_calls = 0
        self.cleanup_calls = 0
        self.claim_calls = 0
        self.__class__.instances.append(self)

    def rebalance_queue(self):
        self.rebalance_calls += 1
        return {"requeued_expired": 0, "boosted_retries": 0}

    def cleanup_finished_jobs(self, **_kwargs):
        self.cleanup_calls += 1
        return 0

    def claim_jobs(self, **_kwargs):
        self.claim_calls += 1
        return []

    def queue_health(self):
        return {
            "deadletter_rate": 0.15,
            "lag_seconds": 1200,
            "due": 500,
        }


def test_pipeline_worker_seeds_activation_hot_and_cold_jobs():
    monitoring = [_Token(id=1, status="monitoring"), _Token(id=2, status="monitoring")]
    active = [_Token(id=10, status="active")]

    repo = _FakeRepo(monitoring=monitoring, active=active)
    settings = _FakeSettings()
    queue_repo = _FakeQueueRepo()

    worker = PipelineWorker(seed_period_seconds=10.0)
    inserted = worker._seed_jobs(repo, settings, queue_repo)

    assert inserted == len(queue_repo.jobs)

    activation_jobs = [j for j in queue_repo.jobs if j["job_type"] == JOB_ACTIVATION]
    hot_jobs = [j for j in queue_repo.jobs if j["job_type"] == JOB_SCORING_HOT]
    cold_jobs = [j for j in queue_repo.jobs if j["job_type"] == JOB_SCORING_COLD]

    assert len(activation_jobs) == 3
    assert len(hot_jobs) == 1
    assert len(cold_jobs) == 2

    assert all(j["priority"] == 400 for j in activation_jobs if j["token_id"] in {1, 2})
    assert any(j["priority"] == 390 and j["token_id"] == 10 for j in activation_jobs)
    assert all(j["idempotency_key"].startswith(j["job_type"] + ":") for j in queue_repo.jobs)


def test_pipeline_worker_seed_jobs_respects_canary_percent():
    monitoring = [_Token(id=1, status="monitoring"), _Token(id=2, status="monitoring"), _Token(id=3, status="monitoring")]
    active = [_Token(id=10, status="active"), _Token(id=11, status="active"), _Token(id=12, status="active")]

    repo = _FakeRepo(monitoring=monitoring, active=active)
    worker = PipelineWorker(seed_period_seconds=10.0)

    class _CanarySettings:
        def get(self, key: str):
            if key == "pipeline_v2_canary_percent":
                return "30"
            return None

    queue_repo = _FakeQueueRepo()
    inserted = worker._seed_jobs(repo, _CanarySettings(), queue_repo)

    selected_monitoring = [t.id for t in monitoring if worker._token_in_canary(t.id, 30)]
    selected_active = [t.id for t in active if worker._token_in_canary(t.id, 30)]
    expected = len(selected_monitoring) * 2 + len(selected_active) * 2  # activation+cold and activation+hot

    assert inserted == expected
    assert len(queue_repo.jobs) == expected
    allowed_ids = set(selected_monitoring + selected_active)
    assert all(j["token_id"] in allowed_ids for j in queue_repo.jobs)


def test_transient_error_classifier():
    assert _is_transient_error("dex_pairs_unavailable")
    assert _is_transient_error("Request timeout while calling upstream")
    assert _is_transient_error("HTTP 429 rate limit")
    assert not _is_transient_error("invalid_token_payload")


def test_retry_delay_increases_for_transient_errors():
    worker = PipelineWorker(worker_id="delay-worker")
    transient = worker._compute_retry_delay(attempts=3, error_text="dex_pairs_unavailable")
    non_transient = worker._compute_retry_delay(attempts=3, error_text="invalid token payload")
    assert transient > non_transient


@pytest.mark.asyncio
async def test_pipeline_worker_defers_job_when_runtime_backoff_active():
    worker = PipelineWorker(worker_id="test-worker")
    future_backoff = datetime.now(tz=timezone.utc) + timedelta(seconds=60)
    queue_repo = _BackoffQueueRepo(backoff_until=future_backoff)

    token = SimpleNamespace(
        id=101,
        status="monitoring",
        mint_address="mint-101",
        created_at=datetime.now(tz=timezone.utc),
    )
    token_repo = SimpleNamespace(get_by_id=lambda _token_id: token)

    async def _fetch_pairs(*_args, **_kwargs):
        raise AssertionError("fetch_pairs should not be called while token is in backoff")

    job = SimpleNamespace(id=11, token_id=101, job_type=JOB_SCORING_COLD)

    await worker._process_single_job(
        queue_repo=queue_repo,
        token_repo=token_repo,
        settings=SimpleNamespace(),
        scoring_service=SimpleNamespace(),
        fetch_pairs=_fetch_pairs,
        job=job,
    )

    assert queue_repo.deferred is True
    assert queue_repo.acked is False


@pytest.mark.asyncio
async def test_pipeline_worker_job_heartbeat_extends_lease():
    worker = PipelineWorker(worker_id="hb-worker", lease_seconds=30)

    class _DummySessionCtx:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    calls: list[tuple[str, list[int], int]] = []

    class _HeartbeatRepo:
        def __init__(self, _db):
            pass

        def heartbeat_jobs(self, *, worker_id: str, job_ids: list[int], lease_seconds: int):
            calls.append((worker_id, list(job_ids), lease_seconds))
            return len(job_ids)

    with (
        patch.object(worker, "_heartbeat_interval_seconds", return_value=0.02),
        patch("src.pipeline.worker.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.pipeline.worker.QueueRepository", _HeartbeatRepo),
    ):
        async with worker._job_heartbeat(job_id=777):
            await asyncio.sleep(0.07)

    assert len(calls) >= 2
    assert all(call[0] == "hb-worker" for call in calls)
    assert all(call[1] == [777] for call in calls)


@pytest.mark.asyncio
async def test_pipeline_worker_scoring_clears_backoff_state():
    worker = PipelineWorker(worker_id="score-worker")
    queue_repo = _ScoringQueueRepo()
    token = SimpleNamespace(
        id=55,
        status="monitoring",
        mint_address="mint-55",
        created_at=datetime.now(tz=timezone.utc),
    )
    token_repo = SimpleNamespace(get_by_id=lambda _token_id: token)
    settings = SimpleNamespace(get=lambda key: "0.1" if key == "min_score" else None)

    scoring_service = SimpleNamespace(
        calculate_token_score=lambda _token, _pairs: (0.4, 0.35, {}, {"tx": 1}, {"tx": 1}),
        save_score_result=lambda **_kwargs: 1,
    )

    async def _fetch_pairs(*_args, **_kwargs):
        return [{"dexId": "raydium", "labels": ["cpmm"], "baseToken": {"address": "mint-55"}}]

    job = SimpleNamespace(id=9, token_id=55, job_type=JOB_SCORING_COLD)

    await worker._process_single_job(
        queue_repo=queue_repo,
        token_repo=token_repo,
        settings=settings,
        scoring_service=scoring_service,
        fetch_pairs=_fetch_pairs,
        job=job,
    )

    assert queue_repo.acked is True
    assert queue_repo.touched
    assert queue_repo.touched[0].get("clear_backoff") is True


@pytest.mark.asyncio
async def test_pipeline_worker_activation_then_scoring_flow():
    worker = PipelineWorker(worker_id="flow-worker")
    token = SimpleNamespace(
        id=301,
        status="monitoring",
        mint_address="mint-301",
        created_at=datetime.now(tz=timezone.utc) - timedelta(hours=2),
        name=None,
        symbol=None,
    )
    token_repo = _FlowTokenRepo(token)
    queue_repo = _FlowQueueRepo()
    settings = SimpleNamespace(
        get=lambda key: "200" if key == "activation_min_liquidity_usd" else ("0.1" if key == "min_score" else None)
    )

    scoring_service = SimpleNamespace(
        calculate_token_score=lambda _token, _pairs: (0.45, 0.42, {"L_tot": 1234.0}, {"tx_accel": 0.6}, {"tx_accel": 0.55}),
        save_score_result=lambda **_kwargs: 1,
    )

    pairs = [
        {
            "dexId": "pumpfun-amm",
            "labels": ["pumpfun-amm"],
            "baseToken": {"address": "mint-301", "name": "Moon Token", "symbol": "MOON"},
            "quoteToken": {"symbol": "SOL"},
            "liquidity": {"usd": 300.0},
            "volume": {"m5": 120.0, "h1": 1500.0},
            "txns": {"m5": {"buys": 20, "sells": 10}, "h1": {"buys": 90, "sells": 70}},
        },
        {
            "dexId": "raydium",
            "labels": ["clmm"],
            "baseToken": {"address": "mint-301", "name": "Moon Token", "symbol": "MOON"},
            "quoteToken": {"symbol": "SOL"},
            "liquidity": {"usd": 1200.0},
            "volume": {"m5": 300.0, "h1": 2500.0},
            "txns": {"m5": {"buys": 35, "sells": 25}, "h1": {"buys": 150, "sells": 140}},
            "pairAddress": "pair-1",
        },
    ]

    async def _fetch_pairs(*_args, **_kwargs):
        return pairs

    activation_job = SimpleNamespace(id=101, token_id=301, job_type=JOB_ACTIVATION)
    scoring_job = SimpleNamespace(id=102, token_id=301, job_type=JOB_SCORING_HOT)

    await worker._process_single_job(
        queue_repo=queue_repo,
        token_repo=token_repo,
        settings=settings,
        scoring_service=scoring_service,
        fetch_pairs=_fetch_pairs,
        job=activation_job,
    )
    await worker._process_single_job(
        queue_repo=queue_repo,
        token_repo=token_repo,
        settings=settings,
        scoring_service=scoring_service,
        fetch_pairs=_fetch_pairs,
        job=scoring_job,
    )

    assert token.status == "active"
    assert token.symbol == "MOON"
    assert queue_repo.acked == [101, 102]
    assert len(queue_repo.touched) == 2
    assert queue_repo.touched[0].get("activation_checked_at") is not None
    assert queue_repo.touched[1].get("score_band") == "hot"
    assert queue_repo.touched[1].get("clear_backoff") is True


@pytest.mark.asyncio
async def test_pipeline_worker_run_iteration_requeues_expired_leases():
    worker = PipelineWorker(worker_id="iter-worker", seed_period_seconds=1.0)
    _RunIterationQueueRepo.instances = []

    class _DummyTokensRepo:
        def __init__(self, _db):
            pass

    class _DummySettingsService:
        def __init__(self, _db):
            pass

        def get(self, _key: str):
            return None

    with (
        patch("src.pipeline.worker.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.pipeline.worker.QueueRepository", _RunIterationQueueRepo),
        patch("src.pipeline.worker.TokensRepository", _DummyTokensRepo),
        patch("src.pipeline.worker.SettingsService", _DummySettingsService),
        patch.object(worker, "_seed_jobs", return_value=0),
        patch("src.pipeline.worker.asyncio.sleep", new=AsyncMock()),
    ):
        await worker.run_iteration()

    assert _RunIterationQueueRepo.instances
    rebalance_calls = sum(repo.rebalance_calls for repo in _RunIterationQueueRepo.instances)
    cleanup_calls = sum(repo.cleanup_calls for repo in _RunIterationQueueRepo.instances)
    claim_calls = sum(repo.claim_calls for repo in _RunIterationQueueRepo.instances)

    assert rebalance_calls == 1
    assert cleanup_calls == 1
    assert claim_calls == 1


@pytest.mark.asyncio
async def test_pipeline_worker_auto_rollback_pauses_seeding():
    worker = PipelineWorker(worker_id="guard-worker", seed_period_seconds=1.0)
    _GuardQueueRepo.instances = []

    class _DummyTokensRepo:
        def __init__(self, _db):
            pass

    class _GuardSettingsService:
        def __init__(self, _db):
            pass

        def get(self, key: str):
            mapping = {
                "pipeline_v2_auto_rollback_enabled": "true",
                "pipeline_v2_deadletter_rollback_threshold": "0.01",
                "pipeline_v2_lag_rollback_seconds": "600",
                "pipeline_v2_due_rollback_threshold": "300",
                "pipeline_v2_rollback_cooldown_sec": "120",
            }
            return mapping.get(key)

    with (
        patch("src.pipeline.worker.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.pipeline.worker.QueueRepository", _GuardQueueRepo),
        patch("src.pipeline.worker.TokensRepository", _DummyTokensRepo),
        patch("src.pipeline.worker.SettingsService", _GuardSettingsService),
        patch.object(worker, "_seed_jobs", return_value=17) as mock_seed,
        patch("src.pipeline.worker.asyncio.sleep", new=AsyncMock()),
    ):
        await worker.run_iteration()

    assert _GuardQueueRepo.instances
    assert mock_seed.call_count == 0
    assert worker._seed_pause_reasons
    assert worker._seed_pause_until > datetime.now(tz=timezone.utc)


@pytest.mark.asyncio
async def test_pipeline_worker_auto_rollback_pauses_seeding_on_dex_error_rate():
    worker = PipelineWorker(worker_id="dex-guard-worker", seed_period_seconds=1.0)
    _RunIterationQueueRepo.instances = []

    class _DummyTokensRepo:
        def __init__(self, _db):
            pass

    class _DexGuardSettingsService:
        def __init__(self, _db):
            pass

        def get(self, key: str):
            mapping = {
                "pipeline_v2_auto_rollback_enabled": "true",
                "pipeline_v2_deadletter_rollback_threshold": "0.5",
                "pipeline_v2_lag_rollback_seconds": "9999",
                "pipeline_v2_due_rollback_threshold": "9999",
                "pipeline_v2_dex_error_rate_rollback_threshold": "0.25",
                "pipeline_v2_dex_min_requests_for_rollback": "50",
                "pipeline_v2_rollback_cooldown_sec": "120",
            }
            return mapping.get(key)

    with (
        patch("src.pipeline.worker.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.pipeline.worker.QueueRepository", _RunIterationQueueRepo),
        patch("src.pipeline.worker.TokensRepository", _DummyTokensRepo),
        patch("src.pipeline.worker.SettingsService", _DexGuardSettingsService),
        patch(
            "src.pipeline.worker.get_dex_broker_stats",
            return_value={"batch_requests": 100, "fallback_requests": 0, "request_failures": 40},
        ),
        patch.object(worker, "_seed_jobs", return_value=11) as mock_seed,
        patch("src.pipeline.worker.asyncio.sleep", new=AsyncMock()),
    ):
        await worker.run_iteration()

    assert mock_seed.call_count == 0
    assert "dex_error_rate_threshold_exceeded" in worker._seed_pause_reasons
