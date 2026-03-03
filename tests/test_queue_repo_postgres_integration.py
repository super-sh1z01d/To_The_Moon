from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


# Keep DB layer imports safe at module import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

from src.adapters.db.base import Base
from src.adapters.db.models import ProcessingJob, Token, TokenRuntimeState
from src.adapters.repositories.queue_repo import QueueRepository


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


def _make_session(engine):
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return factory()


def test_claim_and_recover_expired_lease(integration_engine):
    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        job_id = repo.enqueue_job(
            job_type="scoring_hot",
            token_id=None,
            priority=100,
            idempotency_key="integration:lease:job",
        )
        assert job_id is not None

    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        claimed = repo.claim_jobs(worker_id="worker-a", limit=1, lease_seconds=30)
        assert len(claimed) == 1
        assert claimed[0].id == job_id
        assert claimed[0].status == "leased"

    # Simulate crashed worker by expiring lease manually.
    with integration_engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE processing_jobs
                SET lease_until = :expired, status = 'leased', leased_by = 'worker-a'
                WHERE id = :job_id
                """
            ),
            {"expired": datetime.now(tz=timezone.utc) - timedelta(seconds=5), "job_id": job_id},
        )

    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        requeued = repo.requeue_expired_leases(limit=10)
        assert requeued == 1

    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        claimed = repo.claim_jobs(worker_id="worker-b", limit=1, lease_seconds=30)
        assert len(claimed) == 1
        assert claimed[0].id == job_id
        assert claimed[0].leased_by == "worker-b"


def test_heartbeat_extends_lease(integration_engine):
    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        job_id = repo.enqueue_job(
            job_type="activation_check",
            token_id=None,
            priority=80,
            idempotency_key="integration:hb:job",
        )
        assert job_id is not None

    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        claimed = repo.claim_jobs(worker_id="worker-hb", limit=1, lease_seconds=10)
        assert len(claimed) == 1
        before = claimed[0].lease_until
        assert before is not None

    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        touched = repo.heartbeat_jobs(worker_id="worker-hb", job_ids=[job_id], lease_seconds=60)
        assert touched == 1

    with _make_session(integration_engine) as db:
        row = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        assert row is not None
        assert row.lease_until is not None
        if row.lease_until and row.lease_until.tzinfo is None:
            row_lease = row.lease_until.replace(tzinfo=timezone.utc)
        else:
            row_lease = row.lease_until
        if before and before.tzinfo is None:
            before_lease = before.replace(tzinfo=timezone.utc)
        else:
            before_lease = before
        assert row_lease is not None and before_lease is not None and row_lease > before_lease


def test_rebalance_boosts_stale_retry_priority(integration_engine):
    stale_run_at = datetime.now(tz=timezone.utc) - timedelta(minutes=15)
    with integration_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO processing_jobs
                (job_type, token_id, status, priority, run_at, attempts, created_at, updated_at)
                VALUES
                ('scoring_cold', NULL, 'retry', 120, :run_at, 2, NOW(), NOW())
                """
            ),
            {"run_at": stale_run_at},
        )

    with _make_session(integration_engine) as db:
        repo = QueueRepository(db)
        result = repo.rebalance_queue()
        assert result["boosted_retries"] >= 1

    with _make_session(integration_engine) as db:
        row = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.job_type == "scoring_cold")
            .filter(ProcessingJob.status == "retry")
            .first()
        )
        assert row is not None
        assert int(row.priority or 0) > 120
