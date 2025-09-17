from __future__ import annotations

import logging
import time
from typing import Optional
from sqlalchemy.orm import Session

from src.adapters.repositories.settings_repo import SettingsRepository
from .defaults import DEFAULT_SETTINGS


class SettingsService:
    def __init__(self, db: Session, ttl_seconds: int = 15):
        self.db = db
        self.repo = SettingsRepository(db)
        from typing import Optional
        self._cache: Optional[dict[str, str]] = None
        self._cache_until: float = 0.0
        self._ttl = ttl_seconds
        self._log = logging.getLogger("settings")

    def _now(self) -> float:
        return time.monotonic()

    def _load(self) -> dict[str, str]:
        db_vals = self.repo.get_all()
        merged: dict[str, str] = DEFAULT_SETTINGS.copy()
        for k, v in db_vals.items():
            if v is not None:
                merged[k] = v
        self._cache = merged
        self._cache_until = self._now() + self._ttl
        self._log.debug("settings_cache_refreshed", extra={"extra": {"size": len(merged)}})
        return merged

    def _ensure(self) -> dict[str, str]:
        if self._cache is None or self._now() >= self._cache_until:
            return self._load()
        return self._cache

    def get_all(self) -> dict[str, str]:
        return self._ensure().copy()

    def get(self, key: str) -> Optional[str]:
        return self._ensure().get(key)

    def set(self, key: str, value: Optional[str]) -> None:
        # Validate setting value before saving
        if not self._validate_setting(key, value):
            raise ValueError(f"Invalid value '{value}' for setting '{key}'")
        
        prev = self.repo.get(key)
        self.repo.set(key, value)
        # Инвалидация кэша
        self._cache_until = 0
        self._log.info(
            "setting_updated",
            extra={"extra": {"key": key, "old": prev, "new": value}},
        )
    
    def _validate_setting(self, key: str, value: Optional[str]) -> bool:
        """Validate setting value based on key type and constraints."""
        if value is None:
            return True  # Allow None values (will use defaults)
        
        try:
            # Weight parameters (must be non-negative floats)
            if key in ["weight_s", "weight_l", "weight_m", "weight_t", 
                      "w_tx", "w_vol", "w_fresh", "w_oi"]:
                weight = float(value)
                return weight >= 0.0
            
            # EWMA alpha parameters (must be between 0.0 and 1.0)
            if key in ["ewma_alpha", "score_smoothing_alpha"]:
                alpha = float(value)
                return 0.0 <= alpha <= 1.0
            
            # Threshold parameters (must be positive floats)
            if key in ["freshness_threshold_hours", "min_score", "activation_min_liquidity_usd",
                      "min_pool_liquidity_usd", "min_score_change",
                      "max_liquidity_change_ratio"]:
                threshold = float(value)
                return threshold > 0.0
            
            # Time parameters (must be positive integers)
            if key in ["hot_interval_sec", "cold_interval_sec", "archive_below_hours",
                      "monitoring_timeout_hours"]:
                time_val = int(value)
                return time_val > 0
            
            # Scoring model (must be valid model name)
            if key == "scoring_model_active":
                return value in ["legacy", "hybrid_momentum"]
            
            # For other settings, accept any string value
            return True
            
        except (ValueError, TypeError):
            return False
    
    def get_hybrid_momentum_weights(self) -> dict[str, float]:
        """Get hybrid momentum model weights as floats."""
        return {
            "w_tx": float(self.get("w_tx") or "0.25"),
            "w_vol": float(self.get("w_vol") or "0.25"),
            "w_fresh": float(self.get("w_fresh") or "0.25"),
            "w_oi": float(self.get("w_oi") or "0.25"),
        }
    
    def get_legacy_weights(self) -> dict[str, float]:
        """Get legacy model weights as floats."""
        return {
            "weight_s": float(self.get("weight_s") or "0.35"),
            "weight_l": float(self.get("weight_l") or "0.25"),
            "weight_m": float(self.get("weight_m") or "0.20"),
            "weight_t": float(self.get("weight_t") or "0.20"),
        }
    
    def validate_all_settings(self) -> list[str]:
        """Validate all current settings and return list of validation errors."""
        errors = []
        all_settings = self.get_all()
        
        for key, value in all_settings.items():
            if not self._validate_setting(key, value):
                errors.append(f"Invalid value '{value}' for setting '{key}'")
        
        return errors
