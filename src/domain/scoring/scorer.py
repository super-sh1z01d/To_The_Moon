from __future__ import annotations

import logging
import math
from typing import Any, Tuple


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _get_float(metrics: dict, key: str, default: float = 0.0) -> float:
    v = metrics.get(key)
    try:
        return float(v)
    except Exception:
        return default


def compute_components(metrics: dict) -> dict:
    """Вычислить нормированные компоненты l,s,m,t по ТЗ.

    Ожидаемые поля metrics:
      - L_tot
      - delta_p_5m (доля)
      - delta_p_15m (доля)
      - n_5m (int)
    Возвращает словарь со всеми промежуточными значениями для логов.
    """
    L_tot = max(_get_float(metrics, "L_tot", 0.0), 0.0)
    dp5 = abs(_get_float(metrics, "delta_p_5m", 0.0))
    dp15 = abs(_get_float(metrics, "delta_p_15m", 0.0))
    n5 = max(_get_float(metrics, "n_5m", 0.0), 0.0)

    # LIQ = log10(L_tot) ; l = clip((LIQ - 4)/2)
    LIQ = math.log10(L_tot) if L_tot > 0 else 0.0
    l = _clip01((LIQ - 4.0) / 2.0)

    # SV = abs(ΔP_5m); s = clip(SV / 0.1)
    SV = dp5
    s = _clip01(SV / 0.1)

    # MV = abs(ΔP_5m)/(abs(ΔP_15m)+0.001); m = clip(MV)
    MV = dp5 / (dp15 + 0.001)
    m = _clip01(MV)

    # TF = N_5m / 5; t = clip(TF/300)
    TF = n5 / 5.0
    t = _clip01(TF / 300.0)

    return {
        "L_tot": L_tot,
        "LIQ": LIQ,
        "l": l,
        "SV": SV,
        "s": s,
        "MV": MV,
        "m": m,
        "TF": TF,
        "t": t,
        "HD_norm": 1.0,  # временно
    }


def compute_score(metrics: dict, weights: dict[str, float]) -> Tuple[float, dict]:
    comps = compute_components(metrics)
    Ws = float(weights.get("weight_s", 0.35))
    Wl = float(weights.get("weight_l", 0.25))
    Wm = float(weights.get("weight_m", 0.20))
    Wt = float(weights.get("weight_t", 0.20))

    score = comps["HD_norm"] * (Ws * comps["s"] + Wl * comps["l"] + Wm * comps["m"] + Wt * comps["t"])
    return float(round(score, 6)), comps

