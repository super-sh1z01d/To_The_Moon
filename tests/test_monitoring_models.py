"""
Tests for monitoring data models and metrics collection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.monitoring.models import (
    HealthStatus, AlertLevel, CircuitState, HealthAlert,
    SchedulerHealth, ResourceHealth, APIHealth, SystemHealth,
    PerformanceMetrics, PerformanceAlert, MonitoringConfig
)
from src.monitoring.metrics import (
    MetricsCollector, PerformanceAnalyzer, 
    create_correlation_id, aggregate_health_status
)


class TestHealthModels:
    """Test health monitoring data models."""
    
    def test_health_alert_creation(self):
        """Test HealthAlert model creation."""
        alert = HealthAlert(
            level=AlertLevel.WARNING,
            message="Test alert",
            component="test.component",
            timestamp=datetime.utcnow()
        )
        
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test alert"
        assert alert.component == "test.component"
        assert alert.correlation_id is None
        assert alert.context == {}
    
    def test_scheduler_health_defaults(self):
        """Test SchedulerHealth model with defaults."""
        health = SchedulerHealth(
            status=HealthStatus.HEALTHY,
            hot_group_last_run=datetime.utcnow(),
            cold_group_last_run=datetime.utcnow(),
            hot_group_processing_time=30.0,
            cold_group_processing_time=120.0,
            tokens_processed_per_minute=5.0,
            error_rate=2.5,
            active_jobs=3,
            failed_jobs_last_hour=1
        )
        
        assert health.status == HealthStatus.HEALTHY
        assert health.tokens_processed_per_minute == 5.0
        assert health.error_rate == 2.5
        assert len(health.alerts) == 0
        assert isinstance(health.last_check, datetime)
    
    def test_resource_health_creation(self):
        """Test ResourceHealth model creation."""
        health = ResourceHealth(
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
        
        assert health.memory_usage_mb == 512.0
        assert health.cpu_usage_percent == 25.0
        assert health.status == HealthStatus.HEALTHY
    
    def test_api_health_creation(self):
        """Test APIHealth model creation."""
        health = APIHealth(
            service_name="dexscreener",
            status=HealthStatus.HEALTHY,
            average_response_time=150.0,
            p95_response_time=300.0,
            error_rate=1.0,
            circuit_breaker_state=CircuitState.CLOSED,
            cache_hit_rate=85.0,
            requests_per_minute=30.0,
            last_successful_call=datetime.utcnow(),
            consecutive_failures=0
        )
        
        assert health.service_name == "dexscreener"
        assert health.circuit_breaker_state == CircuitState.CLOSED
        assert health.cache_hit_rate == 85.0
    
    def test_system_health_aggregation(self):
        """Test SystemHealth alert aggregation."""
        scheduler_alert = HealthAlert(
            level=AlertLevel.WARNING,
            message="Scheduler slow",
            component="scheduler",
            timestamp=datetime.utcnow()
        )
        
        resource_alert = HealthAlert(
            level=AlertLevel.CRITICAL,
            message="Memory high",
            component="resources",
            timestamp=datetime.utcnow()
        )
        
        scheduler_health = SchedulerHealth(
            status=HealthStatus.DEGRADED,
            hot_group_last_run=datetime.utcnow(),
            cold_group_last_run=datetime.utcnow(),
            hot_group_processing_time=30.0,
            cold_group_processing_time=120.0,
            tokens_processed_per_minute=5.0,
            error_rate=2.5,
            active_jobs=3,
            failed_jobs_last_hour=1,
            alerts=[scheduler_alert]
        )
        
        resource_health = ResourceHealth(
            memory_usage_mb=900.0,
            memory_usage_percent=90.0,
            cpu_usage_percent=25.0,
            disk_usage_percent=60.0,
            database_connections=5,
            max_database_connections=20,
            open_file_descriptors=100,
            max_file_descriptors=1024,
            status=HealthStatus.CRITICAL,
            alerts=[resource_alert]
        )
        
        system_health = SystemHealth(
            overall_status=HealthStatus.CRITICAL,
            scheduler=scheduler_health,
            resources=resource_health,
            apis={},
            uptime_seconds=3600.0,
            last_restart=None
        )
        
        all_alerts = system_health.get_all_alerts()
        assert len(all_alerts) == 2
        
        critical_alerts = system_health.get_critical_alerts()
        assert len(critical_alerts) == 1
        assert critical_alerts[0].level == AlertLevel.CRITICAL


class TestPerformanceModels:
    """Test performance monitoring models."""
    
    def test_performance_metrics_calculations(self):
        """Test PerformanceMetrics calculations."""
        metrics = PerformanceMetrics(
            component="test",
            timestamp=datetime.utcnow(),
            api_response_times=[100.0, 150.0, 200.0, 120.0, 180.0],
            processing_times=[30.0, 45.0, 35.0, 40.0]
        )
        
        avg_response = metrics.get_avg_api_response_time()
        assert avg_response == 150.0
        
        p95_response = metrics.get_p95_api_response_time()
        assert p95_response == 200.0  # 95th percentile of sorted [100, 120, 150, 180, 200]
        
        avg_processing = metrics.get_avg_processing_time()
        assert avg_processing == 37.5
    
    def test_performance_alert_creation(self):
        """Test PerformanceAlert creation."""
        alert = PerformanceAlert(
            metric_name="api_response_time",
            current_value=2500.0,
            threshold_value=2000.0,
            severity=AlertLevel.WARNING,
            message="API response time high",
            trend_direction="increasing"
        )
        
        assert alert.metric_name == "api_response_time"
        assert alert.current_value == 2500.0
        assert alert.severity == AlertLevel.WARNING
        assert alert.trend_direction == "increasing"


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    @patch('src.monitoring.metrics.psutil')
    def test_collect_resource_metrics(self, mock_psutil):
        """Test resource metrics collection."""
        # Mock psutil responses
        mock_memory = MagicMock()
        mock_memory.used = 512 * 1024 * 1024  # 512 MB
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_psutil.cpu_percent.return_value = 25.0
        
        mock_disk = MagicMock()
        mock_disk.used = 50 * 1024 * 1024 * 1024  # 50 GB
        mock_disk.total = 100 * 1024 * 1024 * 1024  # 100 GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_process = MagicMock()
        mock_process.num_fds.return_value = 100
        mock_psutil.Process.return_value = mock_process
        
        config = MonitoringConfig()
        collector = MetricsCollector(config)
        
        health = collector.collect_resource_metrics()
        
        assert health.memory_usage_mb == 512.0
        assert health.cpu_usage_percent == 25.0
        assert health.disk_usage_percent == 50.0
        assert health.status == HealthStatus.HEALTHY
        assert len(health.alerts) == 0
    
    @patch('src.monitoring.metrics.psutil')
    def test_resource_alerts_generation(self, mock_psutil):
        """Test resource alert generation."""
        # Mock high resource usage
        mock_memory = MagicMock()
        mock_memory.used = 900 * 1024 * 1024  # 900 MB (above warning threshold)
        mock_memory.percent = 90.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_psutil.cpu_percent.return_value = 85.0  # Above critical threshold
        
        mock_disk = MagicMock()
        mock_disk.used = 85 * 1024 * 1024 * 1024  # 85 GB
        mock_disk.total = 100 * 1024 * 1024 * 1024  # 100 GB (85% usage)
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_process = MagicMock()
        mock_process.num_fds.return_value = 100
        mock_psutil.Process.return_value = mock_process
        
        config = MonitoringConfig()
        collector = MetricsCollector(config)
        
        health = collector.collect_resource_metrics()
        
        assert health.status == HealthStatus.CRITICAL
        assert len(health.alerts) == 3  # Memory warning, CPU critical, Disk warning
        
        # Check alert levels
        alert_levels = [alert.level for alert in health.alerts]
        assert AlertLevel.WARNING in alert_levels
        assert AlertLevel.CRITICAL in alert_levels


class TestPerformanceAnalyzer:
    """Test performance analysis functionality."""
    
    def test_trend_analysis(self):
        """Test trend analysis for metrics."""
        config = MonitoringConfig()
        analyzer = PerformanceAnalyzer(config)
        
        # Add increasing trend data
        for i, value in enumerate([100, 110, 120, 130, 140]):
            analyzer.add_metric("test", "response_time", value)
        
        trend, slope = analyzer.analyze_trends("test", "response_time")
        assert trend == "increasing"
        assert slope > 0
        
        # Add decreasing trend data
        for value in [140, 130, 120, 110, 100]:
            analyzer.add_metric("test2", "response_time", value)
        
        trend, slope = analyzer.analyze_trends("test2", "response_time")
        assert trend == "decreasing"
        assert slope < 0
    
    def test_performance_issue_detection(self):
        """Test performance issue detection."""
        config = MonitoringConfig()
        analyzer = PerformanceAnalyzer(config)
        
        # Create metrics with high response times
        metrics = PerformanceMetrics(
            component="test",
            timestamp=datetime.utcnow(),
            api_response_times=[2500.0, 2600.0, 2700.0],  # Above warning threshold
            api_success_rate=75.0  # 25% error rate - above critical threshold
        )
        
        alerts = analyzer.detect_performance_issues(metrics)
        
        assert len(alerts) >= 2  # Response time and error rate alerts
        
        # Check for response time alert
        response_time_alerts = [a for a in alerts if a.metric_name == "api_response_time"]
        assert len(response_time_alerts) == 1
        assert response_time_alerts[0].severity == AlertLevel.WARNING
        
        # Check for error rate alert
        error_rate_alerts = [a for a in alerts if a.metric_name == "api_error_rate"]
        assert len(error_rate_alerts) == 1
        assert error_rate_alerts[0].severity == AlertLevel.CRITICAL


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_correlation_id(self):
        """Test correlation ID creation."""
        id1 = create_correlation_id()
        id2 = create_correlation_id()
        
        assert len(id1) == 8
        assert len(id2) == 8
        assert id1 != id2
    
    def test_aggregate_health_status(self):
        """Test health status aggregation."""
        # All healthy
        statuses = [HealthStatus.HEALTHY, HealthStatus.HEALTHY]
        assert aggregate_health_status(statuses) == HealthStatus.HEALTHY
        
        # Mixed with degraded
        statuses = [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert aggregate_health_status(statuses) == HealthStatus.DEGRADED
        
        # Mixed with critical
        statuses = [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.CRITICAL]
        assert aggregate_health_status(statuses) == HealthStatus.CRITICAL
        
        # Empty list
        assert aggregate_health_status([]) == HealthStatus.UNKNOWN