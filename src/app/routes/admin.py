from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends

from src.scheduler.service import _process_group
from src.scheduler.tasks import archive_once, enforce_activation_once
from src.domain.users.auth_service import get_current_admin_user
from src.domain.users.schemas import User


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/recalculate")
async def recalculate_all(current_admin: User = Depends(get_current_admin_user)) -> dict:
    # Запускаем оба процесса асинхронно, не дожидаясь (fire-and-forget)
    asyncio.create_task(_process_group("hot"))
    asyncio.create_task(_process_group("cold"))
    return {"status": "started"}


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
    def run_activation():
        enforce_activation_once(limit_monitoring=100, limit_active=100)
    
    # Запускаем в отдельном потоке, чтобы не блокировать API
    asyncio.get_event_loop().run_in_executor(None, run_activation)
    return {"status": "activation_started"}

