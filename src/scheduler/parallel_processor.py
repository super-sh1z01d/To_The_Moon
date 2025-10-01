"""
Parallel token processing for scheduler optimization.
Handles batch processing of tokens with concurrent API calls.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from src.adapters.db.models import Token
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient

log = logging.getLogger(__name__)


@dataclass
class TokenProcessingResult:
    """Result of processing a single token"""
    token: Token
    pairs: Optional[List[Dict[str, Any]]]
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0


class ParallelTokenProcessor:
    """Handles parallel processing of tokens with configurable concurrency"""
    
    def __init__(self, max_concurrent: int = 8, timeout: float = 5.0):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def process_token_batch(
        self, 
        tokens: List[Token], 
        client: DexScreenerClient,
        group: str = "unknown"
    ) -> List[TokenProcessingResult]:
        """
        Process a batch of tokens in parallel with controlled concurrency
        
        Args:
            tokens: List of tokens to process
            client: DexScreener client (can be resilient or standard)
            group: Processing group name for logging
            
        Returns:
            List of processing results
        """
        if not tokens:
            return []
            
        log.info(
            "parallel_batch_start",
            extra={"extra": {"group": group, "token_count": len(tokens)}}
        )

        from src.adapters.services.dexscreener_batch_client import get_batch_client

        batch_client = await get_batch_client()
        mints = [token.mint_address for token in tokens]

        start_time = datetime.now()
        pairs_map = await batch_client.get_pairs_for_mints(mints)
        processing_time = (datetime.now() - start_time).total_seconds()

        processed_results = []
        for token in tokens:
            pairs = pairs_map.get(token.mint_address)
            if pairs is None:
                processed_results.append(
                    TokenProcessingResult(
                        token,
                        None,
                        False,
                        "request_failed",
                        processing_time
                    )
                )
            else:
                processed_results.append(
                    TokenProcessingResult(
                        token,
                        pairs,
                        True,
                        None,
                        processing_time
                    )
                )

        successful = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - successful

        log.info(
            "parallel_batch_complete",
            extra={
                "extra": {
                    "group": group,
                    "total_tokens": len(tokens),
                    "successful": successful,
                    "failed": failed,
                    "processing_time": processing_time,
                    "tokens_per_second": len(tokens) / processing_time if processing_time > 0 else 0,
                }
            },
        )

        return processed_results
    
    async def _process_single_token(
        self, 
        token: Token, 
        client: DexScreenerClient,
        group: str
    ) -> TokenProcessingResult:
        """Process a single token with semaphore control and rate limiting"""
        
        async with self.semaphore:
            start_time = datetime.now()
            
            try:
                # Add delay to avoid rate limiting (1s between requests)
                await asyncio.sleep(1.0)
                
                # Use async client if available, otherwise use thread pool
                if hasattr(client, 'get_pairs_async'):
                    pairs = await client.get_pairs_async(token.mint_address)
                else:
                    # Fallback to thread pool for sync clients
                    pairs = await asyncio.to_thread(client.get_pairs, token.mint_address)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if pairs is None:
                    return TokenProcessingResult(
                        token, 
                        None, 
                        False, 
                        "no_pairs_returned",
                        processing_time
                    )
                
                return TokenProcessingResult(
                    token, 
                    pairs, 
                    True, 
                    None,
                    processing_time
                )
                
            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds()
                log.warning(f"token_processing_failed", extra={
                    "extra": {
                        "group": group,
                        "mint": token.mint_address[:20] + "...",
                        "error": str(e),
                        "processing_time": processing_time
                    }
                })
                
                return TokenProcessingResult(
                    token, 
                    None, 
                    False, 
                    str(e),
                    processing_time
                )


class AdaptiveBatchProcessor:
    """Manages adaptive batch sizing based on performance metrics"""
    
    def __init__(self, initial_batch_size: int = 35):
        self.current_batch_size = initial_batch_size
        self.min_batch_size = 10
        self.max_batch_size = 100
        self.performance_history = []
        self.max_history = 10
        
    def get_adaptive_batch_size(self, base_limit: int, system_metrics: Dict[str, Any]) -> int:
        """
        Calculate adaptive batch size based on system performance and load
        
        Args:
            base_limit: Base batch size limit
            system_metrics: Current system metrics
            
        Returns:
            Optimized batch size
        """
        cpu_percent = system_metrics.get("cpu_percent", 50)
        memory_percent = system_metrics.get("memory_percent", 50)
        
        # Start with base limit
        adaptive_size = base_limit
        
        # Adjust based on system load
        if cpu_percent < 30 and memory_percent < 60:
            # System has capacity, increase batch size
            adaptive_size = min(int(base_limit * 1.5), self.max_batch_size)
        elif cpu_percent > 70 or memory_percent > 80:
            # System under load, decrease batch size
            adaptive_size = max(int(base_limit * 0.7), self.min_batch_size)
        
        # Adjust based on recent performance
        if len(self.performance_history) >= 3:
            avg_tokens_per_second = sum(self.performance_history[-3:]) / 3
            
            if avg_tokens_per_second > 2.0:  # Good performance
                adaptive_size = min(adaptive_size + 5, self.max_batch_size)
            elif avg_tokens_per_second < 0.5:  # Poor performance
                adaptive_size = max(adaptive_size - 10, self.min_batch_size)
        
        self.current_batch_size = adaptive_size
        
        log.debug(f"adaptive_batch_size", extra={
            "extra": {
                "base_limit": base_limit,
                "adaptive_size": adaptive_size,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "recent_performance": self.performance_history[-3:] if self.performance_history else []
            }
        })
        
        return adaptive_size
    
    def record_performance(self, tokens_processed: int, processing_time: float):
        """Record performance metrics for adaptive sizing"""
        if processing_time > 0:
            tokens_per_second = tokens_processed / processing_time
            self.performance_history.append(tokens_per_second)
            
            # Keep only recent history
            if len(self.performance_history) > self.max_history:
                self.performance_history = self.performance_history[-self.max_history:]


# Global instances
_parallel_processor = None
_adaptive_batch_processor = None


def get_parallel_processor(max_concurrent: int = 8, timeout: float = 5.0) -> ParallelTokenProcessor:
    """Get or create parallel processor instance"""
    global _parallel_processor
    if (
        _parallel_processor is None
        or _parallel_processor.max_concurrent != max_concurrent
        or _parallel_processor.timeout != timeout
    ):
        _parallel_processor = ParallelTokenProcessor(max_concurrent, timeout)
    return _parallel_processor


def get_adaptive_batch_processor(initial_batch_size: int = 35) -> AdaptiveBatchProcessor:
    """Get or create adaptive batch processor instance"""
    global _adaptive_batch_processor
    if (
        _adaptive_batch_processor is None
        or _adaptive_batch_processor.current_batch_size != initial_batch_size
    ):
        _adaptive_batch_processor = AdaptiveBatchProcessor(initial_batch_size)
    return _adaptive_batch_processor
