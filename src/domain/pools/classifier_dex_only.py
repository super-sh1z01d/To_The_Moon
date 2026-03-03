from __future__ import annotations

from collections import Counter
from typing import Any, Optional


def _norm_label(label: str) -> str:
    return label.strip().lower().replace("-", "_")


def classify_pool_type(dex_id: str, labels: list[str]) -> tuple[str, float]:
    dex = (dex_id or "").strip().lower()
    label_set = {_norm_label(x) for x in labels if isinstance(x, str)}

    if dex == "raydium":
        if "clmm" in label_set:
            return "raydium_clmm", 0.95
        if "cpmm" in label_set:
            return "raydium_cpmm", 0.95
        return "raydium_amm", 0.8

    if dex == "orca":
        if "wp" in label_set or "whirlpool" in label_set:
            return "orca_whirlpool", 0.95
        return "orca_pool", 0.75

    if dex in {"pumpfun", "pumpfun_amm", "pumpfun-amm", "pumpswap"}:
        return "pumpfun_amm", 0.95

    if dex == "meteora":
        if "dlmm" in label_set:
            return "meteora_dlmm", 0.95
        if "damm_v2" in label_set or "dammv2" in label_set:
            return "meteora_damm_v2", 0.95
        return "meteora_pool", 0.75

    if dex:
        return f"{dex}_pool", 0.65
    return "dex_unknown", 0.4


def classify_pairs_dex_only(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        copied = dict(pair)
        dex_id = str(copied.get("dexId") or "")
        labels = copied.get("labels") or []
        if not isinstance(labels, list):
            labels = []
        pool_type, confidence = classify_pool_type(dex_id, labels)
        copied["pool_type"] = pool_type
        copied["pool_type_canonical"] = pool_type
        copied["pool_confidence"] = confidence
        copied["classification_source"] = "dexscreener"
        result.append(copied)
    return result


def determine_primary_pool_type(pairs: list[dict[str, Any]]) -> Optional[str]:
    counts = Counter(
        str(p.get("pool_type_canonical") or p.get("pool_type"))
        for p in pairs
        if isinstance(p, dict) and (p.get("pool_type_canonical") or p.get("pool_type"))
    )
    if not counts:
        return None
    max_count = max(counts.values())
    candidates = sorted(k for k, v in counts.items() if v == max_count)
    return candidates[0] if candidates else None
