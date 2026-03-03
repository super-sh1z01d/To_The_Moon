from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.scheduler.tasks import archive_once
from src.domain.users.auth_service import get_current_admin_user
from src.domain.users.schemas import User
from src.adapters.db.deps import get_db
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.queue_repo import QueueRepository
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.repositories import user_repo
from src.domain.settings.service import SettingsService


router = APIRouter(prefix="/admin", tags=["admin"])


class QueueCanaryPayload(BaseModel):
    percent: int = Field(description="Canary percentage for v2 job seeding", ge=0, le=100)


@router.post("/recalculate")
async def recalculate_all(current_admin: User = Depends(get_current_admin_user)) -> dict:
    async def _run_v2_once() -> None:
        from src.pipeline.worker import PipelineWorker

        worker = PipelineWorker(seed_period_seconds=1.0)
        await worker.run_iteration()

    asyncio.create_task(_run_v2_once())
    return {"status": "started", "mode": "queue_v2"}


@router.post("/archive")
async def run_archiver(current_admin: User = Depends(get_current_admin_user)) -> dict:
    """Принудительно запустить архивацию токенов."""
    def run_archive():
        archive_once()
    
    # Запускаем в отдельном потоке, чтобы не блокировать API
    asyncio.get_event_loop().run_in_executor(None, run_archive)
    return {"status": "archiver_started"}


@router.post("/activation")
async def run_activation(current_admin: User = Depends(get_current_admin_user)) -> dict:
    """Принудительно запустить проверку активации токенов."""
    from src.pipeline.worker import JOB_ACTIVATION

    with SessionLocal() as sess:
        token_repo = TokensRepository(sess)
        settings = SettingsService(sess)
        queue_repo = QueueRepository(sess)

        monitoring_limit = int(settings.get("pipeline_activation_batch") or 120)
        active_limit = int(settings.get("pipeline_active_check_batch") or 80)

        monitoring = token_repo.list_by_status("monitoring", limit=monitoring_limit)
        active = token_repo.list_by_status("active", limit=active_limit)

        jobs = []
        for token in monitoring:
            jobs.append(
                {
                    "job_type": JOB_ACTIVATION,
                    "token_id": token.id,
                    "priority": 400,
                    "idempotency_key": f"{JOB_ACTIVATION}:{token.id}",
                }
            )
        for token in active:
            jobs.append(
                {
                    "job_type": JOB_ACTIVATION,
                    "token_id": token.id,
                    "priority": 390,
                    "idempotency_key": f"{JOB_ACTIVATION}:{token.id}",
                }
            )

        inserted = queue_repo.enqueue_many(jobs)

    return {
        "status": "activation_jobs_enqueued",
        "mode": "queue_v2",
        "inserted_jobs": inserted,
    }


@router.post("/queue/rebalance")
async def rebalance_queue(current_admin: User = Depends(get_current_admin_user)) -> dict:
    """Requeue expired leases and boost stale retry jobs."""
    with SessionLocal() as sess:
        queue_repo = QueueRepository(sess)
        result = queue_repo.rebalance_queue()
        health = queue_repo.queue_health()
    return {
        "status": "ok",
        "rebalance": result,
        "queue": health,
    }


@router.post("/queue/canary")
async def set_queue_canary(
    payload: QueueCanaryPayload,
    current_admin: User = Depends(get_current_admin_user),
) -> dict:
    """Set v2 queue worker canary percentage."""
    allowed_steps = {0, 10, 30, 60, 100}
    if payload.percent not in allowed_steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"percent must be one of {sorted(allowed_steps)}",
        )

    with SessionLocal() as sess:
        settings = SettingsService(sess)
        previous = int(settings.get("pipeline_v2_canary_percent") or 100)
        settings.set("pipeline_v2_canary_percent", str(payload.percent))
        current = int(settings.get("pipeline_v2_canary_percent") or payload.percent)

    from src.pipeline.worker import get_pipeline_worker_state

    return {
        "status": "ok",
        "previous_percent": previous,
        "current_percent": current,
        "allowed_steps": sorted(allowed_steps),
        "pipeline_worker": get_pipeline_worker_state(),
    }


@router.get("/users")
async def get_users(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> dict:
    """Получить список всех пользователей (только для админов)."""
    users = user_repo.get_all_users(db)

    users_data = []
    for user in users:
        users_data.append({
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "auth_provider": user.auth_provider,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "has_google_id": user.google_id is not None,
            "has_password": user.hashed_password is not None,
        })

    return {
        "total": len(users_data),
        "users": users_data
    }
