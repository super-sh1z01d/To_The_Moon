"""
Simple scheduler optimizations that work with existing architecture.
This version doesn't require load_processor or other missing modules.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
import psutil

from src.adapters.db.models import Token
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.scoring.scoring_service import ScoringService

log = logging.getLogger("simple_optimizations")


class SimpleParallelProcessor:
    """Simple parallel processor for API calls."""
    
    def __init__(self, max_concurrent: int = 8):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_tokens_parallel(
        self, 
        tokens: List[Token], 
        client, 
        group: str
    ) -> List[Tuple[Token, Any]]:
        """Process tokens in parallel and return results."""
        
        if not tokens:
            return []
        
        log.info(f"Processing {len(tokens)} tokens in parallel for {group} group")
        
        # Create tasks for parallel processing
        tasks = [
            self._process_single_token(token, client)
            for token in tokens
        ]
        
        # Execute with controlled concurrency
        results = []
        for i in range(0, len(tasks), self.max_concurrent):
            batch = tasks[i:i + self.max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
        
        # Filter successful results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.warning(f"Token processing failed: {result}")
                continue
            
            token = tokens[i]
            pairs = result
            successful_results.append((token, pairs))
        
        log.info(f"Successfully processed {len(successful_results)}/{len(tokens)} tokens")
        return successful_results
    
    async def _process_single_token(self, token: Token, client):
        """Process a single token with semaphore control."""
        async with self.semaphore:
            try:
                # Use async client if available, otherwise thread pool
                if hasattr(client, 'get_pairs_async'):
                    return await client.get_pairs_async(token.mint_address)
                else:
                    return await asyncio.to_thread(client.get_pairs, token.mint_address)
            except Exception as e:
                log.warning(f"Failed to get pairs for {token.mint_address}: {e}")
                raise


def get_system_load() -> Dict[str, float]:
    """Get current system load metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "available_memory_gb": memory.available / (1024**3)
        }
    except Exception as e:
        log.warning(f"Failed to get system metrics: {e}")
        return {"cpu_percent": 50, "memory_percent": 50, "available_memory_gb": 4}


