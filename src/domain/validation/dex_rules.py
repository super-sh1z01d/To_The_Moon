from __future__ import annotations

from typing import Any


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
            dex_id = p.get("dexId")
            if (
                str(base.get("address")) == mint
                and str(quote.get("symbol")).upper() == "WSOL"
                and dex_id == "pumpfun-amm"
            ):
                has_pumpfun_wsol = True
            if dex_id and dex_id != "pumpfun-amm":
                has_external_pool = True
        except Exception:
            # Пропускаем плохо сформированные пары
            continue

    return has_pumpfun_wsol and has_external_pool

