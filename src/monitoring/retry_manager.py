"""
Retry manager with exponential backoff for resilient API calls.

This module provides retry mechanisms with configurable backoff strategies,
jitter, and failure classification to handle transient failures gracefully.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar, Union, Type, Tuple
from functools import wraps
from enum import Enum

from .models import RecoveryConfig
from .config import get_recovery_config

log = logging.getLogger("retry_manager")

T = TypeVar('T')


class RetryStrategy(str, Enum):
    """Retry strategy types."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


class RetryError(Exception):
    """Base exception for retry-related errors."""
    
    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


class MaxRetriesExceededError(RetryError):
    """Exception raised when maximum retry attempts are exceeded."""
    pass


class RetryableError(Exception):
    """Base class for exceptions that should trigger retries."""
    pass


class NonRetryableError(Exception):
    """Base class for exceptions that should not trigger retries."""
    pass


class RetryPolicy:
    """
    Defines retry behavior including strategy, delays, and failure classification.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER,
        jitter_factor: float = 0.1,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.strategy = strategy
        self.jitter_factor = jitter_factor
        self.retryable_exceptions = retryable_exceptions or (Exception,)
        self.non_retryable_exceptions = non_retryable_exceptions or ()
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        elif self.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
            # Add jitter to prevent thundering herd
            jitter = delay * self.jitter_factor * random.random()
            delay += jitter
        else:
            delay = self.base_delay
        
        return min(max(delay, 0.0), self.max_delay)  # Ensure delay is non-negative
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry."""
        # Note: We don't check max_attempts here because that's handled in the retry manager
        # This method only determines if the exception type is retryable
        
        # Check custom error types first
        if isinstance(exception, NonRetryableError):
            return False
        
        if isinstance(exception, RetryableError):
            return True
        
        # Check non-retryable exceptions
        if isinstance(exception, self.non_retryable_exceptions):
            return False
        
        # Check retryable exceptions
        if isinstance(exception, self.retryable_exceptions):
            return True
        
        # For unknown exceptions, check if they're in common retryable categories
        retryable_types = (
            ConnectionError,
            TimeoutError,
            OSError,  # Network-related errors
        )
        
        return isinstance(exception, retryable_types)


