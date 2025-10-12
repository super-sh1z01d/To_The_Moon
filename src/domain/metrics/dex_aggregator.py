from __future__ import annotations

import logging
import time
from typing import Any, Optional
from datetime import datetime, timezone

from ..validation.data_filters import (
    filter_low_liquidity_pools,
    detect_price_anomalies,
    sanitize_price_changes,
    validate_metrics_consistency,
)

_WSOL_SYMBOLS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
_USDC_SYMBOLS = {"USDC", "usdc"}
# Exclude bonding curve platforms; include pumpfun-amm and pumpswap for metrics
_EXCLUDE_DEX_IDS = {"pumpfun", "launchlab"}
# Pumpfun-related DEX IDs that indicate we might need fallback data
_PUMPFUN_RELATED = {"pumpswap", "pumpfun-amm", "pumpfun"}

# Simple cache for fallback pairs data (mint -> (timestamp, pairs))
_FALLBACK_CACHE = {}
_CACHE_TTL = 300  # 5 minutes


def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _fetch_fallback_pairs(mint: str) -> Optional[list[dict[str, Any]]]:
    """
    Fetch full pairs data from token-pairs endpoint when batch data is incomplete.
    Uses simple caching to avoid repeated requests.
    """
    log = logging.getLogger("dex_aggregator")
    
    # Check cache first
    current_time = time.time()
    if mint in _FALLBACK_CACHE:
        cached_time, cached_pairs = _FALLBACK_CACHE[mint]
        if current_time - cached_time < _CACHE_TTL:
            log.debug(f"Using cached fallback pairs for {mint}")
            return cached_pairs
    
    try:
        # Lazy import to avoid circular dependencies
        from ...adapters.services.dexscreener_client import DexScreenerClient
        
        client = DexScreenerClient(timeout=3.0)
        pairs = client.get_pairs(mint)
        
        if pairs:
            # Cache the result
            _FALLBACK_CACHE[mint] = (current_time, pairs)
            log.info(f"Fetched fallback pairs for {mint}: {len(pairs)} pairs found")
            return pairs
        else:
            log.warning(f"No fallback pairs found for {mint}")
            return None
            
    except Exception as e:
        log.error(f"Failed to fetch fallback pairs for {mint}: {e}")
        return None


