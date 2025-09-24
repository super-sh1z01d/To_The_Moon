"""
Resilient DexScreener API client with circuit breaker and retry mechanisms.

This module provides a robust wrapper around the DexScreener API that includes:
- Circuit breaker pattern for handling API failures
- Retry logic with exponential backoff
- Caching for fallback scenarios
- Comprehensive error handling and monitoring
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from functools import wraps

import httpx

from src.monitoring.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from src.monitoring.retry_manager import get_retry_manager, RetryableError, NonRetryableError, CommonRetryPolicies
from src.monitoring.config import get_circuit_breaker_config, get_recovery_config
from .dexscreener_client import DexScreenerClient

log = logging.getLogger("resilient_dexscreener")


class DexScreenerAPIError(Exception):
    """Base exception for DexScreener API errors."""
    pass


class DexScreenerRateLimitError(RetryableError):
    """Exception for rate limiting errors (429)."""
    pass


class DexScreenerTimeoutError(RetryableError):
    """Exception for timeout errors."""
    pass


class DexScreenerConnectionError(RetryableError):
    """Exception for connection errors."""
    pass


class DexScreenerInvalidResponseError(NonRetryableError):
    """Exception for invalid response format."""
    pass


class DexScreenerNotFoundError(NonRetryableError):
    """Exception for 404 errors."""
    pass


class APICache:
    """Simple in-memory cache for API responses."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if datetime.utcnow() > entry['expires_at']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any):
        """Set cached value with TTL."""
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        }
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)


