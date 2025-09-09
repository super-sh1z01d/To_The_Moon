from __future__ import annotations

import asyncio
from fastapi import APIRouter

from src.scheduler.service import _process_group


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/recalculate")
async def recalculate_all() -> dict:
    # Запускаем оба процесса асинхронно, не дожидаясь (fire-and-forget)
    asyncio.create_task(_process_group("hot"))
    asyncio.create_task(_process_group("cold"))
    return {"status": "started"}

