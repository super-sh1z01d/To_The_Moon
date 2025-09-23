"""
Circuit breaker implementation for resilient external API integration.

This module provides a circuit breaker pattern implementation that protects
against cascading failures when external services are unavailable or slow.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar, Generic, Union
from functools import wraps
from contextlib import asynccontextmanager

from .models import CircuitState, CircuitBreakerConfig
from .config import get_circuit_breaker_config

log = logging.getLogger("circuit_breaker")

T = TypeVar('T')


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, message: str, circuit_name: str, state: CircuitState):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.state = state


class CircuitBreakerOpenError(CircuitBreakerError):
    """Exception raised when circuit breaker is open and calls are blocked."""
    pass


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Exception raised when a call times out."""
    pass


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker implementation with configurable failure detection and recovery.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, calls are allowed
    - OPEN: Failure threshold exceeded, calls are blocked
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or get_circuit_breaker_config()
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None
        self._next_attempt_time: Optional[datetime] = None
        
        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_timeouts = 0
        self._total_rejected = 0
        
        # Half-open state tracking
        self._half_open_calls = 0
        
        log.info(f"Circuit breaker '{name}' initialized", extra={
            "circuit_name": name,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout
        })
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        self._update_state()
        return self._state
    
    @property
    def failure_rate(self) -> float:
        """Get current failure rate as percentage."""
        if self._total_calls == 0:
            return 0.0
        return (self._total_failures / self._total_calls) * 100
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking calls)."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function call through the circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            CircuitBreakerTimeoutError: If call times out
            Any exception raised by the function
        """
        self._total_calls += 1
        
        # Check if we should allow the call
        if not self._should_allow_call():
            self._total_rejected += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is {self._state.value}",
                self.name,
                self._state
            )
        
        # Execute the call with timeout
        start_time = time.time()
        try:
            # Apply timeout if configured
            if self.config.call_timeout > 0:
                result = self._call_with_timeout(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            call_duration = time.time() - start_time
            self._record_success(call_duration)
            
            return result
            
        except asyncio.TimeoutError:
            self._total_timeouts += 1
            self._record_failure("timeout")
            raise CircuitBreakerTimeoutError(
                f"Call to '{self.name}' timed out after {self.config.call_timeout}s",
                self.name,
                self._state
            )
        except Exception as e:
            call_duration = time.time() - start_time
            self._record_failure(str(e), call_duration)
            raise
    
    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function call through the circuit breaker.
        
        Args:
            func: Async function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            CircuitBreakerTimeoutError: If call times out
            Any exception raised by the function
        """
        self._total_calls += 1
        
        # Check if we should allow the call
        if not self._should_allow_call():
            self._total_rejected += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is {self._state.value}",
                self.name,
                self._state
            )
        
        # Execute the call with timeout
        start_time = time.time()
        try:
            # Apply timeout if configured
            if self.config.call_timeout > 0:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.call_timeout
                )
            else:
                result = await func(*args, **kwargs)
            
            # Record success
            call_duration = time.time() - start_time
            self._record_success(call_duration)
            
            return result
            
        except asyncio.TimeoutError:
            self._total_timeouts += 1
            self._record_failure("timeout")
            raise CircuitBreakerTimeoutError(
                f"Async call to '{self.name}' timed out after {self.config.call_timeout}s",
                self.name,
                self._state
            )
        except Exception as e:
            call_duration = time.time() - start_time
            self._record_failure(str(e), call_duration)
            raise
    
    def _call_with_timeout(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a synchronous function with timeout."""
        # For sync functions, we can't easily implement timeout without threading
        # For now, just call the function directly
        # In a real implementation, you might use threading or process pools
        return func(*args, **kwargs)
    
    def _should_allow_call(self) -> bool:
        """Check if a call should be allowed based on current state."""
        current_state = self.state  # This updates state if needed
        
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.OPEN:
            return False
        elif current_state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        
        return False
    
    def _record_success(self, call_duration: float):
        """Record a successful call."""
        self._success_count += 1
        self._total_successes += 1
        self._last_success_time = datetime.utcnow()
        
        # Check for slow calls
        is_slow = (
            self.config.slow_call_threshold > 0 and 
            call_duration >= self.config.slow_call_threshold
        )
        
        if is_slow:
            log.warning(f"Slow call detected in circuit '{self.name}'", extra={
                "circuit_name": self.name,
                "call_duration": call_duration,
                "slow_threshold": self.config.slow_call_threshold
            })
        
        # Handle state transitions on success
        if self._state == CircuitState.HALF_OPEN:
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
        
        log.debug(f"Success recorded for circuit '{self.name}'", extra={
            "circuit_name": self.name,
            "call_duration": call_duration,
            "success_count": self._success_count,
            "state": self._state.value
        })
    
    def _record_failure(self, error: str, call_duration: Optional[float] = None):
        """Record a failed call."""
        self._failure_count += 1
        self._total_failures += 1
        self._last_failure_time = datetime.utcnow()
        
        log.warning(f"Failure recorded for circuit '{self.name}'", extra={
            "circuit_name": self.name,
            "error": error,
            "call_duration": call_duration,
            "failure_count": self._failure_count,
            "state": self._state.value
        })
        
        # Handle state transitions on failure
        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state goes back to open
            self._transition_to_open()
    
    def _update_state(self):
        """Update circuit breaker state based on current conditions."""
        if self._state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if self._should_attempt_reset():
                self._transition_to_half_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open to half-open."""
        if not self._next_attempt_time:
            return False
        
        return datetime.utcnow() >= self._next_attempt_time
    
    def _transition_to_closed(self):
        """Transition circuit breaker to closed state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        
        log.info(f"Circuit breaker '{self.name}' transitioned to CLOSED", extra={
            "circuit_name": self.name,
            "old_state": old_state.value,
            "new_state": self._state.value
        })
    
    def _transition_to_open(self):
        """Transition circuit breaker to open state."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._success_count = 0
        self._half_open_calls = 0
        self._next_attempt_time = datetime.utcnow() + timedelta(seconds=self.config.recovery_timeout)
        
        log.error(f"Circuit breaker '{self.name}' transitioned to OPEN", extra={
            "circuit_name": self.name,
            "old_state": old_state.value,
            "new_state": self._state.value,
            "failure_count": self._failure_count,
            "next_attempt_time": self._next_attempt_time.isoformat()
        })
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to half-open state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        self._half_open_calls = 0
        
        log.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN", extra={
            "circuit_name": self.name,
            "old_state": old_state.value,
            "new_state": self._state.value
        })
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        log.info(f"Manually resetting circuit breaker '{self.name}'", extra={
            "circuit_name": self.name,
            "old_state": self._state.value
        })
        self._transition_to_closed()
    
    def force_open(self):
        """Manually force circuit breaker to open state."""
        log.warning(f"Manually forcing circuit breaker '{self.name}' to OPEN", extra={
            "circuit_name": self.name,
            "old_state": self._state.value
        })
        self._transition_to_open()
    
    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "total_timeouts": self._total_timeouts,
            "total_rejected": self._total_rejected,
            "failure_rate": self.failure_rate,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "last_success_time": self._last_success_time.isoformat() if self._last_success_time else None,
            "next_attempt_time": self._next_attempt_time.isoformat() if self._next_attempt_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "half_open_max_calls": self.config.half_open_max_calls,
                "success_threshold": self.config.success_threshold,
                "call_timeout": self.config.call_timeout
            }
        }


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> Callable:
    """
    Decorator to apply circuit breaker pattern to a function.
    
    Args:
        name: Name of the circuit breaker
        config: Circuit breaker configuration
        
    Returns:
        Decorated function with circuit breaker protection
    """
    breaker = CircuitBreaker(name, config)
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    return _circuit_breakers.copy()


def reset_all_circuit_breakers():
    """Reset all circuit breakers to closed state."""
    for breaker in _circuit_breakers.values():
        breaker.reset()


def get_circuit_breaker_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return {name: breaker.get_stats() for name, breaker in _circuit_breakers.items()}