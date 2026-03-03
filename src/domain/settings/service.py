from __future__ import annotations

import logging
import time
from typing import Optional
from sqlalchemy.orm import Session

from src.adapters.repositories.settings_repo import SettingsRepository
from .defaults import DEFAULT_SETTINGS

LEGACY_SETTING_KEYS = {
    "weight_s",
    "weight_l",
    "weight_m",
    "weight_t",
    "score_smoothing_alpha",
    "max_price_change_5m",
}


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
            if k in LEGACY_SETTING_KEYS:
                continue
            if v is not None:
                merged[k] = v
        # Hybrid model is mandatory in v2.
        merged["scoring_model_active"] = "hybrid_momentum"
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
        if key in LEGACY_SETTING_KEYS:
            raise ValueError(f"Setting '{key}' is removed in v2")
        if key == "scoring_model_active":
            raise ValueError("Setting 'scoring_model_active' is read-only in v2")

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
            if key in ["w_tx", "w_vol", "w_fresh", "w_oi"]:
                weight = float(value)
                return weight >= 0.0
            
            # EWMA alpha parameters (must be between 0.0 and 1.0)
            if key == "ewma_alpha":
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
                      "monitoring_timeout_hours", "pipeline_v2_lag_rollback_seconds",
                      "pipeline_v2_due_rollback_threshold", "pipeline_v2_rollback_cooldown_sec",
                      "pipeline_v2_dex_min_requests_for_rollback"]:
                time_val = int(value)
                return time_val > 0

            if key == "pipeline_v2_canary_percent":
                percent = int(value)
                return 0 <= percent <= 100

            if key == "pipeline_v2_auto_rollback_enabled":
                return str(value).strip().lower() in {"true", "false", "1", "0", "yes", "no", "on", "off"}

            if key == "pipeline_v2_deadletter_rollback_threshold":
                threshold = float(value)
                return 0.0 <= threshold <= 1.0

            if key == "pipeline_v2_dex_error_rate_rollback_threshold":
                threshold = float(value)
                return 0.0 <= threshold <= 1.0
            
            # Scoring model (must be valid model name)
            if key == "scoring_model_active":
                return value == "hybrid_momentum"
            
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

    def cleanup_legacy_settings(self) -> int:
        """Remove deprecated settings keys from DB."""
        removed = self.repo.delete_many(sorted(LEGACY_SETTING_KEYS))
        # Also normalize model to hybrid-only.
        current = self.repo.get("scoring_model_active")
        if current != "hybrid_momentum":
            self.repo.set("scoring_model_active", "hybrid_momentum")
        self._cache_until = 0
        return removed
    
    def validate_all_settings(self) -> list[str]:
        """Validate all current settings and return list of validation errors."""
        errors = []
        all_settings = self.get_all()
        
        for key, value in all_settings.items():
            if not self._validate_setting(key, value):
                errors.append(f"Invalid value '{value}' for setting '{key}'")
        
        return errors
