"""
Tests for Load-Based Processor functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.monitoring.metrics import LoadBasedProcessor, get_load_processor


class TestLoadBasedProcessor:
    """Test Load-Based Processor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = LoadBasedProcessor()
    
    def test_initialization(self):
        """Test load processor initialization."""
        assert self.processor.cpu_threshold_warning == 70.0
        assert self.processor.cpu_threshold_critical == 85.0
        assert self.processor.memory_threshold_warning == 75.0
        assert self.processor.memory_threshold_critical == 90.0
        assert self.processor.current_load_level == "normal"
        assert self.processor.current_processing_factor == 1.0
        assert len(self.processor.disabled_features) == 0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_connections')
    def test_assess_system_load(self, mock_connections, mock_disk, mock_memory, mock_cpu):
        """Test system load assessment."""
        # Mock system metrics
        mock_cpu.return_value = 50.0
        
        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 60.0
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = MagicMock()
        mock_disk_obj.used = 400 * 1024**3  # 400GB
        mock_disk_obj.total = 1000 * 1024**3  # 1TB
        mock_disk.return_value = mock_disk_obj
        
        mock_connections.return_value = [1, 2, 3, 4, 5]  # 5 connections
        
        load_metrics = self.processor.assess_system_load()
        
        assert load_metrics["cpu_percent"] == 50.0
        assert load_metrics["memory_percent"] == 60.0
        assert load_metrics["disk_percent"] == 40.0
        assert load_metrics["connections"] == 5
        assert "load_score" in load_metrics
        assert "timestamp" in load_metrics
        
        # Verify load history was updated
        assert len(self.processor.load_history) == 1
    
    def test_determine_load_level_normal(self):
        """Test load level determination for normal conditions."""
        load_metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0
        }
        
        level = self.processor.determine_load_level(load_metrics)
        assert level == "normal"
    
    def test_determine_load_level_reduced(self):
        """Test load level determination for reduced conditions."""
        load_metrics = {
            "cpu_percent": 75.0,  # Above warning threshold
            "memory_percent": 60.0
        }
        
        level = self.processor.determine_load_level(load_metrics)
        assert level == "reduced"
    
    def test_determine_load_level_minimal(self):
        """Test load level determination for minimal conditions."""
        load_metrics = {
            "cpu_percent": 90.0,  # Above critical threshold
            "memory_percent": 95.0  # Above critical threshold
        }
        
        level = self.processor.determine_load_level(load_metrics)
        assert level == "minimal"
    
    def test_adjust_processing_parameters_normal(self):
        """Test processing parameter adjustment for normal load."""
        adjustments = self.processor.adjust_processing_parameters("normal")
        
        assert adjustments["new_level"] == "normal"
        assert adjustments["new_factor"] == 1.0
        assert len(adjustments["disabled_features"]) == 0
        assert self.processor.current_load_level == "normal"
        assert self.processor.current_processing_factor == 1.0
    
    def test_adjust_processing_parameters_reduced(self):
        """Test processing parameter adjustment for reduced load."""
        adjustments = self.processor.adjust_processing_parameters("reduced")
        
        assert adjustments["new_level"] == "reduced"
        assert adjustments["new_factor"] == 0.7
        assert self.processor.current_load_level == "reduced"
        assert self.processor.current_processing_factor == 0.7
        
        # Check that low-priority features are disabled
        assert "statistics_calculation" in self.processor.disabled_features
        assert "background_cleanup" in self.processor.disabled_features
        assert "detailed_logging" in self.processor.disabled_features
    
    def test_adjust_processing_parameters_minimal(self):
        """Test processing parameter adjustment for minimal load."""
        adjustments = self.processor.adjust_processing_parameters("minimal")
        
        assert adjustments["new_level"] == "minimal"
        assert adjustments["new_factor"] == 0.3
        assert self.processor.current_load_level == "minimal"
        assert self.processor.current_processing_factor == 0.3
        
        # Check that more features are disabled
        disabled_count = len(self.processor.disabled_features)
        assert disabled_count > 0
        assert "statistics_calculation" in self.processor.disabled_features
        assert "api_caching" in self.processor.disabled_features
    
    def test_feature_enablement_checks(self):
        """Test feature enablement checks."""
        # Initially all features should be enabled
        assert self.processor.is_feature_enabled("token_scoring")
        assert self.processor.is_feature_enabled("detailed_logging")
        
        # Adjust to reduced load
        self.processor.adjust_processing_parameters("reduced")
        
        # High priority features should still be enabled
        assert self.processor.is_feature_enabled("token_scoring")
        assert self.processor.is_feature_enabled("health_monitoring")
        
        # Low priority features should be disabled
        assert not self.processor.is_feature_enabled("detailed_logging")
        assert not self.processor.is_feature_enabled("statistics_calculation")
    
    def test_get_adjusted_interval(self):
        """Test interval adjustment based on processing factor."""
        base_interval = 10.0
        
        # Normal load - no adjustment
        self.processor.current_processing_factor = 1.0
        assert self.processor.get_adjusted_interval(base_interval) == 10.0
        
        # Reduced load - increased interval
        self.processor.current_processing_factor = 0.7
        adjusted = self.processor.get_adjusted_interval(base_interval)
        assert adjusted > base_interval
        assert adjusted == pytest.approx(14.29, abs=0.1)
        
        # Minimal load - significantly increased interval
        self.processor.current_processing_factor = 0.3
        adjusted = self.processor.get_adjusted_interval(base_interval)
        assert adjusted > base_interval
        assert adjusted == pytest.approx(33.33, abs=0.1)
    
    def test_get_adjusted_batch_size(self):
        """Test batch size adjustment based on processing factor."""
        base_batch_size = 100
        
        # Normal load - no adjustment
        self.processor.current_processing_factor = 1.0
        assert self.processor.get_adjusted_batch_size(base_batch_size) == 100
        
        # Reduced load - smaller batch
        self.processor.current_processing_factor = 0.7
        adjusted = self.processor.get_adjusted_batch_size(base_batch_size)
        assert adjusted == 70
        
        # Minimal load - much smaller batch
        self.processor.current_processing_factor = 0.3
        adjusted = self.processor.get_adjusted_batch_size(base_batch_size)
        assert adjusted == 30
        
        # Ensure minimum of 1
        self.processor.current_processing_factor = 0.001
        adjusted = self.processor.get_adjusted_batch_size(1)
        assert adjusted == 1
    
    def test_should_change_load_level_hysteresis(self):
        """Test hysteresis in load level changes."""
        # Start with normal load
        self.processor.current_load_level = "normal"
        
        # Add some load history
        for i in range(5):
            self.processor.load_history.append({
                "cpu_percent": 65.0,  # Below warning threshold
                "memory_percent": 70.0,
                "timestamp": i
            })
        
        # Should not change to reduced immediately
        assert not self.processor.should_change_load_level("reduced")
        
        # Add consistently high load
        for i in range(5, 8):
            self.processor.load_history.append({
                "cpu_percent": 75.0,  # Above warning threshold
                "memory_percent": 80.0,
                "timestamp": i
            })
        
        # Should change to reduced now
        assert self.processor.should_change_load_level("reduced")
    
    def test_update_thresholds(self):
        """Test threshold updates."""
        original_cpu_warning = self.processor.cpu_threshold_warning
        original_memory_critical = self.processor.memory_threshold_critical
        
        self.processor.update_thresholds(
            cpu_warning=80.0,
            memory_critical=95.0
        )
        
        assert self.processor.cpu_threshold_warning == 80.0
        assert self.processor.memory_threshold_critical == 95.0
        # Other thresholds should remain unchanged
        assert self.processor.cpu_threshold_critical == 85.0
        assert self.processor.memory_threshold_warning == 75.0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_connections')
    def test_process_load_adjustment_integration(self, mock_connections, mock_disk, mock_memory, mock_cpu):
        """Test complete load adjustment process."""
        # Mock high load conditions
        mock_cpu.return_value = 80.0  # High CPU
        
        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 85.0  # High memory
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = MagicMock()
        mock_disk_obj.used = 500 * 1024**3
        mock_disk_obj.total = 1000 * 1024**3
        mock_disk.return_value = mock_disk_obj
        
        mock_connections.return_value = [1] * 10
        
        # Process load adjustment
        result = self.processor.process_load_adjustment()
        
        assert "load_metrics" in result
        assert result["load_metrics"]["cpu_percent"] == 80.0
        assert result["load_metrics"]["memory_percent"] == 85.0
        assert "new_level" in result
        assert "new_factor" in result
    
    def test_get_load_statistics(self):
        """Test load statistics generation."""
        # Add some load history
        for i in range(10):
            self.processor.load_history.append({
                "cpu_percent": 50.0 + i,
                "memory_percent": 60.0 + i,
                "load_score": 55.0 + i,
                "timestamp": i
            })
        
        stats = self.processor.get_load_statistics()
        
        assert "current_state" in stats
        assert "load_averages" in stats
        assert "load_peaks" in stats
        assert "load_distribution" in stats
        assert "thresholds" in stats
        
        # Check averages
        assert stats["load_averages"]["cpu_percent"] == 54.5  # (50+59)/2
        assert stats["load_averages"]["memory_percent"] == 64.5  # (60+69)/2
        
        # Check peaks
        assert stats["load_peaks"]["cpu_percent"] == 59.0
        assert stats["load_peaks"]["memory_percent"] == 69.0
    
    def test_global_load_processor(self):
        """Test global load processor function."""
        processor = get_load_processor()
        assert isinstance(processor, LoadBasedProcessor)
        
        # Should return the same instance (singleton-like behavior)
        processor2 = get_load_processor()
        assert processor is processor2
    
    def test_should_skip_processing(self):
        """Test processing skip logic."""
        # Normal load - should not skip
        assert not self.processor.should_skip_processing("token_scoring")
        
        # Adjust to minimal load
        self.processor.adjust_processing_parameters("minimal")
        
        # High priority features should not be skipped
        assert not self.processor.should_skip_processing("token_scoring")
        assert not self.processor.should_skip_processing("health_monitoring")
        
        # Low priority features should be skipped
        assert self.processor.should_skip_processing("detailed_logging")
        assert self.processor.should_skip_processing("statistics_calculation")
    
    def test_load_level_transitions(self):
        """Test transitions between different load levels."""
        # Start normal
        assert self.processor.current_load_level == "normal"
        assert self.processor.current_processing_factor == 1.0
        
        # Move to reduced
        self.processor.adjust_processing_parameters("reduced")
        assert self.processor.current_load_level == "reduced"
        assert self.processor.current_processing_factor == 0.7
        
        # Move to minimal
        self.processor.adjust_processing_parameters("minimal")
        assert self.processor.current_load_level == "minimal"
        assert self.processor.current_processing_factor == 0.3
        
        # Back to normal
        self.processor.adjust_processing_parameters("normal")
        assert self.processor.current_load_level == "normal"
        assert self.processor.current_processing_factor == 1.0
        assert len(self.processor.disabled_features) == 0
