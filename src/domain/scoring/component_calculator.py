"""
Component Calculator for Hybrid Momentum Scoring Model

This module implements the calculation of individual scoring components
according to the hybrid momentum model specification.
"""
from __future__ import annotations

import logging
import math
from typing import Optional, Dict, Any


class ComponentCalculator:
    """Calculator for hybrid momentum scoring components."""
    
    @staticmethod
    def calculate_tx_accel(tx_count_5m: float, tx_count_1h: float, filtering_settings: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate transaction acceleration component with improved stability.
        
        Enhanced Formula: log(1 + rate_5m) / log(1 + rate_1h) with minimum thresholds
        
        This measures if the trading pace is accelerating in the last 5 minutes
        compared to the average pace over the last hour, with logarithmic smoothing
        to prevent extreme values from small denominators.
        
        Args:
            tx_count_5m: Number of transactions in last 5 minutes
            tx_count_1h: Number of transactions in last 1 hour
            
        Returns:
            Transaction acceleration ratio (0.0 if invalid inputs)
        """
        try:
            # Basic data validation - only check for valid data, no artificial thresholds
            if tx_count_5m < 0 or tx_count_1h < 0:
                return 0.0
            
            # Apply filtering thresholds from settings
            if filtering_settings:
                min_tx_5m = filtering_settings.get("min_tx_threshold_5m", 1.0)
                min_tx_1h = filtering_settings.get("min_tx_threshold_1h", 1.0)
                
                if tx_count_5m < min_tx_5m or tx_count_1h < min_tx_1h:
                    return 0.0
            else:
                # Fallback: require some minimal activity (at least 1 transaction)
                if tx_count_5m == 0 or tx_count_1h == 0:
                    return 0.0
                
            # Calculate rates per minute
            rate_5m = tx_count_5m / 5.0
            rate_1h = tx_count_1h / 60.0
            
            # Use logarithmic smoothing to prevent extreme values
            # log(1 + x) grows slower than x, providing stability
            numerator = math.log(1 + rate_5m)
            denominator = math.log(1 + rate_1h)
            
            if denominator <= 0:
                return 0.0
                
            result = numerator / denominator
            
            # Sanity check for extreme values and cap at reasonable maximum
            if math.isnan(result) or math.isinf(result) or result < 0:
                return 0.0
                
            # Cap at 10x to prevent extreme scores
            return min(result, 10.0)
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "tx_accel_calculation_error", 
                extra={"tx_count_5m": tx_count_5m, "tx_count_1h": tx_count_1h}
            )
            return 0.0
    
    @staticmethod
    def calculate_tx_arbitrage_activity(tx_count_5m: float, tx_count_1h: float, filtering_settings: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate transaction activity component optimized for high-frequency arbitrage.
        
        Hybrid Formula: (absolute_activity * 0.7) + (acceleration * 0.3)
        
        This combines absolute transaction volume with acceleration to identify
        tokens suitable for high-frequency arbitrage bots. Designed for bots
        operating at 700ms intervals requiring 200+ transactions per 5 minutes.
        
        Args:
            tx_count_5m: Number of transactions in last 5 minutes
            tx_count_1h: Number of transactions in last 1 hour
            filtering_settings: Optional settings for thresholds
            
        Returns:
            Arbitrage activity score (0.0 to 1.0)
        """
        try:
            # Basic data validation
            if tx_count_5m < 0 or tx_count_1h < 0:
                return 0.0
            
            # Get thresholds from settings or use defaults optimized for arbitrage
            if filtering_settings:
                min_threshold = filtering_settings.get("arbitrage_min_tx_5m", 50)
                optimal_threshold = filtering_settings.get("arbitrage_optimal_tx_5m", 200)
                acceleration_weight = filtering_settings.get("arbitrage_acceleration_weight", 0.3)
            else:
                min_threshold = 50    # Minimum threshold to enter calculation
                optimal_threshold = 200  # Optimal threshold for arbitrage bots
                acceleration_weight = 0.3  # 30% weight for acceleration
            
            # 1. Absolute Activity Component (70% weight by default)
            if tx_count_5m < min_threshold:
                absolute_score = 0.0
            elif tx_count_5m >= optimal_threshold:
                absolute_score = 1.0
            else:
                # Linear scaling between thresholds
                absolute_score = (tx_count_5m - min_threshold) / (optimal_threshold - min_threshold)
            
            # 2. Acceleration Component (30% weight by default)
            if tx_count_5m == 0 or tx_count_1h == 0:
                acceleration_score = 0.0
            else:
                rate_5m = tx_count_5m / 5.0
                rate_1h = tx_count_1h / 60.0
                
                if rate_1h <= 0:
                    acceleration_score = 0.0
                else:
                    # Calculate acceleration ratio
                    accel_ratio = rate_5m / rate_1h
                    
                    if accel_ratio >= 2.0:
                        # 2x acceleration or more = maximum acceleration score
                        acceleration_score = 1.0
                    elif accel_ratio >= 1.0:
                        # Linear scaling from 1x to 2x acceleration
                        acceleration_score = (accel_ratio - 1.0) / 1.0
                    else:
                        # Deceleration = no acceleration bonus
                        acceleration_score = 0.0
            
            # 3. Combine components with weights
            absolute_weight = 1.0 - acceleration_weight
            final_score = (absolute_score * absolute_weight) + (acceleration_score * acceleration_weight)
            
            # Ensure result is within bounds
            return max(0.0, min(1.0, final_score))
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "tx_arbitrage_activity_calculation_error", 
                extra={"tx_count_5m": tx_count_5m, "tx_count_1h": tx_count_1h}
            )
            return 0.0

    @staticmethod
    def calculate_vol_momentum(volume_5m: float, volume_1h: float, liquidity_usd: float = 0.0, filtering_settings: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate volume momentum component with liquidity weighting.
        
        Enhanced Formula: (volume_5m / avg_5m_volume) * liquidity_factor
        
        This compares the trading volume in the last 5 minutes to the average
        5-minute volume over the last hour, weighted by liquidity depth to
        favor tokens with sufficient liquidity for arbitrage.
        
        Args:
            volume_5m: Trading volume in last 5 minutes (USD)
            volume_1h: Trading volume in last 1 hour (USD)
            liquidity_usd: Total liquidity in USD (optional, default: 0.0)
            
        Returns:
            Volume momentum ratio weighted by liquidity (0.0 if invalid inputs)
        """
        try:
            if volume_5m < 0 or volume_1h < 0:
                return 0.0
            
            # Apply filtering thresholds from settings
            if filtering_settings:
                min_vol_5m = filtering_settings.get("min_volume_threshold_5m", 1.0)
                min_vol_1h = filtering_settings.get("min_volume_threshold_1h", 1.0)
                
                if volume_5m < min_vol_5m or volume_1h < min_vol_1h:
                    return 0.0
            else:
                # Fallback: require some minimal trading activity (at least $1 volume)
                if volume_5m == 0 or volume_1h == 0:
                    return 0.0
                
            # Average 5-minute volume over the last hour
            avg_5m_volume = volume_1h / 12.0
            
            if avg_5m_volume <= 0:
                return 0.0
                
            # Base momentum calculation
            base_momentum = volume_5m / avg_5m_volume
            
            # Liquidity factor: normalize liquidity impact
            # Tokens with higher liquidity get better scores for same momentum
            if liquidity_usd > 0:
                # Get liquidity threshold from settings or use default
                liquidity_threshold = float(filtering_settings.get("liquidity_factor_threshold", 100000.0) if filtering_settings else 100000.0)
                # Sigmoid-like function: significant boost up to configured liquidity threshold
                liquidity_factor = min(1.0, liquidity_usd / liquidity_threshold)
                # Apply square root to reduce extreme differences
                liquidity_factor = math.sqrt(liquidity_factor)
            else:
                liquidity_factor = 0.5  # Default factor if liquidity unknown
            
            result = base_momentum * liquidity_factor
            
            # Sanity check for extreme values and cap at reasonable maximum
            if math.isnan(result) or math.isinf(result) or result < 0:
                return 0.0
                
            # Cap at 15x to prevent extreme scores
            return min(result, 15.0)
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "vol_momentum_calculation_error",
                extra={"volume_5m": volume_5m, "volume_1h": volume_1h, "liquidity_usd": liquidity_usd}
            )
            return 0.0
    
    @staticmethod
    def calculate_token_freshness(hours_since_creation: float, threshold_hours: float = 6.0) -> float:
        """
        Calculate token freshness component.
        
        Formula: max(0, (threshold_hours - hours_since_creation) / threshold_hours)
        
        This gives higher scores to tokens that were recently migrated to the system.
        Fresh tokens (< 6 hours old) get a score between 0 and 1, older tokens get 0.
        
        Args:
            hours_since_creation: Hours since token was first added to system
            threshold_hours: Freshness threshold in hours (default: 6.0)
            
        Returns:
            Token freshness score between 0.0 and 1.0
        """
        try:
            if threshold_hours <= 0:
                return 0.0
                
            if hours_since_creation < 0:
                # Handle edge case of negative time (shouldn't happen in practice)
                return 1.0
                
            freshness = (threshold_hours - hours_since_creation) / threshold_hours
            result = max(0.0, freshness)
            
            # Sanity check
            if math.isnan(result) or math.isinf(result):
                return 0.0
                
            return min(1.0, result)  # Clamp to [0, 1]
            
        except (TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "token_freshness_calculation_error",
                extra={"hours_since_creation": hours_since_creation, "threshold_hours": threshold_hours}
            )
            return 0.0
    
    @staticmethod
    def calculate_orderflow_imbalance(buys_volume_5m: float, sells_volume_5m: float, 
                                    total_buys_5m: int = 0, total_sells_5m: int = 0, settings: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate orderflow imbalance component with volume weighting and significance threshold.
        
        Enhanced Formula: Volume-weighted imbalance with minimum volume threshold
        
        This measures the predominant pressure (buyers vs sellers) in the last 5 minutes,
        weighted by actual volume rather than just transaction count. Only significant
        volume imbalances are considered to avoid noise from small trades.
        
        Args:
            buys_volume_5m: Buy volume in last 5 minutes (USD)
            sells_volume_5m: Sell volume in last 5 minutes (USD)
            total_buys_5m: Number of buy transactions (optional)
            total_sells_5m: Number of sell transactions (optional)
            
        Returns:
            Volume-weighted orderflow imbalance between -1.0 and 1.0 (0.0 if invalid inputs)
        """
        try:
            if buys_volume_5m < 0 or sells_volume_5m < 0:
                return 0.0
                
            total_volume = buys_volume_5m + sells_volume_5m
            
            # Get orderflow volume threshold from settings or use default
            min_volume_threshold = float(settings.get("min_orderflow_volume_5m", 500.0) if settings else 500.0)
            if total_volume < min_volume_threshold:
                return 0.0
            
            # Calculate volume-weighted imbalance
            volume_imbalance = (buys_volume_5m - sells_volume_5m) / total_volume
            
            # Apply significance weighting based on total volume
            # Get significance threshold from settings or use default
            significance_threshold = float(settings.get("orderflow_significance_threshold", 500.0) if settings else 500.0)
            volume_significance = min(1.0, total_volume / significance_threshold)
            
            # If we have transaction counts, check for manipulation patterns
            if total_buys_5m > 0 and total_sells_5m > 0:
                total_txs = total_buys_5m + total_sells_5m
                avg_buy_size = buys_volume_5m / total_buys_5m if total_buys_5m > 0 else 0
                avg_sell_size = sells_volume_5m / total_sells_5m if total_sells_5m > 0 else 0
                
                # Detect potential manipulation: very few large trades vs many small ones
                if total_txs > 0:
                    size_ratio = max(avg_buy_size, avg_sell_size) / (total_volume / total_txs) if total_txs > 0 else 1
                    # Get manipulation detection ratio from settings or use default
                    manipulation_ratio = float(settings.get("manipulation_detection_ratio", 3.0) if settings else 3.0)
                    # Reduce weight if dominated by very few large trades (potential manipulation)
                    if size_ratio > manipulation_ratio:
                        volume_significance *= 0.5
            
            result = volume_imbalance * volume_significance
            
            # Sanity check
            if math.isnan(result) or math.isinf(result):
                return 0.0
                
            # Clamp to [-1, 1] range
            return max(-1.0, min(1.0, result))
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "orderflow_imbalance_calculation_error",
                extra={
                    "buys_volume_5m": buys_volume_5m, 
                    "sells_volume_5m": sells_volume_5m,
                    "total_buys_5m": total_buys_5m,
                    "total_sells_5m": total_sells_5m
                }
            )
            return 0.0
    
    @staticmethod
    def validate_component_inputs(metrics: dict) -> dict:
        """
        Validate and sanitize component calculation inputs.
        
        Args:
            metrics: Dictionary containing raw metrics from DEX aggregator
            
        Returns:
            Dictionary with validated and sanitized inputs
        """
        def safe_float(value, default: float = 0.0) -> float:
            """Safely convert value to float with fallback."""
            try:
                if value is None:
                    return default
                result = float(value)
                return result if not (math.isnan(result) or math.isinf(result)) else default
            except (TypeError, ValueError):
                return default
        
        # Map actual field names from DEX aggregator to expected field names
        # DEX aggregator uses 'n_5m' but scoring expects 'tx_count_5m'
        tx_count_5m = safe_float(metrics.get("tx_count_5m") or metrics.get("n_5m"), 0.0)
        
        return {
            "tx_count_5m": tx_count_5m,
            "tx_count_1h": safe_float(metrics.get("tx_count_1h"), 0.0),
            "volume_5m": safe_float(metrics.get("volume_5m"), 0.0),
            "volume_1h": safe_float(metrics.get("volume_1h"), 0.0),
            "buys_volume_5m": safe_float(metrics.get("buys_volume_5m"), 0.0),
            "sells_volume_5m": safe_float(metrics.get("sells_volume_5m"), 0.0),
            "hours_since_creation": safe_float(metrics.get("hours_since_creation"), 0.0),
            "liquidity_usd": safe_float(metrics.get("L_tot"), 0.0),
            "total_buys_5m": int(safe_float(metrics.get("total_buys_5m"), 0.0)),
            "total_sells_5m": int(safe_float(metrics.get("total_sells_5m"), 0.0)),
        }