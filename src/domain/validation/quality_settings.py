"""
Настройки качества данных для гибкой валидации.
"""
from __future__ import annotations

from src.domain.settings.service import SettingsService


class DataQualitySettings:
    """Настройки качества данных."""
    
    def __init__(self, settings_service: SettingsService):
        self.settings = settings_service
    
    def get_strict_validation_mode(self) -> bool:
        """Получить режим строгой валидации."""
        return self.settings.get("strict_data_validation") == "true"
    
    def get_min_liquidity_for_warnings(self) -> float:
        """Минимальная ликвидность для предупреждений о нулевых транзакциях."""
        try:
            return float(self.settings.get("min_liquidity_for_warnings") or 10000)
        except (ValueError, TypeError):
            return 10000.0
    
    def get_min_transactions_for_warnings(self) -> int:
        """Минимальное количество транзакций для предупреждений о нулевом движении цены."""
        try:
            return int(self.settings.get("min_transactions_for_warnings") or 200)
        except (ValueError, TypeError):
            return 200
    
    def get_max_stale_minutes(self) -> int:
        """Максимальный возраст данных в минутах."""
        try:
            return int(self.settings.get("max_stale_minutes") or 10)
        except (ValueError, TypeError):
            return 10