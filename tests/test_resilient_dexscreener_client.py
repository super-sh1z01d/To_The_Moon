"""
Tests for resilient DexScreener API client.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta

import httpx

from src.adapters.services.resilient_dexscreener_client import (
    ResilientDexScreenerClient, APICache, DexScreenerRateLimitError,
    DexScreenerTimeoutError, DexScreenerConnectionError,
    DexScreenerInvalidResponseError, get_resilient_dexscreener_client
)
from src.monitoring.circuit_breaker import CircuitBreakerOpenError


class TestAPICache:
    """Test APICache functionality."""
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = APICache(ttl_seconds=60)
        
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        
        assert result == {"data": "value1"}
        assert cache.size() == 1
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        cache = APICache(ttl_seconds=1)  # 1 second TTL
        
        cache.set("key1", {"data": "value1"})
        assert cache.get("key1") == {"data": "value1"}
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
        assert cache.size() == 0
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = APICache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestResilientDexScreenerClient:
    """Test ResilientDexScreenerClient functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear circuit breaker registry before each test
        from src.monitoring.circuit_breaker import _circuit_breakers
        _circuit_breakers.clear()
        
        # Clear retry manager registry before each test
        from src.monitoring.retry_manager import _retry_managers
        _retry_managers.clear()
        
        # Create client with all features enabled but short timeouts for testing
        self.client = ResilientDexScreenerClient(
            timeout=1.0,
            cache_ttl=60,
            enable_circuit_breaker=True,
            enable_retry=True,
            enable_cache=True
        )
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_successful_api_call(self, mock_client_class):
        """Test successful API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"pairs": [{"pair": "data"}]}
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        assert result == [{"pair": "data"}]
        assert self.client._stats['successful_requests'] == 1
        assert self.client._stats['total_requests'] == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_api_call_with_caching(self, mock_client_class):
        """Test API call with response caching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"pairs": [{"pair": "data"}]}
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # First call should hit API
        result1 = self.client.get_pairs("test_mint")
        assert result1 == [{"pair": "data"}]
        assert self.client._stats['cache_misses'] == 1
        assert self.client._stats['cache_hits'] == 0
        
        # Second call should hit cache
        result2 = self.client.get_pairs("test_mint")
        assert result2 == [{"pair": "data"}]
        assert self.client._stats['cache_misses'] == 1
        assert self.client._stats['cache_hits'] == 1
        
        # API should only be called once
        assert mock_client.get.call_count == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_rate_limit_handling(self, mock_client_class):
        """Test handling of rate limit responses."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        # Should return None after retries are exhausted
        assert result is None
        assert self.client._stats['failed_requests'] == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_timeout_handling(self, mock_client_class):
        """Test handling of timeout errors."""
        # Mock timeout exception
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        # Should return None after retries are exhausted
        assert result is None
        assert self.client._stats['failed_requests'] == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_connection_error_handling(self, mock_client_class):
        """Test handling of connection errors."""
        # Mock connection error
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        # Should return None after retries are exhausted
        assert result is None
        assert self.client._stats['failed_requests'] == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_invalid_json_handling(self, mock_client_class):
        """Test handling of invalid JSON responses."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        # Should return None (non-retryable error)
        assert result is None
        assert self.client._stats['failed_requests'] == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_404_handling(self, mock_client_class):
        """Test handling of 404 responses."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        # Should return empty list for 404
        assert result == []
        assert self.client._stats['successful_requests'] == 1
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_server_error_handling(self, mock_client_class):
        """Test handling of server errors (5xx)."""
        # Mock server error response
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        result = self.client.get_pairs("test_mint")
        
        # Should return None after retries are exhausted
        assert result is None
        assert self.client._stats['failed_requests'] == 1
    
    def test_circuit_breaker_fallback_to_cache(self):
        """Test fallback to cache when circuit breaker is open."""
        # Pre-populate cache
        self.client._cache.set("test_mint", [{"cached": "data"}])
        
        # Force circuit breaker open
        self.client.force_circuit_breaker_open()
        
        result = self.client.get_pairs("test_mint")
        
        # Should return cached data when circuit breaker is open
        assert result == [{"cached": "data"}]
    
    def test_error_fallback_to_cache(self):
        """Test fallback to cache when API call fails."""
        # Pre-populate cache
        self.client._cache.set("test_mint", [{"cached": "data"}])
        
        # Mock API failure
        with patch('src.adapters.services.resilient_dexscreener_client.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.get.side_effect = Exception("API failure")
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            result = self.client.get_pairs("test_mint")
        
        # Should return cached data as fallback when API fails
        assert result == [{"cached": "data"}]
    
    def test_client_with_features_disabled(self):
        """Test client with resilience features disabled."""
        client = ResilientDexScreenerClient(
            enable_circuit_breaker=False,
            enable_retry=False,
            enable_cache=False
        )
        
        # Mock successful response
        with patch('src.adapters.services.resilient_dexscreener_client.httpx.Client') as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"pair": "data"}]
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            result = client.get_pairs("test_mint")
        
        assert result == [{"pair": "data"}]
        assert client.is_healthy() is True  # Always healthy when circuit breaker disabled
    
    def test_health_check(self):
        """Test client health check."""
        # Should be healthy initially
        assert self.client.is_healthy() is True
        
        # Force circuit breaker open
        self.client.force_circuit_breaker_open()
        assert self.client.is_healthy() is False
        
        # Reset circuit breaker
        self.client.reset_circuit_breaker()
        assert self.client.is_healthy() is True
    
    def test_get_stats(self):
        """Test getting client statistics."""
        stats = self.client.get_stats()
        
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'successful_requests' in stats
        assert 'failed_requests' in stats
        assert 'cache_size' in stats
        assert 'cache_hit_rate' in stats
        assert 'circuit_breaker' in stats
        assert 'retry_manager' in stats
    
    def test_reset_stats(self):
        """Test resetting client statistics."""
        # Generate some stats
        self.client._stats['total_requests'] = 10
        self.client._stats['successful_requests'] = 8
        
        self.client.reset_stats()
        
        assert self.client._stats['total_requests'] == 0
        assert self.client._stats['successful_requests'] == 0
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Add some cached data
        self.client._cache.set("key1", "value1")
        self.client._cache.set("key2", "value2")
        assert self.client._cache.size() == 2
        
        self.client.clear_cache()
        assert self.client._cache.size() == 0
    
    @pytest.mark.asyncio
    async def test_async_get_pairs(self):
        """Test async version of get_pairs."""
        # Mock successful response
        with patch('src.adapters.services.resilient_dexscreener_client.httpx.Client') as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pairs": [{"pair": "data"}]}
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            result = await self.client.get_pairs_async("test_mint")
        
        assert result == [{"pair": "data"}]
    
    def test_different_response_formats(self):
        """Test handling of different API response formats."""
        with patch('src.adapters.services.resilient_dexscreener_client.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            # Test list response format
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"pair": "data1"}]
            mock_client.get.return_value = mock_response
            
            result = self.client.get_pairs("test_mint1")
            assert result == [{"pair": "data1"}]
            
            # Test dict response format
            mock_response.json.return_value = {"pairs": [{"pair": "data2"}]}
            result = self.client.get_pairs("test_mint2")
            assert result == [{"pair": "data2"}]
            
            # Test empty pairs
            mock_response.json.return_value = {"pairs": None}
            result = self.client.get_pairs("test_mint3")
            assert result == []


class TestGlobalClient:
    """Test global client functions."""
    
    def test_get_resilient_dexscreener_client(self):
        """Test getting global resilient client."""
        client1 = get_resilient_dexscreener_client()
        client2 = get_resilient_dexscreener_client()
        
        # Should return the same instance
        assert client1 is client2
        assert isinstance(client1, ResilientDexScreenerClient)
    
    def test_create_resilient_dexscreener_client(self):
        """Test creating new resilient client with custom config."""
        from src.adapters.services.resilient_dexscreener_client import create_resilient_dexscreener_client
        
        client = create_resilient_dexscreener_client(
            timeout=5.0,
            cache_ttl=120,
            enable_cache=False
        )
        
        assert client.timeout == 5.0
        assert client.enable_cache is False


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear circuit breaker registry before each test
        from src.monitoring.circuit_breaker import _circuit_breakers
        _circuit_breakers.clear()
        
        # Clear retry manager registry before each test
        from src.monitoring.retry_manager import _retry_managers
        _retry_managers.clear()
        
        self.client = ResilientDexScreenerClient(
            timeout=1.0,
            cache_ttl=60
        )
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_retry_then_circuit_breaker_then_cache(self, mock_client_class):
        """Test scenario: retries fail, circuit breaker opens, fallback to cache."""
        # Pre-populate cache
        self.client._cache.set("test_mint", [{"cached": "data"}])
        
        # Mock consistent failures to trigger circuit breaker
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Make multiple calls to trigger circuit breaker
        results = []
        for i in range(10):
            result = self.client.get_pairs("test_mint")
            results.append(result)
        
        # Should have some cached results returned as fallback
        cached_results = [r for r in results if r == [{"cached": "data"}]]
        assert len(cached_results) > 0
    
    @patch('src.adapters.services.resilient_dexscreener_client.httpx.Client')
    def test_intermittent_failures_with_recovery(self, mock_client_class):
        """Test scenario with intermittent failures and recovery."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Simulate intermittent failures
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Every 3rd call succeeds
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = [{"pair": f"data_{call_count}"}]
                return mock_response
            else:
                raise httpx.TimeoutException("Intermittent timeout")
        
        mock_client.get.side_effect = side_effect
        
        # Make several calls
        results = []
        for i in range(9):
            result = self.client.get_pairs(f"test_mint_{i}")
            results.append(result)
        
        # Some calls should succeed (every 3rd call)
        successful_results = [r for r in results if r is not None and r != []]
        assert len(successful_results) > 0