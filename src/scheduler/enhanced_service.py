"""
Enhanced scheduler service with integrated parallel processing.
This module provides a direct replacement for the sequential processing
in the main service.py without requiring external dependencies.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

log = logging.getLogger("enhanced_service")


async def process_group_with_parallel_fetch(group: str) -> None:
    """
    Enhanced _process_group function with integrated parallel processing.
    This is a direct replacement for the original _process_group function
    that adds parallel API fetching while maintaining all existing logic.
    """
    log.info(f"Starting enhanced processing for {group} group")
    start_time = datetime.now(timezone.utc)
    
    # Import dependencies (same as original)
    from src.adapters.db.base import SessionLocal
    from src.adapters.repositories.tokens_repo import TokensRepository
    from src.domain.settings.service import SettingsService
    from src.domain.scoring.scoring_service import ScoringService
    from src.adapters.services.dexscreener_client import DexScreenerClient
    
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        scoring_service = ScoringService(repo, settings)
        min_score = float(settings.get("min_score") or 0.1)
        min_score_change = float(settings.get("min_score_change") or 0.05)
        
        # Get client with appropriate timeout (same logic as original)
        timeout = 5.0 if group == "hot" else 2.0
        client = DexScreenerClient(timeout=timeout)
        
        log.info(f"Using enhanced DexScreener client with {timeout}s timeout", extra={"extra": {"group": group}})
        
        # Get system metrics and load processor (same logic as original)
        try:
            from src.monitoring.metrics import get_load_processor
            load_processor = get_load_processor()
            system_metrics = load_processor.get_current_load()
        except ImportError:
            # Fallback if load processor not available
            system_metrics = {"cpu_percent": 50, "memory_percent": 50}
            
        # Get priority-based token processing (same logic as original)
        from src.scheduler.priority_processor import get_priority_processor
        priority_processor = get_priority_processor()
        
        # Adjust batch size based on system load
        base_limit = 35 if group == "hot" else 70
        try:
            adjusted_limit = load_processor.get_adjusted_batch_size(base_limit)
        except:
            adjusted_limit = base_limit
            
        # Get tokens with priority ordering (same logic as original)
        tokens = priority_processor.get_prioritized_tokens(
            repo, group, adjusted_limit, system_metrics
        )
        
        if not tokens:
            log.info(f"No tokens to process for group {group}")
            return
        
        log.info("processing_group", extra={"extra": {
            "group": group,
            "active_model": settings.get("scoring_model_active") or "legacy",
            "tokens_count": len(tokens)
        }})
        
        # Enhanced: Parallel pairs fetching
        processed, updated = await _process_tokens_parallel(
            tokens=tokens,
            client=client,
            scoring_service=scoring_service,
            repo=repo,
            group=group,
            min_score_change=min_score_change,
            max_concurrent=8 if group == "hot" else 6
        )
        
        # Log summary (same as original)
        log.info("group_summary", extra={"extra": {
            "group": group,
            "processed": processed,
            "updated": updated,
            "model": settings.get("scoring_model_active") or "legacy"
        }})
        
        # Record execution for monitoring (same as original)
        try:
            from src.scheduler.monitoring import record_group_execution
            record_group_execution()
        except ImportError:
            pass
        
        # Log scheduler execution metrics (same as original)
        try:
            from src.monitoring.metrics import log_scheduler_execution
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            batch_size = 70 if group == "cold" else 35
            
            log_scheduler_execution({
                'group': group,
                'tokens_processed': processed,
                'tokens_updated': updated,
                'processing_time': processing_time,
                'error_count': 0,
                'batch_size': batch_size
            })
        except ImportError:
            # Fallback logging if metrics module not available
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            log.info(f"Enhanced scheduler execution: {group} group, {processed} processed, {updated} updated, {processing_time:.2f}s")


async def _process_tokens_parallel(
    tokens: List[Any],
    client: Any,
    scoring_service: Any,
    repo: Any,
    group: str,
    min_score_change: float,
    max_concurrent: int = 8
) -> Tuple[int, int]:
    """
    Process tokens with parallel pairs fetching.
    This replaces the sequential loop in the original _process_group.
    """
    if not tokens:
        return 0, 0
    
    log.info(f"Processing {len(tokens)} tokens with parallel fetch (max_concurrent={max_concurrent})")
    
    # Step 1: Fetch all pairs in parallel
    pairs_data = await _fetch_pairs_parallel(tokens, client, max_concurrent)
    
    # Step 2: Process tokens sequentially (scoring and DB operations)
    processed = 0
    updated = 0
    
    for token in tokens:
        processed += 1
        
        # Get pairs data from parallel fetch
        pairs = pairs_data.get(token.mint_address)
        if pairs is None:
            log.warning("pairs_fetch_failed", extra={"extra": {"group": group, "mint": token.mint_address}})
            continue
        
        try:
            # Get last score for comparison (same logic as original)
            last_snapshot = repo.get_latest_score(token.id)
            last_score = last_snapshot.smoothed_score if last_snapshot else None
            
            # Calculate score using unified scoring service (same as original)
            score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(token, pairs)
            
            # Check if we should skip update (same logic as original)
            from src.domain.validation.data_filters import should_skip_score_update
            should_skip = should_skip_score_update(smoothed_score, last_score, min_score_change)
            
            # Handle active tokens timestamp updates (same logic as original)
            if should_skip and token.status == "active":
                repo.update_token_timestamp(token.id)
                log.debug("active_token_timestamp_updated", extra={"extra": {
                    "symbol": token.symbol, 
                    "mint": token.mint_address[:8], 
                    "score_change": abs(score - (last_score or 0))
                }})
                continue
            elif should_skip:
                log.debug("score_update_skipped", extra={"extra": {
                    "group": group, 
                    "mint": token.mint_address, 
                    "change": abs(score - (last_score or 0))
                }})
                continue
            
            # Save score result (same as original)
            scoring_service.save_score_result(
                token=token,
                score=score,
                smoothed_score=smoothed_score,
                metrics=metrics,
                raw_components=raw_components,
                smoothed_components=smoothed_components
            )
            
            updated += 1
            
            # Log successful update (enhanced with more details)
            log.info("token_updated", extra={"extra": {
                "group": group,
                "mint": token.mint_address,
                "score": score,
                "smoothed_score": smoothed_score,
                "model": scoring_service.settings.get("scoring_model_active") or "legacy",
                "L_tot": metrics.get("L_tot"),
                "n_5m": metrics.get("n_5m"),
                "filtered_pools": metrics.get("filtered_pools"),
                "data_quality_ok": metrics.get("data_quality_ok", True)
            }})
            
        except Exception as e:
            log.error(f"Error processing token {token.mint_address}: {e}")
            continue
    
    return processed, updated


async def _fetch_pairs_parallel(
    tokens: List[Any], 
    client: Any, 
    max_concurrent: int = 8
) -> Dict[str, Any]:
    """
    Fetch pairs for multiple tokens in parallel using semaphore control.
    """
    if not tokens:
        return {}
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_single_token(token):
        async with semaphore:
            try:
                pairs = await asyncio.to_thread(client.get_pairs, token.mint_address)
                return token.mint_address, pairs
            except Exception as e:
                log.warning(f"Failed to fetch pairs for {token.mint_address}: {e}")
                return token.mint_address, None
    
    # Execute all fetches in parallel
    tasks = [fetch_single_token(token) for token in tokens]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    pairs_data = {}
    successful = 0
    failed = 0
    
    for result in results:
        if isinstance(result, Exception):
            log.warning(f"Exception in parallel fetch: {result}")
            failed += 1
        else:
            mint_address, pairs = result
            pairs_data[mint_address] = pairs
            if pairs is not None:
                successful += 1
            else:
                failed += 1
    
    log.info(f"Parallel fetch completed: {successful} successful, {failed} failed")
    return pairs_data


def enable_enhanced_scheduler():
    """
    Enable enhanced scheduler with parallel processing.
    This replaces the original _process_group function with the enhanced version.
    """
    try:
        import src.scheduler.service as scheduler_service
        
        # Store original function for potential rollback
        if not hasattr(scheduler_service, '_original_process_group'):
            scheduler_service._original_process_group = scheduler_service._process_group
        
        # Replace with enhanced version
        scheduler_service._process_group = process_group_with_parallel_fetch
        
        log.info("✅ Enhanced scheduler with parallel processing enabled")
        return True
        
    except Exception as e:
        log.error(f"❌ Failed to enable enhanced scheduler: {e}")
        return False


def disable_enhanced_scheduler():
    """
    Disable enhanced scheduler and restore original function.
    """
    try:
        import src.scheduler.service as scheduler_service
        
        if hasattr(scheduler_service, '_original_process_group'):
            scheduler_service._process_group = scheduler_service._original_process_group
            log.info("✅ Enhanced scheduler disabled, original restored")
            return True
        else:
            log.warning("No original function found to restore")
            return False
            
    except Exception as e:
        log.error(f"❌ Failed to disable enhanced scheduler: {e}")
        return False