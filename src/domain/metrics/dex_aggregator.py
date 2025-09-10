from __future__ import annotations

from typing import Any, Optional

_WSOL_SYMBOLS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
# Exclude only classic pumpfun; include pumpfun-amm and pumpswap
_EXCLUDE_DEX_IDS = {"pumpfun"}


def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def aggregate_wsol_metrics(mint: str, pairs: list[dict[str, Any]]) -> dict[str, Any]:
    """Собирает агрегаты по WSOL/токен парам для данного mint.

    Возвращает словарь с ключами:
      - L_tot: float
      - delta_p_5m: float (как доля, например 0.052 для +5.2%)
      - delta_p_15m: float (доля)
      - n_5m: int
      - ws_pairs: int
      - primary_dex: str | None
      - primary_liq_usd: float | None
    """
    # Фильтруем только пары WSOL/токен, где baseToken.address == mint
    ws_pairs: list[dict[str, Any]] = []
    pools: list[dict[str, Any]] = []
    for p in pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            # Используем WSOL/SOL пары данного mint за исключением pumpfun (classic)
            # (включая pumpfun-amm, pumpswap и внешние DEX)
            if (
                str(base.get("address")) == mint
                and str(quote.get("symbol", "")).upper() in _WSOL_SYMBOLS
                and dex_id not in _EXCLUDE_DEX_IDS
            ):
                addr = p.get("pairAddress") or p.get("address")
                pools.append(
                    {
                        "address": addr,
                        "dex": dex_id,
                        "quote": (quote or {}).get("symbol"),
                        "is_wsol": True,
                    }
                )
                ws_pairs.append(p)
        except Exception:
            continue

    l_tot = 0.0
    primary = None
    primary_lq = -1.0
    for p in ws_pairs:
        liq_usd = _to_float((p.get("liquidity") or {}).get("usd"))
        if liq_usd:
            l_tot += liq_usd
            if liq_usd > primary_lq:
                primary_lq = liq_usd
                primary = p

    # ΔP берём из наиболее ликвидной WSOL-пары
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

    # N_5m — сумма buys + sells по всем WSOL-парам за m5
    n5m = 0
    for p in ws_pairs:
        tx = (p.get("txns") or {}).get("m5") or {}
        buys = _to_float(tx.get("buys")) or 0.0
        sells = _to_float(tx.get("sells")) or 0.0
        n5m += int(buys + sells)

    return {
        "L_tot": round(l_tot, 6),
        "delta_p_5m": round(dp5, 6),
        "delta_p_15m": round(dp15, 6),
        "n_5m": int(n5m),
        "ws_pairs": len(ws_pairs),
        "primary_dex": (primary or {}).get("dexId") if primary else None,
        "primary_liq_usd": round(primary_lq, 6) if primary_lq >= 0 else None,
        "source": "dexscreener",
        "pools": pools,
    }
