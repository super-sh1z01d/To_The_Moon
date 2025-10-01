"""
Hybrid Momentum Scoring Model

This module implements the new hybrid momentum scoring model that combines
transaction acceleration, volume momentum, token freshness, and orderflow
imbalance to provide better short-term arbitrage potential assessment.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .component_calculator import ComponentCalculator
from .ewma_service import EWMAService
from src.domain.settings.service import SettingsService
from src.adapters.db.models import Token


class ScoringResult:
    """Result of scoring calculation with all components and metadata."""
    
    def __init__(
        self,
        final_score: float,
        smoothed_score: float,
        raw_components: Dict[str, float],
        smoothed_components: Dict[str, float],
        weights: Dict[str, float],
        metadata: Dict[str, Any]
    ):
        self.final_score = final_score
        self.smoothed_score = smoothed_score
        self.raw_components = raw_components
        self.smoothed_components = smoothed_components
        self.weights = weights
        self.metadata = metadata


class WeightConfig:
    """Configuration for scoring component weights."""
    
    def __init__(
        self,
        w_tx: float = 0.25,
        w_vol: float = 0.25,
        w_fresh: float = 0.25,
        w_oi: float = 0.25,
        ewma_alpha: float = 0.3,
        freshness_threshold_hours: float = 6.0
    ):
        self.w_tx = w_tx
        self.w_vol = w_vol
        self.w_fresh = w_fresh
        self.w_oi = w_oi
        self.ewma_alpha = ewma_alpha
        self.freshness_threshold_hours = freshness_threshold_hours
    
    def validate(self) -> bool:
        """Validate weight configuration."""
        try:
            # Check all weights are non-negative
            if any(w < 0 for w in [self.w_tx, self.w_vol, self.w_fresh, self.w_oi]):
                return False
            
            # Check EWMA alpha is in valid range
            if not (0.0 <= self.ewma_alpha <= 1.0):
                return False
            
            # Check freshness threshold is positive
            if self.freshness_threshold_hours <= 0:
                return False
            
            return True
        except Exception:
            return False


class HybridMomentumModel:
    """Hybrid momentum scoring model implementation."""
    
    def __init__(self, settings_service: SettingsService, ewma_service: EWMAService):
        """
        Initialize hybrid momentum model.
        
        Args:
            settings_service: Service for accessing configuration settings
            ewma_service: Service for EWMA smoothing
        """
        self.settings = settings_service
        self.ewma = ewma_service
        self.logger = logging.getLogger("hybrid_momentum_model")
    
    def calculate_score(self, token: Token, metrics: Dict[str, Any]) -> ScoringResult:
        """
        Calculate hybrid momentum score with EWMA smoothing.
        
        Args:
            token: Token entity with creation timestamp
            metrics: Enhanced metrics from DEX aggregator
            
        Returns:
            ScoringResult with all scoring components and metadata
        """
        try:
            # Get current weight configuration
            weights = self.get_weights()
            
            if not weights.validate():
                raise ValueError("Invalid weight configuration")
            
            # Calculate raw components
            raw_components = self.calculate_components(metrics, token, weights)
            
            # Calculate raw final score
            raw_final_score = self._calculate_weighted_score(raw_components, weights)
            raw_components["final_score"] = raw_final_score
            
            # Apply EWMA smoothing
            smoothed_components = self.ewma.apply_smoothing(
                token.id, raw_components, weights.ewma_alpha
            )
            
            smoothed_final_score = smoothed_components.get("final_score", raw_final_score)
            
            # Prepare metadata
            metadata = {
                "model_version": "hybrid_momentum_v1.0",
                "calculated_at": datetime.now().isoformat(),
                "token_id": token.id,
                "mint_address": token.mint_address,
                "ewma_alpha": weights.ewma_alpha,
                "freshness_threshold_hours": weights.freshness_threshold_hours,
                "input_metrics_count": len(metrics),
                "has_previous_ewma": self.ewma.get_previous_values(token.id) is not None,
            }
            
            result = ScoringResult(
                final_score=raw_final_score,
                smoothed_score=smoothed_final_score,
                raw_components=raw_components,
                smoothed_components=smoothed_components,
                weights={
                    "w_tx": weights.w_tx,
                    "w_vol": weights.w_vol,
                    "w_fresh": weights.w_fresh,
                    "w_oi": weights.w_oi,
                },
                metadata=metadata
            )
            
            self.logger.info(
                "hybrid_momentum_score_calculated",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "raw_score": raw_final_score,
                    "smoothed_score": smoothed_final_score,
                    "components": {
                        "tx_accel": raw_components.get("tx_accel"),
                        "vol_momentum": raw_components.get("vol_momentum"),
                        "token_freshness": raw_components.get("token_freshness"),
                        "orderflow_imbalance": raw_components.get("orderflow_imbalance"),
                    }
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "hybrid_momentum_scoring_error",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "error": str(e),
                    "metrics_keys": list(metrics.keys()) if metrics else []
                }
            )
            # Return fallback result
            return self._create_fallback_result(token, str(e))
    
    def calculate_components(
        self, 
        metrics: Dict[str, Any], 
        token: Any,  # Token object with status and created_at
        weights: WeightConfig
    ) -> Dict[str, float]:
        """
        Calculate raw scoring components.
        
        Args:
            metrics: Enhanced metrics from DEX aggregator
            token: Token object with status and created_at attributes
            weights: Weight configuration
            
        Returns:
            Dictionary of raw component values
        """
        try:
            # Validate and sanitize inputs
            validated_inputs = ComponentCalculator.validate_component_inputs(metrics)
            
            # Get filtering thresholds based on token status
            filtering_settings = self._get_filtering_settings(token.status)
            
            # Calculate transaction component based on mode setting
            tx_calculation_mode = self.settings.get("tx_calculation_mode") or "acceleration"
            
            if tx_calculation_mode == "arbitrage_activity":
                # Use new arbitrage-optimized calculation
                tx_accel = ComponentCalculator.calculate_tx_arbitrage_activity(
                    validated_inputs["tx_count_5m"],
                    validated_inputs["tx_count_1h"],
                    filtering_settings
                )
            else:
                # Use traditional acceleration calculation (default)
                tx_accel = ComponentCalculator.calculate_tx_accel(
                    validated_inputs["tx_count_5m"],
                    validated_inputs["tx_count_1h"],
                    filtering_settings
                )
            
            vol_momentum = ComponentCalculator.calculate_vol_momentum(
                validated_inputs["volume_5m"],
                validated_inputs["volume_1h"],
                validated_inputs["liquidity_usd"],
                filtering_settings
            )
            
            token_freshness = ComponentCalculator.calculate_token_freshness(
                validated_inputs["hours_since_creation"],
                weights.freshness_threshold_hours
            )
            
            orderflow_imbalance = ComponentCalculator.calculate_orderflow_imbalance(
                validated_inputs["buys_volume_5m"],
                validated_inputs["sells_volume_5m"],
                validated_inputs["total_buys_5m"],
                validated_inputs["total_sells_5m"],
                filtering_settings
            )
            
            components = {
                "tx_accel": tx_accel,
                "vol_momentum": vol_momentum,
                "token_freshness": token_freshness,
                "orderflow_imbalance": orderflow_imbalance,
            }
            
            self.logger.debug(
                "components_calculated",
                extra={
                    "components": components,
                    "validated_inputs": validated_inputs,
                    "freshness_threshold": weights.freshness_threshold_hours,
                }
            )
            
            return components
            
        except Exception as e:
            import traceback
            self.logger.error(
                "component_calculation_error",
                extra={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "metrics_keys": list(metrics.keys()) if metrics else [],
                    "token_created_at": str(token.created_at),
                    "token_status": getattr(token, 'status', 'unknown') if hasattr(token, 'status') else 'no_token'
                }
            )
            # Return zero components as fallback
            return {
                "tx_accel": 0.0,
                "vol_momentum": 0.0,
                "token_freshness": 0.0,
                "orderflow_imbalance": 0.0,
            }
    
    def get_weights(self) -> WeightConfig:
        """
        Get current weight configuration from settings.
        
        Returns:
            WeightConfig with current settings
        """
        try:
            w_tx = float(self.settings.get("w_tx") or "0.25")
            w_vol = float(self.settings.get("w_vol") or "0.25")
            w_fresh = float(self.settings.get("w_fresh") or "0.25")
            w_oi = float(self.settings.get("w_oi") or "0.25")
            ewma_alpha = float(self.settings.get("ewma_alpha") or "0.3")
            freshness_threshold = float(self.settings.get("freshness_threshold_hours") or "6.0")
            
            return WeightConfig(
                w_tx=w_tx,
                w_vol=w_vol,
                w_fresh=w_fresh,
                w_oi=w_oi,
                ewma_alpha=ewma_alpha,
                freshness_threshold_hours=freshness_threshold
            )
            
        except Exception as e:
            self.logger.warning(
                "weight_config_error_using_defaults",
                extra={"error": str(e)}
            )
            # Return default configuration
            return WeightConfig()
    
    def _get_filtering_settings(self, token_status: str = "active") -> Dict[str, Any]:
        """
        Get filtering threshold settings based on token status.
        
        Args:
            token_status: Token status ("monitoring" or "active")
            
        Returns:
            Dictionary with filtering thresholds
        """
        try:
            if token_status == "monitoring":
                # For monitoring tokens: minimal filtering, only basic validation
                return {
                    "min_tx_threshold_5m": 1.0,    # At least 1 transaction
                    "min_tx_threshold_1h": 1.0,    # At least 1 transaction  
                    "min_volume_threshold_5m": 1.0,  # At least $1 volume
                    "min_volume_threshold_1h": 1.0,  # At least $1 volume
                    "min_orderflow_volume_5m": 1.0,  # At least $1 volume
                    # Component calculation parameters (same for all tokens)
                    "liquidity_factor_threshold": float(self.settings.get("liquidity_factor_threshold") or "100000.0"),
                    "orderflow_significance_threshold": float(self.settings.get("orderflow_significance_threshold") or "500.0"),
                    "manipulation_detection_ratio": float(self.settings.get("manipulation_detection_ratio") or "3.0"),
                    # Arbitrage mode parameters - use same settings as active tokens
                    "arbitrage_min_tx_5m": int(self.settings.get("arbitrage_min_tx_5m") or "100"),
                    "arbitrage_optimal_tx_5m": int(self.settings.get("arbitrage_optimal_tx_5m") or "200"),
                    "arbitrage_acceleration_weight": float(self.settings.get("arbitrage_acceleration_weight") or "0.1"),
                }
            else:
                # For active tokens: strict filtering (current behavior)
                return {
                    "min_tx_threshold_5m": float(self.settings.get("min_tx_threshold_5m") or "0"),
                    "min_tx_threshold_1h": float(self.settings.get("min_tx_threshold_1h") or "0"),
                    "min_volume_threshold_5m": float(self.settings.get("min_volume_threshold_5m") or "0"),
                    "min_volume_threshold_1h": float(self.settings.get("min_volume_threshold_1h") or "0"),
                    "min_orderflow_volume_5m": float(self.settings.get("min_orderflow_volume_5m") or "0"),
                    # Component calculation parameters
                    "liquidity_factor_threshold": float(self.settings.get("liquidity_factor_threshold") or "100000.0"),
                    "orderflow_significance_threshold": float(self.settings.get("orderflow_significance_threshold") or "500.0"),
                    "manipulation_detection_ratio": float(self.settings.get("manipulation_detection_ratio") or "3.0"),
                    # Arbitrage mode parameters - consistent with monitoring tokens
                    "arbitrage_min_tx_5m": int(self.settings.get("arbitrage_min_tx_5m") or "100"),
                    "arbitrage_optimal_tx_5m": int(self.settings.get("arbitrage_optimal_tx_5m") or "200"),
                    "arbitrage_acceleration_weight": float(self.settings.get("arbitrage_acceleration_weight") or "0.1"),
                }
        except Exception as e:
            self.logger.warning(
                "filtering_settings_error_using_defaults",
                extra={"error": str(e), "token_status": token_status}
            )
            # Return default thresholds
            return {
                "min_tx_threshold_5m": 0.0,
                "min_tx_threshold_1h": 0.0,
                "min_volume_threshold_5m": 0.0,
                "min_volume_threshold_1h": 0.0,
                "min_orderflow_volume_5m": 0.0,
                # Component calculation parameters
                "liquidity_factor_threshold": 100000.0,
                "orderflow_significance_threshold": 500.0,
                "manipulation_detection_ratio": 3.0,
            }
    
    def _calculate_weighted_score(
        self, 
        components: Dict[str, float], 
        weights: WeightConfig
    ) -> float:
        """
        Calculate weighted final score from components.
        
        Formula: Score = (W_tx * Tx_Accel) + (W_vol * Vol_Momentum) + 
                        (W_fresh * Token_Freshness) + (W_oi * Orderflow_Imbalance)
        
        Args:
            components: Dictionary of component values
            weights: Weight configuration
            
        Returns:
            Weighted final score
        """
        try:
            score = (
                weights.w_tx * components.get("tx_accel", 0.0) +
                weights.w_vol * components.get("vol_momentum", 0.0) +
                weights.w_fresh * components.get("token_freshness", 0.0) +
                weights.w_oi * components.get("orderflow_imbalance", 0.0)
            )
            
            # Round to avoid floating point precision issues
            return round(score, 6)
            
        except Exception as e:
            self.logger.error(
                "weighted_score_calculation_error",
                extra={
                    "error": str(e),
                    "components": components,
                    "weights": {
                        "w_tx": weights.w_tx,
                        "w_vol": weights.w_vol,
                        "w_fresh": weights.w_fresh,
                        "w_oi": weights.w_oi,
                    }
                }
            )
            return 0.0
    
    def _create_fallback_result(self, token: Token, error_message: str) -> ScoringResult:
        """
        Create fallback scoring result when calculation fails.
        
        Args:
            token: Token entity
            error_message: Error description
            
        Returns:
            ScoringResult with zero values and error metadata
        """
        fallback_components = {
            "tx_accel": 0.0,
            "vol_momentum": 0.0,
            "token_freshness": 0.0,
            "orderflow_imbalance": 0.0,
            "final_score": 0.0,
        }
        
        fallback_metadata = {
            "model_version": "hybrid_momentum_v1.0",
            "calculated_at": datetime.now().isoformat(),
            "token_id": token.id,
            "mint_address": token.mint_address,
            "error": error_message,
            "is_fallback": True,
        }
        
        return ScoringResult(
            final_score=0.0,
            smoothed_score=0.0,
            raw_components=fallback_components,
            smoothed_components=fallback_components,
            weights={"w_tx": 0.25, "w_vol": 0.25, "w_fresh": 0.25, "w_oi": 0.25},
            metadata=fallback_metadata
        )
    
    def validate_scoring_inputs(self, token: Token, metrics: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate inputs for scoring calculation.
        
        Args:
            token: Token entity
            metrics: Metrics dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not token:
                return False, "Token is None"
            
            if not token.id:
                return False, "Token ID is missing"
            
            if not token.created_at:
                return False, "Token creation timestamp is missing"
            
            if not isinstance(metrics, dict):
                return False, "Metrics must be a dictionary"
            
            # Check for required metric fields (with fallbacks)
            required_fields = [
                "tx_count_5m", "tx_count_1h", "volume_5m", "volume_1h",
                "buys_volume_5m", "sells_volume_5m", "hours_since_creation"
            ]
            
            missing_fields = [field for field in required_fields if field not in metrics]
            if missing_fields:
                self.logger.warning(
                    "missing_metric_fields_will_use_defaults",
                    extra={
                        "token_id": token.id,
                        "missing_fields": missing_fields
                    }
                )
                # Don't fail validation, just warn - ComponentCalculator will handle defaults
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"