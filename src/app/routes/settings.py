from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.db.deps import get_db
from src.domain.settings.service import SettingsService
from src.domain.settings.defaults import DEFAULT_SETTINGS


router = APIRouter(prefix="/settings", tags=["settings"])


class SettingItem(BaseModel):
    key: str = Field(description="Ключ настройки")
    value: Optional[str] = Field(default=None, description="Значение (строка)")


@router.get("/", response_model=dict[str, str])
async def list_settings(db: Session = Depends(get_db)) -> dict[str, str]:
    svc = SettingsService(db)
    return svc.get_all()


@router.get("/defaults", response_model=dict[str, str])
async def list_default_settings() -> dict[str, str]:
    # Возвращаем дефолтные значения без учёта БД
    return DEFAULT_SETTINGS.copy()


@router.get("/{key}", response_model=SettingItem)
async def get_setting(key: str, db: Session = Depends(get_db)) -> SettingItem:
    svc = SettingsService(db)
    # Возвращаем значение из кэша/БД, либо дефолт, если ключ известен
    if key not in DEFAULT_SETTINGS and svc.get(key) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setting not found")
    value = svc.get(key)
    if value is None:
        value = DEFAULT_SETTINGS.get(key)
    return SettingItem(key=key, value=value)


class SettingValue(BaseModel):
    value: Optional[str]


@router.put("/{key}", response_model=SettingItem)
async def put_setting(key: str, payload: SettingValue, db: Session = Depends(get_db)) -> SettingItem:
    svc = SettingsService(db)
    svc.set(key, payload.value)
    # После обновления возвращаем актуальное значение
    value = svc.get(key)
    return SettingItem(key=key, value=value)
