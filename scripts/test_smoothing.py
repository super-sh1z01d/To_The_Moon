#!/usr/bin/env python3
"""
Скрипт для демонстрации работы сглаживания скоров.
Показывает разницу между обычными и сглаженными скорами.
"""

from __future__ import annotations

import sys
import logging
from src.core.json_logging import configure_logging
from src.domain.scoring.scorer import compute_smoothed_score


def demo_smoothing():
    """Демонстрирует эффект сглаживания на примере волатильных скоров."""
    configure_logging(level="INFO")
    log = logging.getLogger("smoothing_demo")
    
    # Симуляция волатильных скоров
    raw_scores = [0.5, 0.8, 0.3, 0.9, 0.2, 0.7, 0.4, 0.85, 0.25, 0.75]
    alpha = 0.3  # Коэффициент сглаживания
    
    print("Демонстрация сглаживания скоров")
    print("=" * 50)
    print(f"Коэффициент α = {alpha}")
    print(f"Формула: smoothed = α × new + (1-α) × previous")
    print()
    print("Шаг | Исходный | Сглаженный | Изменение")
    print("-" * 45)
    
    smoothed_score = None
    total_raw_volatility = 0
    total_smooth_volatility = 0
    
    for i, raw_score in enumerate(raw_scores):
        previous_smooth = smoothed_score
        smoothed_score = compute_smoothed_score(raw_score, smoothed_score, alpha)
        
        # Вычисляем волатильность (изменение от предыдущего значения)
        if i > 0:
            raw_change = abs(raw_score - raw_scores[i-1])
            smooth_change = abs(smoothed_score - previous_smooth) if previous_smooth else 0
            total_raw_volatility += raw_change
            total_smooth_volatility += smooth_change
            change_str = f"{smooth_change:+.3f}"
        else:
            change_str = "—"
        
        print(f" {i+1:2d}  |   {raw_score:.3f}   |   {smoothed_score:.3f}    | {change_str}")
    
    print("-" * 45)
    print(f"Общая волатильность:")
    print(f"Исходные скоры:   {total_raw_volatility:.3f}")
    print(f"Сглаженные скоры: {total_smooth_volatility:.3f}")
    print(f"Снижение волатильности: {((total_raw_volatility - total_smooth_volatility) / total_raw_volatility * 100):.1f}%")
    
    # Демонстрация разных коэффициентов
    print()
    print("Влияние коэффициента α:")
    print("=" * 30)
    test_scores = [0.5, 0.9, 0.1, 0.8]
    
    for alpha_test in [0.1, 0.3, 0.5, 0.8, 1.0]:
        smooth = None
        final_volatility = 0
        for i, score in enumerate(test_scores):
            prev = smooth
            smooth = compute_smoothed_score(score, smooth, alpha_test)
            if i > 0:
                final_volatility += abs(smooth - prev)
        print(f"α = {alpha_test:.1f}: волатильность = {final_volatility:.3f}")


if __name__ == "__main__":
    demo_smoothing()
