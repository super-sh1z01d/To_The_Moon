"""
Parallel processing integration for the main scheduler.
This module provides parallel token processing capabilities that can be
directly integrated into the main service.py without external dependencies.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import threading

log = logging.getLogger("parallel_integration")


class ParallelTokenProcessor:
    """
    Parallel token processor that can be integrated directly into service.py
    without requiring external dependencies.
    """
    
    def __init__(self, max_concurrent: int = 8, timeout: float = 5.0):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = None
        self._lock = threading.Lock()
    
    @property
    def executor(self):
        """Lazy initialization of thread pool executor."""
        if self._executor is None:
            with self._lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(
                        max_workers=self.max_concurrent,
                        thread_name_prefix="token_processor"
                    )
        return self._executor
    
    async def fetch_token_pairs_parallel(
        self, 
        tokens: List[Any], 
        client: Any
    ) -> Dict[str, Any]:
        """
        Fetch pairs for multiple tokens in parallel.
        
        Args:
            tokens: List of token objects with mint_address attribute
            client: DexScreener client instance
            
        Returns:
            Dict mapping mint_address to pairs data (or None if failed)
        """
        if not tokens:
            return {}
        
        log.info(f"Starting parallel pairs fetch for {len(tokens)} tokens")
        start_time = time.time()
        
        # Create tasks for parallel execution
        tasks = []
        for token in tokens:
            task = self._fetch_single_token_pairs(token.mint_address, client)
            tasks.append((token.mint_address, task))
        
        # Execute all tasks in parallel
        results = {}
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks], 
            return_exceptions=True
        )
        
        # Process results
        successful = 0
        failed = 0
        
        for (mint_address, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                log.warning(f"Failed to fetch pairs for {mint_address}: {result}")
                results[mint_address] = None
                failed += 1
            else:
                results[mint_address] = result
                if result is not None:
                    successful += 1
                else:
                    failed += 1
        
        total_time = time.time() - start_time
        log.info(
            f"Parallel pairs fetch completed: {successful} successful, "
            f"{failed} failed, {total_time:.2f}s total"
        )
        
        return results
    
    async def _fetch_single_token_pairs(self, mint_address: str, client: Any) -> Optional[Any]:
        """
        Fetch pairs for a single token with semaphore control.
        """
        async with self.semaphore:
            try:
                # Use asyncio.to_thread for thread pool execution
                pairs = await asyncio.wait_for(
                    asyncio.to_thread(client.get_pairs, mint_address),
                    timeout=self.timeout
                )
                return pairs
            except asyncio.TimeoutError:
                log.warning(f"Timeout fetching pairs for {mint_address}")
                return None
            except Exception as e:
                log.warning(f"Error fetching pairs for {mint_address}: {e}")
                return None
    
    def cleanup(self):
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)


# Global instance for reuse
_parallel_processor = None
_processor_lock = threading.Lock()


def get_parallel_processor(max_concurrent: int = 8, timeout: float = 5.0) -> ParallelTokenProcessor:
    """
    Get or create a parallel processor instance.
    """
    global _parallel_processor
    
    if _parallel_processor is None:
        with _processor_lock:
            if _parallel_processor is None:
                _parallel_processor = ParallelTokenProcessor(max_concurrent, timeout)
    
    return _parallel_processor


async def process_tokens_with_parallel_fetch(
    tokens: List[Any],
    client: Any,
    scoring_service: Any,
    repo: Any,
    group: str,
    min_score_change: float,
    max_concurrent: int = 8,
    timeout: float = 5.0
) -> Tuple[int, int]:
    """
    Process tokens with parallel pairs fetching.
    
    This function can be used as a drop-in replacement for the sequential
    token processing loop in service.py.
    
    Args:
        tokens: List of tokens to process
        client: DexScreener client
        scoring_service: Scoring service instance
        repo: Token repository
        group: Processing group name ("hot" or "cold")
        min_score_change: Minimum score change threshold
        max_concurrent: Maximum concurrent API calls
        timeout: Timeout for individual API calls
        
    Returns:
        Tuple of (processed_count, updated_count)
    """
    if not tokens:
        return 0, 0
    
    log.info(f"Processing {len(tokens)} tokens with parallel fetch (group: {group})")
    start_time = time.time()
    
    # Step 1: Fetch all pairs in parallel
    processor = get_parallel_processor(max_concurrent, timeout)
    pairs_data = await processor.fetch_token_pairs_parallel(tokens, client)
    
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
            # Get last score for comparison
            last_snapshot = repo.get_latest_score(token.id)
            last_score = last_snapshot.smoothed_score if last_snapshot else None
            
            # Calculate score using unified scoring service
            score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(token, pairs)
            
            # Check if we should skip update due to minimal score change
            from src.domain.validation.data_filters import should_skip_score_update
            should_skip = should_skip_score_update(smoothed_score, last_score, min_score_change)
            
            # For active tokens, always update timestamp even if score didn't change significantly
            if should_skip and token.status == "active":
                repo.update_token_timestamp(token.id)
                log.debug("active_token_timestamp_updated", extra={"extra": {"symbol": token.symbol, "mint": token.mint_address[:8], "score_change": abs(score - (last_score or 0))}})
                continue
            elif should_skip:
                log.debug("score_update_skipped", extra={"extra": {"group": group, "mint": token.mint_address, "change": abs(score - (last_score or 0))}})
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
            
            # Log successful update
            log.info("token_updated", extra={"extra": {
                "group": group,
                "mint": token.mint_address,
                "score": score,
                "smoothed_score": smoothed_score,
                "model": scoring_service.settings.get("scoring_model_active") or "legacy"
            }})
            
        except Exception as e:
            log.error(f"Error processing token {token.mint_address}: {e}")
            continue
    
    total_time = time.time() - start_time
    log.info(f"Parallel token processing complete: {processed} processed, {updated} updated, {total_time:.2f}s total")
    
    return processed, updated


def enable_parallel_processing_in_service():
    """
    Enable parallel processing in the main service.py by monkey-patching
    the _process_group function.
    
    This is a safe way to add parallel processing without modifying service.py directly.
    """
    try:
        from src.scheduler import service
        
        # Store original function
        original_process_group = service._process_group
        
        async def parallel_process_group(group: str) -> None:
            """
            Enhanced _process_group with parallel pairs fetching.
            """
            log.info(f"Starting parallel processing for {group} group")
            start_time = time.time()
            
            # Get all the same setup as original function
            with service.SessionLocal() as sess:
                from src.adapters.repositories.tokens_repo import TokensRepository
                from src.domain.settings.service import SettingsService
                from src.domain.scoring.scoring_service import ScoringService
                from src.adapters.services.dexscreener_client import DexScreenerClient
                
                repo = TokensRepository(sess)
                settings = SettingsService(sess)
                scoring_service = ScoringService(repo, settings)
                min_score = float(settings.get("min_score") or 0.1)
                min_score_change = float(settings.get("min_score_change") or 0.05)
                
                # Get client with appropriate timeout
                timeout = 5.0 if group == "hot" else 2.0
                client = DexScreenerClient(timeout=timeout)
                
                log.info(f"Using parallel DexScreener client with {timeout}s timeout", extra={"extra": {"group": group}})
                
                # Get tokens using same logic as original
                tokens = repo.get_tokens_for_processing(group, min_score)
                
                if not tokens:
                    log.info(f"No tokens to process for group {group}")
                    return
                
                log.info("processing_group", extra={"extra": {
                    "group": group,
                    "active_model": scoring_service.settings.get("scoring_model_active") or "legacy",
                    "tokens_count": len(tokens)
                }})
                
                # Use parallel processing
                max_concurrent = 8 if group == "hot" else 6  # Slightly different concurrency for different groups
                processed, updated = await process_tokens_with_parallel_fetch(
                    tokens=tokens,
                    client=client,
                    scoring_service=scoring_service,
                    repo=repo,
                    group=group,
                    min_score_change=min_score_change,
                    max_concurrent=max_concurrent,
                    timeout=timeout
                )
                
                # Log summary (same as original)
                total_time = time.time() - start_time
                log.info("group_summary", extra={"extra": {
                    "group": group,
                    "processed": processed,
                    "updated": updated,
                    "model": scoring_service.settings.get("scoring_model_active") or "legacy"
                }})
                
                # Record execution for monitoring
                try:
                    from src.scheduler.monitoring import record_group_execution
                    record_group_execution()
                except ImportError:
                    pass
                
                # Log scheduler execution metrics
                from src.monitoring.metrics import log_scheduler_execution
                batch_size = 70 if group == "cold" else 35  # Approximate batch sizes
                log_scheduler_execution({
                    'group': group,
                    'tokens_processed': processed,
                    'tokens_updated': updated,
                    'processing_time': total_time,
                    'error_count': 0,
                    'batch_size': batch_size
                })
        
        # Replace the function
        service._process_group = parallel_process_group
        
        log.info("✅ Parallel processing enabled in main scheduler service")
        return True
        
    except Exception as e:
        log.error(f"❌ Failed to enable parallel processing: {e}")
        return False