from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("data_filters")


def filter_low_liquidity_pools(pairs: List[Dict[str, Any]], min_liquidity_usd: float = 500) -> List[Dict[str, Any]]:
    """
    Фильтрует пулы с низкой ликвидностью (пылинки).
    
    Args:
        pairs: Список пар от DexScreener
        min_liquidity_usd: Минимальная ликвидность пула в USD
        
    Returns:
        Отфильтрованный список пар
    """
    filtered = []
    removed_count = 0
    
    for pair in pairs:
        try:
            liquidity_usd = (pair.get("liquidity") or {}).get("usd", 0)
            if isinstance(liquidity_usd, (int, float)) and liquidity_usd >= min_liquidity_usd:
                filtered.append(pair)
            else:
                removed_count += 1
        except Exception:
            # Пропускаем пары с некорректными данными
            removed_count += 1
            continue
    
    if removed_count > 0:
        log.debug(f"Filtered {removed_count} low liquidity pools (< ${min_liquidity_usd})")
    
    return filtered


def detect_price_anomalies(delta_p_5m: float, delta_p_15m: float, max_change: float = 0.5) -> bool:
    """
    Детектирует аномальные изменения цены.
    
    Args:
        delta_p_5m: Изменение цены за 5 минут (доля)
        delta_p_15m: Изменение цены за 15 минут (доля)
        max_change: Максимальное допустимое изменение (доля)
        
    Returns:
        True если обнаружена аномалия
    """
    # Проверяем экстремальные изменения за 5 минут
    if abs(delta_p_5m) > max_change:
        log.warning(f"Extreme 5m price change detected: {delta_p_5m:.1%}")
        return True
    
    # Проверяем подозрительную разность между интервалами
    if abs(delta_p_5m) > 0.01 and abs(delta_p_15m) > 0:
        ratio = abs(delta_p_5m) / abs(delta_p_15m)
        if ratio > 15:  # 5-минутное изменение в 15+ раз больше 15-минутного
            log.warning(f"Suspicious price change ratio: 5m/15m = {ratio:.1f}")
            return True
    
    return False


def sanitize_price_changes(delta_p_5m: float, delta_p_15m: float, max_change: float = 0.5) -> Tuple[float, float]:
    """
    Очищает аномальные изменения цены, ограничивая их разумными пределами.
    
    Args:
        delta_p_5m: Изменение цены за 5 минут
        delta_p_15m: Изменение цены за 15 минут  
        max_change: Максимальное допустимое изменение
        
    Returns:
        Кортеж (очищенный_delta_p_5m, очищенный_delta_p_15m)
    """
    # Ограничиваем экстремальные изменения
    if abs(delta_p_5m) > max_change:
        sign = 1 if delta_p_5m > 0 else -1
        delta_p_5m = max_change * sign
        log.info(f"Capped 5m price change to {delta_p_5m:.1%}")
    
    if abs(delta_p_15m) > max_change:
        sign = 1 if delta_p_15m > 0 else -1
        delta_p_15m = max_change * sign
        log.info(f"Capped 15m price change to {delta_p_15m:.1%}")
    
    return delta_p_5m, delta_p_15m


