"""
Enhanced DEX Aggregator for Hybrid Momentum Scoring

This module extends the existing dex_aggregator functionality to collect
additional metrics required for the hybrid momentum scoring model.
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from datetime import datetime, timezone

from .dex_aggregator import (
    aggregate_wsol_metrics,
    _to_float,
    _WSOL_SYMBOLS,
    _USDC_SYMBOLS,
    _EXCLUDE_DEX_IDS
)
from ..validation.data_filters import (
    filter_low_liquidity_pools,
    detect_price_anomalies,
    sanitize_price_changes,
    validate_metrics_consistency,
)


def aggregate_enhanced_metrics(
    mint: str, 
    pairs: list[dict[str, Any]], 
    created_at: datetime,
    min_liquidity_usd: float = 500
) -> dict[str, Any]:
    """
    Collect enhanced metrics for hybrid momentum scoring model.
    
    This function extends the existing aggregate_wsol_metrics to include
    additional data required for the new scoring components.
    
    Args:
        mint: Token contract address
        pairs: List of pairs from DexScreener API
        created_at: Token creation timestamp for freshness calculation
        min_liquidity_usd: Minimum pool liquidity for inclusion
        
    Returns:
        Dictionary with enhanced metrics including:
        - All existing metrics from aggregate_wsol_metrics (with default price limits)
        - tx_count_5m, tx_count_1h: Transaction counts
        - volume_5m, volume_1h: Trading volumes
        - buys_volume_5m, sells_volume_5m: Estimated buy/sell volumes
        - hours_since_creation: Time since token creation
    """
    log = logging.getLogger("enhanced_dex_aggregator")
    
    # Start with existing metrics (using default price change limit for legacy compatibility)
    base_metrics = aggregate_wsol_metrics(mint, pairs, min_liquidity_usd, 0.5)
    
    # Filter pairs using same logic as base aggregator
    filtered_pairs = filter_low_liquidity_pools(pairs, min_liquidity_usd)
    
    # Extract relevant pairs (WSOL/SOL and USDC pairs)
    relevant_pairs = []
    for p in filtered_pairs:
        try:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            dex_id = str(p.get("dexId") or "")
            qsym = str(quote.get("symbol", "")).upper()
            
            if (str(base.get("address")) == mint and 
                dex_id not in _EXCLUDE_DEX_IDS and 
                (qsym in _WSOL_SYMBOLS or qsym in _USDC_SYMBOLS)):
                relevant_pairs.append(p)
        except Exception:
            continue
    
    # Calculate enhanced metrics
    enhanced_metrics = _calculate_enhanced_metrics(relevant_pairs, created_at, log)
    
    # Merge with base metrics
    base_metrics.update(enhanced_metrics)
    
    # Add enhanced metadata
    base_metrics.update({
        "enhanced_metrics_version": "1.0",
        "relevant_pairs_count": len(relevant_pairs),
    })
    
    log.debug(
        "enhanced_metrics_calculated",
        extra={
            "mint": mint,
            "relevant_pairs": len(relevant_pairs),
            "tx_count_5m": enhanced_metrics.get("tx_count_5m"),
            "tx_count_1h": enhanced_metrics.get("tx_count_1h"),
            "volume_5m": enhanced_metrics.get("volume_5m"),
            "volume_1h": enhanced_metrics.get("volume_1h"),
            "hours_since_creation": enhanced_metrics.get("hours_since_creation"),
        }
    )
    
    return base_metrics


def _calculate_enhanced_metrics(
    pairs: list[dict[str, Any]], 
    created_at: datetime,
    log: logging.Logger
) -> dict[str, Any]:
    """
    Calculate enhanced metrics from filtered pairs.
    
    Args:
        pairs: List of relevant trading pairs
        created_at: Token creation timestamp
        log: Logger instance
        
    Returns:
        Dictionary with enhanced metrics
    """
    # Initialize metrics
    tx_count_5m = 0
    tx_count_1h = 0
    volume_5m = 0.0
    volume_1h = 0.0
    buys_5m = 0
    sells_5m = 0
    
    # Aggregate transaction and volume data
    for pair in pairs:
        try:
            # Extract transaction data
            txns = pair.get("txns", {})
            
            # 5-minute transactions
            m5_txns = txns.get("m5", {})
            buys_m5 = _to_float(m5_txns.get("buys")) or 0.0
            sells_m5 = _to_float(m5_txns.get("sells")) or 0.0
            tx_count_5m += int(buys_m5 + sells_m5)
            buys_5m += int(buys_m5)
            sells_5m += int(sells_m5)
            
            # 1-hour transactions
            h1_txns = txns.get("h1", {})
            buys_h1 = _to_float(h1_txns.get("buys")) or 0.0
            sells_h1 = _to_float(h1_txns.get("sells")) or 0.0
            tx_count_1h += int(buys_h1 + sells_h1)
            
            # Extract volume data
            volume = pair.get("volume", {})
            pair_volume_5m = _to_float(volume.get("m5")) or 0.0
            pair_volume_1h = _to_float(volume.get("h1")) or 0.0
            
            volume_5m += pair_volume_5m
            volume_1h += pair_volume_1h
            
        except Exception as e:
            log.warning(
                "pair_processing_error",
                extra={
                    "pair_address": pair.get("pairAddress"),
                    "error": str(e)
                }
            )
            continue
    
    # Calculate estimated buy/sell volumes using transaction ratios
    buys_volume_5m, sells_volume_5m = _estimate_buy_sell_volumes(
        volume_5m, buys_5m, sells_5m, log
    )
    
    # Calculate hours since creation
    hours_since_creation = _calculate_hours_since_creation(created_at, log)
    
    return {
        "tx_count_5m": tx_count_5m,
        "tx_count_1h": tx_count_1h,
        "volume_5m": round(volume_5m, 6),
        "volume_1h": round(volume_1h, 6),
        "buys_volume_5m": round(buys_volume_5m, 6),
        "sells_volume_5m": round(sells_volume_5m, 6),
        "hours_since_creation": round(hours_since_creation, 6),
        "total_buys_5m": buys_5m,
        "total_sells_5m": sells_5m,
    }


def _estimate_buy_sell_volumes(
    total_volume_5m: float, 
    buys_count: int, 
    sells_count: int,
    log: logging.Logger
) -> tuple[float, float]:
    """
    Estimate buy and sell volumes using transaction count ratios.
    
    Since DexScreener doesn't provide separate buy/sell volumes,
    we estimate them based on the ratio of buy/sell transaction counts.
    
    Args:
        total_volume_5m: Total trading volume in 5 minutes
        buys_count: Number of buy transactions
        sells_count: Number of sell transactions
        log: Logger instance
        
    Returns:
        Tuple of (estimated_buys_volume, estimated_sells_volume)
    """
    try:
        total_txns = buys_count + sells_count
        
        if total_txns == 0 or total_volume_5m <= 0:
            return 0.0, 0.0
        
        # Calculate ratios
        buys_ratio = buys_count / total_txns
        sells_ratio = sells_count / total_txns
        
        # Estimate volumes
        buys_volume = total_volume_5m * buys_ratio
        sells_volume = total_volume_5m * sells_ratio
        
        log.debug(
            "volume_estimation",
            extra={
                "total_volume_5m": total_volume_5m,
                "buys_count": buys_count,
                "sells_count": sells_count,
                "buys_ratio": buys_ratio,
                "estimated_buys_volume": buys_volume,
                "estimated_sells_volume": sells_volume,
            }
        )
        
        return buys_volume, sells_volume
        
    except Exception as e:
        log.warning(
            "volume_estimation_error",
            extra={
                "total_volume_5m": total_volume_5m,
                "buys_count": buys_count,
                "sells_count": sells_count,
                "error": str(e)
            }
        )
        return 0.0, 0.0


def _calculate_hours_since_creation(created_at: datetime, log: logging.Logger) -> float:
    """
    Calculate hours since token creation.
    
    Args:
        created_at: Token creation timestamp
        log: Logger instance
        
    Returns:
        Hours since creation as float
    """
    try:
        now = datetime.now(tz=timezone.utc)
        
        # Ensure created_at is timezone-aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        time_diff = now - created_at
        hours_since_creation = time_diff.total_seconds() / 3600.0
        
        # Ensure non-negative value
        hours_since_creation = max(0.0, hours_since_creation)
        
        log.debug(
            "hours_since_creation_calculated",
            extra={
                "created_at": created_at.isoformat(),
                "now": now.isoformat(),
                "hours_since_creation": hours_since_creation,
            }
        )
        
        return hours_since_creation
        
    except Exception as e:
        log.warning(
            "hours_since_creation_error",
            extra={
                "created_at": str(created_at),
                "error": str(e)
            }
        )
        # Return a reasonable default (24 hours) if calculation fails
        return 24.0


def validate_enhanced_metrics(metrics: dict[str, Any]) -> bool:
    """
    Validate enhanced metrics for consistency and reasonableness.
    
    Args:
        metrics: Dictionary of enhanced metrics
        
    Returns:
        True if metrics pass validation, False otherwise
    """
    try:
        # Check required fields exist
        required_fields = [
            "tx_count_5m", "tx_count_1h", "volume_5m", "volume_1h",
            "buys_volume_5m", "sells_volume_5m", "hours_since_creation"
        ]
        
        for field in required_fields:
            if field not in metrics:
                return False
        
        # Validate logical relationships
        tx_5m = metrics.get("tx_count_5m", 0)
        tx_1h = metrics.get("tx_count_1h", 0)
        vol_5m = metrics.get("volume_5m", 0)
        vol_1h = metrics.get("volume_1h", 0)
        buys_vol = metrics.get("buys_volume_5m", 0)
        sells_vol = metrics.get("sells_volume_5m", 0)
        hours = metrics.get("hours_since_creation", 0)
        
        # Basic sanity checks
        if tx_5m < 0 or tx_1h < 0 or vol_5m < 0 or vol_1h < 0:
            return False
            
        if buys_vol < 0 or sells_vol < 0 or hours < 0:
            return False
            
        # Volume consistency check
        total_estimated_volume = buys_vol + sells_vol
        if vol_5m > 0 and total_estimated_volume > 0:
            # Allow some tolerance for rounding errors
            ratio = abs(total_estimated_volume - vol_5m) / vol_5m
            if ratio > 0.01:  # 1% tolerance
                return False
        
        return True
        
    except Exception:
        return False
