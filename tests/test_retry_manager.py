"""
Tests for retry manager implementation.
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from src.monitoring.retry_manager import (
    RetryManager, RetryPolicy, RetryStrategy, RetryError,
    MaxRetriesExceededError, RetryableError, NonRetryableError,
    retry, get_retry_manager, get_all_retry_managers,
    reset_all_retry_stats, CommonRetryPolicies
)


class TestRetryPolicy:
    """Test RetryPolicy class."""
    
    def test_default_policy(self):
        """Test default retry policy."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.exponential_base == 2.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_JITTER
        assert policy.jitter_factor == 0.1
    
    def test_fixed_delay_calculation(self):
        """Test fixed delay calculation."""
        policy = RetryPolicy(
            base_delay=2.0,
            strategy=RetryStrategy.FIXED
        )
        
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(5) == 2.0
    
    def test_linear_delay_calculation(self):
        """Test linear delay calculation."""
        policy = RetryPolicy(
            base_delay=1.0,
            strategy=RetryStrategy.LINEAR
        )
        
        assert policy.calculate_delay(1) == 1.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(3) == 3.0
    
    def test_exponential_delay_calculation(self):
        """Test exponential delay calculation."""
        policy = RetryPolicy(
            base_delay=1.0,
            exponential_base=2.0,
            strategy=RetryStrategy.EXPONENTIAL
        )
        
        assert policy.calculate_delay(1) == 1.0  # 1.0 * 2^0
        assert policy.calculate_delay(2) == 2.0  # 1.0 * 2^1
        assert policy.calculate_delay(3) == 4.0  # 1.0 * 2^2
    
    def test_exponential_jitter_delay_calculation(self):
        """Test exponential delay with jitter."""
        policy = RetryPolicy(
            base_delay=1.0,
            exponential_base=2.0,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
            jitter_factor=0.1
        )
        
        # With jitter, delay should be base + some random amount
        delay1 = policy.calculate_delay(2)
        delay2 = policy.calculate_delay(2)
        
        # Base delay should be 2.0, jitter adds up to 0.2
        assert 2.0 <= delay1 <= 2.2
        assert 2.0 <= delay2 <= 2.2
        # Jitter should make delays different (with high probability)
        # Note: This test might occasionally fail due to randomness
    
    def test_max_delay_limit(self):
        """Test that delays are capped at max_delay."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            strategy=RetryStrategy.EXPONENTIAL
        )
        
        # Large attempt should be capped at max_delay
        assert policy.calculate_delay(10) == 5.0
    
    def test_should_retry_with_retryable_exceptions(self):
        """Test retry decision with retryable exceptions."""
        policy = RetryPolicy(
            max_attempts=3,
            retryable_exceptions=(ValueError, ConnectionError)
        )
        
        # Should retry retryable exceptions
        assert policy.should_retry(ValueError("test"), 1) is True
        assert policy.should_retry(ConnectionError("test"), 2) is True
        
        # Should not retry non-retryable exceptions
        assert policy.should_retry(TypeError("test"), 1) is False
    
    def test_should_retry_with_non_retryable_exceptions(self):
        """Test retry decision with non-retryable exceptions."""
        policy = RetryPolicy(
            max_attempts=3,
            non_retryable_exceptions=(ValueError,)
        )
        
        # Should not retry non-retryable exceptions
        assert policy.should_retry(ValueError("test"), 1) is False
        
        # Should retry other exceptions
        assert policy.should_retry(ConnectionError("test"), 1) is True
    
    def test_should_retry_max_attempts_exceeded(self):
        """Test that retry decision is based on exception type, not attempt count."""
        policy = RetryPolicy(
            max_attempts=2,
            retryable_exceptions=(ConnectionError,),  # Only ConnectionError is retryable
            non_retryable_exceptions=(ValueError,)    # ValueError is explicitly non-retryable
        )
        
        # should_retry now only checks exception type, not attempt count
        # ValueError is non-retryable, so should return False
        assert policy.should_retry(ValueError("test"), 1) is False
        assert policy.should_retry(ValueError("test"), 2) is False
        
        # ConnectionError is retryable, so should return True regardless of attempt
        assert policy.should_retry(ConnectionError("test"), 1) is True
        assert policy.should_retry(ConnectionError("test"), 2) is True
    
    def test_should_retry_with_custom_error_types(self):
        """Test retry decision with custom error types."""
        policy = RetryPolicy(max_attempts=3)
        
        # Should retry RetryableError
        assert policy.should_retry(RetryableError("test"), 1) is True
        
        # Should not retry NonRetryableError
        assert policy.should_retry(NonRetryableError("test"), 1) is False


class TestRetryManager:
    """Test RetryManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.policy = RetryPolicy(
            max_attempts=3,
            base_delay=0.1,  # Short delay for tests
            strategy=RetryStrategy.FIXED
        )
        self.manager = RetryManager("test_manager", self.policy)
    
    def test_initialization(self):
        """Test RetryManager initialization."""
        assert self.manager.name == "test_manager"
        assert self.manager.policy == self.policy
        assert self.manager._total_calls == 0
        assert self.manager._total_successes == 0
        assert self.manager._total_failures == 0
    
    def test_successful_execution(self):
        """Test successful function execution."""
        def success_func(x, y):
            return x + y
        
        result = self.manager.execute(success_func, 2, 3)
        
        assert result == 5
        assert self.manager._total_calls == 1
        assert self.manager._total_successes == 1
        assert self.manager._total_failures == 0
        assert self.manager._total_retries == 0
    
    def test_execution_with_retries(self):
        """Test function execution with retries."""
        call_count = 0
        
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        result = self.manager.execute(flaky_func)
        
        assert result == "success"
        assert call_count == 3
        assert self.manager._total_calls == 1
        assert self.manager._total_successes == 1
        assert self.manager._total_retries == 2
    
    def test_execution_max_retries_exceeded(self):
        """Test execution when max retries are exceeded."""
        def always_failing_func():
            raise ConnectionError("Always fails")
        
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            self.manager.execute(always_failing_func)
        
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, ConnectionError)
        assert self.manager._total_calls == 1
        assert self.manager._total_successes == 0
        assert self.manager._total_failures == 1
        assert self.manager._total_retries == 2
    
    def test_execution_non_retryable_error(self):
        """Test execution with non-retryable error."""
        policy = RetryPolicy(
            max_attempts=3,
            non_retryable_exceptions=(ValueError,)
        )
        manager = RetryManager("test_non_retryable", policy)
        
        def failing_func():
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError, match="Non-retryable error"):
            manager.execute(failing_func)
        
        # Should not have retried
        assert manager._total_calls == 1
        assert manager._total_retries == 0
        assert manager._total_failures == 1
    
    @pytest.mark.asyncio
    async def test_async_successful_execution(self):
        """Test successful async function execution."""
        async def async_success_func(x, y):
            return x * y
        
        result = await self.manager.execute_async(async_success_func, 3, 4)
        
        assert result == 12
        assert self.manager._total_successes == 1
    
    @pytest.mark.asyncio
    async def test_async_execution_with_retries(self):
        """Test async function execution with retries."""
        call_count = 0
        
        async def async_flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "async_success"
        
        result = await self.manager.execute_async(async_flaky_func)
        
        assert result == "async_success"
        assert call_count == 2
        assert self.manager._total_retries == 1
    
    @pytest.mark.asyncio
    async def test_async_max_retries_exceeded(self):
        """Test async execution when max retries are exceeded."""
        async def async_always_failing_func():
            raise TimeoutError("Always times out")
        
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await self.manager.execute_async(async_always_failing_func)
        
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, TimeoutError)
    
    def test_get_stats(self):
        """Test getting retry manager statistics."""
        # Execute some functions to generate stats
        def success_func():
            return "success"
        
        def failing_func():
            raise ConnectionError("Network error")
        
        # Successful call
        self.manager.execute(success_func)
        
        # Failed call with retries
        try:
            self.manager.execute(failing_func)
        except MaxRetriesExceededError:
            pass
        
        stats = self.manager.get_stats()
        
        assert stats["name"] == "test_manager"
        assert stats["total_calls"] == 2
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1
        assert stats["total_retries"] == 2
        assert stats["success_rate"] == 50.0
        assert "retry_attempts_histogram" in stats
        assert "policy" in stats
    
    def test_reset_stats(self):
        """Test resetting retry manager statistics."""
        # Generate some stats
        def success_func():
            return "success"
        
        self.manager.execute(success_func)
        assert self.manager._total_calls == 1
        
        # Reset stats
        self.manager.reset_stats()
        
        assert self.manager._total_calls == 0
        assert self.manager._total_successes == 0
        assert self.manager._total_failures == 0
        assert self.manager._total_retries == 0
        assert len(self.manager._retry_attempts_histogram) == 0