def validate_metrics_consistency(metrics: Dict[str, Any], strict_mode: bool = False) -> tuple[bool, list[str]]:
    """
    Проверяет консистентность метрик между собой с градацией серьезности.
    
    Args:
        metrics: Словарь метрик
        strict_mode: Если True, все предупреждения блокируют обновление
        
    Returns:
        Tuple (is_valid, warnings_list)
    """
    warnings = []
    critical_issues = []
    
    try:
        L_tot = float(metrics.get("L_tot", 0))
        n_5m = float(metrics.get("n_5m", 0))
        delta_p_5m = abs(float(metrics.get("delta_p_5m", 0)))
        
        # Критические проблемы (всегда блокируют)
        if L_tot < 0:
            critical_issues.append(f"Negative liquidity: ${L_tot}")
        if n_5m < 0:
            critical_issues.append(f"Negative transactions: {n_5m}")
            
        # Предупреждения (блокируют только в strict_mode)
        if L_tot > 10000 and n_5m == 0:
            warnings.append(f"High liquidity (${L_tot:.0f}) but no transactions")
            
        if n_5m > 200 and delta_p_5m < 0.001:
            warnings.append(f"Many transactions ({n_5m}) but no price movement")
            
        # Check for potentially stale transaction data
        # If we have transactions but no volume, data might be stale
        volume_5m = float(metrics.get("volume_5m", 0))
        if n_5m > 0 and volume_5m == 0:
            warnings.append(f"Transactions reported ({n_5m}) but zero volume - possibly stale data")
            
        # Логируем все проблемы
        for issue in critical_issues:
            log.error(f"Critical data issue: {issue}")
        for warning in warnings:
            log.warning(f"Data quality warning: {warning}")
            
        # Определяем валидность
        has_critical = len(critical_issues) > 0
        has_warnings = len(warnings) > 0
        
        if has_critical:
            return False, critical_issues + warnings
        elif has_warnings and strict_mode:
            return False, warnings
        else:
            return True, warnings
        
    except (ValueError, TypeError) as e:
        critical_issues.append(f"Invalid metric types: {str(e)}")
        log.error(f"Metrics validation error: {e}")
        return False, critical_issues


def should_skip_score_update(
    new_score: float, 
    previous_score: Optional[float], 
    min_change: float = 0.05
) -> bool:
    """
    Определяет, следует ли пропустить обновление скора из-за незначительных изменений.
    
    Args:
        new_score: Новый скор
        previous_score: Предыдущий скор  
        min_change: Минимальное значимое изменение
        
    Returns:
        True если обновление следует пропустить
    """
    if previous_score is None:
        return False  # Первое обновление всегда важно
    
    change = abs(new_score - previous_score)
    
    if change < min_change:
        log.debug(f"Skipping minor score change: {change:.3f} < {min_change}")
        return True
    
    return False


def smooth_liquidity_changes(
    new_liquidity: float, 
    previous_liquidity: Optional[float], 
    max_ratio: float = 3.0
) -> float:
    """
    Сглаживает резкие изменения ликвидности.
    
    Args:
        new_liquidity: Новое значение ликвидности
        previous_liquidity: Предыдущее значение ликвидности
        max_ratio: Максимальное допустимое отношение изменения
        
    Returns:
        Сглаженное значение ликвидности
    """
    if previous_liquidity is None or previous_liquidity <= 0:
        return new_liquidity
    
    ratio = new_liquidity / previous_liquidity
    
    # Если изменение слишком резкое - ограничиваем его
    if ratio > max_ratio:
        smoothed_liquidity = previous_liquidity * max_ratio
        log.info(f"Limited liquidity increase: ${new_liquidity:.0f} -> ${smoothed_liquidity:.0f}")
        return smoothed_liquidity
    elif ratio < (1.0 / max_ratio):
        smoothed_liquidity = previous_liquidity / max_ratio
        log.info(f"Limited liquidity decrease: ${new_liquidity:.0f} -> ${smoothed_liquidity:.0f}")
        return smoothed_liquidity
    
    return new_liquidity


def get_pool_count_anomaly_threshold(previous_count: Optional[int]) -> int:
    """
    Определяет пороговое значение для детекции аномалий в количестве пулов.
    
    Args:
        previous_count: Предыдущее количество пулов
        
    Returns:
        Максимально допустимое изменение количества пулов
    """
    if previous_count is None or previous_count <= 1:
        return 10  # Для новых токенов разрешаем больше изменений
    
    # Для установившихся токенов - более строгие ограничения
    if previous_count <= 3:
        return 2  # Может измениться на ±2 пула
    else:
        return max(2, previous_count // 2)  # Может измениться на половину


def validate_pool_count_change(new_count: int, previous_count: Optional[int]) -> bool:
    """
    Проверяет, не является ли изменение количества пулов аномальным.
    
    Args:
        new_count: Новое количество пулов
        previous_count: Предыдущее количество пулов
        
    Returns:
        True если изменение нормальное
    """
    if previous_count is None:
        return True  # Первое обновление
    
    threshold = get_pool_count_anomaly_threshold(previous_count)
    change = abs(new_count - previous_count)
    
    if change > threshold:
        log.warning(f"Suspicious pool count change: {previous_count} -> {new_count} (Δ={change})")
        return False
    
    return True
