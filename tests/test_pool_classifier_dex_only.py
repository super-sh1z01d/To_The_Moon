from __future__ import annotations

from src.domain.pools.classifier_dex_only import (
    classify_pool_type,
    classify_pairs_dex_only,
    determine_primary_pool_type,
)


def test_classify_pool_type_with_dex_and_labels():
    assert classify_pool_type("raydium", ["clmm"])[0] == "raydium_clmm"
    assert classify_pool_type("orca", ["whirlpool"])[0] == "orca_whirlpool"
    assert classify_pool_type("meteora", ["dlmm"])[0] == "meteora_dlmm"
    assert classify_pool_type("pumpfun", [])[0] == "pumpfun_amm"


def test_classify_pairs_and_primary_pool_type():
    pairs = [
        {"dexId": "raydium", "labels": ["cpmm"]},
        {"dexId": "raydium", "labels": ["cpmm"]},
        {"dexId": "orca", "labels": ["whirlpool"]},
    ]
    enriched = classify_pairs_dex_only(pairs)

    assert all(p["classification_source"] == "dexscreener" for p in enriched)
    assert all("pool_type_canonical" in p for p in enriched)

    primary = determine_primary_pool_type(enriched)
    assert primary == "raydium_cpmm"
