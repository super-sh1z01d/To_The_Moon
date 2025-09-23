"""
Tests for Alert Manager functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from io import StringIO
import sys

from src.monitoring.alert_manager import (
    AlertManager, AlertRule, AlertChannel, AlertHistory,
    send_alert, send_alerts, get_alert_manager
)
from src.monitoring.models import HealthAlert, AlertLevel


class TestAlertManager:
    """Test Alert Manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.alert_manager = AlertManager()
    
    def test_alert_manager_initialization(self):
        """Test alert manager initialization."""
        assert len(self.alert_manager._alert_rules) > 0
        assert AlertChannel.LOG in self.alert_manager._alert_handlers
        assert AlertChannel.CONSOLE in self.alert_manager._alert_handlers
        assert len(self.alert_manager._alert_history) == 0
        assert len(self.alert_manager._suppressed_alerts) == 0
    
    def test_pattern_matching(self):
        """Test component pattern matching."""
        # Exact match
        assert self.alert_manager._matches_pattern("scheduler", "scheduler")
        assert not self.alert_manager._matches_pattern("scheduler", "api")
        
        # Wildcard match
        assert self.alert_manager._matches_pattern("scheduler.hot", "scheduler*")
        assert self.alert_manager._matches_pattern("api.dexscreener", "*api*")
        assert self.alert_manager._matches_pattern("anything", "*")
        
        # Prefix/suffix wildcards
        assert self.alert_manager._matches_pattern("test.component", "*component")
        assert not self.alert_manager._matches_pattern("component.test", "*component")
    
    def test_alert_key_generation(self):
        """Test alert key generation for deduplication."""
        alert1 = HealthAlert(
            level=AlertLevel.ERROR,
            message="Test error message",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        alert2 = HealthAlert(
            level=AlertLevel.ERROR,
            message="Test error message",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-2"  # Different correlation ID
        )
        
        alert3 = HealthAlert(
            level=AlertLevel.WARNING,
            message="Test error message",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-3"
        )
        
        key1 = self.alert_manager._generate_alert_key(alert1)
        key2 = self.alert_manager._generate_alert_key(alert2)
        key3 = self.alert_manager._generate_alert_key(alert3)
        
        # Same component, level, and message should generate same key
        assert key1 == key2
        
        # Different level should generate different key
        assert key1 != key3
    
    def test_find_matching_rule(self):
        """Test finding matching alert rules."""
        alert = HealthAlert(
            level=AlertLevel.ERROR,
            message="Scheduler error",
            component="scheduler.hot",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        rule = self.alert_manager._find_matching_rule(alert)
        assert rule is not None
        assert rule.min_level.value <= AlertLevel.ERROR.value
        
        # Test with info level alert
        info_alert = HealthAlert(
            level=AlertLevel.INFO,
            message="Info message",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-2"
        )
        
        info_rule = self.alert_manager._find_matching_rule(info_alert)
        assert info_rule is not None
        assert info_rule.min_level == AlertLevel.INFO
    
    def test_alert_suppression_cooldown(self):
        """Test alert suppression due to cooldown."""
        alert = HealthAlert(
            level=AlertLevel.WARNING,
            message="Test warning",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        rule = AlertRule(
            component_pattern="*",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=5,
            max_frequency_per_hour=10
        )
        
        # First alert should not be suppressed
        assert not self.alert_manager._should_suppress_alert(alert, rule)
        
        # Second alert immediately after should be suppressed
        assert self.alert_manager._should_suppress_alert(alert, rule)
        
        # Simulate time passing beyond cooldown
        alert_key = self.alert_manager._generate_alert_key(alert)
        history = self.alert_manager._alert_history[alert_key]
        history.last_sent = datetime.utcnow() - timedelta(minutes=6)
        
        # Should not be suppressed after cooldown
        assert not self.alert_manager._should_suppress_alert(alert, rule)
    
    def test_alert_suppression_frequency(self):
        """Test alert suppression due to frequency limits."""
        alert = HealthAlert(
            level=AlertLevel.WARNING,
            message="Frequent warning",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        rule = AlertRule(
            component_pattern="*",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=0,  # No cooldown
            max_frequency_per_hour=2  # Low frequency limit
        )
        
        # First two alerts should pass
        assert not self.alert_manager._should_suppress_alert(alert, rule)
        assert not self.alert_manager._should_suppress_alert(alert, rule)
        
        # Third alert should be suppressed due to frequency limit
        assert self.alert_manager._should_suppress_alert(alert, rule)
    
    @patch('builtins.print')
    def test_console_alert_handler(self, mock_print):
        """Test console alert handler."""
        alert = HealthAlert(
            level=AlertLevel.ERROR,
            message="Test console alert",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1",
            context={"key": "value"}
        )
        
        rule = AlertRule(
            component_pattern="*",
            min_level=AlertLevel.ERROR,
            channels=[AlertChannel.CONSOLE]
        )
        
        self.alert_manager._handle_console_alert(alert, rule)
        
        # Verify print was called
        assert mock_print.called
        
        # Check that the alert information was printed
        printed_text = ''.join(call.args[0] for call in mock_print.call_args_list)
        assert "ERROR" in printed_text
        assert "Test console alert" in printed_text
        assert "test.component" in printed_text
    
    @patch('src.monitoring.alert_manager.log')
    def test_log_alert_handler(self, mock_log):
        """Test log alert handler."""
        alert = HealthAlert(
            level=AlertLevel.WARNING,
            message="Test log alert",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        rule = AlertRule(
            component_pattern="*",
            min_level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG]
        )
        
        self.alert_manager._handle_log_alert(alert, rule)
        
        # Verify log was called with correct level
        mock_log.log.assert_called_once()
        call_args = mock_log.log.call_args
        assert call_args[0][0] == 30  # WARNING level
        assert call_args[0][1] == "alert_triggered"
    
    def test_send_alert_success(self):
        """Test successful alert sending."""
        alert = HealthAlert(
            level=AlertLevel.ERROR,
            message="Test alert",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        # Test that alert is sent successfully (returns True)
        result = self.alert_manager.send_alert(alert)
        assert result is True
        
        # Verify that alert history was created
        alert_key = self.alert_manager._generate_alert_key(alert)
        assert alert_key in self.alert_manager._alert_history
        
        # Verify history details
        history = self.alert_manager._alert_history[alert_key]
        assert history.total_count == 1
        assert history.count_last_hour == 1
    
    def test_send_alert_no_matching_rule(self):
        """Test alert sending with no matching rule."""
        # Clear all rules
        self.alert_manager._alert_rules = []
        
        alert = HealthAlert(
            level=AlertLevel.ERROR,
            message="Test alert",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        result = self.alert_manager.send_alert(alert)
        assert result is False
    
    def test_send_multiple_alerts(self):
        """Test sending multiple alerts."""
        alerts = [
            HealthAlert(
                level=AlertLevel.ERROR,
                message=f"Test alert {i}",
                component="test.component",
                timestamp=datetime.utcnow(),
                correlation_id=f"test-{i}"
            )
            for i in range(3)
        ]
        
        with patch.object(self.alert_manager, 'send_alert', return_value=True) as mock_send:
            sent_count = self.alert_manager.send_alerts(alerts)
            
            assert sent_count == 3
            assert mock_send.call_count == 3
    
    def test_manual_alert_suppression(self):
        """Test manual alert suppression."""
        component = "test.component"
        level = AlertLevel.WARNING
        message_pattern = "Test warning"
        
        # Suppress alerts
        self.alert_manager.suppress_alert(component, level, message_pattern)
        
        # Create matching alert
        alert = HealthAlert(
            level=level,
            message=message_pattern,
            component=component,
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        rule = AlertRule(
            component_pattern="*",
            min_level=level,
            cooldown_minutes=0
        )
        
        # Alert should be suppressed
        assert self.alert_manager._should_suppress_alert(alert, rule)
        
        # Unsuppress alerts
        self.alert_manager.unsuppress_alert(component, level, message_pattern)
        
        # Alert should not be suppressed anymore
        assert not self.alert_manager._should_suppress_alert(alert, rule)
    
    def test_add_remove_alert_rules(self):
        """Test adding and removing alert rules."""
        initial_count = len(self.alert_manager._alert_rules)
        
        # Add new rule
        new_rule = AlertRule(
            component_pattern="custom.*",
            min_level=AlertLevel.ERROR,
            cooldown_minutes=1,
            channels=[AlertChannel.LOG]
        )
        
        self.alert_manager.add_alert_rule(new_rule)
        assert len(self.alert_manager._alert_rules) == initial_count + 1
        
        # Remove rule
        removed = self.alert_manager.remove_alert_rule("custom.*", AlertLevel.ERROR)
        assert removed is True
        assert len(self.alert_manager._alert_rules) == initial_count
        
        # Try to remove non-existent rule
        removed = self.alert_manager.remove_alert_rule("nonexistent", AlertLevel.CRITICAL)
        assert removed is False
    
    def test_custom_alert_handler(self):
        """Test adding custom alert handler."""
        custom_handler_called = False
        
        def custom_handler(alert: HealthAlert, rule: AlertRule):
            nonlocal custom_handler_called
            custom_handler_called = True
        
        # Add custom channel (simulate extending enum)
        custom_channel = AlertChannel.LOG  # Use existing channel for test
        
        self.alert_manager.add_alert_handler(custom_channel, custom_handler)
        
        alert = HealthAlert(
            level=AlertLevel.ERROR,
            message="Test custom handler",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="test-1"
        )
        
        # Send alert
        self.alert_manager.send_alert(alert)
        
        assert custom_handler_called
    
    def test_alert_statistics(self):
        """Test alert statistics generation."""
        # Send some test alerts
        for i in range(3):
            alert = HealthAlert(
                level=AlertLevel.WARNING,
                message=f"Test alert {i}",
                component="test.component",
                timestamp=datetime.utcnow(),
                correlation_id=f"test-{i}"
            )
            self.alert_manager.send_alert(alert)
        
        stats = self.alert_manager.get_alert_statistics()
        
        assert "total_unique_alerts" in stats
        assert "recent_alerts_last_hour" in stats
        assert "alerts_by_level_last_24h" in stats
        assert "alerts_by_component_last_24h" in stats
        assert "available_channels" in stats
        assert stats["total_unique_alerts"] >= 3
    
    def test_cleanup_old_history(self):
        """Test cleanup of old alert history."""
        # Add some old history entries
        old_time = datetime.utcnow() - timedelta(days=10)
        
        for i in range(5):
            history = AlertHistory(
                alert_key=f"old_alert_{i}",
                last_sent=old_time,
                first_occurrence=old_time,
                last_occurrence=old_time
            )
            self.alert_manager._alert_history[f"old_alert_{i}"] = history
        
        # Add recent history
        recent_time = datetime.utcnow()
        recent_history = AlertHistory(
            alert_key="recent_alert",
            last_sent=recent_time,
            first_occurrence=recent_time,
            last_occurrence=recent_time
        )
        self.alert_manager._alert_history["recent_alert"] = recent_history
        
        initial_count = len(self.alert_manager._alert_history)
        
        # Cleanup old history (keep 7 days)
        removed_count = self.alert_manager.cleanup_old_history(days_to_keep=7)
        
        assert removed_count == 5
        assert len(self.alert_manager._alert_history) == initial_count - 5
        assert "recent_alert" in self.alert_manager._alert_history


class TestAlertManagerGlobalFunctions:
    """Test global alert manager functions."""
    
    def test_send_alert_global_function(self):
        """Test global send_alert function."""
        alert = HealthAlert(
            level=AlertLevel.INFO,
            message="Global test alert",
            component="test.component",
            timestamp=datetime.utcnow(),
            correlation_id="global-test-1"
        )
        
        with patch.object(get_alert_manager(), 'send_alert', return_value=True) as mock_send:
            result = send_alert(alert)
            
            assert result is True
            mock_send.assert_called_once_with(alert)
    
    def test_send_alerts_global_function(self):
        """Test global send_alerts function."""
        alerts = [
            HealthAlert(
                level=AlertLevel.INFO,
                message=f"Global test alert {i}",
                component="test.component",
                timestamp=datetime.utcnow(),
                correlation_id=f"global-test-{i}"
            )
            for i in range(2)
        ]
        
        with patch.object(get_alert_manager(), 'send_alerts', return_value=2) as mock_send:
            result = send_alerts(alerts)
            
            assert result == 2
            mock_send.assert_called_once_with(alerts)
    
    def test_get_alert_manager_function(self):
        """Test get_alert_manager function."""
        manager = get_alert_manager()
        assert isinstance(manager, AlertManager)
        
        # Should return the same instance (singleton-like behavior)
        manager2 = get_alert_manager()
        assert manager is manager2