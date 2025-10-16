from __future__ import annotations

from typing import Any

_WSOL_SYMBOLS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
_PUMPFUN_DEX_IDS = {"pumpfun-amm", "pumpfun", "pumpswap"}


def has_external_pools(mint: str, pairs: list[dict[str, Any]]) -> bool:
    """
    Check if token has any external pools (non-pumpfun DEXs).
    Used to determine if we need to fetch fallback data.
    """
    excluded_dexes = {"pumpfun", "launchlab"}
    usdc_symbols = {"USDC", "usdc", "USD1", "usd1"}
    
    for p in pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            
            # Check if this is our token's pool
            if str(base.get("address")) != mint:
                continue
                
            # Check for external pools (non-pumpfun)
            if (dex_id and 
                dex_id not in _PUMPFUN_DEX_IDS and 
                dex_id not in excluded_dexes):
                
                # Check if it's a relevant quote token (WSOL/SOL or USDC)
                quote_symbol = str(quote.get("symbol", "")).upper()
                if quote_symbol in _WSOL_SYMBOLS or quote_symbol in usdc_symbols:
                    return True
                    
        except Exception:
            continue
            
    return False


def check_transaction_volume(pairs: list[dict[str, Any]], min_txns_5m: int = 300) -> bool:
    """
    Check if token has sufficient transaction volume (>300 txns in last 5 minutes).
    Uses txns.m5 from DexScreener pairs data.
    """
    for p in pairs:
        try:
            txns = p.get("txns", {})
            if not txns:
                continue

            # Get 5-minute transaction count
            m5_data = txns.get("m5", {})
            if not m5_data:
                continue

            # Sum buys + sells for total transaction count
            buys = m5_data.get("buys", 0)
            sells = m5_data.get("sells", 0)
            total_txns = buys + sells

            if total_txns >= min_txns_5m:
                return True

        except Exception:
            continue

    return False


def check_activation_conditions(mint: str, pairs: list[dict[str, Any]], min_liquidity_usd: float = 500.0) -> bool:
    """
    Условия активации (ИЛИ):
    Условие 1: Пул на Pump.fun + хотя бы один внешний пул с достаточной ликвидностью
    ИЛИ
    Условие 2: Два или более внешних пулов с достаточной ликвидностью (без требования Pump.fun)
    """
    import logging
    logger = logging.getLogger("activation")
    
    has_pumpfun_wsol = False
    external_pools_with_liquidity = 0
    external_pools_found = 0
    
    # Исключаем bonding curve платформы
    excluded_dexes = {"pumpfun", "launchlab"}
    usdc_symbols = {"USDC", "usdc", "USD1", "usd1"}

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
                
                external_pools_found += 1
                
                # Проверяем ликвидность только для WSOL/SOL и USDC пулов
                quote_symbol = str(quote.get("symbol", "")).upper()
                if quote_symbol in _WSOL_SYMBOLS or quote_symbol in usdc_symbols:
                    liquidity_usd = (p.get("liquidity") or {}).get("usd", 0)
                    try:
                        liquidity_value = float(liquidity_usd)
                        if liquidity_value >= min_liquidity_usd:
                            external_pools_with_liquidity += 1
                            logger.debug(
                                "external_pool_with_liquidity",
                                extra={
                                    "mint": mint,
                                    "dex": dex_id,
                                    "quote": quote_symbol,
                                    "liquidity": liquidity_value,
                                    "threshold": min_liquidity_usd
                                }
                            )
                    except (ValueError, TypeError):
                        continue
                
        except Exception:
            # Пропускаем плохо сформированные пары
            continue

    # Условие 1: Pump.fun + хотя бы один внешний пул с ликвидностью
    condition_1 = has_pumpfun_wsol and external_pools_with_liquidity >= 1
    
    # Условие 2: Два или более внешних пулов с ликвидностью
    condition_2 = external_pools_with_liquidity >= 2
    
    result = condition_1 or condition_2
    
    logger.info(
        f"activation_conditions_check: mint={mint[:8]}... pairs={len(pairs)} pumpfun={has_pumpfun_wsol} ext_found={external_pools_found} ext_liq={external_pools_with_liquidity} threshold={min_liquidity_usd} c1={condition_1} c2={condition_2} result={result}"
    )
    
    return result


def check_archived_token_activation(
    mint: str,
    pairs: list[dict[str, Any]],
    min_liquidity_usd: float = 50.0,
    min_txns_5m: int = 300
) -> bool:
    """
    Условия реактивации для архивных токенов.
    Все условия должны выполняться одновременно (И):

    1) Пулы (ИЛИ):
       - Pump.fun/pumpswap + хотя бы один внешний пул с ликвидностью >= 50 USD
       ИЛИ
       - Два или более внешних пулов с ликвидностью >= 50 USD

    2) Минимальная ликвидность внешнего пула: >= 50 USD

    3) Объем транзакций: >= 300 транзакций за последние 5 минут
    """
    import logging
    logger = logging.getLogger("archived_activation")

    has_pumpfun_wsol = False
    external_pools_with_liquidity = 0
    external_pools_found = 0

    excluded_dexes = {"pumpfun", "launchlab"}
    usdc_symbols = {"USDC", "usdc", "USD1", "usd1"}

    for p in pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")

            if str(base.get("address")) != mint:
                continue

            # Проверяем Pump.fun пул
            if (str(quote.get("symbol", "")).upper() in _WSOL_SYMBOLS and
                dex_id in _PUMPFUN_DEX_IDS):
                has_pumpfun_wsol = True

            # Считаем внешние пулы с достаточной ликвидностью
            if (dex_id and
                dex_id not in _PUMPFUN_DEX_IDS and
                dex_id not in excluded_dexes):

                external_pools_found += 1

                quote_symbol = str(quote.get("symbol", "")).upper()
                if quote_symbol in _WSOL_SYMBOLS or quote_symbol in usdc_symbols:
                    liquidity_usd = (p.get("liquidity") or {}).get("usd", 0)
                    try:
                        liquidity_value = float(liquidity_usd)
                        if liquidity_value >= min_liquidity_usd:
                            external_pools_with_liquidity += 1
                    except (ValueError, TypeError):
                        continue

        except Exception:
            continue

    # Проверяем объем транзакций
    has_sufficient_volume = check_transaction_volume(pairs, min_txns_5m)

    # Условие 1: (Pump.fun + внешний пул) ИЛИ (2+ внешних пулов)
    pools_condition = (has_pumpfun_wsol and external_pools_with_liquidity >= 1) or (external_pools_with_liquidity >= 2)

    # Условие 2: >= 300 транзакций за 5 минут
    volume_condition = has_sufficient_volume

    # Результат: оба условия должны выполняться
    result = pools_condition and volume_condition

    logger.info(
        f"archived_activation_check: mint={mint[:8]}... "
        f"pumpfun={has_pumpfun_wsol} "
        f"ext_pools_liq={external_pools_with_liquidity} "
        f"ext_pools_total={external_pools_found} "
        f"volume_ok={has_sufficient_volume} "
        f"pools_ok={pools_condition} "
        f"result={result}"
    )

    return result
