"""
Tests for Performance Tracker functionality.
"""

import pytest
import time
from unittest.mock import patch

from src.monitoring.metrics import PerformanceTracker, get_performance_tracker


class TestPerformanceTracker:
    """Test Performance Tracker functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = PerformanceTracker(max_history_size=100)
    
    def test_initialization(self):
        """Test performance tracker initialization."""
        assert self.tracker.max_history_size == 100
        assert len(self.tracker._api_calls) == 0
        assert len(self.tracker._scheduler_executions) == 0
        assert len(self.tracker._system_metrics) == 0
        assert len(self.tracker._baselines) == 0
    
    def test_record_api_call(self):
        """Test recording API calls."""
        # Record successful API call
        self.tracker.record_api_call("dexscreener", 150.0, True, endpoint="/pairs")
        
        # Verify call was recorded
        assert "dexscreener" in self.tracker._api_calls
        assert len(self.tracker._api_calls["dexscreener"]) == 1
        
        call = self.tracker._api_calls["dexscreener"][0]
        assert call["response_time"] == 150.0
        assert call["success"] is True
        assert call["endpoint"] == "/pairs"
        assert call["error"] is None
        
        # Verify stats were updated
        assert "dexscreener" in self.tracker._api_stats
        stats = self.tracker._api_stats["dexscreener"]
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 100.0
        assert stats["average_response_time"] == 150.0
    
    def test_record_api_call_with_error(self):
        """Test recording API call with error."""
        self.tracker.record_api_call("dexscreener", 5000.0, False, error="Timeout", endpoint="/pairs")
        
        call = self.tracker._api_calls["dexscreener"][0]
        assert call["response_time"] == 5000.0
        assert call["success"] is False
        assert call["error"] == "Timeout"
        
        stats = self.tracker._api_stats["dexscreener"]
        assert stats["success_rate"] == 0.0
        assert stats["error_rate"] == 100.0
    
    def test_record_scheduler_execution(self):
        """Test recording scheduler executions."""
        self.tracker.record_scheduler_execution("hot", 30.0, 10, 8, 1)
        
        # Verify execution was recorded
        assert "hot" in self.tracker._scheduler_executions
        assert len(self.tracker._scheduler_executions["hot"]) == 1
        
        execution = self.tracker._scheduler_executions["hot"][0]
        assert execution["processing_time"] == 30.0
        assert execution["tokens_processed"] == 10
        assert execution["tokens_updated"] == 8
        assert execution["error_count"] == 1
        assert execution["success_rate"] == 0.8
        
        # Verify stats were updated
        assert "hot" in self.tracker._scheduler_stats
        stats = self.tracker._scheduler_stats["hot"]
        assert stats["total_executions"] == 1
        assert stats["average_processing_time"] == 30.0
        assert stats["overall_success_rate"] == 80.0
    
    def test_record_system_metrics(self):
        """Test recording system metrics."""
        self.tracker.record_system_metrics(25.0, 60.0, 45.0, 5)
        
        # Verify metrics were recorded
        assert len(self.tracker._system_metrics) == 1
        
        metric = self.tracker._system_metrics[0]
        assert metric["cpu_percent"] == 25.0
        assert metric["memory_percent"] == 60.0
        assert metric["disk_percent"] == 45.0
        assert metric["active_connections"] == 5
    
    def test_calculate_percentile(self):
        """Test percentile calculation."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        # Test various percentiles
        assert self.tracker._calculate_percentile(values, 50) == 5.5
        assert self.tracker._calculate_percentile(values, 95) == 9.5
        assert self.tracker._calculate_percentile(values, 99) == 9.9
        
        # Test edge cases
        assert self.tracker._calculate_percentile([], 50) == 0.0
        assert self.tracker._calculate_percentile([5], 50) == 5
    
    def test_api_performance_statistics(self):
        """Test API performance statistics calculation."""
        # Record multiple API calls with varying performance
        calls_data = [
            (100.0, True), (150.0, True), (200.0, True), (5000.0, False),
            (120.0, True), (180.0, True), (300.0, True), (2000.0, False)
        ]
        
        for response_time, success in calls_data:
            self.tracker.record_api_call("test_api", response_time, success)
        
        stats = self.tracker.get_api_performance("test_api")
        
        assert stats["total_calls"] == 8
        assert stats["success_rate"] == 75.0  # 6 out of 8 successful
        assert stats["error_rate"] == 25.0
        assert stats["average_response_time"] == pytest.approx(1256.25, abs=1)
        assert stats["min_response_time"] == 100.0
        assert stats["max_response_time"] == 5000.0
        assert "p95_response_time" in stats
        assert "p99_response_time" in stats
    
    def test_scheduler_performance_statistics(self):
        """Test scheduler performance statistics calculation."""
        # Record multiple scheduler executions
        executions_data = [
            (30.0, 10, 9, 0), (45.0, 15, 12, 1), (25.0, 8, 8, 0),
            (60.0, 20, 15, 2), (35.0, 12, 10, 1)
        ]
        
        for processing_time, processed, updated, errors in executions_data:
            self.tracker.record_scheduler_execution("test_group", processing_time, processed, updated, errors)
        
        stats = self.tracker.get_scheduler_performance("test_group")
        
        assert stats["total_executions"] == 5
        assert stats["average_processing_time"] == 39.0  # (30+45+25+60+35)/5
        assert stats["total_tokens_processed"] == 65  # 10+15+8+20+12
        assert stats["total_tokens_updated"] == 54  # 9+12+8+15+10
        assert stats["overall_success_rate"] == pytest.approx(83.08, abs=0.1)  # 54/65 * 100
        assert stats["total_errors"] == 4  # 0+1+0+2+1
        assert stats["min_processing_time"] == 25.0
        assert stats["max_processing_time"] == 60.0
    
    def test_system_performance_statistics(self):
        """Test system performance statistics calculation."""
        # Record multiple system metrics
        metrics_data = [
            (20.0, 50.0, 30.0, 3), (25.0, 55.0, 35.0, 4),
            (30.0, 60.0, 40.0, 5), (35.0, 65.0, 45.0, 6)
        ]
        
        for cpu, memory, disk, connections in metrics_data:
            self.tracker.record_system_metrics(cpu, memory, disk, connections)
        
        stats = self.tracker.get_system_performance()
        
        assert stats["average_cpu_percent"] == 27.5  # (20+25+30+35)/4
        assert stats["average_memory_percent"] == 57.5  # (50+55+60+65)/4
        assert stats["average_disk_percent"] == 37.5  # (30+35+40+45)/4
        assert stats["average_connections"] == 4.5  # (3+4+5+6)/4
        assert stats["peak_cpu_percent"] == 35.0
        assert stats["peak_memory_percent"] == 65.0
        assert stats["peak_disk_percent"] == 45.0
        assert stats["peak_connections"] == 6
        assert stats["metrics_collected"] == 4
    
    def test_performance_trend_analysis(self):
        """Test performance trend analysis."""
        # Record API calls with improving trend
        for i in range(20):
            response_time = 200 - (i * 5)  # Decreasing response time
            self.tracker.record_api_call("improving_api", response_time, True)
        
        stats = self.tracker.get_api_performance("improving_api")
        assert stats["response_time_trend"] == "improving"
        assert stats["response_time_change_percent"] < 0  # Negative change = improvement
        
        # Record scheduler executions with degrading trend
        for i in range(20):
            processing_time = 30 + (i * 2)  # Increasing processing time
            self.tracker.record_scheduler_execution("degrading_group", processing_time, 10, 9, 0)
        
        scheduler_stats = self.tracker.get_scheduler_performance("degrading_group")
        assert scheduler_stats["processing_time_trend"] == "degrading"
        assert scheduler_stats["processing_time_change_percent"] > 0  # Positive change = degradation
    
    def test_performance_anomaly_detection(self):
        """Test performance anomaly detection."""
        # Create baseline performance
        for _ in range(10):
            self.tracker.record_api_call("stable_api", 100.0, True)
        
        # Create anomalous performance
        for _ in range(10):
            self.tracker.record_api_call("stable_api", 300.0, True)  # 3x slower
        
        anomalies = self.tracker.detect_performance_anomalies(service="stable_api")
        
        assert len(anomalies) > 0
        response_time_anomaly = next((a for a in anomalies if a["type"] == "api_response_time_spike"), None)
        assert response_time_anomaly is not None
        assert response_time_anomaly["severity"] in ["medium", "high"]
        assert response_time_anomaly["change_percent"] > 50
    
    def test_performance_summary(self):
        """Test comprehensive performance summary."""
        # Add some test data
        self.tracker.record_api_call("test_api", 150.0, True)
        self.tracker.record_scheduler_execution("test_group", 30.0, 10, 9, 0)
        self.tracker.record_system_metrics(25.0, 60.0, 40.0, 5)
        
        summary = self.tracker.get_performance_summary()
        
        assert "system" in summary
        assert "apis" in summary
        assert "scheduler_groups" in summary
        assert "overall_health" in summary
        
        assert "test_api" in summary["apis"]
        assert "test_group" in summary["scheduler_groups"]
        assert summary["overall_health"] == "healthy"
    
    def test_performance_baselines(self):
        """Test performance baseline management."""
        # Set baselines
        self.tracker.set_performance_baseline("api_response_time", 200.0)
        self.tracker.set_performance_baseline("scheduler_processing_time", 45.0)
        
        # Get baselines
        assert self.tracker.get_performance_baseline("api_response_time") == 200.0
        assert self.tracker.get_performance_baseline("scheduler_processing_time") == 45.0
        assert self.tracker.get_performance_baseline("nonexistent") is None
    
    def test_cleanup_old_data(self):
        """Test cleanup of old performance data."""
        # Add old data (simulate by mocking timestamp)
        with patch('time.time', return_value=1000):
            self.tracker.record_api_call("old_api", 100.0, True)
            self.tracker.record_scheduler_execution("old_group", 30.0, 10, 9, 0)
            self.tracker.record_system_metrics(25.0, 60.0, 40.0, 5)
        
        # Add recent data
        with patch('time.time', return_value=2000):
            self.tracker.record_api_call("old_api", 150.0, True)
            self.tracker.record_scheduler_execution("old_group", 35.0, 12, 10, 0)
            self.tracker.record_system_metrics(30.0, 65.0, 45.0, 6)
        
        # Verify we have data
        assert len(self.tracker._api_calls["old_api"]) == 2
        assert len(self.tracker._scheduler_executions["old_group"]) == 2
        assert len(self.tracker._system_metrics) == 2
        
        # Cleanup old data (keep only last hour from time 2000)
        with patch('time.time', return_value=2000):
            cleaned_count = self.tracker.cleanup_old_data(max_age_hours=0.5)  # 30 minutes
        
        # Verify old data was cleaned
        assert cleaned_count > 0
        assert len(self.tracker._api_calls["old_api"]) == 1
        assert len(self.tracker._scheduler_executions["old_group"]) == 1
        assert len(self.tracker._system_metrics) == 1
    
    def test_global_performance_tracker(self):
        """Test global performance tracker function."""
        tracker = get_performance_tracker()
        assert isinstance(tracker, PerformanceTracker)
        
        # Should return the same instance (singleton-like behavior)
        tracker2 = get_performance_tracker()
        assert tracker is tracker2
    
    def test_max_history_size_limit(self):
        """Test that history size is limited to prevent memory issues."""
        small_tracker = PerformanceTracker(max_history_size=5)
        
        # Add more calls than the limit
        for i in range(10):
            small_tracker.record_api_call("test_api", 100.0 + i, True)
        
        # Should only keep the last 5 calls
        assert len(small_tracker._api_calls["test_api"]) == 5
        
        # Verify it kept the most recent calls
        calls = list(small_tracker._api_calls["test_api"])
        response_times = [call["response_time"] for call in calls]
        assert response_times == [105.0, 106.0, 107.0, 108.0, 109.0]
