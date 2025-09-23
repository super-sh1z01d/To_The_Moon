"""
Tests for scheduler health detection functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from src.scheduler.monitoring import SchedulerHealthMonitor, JobExecution, SchedulerMetrics
from src.monitoring.models import AlertLevel, HealthStatus


class TestSchedulerHealthMonitor:
    """Test scheduler health monitoring functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = SchedulerHealthMonitor()
    
    def test_record_group_execution(self):
        """Test recording group execution."""
        # Record hot group execution
        self.monitor.record_group_execution("hot", 10, 5)
        
        assert self.monitor.last_hot_run is not None
        assert len(self.monitor.metrics.hot_group_executions) == 1
        
        execution = self.monitor.metrics.hot_group_executions[0]
        assert execution.group == "hot"
        assert execution.tokens_processed == 10
        assert execution.tokens_updated == 5
        assert execution.status == "completed"
    
    def test_job_tracking(self):
        """Test job tracking functionality."""
        job_id = "test_job_123"
        
        # Start tracking
        self.monitor.start_job_tracking(job_id, "hot")
        assert job_id in self.monitor._active_jobs
        assert self.monitor._active_jobs[job_id].status == "running"
        
        # Finish tracking
        self.monitor.finish_job_tracking(job_id, 15, 8, 0)
        assert job_id not in self.monitor._active_jobs
        assert len(self.monitor.metrics.hot_group_executions) == 1
        
        execution = self.monitor.metrics.hot_group_executions[0]
        assert execution.tokens_processed == 15
        assert execution.tokens_updated == 8
        assert execution.status == "completed"
    
    def test_stuck_job_detection(self):
        """Test stuck job detection."""
        job_id = "stuck_job_123"
        
        # Start tracking a job
        self.monitor.start_job_tracking(job_id, "hot")
        
        # Simulate job being stuck by setting old start time
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.monitor._active_jobs[job_id].start_time = old_time
        
        # Detect stuck jobs
        stuck_jobs = self.monitor.detect_stuck_jobs()
        
        assert job_id in stuck_jobs
        assert job_id in self.monitor.metrics.stuck_jobs
    
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation."""
        # Add some test executions
        now = datetime.now(timezone.utc)
        
        # Hot group executions
        for i in range(3):
            execution = JobExecution(
                job_id=f"hot_{i}",
                group="hot",
                start_time=now - timedelta(minutes=30),
                end_time=now - timedelta(minutes=29),
                tokens_processed=10,
                tokens_updated=5,
                status="completed"
            )
            self.monitor.metrics.hot_group_executions.append(execution)
        
        # Cold group executions
        for i in range(2):
            execution = JobExecution(
                job_id=f"cold_{i}",
                group="cold",
                start_time=now - timedelta(minutes=20),
                end_time=now - timedelta(minutes=18),
                tokens_processed=20,
                tokens_updated=10,
                status="completed"
            )
            self.monitor.metrics.cold_group_executions.append(execution)
        
        # Calculate metrics
        metrics = self.monitor.calculate_performance_metrics()
        
        assert "average_processing_time_hot" in metrics
        assert "average_processing_time_cold" in metrics
        assert "tokens_per_minute" in metrics
        assert "total_errors_last_hour" in metrics
        
        assert metrics["average_processing_time_hot"] == 60.0  # 1 minute
        assert metrics["average_processing_time_cold"] == 120.0  # 2 minutes
    
    def test_health_alerts_generation(self):
        """Test health alerts generation."""
        # Simulate stuck job
        job_id = "stuck_job"
        self.monitor.start_job_tracking(job_id, "hot")
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.monitor._active_jobs[job_id].start_time = old_time
        
        # Simulate delayed execution
        self.monitor.last_hot_run = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.monitor.hot_interval_sec = 30  # 30 seconds expected
        
        # Generate alerts
        alerts = self.monitor.get_health_alerts()
        
        assert len(alerts) >= 2  # At least stuck job and delayed execution alerts
        
        # Check stuck job alert
        stuck_alert = next((a for a in alerts if "stuck" in a.message.lower()), None)
        assert stuck_alert is not None
        assert stuck_alert.level == AlertLevel.ERROR
        
        # Check delayed execution alert
        delay_alert = next((a for a in alerts if "delayed" in a.message.lower()), None)
        assert delay_alert is not None
        assert delay_alert.level == AlertLevel.WARNING
    
    def test_comprehensive_health_status(self):
        """Test comprehensive health status."""
        # Set up some basic state
        self.monitor.last_hot_run = datetime.now(timezone.utc) - timedelta(seconds=30)
        self.monitor.last_cold_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        # Get comprehensive status
        status = self.monitor.get_comprehensive_health_status()
        
        assert "status" in status
        assert "last_check" in status
        assert "hot_group" in status
        assert "cold_group" in status
        assert "performance" in status
        assert "alerts" in status
        
        # Check hot group info
        hot_group = status["hot_group"]
        assert "last_run" in hot_group
        assert "interval_seconds" in hot_group
        assert "average_processing_time" in hot_group
        
        # Check cold group info
        cold_group = status["cold_group"]
        assert "last_run" in cold_group
        assert "interval_seconds" in cold_group
        assert "average_processing_time" in cold_group
        
        # Check performance info
        performance = status["performance"]
        assert "tokens_per_minute" in performance
        assert "total_errors_last_hour" in performance
        assert "active_jobs" in performance
        assert "stuck_jobs" in performance
    
    def test_health_status_determination(self):
        """Test health status determination based on alerts."""
        # Test healthy status (no alerts)
        status = self.monitor.get_comprehensive_health_status()
        assert status["status"] == HealthStatus.HEALTHY.value
        
        # Test degraded status (warning alerts)
        self.monitor.last_hot_run = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.monitor.hot_interval_sec = 30
        
        status = self.monitor.get_comprehensive_health_status()
        assert status["status"] == HealthStatus.DEGRADED.value
        
        # Test critical status (stuck jobs)
        job_id = "critical_stuck_job"
        self.monitor.start_job_tracking(job_id, "hot")
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.monitor._active_jobs[job_id].start_time = old_time
        
        status = self.monitor.get_comprehensive_health_status()
        assert status["status"] == HealthStatus.DEGRADED.value  # ERROR level makes it DEGRADED
    
    def test_execution_history_limit(self):
        """Test that execution history is limited to prevent memory issues."""
        # Add more than 50 executions
        for i in range(60):
            execution = JobExecution(
                job_id=f"test_{i}",
                group="hot",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                tokens_processed=1,
                status="completed"
            )
            self.monitor.metrics.hot_group_executions.append(execution)
        
        # Record one more execution to trigger cleanup
        self.monitor.record_group_execution("hot", 1, 1)
        
        # Should be limited to 50
        assert len(self.monitor.metrics.hot_group_executions) == 50
    
    def test_error_tracking(self):
        """Test error tracking in job executions."""
        job_id = "error_job"
        
        # Start and finish job with errors
        self.monitor.start_job_tracking(job_id, "hot")
        self.monitor.finish_job_tracking(job_id, 10, 5, 3, "API timeout error")
        
        execution = self.monitor.metrics.hot_group_executions[0]
        assert execution.error_count == 3
        assert execution.error_message == "API timeout error"
        assert execution.status == "failed"
        
        # Check that errors are counted in metrics
        metrics = self.monitor.calculate_performance_metrics()
        assert metrics["total_errors_last_hour"] == 3
    
    @patch('src.scheduler.monitoring.SessionLocal')
    def test_stale_tokens_check(self, mock_session):
        """Test stale tokens detection."""
        # Mock database session and repository
        mock_sess = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_sess
        
        mock_repo = MagicMock()
        mock_sess.return_value = mock_repo
        
        # Mock tokens and snapshots
        mock_token = MagicMock()
        mock_token.id = 1
        mock_token.symbol = "TEST"
        mock_token.mint_address = "test_mint"
        
        mock_snapshot = MagicMock()
        mock_snapshot.created_at = datetime.now(timezone.utc) - timedelta(minutes=15)
        
        with patch('src.scheduler.monitoring.TokensRepository') as mock_repo_class:
            mock_repo_instance = mock_repo_class.return_value
            mock_repo_instance.list_by_status.return_value = [mock_token]
            mock_repo_instance.get_latest_snapshot.return_value = mock_snapshot
            
            # Check stale tokens
            result = self.monitor.check_stale_tokens(max_age_minutes=10)
            
            assert result["stale_count"] == 1
            assert result["total_active"] == 1
            assert result["stale_percentage"] == 100.0
            assert len(result["stale_tokens"]) == 1
            assert result["stale_tokens"][0]["symbol"] == "TEST"