def aggregate_wsol_metrics(
    mint: str, 
    pairs: list[dict[str, Any]], 
    min_liquidity_usd: float = 500,
    max_price_change: float = 0.5
) -> dict[str, Any]:
    """Собирает агрегаты по WSOL/токен парам для данного mint с фильтрацией данных.

    Args:
        mint: Адрес токена
        pairs: Список пар от DexScreener
        min_liquidity_usd: Минимальная ликвидность пула для учета
        max_price_change: Максимальное изменение цены (для детекции аномалий)

    Возвращает словарь с ключами:
      - L_tot: float
      - delta_p_5m: float (как доля, например 0.052 для +5.2%)
      - delta_p_15m: float (доля)
      - n_5m: int
      - ws_pairs: int
      - primary_dex: str | None
      - primary_liq_usd: float | None
      - filtered_pools_count: int (количество отфильтрованных пулов)
    """
    log = logging.getLogger("dex_aggregator")
    
    # 1. Фильтруем пулы с низкой ликвидностью
    filtered_pairs = filter_low_liquidity_pools(pairs, min_liquidity_usd)
    
    if len(filtered_pairs) < len(pairs):
        log.debug(f"Filtered {len(pairs) - len(filtered_pairs)} low liquidity pools for {mint}")
    
    # 1.5. Check if we need fallback data (only pumpfun-related DEXs found)
    fallback_used = False
    external_dexs_found = False
    
    for p in filtered_pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            qsym = str(quote.get("symbol", "")).upper()
            
            if (str(base.get("address")) == mint and 
                dex_id not in _EXCLUDE_DEX_IDS and 
                (qsym in _WSOL_SYMBOLS or qsym in _USDC_SYMBOLS)):
                
                if dex_id not in _PUMPFUN_RELATED:
                    external_dexs_found = True
                    break
        except Exception:
            continue
    
    # If only pumpfun-related DEXs found, try fallback
    if not external_dexs_found:
        log.info(f"Only pumpfun-related DEXs found for {mint}, trying fallback")
        fallback_pairs = _fetch_fallback_pairs(mint)
        if fallback_pairs:
            # Re-filter with fallback data
            fallback_filtered = filter_low_liquidity_pools(fallback_pairs, min_liquidity_usd)
            if len(fallback_filtered) > len(filtered_pairs):
                log.info(f"Fallback improved data for {mint}: {len(filtered_pairs)} -> {len(fallback_filtered)} pairs")
                filtered_pairs = fallback_filtered
                fallback_used = True
    
    # 2. Фильтруем только пары WSOL/токен и USDC/токен, где baseToken.address == mint
    ws_pairs: list[dict[str, Any]] = []
    usdc_pairs: list[dict[str, Any]] = []
    pools_with_liquidity: list[tuple[dict[str, Any], float]] = []  # (pool_info, liquidity)
    
    for p in filtered_pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            # Используем WSOL/SOL или USDC пары данного mint за исключением pumpfun (classic)
            # (включая pumpfun-amm, pumpswap и внешние DEX)
            qsym = str(quote.get("symbol", "")).upper()
            if (str(base.get("address")) == mint and dex_id not in _EXCLUDE_DEX_IDS and (qsym in _WSOL_SYMBOLS or qsym in _USDC_SYMBOLS)):
                addr = p.get("pairAddress") or p.get("address")
                liquidity_usd = _to_float((p.get("liquidity") or {}).get("usd")) or 0.0
                
                pool_info = {
                    "address": addr,
                    "dex": dex_id,
                    "quote": (quote or {}).get("symbol"),
                    "is_wsol": True if qsym in _WSOL_SYMBOLS else False,
                    "is_usdc": True if qsym in _USDC_SYMBOLS else False,
                    "pool_type": p.get("pool_type"),
                    "owner_program": p.get("owner_program"),
                }
                
                # Store pool with its liquidity for sorting
                pools_with_liquidity.append((pool_info, liquidity_usd))
                
                if qsym in _WSOL_SYMBOLS:
                    ws_pairs.append(p)
                elif qsym in _USDC_SYMBOLS:
                    usdc_pairs.append(p)
        except Exception:
            continue
    
    # Sort pools by liquidity (highest first) for better arbitrage opportunities
    pools_with_liquidity.sort(key=lambda x: x[1], reverse=True)
    pools = [pool_info for pool_info, _ in pools_with_liquidity]

    image_url = None
    for p in filtered_pairs:
        info = p.get("info") or {}
        candidate = info.get("imageUrl")
        if isinstance(candidate, str) and candidate.strip():
            image_url = candidate.strip()
            break

    l_tot = 0.0
    primary = None
    primary_lq = -1.0
    for p in (ws_pairs + usdc_pairs):
        liq_usd = _to_float((p.get("liquidity") or {}).get("usd"))
        if liq_usd:
            l_tot += liq_usd
            if liq_usd > primary_lq:
                primary_lq = liq_usd
                primary = p

    # 3. ΔP берём из наиболее ликвидной WSOL-пары с фильтрацией аномалий
    dp5 = 0.0
    dp15 = 0.0
    if primary is not None:
        pc = primary.get("priceChange") or {}
        raw5 = _to_float(pc.get("m5"))
        raw15 = _to_float(pc.get("m15"))
        # Преобразуем проценты в доли (если данные в процентах)
        if raw5 is not None:
            dp5 = raw5 / 100.0
        if raw15 is not None:
            dp15 = raw15 / 100.0
        else:
            # Fallback: DexScreener часто не возвращает m15 на Solana; используем h1/4 как приблизительную оценку
            h1 = _to_float(pc.get("h1"))
            if h1 is not None:
                dp15 = (h1 / 4.0) / 100.0

        # 4. Детекция и очистка аномальных изменений цены
        if detect_price_anomalies(dp5, dp15, max_price_change):
            log.warning(f"Price anomaly detected for {mint}: dp5={dp5:.1%}, dp15={dp15:.1%}")
            dp5, dp15 = sanitize_price_changes(dp5, dp15, max_price_change)

    # N_5m — сумма buys + sells по всем выбранным парам за m5
    n5m = 0
    for p in (ws_pairs + usdc_pairs):
        tx = (p.get("txns") or {}).get("m5") or {}
        buys = _to_float(tx.get("buys")) or 0.0
        sells = _to_float(tx.get("sells")) or 0.0
        n5m += int(buys + sells)

    # 5. Формируем итоговые метрики
    metrics = {
        "L_tot": round(l_tot, 6),
        "delta_p_5m": round(dp5, 6),
        "delta_p_15m": round(dp15, 6),
        "n_5m": int(n5m),
        "ws_pairs": len(ws_pairs),
        "usdc_pairs": len(usdc_pairs),
        "primary_dex": (primary or {}).get("dexId") if primary else None,
        "primary_liq_usd": round(primary_lq, 6) if primary_lq >= 0 else None,
        "image_url": image_url,
        "source": "dexscreener_with_fallback" if fallback_used else "dexscreener",
        "pools": pools,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        # Информация о фильтрации
        "total_pairs_received": len(pairs),
        "filtered_pairs_used": len(filtered_pairs),
        "pools_filtered_out": len(pairs) - len(filtered_pairs),
        "fallback_used": fallback_used,
    }
    
    # 6. Валидация консистентности финальных метрик с градацией серьезности
    is_valid, issues = validate_metrics_consistency(metrics, strict_mode=False)
    
    if not is_valid:
        log.warning(f"Metrics consistency check failed for {mint}: {'; '.join(issues)}")
        metrics["data_quality_warning"] = True
        metrics["data_quality_issues"] = issues
    elif issues:  # Есть предупреждения, но не критичные
        log.info(f"Metrics quality warnings for {mint}: {'; '.join(issues)}")
        metrics["data_quality_issues"] = issues
    
    return metrics
