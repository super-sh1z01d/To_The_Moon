"""
Optimized token processor that integrates parallel processing with the main scheduler.
This module provides the main entry point for parallel token processing.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

from src.adapters.db.models import Token
from src.adapters.repositories.tokens_repo import TokensRepository as TokenRepository
from src.domain.scoring.scoring_service import ScoringService
from src.scheduler.parallel_processor import get_parallel_processor, get_adaptive_batch_processor
from src.scheduler.load_processor import get_load_processor

log = logging.getLogger(__name__)


class OptimizedTokenProcessor:
    """
    Main optimized processor that coordinates parallel API calls with sequential scoring.
    """
    
    def __init__(self):
        self.load_processor = get_load_processor()
        self.adaptive_processor = get_adaptive_batch_processor()
        
    async def process_token_group(
        self,
        tokens: List[Token],
        client,
        repo: TokenRepository,
        scoring_service: ScoringService,
        group: str,
        min_score: float,
        min_score_change: float
    ) -> Tuple[int, int]:
        """
        Process a group of tokens with optimized parallel API calls and sequential scoring.
        
        Args:
            tokens: List of tokens to process
            client: DexScreener client (sync or async)
            repo: Token repository
            scoring_service: Scoring service
            group: Processing group name
            min_score: Minimum score threshold
            min_score_change: Minimum score change threshold
            
        Returns:
            Tuple of (processed_count, updated_count)
        """
        if not tokens:
            return 0, 0
        
        # Get system metrics for adaptive processing
        system_metrics = self.load_processor.get_current_load()
        
        # Filter tokens based on group-specific logic
        filtered_tokens = self._filter_tokens_by_group(tokens, repo, group, min_score)
        
        if not filtered_tokens:
            log.info(f"no_tokens_after_filtering", extra={
                "extra": {
                    "group": group,
                    "original_count": len(tokens),
                    "filtered_count": 0
                }
            })
            return 0, 0
        
        # Configure parallel processing based on system load and group
        max_concurrent = self._get_optimal_concurrency(group, system_metrics)
        timeout = self._get_optimal_timeout(group, system_metrics)
        
        # Get parallel processor
        parallel_processor = get_parallel_processor(max_concurrent, timeout)
        
        # Process API calls in parallel
        log.info(f"starting_parallel_processing", extra={
            "extra": {
                "group": group,
                "token_count": len(filtered_tokens),
                "max_concurrent": max_concurrent,
                "timeout": timeout
            }
        })
        
        start_time = datetime.now()
        results = await parallel_processor.process_token_batch(filtered_tokens, client, group)
        api_processing_time = (datetime.now() - start_time).total_seconds()
        
        # Record performance for adaptive sizing
        self.adaptive_processor.record_performance(len(filtered_tokens), api_processing_time)
        
        # Process scoring and database updates sequentially
        processed, updated = await self._process_scoring_results(
            results, repo, scoring_service, group, min_score_change
        )
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        log.info(f"group_processing_complete", extra={
            "extra": {
                "group": group,
                "total_tokens": len(filtered_tokens),
                "processed": processed,
                "updated": updated,
                "api_time": api_processing_time,
                "total_time": total_time,
                "tokens_per_second": len(filtered_tokens) / total_time if total_time > 0 else 0
            }
        })
        
        return processed, updated
    
    def _filter_tokens_by_group(
        self, 
        tokens: List[Token], 
        repo: TokenRepository, 
        group: str, 
        min_score: float
    ) -> List[Token]:
        """Filter tokens based on group-specific logic."""
        filtered_tokens = []
        
        # Batch load snapshots to avoid N+1 queries
        token_ids = [t.id for t in tokens]
        snapshots = repo.get_latest_snapshots_batch(token_ids)
        
        for t in tokens:
            snap = snapshots.get(t.id)
            last_score = float(snap.smoothed_score) if (snap and snap.smoothed_score is not None) else None
            if last_score is None:
                last_score = float(snap.score) if (snap and snap.score is not None) else None
            
            # Apply group-specific filtering logic
            if t.status == "active":
                # Active tokens: hot group gets high-scoring, cold group gets low-scoring
                is_hot = last_score is not None and last_score >= min_score
                if group == "hot" and not is_hot:
                    continue  # Low-scoring active tokens don't go to hot group
                if group == "cold":
                    continue  # Active tokens don't go to cold group
            else:
                # For monitoring tokens, use score-based filtering with activation priority
                if last_score is None:
                    # New monitoring tokens without scores go to cold group for activation check
                    if group == "hot":
                        continue
                else:
                    # High-scoring monitoring tokens should be processed more frequently
                    high_score_threshold = min_score * 2.0  # 2x min_score for priority processing
                    is_high_priority = last_score >= high_score_threshold
                    is_hot = last_score >= min_score
                    
                    if group == "hot":
                        # Hot group processes high-priority monitoring tokens + all active tokens
                        if not (is_hot or is_high_priority):
                            continue
                    elif group == "cold":
                        # Cold group processes low-priority monitoring tokens + activation checks
                        if is_hot and is_high_priority:
                            continue
                    
                    # Log high-priority monitoring tokens for debugging
                    if is_high_priority and t.status == "monitoring":
                        log.debug(f"processing_high_priority_monitoring_token", extra={
                            "extra": {
                                "mint": t.mint_address[:20] + "...",
                                "score": last_score,
                                "group": group,
                                "threshold": high_score_threshold
                            }
                        })
            
            filtered_tokens.append(t)
        
        return filtered_tokens
    
    def _get_optimal_concurrency(self, group: str, system_metrics: Dict[str, Any]) -> int:
        """Calculate optimal concurrency based on group and system load."""
        # Base concurrency levels
        base_concurrent = 8 if group == "hot" else 12  # More concurrent for cold group
        
        # Adjust based on system load
        cpu_percent = system_metrics.get("cpu_percent", 50)
        memory_percent = system_metrics.get("memory_percent", 50)
        
        if cpu_percent > 80 or memory_percent > 85:
            # High load - reduce concurrency significantly
            return max(3, base_concurrent // 3)
        elif cpu_percent > 60 or memory_percent > 70:
            # Medium load - reduce concurrency moderately
            return max(4, base_concurrent // 2)
        elif cpu_percent < 30 and memory_percent < 50:
            # Low load - increase concurrency
            return min(20, int(base_concurrent * 1.5))
        
        return base_concurrent
    
    def _get_optimal_timeout(self, group: str, system_metrics: Dict[str, Any]) -> float:
        """Calculate optimal timeout based on group and system performance."""
        # Base timeouts
        base_timeout = 3.0 if group == "hot" else 2.0  # Shorter timeout for cold group
        
        # Adjust based on recent API performance
        from src.monitoring.health_monitor import get_health_monitor
        health_monitor = get_health_monitor()
        api_stats = health_monitor.get_api_stats("dexscreener")
        
        if api_stats and api_stats.get("avg_response_time", 0) > 2000:  # > 2 seconds
            # API is slow, increase timeout slightly
            return min(base_timeout * 1.5, 5.0)
        elif api_stats and api_stats.get("avg_response_time", 0) < 500:  # < 0.5 seconds
            # API is fast, can use shorter timeout
            return max(base_timeout * 0.8, 1.0)
        
        return base_timeout
    
    async def _process_scoring_results(
        self,
        results,
        repo: TokenRepository,
        scoring_service: ScoringService,
        group: str,
        min_score_change: float
    ) -> Tuple[int, int]:
        """Process scoring results sequentially."""
        processed = 0
        updated = 0
        
        for result in results:
            if not result.success:
                log.warning("token_processing_failed", extra={
                    "extra": {
                        "group": group,
                        "mint": result.token.mint_address[:20] + "...",
                        "error": result.error
                    }
                })
                continue
            
            processed += 1
            t = result.token
            pairs = result.pairs
            
            if not pairs:
                continue
            
            try:
                # Get last score for comparison
                last_score = repo.get_latest_token_score(t.id)
                
                # Calculate score using unified scoring service
                score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(t, pairs)
                
                # Check if we should skip update due to minimal score change
                from src.domain.validation.data_filters import should_skip_score_update
                should_skip = should_skip_score_update(smoothed_score, last_score, min_score_change)
                
                # For active tokens, always update timestamp even if score didn't change significantly
                if should_skip and t.status == "active":
                    repo.update_token_timestamp(t.id)
                    log.debug("active_token_timestamp_updated", extra={
                        "extra": {
                            "symbol": t.symbol,
                            "mint": t.mint_address[:8],
                            "score_change": abs(score - (last_score or 0))
                        }
                    })
                    continue
                elif should_skip:
                    log.debug("score_update_skipped", extra={
                        "extra": {
                            "group": group,
                            "mint": t.mint_address,
                            "change": abs(score - (last_score or 0))
                        }
                    })
                    continue
                
                # Save score result
                snapshot_id = scoring_service.save_score_result(
                    token=t,
                    score=score,
                    smoothed_score=smoothed_score,
                    metrics=metrics,
                    raw_components=raw_components,
                    smoothed_components=smoothed_components
                )
                
                updated += 1
                
                # Log detailed information for debugging
                log.debug("token_score_updated", extra={
                    "extra": {
                        "group": group,
                        "mint": t.mint_address[:20] + "...",
                        "symbol": t.symbol,
                        "score": score,
                        "smoothed_score": smoothed_score,
                        "snapshot_id": snapshot_id
                    }
                })
                
            except Exception as e:
                log.error("scoring_failed", extra={
                    "extra": {
                        "group": group,
                        "mint": t.mint_address[:20] + "...",
                        "error": str(e)
                    }
                })
                continue
        
        return processed, updated


# Global instance
_optimized_processor = None


def get_optimized_processor() -> OptimizedTokenProcessor:
    """Get or create optimized processor instance."""
    global _optimized_processor
    if _optimized_processor is None:
        _optimized_processor = OptimizedTokenProcessor()
    return _optimized_processor