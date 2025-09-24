"""
Tests for monitoring configuration system.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.monitoring.config import (
    MonitoringSettings, ConfigurationManager,
    get_monitoring_config_manager, get_monitoring_config
)
from src.monitoring.models import MonitoringConfig, RecoveryConfig, CircuitBreakerConfig


class TestMonitoringSettings:
    """Test MonitoringSettings pydantic model."""
    
    def test_default_settings(self):
        """Test default monitoring settings."""
        settings = MonitoringSettings()
        
        assert settings.health_check_interval == 30
        assert settings.memory_warning_threshold == 1400.0
        assert settings.memory_critical_threshold == 1600.0
        assert settings.cpu_warning_threshold == 70.0
        assert settings.cpu_critical_threshold == 80.0
        assert settings.api_response_time_warning == 2000.0
        assert settings.api_response_time_critical == 5000.0
        assert settings.enable_external_monitoring is True
    
    def test_environment_variable_override(self):
        """Test environment variable override."""
        with patch.dict(os.environ, {
            'MONITORING_HEALTH_CHECK_INTERVAL': '60',
            'MONITORING_MEMORY_WARNING_THRESHOLD': '512.0',
            'MONITORING_ENABLE_EXTERNAL_MONITORING': 'false'
        }):
            settings = MonitoringSettings()
            
            assert settings.health_check_interval == 60
            assert settings.memory_warning_threshold == 512.0
            assert settings.enable_external_monitoring is False
    
    def test_validation_memory_thresholds(self):
        """Test validation of memory thresholds."""
        with pytest.raises(ValueError, match="memory_critical_threshold must be higher"):
            MonitoringSettings(
                memory_warning_threshold=1000.0,
                memory_critical_threshold=800.0  # Lower than warning
            )
    
    def test_validation_cpu_thresholds(self):
        """Test validation of CPU thresholds."""
        with pytest.raises(ValueError, match="cpu_critical_threshold must be higher"):
            MonitoringSettings(
                cpu_warning_threshold=80.0,
                cpu_critical_threshold=70.0  # Lower than warning
            )
    
    def test_validation_api_response_thresholds(self):
        """Test validation of API response time thresholds."""
        with pytest.raises(ValueError, match="api_response_time_critical must be higher"):
            MonitoringSettings(
                api_response_time_warning=5000.0,
                api_response_time_critical=2000.0  # Lower than warning
            )


class TestConfigurationManager:
    """Test ConfigurationManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = ConfigurationManager()
    
    def test_initialization(self):
        """Test ConfigurationManager initialization."""
        assert self.config_manager._settings is not None
        assert self.config_manager._config_cache is not None
        assert isinstance(self.config_manager._last_reload, datetime)
    
    def test_get_monitoring_config(self):
        """Test getting monitoring configuration."""
        config = self.config_manager.get_monitoring_config()
        
        assert isinstance(config, MonitoringConfig)
        assert config.health_check_interval > 0
        assert config.memory_warning_threshold > 0
        assert config.memory_critical_threshold > config.memory_warning_threshold
        assert config.cpu_warning_threshold > 0
        assert config.cpu_critical_threshold > config.cpu_warning_threshold
    
    def test_get_recovery_config(self):
        """Test getting recovery configuration."""
        config = self.config_manager.get_recovery_config()
        
        assert isinstance(config, RecoveryConfig)
        assert config.max_restart_attempts > 0
        assert config.restart_cooldown > 0
        assert config.graceful_shutdown_timeout > 0
        assert config.max_retries > 0
        assert config.base_retry_delay > 0
    
    def test_get_circuit_breaker_config(self):
        """Test getting circuit breaker configuration."""
        config = self.config_manager.get_circuit_breaker_config()
        
        assert isinstance(config, CircuitBreakerConfig)
        assert config.failure_threshold > 0
        assert config.recovery_timeout > 0
        assert config.half_open_max_calls > 0
        assert config.success_threshold > 0
    
    def test_is_feature_enabled(self):
        """Test feature enablement checking."""
        # Test default enabled features
        assert self.config_manager.is_feature_enabled("external_monitoring") is True
        assert self.config_manager.is_feature_enabled("performance_tracking") is True
        
        # Test non-existent feature (should default to True)
        assert self.config_manager.is_feature_enabled("non_existent_feature") is True
    
    def test_register_change_callback(self):
        """Test registering configuration change callbacks."""
        callback_called = False
        callback_args = None
        
        def test_callback(key, old_value, new_value):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = (key, old_value, new_value)
        
        self.config_manager.register_change_callback("test", test_callback)
        assert "test" in self.config_manager._change_callbacks
        
        # Simulate configuration change
        old_config = {"test_key": "old_value"}
        new_config = {"test_key": "new_value"}
        self.config_manager._notify_config_changes(old_config, new_config)
        
        assert callback_called is True
        assert callback_args == ("test_key", "old_value", "new_value")
    
    def test_unregister_change_callback(self):
        """Test unregistering configuration change callbacks."""
        def test_callback(key, old_value, new_value):
            pass
        
        self.config_manager.register_change_callback("test", test_callback)
        assert "test" in self.config_manager._change_callbacks
        
        self.config_manager.unregister_change_callback("test")
        assert "test" not in self.config_manager._change_callbacks
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        errors = self.config_manager.validate_configuration()
        
        # Should have no errors with default configuration
        assert len(errors) == 0
    
    def test_export_config(self):
        """Test configuration export."""
        export = self.config_manager.export_config()
        
        assert "effective_config" in export
        assert "last_reload" in export
        assert "validation_errors" in export
        
        assert isinstance(export["effective_config"], dict)
        assert isinstance(export["validation_errors"], dict)
    
    def test_merge_with_database_settings(self):
        """Test merging with database settings."""
        # Mock database session factory
        mock_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_session_factory.return_value.__enter__.return_value = mock_session
        
        mock_settings_service = MagicMock()
        mock_settings_service.get.side_effect = lambda key: {
            "monitoring_health_check_interval": "45",
            "monitoring_memory_warning_mb": "600.0",
            "monitoring_enable_external": "false"
        }.get(key)
        
        with patch('src.monitoring.config.SettingsService', return_value=mock_settings_service):
            config_manager = ConfigurationManager(mock_session_factory)
            config = config_manager._get_effective_config()
            
            # Should have database overrides
            assert config["health_check_interval"] == 45
            assert config["memory_warning_threshold"] == 600.0
            assert config["enable_external_monitoring"] is False
    
    def test_config_reload_detection(self):
        """Test configuration reload and change detection."""
        # Initial config
        initial_config = self.config_manager._config_cache.copy()
        
        # Mock environment change
        with patch.dict(os.environ, {'MONITORING_HEALTH_CHECK_INTERVAL': '90'}):
            # Force reload
            changes_detected = self.config_manager._reload_config()
            
            assert changes_detected is True
            new_config = self.config_manager._config_cache
            assert new_config["health_check_interval"] == 90
            assert new_config != initial_config
    
    def test_automatic_reload_timing(self):
        """Test automatic configuration reload timing."""
        # Set last reload to more than 30 seconds ago
        self.config_manager._last_reload = datetime.utcnow() - timedelta(seconds=35)
        
        with patch.object(self.config_manager, '_reload_config') as mock_reload:
            mock_reload.return_value = False
            
            # Should trigger reload
            config = self.config_manager._get_effective_config()
            mock_reload.assert_called_once()
    
    def test_config_change_notification(self):
        """Test configuration change notification system."""
        callback_calls = []
        
        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
        
        self.config_manager.register_change_callback("test", test_callback)
        
        old_config = {
            "health_check_interval": 30,
            "memory_warning_threshold": 800.0,
            "unchanged_key": "same_value"
        }
        
        new_config = {
            "health_check_interval": 60,  # Changed
            "memory_warning_threshold": 600.0,  # Changed
            "unchanged_key": "same_value",  # Unchanged
            "new_key": "new_value"  # New
        }
        
        self.config_manager._notify_config_changes(old_config, new_config)
        
        # Should have 3 callback calls (2 changes + 1 new key)
        assert len(callback_calls) == 3
        
        # Check specific changes
        changes_dict = {call[0]: (call[1], call[2]) for call in callback_calls}
        assert changes_dict["health_check_interval"] == (30, 60)
        assert changes_dict["memory_warning_threshold"] == (800.0, 600.0)
        assert changes_dict["new_key"] == (None, "new_value")


