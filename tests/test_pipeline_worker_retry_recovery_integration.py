from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


# Keep DB layer imports safe at module import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

from src.adapters.db.base import Base
from src.adapters.db.models import ProcessingJob, Token, TokenRuntimeState
from src.adapters.repositories.queue_repo import QueueRepository
from src.pipeline.worker import JOB_SCORING_COLD, PipelineWorker


def _integration_url() -> str | None:
    url = os.getenv("INTEGRATION_DATABASE_URL")
    if not url:
        return None
    if not url.startswith("postgresql"):
        return None
    return url


@pytest.fixture(scope="module")
def integration_engine():
    url = _integration_url()
    if not url:
        pytest.skip("INTEGRATION_DATABASE_URL is not set")

    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"integration database is unavailable: {exc}")

    Base.metadata.create_all(
        engine,
        tables=[Token.__table__, ProcessingJob.__table__, TokenRuntimeState.__table__],
    )
    yield engine
    Base.metadata.drop_all(
        engine,
        tables=[TokenRuntimeState.__table__, ProcessingJob.__table__, Token.__table__],
    )
    engine.dispose()


@pytest.fixture(autouse=True)
def _cleanup_tables(integration_engine):
    with integration_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE token_runtime_state, processing_jobs, tokens RESTART IDENTITY CASCADE"))
    yield


def _make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.mark.asyncio
async def test_pipeline_worker_retries_then_acks_without_job_loss(integration_engine):
    session_factory = _make_session_factory(integration_engine)

    with session_factory() as db:
        queue_repo = QueueRepository(db)
        job_id = queue_repo.enqueue_job(
            job_type=JOB_SCORING_COLD,
            token_id=None,
            priority=100,
            idempotency_key="integration:worker:retry:1",
        )
        assert job_id is not None

    worker = PipelineWorker(
        worker_id="integration-worker",
        claim_limit=1,
        lease_seconds=20,
        seed_period_seconds=3600.0,
        max_attempts=8,
    )
    worker._last_seed_at = datetime.now(tz=timezone.utc)

    class _DummyTokensRepo:
        def __init__(self, _db):
            pass

    class _DummySettings:
        def __init__(self, _db):
            pass

        def get(self, _key: str):
            return None

    class _DummyScoring:
        def __init__(self, _repo, _settings):
            pass

    class _DummyBatchClient:
        async def get_pairs_for_mints(self, mints):
            return {mint: [] for mint in mints}

    calls = {"count": 0}

    async def _process_single_job_side_effect(*, queue_repo, job, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("dex_pairs_unavailable")
        queue_repo.ack_job(job.id, worker_id=worker.worker_id)

    with (
        patch("src.pipeline.worker.SessionLocal", session_factory),
        patch("src.pipeline.worker.get_config", return_value=SimpleNamespace(dex_broker_enabled=False)),
        patch("src.pipeline.worker.TokensRepository", _DummyTokensRepo),
        patch("src.pipeline.worker.SettingsService", _DummySettings),
        patch("src.pipeline.worker.ScoringService", _DummyScoring),
        patch("src.pipeline.worker.get_batch_client", return_value=_DummyBatchClient()),
        patch.object(worker, "_process_single_job", side_effect=_process_single_job_side_effect),
        patch.object(worker, "_compute_retry_delay", return_value=1),
        patch("src.pipeline.worker.asyncio.sleep", new=AsyncMock()),
    ):
        # First iteration fails job -> retry
        await worker.run_iteration()

    with session_factory() as db:
        row = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        assert row is not None
        assert row.status == "retry"
        assert int(row.attempts or 0) >= 1
        assert row.last_error is not None

    # Make retry immediately due.
    with integration_engine.begin() as conn:
        conn.execute(
            text("UPDATE processing_jobs SET run_at = :run_at WHERE id = :job_id"),
            {"run_at": datetime.now(tz=timezone.utc) - timedelta(seconds=5), "job_id": job_id},
        )

    with (
        patch("src.pipeline.worker.SessionLocal", session_factory),
        patch("src.pipeline.worker.get_config", return_value=SimpleNamespace(dex_broker_enabled=False)),
        patch("src.pipeline.worker.TokensRepository", _DummyTokensRepo),
        patch("src.pipeline.worker.SettingsService", _DummySettings),
        patch("src.pipeline.worker.ScoringService", _DummyScoring),
        patch("src.pipeline.worker.get_batch_client", return_value=_DummyBatchClient()),
        patch.object(worker, "_process_single_job", side_effect=_process_single_job_side_effect),
        patch.object(worker, "_compute_retry_delay", return_value=1),
        patch("src.pipeline.worker.asyncio.sleep", new=AsyncMock()),
    ):
        # Second iteration acks job
        await worker.run_iteration()

    with session_factory() as db:
        row = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        assert row is not None
        assert row.status == "done"
        assert row.lease_until is None
        assert row.leased_by is None
        assert calls["count"] == 2
