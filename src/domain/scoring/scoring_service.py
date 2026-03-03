"""
Scoring Service - hybrid momentum only (v2).

Legacy scoring model has been removed. All score computations use
the hybrid momentum model with EWMA smoothing.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from src.adapters.db.models import Token
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.metrics.enhanced_dex_aggregator import aggregate_enhanced_metrics
from src.domain.pools.classifier_dex_only import (
    classify_pairs_dex_only,
    determine_primary_pool_type,
)
from src.domain.settings.service import SettingsService

from src.domain.scoring.ewma_service import EWMAService
from src.domain.scoring.hybrid_momentum_model import HybridMomentumModel


class NoClassifiedPoolsError(Exception):
    """Raised when no usable pools are available for scoring."""

    pass


class ScoringService:
    """Hybrid-momentum scoring service."""

    def __init__(self, repository: TokensRepository, settings_service: SettingsService):
        self.repository = repository
        self.settings = settings_service
        self.logger = logging.getLogger("scoring_service")
        self.ewma_service = EWMAService(repository)
        self.hybrid_model = HybridMomentumModel(settings_service, self.ewma_service)

    def close(self) -> None:
        # Kept for API compatibility with older call-sites.
        return None

    def calculate_token_score(
        self,
        token: Token,
        pairs: list[dict[str, Any]],
    ) -> Tuple[float, Optional[float], dict[str, Any], Optional[dict], Optional[dict]]:
        try:
            return self._calculate_hybrid_momentum_score(token, pairs)
        except NoClassifiedPoolsError:
            raise
        except Exception as e:
            self.logger.error(
                "scoring_calculation_error",
                extra={
                    "token_id": token.id,
                    "mint_address": token.mint_address,
                    "error": str(e),
                },
            )
            return 0.0, 0.0, {}, None, None

    def _calculate_hybrid_momentum_score(
        self,
        token: Token,
        pairs: list[dict[str, Any]],
    ) -> Tuple[float, Optional[float], dict[str, Any], Optional[dict], Optional[dict]]:
        # Use lower threshold for monitoring tokens.
        if token.status == "monitoring":
            min_liquidity = float(self.settings.get("activation_min_liquidity_usd") or "200")
        else:
            min_liquidity = float(self.settings.get("min_pool_liquidity_usd") or "500")

        enriched_pairs = classify_pairs_dex_only(pairs or [])
        if not enriched_pairs:
            raise NoClassifiedPoolsError("no pools available after dex-only classification")

        metrics = aggregate_enhanced_metrics(
            token.mint_address,
            enriched_pairs,
            token.created_at,
            min_liquidity_usd=min_liquidity,
        )
        metrics["pool_classification_source"] = "dexscreener"
        primary_pool_type = determine_primary_pool_type(metrics.get("pools") or [])
        if primary_pool_type:
            metrics["primary_pool_type"] = primary_pool_type

        result = self.hybrid_model.calculate_score(token, metrics)

        self.logger.info(
            "hybrid_momentum_score_calculated",
            extra={
                "token_id": token.id,
                "mint_address": token.mint_address,
                "raw_score": result.final_score,
                "smoothed_score": result.smoothed_score,
                "model": "hybrid_momentum",
            },
        )

        return (
            result.final_score,
            result.smoothed_score,
            metrics,
            result.raw_components,
            result.smoothed_components,
        )

    def save_score_result(
        self,
        token: Token,
        score: float,
        smoothed_score: Optional[float],
        metrics: dict[str, Any],
        raw_components: Optional[dict] = None,
        smoothed_components: Optional[dict] = None,
    ) -> int:
        snapshot_id = self.repository.insert_score_snapshot(
            token_id=token.id,
            metrics=metrics,
            score=score,
            smoothed_score=smoothed_score,
            raw_components=raw_components,
            smoothed_components=smoothed_components,
            scoring_model="hybrid_momentum",
        )

        self.logger.debug(
            "score_result_saved",
            extra={
                "token_id": token.id,
                "snapshot_id": snapshot_id,
                "score": score,
                "smoothed_score": smoothed_score,
                "model": "hybrid_momentum",
            },
        )
        return snapshot_id

    def get_active_model(self) -> str:
        return "hybrid_momentum"

    def validate_model_configuration(self, model_name: str) -> Tuple[bool, str]:
        if model_name != "hybrid_momentum":
            return False, "Only hybrid_momentum is supported in v2"

        try:
            weights = self.hybrid_model.get_weights()
            if not weights.validate():
                return False, "Invalid hybrid momentum weight configuration"
            return True, ""
        except Exception as e:
            return False, f"Validation error: {e}"