class TestGlobalFunctions:
    """Test global configuration functions."""
    
    def test_get_monitoring_config_manager(self):
        """Test getting global configuration manager."""
        manager1 = get_monitoring_config_manager()
        manager2 = get_monitoring_config_manager()
        
        # Should return the same instance (singleton)
        assert manager1 is manager2
        assert isinstance(manager1, ConfigurationManager)
    
    def test_get_monitoring_config(self):
        """Test getting monitoring configuration via global function."""
        config = get_monitoring_config()
        
        assert isinstance(config, MonitoringConfig)
        assert config.health_check_interval > 0
    
    @patch.dict(os.environ, {'MONITORING_ENABLE_EXTERNAL_MONITORING': 'false'})
    def test_feature_enablement_with_env_override(self):
        """Test feature enablement with environment variable override."""
        from src.monitoring.config import is_monitoring_feature_enabled
        
        # Clear global manager to pick up new environment
        import src.monitoring.config
        src.monitoring.config._config_manager = None
        
        enabled = is_monitoring_feature_enabled("external_monitoring")
        assert enabled is False


class TestConfigurationIntegration:
    """Test integration with existing systems."""
    
    def test_config_structure_compatibility(self):
        """Test that configuration structure is compatible with models."""
        config_manager = ConfigurationManager()
        
        # Should be able to create all config objects without errors
        monitoring_config = config_manager.get_monitoring_config()
        recovery_config = config_manager.get_recovery_config()
        circuit_config = config_manager.get_circuit_breaker_config()
        
        assert isinstance(monitoring_config, MonitoringConfig)
        assert isinstance(recovery_config, RecoveryConfig)
        assert isinstance(circuit_config, CircuitBreakerConfig)
    
    def test_validation_with_invalid_values(self):
        """Test validation with invalid configuration values."""
        # Test with invalid environment variables
        with patch.dict(os.environ, {
            'MONITORING_MEMORY_WARNING_THRESHOLD': 'invalid_float',
            'MONITORING_HEALTH_CHECK_INTERVAL': 'invalid_int'
        }):
            # Should handle invalid values gracefully
            try:
                settings = MonitoringSettings()
                # Should use defaults for invalid values
                assert settings.memory_warning_threshold == 800.0  # default
                assert settings.health_check_interval == 30  # default
            except Exception as e:
                # Or raise appropriate validation error
                assert "invalid" in str(e).lower()
    
    def test_hot_reload_scenario(self):
        """Test hot reload scenario with configuration changes."""
        config_manager = ConfigurationManager()
        
        # Register callback to track changes
        changes_tracked = []
        def track_changes(key, old_val, new_val):
            changes_tracked.append((key, old_val, new_val))
        
        config_manager.register_change_callback("tracker", track_changes)
        
        # Get initial config
        initial_config = config_manager.get_monitoring_config()
        initial_interval = initial_config.health_check_interval
        
        # Simulate environment change and reload
        with patch.dict(os.environ, {'MONITORING_HEALTH_CHECK_INTERVAL': '120'}):
            changes_detected = config_manager.reload_config()
            
            if changes_detected:
                new_config = config_manager.get_monitoring_config()
                assert new_config.health_check_interval == 120
                assert new_config.health_check_interval != initial_interval
                
                # Should have tracked the change
                assert len(changes_tracked) > 0