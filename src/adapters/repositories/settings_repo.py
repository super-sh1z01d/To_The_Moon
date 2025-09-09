from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from src.adapters.db.models import AppSetting


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> dict[str, Optional[str]]:
        rows = self.db.query(AppSetting).all()
        return {r.key: r.value for r in rows}

    def get(self, key: str) -> Optional[str]:
        row = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        return row.value if row else None

    def set(self, key: str, value: Optional[str]) -> None:
        obj = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        if obj is None:
            obj = AppSetting(key=key, value=value)
            self.db.add(obj)
        else:
            obj.value = value
        self.db.commit()

