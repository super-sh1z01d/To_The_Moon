from fastapi import APIRouter
from src.core.config import get_config


router = APIRouter()


@router.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


@router.get("/version", tags=["meta"])
async def version() -> dict:
    cfg = get_config()
    return {"name": cfg.app_name, "version": cfg.app_version, "env": cfg.app_env}

