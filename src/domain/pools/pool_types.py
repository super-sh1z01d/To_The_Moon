"""
Pool Type Classification

This module provides classification of pool types based on DEX ID.
Different DEXs use different pool models (AMM, CLMM, DLMM).
"""
from __future__ import annotations

from typing import Dict, Optional
from enum import Enum


class PoolType(Enum):
    """Pool type classification."""
    AMM = "amm"           # Automated Market Maker (constant product)
    CLMM = "clmm"         # Concentrated Liquidity Market Maker
    DLMM = "dlmm"         # Dynamic Liquidity Market Maker
    HYBRID = "hybrid"     # Hybrid model
    UNKNOWN = "unknown"   # Unknown or unclassified


# Mapping of DEX IDs to pool types based on their underlying technology
DEX_POOL_TYPE_MAPPING: Dict[str, PoolType] = {
    # Raydium - Multiple pool types
    "raydium": PoolType.AMM,           # Classic AMM pools
    "raydium-clmm": PoolType.CLMM,     # Concentrated liquidity pools
    
    # Orca - Multiple pool types  
    "orca": PoolType.AMM,              # Classic AMM pools
    "orca-whirlpools": PoolType.CLMM,  # Whirlpools (concentrated liquidity)
    
    # Meteora - Dynamic liquidity
    "meteora": PoolType.DLMM,          # Dynamic Liquidity Market Maker
    "meteora-dlmm": PoolType.DLMM,     # Explicit DLMM pools
    
    # Jupiter - Aggregator (various underlying pools)
    "jupiter": PoolType.HYBRID,        # Aggregates multiple pool types
    
    # Pump.fun ecosystem
    "pumpfun-amm": PoolType.AMM,       # Pump.fun AMM pools
    "pumpswap": PoolType.AMM,          # Pump.fun swap pools
    "pumpfun": PoolType.AMM,           # Classic pump.fun (excluded usually)
    
    # Other DEXs
    "serum": PoolType.AMM,             # Serum DEX
    "aldrin": PoolType.AMM,            # Aldrin AMM
    "cropper": PoolType.AMM,           # Cropper Finance
    "saber": PoolType.AMM,             # Saber (stablecoin AMM)
    "mercurial": PoolType.AMM,         # Mercurial Finance
    "lifinity": PoolType.AMM,          # Lifinity
    "phoenix": PoolType.CLMM,          # Phoenix (order book + CLMM)
    "openbook": PoolType.AMM,          # OpenBook DEX
    "fluxbeam": PoolType.AMM,          # FluxBeam
    "invariant": PoolType.CLMM,        # Invariant Protocol
    "stepn": PoolType.AMM,             # STEPN DEX
    "dradex": PoolType.AMM,            # DradEx
    "balansol": PoolType.AMM,          # Balansol
    "crema": PoolType.CLMM,            # Crema Finance
    "sencha": PoolType.AMM,            # Sencha Exchange
    "saros": PoolType.AMM,             # Saros Finance
    "symmetry": PoolType.AMM,          # Symmetry
    "goosefx": PoolType.AMM,           # GooseFX
    "dexlab": PoolType.AMM,            # DexLab
    "penguin": PoolType.AMM,           # Penguin Finance
    "quarry": PoolType.AMM,            # Quarry Protocol
    "launchlab": PoolType.AMM,         # LaunchLab (usually excluded)
}


def get_pool_type(dex_id: str) -> PoolType:
    """
    Get pool type for a given DEX ID.
    
    Args:
        dex_id: DEX identifier from DexScreener
        
    Returns:
        PoolType enum value
    """
    if not dex_id:
        return PoolType.UNKNOWN
    
    return DEX_POOL_TYPE_MAPPING.get(dex_id.lower(), PoolType.UNKNOWN)


def get_pool_type_description(pool_type: PoolType) -> str:
    """
    Get human-readable description of pool type.
    
    Args:
        pool_type: PoolType enum value
        
    Returns:
        Description string
    """
    descriptions = {
        PoolType.AMM: "Automated Market Maker (constant product formula)",
        PoolType.CLMM: "Concentrated Liquidity Market Maker (Uniswap V3 style)",
        PoolType.DLMM: "Dynamic Liquidity Market Maker (adaptive fees/ranges)",
        PoolType.HYBRID: "Hybrid model (aggregates multiple pool types)",
        PoolType.UNKNOWN: "Unknown or unclassified pool type",
    }
    return descriptions.get(pool_type, "Unknown pool type")


def classify_pools_by_type(pools: list[dict]) -> Dict[PoolType, list[dict]]:
    """
    Classify a list of pools by their type.
    
    Args:
        pools: List of pool dictionaries with 'dex' field
        
    Returns:
        Dictionary mapping pool types to lists of pools
    """
    classified = {pool_type: [] for pool_type in PoolType}
    
    for pool in pools:
        dex_id = pool.get("dex", "")
        pool_type = get_pool_type(dex_id)
        classified[pool_type].append(pool)
    
    return classified


def get_pool_type_stats(pools: list[dict]) -> Dict[str, int]:
    """
    Get statistics of pool types in a list of pools.
    
    Args:
        pools: List of pool dictionaries with 'dex' field
        
    Returns:
        Dictionary with pool type counts
    """
    classified = classify_pools_by_type(pools)
    return {
        pool_type.value: len(pool_list) 
        for pool_type, pool_list in classified.items() 
        if pool_list  # Only include non-empty categories
    }


def is_concentrated_liquidity(dex_id: str) -> bool:
    """
    Check if a DEX uses concentrated liquidity model.
    
    Args:
        dex_id: DEX identifier
        
    Returns:
        True if DEX uses concentrated liquidity (CLMM)
    """
    pool_type = get_pool_type(dex_id)
    return pool_type == PoolType.CLMM


def is_dynamic_liquidity(dex_id: str) -> bool:
    """
    Check if a DEX uses dynamic liquidity model.
    
    Args:
        dex_id: DEX identifier
        
    Returns:
        True if DEX uses dynamic liquidity (DLMM)
    """
    pool_type = get_pool_type(dex_id)
    return pool_type == PoolType.DLMM


def get_advanced_pool_features(dex_id: str) -> Dict[str, bool]:
    """
    Get advanced features available for a pool type.
    
    Args:
        dex_id: DEX identifier
        
    Returns:
        Dictionary of feature flags
    """
    pool_type = get_pool_type(dex_id)
    
    features = {
        "concentrated_liquidity": pool_type == PoolType.CLMM,
        "dynamic_fees": pool_type in [PoolType.DLMM, PoolType.CLMM],
        "custom_ranges": pool_type in [PoolType.CLMM, PoolType.DLMM],
        "auto_rebalancing": pool_type == PoolType.DLMM,
        "multiple_fee_tiers": pool_type == PoolType.CLMM,
        "impermanent_loss_protection": pool_type == PoolType.DLMM,
    }
    
    return features