class TestRetryDecorator:
    """Test retry decorator."""
    
    def test_sync_function_decorator(self):
        """Test retry decorator on sync function."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01, strategy=RetryStrategy.FIXED)
        def flaky_func(x):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return x * 2
        
        result = flaky_func(5)
        
        assert result == 10
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """Test retry decorator on async function."""
        call_count = 0
        
        @retry(max_attempts=2, base_delay=0.01, strategy=RetryStrategy.FIXED)
        async def async_flaky_func(x):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return x ** 2
        
        result = await async_flaky_func(4)
        
        assert result == 16
        assert call_count == 2
    
    def test_decorator_with_non_retryable_exception(self):
        """Test decorator with non-retryable exception."""
        @retry(
            max_attempts=3,
            base_delay=0.01,
            non_retryable_exceptions=(ValueError,)
        )
        def failing_func():
            raise ValueError("Non-retryable")
        
        with pytest.raises(ValueError, match="Non-retryable"):
            failing_func()
    
    def test_decorator_max_retries_exceeded(self):
        """Test decorator when max retries are exceeded."""
        @retry(max_attempts=2, base_delay=0.01)
        def always_failing_func():
            raise ConnectionError("Always fails")
        
        with pytest.raises(MaxRetriesExceededError):
            always_failing_func()


class TestRetryManagerRegistry:
    """Test retry manager registry functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry before each test
        from src.monitoring.retry_manager import _retry_managers
        _retry_managers.clear()
    
    def test_get_retry_manager(self):
        """Test getting retry manager from registry."""
        policy = RetryPolicy(max_attempts=5)
        
        # Get new retry manager
        manager1 = get_retry_manager("test_registry", policy)
        assert manager1.name == "test_registry"
        assert manager1.policy.max_attempts == 5
        
        # Get same retry manager again
        manager2 = get_retry_manager("test_registry")
        assert manager1 is manager2  # Should be the same instance
    
    def test_get_all_retry_managers(self):
        """Test getting all retry managers from registry."""
        # Initially empty
        all_managers = get_all_retry_managers()
        assert len(all_managers) == 0
        
        # Add some retry managers
        manager1 = get_retry_manager("manager1")
        manager2 = get_retry_manager("manager2")
        
        all_managers = get_all_retry_managers()
        assert len(all_managers) == 2
        assert "manager1" in all_managers
        assert "manager2" in all_managers
        assert all_managers["manager1"] is manager1
        assert all_managers["manager2"] is manager2
    
    def test_reset_all_retry_stats(self):
        """Test resetting statistics for all retry managers."""
        # Create managers and generate some stats
        manager1 = get_retry_manager("stats_test1")
        manager2 = get_retry_manager("stats_test2")
        
        def success_func():
            return "success"
        
        manager1.execute(success_func)
        manager2.execute(success_func)
        
        assert manager1._total_calls == 1
        assert manager2._total_calls == 1
        
        # Reset all stats
        reset_all_retry_stats()
        
        assert manager1._total_calls == 0
        assert manager2._total_calls == 0
    
    def test_get_retry_manager_stats(self):
        """Test getting statistics for all retry managers."""
        from src.monitoring.retry_manager import get_retry_manager_stats
        
        # Create managers and generate stats
        manager1 = get_retry_manager("stats_test1")
        manager2 = get_retry_manager("stats_test2")
        
        def success_func():
            return "success"
        
        manager1.execute(success_func)
        manager2.execute(success_func)
        manager2.execute(success_func)
        
        stats = get_retry_manager_stats()
        
        assert len(stats) == 2
        assert "stats_test1" in stats
        assert "stats_test2" in stats
        assert stats["stats_test1"]["total_calls"] == 1
        assert stats["stats_test2"]["total_calls"] == 2


