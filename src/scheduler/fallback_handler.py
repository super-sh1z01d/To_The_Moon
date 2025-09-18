"""
Fallback механизмы для обработки проблемных токенов.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService

log = logging.getLogger("fallback_handler")


class TokenFallbackHandler:
    """Обработчик fallback сценариев для токенов."""
    
    def __init__(self, repo: TokensRepository, settings: SettingsService):
        self.repo = repo
        self.settings = settings
    
    def should_use_fallback_score(self, token_id: int, current_score: float) -> tuple[bool, Optional[float]]:
        """
        Определить, нужно ли использовать fallback скор.
        
        Returns:
            (should_use_fallback, fallback_score)
        """
        # Получаем историю скоров
        history = self.repo.get_score_history(token_id, limit=5)
        
        if len(history) < 2:
            return False, None
            
        # Если текущий скор 0, но предыдущие были высокими
        if current_score == 0.0:
            recent_scores = [h.score for h in history[1:4] if h.score and h.score > 0]
            
            if recent_scores and len(recent_scores) >= 2:
                avg_recent = sum(recent_scores) / len(recent_scores)
                
                # Если средний скор за последние записи > 0.5, используем деградированный скор
                if avg_recent > 0.5:
                    fallback_score = avg_recent * 0.7  # Снижаем на 30%
                    log.info(
                        "fallback_score_applied",
                        extra={
                            "token_id": token_id,
                            "current_score": current_score,
                            "fallback_score": fallback_score,
                            "avg_recent": avg_recent
                        }
                    )
                    return True, fallback_score
        
        return False, None
    
    def handle_stale_token(self, token_id: int, minutes_stale: int) -> bool:
        """
        Обработать токен с устаревшими данными.
        
        Returns:
            True если токен был обработан
        """
        max_stale = int(self.settings.get("max_stale_minutes") or 30)
        
        if minutes_stale > max_stale:
            # Попробуем принудительно обновить
            token = self.repo.get_by_id(token_id)
            if token:
                log.warning(
                    "forcing_stale_token_update",
                    extra={
                        "token_id": token_id,
                        "mint": token.mint_address,
                        "minutes_stale": minutes_stale
                    }
                )
                
                # Здесь можно добавить логику принудительного обновления
                # Например, пометить токен для приоритетной обработки
                return True
        
        return False
    
    def get_emergency_score(self, token_id: int) -> Optional[float]:
        """
        Получить аварийный скор для токена при полном отказе данных.
        """
        # Берем медианный скор за последние 10 записей
        history = self.repo.get_score_history(token_id, limit=10)
        
        if not history:
            return None
            
        valid_scores = [h.smoothed_score for h in history if h.smoothed_score and h.smoothed_score > 0]
        
        if len(valid_scores) >= 3:
            valid_scores.sort()
            median_score = valid_scores[len(valid_scores) // 2]
            emergency_score = median_score * 0.5  # Сильно снижаем
            
            log.warning(
                "emergency_score_used",
                extra={
                    "token_id": token_id,
                    "emergency_score": emergency_score,
                    "median_score": median_score,
                    "history_count": len(valid_scores)
                }
            )
            
            return emergency_score
        
        return None