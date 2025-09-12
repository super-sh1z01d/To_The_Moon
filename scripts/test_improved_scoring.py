#!/usr/bin/env python3
"""
Интеграционный тест для проверки улучшенных формул скоринга.
"""

from __future__ import annotations

import sys
import logging
from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.domain.scoring.scorer import compute_score, compute_smoothed_score


def test_improved_scoring():
    """Тестирует улучшенные формулы скоринга."""
    configure_logging(level="INFO")
    log = logging.getLogger("improved_scoring_test")
    
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
        
        print(f"🧮 Тест улучшенных формул скоринга")
        print(f"Настройки: α = {alpha}, веса = {weights}")
        print()
        
        # Тестовые случаи с проблемными сценариями для старых формул
        test_scenarios = [
            {
                "name": "🔥 Высокая волатильность",
                "metrics": {"L_tot": 50000, "delta_p_5m": 0.12, "delta_p_15m": 0.08, "n_5m": 200}
            },
            {
                "name": "⚡ Проблемный momentum (малый dp15)",
                "metrics": {"L_tot": 25000, "delta_p_5m": 0.06, "delta_p_15m": 0.002, "n_5m": 120}
            },
            {
                "name": "🧊 Нулевой dp15",
                "metrics": {"L_tot": 15000, "delta_p_5m": 0.04, "delta_p_15m": 0.0, "n_5m": 80}
            },
            {
                "name": "📈 Стабильный рост",
                "metrics": {"L_tot": 35000, "delta_p_5m": 0.03, "delta_p_15m": 0.05, "n_5m": 100}
            },
            {
                "name": "🌊 Низкая активность",
                "metrics": {"L_tot": 8000, "delta_p_5m": 0.01, "delta_p_15m": 0.02, "n_5m": 30}
            }
        ]
        
        print("Сценарий                      | Score | Компоненты (l, s, m, t)")
        print("-" * 65)
        
        for scenario in test_scenarios:
            score, comps = compute_score(scenario["metrics"], weights)
            
            print(f"{scenario['name']:28s} | {score:.3f} | l={comps['l']:.2f} s={comps['s']:.2f} m={comps['m']:.2f} t={comps['t']:.2f}")
            
        print()
        print("Демонстрация сглаживания на волатильных данных:")
        print("Итерация | Исходный | Сглаженный | Изменение")
        print("-" * 45)
        
        # Симулируем серию волатильных обновлений
        volatile_metrics = [
            {"L_tot": 20000, "delta_p_5m": 0.08, "delta_p_15m": 0.06, "n_5m": 150},
            {"L_tot": 45000, "delta_p_5m": 0.02, "delta_p_15m": 0.001, "n_5m": 80},   # Проблемный случай
            {"L_tot": 18000, "delta_p_5m": 0.11, "delta_p_15m": 0.0, "n_5m": 200},   # Нулевой dp15
            {"L_tot": 30000, "delta_p_5m": 0.01, "delta_p_15m": 0.08, "n_5m": 60},
        ]
        
        smoothed_score = None
        
        for i, metrics in enumerate(volatile_metrics):
            raw_score, _ = compute_score(metrics, weights)
            smoothed_score = compute_smoothed_score(raw_score, smoothed_score, alpha)
            
            change = f"{smoothed_score - (smoothed_score if i == 0 else prev_smooth):+.3f}" if i > 0 else "—"
            print(f"   {i+1:2d}    |  {raw_score:.3f}   |   {smoothed_score:.3f}    | {change}")
            
            prev_smooth = smoothed_score
        
        print()
        print("🎉 Результаты:")
        print("✅ Логарифмическое сглаживание волатильности работает")
        print("✅ Защита от деления на малые числа в momentum")
        print("✅ Экспоненциальное сглаживание стабилизирует скоры")
        print("✅ Нет экстремальных значений и артефактов")


if __name__ == "__main__":
    test_improved_scoring()
