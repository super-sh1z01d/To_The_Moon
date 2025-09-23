"""
Tests for circuit breaker implementation.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.monitoring.circuit_breaker import (
    CircuitBreaker, CircuitBreakerError, CircuitBreakerOpenError,
    CircuitBreakerTimeoutError, circuit_breaker, get_circuit_breaker,
    reset_all_circuit_breakers, get_circuit_breaker_stats
)
from src.monitoring.models import CircuitState, CircuitBreakerConfig


class TestCircuitBreaker:
    """Test CircuitBreaker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5,
            half_open_max_calls=2,
            success_threshold=2,
            call_timeout=1.0
        )
        self.breaker = CircuitBreaker("test_breaker", self.config)
    
    def test_initialization(self):
        """Test circuit breaker initialization."""
        assert self.breaker.name == "test_breaker"
        assert self.breaker.config == self.config
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker.failure_rate == 0.0
        assert self.breaker.is_closed is True
        assert self.breaker.is_open is False
        assert self.breaker.is_half_open is False
    
    def test_successful_call(self):
        """Test successful function call through circuit breaker."""
        def test_func(x, y):
            return x + y
        
        result = self.breaker.call(test_func, 2, 3)
        assert result == 5
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker._total_calls == 1
        assert self.breaker._total_successes == 1
        assert self.breaker._total_failures == 0
    
    def test_failed_call(self):
        """Test failed function call through circuit breaker."""
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            self.breaker.call(failing_func)
        
        assert self.breaker.state == CircuitState.CLOSED  # Still closed after 1 failure
        assert self.breaker._total_calls == 1
        assert self.breaker._total_successes == 0
        assert self.breaker._total_failures == 1
        assert self.breaker._failure_count == 1
    
    def test_transition_to_open(self):
        """Test transition from closed to open state."""
        def failing_func():
            raise ValueError("Test error")
        
        # Make enough failures to trigger open state
        for i in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                self.breaker.call(failing_func)
        
        assert self.breaker.state == CircuitState.OPEN
        assert self.breaker.is_open is True
        assert self.breaker._failure_count == self.config.failure_threshold
    
    def test_calls_blocked_when_open(self):
        """Test that calls are blocked when circuit is open."""
        # Force circuit to open state
        self.breaker._transition_to_open()
        
        def test_func():
            return "should not be called"
        
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            self.breaker.call(test_func)
        
        assert exc_info.value.circuit_name == "test_breaker"
        assert exc_info.value.state == CircuitState.OPEN
        assert self.breaker._total_rejected == 1
    
    def test_transition_to_half_open(self):
        """Test transition from open to half-open state."""
        # Force to open state
        self.breaker._transition_to_open()
        assert self.breaker.state == CircuitState.OPEN
        
        # Mock time to simulate recovery timeout passing
        future_time = datetime.utcnow() + timedelta(seconds=self.config.recovery_timeout + 1)
        with patch('src.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = future_time
            
            # Check state - should transition to half-open
            state = self.breaker.state
            assert state == CircuitState.HALF_OPEN
    
    def test_half_open_success_transitions_to_closed(self):
        """Test that successful calls in half-open state transition to closed."""
        # Force to half-open state
        self.breaker._transition_to_half_open()
        assert self.breaker.state == CircuitState.HALF_OPEN
        
        def success_func():
            return "success"
        
        # Make enough successful calls to close the circuit
        for i in range(self.config.success_threshold):
            result = self.breaker.call(success_func)
            assert result == "success"
        
        assert self.breaker.state == CircuitState.CLOSED
    
    def test_half_open_failure_transitions_to_open(self):
        """Test that failed calls in half-open state transition back to open."""
        # Force to half-open state
        self.breaker._transition_to_half_open()
        assert self.breaker.state == CircuitState.HALF_OPEN
        
        def failing_func():
            raise ValueError("Test error")
        
        # Any failure in half-open should go back to open
        with pytest.raises(ValueError):
            self.breaker.call(failing_func)
        
        assert self.breaker.state == CircuitState.OPEN
    
    def test_half_open_call_limit(self):
        """Test that half-open state limits concurrent calls."""
        # Use config with higher success threshold to prevent immediate transition to closed
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5,
            half_open_max_calls=2,
            success_threshold=5,  # Higher threshold
            call_timeout=1.0
        )
        breaker = CircuitBreaker("test_limit", config)
        
        # Force to half-open state
        breaker._transition_to_half_open()
        
        def test_func():
            return "success"
        
        # Make calls up to the limit
        for i in range(config.half_open_max_calls):
            result = breaker.call(test_func)
            assert result == "success"
            # Should still be in half-open state
            assert breaker.state == CircuitState.HALF_OPEN
        
        # Next call should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(test_func)
    
    @pytest.mark.asyncio
    async def test_async_successful_call(self):
        """Test successful async function call through circuit breaker."""
        async def async_test_func(x, y):
            return x * y
        
        result = await self.breaker.call_async(async_test_func, 3, 4)
        assert result == 12
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker._total_successes == 1
    
    @pytest.mark.asyncio
    async def test_async_failed_call(self):
        """Test failed async function call through circuit breaker."""
        async def async_failing_func():
            raise ValueError("Async test error")
        
        with pytest.raises(ValueError, match="Async test error"):
            await self.breaker.call_async(async_failing_func)
        
        assert self.breaker._total_failures == 1
    
    @pytest.mark.asyncio
    async def test_async_timeout(self):
        """Test async function timeout through circuit breaker."""
        async def slow_async_func():
            await asyncio.sleep(2.0)  # Longer than timeout
            return "should not reach here"
        
        with pytest.raises(CircuitBreakerTimeoutError) as exc_info:
            await self.breaker.call_async(slow_async_func)
        
        assert exc_info.value.circuit_name == "test_breaker"
        assert self.breaker._total_timeouts == 1
        assert self.breaker._total_failures == 1
    
    def test_manual_reset(self):
        """Test manual reset of circuit breaker."""
        # Force to open state
        self.breaker._transition_to_open()
        assert self.breaker.state == CircuitState.OPEN
        
        # Reset manually
        self.breaker.reset()
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker._failure_count == 0
        assert self.breaker._success_count == 0
    
    def test_manual_force_open(self):
        """Test manually forcing circuit breaker to open."""
        assert self.breaker.state == CircuitState.CLOSED
        
        self.breaker.force_open()
        assert self.breaker.state == CircuitState.OPEN
    
    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        def success_func():
            return "success"
        
        def failing_func():
            raise ValueError("Test error")
        
        # Make some successful and failed calls
        self.breaker.call(success_func)  # 1 success
        
        try:
            self.breaker.call(failing_func)  # 1 failure
        except ValueError:
            pass
        
        self.breaker.call(success_func)  # 1 more success
        
        # Should be 1 failure out of 3 calls = 33.33%
        assert abs(self.breaker.failure_rate - 33.33) < 0.01
    
    def test_get_stats(self):
        """Test getting circuit breaker statistics."""
        def test_func():
            return "success"
        
        # Make a call to generate some stats
        self.breaker.call(test_func)
        
        stats = self.breaker.get_stats()
        
        assert stats["name"] == "test_breaker"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["total_calls"] == 1
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 0
        assert stats["failure_rate"] == 0.0
        assert "config" in stats
        assert stats["config"]["failure_threshold"] == self.config.failure_threshold


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
    
    def test_sync_function_decorator(self):
        """Test circuit breaker decorator on sync function."""
        @circuit_breaker("decorated_sync", self.config)
        def test_func(x, y):
            if x < 0:
                raise ValueError("Negative input")
            return x + y
        
        # Successful call
        result = test_func(2, 3)
        assert result == 5
        
        # Failed calls
        with pytest.raises(ValueError):
            test_func(-1, 3)
        
        with pytest.raises(ValueError):
            test_func(-2, 3)
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerOpenError):
            test_func(1, 2)  # This should be blocked
    
    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """Test circuit breaker decorator on async function."""
        @circuit_breaker("decorated_async", self.config)
        async def async_test_func(x, y):
            if x < 0:
                raise ValueError("Negative input")
            return x * y
        
        # Successful call
        result = await async_test_func(2, 3)
        assert result == 6
        
        # Failed calls
        with pytest.raises(ValueError):
            await async_test_func(-1, 3)
        
        with pytest.raises(ValueError):
            await async_test_func(-2, 3)
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerOpenError):
            await async_test_func(1, 2)  # This should be blocked


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry before each test
        reset_all_circuit_breakers()
        from src.monitoring.circuit_breaker import _circuit_breakers
        _circuit_breakers.clear()
    
    def test_get_circuit_breaker(self):
        """Test getting circuit breaker from registry."""
        config = CircuitBreakerConfig(failure_threshold=5)
        
        # Get new circuit breaker
        breaker1 = get_circuit_breaker("test_registry", config)
        assert breaker1.name == "test_registry"
        assert breaker1.config.failure_threshold == 5
        
        # Get same circuit breaker again
        breaker2 = get_circuit_breaker("test_registry")
        assert breaker1 is breaker2  # Should be the same instance
    
    def test_get_all_circuit_breakers(self):
        """Test getting all circuit breakers from registry."""
        from src.monitoring.circuit_breaker import get_all_circuit_breakers
        
        # Initially empty
        all_breakers = get_all_circuit_breakers()
        assert len(all_breakers) == 0
        
        # Add some circuit breakers
        breaker1 = get_circuit_breaker("breaker1")
        breaker2 = get_circuit_breaker("breaker2")
        
        all_breakers = get_all_circuit_breakers()
        assert len(all_breakers) == 2
        assert "breaker1" in all_breakers
        assert "breaker2" in all_breakers
        assert all_breakers["breaker1"] is breaker1
        assert all_breakers["breaker2"] is breaker2
    
    def test_reset_all_circuit_breakers(self):
        """Test resetting all circuit breakers."""
        # Create and open some circuit breakers
        breaker1 = get_circuit_breaker("breaker1")
        breaker2 = get_circuit_breaker("breaker2")
        
        breaker1.force_open()
        breaker2.force_open()
        
        assert breaker1.state == CircuitState.OPEN
        assert breaker2.state == CircuitState.OPEN
        
        # Reset all
        reset_all_circuit_breakers()
        
        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED
    
    def test_get_circuit_breaker_stats(self):
        """Test getting statistics for all circuit breakers."""
        # Create some circuit breakers and make calls
        breaker1 = get_circuit_breaker("stats_test1")
        breaker2 = get_circuit_breaker("stats_test2")
        
        def test_func():
            return "success"
        
        breaker1.call(test_func)
        breaker2.call(test_func)
        breaker2.call(test_func)
        
        stats = get_circuit_breaker_stats()
        
        assert len(stats) == 2
        assert "stats_test1" in stats
        assert "stats_test2" in stats
        assert stats["stats_test1"]["total_calls"] == 1
        assert stats["stats_test2"]["total_calls"] == 2


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=0)
        breaker = CircuitBreaker("zero_threshold", config)
        
        def failing_func():
            raise ValueError("Test error")
        
        # Should open immediately on first failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
    
    def test_very_short_recovery_timeout(self):
        """Test circuit breaker with very short recovery timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker("short_timeout", config)
        
        def failing_func():
            raise ValueError("Test error")
        
        # Trigger open state
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should transition to half-open
        assert breaker.state == CircuitState.HALF_OPEN
    
    def test_no_timeout_configured(self):
        """Test circuit breaker with no call timeout."""
        config = CircuitBreakerConfig(call_timeout=0)
        breaker = CircuitBreaker("no_timeout", config)
        
        def slow_func():
            time.sleep(0.1)  # Short delay
            return "success"
        
        # Should complete successfully without timeout
        result = breaker.call(slow_func)
        assert result == "success"
    
    def test_exception_in_success_callback(self):
        """Test handling of exceptions during success recording."""
        breaker = CircuitBreaker("exception_test")
        
        def test_func():
            return "success"
        
        # Mock _record_success to raise an exception
        original_record_success = breaker._record_success
        def failing_record_success(*args, **kwargs):
            original_record_success(*args, **kwargs)
            raise RuntimeError("Success recording failed")
        
        breaker._record_success = failing_record_success
        
        # The call should still succeed despite the exception in recording
        with pytest.raises(RuntimeError, match="Success recording failed"):
            breaker.call(test_func)
        
        # But the success should still be recorded
        assert breaker._total_successes == 1