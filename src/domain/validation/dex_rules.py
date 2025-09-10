from __future__ import annotations

from typing import Any

_WSOL_SYMBOLS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
_PUMPFUN_DEX_IDS = {"pumpfun-amm", "pumpfun", "pumpswap"}


def check_activation_conditions(mint: str, pairs: list[dict[str, Any]]) -> bool:
    """
    Условия активации из ТЗ:
    - Должна быть хотя бы одна пара: baseToken.address == mint, quoteToken.symbol == 'WSOL', dexId == 'pumpfun-amm'
    - Должна быть хотя бы одна пара с dexId != 'pumpfun-amm' (внешний пул)
    """
    has_pumpfun_wsol = False
    has_external_pool = False

    for p in pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            if (
                str(base.get("address")) == mint
                and str(quote.get("symbol", "")).upper() in _WSOL_SYMBOLS
                and dex_id in _PUMPFUN_DEX_IDS
            ):
                has_pumpfun_wsol = True
            # внешний пул по тому же mint на любом DEX, кроме pumpfun-семейства
            if str(base.get("address")) == mint and dex_id and dex_id not in _PUMPFUN_DEX_IDS:
                has_external_pool = True
        except Exception:
            # Пропускаем плохо сформированные пары
            continue

    return has_pumpfun_wsol and has_external_pool
