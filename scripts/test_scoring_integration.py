#!/usr/bin/env python3
"""
Интеграционный тест для проверки работы сглаживания скоров.
"""

from __future__ import annotations

import sys
import logging
from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.domain.scoring.scorer import compute_score, compute_smoothed_score


def test_smoothing_integration():
    """Тестирует интеграцию сглаживания с репозиторием."""
    configure_logging(level="INFO")
    log = logging.getLogger("smoothing_test")
    
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        
        # Получаем настройки
        alpha = float(settings.get("score_smoothing_alpha") or 0.3)
        weights = {
            "weight_s": float(settings.get("weight_s") or 0.35),
            "weight_l": float(settings.get("weight_l") or 0.25),
            "weight_m": float(settings.get("weight_m") or 0.20),
            "weight_t": float(settings.get("weight_t") or 0.20),
        }
        
        print(f"Настройки сглаживания: α = {alpha}")
        print(f"Веса скоринга: {weights}")
        print()
        
        # Найдем тестовый токен или создадим
        test_mint = "TestSmoothingMint1111111111111111111111"
        token = repo.get_by_mint(test_mint)
        
        if not token:
            # Создаем тестовый токен
            inserted = repo.insert_monitoring(
                mint=test_mint,
                name="Test Smoothing Token", 
                symbol="TST"
            )
            if not inserted:
                print("Ошибка: не удалось создать тестовый токен")
                return
            token = repo.get_by_mint(test_mint)
            repo.set_active(token)
            print(f"✅ Создан тестовый токен: {test_mint}")
        
        # Симулируем несколько обновлений с волатильными метриками
        test_metrics = [
            {"L_tot": 10000, "delta_p_5m": 0.08, "delta_p_15m": 0.05, "n_5m": 150},  # score ≈ 0.7
            {"L_tot": 50000, "delta_p_5m": 0.02, "delta_p_15m": 0.08, "n_5m": 80},   # score ≈ 0.5
            {"L_tot": 8000, "delta_p_5m": 0.12, "delta_p_15m": 0.03, "n_5m": 200},  # score ≈ 0.8
            {"L_tot": 30000, "delta_p_5m": 0.01, "delta_p_15m": 0.06, "n_5m": 60},  # score ≈ 0.4
        ]
        
        print("Симуляция обновлений скоров:")
        print("Шаг | Исходный | Сглаженный | Разница")
        print("-" * 40)
        
        previous_raw = None
        previous_smooth = None
        
        for i, metrics in enumerate(test_metrics):
            # Вычисляем исходный скор
            raw_score, _ = compute_score(metrics, weights)
            
            # Получаем предыдущий сглаженный скор
            prev_smoothed_score = repo.get_previous_smoothed_score(token.id)
            
            # Вычисляем сглаженный скор
            smoothed_score = compute_smoothed_score(raw_score, prev_smoothed_score, alpha)
            
            # Сохраняем в БД
            snap_id = repo.insert_score_snapshot(
                token_id=token.id,
                metrics=metrics,
                score=raw_score,
                smoothed_score=smoothed_score
            )
            
            # Показываем результат
            raw_change = f"{raw_score - previous_raw:+.3f}" if previous_raw else "—"
            smooth_change = f"{smoothed_score - previous_smooth:+.3f}" if previous_smooth else "—"
            
            print(f" {i+1:2d}  |  {raw_score:.3f}   |   {smoothed_score:.3f}    | Δ={smooth_change}")
            
            previous_raw = raw_score
            previous_smooth = smoothed_score
        
        print()
        
        # Проверяем историю
        history = repo.get_score_history(token.id, limit=10)
        print(f"✅ Сохранено {len(history)} записей в истории")
        
        # Проверяем последний снапшот
        latest = repo.get_latest_snapshot(token.id)
        if latest:
            print(f"✅ Последний снапшот: score={latest.score}, smoothed_score={latest.smoothed_score}")
        
        print()
        print("🎉 Тест сглаживания прошел успешно!")
        print(f"📊 Токен для проверки в UI: {test_mint}")


if __name__ == "__main__":
    test_smoothing_integration()
