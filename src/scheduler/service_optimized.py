"""
Optimized scheduler service with parallel processing capabilities.
This is an enhanced version of the original scheduler with performance optimizations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Tuple

from src.adapters.repositories.tokens_repo import TokensRepository as TokenRepository
from src.domain.scoring.scoring_service import ScoringService
# load_processor will be imported inside functions with fallback
from src.scheduler.optimized_processor import get_optimized_processor
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.core.config import get_config

log = logging.getLogger("scheduler_optimized")


async def process_group_optimized(
    repo: TokenRepository,
    scoring_service: ScoringService,
    group: str,
    min_score: float = 0.5,
    min_score_change: float = 0.01
) -> Tuple[int, int]:
    """
    Optimized version of _process_group with parallel API calls and adaptive batching.
    
    Args:
        repo: Token repository
        scoring_service: Scoring service
        group: Processing group ("hot" or "cold")
        min_score: Minimum score threshold for filtering
        min_score_change: Minimum score change to trigger update
        
    Returns:
        Tuple of (processed_count, updated_count)
    """
    start_time = datetime.now()
    
    # Get system metrics and load processor with fallback
    try:
        from src.scheduler.load_processor import get_load_processor
        load_processor = get_load_processor()
    except ImportError:
        # Fallback implementation if load_processor doesn't exist
        class FallbackLoadProcessor:
            def get_adjusted_interval(self, base_interval):
                return base_interval
            def record_performance(self, *args, **kwargs):
                pass
            def get_current_load(self):
                return {"cpu_percent": 50, "memory_percent": 50}
            def get_adjusted_batch_size(self, base_limit):
                return base_limit
            def process_load_adjustment(self, *args, **kwargs):
                pass
        load_processor = FallbackLoadProcessor()
    
    system_metrics = load_processor.get_current_load()
    
    # Use adaptive batch sizing for better performance
    from src.scheduler.parallel_processor import get_adaptive_batch_processor
    adaptive_processor = get_adaptive_batch_processor()
    
    # Adjust batch size based on system load and token count
    base_limit = 35 if group == "hot" else 70  # Balanced batches for stable performance
    adjusted_limit = load_processor.get_adjusted_batch_size(base_limit)
    adaptive_limit = adaptive_processor.get_adaptive_batch_size(adjusted_limit, system_metrics)
    
    # Get priority-based token processing
    from src.scheduler.priority_processor import get_priority_processor
    priority_processor = get_priority_processor()
    
    # Get tokens with priority ordering
    tokens = priority_processor.get_prioritized_tokens(
        repo, group, adaptive_limit, system_metrics
    )
    
    # Process deferred tokens if system load is low (only for cold group to avoid conflicts)
    if group == "cold" and system_metrics.get("cpu_percent", 100) < 70:
        deferred_processed = priority_processor.process_deferred_tokens(repo, max_tokens=20)
        if deferred_processed > 0:
            log.info(f"processed_deferred_tokens", extra={
                "extra": {
                    "count": deferred_processed,
                    "group": group
                }
            })
    
    if not tokens:
        log.info(f"no_tokens_to_process", extra={
            "extra": {
                "group": group,
                "adaptive_limit": adaptive_limit
            }
        })
        return 0, 0
    
    # Use resilient client with circuit breaker in production
    config = get_config()
    
    if config.app_env == "prod":
        from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
        # Use shorter cache for hot tokens (more frequent updates)
        cache_ttl = 15 if group == "hot" else 30
        # Shorter timeout for cold group to process more tokens faster
        timeout = 2.0 if group == "cold" else 5.0
        client = ResilientDexScreenerClient(timeout=timeout, cache_ttl=cache_ttl)
        log.info(f"Using resilient DexScreener client with circuit breaker, {timeout}s timeout and {cache_ttl}s cache for {group} tokens")
    else:
        timeout = 2.0 if group == "cold" else 5.0
        client = DexScreenerClient(timeout=timeout)
        log.info(f"Using standard DexScreener client with {timeout}s timeout")
    
    # Get optimized processor and process tokens
    optimized_processor = get_optimized_processor()
    
    try:
        processed, updated = await optimized_processor.process_token_group(
            tokens=tokens,
            client=client,
            repo=repo,
            scoring_service=scoring_service,
            group=group,
            min_score=min_score,
            min_score_change=min_score_change
        )
        
        # Process load adjustment after processing
        processing_time = (datetime.now() - start_time).total_seconds()
        load_processor.process_load_adjustment(
            processed_count=processed,
            processing_time=processing_time,
            group=group,
            system_metrics=system_metrics
        )
        
        # Log performance metrics
        performance_metrics = {
            "cpu_usage": system_metrics.get("cpu_percent", 0),
            "memory_usage": system_metrics.get("memory_percent", 0),
            "processing_time": processing_time,
            "tokens_per_second": processed / processing_time if processing_time > 0 else 0,
            "update_rate": (updated / processed * 100) if processed > 0 else 0
        }
        
        log.info(f"optimized_group_processing_complete", extra={
            "extra": {
                "group": group,
                "processed": processed,
                "updated": updated,
                "performance": performance_metrics,
                "adaptive_limit": adaptive_limit,
                "original_limit": base_limit
            }
        })
        
        return processed, updated
        
    except Exception as e:
        log.error(f"optimized_group_processing_failed", extra={
            "extra": {
                "group": group,
                "error": str(e),
                "token_count": len(tokens)
            }
        })
        raise
    finally:
        # Clean up async client if needed
        if hasattr(client, 'close_async_client'):
            try:
                await client.close_async_client()
            except Exception as e:
                log.warning(f"Failed to close async client: {e}")


async def process_hot_tokens_optimized(
    repo: TokenRepository,
    scoring_service: ScoringService
) -> Tuple[int, int]:
    """Process hot tokens with optimized parallel processing."""
    return await process_group_optimized(repo, scoring_service, "hot")


async def process_cold_tokens_optimized(
    repo: TokenRepository,
    scoring_service: ScoringService
) -> Tuple[int, int]:
    """Process cold tokens with optimized parallel processing."""
    return await process_group_optimized(repo, scoring_service, "cold")


def enable_optimized_scheduler():
    """
    Enable optimized scheduler by replacing the original functions.
    This allows for gradual rollout and easy rollback.
    """
    try:
        # Try to use full optimizations first
        import src.scheduler.service as original_service
        
        # Replace original functions with optimized versions
        original_service._process_group = process_group_optimized
        original_service.process_hot_tokens = process_hot_tokens_optimized
        original_service.process_cold_tokens = process_cold_tokens_optimized
        
        log.info("Full optimized scheduler enabled - using parallel processing")
        
    except ImportError as e:
        # Fallback to simple optimizations if modules are missing
        log.warning(f"Full optimizations unavailable ({e}), using simple optimizations")
        
        from src.scheduler.simple_optimizations import enable_simple_optimizations, set_optimizations_enabled
        
        if enable_simple_optimizations():
            set_optimizations_enabled(True)
            log.info("Simple scheduler optimizations enabled - using parallel API calls")
        else:
            log.error("Failed to enable any optimizations")
            raise


def disable_optimized_scheduler():
    """
    Disable optimized scheduler and revert to original implementation.
    """
    # This would require storing original functions, but for now just log
    log.warning("Optimized scheduler disable requested - restart required to revert")


# Configuration flag to enable/disable optimized scheduler
ENABLE_OPTIMIZED_SCHEDULER = True

if ENABLE_OPTIMIZED_SCHEDULER:
    # Auto-enable optimized scheduler on import
    try:
        enable_optimized_scheduler()
        log.info("Optimized scheduler auto-enabled")
    except Exception as e:
        log.error(f"Failed to enable optimized scheduler: {e}")
        log.info("Falling back to original scheduler")