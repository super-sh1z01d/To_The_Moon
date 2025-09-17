"""
Scoring Service - Unified interface for different scoring models

This service provides a unified interface for scoring tokens using different
models (legacy and hybrid momentum) based on configuration settings.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.adapters.db.models import Token, TokenScore
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.domain.metrics.enhanced_dex_aggregator import aggregate_enhanced_metrics
from src.domain.metrics.dex_aggregator import aggregate_wsol_metrics

# Legacy scoring
from src.domain.scoring.scorer import compute_score, compute_smoothed_score

# New hybrid momentum scoring
from src.domain.scoring.hybrid_momentum_model import HybridMomentumModel, ScoringResult
from src.domain.scoring.ewma_service import EWMAService


class ScoringService:
    """Unified scoring service that supports multiple scoring models."""
    
    def __init__(self, repository: TokensRepository, settings_service: SettingsService):
        """
        Initialize scoring service.
        
        Args:
            repository: Token repository for data access
            settings_service: Settings service for configuration
        """
        self.repository = repository
        self.settings = settings_service
        self.logger = logging.getLogger("scoring_service")
        
        # Initialize services for hybrid momentum model
        self.ewma_service = EWMAService(repository)
        self.hybrid_model = HybridMomentumModel(settings_service, self.ewma_service)
    
    def calculate_token_score(
        self, 
        token: Token, 
        pairs: list[dict[str, Any]]
    ) -> Tuple[float, Optional[float], dict[str, Any], Optional[dict], Optional[dict]]:
        """
        Calculate token score using the active scoring model.
        
        Args:
            token: Token entity
            pairs: DexScreener pairs data
            
        Returns:
            Tuple of (score, smoothed_score, metrics, raw_components, smoothed_components)
        """
        try:
            # Get active scoring model from settings
            active_model = self.settings.get("scoring_model_active") or "legacy"
            
            if active_model == "hybrid_momentum":
                return self._calculate_hybrid_momentum_score(token, pairs)
            else:
                return self._calculate_legacy_score(token, pairs)
                
        except Exception as e:
            self.logger.error(
                "scoring_calculation_error",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "error": str(e)
                }
            )
            # Return fallback values
            return 0.0, 0.0, {}, None, None
    
    def _calculate_hybrid_momentum_score(
        self, 
        token: Token, 
        pairs: list[dict[str, Any]]
    ) -> Tuple[float, Optional[float], dict[str, Any], Optional[dict], Optional[dict]]:
        """
        Calculate score using hybrid momentum model.
        
        Args:
            token: Token entity
            pairs: DexScreener pairs data
            
        Returns:
            Tuple of (score, smoothed_score, metrics, raw_components, smoothed_components)
        """
        try:
            # Get enhanced metrics
            min_liquidity = float(self.settings.get("min_pool_liquidity_usd") or "500")
            # NOTE: max_price_change_5m removed - not used in Hybrid Momentum model
            
            metrics = aggregate_enhanced_metrics(
                token.mint_address,
                pairs,
                token.created_at,
                min_liquidity_usd=min_liquidity
            )
            
            # Calculate score using hybrid momentum model
            result = self.hybrid_model.calculate_score(token, metrics)
            
            self.logger.info(
                "hybrid_momentum_score_calculated",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "raw_score": result.final_score,
                    "smoothed_score": result.smoothed_score,
                    "model": "hybrid_momentum"
                }
            )
            
            return (
                result.final_score,
                result.smoothed_score,
                metrics,
                result.raw_components,
                result.smoothed_components
            )
            
        except Exception as e:
            self.logger.error(
                "hybrid_momentum_scoring_error",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "error": str(e)
                }
            )
            raise
    
    def _calculate_legacy_score(
        self, 
        token: Token, 
        pairs: list[dict[str, Any]]
    ) -> Tuple[float, Optional[float], dict[str, Any], Optional[dict], Optional[dict]]:
        """
        Calculate score using legacy scoring model.
        
        Args:
            token: Token entity
            pairs: DexScreener pairs data
            
        Returns:
            Tuple of (score, smoothed_score, metrics, raw_components, smoothed_components)
        """
        try:
            # Get legacy settings
            min_liquidity = float(self.settings.get("min_pool_liquidity_usd") or "500")
            max_price_change = float(self.settings.get("max_price_change_5m") or "0.5")
            smoothing_alpha = float(self.settings.get("score_smoothing_alpha") or "0.3")
            
            weights = {
                "weight_s": float(self.settings.get("weight_s") or "0.35"),
                "weight_l": float(self.settings.get("weight_l") or "0.25"),
                "weight_m": float(self.settings.get("weight_m") or "0.20"),
                "weight_t": float(self.settings.get("weight_t") or "0.20"),
            }
            
            # Get legacy metrics
            metrics = aggregate_wsol_metrics(
                token.mint_address,
                pairs,
                min_liquidity_usd=min_liquidity,
                max_price_change=max_price_change
            )
            
            # Calculate legacy score
            score, components = compute_score(metrics, weights)
            
            # Get previous smoothed score and calculate new smoothed score
            previous_smoothed = self.repository.get_previous_smoothed_score(token.id)
            smoothed_score = compute_smoothed_score(score, previous_smoothed, smoothing_alpha)
            
            self.logger.info(
                "legacy_score_calculated",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "raw_score": score,
                    "smoothed_score": smoothed_score,
                    "model": "legacy"
                }
            )
            
            return score, smoothed_score, metrics, None, None
            
        except Exception as e:
            self.logger.error(
                "legacy_scoring_error",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "error": str(e)
                }
            )
            raise
    
    def save_score_result(
        self,
        token: Token,
        score: float,
        smoothed_score: Optional[float],
        metrics: dict[str, Any],
        raw_components: Optional[dict] = None,
        smoothed_components: Optional[dict] = None
    ) -> int:
        """
        Save scoring result to database.
        
        Args:
            token: Token entity
            score: Raw calculated score
            smoothed_score: Smoothed score (if applicable)
            metrics: Metrics used for calculation
            raw_components: Raw component values (for hybrid model)
            smoothed_components: Smoothed component values (for hybrid model)
            
        Returns:
            ID of created score snapshot
        """
        try:
            active_model = self.settings.get("scoring_model_active") or "legacy"
            
            snapshot_id = self.repository.insert_score_snapshot(
                token_id=token.id,
                metrics=metrics,
                score=score,
                smoothed_score=smoothed_score,
                raw_components=raw_components,
                smoothed_components=smoothed_components,
                scoring_model=active_model
            )
            
            self.logger.debug(
                "score_result_saved",
                extra={
                    "token_id": token.id,
                    "snapshot_id": snapshot_id,
                    "score": score,
                    "smoothed_score": smoothed_score,
                    "model": active_model
                }
            )
            
            return snapshot_id
            
        except Exception as e:
            self.logger.error(
                "score_save_error",
                extra={
                    "token_id": token.id,
                    "error": str(e)
                }
            )
            raise
    
    def get_active_model(self) -> str:
        """
        Get the currently active scoring model.
        
        Returns:
            Active model name ("legacy" or "hybrid_momentum")
        """
        return self.settings.get("scoring_model_active") or "legacy"
    
    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different scoring model.
        
        Args:
            model_name: Name of the model to switch to
            
        Returns:
            True if switch was successful, False otherwise
        """
        try:
            if model_name not in ["legacy", "hybrid_momentum"]:
                self.logger.error(
                    "invalid_model_name",
                    extra={"model_name": model_name}
                )
                return False
            
            self.settings.set("scoring_model_active", model_name)
            
            self.logger.info(
                "scoring_model_switched",
                extra={
                    "new_model": model_name,
                    "previous_model": self.get_active_model()
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "model_switch_error",
                extra={
                    "model_name": model_name,
                    "error": str(e)
                }
            )
            return False
    
    def validate_model_configuration(self, model_name: str) -> Tuple[bool, str]:
        """
        Validate configuration for a specific scoring model.
        
        Args:
            model_name: Name of the model to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if model_name == "hybrid_momentum":
                # Validate hybrid momentum configuration
                weights = self.hybrid_model.get_weights()
                if not weights.validate():
                    return False, "Invalid hybrid momentum weight configuration"
                
                # Check required settings exist
                required_settings = [
                    "w_tx", "w_vol", "w_fresh", "w_oi", 
                    "ewma_alpha", "freshness_threshold_hours"
                ]
                
                for setting in required_settings:
                    value = self.settings.get(setting)
                    if value is None:
                        return False, f"Missing required setting: {setting}"
                
                return True, ""
                
            elif model_name == "legacy":
                # Validate legacy configuration
                required_settings = [
                    "weight_s", "weight_l", "weight_m", "weight_t",
                    "score_smoothing_alpha"
                ]
                
                for setting in required_settings:
                    value = self.settings.get(setting)
                    if value is None:
                        return False, f"Missing required setting: {setting}"
                
                return True, ""
                
            else:
                return False, f"Unknown model: {model_name}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"