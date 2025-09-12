#!/usr/bin/env python3
"""
Демонстрация улучшений в формулах скоринга.
Сравнивает старые и новые версии формул.
"""

from __future__ import annotations

import math
import sys
import logging
from src.core.json_logging import configure_logging


def _clip01(x: float) -> float:
    """Функция клиппинга к диапазону [0, 1]."""
    return max(0.0, min(1.0, x))


def old_formulas(dp5: float, dp15: float) -> tuple[float, float]:
    """Старые формулы с проблемами."""
    # Старая формула волатильности - слишком резкая
    s_old = _clip01(dp5 / 0.1)
    
    # Старая формула momentum - проблема деления на малые числа
    m_old = _clip01(dp5 / (dp15 + 0.001))
    
    return s_old, m_old


def new_formulas(dp5: float, dp15: float) -> tuple[float, float]:
    """Новые улучшенные формулы."""
    # Новая формула волатильности - логарифмическое сглаживание
    s_new = _clip01(math.log(1 + dp5 * 10) / math.log(11)) if dp5 > 0 else 0.0
    
    # Новая формула momentum - защита от деления на малые числа
    m_new = _clip01(dp5 / max(abs(dp15), 0.01))
    
    return s_new, m_new


def demo_improvements():
    """Демонстрирует улучшения в формулах."""
    configure_logging(level="INFO")
    
    print("Демонстрация улучшений формул скоринга")
    print("=" * 50)
    print()
    
    # Тестовые случаи, которые показывают проблемы старых формул
    test_cases = [
        # (dp5, dp15, описание)
        (0.05, 0.08, "Нормальные значения"),
        (0.12, 0.001, "Малое dp15 - проблема momentum"),
        (0.02, 0.0, "Нулевое dp15 - деление на ноль"),
        (0.15, 0.05, "Высокая волатильность"),
        (0.01, 0.12, "Низкая краткосрочная активность"),
        (0.08, 0.002, "Экстремально малое dp15"),
    ]
    
    print("Сравнение компонента волатильности (s):")
    print("ΔP_5m  | Старая s | Новая s | Улучшение")
    print("-" * 45)
    
    for dp5, dp15, desc in test_cases:
        s_old, _ = old_formulas(dp5, dp15)
        s_new, _ = new_formulas(dp5, dp15)
        improvement = "✅" if abs(s_new - s_old) < 0.3 else "🔧"
        print(f"{dp5:5.3f}  |  {s_old:.3f}   |  {s_new:.3f}   | {improvement} {desc}")
    
    print()
    print("Сравнение компонента momentum (m):")
    print("ΔP_5m  | ΔP_15m | Старая m | Новая m | Проблема")
    print("-" * 55)
    
    for dp5, dp15, desc in test_cases:
        _, m_old = old_formulas(dp5, dp15)
        _, m_new = new_formulas(dp5, dp15)
        
        # Проверяем на экстремальные значения
        is_extreme = m_old > 0.9 and dp15 < 0.01
        problem = "❌ Экстремум" if is_extreme else "✅ Норма"
        
        print(f"{dp5:5.3f}  | {dp15:6.3f} |  {m_old:.3f}   |  {m_new:.3f}   | {problem}")
    
    print()
    print("Демонстрация логарифмического сглаживания волатильности:")
    print("ΔP_5m  | Линейная | Логарифм. | Разница")
    print("-" * 42)
    
    volatility_test = [0.01, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20]
    
    for vol in volatility_test:
        linear = _clip01(vol / 0.1)  # Старая формула
        logarithmic = _clip01(math.log(1 + vol * 10) / math.log(11))  # Новая
        diff = abs(linear - logarithmic)
        print(f"{vol:5.3f}  |  {linear:.3f}   |   {logarithmic:.3f}    | {diff:.3f}")
    
    print()
    print("Ключевые улучшения:")
    print("✅ Волатильность: логарифмическое сглаживание вместо линейного")
    print("✅ Momentum: защита от деления на очень малые числа") 
    print("✅ Более стабильное поведение при экстремальных значениях")
    print("✅ Меньше артефактов и резких скачков")


if __name__ == "__main__":
    demo_improvements()
