from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.adapters.db.models import ProcessingJob, TokenRuntimeState


OPEN_JOB_STATUSES = {"queued", "retry", "leased"}


class QueueRepository:
    def __init__(self, db: Session):
        self.db = db
        self._log = logging.getLogger("queue_repo")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)

    def enqueue_job(
        self,
        *,
        job_type: str,
        token_id: Optional[int] = None,
        priority: int = 100,
        run_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> Optional[int]:
        if idempotency_key and self._idempotency_key_exists(idempotency_key):
            return None

        job = ProcessingJob(
            job_type=job_type,
            token_id=token_id,
            status="queued",
            priority=priority,
            run_at=run_at or self._now(),
            lease_until=None,
            attempts=0,
            last_error=None,
            idempotency_key=idempotency_key,
            payload=payload,
            leased_by=None,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job.id

    def _idempotency_key_exists(self, idempotency_key: str) -> bool:
        existing = (
            self.db.query(ProcessingJob.id)
            .filter(ProcessingJob.idempotency_key == idempotency_key)
            .filter(ProcessingJob.status.in_(OPEN_JOB_STATUSES))
            .first()
        )
        return existing is not None

    def _find_existing_open_idempotency_keys(self, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        rows = (
            self.db.query(ProcessingJob.idempotency_key)
            .filter(ProcessingJob.idempotency_key.in_(keys))
            .filter(ProcessingJob.status.in_(OPEN_JOB_STATUSES))
            .all()
        )
        return {str(row[0]) for row in rows if row and row[0]}

    def enqueue_many(self, jobs: Iterable[dict[str, Any]]) -> int:
        prepared_jobs = list(jobs)
        if not prepared_jobs:
            return 0

        inserted = 0
        now = self._now()

        incoming_keys = [
            str(job.get("idempotency_key"))
            for job in prepared_jobs
            if job.get("idempotency_key")
        ]
        existing_keys = self._find_existing_open_idempotency_keys(incoming_keys)
        local_seen: set[str] = set()

        for raw in prepared_jobs:
            try:
                idempotency_key = raw.get("idempotency_key")
                if idempotency_key:
                    idempotency_key = str(idempotency_key)
                    if idempotency_key in existing_keys or idempotency_key in local_seen:
                        continue
                    local_seen.add(idempotency_key)

                run_at = raw.get("run_at") or now
                job = ProcessingJob(
                    job_type=str(raw.get("job_type") or "scoring_cold"),
                    token_id=raw.get("token_id"),
                    status="queued",
                    priority=int(raw.get("priority") or 100),
                    run_at=run_at,
                    lease_until=None,
                    attempts=0,
                    last_error=None,
                    idempotency_key=idempotency_key,
                    payload=raw.get("payload"),
                    leased_by=None,
                )
                self.db.add(job)
                inserted += 1
            except Exception as exc:  # noqa: BLE001
                self._log.warning(
                    "enqueue_job_failed",
                    extra={"extra": {"error": str(exc), "job": str(raw)[:200]}},
                )

        if inserted:
            self.db.commit()
        return inserted

    def claim_jobs(self, *, worker_id: str, limit: int, lease_seconds: int = 45) -> list[ProcessingJob]:
        if limit <= 0:
            return []

        now = self._now()
        lease_until = now + timedelta(seconds=max(5, lease_seconds))

        q = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.status.in_(["queued", "retry", "leased"]))
            .filter(ProcessingJob.run_at <= now)
            .filter(or_(ProcessingJob.lease_until.is_(None), ProcessingJob.lease_until < now))
            .order_by(ProcessingJob.priority.desc(), ProcessingJob.run_at.asc(), ProcessingJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

        jobs = list(q.all())

        for job in jobs:
            job.status = "leased"
            job.leased_by = worker_id
            job.lease_until = lease_until
            job.attempts = int(job.attempts or 0) + 1
            job.updated_at = now
            self.db.add(job)

        if jobs:
            self.db.commit()
        return jobs

    def heartbeat_jobs(self, *, worker_id: str, job_ids: list[int], lease_seconds: int = 45) -> int:
        if not job_ids:
            return 0

        now = self._now()
        lease_until = now + timedelta(seconds=max(5, lease_seconds))

        jobs = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.id.in_(job_ids))
            .filter(ProcessingJob.status == "leased")
            .filter(ProcessingJob.leased_by == worker_id)
            .all()
        )
        for job in jobs:
            job.lease_until = lease_until
            job.updated_at = now
            self.db.add(job)

        if jobs:
            self.db.commit()
        return len(jobs)

    def ack_job(self, job_id: int, *, worker_id: Optional[str] = None) -> bool:
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            return False
        if worker_id and job.leased_by and job.leased_by != worker_id:
            return False

        now = self._now()
        job.status = "done"
        job.leased_by = None
        job.lease_until = None
        job.last_error = None
        job.updated_at = now
        self.db.add(job)
        self.db.commit()
        return True

    def fail_job(
        self,
        job_id: int,
        *,
        error: str,
        worker_id: Optional[str] = None,
        retry_delay_seconds: int = 30,
        max_attempts: int = 8,
    ) -> bool:
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            return False
        if worker_id and job.leased_by and job.leased_by != worker_id:
            return False

        now = self._now()
        attempts = int(job.attempts or 0)

        job.last_error = error[:2000]
        job.leased_by = None
        job.lease_until = None
        job.updated_at = now

        if attempts >= max_attempts:
            job.status = "deadletter"
            job.run_at = now
        else:
            job.status = "retry"
            job.run_at = now + timedelta(seconds=max(1, retry_delay_seconds))

        self.db.add(job)
        self.db.commit()
        return True

    def defer_job(
        self,
        job_id: int,
        *,
        worker_id: Optional[str] = None,
        delay_seconds: int = 30,
        reason: Optional[str] = None,
    ) -> bool:
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            return False
        if worker_id and job.leased_by and job.leased_by != worker_id:
            return False

        now = self._now()
        job.status = "retry"
        job.leased_by = None
        job.lease_until = None
        job.run_at = now + timedelta(seconds=max(1, delay_seconds))
        if reason:
            job.last_error = reason[:2000]
        job.updated_at = now
        self.db.add(job)
        self.db.commit()
        return True

    def requeue_expired_leases(self, *, limit: int = 1000) -> int:
        now = self._now()

        q = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.status == "leased")
            .filter(ProcessingJob.lease_until.is_not(None))
            .filter(ProcessingJob.lease_until < now)
            .order_by(ProcessingJob.lease_until.asc())
            .limit(max(1, limit))
        )
        jobs = q.all()
        for job in jobs:
            job.status = "retry"
            job.leased_by = None
            job.lease_until = None
            job.run_at = now
            job.updated_at = now
            self.db.add(job)

        if jobs:
            self.db.commit()
        return len(jobs)

    def cleanup_finished_jobs(self, *, older_than_hours: int = 24, limit: int = 5000) -> int:
        cutoff = self._now() - timedelta(hours=max(1, older_than_hours))
        q = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.status.in_(["done", "cancelled"]))
            .filter(ProcessingJob.updated_at < cutoff)
            .limit(max(1, limit))
        )
        jobs = q.all()
        removed = 0
        for job in jobs:
            self.db.delete(job)
            removed += 1
        if removed:
            self.db.commit()
        return removed

    def queue_health(self) -> dict[str, Any]:
        now = self._now()

        grouped = (
            self.db.query(ProcessingJob.status, func.count(ProcessingJob.id))
            .group_by(ProcessingJob.status)
            .all()
        )
        by_status = {status: int(count) for status, count in grouped}
        total_jobs = int(sum(by_status.values()))

        due_jobs = (
            self.db.query(func.count(ProcessingJob.id))
            .filter(ProcessingJob.status.in_(["queued", "retry"]))
            .filter(ProcessingJob.run_at <= now)
            .scalar()
            or 0
        )
        leased_expired = (
            self.db.query(func.count(ProcessingJob.id))
            .filter(ProcessingJob.status == "leased")
            .filter(ProcessingJob.lease_until.is_not(None))
            .filter(ProcessingJob.lease_until < now)
            .scalar()
            or 0
        )

        oldest_due_row = (
            self.db.query(ProcessingJob.run_at)
            .filter(ProcessingJob.status.in_(["queued", "retry"]))
            .filter(ProcessingJob.run_at <= now)
            .order_by(ProcessingJob.run_at.asc())
            .first()
        )
        lag_seconds = 0
        if oldest_due_row and oldest_due_row[0]:
            lag_seconds = max(0, int((now - oldest_due_row[0]).total_seconds()))

        by_type_rows = (
            self.db.query(ProcessingJob.job_type, func.count(ProcessingJob.id))
            .group_by(ProcessingJob.job_type)
            .all()
        )
        by_type = {str(job_type): int(count) for job_type, count in by_type_rows}
        deadletter_count = int(by_status.get("deadletter", 0))
        deadletter_rate = (deadletter_count / total_jobs) if total_jobs > 0 else 0.0

        return {
            "total": total_jobs,
            "due": int(due_jobs),
            "lag_seconds": lag_seconds,
            "leased_expired": int(leased_expired),
            "deadletter_rate": round(deadletter_rate, 6),
            "by_status": {
                "queued": int(by_status.get("queued", 0)),
                "leased": int(by_status.get("leased", 0)),
                "retry": int(by_status.get("retry", 0)),
                "done": int(by_status.get("done", 0)),
                "deadletter": int(by_status.get("deadletter", 0)),
                "cancelled": int(by_status.get("cancelled", 0)),
            },
            "by_type": by_type,
        }

    def rebalance_queue(self) -> dict[str, int]:
        # 1) Requeue expired leases.
        requeued = self.requeue_expired_leases(limit=5000)

        # 2) Boost priority for long-waiting retries.
        now = self._now()
        stale_cutoff = now - timedelta(minutes=5)
        stale_retry = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.status == "retry")
            .filter(ProcessingJob.run_at < stale_cutoff)
            .order_by(ProcessingJob.run_at.asc())
            .limit(2000)
            .all()
        )

        boosted = 0
        for job in stale_retry:
            old = int(job.priority or 0)
            new = min(old + 20, 10_000)
            if new != old:
                job.priority = new
                job.updated_at = now
                self.db.add(job)
                boosted += 1

        if boosted:
            self.db.commit()

        return {"requeued_expired": requeued, "boosted_retries": boosted}

    def get_runtime_state(self, token_id: int) -> Optional[TokenRuntimeState]:
        return self.db.query(TokenRuntimeState).filter(TokenRuntimeState.token_id == token_id).first()

    def touch_runtime_state(
        self,
        *,
        token_id: int,
        scored_at: Optional[datetime] = None,
        activation_checked_at: Optional[datetime] = None,
        score_band: Optional[str] = None,
        backoff_until: Optional[datetime] = None,
        clear_backoff: bool = False,
    ) -> None:
        state = self.get_runtime_state(token_id)
        now = self._now()

        if state is None:
            state = TokenRuntimeState(
                token_id=token_id,
                last_scored_at=scored_at,
                last_activation_check_at=activation_checked_at,
                score_band=score_band,
                backoff_until=None if clear_backoff else backoff_until,
                version=1,
                updated_at=now,
            )
        else:
            if scored_at is not None:
                state.last_scored_at = scored_at
            if activation_checked_at is not None:
                state.last_activation_check_at = activation_checked_at
            if score_band is not None:
                state.score_band = score_band
            if clear_backoff:
                state.backoff_until = None
            elif backoff_until is not None:
                state.backoff_until = backoff_until
            state.version = int(state.version or 0) + 1
            state.updated_at = now

        self.db.add(state)
        self.db.commit()