class TestCommonRetryPolicies:
    """Test predefined retry policies."""
    
    def test_network_requests_policy(self):
        """Test network requests retry policy."""
        policy = CommonRetryPolicies.network_requests()
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 30.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_JITTER
        
        # Should retry network errors
        assert policy.should_retry(ConnectionError("test"), 1) is True
        assert policy.should_retry(TimeoutError("test"), 1) is True
        
        # Should not retry value errors
        assert policy.should_retry(ValueError("test"), 1) is False
    
    def test_database_operations_policy(self):
        """Test database operations retry policy."""
        policy = CommonRetryPolicies.database_operations()
        
        assert policy.max_attempts == 5
        assert policy.base_delay == 0.5
        assert policy.max_delay == 10.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_JITTER
        assert policy.jitter_factor == 0.2
    
    def test_api_calls_policy(self):
        """Test API calls retry policy."""
        policy = CommonRetryPolicies.api_calls()
        
        assert policy.max_attempts == 4
        assert policy.base_delay == 2.0
        assert policy.max_delay == 60.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_JITTER
    
    def test_quick_operations_policy(self):
        """Test quick operations retry policy."""
        policy = CommonRetryPolicies.quick_operations()
        
        assert policy.max_attempts == 2
        assert policy.base_delay == 0.1
        assert policy.max_delay == 1.0
        assert policy.strategy == RetryStrategy.FIXED


class TestRetryEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_max_attempts(self):
        """Test retry manager with zero max attempts."""
        policy = RetryPolicy(max_attempts=0)
        manager = RetryManager("zero_attempts", policy)
        
        def test_func():
            return "success"
        
        # Should still execute once (attempt 1)
        with pytest.raises(MaxRetriesExceededError):
            manager.execute(test_func)
    
    def test_negative_delays(self):
        """Test retry policy with negative delays."""
        policy = RetryPolicy(base_delay=-1.0)
        
        # Should handle negative delays gracefully
        delay = policy.calculate_delay(1)
        assert delay >= 0  # Should not be negative
    
    def test_very_large_delays(self):
        """Test retry policy with very large calculated delays."""
        policy = RetryPolicy(
            base_delay=1000.0,
            max_delay=5.0,  # Much smaller max
            exponential_base=10.0,
            strategy=RetryStrategy.EXPONENTIAL
        )
        
        # Should be capped at max_delay
        delay = policy.calculate_delay(5)
        assert delay == 5.0
    
    def test_exception_in_function_with_args(self):
        """Test retry behavior with function arguments and exceptions."""
        call_count = 0
        
        def func_with_args(a, b, c=None, d="default"):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError(f"Error with args: {a}, {b}, {c}, {d}")
            return f"Success: {a}, {b}, {c}, {d}"
        
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        manager = RetryManager("args_test", policy)
        
        result = manager.execute(func_with_args, "arg1", "arg2", c="kwarg1", d="kwarg2")
        
        assert result == "Success: arg1, arg2, kwarg1, kwarg2"
        assert call_count == 2