class ResilientDexScreenerClient:
    """
    Resilient DexScreener API client with circuit breaker, retry, and caching.
    
    This client wraps the original DexScreenerClient with additional resilience features:
    - Circuit breaker to prevent cascading failures
    - Retry logic with exponential backoff for transient errors
    - Response caching for fallback scenarios
    - Comprehensive error classification and handling
    """
    
    def __init__(
        self,
        timeout: float = 10.0,
        cache_ttl: int = 300,
        enable_circuit_breaker: bool = True,
        enable_retry: bool = True,
        enable_cache: bool = True
    ):
        self.timeout = timeout
        self.enable_circuit_breaker = enable_circuit_breaker
        self.enable_retry = enable_retry
        self.enable_cache = enable_cache
        
        # Initialize underlying client
        self._client = DexScreenerClient(timeout=timeout)
        
        # Initialize resilience components
        if self.enable_circuit_breaker:
            self._circuit_breaker = get_circuit_breaker(
                "dexscreener_api",
                get_circuit_breaker_config()
            )
        
        if self.enable_retry:
            self._retry_manager = get_retry_manager(
                "dexscreener_api",
                CommonRetryPolicies.api_calls()
            )
        
        if self.enable_cache:
            self._cache = APICache(ttl_seconds=cache_ttl)
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'circuit_breaker_trips': 0,
            'retry_attempts': 0,
            'successful_requests': 0,
            'failed_requests': 0
        }
        
        log.info("Resilient DexScreener client initialized", extra={
            "timeout": timeout,
            "cache_ttl": cache_ttl,
            "circuit_breaker_enabled": enable_circuit_breaker,
            "retry_enabled": enable_retry,
            "cache_enabled": enable_cache
        })
    
    def get_pairs(self, mint: str) -> Optional[list[dict[str, Any]]]:
        """
        Get token pairs with full resilience features.
        
        Args:
            mint: Token mint address
            
        Returns:
            List of token pairs or None if unavailable
        """
        self._stats['total_requests'] += 1
        
        # Check cache first
        if self.enable_cache:
            cached_result = self._cache.get(mint)
            if cached_result is not None:
                self._stats['cache_hits'] += 1
                log.debug(f"Cache hit for mint {mint}")
                return cached_result
            self._stats['cache_misses'] += 1
        
        try:
            # Execute with resilience features
            result = self._execute_with_resilience(mint)
            
            # Cache successful results
            if self.enable_cache and result is not None:
                self._cache.set(mint, result)
            
            self._stats['successful_requests'] += 1
            return result
            
        except CircuitBreakerOpenError:
            self._stats['circuit_breaker_trips'] += 1
            log.warning(f"Circuit breaker open for DexScreener API, mint: {mint}")
            
            # Try to return cached result as fallback
            if self.enable_cache:
                cached_result = self._cache.get(mint)
                if cached_result is not None:
                    log.info(f"Returning stale cached result for mint {mint}")
                    return cached_result
            
            return None
            
        except Exception as e:
            self._stats['failed_requests'] += 1
            log.error(f"Failed to get pairs for mint {mint}: {e}")
            
            # Try to return cached result as fallback
            if self.enable_cache:
                cached_result = self._cache.get(mint)
                if cached_result is not None:
                    log.info(f"Returning stale cached result after error for mint {mint}")
                    return cached_result
            
            return None
    
    def _execute_with_resilience(self, mint: str) -> Optional[list[dict[str, Any]]]:
        """Execute API call with circuit breaker and retry."""
        def api_call():
            return self._make_api_call(mint)
        
        # Apply circuit breaker if enabled
        if self.enable_circuit_breaker:
            if self.enable_retry:
                # Both circuit breaker and retry
                return self._circuit_breaker.call(
                    lambda: self._retry_manager.execute(api_call)
                )
            else:
                # Only circuit breaker
                return self._circuit_breaker.call(api_call)
        elif self.enable_retry:
            # Only retry
            return self._retry_manager.execute(api_call)
        else:
            # No resilience features
            return api_call()
    
    def _make_api_call(self, mint: str) -> Optional[list[dict[str, Any]]]:
        """Make the actual API call with proper error classification."""
        url = self._client._build_url(mint)
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                start_time = time.time()
                resp = client.get(url)
                duration = time.time() - start_time
                
                log.debug(f"DexScreener API call completed", extra={
                    "mint": mint,
                    "status_code": resp.status_code,
                    "duration": duration
                })
                
                # Handle different response codes
                if resp.status_code == 200:
                    return self._parse_response(resp, mint)
                elif resp.status_code == 404:
                    # Not found is not an error, just no pairs
                    log.debug(f"No pairs found for mint {mint}")
                    return []
                elif resp.status_code == 429:
                    # Rate limiting - retryable
                    raise DexScreenerRateLimitError(f"Rate limited for mint {mint}")
                elif resp.status_code >= 500:
                    # Server errors - retryable
                    raise DexScreenerAPIError(f"Server error {resp.status_code} for mint {mint}")
                elif resp.status_code >= 400:
                    # Client errors (except 404, 429) - non-retryable
                    raise DexScreenerInvalidResponseError(f"Client error {resp.status_code} for mint {mint}")
                else:
                    # Unexpected status codes
                    raise DexScreenerAPIError(f"Unexpected status {resp.status_code} for mint {mint}")
                    
        except httpx.TimeoutException:
            raise DexScreenerTimeoutError(f"Timeout for mint {mint}")
        except httpx.ConnectError:
            raise DexScreenerConnectionError(f"Connection error for mint {mint}")
        except httpx.HTTPError as e:
            raise DexScreenerConnectionError(f"HTTP error for mint {mint}: {e}")
        except Exception as e:
            # Unexpected errors - treat as retryable
            raise DexScreenerAPIError(f"Unexpected error for mint {mint}: {e}")
    
    def _parse_response(self, resp: httpx.Response, mint: str) -> Optional[list[dict[str, Any]]]:
        """Parse API response with error handling."""
        try:
            data = resp.json()
        except Exception as e:
            raise DexScreenerInvalidResponseError(f"Invalid JSON response for mint {mint}: {e}")
        
        # Handle different response formats
        if isinstance(data, list):
            pairs = data
        elif isinstance(data, dict):
            pairs = data.get("pairs")
        else:
            raise DexScreenerInvalidResponseError(f"Unexpected response format for mint {mint}")
        
        if not isinstance(pairs, list):
            log.debug(f"No pairs in response for mint {mint}")
            return []
        
        return pairs
    
    async def get_pairs_async(self, mint: str) -> Optional[list[dict[str, Any]]]:
        """
        Async version of get_pairs.
        
        Args:
            mint: Token mint address
            
        Returns:
            List of token pairs or None if unavailable
        """
        # For now, run sync version in thread pool
        # In a real implementation, you might want to use httpx.AsyncClient
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_pairs, mint)
    
    def is_healthy(self) -> bool:
        """Check if the API client is healthy."""
        if not self.enable_circuit_breaker:
            return True
        
        return self._circuit_breaker.is_closed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self._stats.copy()
        
        # Add cache stats
        if self.enable_cache:
            stats['cache_size'] = self._cache.size()
            stats['cache_hit_rate'] = (
                (stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) * 100)
                if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0
            )
        
        # Add circuit breaker stats
        if self.enable_circuit_breaker:
            stats['circuit_breaker'] = self._circuit_breaker.get_stats()
        
        # Add retry stats
        if self.enable_retry:
            stats['retry_manager'] = self._retry_manager.get_stats()
        
        return stats
    
    def reset_stats(self):
        """Reset all statistics."""
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'circuit_breaker_trips': 0,
            'retry_attempts': 0,
            'successful_requests': 0,
            'failed_requests': 0
        }
        
        if self.enable_retry:
            self._retry_manager.reset_stats()
    
    def clear_cache(self):
        """Clear the response cache."""
        if self.enable_cache:
            self._cache.clear()
            log.info("DexScreener API cache cleared")
    
    def force_circuit_breaker_open(self):
        """Manually force circuit breaker to open state (for testing)."""
        if self.enable_circuit_breaker:
            self._circuit_breaker.force_open()
            log.warning("DexScreener circuit breaker manually forced open")
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker to closed state."""
        if self.enable_circuit_breaker:
            self._circuit_breaker.reset()
            log.info("DexScreener circuit breaker manually reset")


# Global resilient client instance
_resilient_client: Optional[ResilientDexScreenerClient] = None


def get_resilient_dexscreener_client() -> ResilientDexScreenerClient:
    """Get global resilient DexScreener client instance."""
    global _resilient_client
    if _resilient_client is None:
        _resilient_client = ResilientDexScreenerClient(cache_ttl=30)
    return _resilient_client


def create_resilient_dexscreener_client(**kwargs) -> ResilientDexScreenerClient:
    """Create a new resilient DexScreener client with custom configuration."""
    return ResilientDexScreenerClient(**kwargs)