class RetryManager:
    """
    Manages retry logic with configurable policies and detailed tracking.
    """
    
    def __init__(self, name: str, policy: Optional[RetryPolicy] = None):
        self.name = name
        self.policy = policy or self._create_default_policy()
        
        # Statistics
        self._total_calls = 0
        self._total_retries = 0
        self._total_successes = 0
        self._total_failures = 0
        self._retry_attempts_histogram = {}  # attempt_count -> frequency
        
        log.info(f"Retry manager '{name}' initialized", extra={
            "retry_manager": name,
            "max_attempts": self.policy.max_attempts,
            "strategy": self.policy.strategy.value,
            "base_delay": self.policy.base_delay
        })
    
    def _create_default_policy(self) -> RetryPolicy:
        """Create default retry policy from configuration."""
        config = get_recovery_config()
        
        return RetryPolicy(
            max_attempts=config.max_retries,
            base_delay=config.base_retry_delay,
            max_delay=config.max_retry_delay,
            exponential_base=config.retry_exponential_base,
            strategy=RetryStrategy.EXPONENTIAL_JITTER
        )
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            MaxRetriesExceededError: If all retry attempts are exhausted
            Any non-retryable exception raised by the function
        """
        self._total_calls += 1
        last_exception = None
        
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                
                # Record success
                duration = time.time() - start_time
                self._record_success(attempt, duration)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.policy.should_retry(e, attempt):
                    self._record_failure(attempt, str(e), retryable=False)
                    raise
                
                # If this is the last attempt, don't sleep and retry
                if attempt < self.policy.max_attempts:
                    # Calculate delay and wait
                    delay = self.policy.calculate_delay(attempt)
                    
                    log.warning(f"Retry attempt {attempt} for '{self.name}' failed", extra={
                        "retry_manager": self.name,
                        "attempt": attempt,
                        "max_attempts": self.policy.max_attempts,
                        "error": str(e),
                        "delay": delay
                    })
                    
                    time.sleep(delay)
                    self._total_retries += 1
                else:
                    # This was the last attempt, log and break
                    log.warning(f"Final retry attempt {attempt} for '{self.name}' failed", extra={
                        "retry_manager": self.name,
                        "attempt": attempt,
                        "max_attempts": self.policy.max_attempts,
                        "error": str(e)
                    })
        
        # All retries exhausted
        self._record_failure(self.policy.max_attempts, str(last_exception), retryable=True)
        
        raise MaxRetriesExceededError(
            f"Max retries ({self.policy.max_attempts}) exceeded for '{self.name}'",
            self.policy.max_attempts,
            last_exception
        )
    
    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            MaxRetriesExceededError: If all retry attempts are exhausted
            Any non-retryable exception raised by the function
        """
        self._total_calls += 1
        last_exception = None
        
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                
                # Record success
                duration = time.time() - start_time
                self._record_success(attempt, duration)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.policy.should_retry(e, attempt):
                    self._record_failure(attempt, str(e), retryable=False)
                    raise
                
                # If this is the last attempt, don't sleep and retry
                if attempt < self.policy.max_attempts:
                    # Calculate delay and wait
                    delay = self.policy.calculate_delay(attempt)
                    
                    log.warning(f"Async retry attempt {attempt} for '{self.name}' failed", extra={
                        "retry_manager": self.name,
                        "attempt": attempt,
                        "max_attempts": self.policy.max_attempts,
                        "error": str(e),
                        "delay": delay
                    })
                    
                    await asyncio.sleep(delay)
                    self._total_retries += 1
                else:
                    # This was the last attempt, log and break
                    log.warning(f"Final async retry attempt {attempt} for '{self.name}' failed", extra={
                        "retry_manager": self.name,
                        "attempt": attempt,
                        "max_attempts": self.policy.max_attempts,
                        "error": str(e)
                    })
        
        # All retries exhausted
        self._record_failure(self.policy.max_attempts, str(last_exception), retryable=True)
        
        raise MaxRetriesExceededError(
            f"Max retries ({self.policy.max_attempts}) exceeded for '{self.name}'",
            self.policy.max_attempts,
            last_exception
        )
    
    def _record_success(self, attempt: int, duration: float):
        """Record a successful execution."""
        self._total_successes += 1
        self._retry_attempts_histogram[attempt] = self._retry_attempts_histogram.get(attempt, 0) + 1
        
        log.debug(f"Success for '{self.name}' on attempt {attempt}", extra={
            "retry_manager": self.name,
            "attempt": attempt,
            "duration": duration
        })
    
    def _record_failure(self, attempt: int, error: str, retryable: bool):
        """Record a failed execution."""
        self._total_failures += 1
        self._retry_attempts_histogram[attempt] = self._retry_attempts_histogram.get(attempt, 0) + 1
        
        log.error(f"Failure for '{self.name}' after {attempt} attempts", extra={
            "retry_manager": self.name,
            "attempt": attempt,
            "error": error,
            "retryable": retryable
        })
    
    def get_stats(self) -> dict[str, Any]:
        """Get retry manager statistics."""
        success_rate = (self._total_successes / self._total_calls * 100) if self._total_calls > 0 else 0
        avg_attempts = sum(attempt * count for attempt, count in self._retry_attempts_histogram.items()) / max(self._total_calls, 1)
        
        return {
            "name": self.name,
            "total_calls": self._total_calls,
            "total_retries": self._total_retries,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": success_rate,
            "average_attempts": avg_attempts,
            "retry_attempts_histogram": self._retry_attempts_histogram.copy(),
            "policy": {
                "max_attempts": self.policy.max_attempts,
                "base_delay": self.policy.base_delay,
                "max_delay": self.policy.max_delay,
                "strategy": self.policy.strategy.value,
                "exponential_base": self.policy.exponential_base
            }
        }
    
    def reset_stats(self):
        """Reset all statistics."""
        self._total_calls = 0
        self._total_retries = 0
        self._total_successes = 0
        self._total_failures = 0
        self._retry_attempts_histogram.clear()
        
        log.info(f"Statistics reset for retry manager '{self.name}'")


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    name: Optional[str] = None
) -> Callable:
    """
    Decorator to add retry logic to a function.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        strategy: Retry strategy to use
        retryable_exceptions: Tuple of exception types that should trigger retries
        non_retryable_exceptions: Tuple of exception types that should not trigger retries
        name: Name for the retry manager (defaults to function name)
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        retry_name = name or f"{func.__module__}.{func.__name__}"
        
        policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            strategy=strategy,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions
        )
        
        retry_manager = RetryManager(retry_name, policy)
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_manager.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_manager.execute(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


# Global retry manager registry
_retry_managers: dict[str, RetryManager] = {}


def get_retry_manager(name: str, policy: Optional[RetryPolicy] = None) -> RetryManager:
    """Get or create a retry manager by name."""
    if name not in _retry_managers:
        _retry_managers[name] = RetryManager(name, policy)
    return _retry_managers[name]


def get_all_retry_managers() -> dict[str, RetryManager]:
    """Get all registered retry managers."""
    return _retry_managers.copy()


def reset_all_retry_stats():
    """Reset statistics for all retry managers."""
    for manager in _retry_managers.values():
        manager.reset_stats()


def get_retry_manager_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all retry managers."""
    return {name: manager.get_stats() for name, manager in _retry_managers.items()}


# Common retry policies for different scenarios
class CommonRetryPolicies:
    """Predefined retry policies for common scenarios."""
    
    @staticmethod
    def network_requests() -> RetryPolicy:
        """Retry policy optimized for network requests."""
        return RetryPolicy(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                OSError,
                RetryableError
            ),
            non_retryable_exceptions=(
                ValueError,
                TypeError,
                NonRetryableError
            )
        )
    
    @staticmethod
    def database_operations() -> RetryPolicy:
        """Retry policy optimized for database operations."""
        return RetryPolicy(
            max_attempts=5,
            base_delay=0.5,
            max_delay=10.0,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
            jitter_factor=0.2
        )
    
    @staticmethod
    def api_calls() -> RetryPolicy:
        """Retry policy optimized for external API calls."""
        return RetryPolicy(
            max_attempts=4,
            base_delay=2.0,
            max_delay=60.0,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
            jitter_factor=0.15
        )
    
    @staticmethod
    def quick_operations() -> RetryPolicy:
        """Retry policy for quick operations that should fail fast."""
        return RetryPolicy(
            max_attempts=2,
            base_delay=0.1,
            max_delay=1.0,
            strategy=RetryStrategy.FIXED
        )