"""
Tests for parallel token processor.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.scheduler.parallel_processor import (
    ParallelTokenProcessor,
    AdaptiveBatchProcessor,
    TokenProcessingResult,
    get_parallel_processor,
    get_adaptive_batch_processor
)
from src.adapters.db.models import Token


@pytest.fixture
def mock_token():
    """Create a mock token for testing."""
    token = Mock(spec=Token)
    token.id = 1
    token.mint_address = "test_mint_address_123"
    token.symbol = "TEST"
    token.name = "Test Token"
    token.status = "monitoring"
    return token


@pytest.fixture
def mock_client():
    """Create a mock DexScreener client."""
    client = Mock()
    client.get_pairs = Mock(return_value=[{"pair": "test_pair"}])
    client.get_pairs_async = AsyncMock(return_value=[{"pair": "test_pair"}])
    return client


@pytest.fixture
def parallel_processor():
    """Create a parallel processor for testing."""
    return ParallelTokenProcessor(max_concurrent=4, timeout=2.0)


@pytest.fixture
def adaptive_processor():
    """Create an adaptive batch processor for testing."""
    return AdaptiveBatchProcessor(initial_batch_size=20)


class TestParallelTokenProcessor:
    """Test parallel token processor functionality."""
    
    @pytest.mark.asyncio
    async def test_process_empty_batch(self, parallel_processor, mock_client):
        """Test processing empty token batch."""
        results = await parallel_processor.process_token_batch([], mock_client, "test")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_process_single_token_success(self, parallel_processor, mock_client, mock_token):
        """Test successful processing of single token."""
        results = await parallel_processor.process_token_batch([mock_token], mock_client, "test")
        
        assert len(results) == 1
        result = results[0]
        assert result.token == mock_token
        assert result.success is True
        assert result.pairs == [{"pair": "test_pair"}]
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_process_token_with_async_client(self, parallel_processor, mock_client, mock_token):
        """Test processing with async client."""
        # Mock async client
        mock_client.get_pairs_async = AsyncMock(return_value=[{"async_pair": "test"}])
        
        results = await parallel_processor.process_token_batch([mock_token], mock_client, "test")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.pairs == [{"async_pair": "test"}]
        mock_client.get_pairs_async.assert_called_once_with(mock_token.mint_address)
    
    @pytest.mark.asyncio
    async def test_process_token_with_sync_client_fallback(self, parallel_processor, mock_client, mock_token):
        """Test fallback to sync client when async not available."""
        # Remove async method
        delattr(mock_client, 'get_pairs_async')
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = [{"sync_pair": "test"}]
            
            results = await parallel_processor.process_token_batch([mock_token], mock_client, "test")
            
            assert len(results) == 1
            result = results[0]
            assert result.success is True
            assert result.pairs == [{"sync_pair": "test"}]
            mock_to_thread.assert_called_once_with(mock_client.get_pairs, mock_token.mint_address)
    
    @pytest.mark.asyncio
    async def test_process_token_failure(self, parallel_processor, mock_client, mock_token):
        """Test handling of token processing failure."""
        mock_client.get_pairs_async = AsyncMock(side_effect=Exception("API Error"))
        
        results = await parallel_processor.process_token_batch([mock_token], mock_client, "test")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.pairs is None
        assert "API Error" in result.error
    
    @pytest.mark.asyncio
    async def test_process_multiple_tokens_concurrency(self, mock_client):
        """Test concurrent processing of multiple tokens."""
        # Create multiple tokens
        tokens = []
        for i in range(5):
            token = Mock(spec=Token)
            token.id = i
            token.mint_address = f"test_mint_{i}"
            token.symbol = f"TEST{i}"
            tokens.append(token)
        
        # Mock async client with delay to test concurrency
        async def mock_get_pairs_async(mint):
            await asyncio.sleep(0.1)  # Simulate API delay
            return [{"pair": f"pair_for_{mint}"}]
        
        mock_client.get_pairs_async = mock_get_pairs_async
        
        processor = ParallelTokenProcessor(max_concurrent=3, timeout=5.0)
        
        start_time = datetime.now()
        results = await processor.process_token_batch(tokens, mock_client, "test")
        end_time = datetime.now()
        
        # Should complete faster than sequential processing
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 0.5  # Should be much faster than 5 * 0.1 = 0.5s
        
        assert len(results) == 5
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_timeout(self, mock_client, mock_token):
        """Test batch timeout handling."""
        # Mock slow async client
        async def slow_get_pairs_async(mint):
            await asyncio.sleep(2.0)  # Longer than timeout
            return [{"pair": "test"}]
        
        mock_client.get_pairs_async = slow_get_pairs_async
        
        processor = ParallelTokenProcessor(max_concurrent=2, timeout=0.5)
        
        results = await processor.process_token_batch([mock_token], mock_client, "test")
        
        # Should handle timeout gracefully
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert "batch_timeout" in result.error


class TestAdaptiveBatchProcessor:
    """Test adaptive batch processor functionality."""
    
    def test_initial_batch_size(self, adaptive_processor):
        """Test initial batch size setting."""
        assert adaptive_processor.current_batch_size == 20
        assert adaptive_processor.min_batch_size == 10
        assert adaptive_processor.max_batch_size == 100
    
    def test_adaptive_sizing_low_load(self, adaptive_processor):
        """Test batch size increase under low system load."""
        system_metrics = {
            "cpu_percent": 20,
            "memory_percent": 40
        }
        
        # Record good performance
        adaptive_processor.record_performance(50, 10.0)  # 5 tokens/sec
        adaptive_processor.record_performance(50, 10.0)
        adaptive_processor.record_performance(50, 10.0)
        
        batch_size = adaptive_processor.get_adaptive_batch_size(30, system_metrics)
        
        # Should increase batch size due to low load and good performance
        assert batch_size > 30
    
    def test_adaptive_sizing_high_load(self, adaptive_processor):
        """Test batch size decrease under high system load."""
        system_metrics = {
            "cpu_percent": 80,
            "memory_percent": 85
        }
        
        batch_size = adaptive_processor.get_adaptive_batch_size(50, system_metrics)
        
        # Should decrease batch size due to high load
        assert batch_size < 50
        assert batch_size >= adaptive_processor.min_batch_size
    
    def test_adaptive_sizing_poor_performance(self, adaptive_processor):
        """Test batch size decrease with poor performance."""
        system_metrics = {
            "cpu_percent": 40,
            "memory_percent": 50
        }
        
        # Record poor performance
        adaptive_processor.record_performance(10, 30.0)  # 0.33 tokens/sec
        adaptive_processor.record_performance(10, 30.0)
        adaptive_processor.record_performance(10, 30.0)
        
        batch_size = adaptive_processor.get_adaptive_batch_size(40, system_metrics)
        
        # Should decrease batch size due to poor performance
        assert batch_size < 40
    
    def test_performance_recording(self, adaptive_processor):
        """Test performance metrics recording."""
        adaptive_processor.record_performance(100, 20.0)  # 5 tokens/sec
        adaptive_processor.record_performance(50, 25.0)   # 2 tokens/sec
        
        assert len(adaptive_processor.performance_history) == 2
        assert adaptive_processor.performance_history[0] == 5.0
        assert adaptive_processor.performance_history[1] == 2.0
    
    def test_performance_history_limit(self, adaptive_processor):
        """Test performance history size limit."""
        # Record more than max_history entries
        for i in range(15):
            adaptive_processor.record_performance(10, 1.0)
        
        # Should keep only the most recent entries
        assert len(adaptive_processor.performance_history) == adaptive_processor.max_history
    
    def test_batch_size_bounds(self, adaptive_processor):
        """Test batch size stays within bounds."""
        # Test with extreme system metrics
        high_load_metrics = {
            "cpu_percent": 95,
            "memory_percent": 95
        }
        
        low_load_metrics = {
            "cpu_percent": 5,
            "memory_percent": 10
        }
        
        # Record excellent performance
        for _ in range(5):
            adaptive_processor.record_performance(100, 10.0)  # 10 tokens/sec
        
        high_load_size = adaptive_processor.get_adaptive_batch_size(50, high_load_metrics)
        low_load_size = adaptive_processor.get_adaptive_batch_size(50, low_load_metrics)
        
        # Should respect bounds
        assert adaptive_processor.min_batch_size <= high_load_size <= adaptive_processor.max_batch_size
        assert adaptive_processor.min_batch_size <= low_load_size <= adaptive_processor.max_batch_size


class TestGlobalInstances:
    """Test global instance management."""
    
    def test_get_parallel_processor_singleton(self):
        """Test parallel processor singleton behavior."""
        processor1 = get_parallel_processor()
        processor2 = get_parallel_processor()
        
        assert processor1 is processor2
    
    def test_get_adaptive_batch_processor_singleton(self):
        """Test adaptive batch processor singleton behavior."""
        processor1 = get_adaptive_batch_processor()
        processor2 = get_adaptive_batch_processor()
        
        assert processor1 is processor2
    
    def test_parallel_processor_custom_params(self):
        """Test parallel processor with custom parameters."""
        processor = get_parallel_processor(max_concurrent=16, timeout=10.0)
        
        assert processor.max_concurrent == 16
        assert processor.timeout == 10.0
    
    def test_adaptive_processor_custom_params(self):
        """Test adaptive processor with custom parameters."""
        processor = get_adaptive_batch_processor(initial_batch_size=50)
        
        assert processor.current_batch_size == 50