def get_optimal_concurrency(group: str, system_load: Dict[str, float]) -> int:
    """Calculate optimal concurrency based on system load."""
    base_concurrent = 8 if group == "hot" else 12
    
    cpu_percent = system_load.get("cpu_percent", 50)
    memory_percent = system_load.get("memory_percent", 50)
    
    # Adjust based on system load
    if cpu_percent > 80 or memory_percent > 85:
        return max(3, base_concurrent // 3)
    elif cpu_percent > 60 or memory_percent > 70:
        return max(4, base_concurrent // 2)
    elif cpu_percent < 30 and memory_percent < 50:
        return min(16, int(base_concurrent * 1.5))
    
    return base_concurrent


async def process_group_optimized_simple(
    repo: TokensRepository,
    scoring_service: ScoringService,
    group: str,
    tokens: List[Token],
    client,
    min_score: float = 0.5,
    min_score_change: float = 0.01
) -> Tuple[int, int]:
    """
    Simple optimized processing that works with existing architecture.
    """
    if not tokens:
        return 0, 0
    
    start_time = time.time()
    
    # Get system load for optimization
    system_load = get_system_load()
    
    # Calculate optimal concurrency
    max_concurrent = get_optimal_concurrency(group, system_load)
    
    log.info(f"Starting optimized processing for {group} group", extra={
        "tokens": len(tokens),
        "max_concurrent": max_concurrent,
        "cpu_percent": system_load.get("cpu_percent"),
        "memory_percent": system_load.get("memory_percent")
    })
    
    # Process tokens in parallel
    parallel_processor = SimpleParallelProcessor(max_concurrent)
    
    try:
        # Get pairs in parallel
        api_start = time.time()
        token_pairs_results = await parallel_processor.process_tokens_parallel(
            tokens, client, group
        )
        api_time = time.time() - api_start
        
        log.info(f"Parallel API processing completed", extra={
            "group": group,
            "api_time": api_time,
            "successful_requests": len(token_pairs_results),
            "requests_per_second": len(token_pairs_results) / api_time if api_time > 0 else 0
        })
        
        # Process scoring sequentially (to maintain data consistency)
        processed = 0
        updated = 0
        
        for token, pairs in token_pairs_results:
            if pairs is None:
                continue
            
            processed += 1
            
            try:
                # Get last score for comparison
                last_snapshot = repo.get_latest_score(token.id)
                last_score = last_snapshot.smoothed_score if last_snapshot else None
                
                # Calculate score
                score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(token, pairs)
                
                # Check if we should skip update
                from src.domain.validation.data_filters import should_skip_score_update
                should_skip = should_skip_score_update(smoothed_score, last_score, min_score_change)
                
                if should_skip and token.status == "active":
                    repo.update_token_timestamp(token.id)
                    continue
                elif should_skip:
                    continue
                
                # Save score result
                scoring_service.save_score_result(
                    token=token,
                    score=score,
                    smoothed_score=smoothed_score,
                    metrics=metrics,
                    raw_components=raw_components,
                    smoothed_components=smoothed_components
                )
                
                updated += 1
                
            except Exception as e:
                log.error(f"Scoring failed for {token.mint_address}: {e}")
                continue
        
        total_time = time.time() - start_time
        
        log.info(f"Optimized group processing complete", extra={
            "group": group,
            "processed": processed,
            "updated": updated,
            "total_time": total_time,
            "api_time": api_time,
            "tokens_per_second": processed / total_time if total_time > 0 else 0,
            "speedup_estimate": f"{api_time / total_time * 100:.1f}% API time"
        })
        
        return processed, updated
        
    except Exception as e:
        log.error(f"Optimized processing failed for {group}: {e}")
        raise


def enable_simple_optimizations():
    """Enable simple optimizations by monkey-patching the original scheduler."""
    try:
        import src.scheduler.service as scheduler_service
        
        # Store original function
        original_process_group = scheduler_service._process_group
        
        async def optimized_process_group_wrapper(group: str):
            """Wrapper that adds parallel processing to existing logic."""
            
            # Get dependencies (same way as original function)
            from src.adapters.db.base import SessionLocal
            from src.adapters.repositories.tokens_repo import TokensRepository
            from src.domain.scoring.scoring_service import ScoringService
            from src.domain.settings.service import SettingsService
            
            with SessionLocal() as db:
                repo = TokensRepository(db)
                settings = SettingsService(db)
                scoring_service = ScoringService(repo, settings)
                
                # Get settings
                min_score = float(settings.get("min_score") or 0.1)
                min_score_change = float(settings.get("min_score_change") or 0.05)
                
                # Get system load
                system_load = get_system_load()
                
                # Use original logic for token selection and client setup
                # This ensures compatibility with existing code
                
                # Get tokens using existing logic
                from src.scheduler.priority_processor import get_priority_processor
                priority_processor = get_priority_processor()
                
                # Determine batch size (simplified)
                base_limit = 35 if group == "hot" else 70
                if system_load.get("cpu_percent", 50) > 70:
                    adjusted_limit = max(10, base_limit // 2)
                else:
                    adjusted_limit = base_limit
                
                tokens = priority_processor.get_prioritized_tokens(
                    repo, group, adjusted_limit, system_load
                )
                
                if not tokens:
                    return
                
                # Setup client (using existing logic)
                from src.core.config import get_config
                config = get_config()
                
                if config.app_env == "prod":
                    from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
                    timeout = 2.0 if group == "cold" else 5.0
                    client = ResilientDexScreenerClient(timeout=timeout, cache_ttl=30)
                else:
                    from src.adapters.services.dexscreener_client import DexScreenerClient
                    timeout = 2.0 if group == "cold" else 5.0
                    client = DexScreenerClient(timeout=timeout)
                
                # Use optimized processing
                processed, updated = await process_group_optimized_simple(
                    repo, scoring_service, group, tokens, client, min_score, min_score_change
                )
                
                log.info(f"Optimized {group} group processing complete: {processed} processed, {updated} updated")
        
        # Replace the original function
        scheduler_service._process_group = optimized_process_group_wrapper
        
        log.info("Simple scheduler optimizations enabled successfully")
        return True
        
    except Exception as e:
        log.error(f"Failed to enable simple optimizations: {e}")
        return False


# Global flag to track if optimizations are enabled
_optimizations_enabled = False


def is_optimizations_enabled() -> bool:
    """Check if optimizations are currently enabled."""
    return _optimizations_enabled


def set_optimizations_enabled(enabled: bool):
    """Set optimization status."""
    global _optimizations_enabled
    _optimizations_enabled = enabled