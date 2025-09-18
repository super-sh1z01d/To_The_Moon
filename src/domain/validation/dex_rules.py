from __future__ import annotations

from typing import Any

_WSOL_SYMBOLS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
_PUMPFUN_DEX_IDS = {"pumpfun-amm", "pumpfun", "pumpswap"}


def check_activation_conditions(mint: str, pairs: list[dict[str, Any]]) -> bool:
    """
    Условия активации (ИЛИ):
    Условие 1: Пул на Pump.fun + хотя бы один внешний пул
    ИЛИ
    Условие 2: Более двух внешних пулов (без требования Pump.fun)
    """
    has_pumpfun_wsol = False
    external_pools_count = 0
    
    # Исключаем bonding curve платформы
    excluded_dexes = {"pumpfun", "launchlab"}

    for p in pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            
            # Проверяем, что это пул нашего токена
            if str(base.get("address")) != mint:
                continue
                
            # Проверяем пул на Pump.fun
            if (str(quote.get("symbol", "")).upper() in _WSOL_SYMBOLS and 
                dex_id in _PUMPFUN_DEX_IDS):
                has_pumpfun_wsol = True
                
            # Считаем внешние пулы (не bonding curve платформы)
            if (dex_id and 
                dex_id not in _PUMPFUN_DEX_IDS and 
                dex_id not in excluded_dexes):
                external_pools_count += 1
                
        except Exception:
            # Пропускаем плохо сформированные пары
            continue

    # Условие 1: Pump.fun + хотя бы один внешний пул
    condition_1 = has_pumpfun_wsol and external_pools_count >= 1
    
    # Условие 2: Более двух внешних пулов
    condition_2 = external_pools_count > 2
    
    return condition_1 or condition_2
