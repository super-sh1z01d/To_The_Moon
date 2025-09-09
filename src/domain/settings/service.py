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
        prev = self.repo.get(key)
        self.repo.set(key, value)
        # Инвалидация кэша
        self._cache_until = 0
        self._log.info(
            "setting_updated",
            extra={"extra": {"key": key, "old": prev, "new": value}},
        )
