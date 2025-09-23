"""
Tests for the enhanced health monitoring system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.models import (
    HealthStatus, AlertLevel, CircuitState, MonitoringConfig
)


class TestHealthMonitor:
    """Test the main HealthMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = MonitoringConfig(
            health_check_interval=30,
            api_response_time_warning=1000.0,
            api_response_time_critical=2000.0,
            api_error_rate_warning=10.0,
            api_error_rate_critical=20.0
        )
        self.monitor = HealthMonitor(self.config)
    
    def test_health_monitor_initialization(self):
        """Test HealthMonitor initialization."""
        assert self.monitor.config == self.config
        assert self.monitor.metrics_collector is not None
        assert self.monitor.performance_analyzer is not None
        assert len(self.monitor._scheduler_execution_history) == 0
        assert len(self.monitor._api_call_history) == 0
    
    def test_record_scheduler_execution(self):
        """Test recording scheduler execution."""
        self.monitor.record_scheduler_execution("hot", 10, 8, 25.5)
        
        hot_history = self.monitor._scheduler_execution_history["hot"]
        assert len(hot_history) == 1
        assert isinstance(hot_history[0], datetime)
    
    def test_record_api_call(self):
        """Test recording API call."""
        self.monitor.record_api_call("dexscreener", True, 150.0)
        self.monitor.record_api_call("dexscreener", False, 5000.0, "Timeout")
        
        history = self.monitor._api_call_history["dexscreener"]
        assert len(history) == 2
        
        assert history[0]["success"] is True
        assert history[0]["response_time"] == 150.0
        assert history[0]["error"] is None
        
        assert history[1]["success"] is False
        assert history[1]["response_time"] == 5000.0
        assert history[1]["error"] == "Timeout"
    
    @pytest.mark.asyncio
    async def test_monitor_scheduler_health_no_executions(self):
        """Test scheduler health monitoring with no executions."""
        health = await self.monitor.monitor_scheduler_health()
        
        assert health.status == HealthStatus.CRITICAL
        assert health.hot_group_last_run is None
        assert health.cold_group_last_run is None
        assert len(health.alerts) >= 2  # Should have alerts for both groups never executing
        
        # Check for critical alerts
        critical_alerts = [alert for alert in health.alerts if alert.level == AlertLevel.CRITICAL]
        assert len(critical_alerts) >= 2
    
    @pytest.mark.asyncio
    async def test_monitor_scheduler_health_with_executions(self):
        """Test scheduler health monitoring with recent executions."""
        # Record recent executions
        now = datetime.utcnow()
        self.monitor._scheduler_execution_history["hot"] = [now - timedelta(seconds=10)]
        self.monitor._scheduler_execution_history["cold"] = [now - timedelta(seconds=20)]
        
        health = await self.monitor.monitor_scheduler_health()
        
        assert health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert health.hot_group_last_run is not None
        assert health.cold_group_last_run is not None
        
        # Should have fewer critical alerts
        critical_alerts = [alert for alert in health.alerts if alert.level == AlertLevel.CRITICAL]
        assert len(critical_alerts) == 0  # Recent executions, so no critical alerts
    
    @pytest.mark.asyncio
    async def test_monitor_scheduler_health_delayed_executions(self):
        """Test scheduler health monitoring with delayed executions."""
        # Record old executions (beyond threshold)
        old_time = datetime.utcnow() - timedelta(seconds=120)  # 2 minutes ago
        self.monitor._scheduler_execution_history["hot"] = [old_time]
        self.monitor._scheduler_execution_history["cold"] = [old_time]
        
        health = await self.monitor.monitor_scheduler_health()
        
        assert health.status in [HealthStatus.DEGRADED, HealthStatus.CRITICAL]
        
        # Should have alerts for delayed executions
        delay_alerts = [alert for alert in health.alerts if "delayed" in alert.message.lower()]
        assert len(delay_alerts) >= 1
    
    @pytest.mark.asyncio
    @patch('src.monitoring.health_monitor.MetricsCollector')
    async def test_monitor_resource_usage(self, mock_collector_class):
        """Test resource usage monitoring."""
        # Mock the metrics collector
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        
        from src.monitoring.models import ResourceHealth
        mock_resource_health = ResourceHealth(
            memory_usage_mb=512.0,
            memory_usage_percent=50.0,
            cpu_usage_percent=25.0,
            disk_usage_percent=60.0,
            database_connections=5,
            max_database_connections=20,
            open_file_descriptors=100,
            max_file_descriptors=1024,
            status=HealthStatus.HEALTHY
        )
        mock_collector.collect_resource_metrics.return_value = mock_resource_health
        
        # Create new monitor with mocked collector
        monitor = HealthMonitor(self.config)
        monitor.metrics_collector = mock_collector
        
        health = await monitor.monitor_resource_usage()
        
        assert health.status == HealthStatus.HEALTHY
        assert health.memory_usage_mb == 512.0
        assert health.cpu_usage_percent == 25.0
        mock_collector.collect_resource_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_api_health_no_history(self):
        """Test API health monitoring with no call history."""
        health = await self.monitor.monitor_api_health("dexscreener")
        
        assert health.service_name == "dexscreener"
        assert health.status == HealthStatus.UNKNOWN
        assert health.average_response_time == 0.0
        assert health.error_rate == 0.0
        assert health.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_monitor_api_health_with_successful_calls(self):
        """Test API health monitoring with successful API calls."""
        now = datetime.utcnow()
        
        # Add successful API calls
        for i in range(10):
            call_time = now - timedelta(minutes=i)
            self.monitor._api_call_history["dexscreener"].append({
                "timestamp": call_time,
                "success": True,
                "response_time": 100.0 + i * 10,  # 100-190ms
                "error": None
            })
        
        health = await self.monitor.monitor_api_health("dexscreener")
        
        assert health.service_name == "dexscreener"
        assert health.status == HealthStatus.HEALTHY
        assert health.average_response_time > 0
        assert health.error_rate == 0.0
        assert health.consecutive_failures == 0
        assert health.circuit_breaker_state == CircuitState.CLOSED
        assert len(health.alerts) == 0
    
    @pytest.mark.asyncio
    async def test_monitor_api_health_with_failures(self):
        """Test API health monitoring with API failures."""
        now = datetime.utcnow()
        
        # Add mix of successful and failed calls
        for i in range(10):
            call_time = now - timedelta(minutes=i)
            success = i < 3  # First 3 are successful, rest fail
            self.monitor._api_call_history["dexscreener"].append({
                "timestamp": call_time,
                "success": success,
                "response_time": 2500.0 if not success else 150.0,
                "error": "Timeout" if not success else None
            })
        
        health = await self.monitor.monitor_api_health("dexscreener")
        
        assert health.service_name == "dexscreener"
        assert health.status in [HealthStatus.DEGRADED, HealthStatus.CRITICAL]
        assert health.error_rate > 50.0  # 70% failure rate
        assert health.consecutive_failures == 7  # Last 7 calls failed
        assert health.circuit_breaker_state in [CircuitState.HALF_OPEN, CircuitState.OPEN]
        assert len(health.alerts) > 0
    
    @pytest.mark.asyncio
    async def test_monitor_api_health_high_response_times(self):
        """Test API health monitoring with high response times."""
        now = datetime.utcnow()
        
        # Add calls with high response times
        for i in range(5):
            call_time = now - timedelta(minutes=i)
            self.monitor._api_call_history["dexscreener"].append({
                "timestamp": call_time,
                "success": True,
                "response_time": 2500.0,  # Above critical threshold
                "error": None
            })
        
        health = await self.monitor.monitor_api_health("dexscreener")
        
        assert health.status in [HealthStatus.DEGRADED, HealthStatus.CRITICAL]
        assert health.average_response_time >= self.config.api_response_time_critical
        
        # Should have response time alerts
        response_time_alerts = [
            alert for alert in health.alerts 
            if "response time" in alert.message.lower()
        ]
        assert len(response_time_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_health(self):
        """Test comprehensive health status aggregation."""
        # Add some execution history to avoid critical scheduler status
        now = datetime.utcnow()
        self.monitor._scheduler_execution_history["hot"] = [now - timedelta(seconds=10)]
        self.monitor._scheduler_execution_history["cold"] = [now - timedelta(seconds=20)]
        
        # Add some successful API calls
        for i in range(5):
            self.monitor._api_call_history["dexscreener"].append({
                "timestamp": now - timedelta(minutes=i),
                "success": True,
                "response_time": 150.0,
                "error": None
            })
        
        with patch.object(self.monitor, 'monitor_resource_usage') as mock_resource:
            from src.monitoring.models import ResourceHealth
            mock_resource.return_value = ResourceHealth(
                memory_usage_mb=512.0,
                memory_usage_percent=50.0,
                cpu_usage_percent=25.0,
                disk_usage_percent=60.0,
                database_connections=5,
                max_database_connections=20,
                open_file_descriptors=100,
                max_file_descriptors=1024,
                status=HealthStatus.HEALTHY
            )
            
            health = await self.monitor.get_comprehensive_health_async()
        
        assert health.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert health.scheduler is not None
        assert health.resources is not None
        assert "dexscreener" in health.apis
        assert health.uptime_seconds > 0
        
        # Test alert aggregation
        all_alerts = health.get_all_alerts()
        assert isinstance(all_alerts, list)
        
        critical_alerts = health.get_critical_alerts()
        assert isinstance(critical_alerts, list)
    
    def test_alert_cooldown(self):
        """Test alert cooldown functionality."""
        alert_key = "test_alert"
        
        # First alert should be sent
        assert self.monitor._should_send_alert(alert_key) is True
        
        # Immediate second alert should be blocked
        assert self.monitor._should_send_alert(alert_key) is False
        
        # Simulate cooldown period passing
        past_time = datetime.utcnow() - timedelta(seconds=self.config.alert_cooldown + 1)
        self.monitor._alert_cooldowns[alert_key] = past_time
        
        # Alert should be sent again after cooldown
        assert self.monitor._should_send_alert(alert_key) is True
    
    def test_scheduler_execution_history_limit(self):
        """Test that scheduler execution history is limited."""
        # Add more than 50 executions
        for i in range(60):
            self.monitor.record_scheduler_execution("hot", 10, 8, 25.0)
        
        # Should only keep last 50
        hot_history = self.monitor._scheduler_execution_history["hot"]
        assert len(hot_history) == 50
    
    def test_api_call_history_limit(self):
        """Test that API call history is limited."""
        # Add more than 100 API calls
        for i in range(120):
            self.monitor.record_api_call("dexscreener", True, 150.0)
        
        # Should only keep last 100
        history = self.monitor._api_call_history["dexscreener"]
        assert len(history) == 100