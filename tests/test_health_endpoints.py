"""
Tests for health monitoring endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.app.main import app
from src.monitoring.models import (
    HealthStatus, AlertLevel, CircuitState, HealthAlert,
    SchedulerHealth, ResourceHealth, APIHealth, SystemHealth
)


class TestHealthEndpoints:
    """Test health monitoring endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    @patch('src.app.routes.health.health_monitor')
    def test_basic_health_endpoint(self, mock_health_monitor):
        """Test basic health endpoint."""
        # Mock system health
        mock_system_health = MagicMock()
        mock_system_health.overall_status = HealthStatus.HEALTHY
        mock_system_health.timestamp = datetime.utcnow()
        mock_system_health.uptime_seconds = 3600.0
        
        mock_health_monitor.get_comprehensive_health_async = AsyncMock(return_value=mock_system_health)
        
        response = self.client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["uptime_seconds"] == 3600.0
        assert "System operational" in data["message"]
    
    @patch('src.app.routes.health.health_monitor')
    def test_basic_health_endpoint_degraded(self, mock_health_monitor):
        """Test basic health endpoint with degraded status."""
        # Mock degraded system health
        mock_system_health = MagicMock()
        mock_system_health.overall_status = HealthStatus.DEGRADED
        mock_system_health.timestamp = datetime.utcnow()
        mock_system_health.uptime_seconds = 1800.0
        
        mock_health_monitor.get_comprehensive_health_async = AsyncMock(return_value=mock_system_health)
        
        response = self.client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert "System degraded" in data["message"]
    
    @patch('src.app.routes.health.health_monitor')
    def test_detailed_health_endpoint(self, mock_health_monitor):
        """Test detailed health endpoint."""
        # Create mock components
        scheduler_health = SchedulerHealth(
            status=HealthStatus.HEALTHY,
            hot_group_last_run=datetime.utcnow(),
            cold_group_last_run=datetime.utcnow(),
            hot_group_processing_time=30.0,
            cold_group_processing_time=120.0,
            tokens_processed_per_minute=5.0,
            error_rate=2.0,
            active_jobs=3,
            failed_jobs_last_hour=1
        )
        
        resource_health = ResourceHealth(
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
        
        api_health = APIHealth(
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
        
        mock_system_health = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            scheduler=scheduler_health,
            resources=resource_health,
            apis={"dexscreener": api_health},
            uptime_seconds=3600.0,
            last_restart=None
        )
        
        mock_health_monitor.get_comprehensive_health_async = AsyncMock(return_value=mock_system_health)
        
        response = self.client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "components" in data
        assert "scheduler" in data["components"]
        assert "resources" in data["components"]
        assert "apis" in data["components"]
        assert "alerts" in data
        assert "statistics" in data
        
        # Check scheduler component
        scheduler = data["components"]["scheduler"]
        assert scheduler["status"] == "healthy"
        assert scheduler["tokens_processed_per_minute"] == 5.0
        assert scheduler["error_rate"] == 2.0
        
        # Check resources component
        resources = data["components"]["resources"]
        assert resources["status"] == "healthy"
        assert resources["memory_usage_mb"] == 512.0
        assert resources["cpu_usage_percent"] == 25.0
        
        # Check APIs component
        apis = data["components"]["apis"]
        assert "dexscreener" in apis
        assert apis["dexscreener"]["status"] == "healthy"
        assert apis["dexscreener"]["average_response_time"] == 150.0
    
    @patch('src.monitoring.health_monitor.HealthMonitor.monitor_scheduler_health')
    def test_scheduler_health_endpoint(self, mock_monitor_scheduler_health):
        """Test scheduler health endpoint."""
        # Mock scheduler health
        scheduler_health = SchedulerHealth(
            status=HealthStatus.HEALTHY,
            hot_group_last_run=datetime.utcnow(),
            cold_group_last_run=datetime.utcnow(),
            hot_group_processing_time=30.0,
            cold_group_processing_time=120.0,
            tokens_processed_per_minute=5.0,
            error_rate=2.0,
            active_jobs=3,
            failed_jobs_last_hour=1
        )
        
        mock_monitor_scheduler_health.return_value = scheduler_health
        
        response = self.client.get("/health/scheduler")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "hot_group" in data
        assert "cold_group" in data
        assert "performance" in data
        assert data["performance"]["tokens_processed_per_minute"] == 5.0
        assert data["performance"]["error_rate"] == 2.0
    
    @patch('src.monitoring.health_monitor.HealthMonitor.monitor_resource_usage')
    def test_resource_health_endpoint(self, mock_monitor_resource_usage):
        """Test resource health endpoint."""
        # Mock resource health
        resource_health = ResourceHealth(
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
        
        mock_monitor_resource_usage.return_value = resource_health
        
        response = self.client.get("/health/resources")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["memory"]["usage_mb"] == 512.0
        assert data["cpu"]["usage_percent"] == 25.0
        assert data["database"]["connections"] == 5
    
    @patch('src.monitoring.health_monitor.HealthMonitor.monitor_api_health')
    @patch('src.app.routes.health.get_resilient_dexscreener_client')
    def test_apis_health_endpoint(self, mock_get_client, mock_monitor_api_health):
        """Test APIs health endpoint."""
        # Mock API health
        api_health = APIHealth(
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
        
        # Mock resilient client
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {"total_requests": 100, "success_rate": 99.0}
        mock_get_client.return_value = mock_client
        
        mock_monitor_api_health.return_value = api_health
        
        response = self.client.get("/health/apis")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dexscreener" in data
        assert data["dexscreener"]["status"] == "healthy"
        assert data["dexscreener"]["performance"]["average_response_time"] == 150.0
        assert data["dexscreener"]["circuit_breaker"]["state"] == "closed"
        assert "client_stats" in data["dexscreener"]
    
    @patch('src.app.routes.health.get_all_circuit_breakers')
    @patch('src.app.routes.health.get_circuit_breaker_stats')
    def test_circuit_breakers_endpoint(self, mock_get_stats, mock_get_breakers):
        """Test circuit breakers status endpoint."""
        # Mock circuit breakers
        mock_breaker = MagicMock()
        mock_breaker.state.value = "closed"
        mock_breaker.is_closed = True
        mock_breaker.is_open = False
        mock_breaker.is_half_open = False
        mock_breaker.failure_rate = 2.0
        
        mock_get_breakers.return_value = {"dexscreener": mock_breaker}
        mock_get_stats.return_value = {"dexscreener": {"total_calls": 100, "failures": 2}}
        
        response = self.client.get("/health/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "circuit_breakers" in data
        assert "dexscreener" in data["circuit_breakers"]
        assert data["circuit_breakers"]["dexscreener"]["state"] == "closed"
        assert data["circuit_breakers"]["dexscreener"]["is_healthy"] is True
        assert "summary" in data
        assert data["summary"]["total_breakers"] == 1
        assert data["summary"]["healthy_breakers"] == 1
    
    @patch('src.app.routes.health.get_all_retry_managers')
    @patch('src.app.routes.health.get_retry_manager_stats')
    def test_retry_managers_endpoint(self, mock_get_stats, mock_get_managers):
        """Test retry managers status endpoint."""
        # Mock retry managers
        mock_manager = MagicMock()
        
        mock_get_managers.return_value = {"dexscreener": mock_manager}
        mock_get_stats.return_value = {
            "dexscreener": {
                "success_rate": 95.0,
                "average_attempts": 1.2,
                "total_calls": 100,
                "total_retries": 20
            }
        }
        
        response = self.client.get("/health/retry-managers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "retry_managers" in data
        assert "dexscreener" in data["retry_managers"]
        assert data["retry_managers"]["dexscreener"]["success_rate"] == 95.0
        assert "summary" in data
        assert data["summary"]["total_managers"] == 1
        assert data["summary"]["total_calls"] == 100
    
    @patch('src.app.routes.health.health_monitor')
    def test_alerts_endpoint(self, mock_health_monitor):
        """Test system alerts endpoint."""
        # Create mock alerts
        alert1 = HealthAlert(
            level=AlertLevel.WARNING,
            message="High CPU usage",
            component="resources",
            timestamp=datetime.utcnow(),
            correlation_id="test-1",
            context={"cpu_percent": 85}
        )
        
        alert2 = HealthAlert(
            level=AlertLevel.ERROR,
            message="API timeout",
            component="dexscreener",
            timestamp=datetime.utcnow(),
            correlation_id="test-2",
            context={"timeout": 5000}
        )
        
        mock_system_health = MagicMock()
        mock_system_health.get_all_alerts.return_value = [alert1, alert2]
        
        mock_health_monitor.get_comprehensive_health_async = AsyncMock(return_value=mock_system_health)
        
        response = self.client.get("/health/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data
        assert len(data["alerts"]) == 2
        assert data["alerts"][0]["level"] == "warning"
        assert data["alerts"][1]["level"] == "error"
        assert "summary" in data
        assert data["summary"]["total_alerts"] == 2
        assert data["summary"]["warning_alerts"] == 1
        assert data["summary"]["error_alerts"] == 1
    
    @patch('src.app.routes.health.health_monitor')
    def test_alerts_endpoint_with_filters(self, mock_health_monitor):
        """Test system alerts endpoint with filters."""
        # Create mock alerts
        alert1 = HealthAlert(
            level=AlertLevel.WARNING,
            message="High CPU usage",
            component="resources",
            timestamp=datetime.utcnow(),
            correlation_id="test-1",
            context={}
        )
        
        alert2 = HealthAlert(
            level=AlertLevel.ERROR,
            message="API timeout",
            component="dexscreener",
            timestamp=datetime.utcnow(),
            correlation_id="test-2",
            context={}
        )
        
        mock_system_health = MagicMock()
        mock_system_health.get_all_alerts.return_value = [alert1, alert2]
        
        mock_health_monitor.get_comprehensive_health_async = AsyncMock(return_value=mock_system_health)
        
        # Test level filter
        response = self.client.get("/health/alerts?level=error")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["level"] == "error"
        assert data["filters_applied"]["level"] == "error"
    
    @patch('src.monitoring.circuit_breaker.reset_all_circuit_breakers')
    @patch('src.monitoring.retry_manager.reset_all_retry_stats')
    @patch('src.app.routes.health.get_resilient_dexscreener_client')
    def test_reset_monitoring_stats(self, mock_get_client, mock_reset_retry, mock_reset_breakers):
        """Test reset monitoring statistics endpoint."""
        # Mock resilient client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        response = self.client.post("/health/reset")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Monitoring statistics reset successfully" in data["message"]
        assert "reset_components" in data
        assert len(data["reset_components"]) == 3
        
        # Verify reset functions were called
        mock_reset_breakers.assert_called_once()
        mock_reset_retry.assert_called_once()
        mock_client.reset_stats.assert_called_once()
    
    @patch('src.app.routes.health.health_monitor')
    def test_status_summary_endpoint(self, mock_health_monitor):
        """Test health status summary endpoint."""
        # Create mock system health
        scheduler_health = SchedulerHealth(
            status=HealthStatus.HEALTHY,
            hot_group_last_run=datetime.utcnow(),
            cold_group_last_run=datetime.utcnow(),
            hot_group_processing_time=30.0,
            cold_group_processing_time=120.0,
            tokens_processed_per_minute=5.0,
            error_rate=2.0,
            active_jobs=3,
            failed_jobs_last_hour=1
        )
        
        resource_health = ResourceHealth(
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
        
        api_health = APIHealth(
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
        
        # Create alert
        alert = HealthAlert(
            level=AlertLevel.INFO,
            message="System running normally",
            component="system",
            timestamp=datetime.utcnow(),
            correlation_id="test-1",
            context={}
        )
        
        mock_system_health = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            scheduler=scheduler_health,
            resources=resource_health,
            apis={"dexscreener": api_health},
            uptime_seconds=3600.0,
            last_restart=None
        )
        mock_system_health.get_all_alerts = MagicMock(return_value=[alert])
        
        mock_health_monitor.get_comprehensive_health_async = AsyncMock(return_value=mock_system_health)
        
        response = self.client.get("/health/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["overall_status"] == "healthy"
        assert data["uptime_seconds"] == 3600.0
        assert "components_status" in data
        assert data["components_status"]["scheduler"] == "healthy"
        assert data["components_status"]["resources"] == "healthy"
        assert "dexscreener" in data["components_status"]["apis"]
        assert "alert_counts" in data
        assert data["alert_counts"]["info"] == 1
        assert data["healthy_components"] == 3  # scheduler + resources + 1 API
        assert data["total_components"] == 3
    
    @patch('src.monitoring.health_monitor.HealthMonitor.get_comprehensive_health_async')
    def test_health_endpoint_error_handling(self, mock_get_comprehensive_health):
        """Test health endpoint error handling."""
        # Mock exception
        mock_get_comprehensive_health.side_effect = Exception("Test error")
        
        response = self.client.get("/health/")
        
        assert response.status_code == 500
        data = response.json()
        assert "Health check failed" in data["error"]["message"]
    
    @patch('src.monitoring.health_monitor.HealthMonitor.get_comprehensive_health_async')
    def test_detailed_health_endpoint_error_handling(self, mock_get_comprehensive_health):
        """Test detailed health endpoint error handling."""
        # Mock exception
        mock_get_comprehensive_health.side_effect = Exception("Test error")
        
        response = self.client.get("/health/detailed")
        
        assert response.status_code == 500
        data = response.json()
        assert "Detailed health check failed" in data["error"]["message"]