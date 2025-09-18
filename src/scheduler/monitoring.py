"""
Мониторинг планировщика для отслеживания здоровья системы.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository

log = logging.getLogger("scheduler_monitoring")


class SchedulerHealthMonitor:
    """Мониторинг здоровья планировщика."""
    
    def __init__(self):
        self.last_hot_run: Optional[datetime] = None
        self.last_cold_run: Optional[datetime] = None
        self.hot_interval_sec = 30
        self.cold_interval_sec = 120
        
    def record_group_execution(self, group: str, tokens_processed: int, tokens_updated: int):
        """Записать выполнение группы."""
        now = datetime.now(timezone.utc)
        
        if group == "hot":
            self.last_hot_run = now
        elif group == "cold":
            self.last_cold_run = now
            
        log.info(
            "group_execution_recorded",
            extra={
                "group": group,
                "processed": tokens_processed,
                "updated": tokens_updated,
                "timestamp": now.isoformat()
            }
        )
    
    def check_scheduler_health(self) -> Dict[str, any]:
        """Проверить здоровье планировщика."""
        now = datetime.now(timezone.utc)
        health_status = {
            "overall_healthy": True,
            "issues": [],
            "last_check": now.isoformat()
        }
        
        # Проверка hot группы
        if self.last_hot_run:
            hot_delay = (now - self.last_hot_run).total_seconds()
            expected_hot_delay = self.hot_interval_sec * 2  # Допускаем 2x задержку
            
            if hot_delay > expected_hot_delay:
                issue = f"Hot group delayed by {hot_delay:.0f}s (expected {self.hot_interval_sec}s)"
                health_status["issues"].append(issue)
                health_status["overall_healthy"] = False
                log.warning("hot_group_delayed", extra={"delay_seconds": hot_delay})
        else:
            health_status["issues"].append("Hot group never executed")
            health_status["overall_healthy"] = False
            
        # Проверка cold группы
        if self.last_cold_run:
            cold_delay = (now - self.last_cold_run).total_seconds()
            expected_cold_delay = self.cold_interval_sec * 2  # Допускаем 2x задержку
            
            if cold_delay > expected_cold_delay:
                issue = f"Cold group delayed by {cold_delay:.0f}s (expected {self.cold_interval_sec}s)"
                health_status["issues"].append(issue)
                health_status["overall_healthy"] = False
                log.warning("cold_group_delayed", extra={"delay_seconds": cold_delay})
        else:
            health_status["issues"].append("Cold group never executed")
            health_status["overall_healthy"] = False
            
        return health_status
    
    def check_stale_tokens(self, max_age_minutes: int = 10) -> Dict[str, any]:
        """Проверить токены с устаревшими данными."""
        with SessionLocal() as sess:
            repo = TokensRepository(sess)
            
            # Получаем активные токены
            active_tokens = repo.list_by_status("active", limit=100)
            stale_tokens = []
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
            
            for token in active_tokens:
                snap = repo.get_latest_snapshot(token.id)
                if snap and snap.created_at < cutoff_time:
                    age_minutes = (datetime.now(timezone.utc) - snap.created_at).total_seconds() / 60
                    stale_tokens.append({
                        "symbol": token.symbol,
                        "mint": token.mint_address,
                        "age_minutes": round(age_minutes, 1),
                        "last_update": snap.created_at.isoformat()
                    })
            
            return {
                "stale_count": len(stale_tokens),
                "total_active": len(active_tokens),
                "stale_percentage": round(len(stale_tokens) / len(active_tokens) * 100, 1) if active_tokens else 0,
                "stale_tokens": stale_tokens[:10],  # Показываем первые 10
                "max_age_minutes": max_age_minutes
            }


# Глобальный экземпляр монитора
health_monitor = SchedulerHealthMonitor()


async def check_scheduler_health_endpoint():
    """Эндпоинт для проверки здоровья планировщика."""
    scheduler_health = health_monitor.check_scheduler_health()
    stale_tokens = health_monitor.check_stale_tokens()
    
    return {
        "scheduler": scheduler_health,
        "stale_tokens": stale_tokens,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }