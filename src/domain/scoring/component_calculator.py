"""
Component Calculator for Hybrid Momentum Scoring Model

This module implements the calculation of individual scoring components
according to the hybrid momentum model specification.
"""
from __future__ import annotations

import logging
import math
from typing import Optional


class ComponentCalculator:
    """Calculator for hybrid momentum scoring components."""
    
    @staticmethod
    def calculate_tx_accel(tx_count_5m: float, tx_count_1h: float) -> float:
        """
        Calculate transaction acceleration component.
        
        Formula: (tx_count_5m / 5) / (tx_count_1h / 60)
        
        This measures if the trading pace is accelerating in the last 5 minutes
        compared to the average pace over the last hour.
        
        Args:
            tx_count_5m: Number of transactions in last 5 minutes
            tx_count_1h: Number of transactions in last 1 hour
            
        Returns:
            Transaction acceleration ratio (0.0 if invalid inputs)
        """
        try:
            if tx_count_1h <= 0 or tx_count_5m < 0:
                return 0.0
                
            # Calculate rates per minute
            rate_5m = tx_count_5m / 5.0
            rate_1h = tx_count_1h / 60.0
            
            if rate_1h <= 0:
                return 0.0
                
            result = rate_5m / rate_1h
            
            # Sanity check for extreme values
            if math.isnan(result) or math.isinf(result) or result < 0:
                return 0.0
                
            return result
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "tx_accel_calculation_error", 
                extra={"tx_count_5m": tx_count_5m, "tx_count_1h": tx_count_1h}
            )
            return 0.0
    
    @staticmethod
    def calculate_vol_momentum(volume_5m: float, volume_1h: float) -> float:
        """
        Calculate volume momentum component.
        
        Formula: volume_5m / (volume_1h / 12)
        
        This compares the trading volume in the last 5 minutes to the average
        5-minute volume over the last hour.
        
        Args:
            volume_5m: Trading volume in last 5 minutes (USD)
            volume_1h: Trading volume in last 1 hour (USD)
            
        Returns:
            Volume momentum ratio (0.0 if invalid inputs)
        """
        try:
            if volume_1h <= 0 or volume_5m < 0:
                return 0.0
                
            # Average 5-minute volume over the last hour
            avg_5m_volume = volume_1h / 12.0
            
            if avg_5m_volume <= 0:
                return 0.0
                
            result = volume_5m / avg_5m_volume
            
            # Sanity check for extreme values
            if math.isnan(result) or math.isinf(result) or result < 0:
                return 0.0
                
            return result
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "vol_momentum_calculation_error",
                extra={"volume_5m": volume_5m, "volume_1h": volume_1h}
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
    def calculate_orderflow_imbalance(buys_volume_5m: float, sells_volume_5m: float) -> float:
        """
        Calculate orderflow imbalance component.
        
        Formula: (buys_volume_5m - sells_volume_5m) / (buys_volume_5m + sells_volume_5m)
        
        This measures the predominant pressure (buyers vs sellers) in the last 5 minutes.
        Positive values indicate buying pressure, negative values indicate selling pressure.
        
        Args:
            buys_volume_5m: Buy volume in last 5 minutes (USD)
            sells_volume_5m: Sell volume in last 5 minutes (USD)
            
        Returns:
            Orderflow imbalance between -1.0 and 1.0 (0.0 if invalid inputs)
        """
        try:
            if buys_volume_5m < 0 or sells_volume_5m < 0:
                return 0.0
                
            total_volume = buys_volume_5m + sells_volume_5m
            
            if total_volume <= 0:
                return 0.0
                
            result = (buys_volume_5m - sells_volume_5m) / total_volume
            
            # Sanity check
            if math.isnan(result) or math.isinf(result):
                return 0.0
                
            # Clamp to [-1, 1] range
            return max(-1.0, min(1.0, result))
            
        except (ZeroDivisionError, TypeError, ValueError):
            logging.getLogger("component_calculator").warning(
                "orderflow_imbalance_calculation_error",
                extra={"buys_volume_5m": buys_volume_5m, "sells_volume_5m": sells_volume_5m}
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
        
        return {
            "tx_count_5m": safe_float(metrics.get("tx_count_5m"), 0.0),
            "tx_count_1h": safe_float(metrics.get("tx_count_1h"), 0.0),
            "volume_5m": safe_float(metrics.get("volume_5m"), 0.0),
            "volume_1h": safe_float(metrics.get("volume_1h"), 0.0),
            "buys_volume_5m": safe_float(metrics.get("buys_volume_5m"), 0.0),
            "sells_volume_5m": safe_float(metrics.get("sells_volume_5m"), 0.0),
            "hours_since_creation": safe_float(metrics.get("hours_since_creation"), 0.0),
        }