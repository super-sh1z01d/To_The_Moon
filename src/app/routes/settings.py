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
    
    try:
        svc.set(key, payload.value)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # После обновления возвращаем актуальное значение
    value = svc.get(key)
    return SettingItem(key=key, value=value)


@router.get("/validation/errors", response_model=list[str])
async def get_validation_errors(db: Session = Depends(get_db)) -> list[str]:
    """Get list of current setting validation errors."""
    svc = SettingsService(db)
    return svc.validate_all_settings()


class WeightsResponse(BaseModel):
    hybrid_momentum: dict[str, float] = Field(description="Hybrid momentum model weights")
    legacy: dict[str, float] = Field(description="Legacy model weights")
    active_model: str = Field(description="Currently active scoring model")


@router.get("/weights", response_model=WeightsResponse)
async def get_weights(db: Session = Depends(get_db)) -> WeightsResponse:
    """Get all scoring model weights."""
    svc = SettingsService(db)
    
    return WeightsResponse(
        hybrid_momentum=svc.get_hybrid_momentum_weights(),
        legacy=svc.get_legacy_weights(),
        active_model=svc.get("scoring_model_active") or "hybrid_momentum"
    )


class ModelSwitchRequest(BaseModel):
    model: str = Field(description="Model to switch to: 'legacy' or 'hybrid_momentum'")


@router.post("/model/switch")
async def switch_scoring_model(
    request: ModelSwitchRequest, 
    db: Session = Depends(get_db)
) -> dict[str, str]:
    """Switch active scoring model."""
    svc = SettingsService(db)
    
    if request.model not in ["legacy", "hybrid_momentum"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model. Must be 'legacy' or 'hybrid_momentum'"
        )
    
    try:
        svc.set("scoring_model_active", request.model)
        return {
            "message": f"Switched to {request.model} scoring model",
            "active_model": request.model
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
