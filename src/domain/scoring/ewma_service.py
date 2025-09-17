"""
EWMA (Exponential Weighted Moving Average) Smoothing Service

This service applies EWMA smoothing to scoring components to reduce volatility
and provide more stable scoring results over time.
"""
from __future__ import annotations

import logging
import math
from typing import Optional, Dict, Any

from src.adapters.repositories.tokens_repo import TokensRepository


class EWMAService:
    """Service for applying EWMA smoothing to scoring components."""
    
    def __init__(self, repository: TokensRepository):
        """
        Initialize EWMA service.
        
        Args:
            repository: Token repository for accessing historical EWMA data
        """
        self.repository = repository
        self.logger = logging.getLogger("ewma_service")
    
    def apply_smoothing(self, token_id: int, raw_components: Dict[str, float], alpha: float) -> Dict[str, float]:
        """
        Apply EWMA smoothing to all components and final score.
        
        Args:
            token_id: ID of the token being scored
            raw_components: Dictionary of raw component values
            alpha: EWMA smoothing parameter (0.0-1.0)
            
        Returns:
            Dictionary of smoothed component values
        """
        try:
            # Validate alpha parameter
            alpha = max(0.0, min(1.0, alpha))
            
            # Get previous EWMA values
            previous_values = self.get_previous_values(token_id)
            
            # Apply smoothing to each component
            smoothed_components = {}
            
            # Define the components that need smoothing
            component_keys = [
                "tx_accel",
                "vol_momentum", 
                "token_freshness",
                "orderflow_imbalance",
                "final_score"
            ]
            
            for key in component_keys:
                if key in raw_components:
                    current_value = raw_components[key]
                    previous_value = previous_values.get(key) if previous_values else None
                    
                    smoothed_value = self.calculate_ewma(current_value, previous_value, alpha)
                    smoothed_components[key] = smoothed_value
                    
                    self.logger.debug(
                        "ewma_smoothing_applied",
                        extra={
                            "token_id": token_id,
                            "component": key,
                            "raw_value": current_value,
                            "previous_value": previous_value,
                            "smoothed_value": smoothed_value,
                            "alpha": alpha
                        }
                    )
            
            return smoothed_components
            
        except Exception as e:
            self.logger.error(
                "ewma_smoothing_error",
                extra={
                    "token_id": token_id,
                    "error": str(e),
                    "raw_components": raw_components
                }
            )
            # Return raw components as fallback
            return raw_components.copy()
    
    def get_previous_values(self, token_id: int) -> Optional[Dict[str, float]]:
        """
        Get previous EWMA values for a token.
        
        Args:
            token_id: ID of the token
            
        Returns:
            Dictionary of previous smoothed values or None if no history exists
        """
        try:
            # Get the most recent score record for this token
            latest_score = self.repository.get_latest_score(token_id)
            
            if latest_score and latest_score.smoothed_components:
                return latest_score.smoothed_components
                
            return None
            
        except Exception as e:
            self.logger.warning(
                "failed_to_get_previous_ewma_values",
                extra={
                    "token_id": token_id,
                    "error": str(e)
                }
            )
            return None
    
    def calculate_ewma(self, current: float, previous: Optional[float], alpha: float) -> float:
        """
        Calculate single EWMA value.
        
        Formula: EWMA_new = alpha * current + (1 - alpha) * EWMA_previous
        
        Args:
            current: Current raw value
            previous: Previous EWMA value (None for initialization)
            alpha: EWMA smoothing parameter (0.0-1.0)
            
        Returns:
            Smoothed EWMA value
        """
        try:
            # Validate inputs
            if math.isnan(current) or math.isinf(current):
                current = 0.0
                
            alpha = max(0.0, min(1.0, alpha))
            
            # Handle initialization case
            if previous is None:
                return float(round(current, 6))
            
            # Validate previous value
            if math.isnan(previous) or math.isinf(previous):
                previous = 0.0
            
            # Calculate EWMA
            ewma_value = alpha * current + (1 - alpha) * previous
            
            # Round to avoid floating point precision issues
            return float(round(ewma_value, 6))
            
        except Exception as e:
            self.logger.warning(
                "ewma_calculation_error",
                extra={
                    "current": current,
                    "previous": previous,
                    "alpha": alpha,
                    "error": str(e)
                }
            )
            # Fallback to current value
            return float(round(current if not (math.isnan(current) or math.isinf(current)) else 0.0, 6))
    
    def validate_smoothing_parameters(self, alpha: float) -> float:
        """
        Validate and sanitize EWMA smoothing parameters.
        
        Args:
            alpha: Raw alpha parameter
            
        Returns:
            Validated alpha parameter clamped to [0.0, 1.0]
        """
        try:
            if alpha is None:
                return 0.3  # Default value
                
            alpha_float = float(alpha)
            
            if math.isnan(alpha_float) or math.isinf(alpha_float):
                return 0.3  # Default value
                
            # Clamp to valid range
            return max(0.0, min(1.0, alpha_float))
            
        except (TypeError, ValueError):
            self.logger.warning(
                "invalid_alpha_parameter",
                extra={"alpha": alpha}
            )
            return 0.3  # Default value
    
    def get_smoothing_statistics(self, token_id: int, component: str, window_size: int = 10) -> Dict[str, Any]:
        """
        Get smoothing statistics for analysis and debugging.
        
        Args:
            token_id: ID of the token
            component: Component name to analyze
            window_size: Number of recent values to analyze
            
        Returns:
            Dictionary with smoothing statistics
        """
        try:
            # Get recent score history
            recent_scores = self.repository.get_score_history(token_id, limit=window_size)
            
            if not recent_scores:
                return {"error": "No score history available"}
            
            raw_values = []
            smoothed_values = []
            
            for score in recent_scores:
                if score.metrics and component in score.metrics:
                    raw_values.append(score.metrics[component])
                    
                if score.smoothed_components and component in score.smoothed_components:
                    smoothed_values.append(score.smoothed_components[component])
            
            if not raw_values or not smoothed_values:
                return {"error": f"No data available for component {component}"}
            
            # Calculate statistics
            raw_mean = sum(raw_values) / len(raw_values)
            smoothed_mean = sum(smoothed_values) / len(smoothed_values)
            
            raw_variance = sum((x - raw_mean) ** 2 for x in raw_values) / len(raw_values)
            smoothed_variance = sum((x - smoothed_mean) ** 2 for x in smoothed_values) / len(smoothed_values)
            
            variance_reduction = (raw_variance - smoothed_variance) / raw_variance if raw_variance > 0 else 0
            
            return {
                "component": component,
                "window_size": len(raw_values),
                "raw_mean": round(raw_mean, 6),
                "smoothed_mean": round(smoothed_mean, 6),
                "raw_variance": round(raw_variance, 6),
                "smoothed_variance": round(smoothed_variance, 6),
                "variance_reduction": round(variance_reduction, 4),
                "latest_raw": raw_values[-1] if raw_values else None,
                "latest_smoothed": smoothed_values[-1] if smoothed_values else None,
            }
            
        except Exception as e:
            self.logger.error(
                "smoothing_statistics_error",
                extra={
                    "token_id": token_id,
                    "component": component,
                    "error": str(e)
                }
            )
            return {"error": f"Failed to calculate statistics: {str(e)}"}