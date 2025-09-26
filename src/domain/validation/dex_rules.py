from __future__ import annotations

from typing import Any

_WSOL_SYMBOLS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
_PUMPFUN_DEX_IDS = {"pumpfun-amm", "pumpfun", "pumpswap"}


def check_activation_conditions(mint: str, pairs: list[dict[str, Any]], min_liquidity_usd: float = 500.0) -> bool:
    """
    Условия активации (ИЛИ):
    Условие 1: Пул на Pump.fun + хотя бы один внешний пул с достаточной ликвидностью
    ИЛИ
    Условие 2: Два или более внешних пулов с достаточной ликвидностью (без требования Pump.fun)
    """
    has_pumpfun_wsol = False
    external_pools_with_liquidity = 0
    
    # Исключаем bonding curve платформы
    excluded_dexes = {"pumpfun", "launchlab"}
    usdc_symbols = {"USDC", "usdc"}

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
                
            # Считаем внешние пулы с достаточной ликвидностью
            if (dex_id and 
                dex_id not in _PUMPFUN_DEX_IDS and 
                dex_id not in excluded_dexes):
                
                # Проверяем ликвидность только для WSOL/SOL и USDC пулов
                quote_symbol = str(quote.get("symbol", "")).upper()
                if quote_symbol in _WSOL_SYMBOLS or quote_symbol in usdc_symbols:
                    liquidity_usd = (p.get("liquidity") or {}).get("usd", 0)
                    try:
                        if float(liquidity_usd) >= min_liquidity_usd:
                            external_pools_with_liquidity += 1
                    except (ValueError, TypeError):
                        continue
                
        except Exception:
            # Пропускаем плохо сформированные пары
            continue

    # Условие 1: Pump.fun + хотя бы один внешний пул с ликвидностью
    condition_1 = has_pumpfun_wsol and external_pools_with_liquidity >= 1
    
    # Условие 2: Два или более внешних пулов с ликвидностью
    condition_2 = external_pools_with_liquidity >= 2
    
    return condition_1 or condition_2
