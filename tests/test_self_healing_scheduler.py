"""
Tests for Self-Healing Scheduler functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.scheduler.monitoring import SelfHealingSchedulerWrapper


class TestSelfHealingSchedulerWrapper:
    """Test Self-Healing Scheduler Wrapper functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_scheduler = MagicMock(spec=AsyncIOScheduler)
        self.mock_scheduler.running = True
        self.mock_scheduler.get_jobs.return_value = []
        
        self.wrapper = SelfHealingSchedulerWrapper(self.mock_scheduler)
    
    def test_initialization(self):
        """Test wrapper initialization."""
        assert self.wrapper.scheduler == self.mock_scheduler
        assert self.wrapper._restart_count == 0
        assert not self.wrapper._is_restarting
        assert len(self.wrapper._job_configs) == 0
    
    def test_store_job_configurations(self):
        """Test storing job configurations."""
        # Mock jobs
        mock_job1 = MagicMock()
        mock_job1.id = "job1"
        mock_job1.func = lambda: None
        mock_job1.trigger = "interval"
        mock_job1.args = ()
        mock_job1.kwargs = {}
        mock_job1.name = "Test Job 1"
        mock_job1.misfire_grace_time = 30
        mock_job1.coalesce = True
        mock_job1.max_instances = 1
        mock_job1.next_run_time = datetime.now(timezone.utc)
        
        mock_job2 = MagicMock()
        mock_job2.id = "job2"
        mock_job2.func = lambda: None
        mock_job2.trigger = "cron"
        mock_job2.args = ("arg1",)
        mock_job2.kwargs = {"key": "value"}
        mock_job2.name = "Test Job 2"
        mock_job2.misfire_grace_time = 60
        mock_job2.coalesce = False
        mock_job2.max_instances = 2
        mock_job2.next_run_time = datetime.now(timezone.utc)
        
        self.mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        
        # Store configurations
        self.wrapper._store_job_configurations()
        
        # Verify storage
        assert len(self.wrapper._job_configs) == 2
        assert "job1" in self.wrapper._job_configs
        assert "job2" in self.wrapper._job_configs
        assert len(self.wrapper._original_jobs) == 2
        
        # Verify job1 config
        job1_config = self.wrapper._job_configs["job1"]
        assert job1_config["id"] == "job1"
        assert job1_config["name"] == "Test Job 1"
        assert job1_config["misfire_grace_time"] == 30
        assert job1_config["coalesce"] is True
        assert job1_config["max_instances"] == 1
    
    def test_should_allow_restart_within_limit(self):
        """Test restart allowance within frequency limit."""
        # Should allow restart initially
        assert self.wrapper._should_allow_restart() is True
        
        # Add some restarts within the hour
        now = datetime.now(timezone.utc)
        self.wrapper._restart_history = [
            now - timedelta(minutes=30),
            now - timedelta(minutes=20),
            now - timedelta(minutes=10)
        ]
        
        # Should still allow restart (3 < 5)
        assert self.wrapper._should_allow_restart() is True
    
    def test_should_allow_restart_exceeds_limit(self):
        """Test restart allowance when frequency limit is exceeded."""
        # Add too many restarts within the hour
        now = datetime.now(timezone.utc)
        self.wrapper._restart_history = [
            now - timedelta(minutes=50),
            now - timedelta(minutes=40),
            now - timedelta(minutes=30),
            now - timedelta(minutes=20),
            now - timedelta(minutes=10)
        ]
        
        # Should not allow restart (5 >= 5)
        assert self.wrapper._should_allow_restart() is False
    
    def test_should_allow_restart_cleans_old_history(self):
        """Test that old restart history is cleaned up."""
        # Add old restarts (more than 1 hour ago)
        now = datetime.now(timezone.utc)
        self.wrapper._restart_history = [
            now - timedelta(hours=2),  # Old, should be removed
            now - timedelta(hours=1, minutes=30),  # Old, should be removed
            now - timedelta(minutes=30),  # Recent, should be kept
            now - timedelta(minutes=10)   # Recent, should be kept
        ]
        
        # Should allow restart and clean old history
        assert self.wrapper._should_allow_restart() is True
        assert len(self.wrapper._restart_history) == 2
    
    @pytest.mark.asyncio
    async def test_graceful_restart_success(self):
        """Test successful graceful restart."""
        # Mock job configurations
        self.wrapper._job_configs = {"job1": {"id": "job1", "func": lambda: None}}
        self.wrapper._original_jobs = [{"id": "job1", "func": lambda: None}]
        
        # Mock scheduler methods
        self.mock_scheduler.shutdown = MagicMock()
        self.mock_scheduler.start = MagicMock()
        
        with patch('src.scheduler.monitoring.AsyncIOScheduler') as mock_scheduler_class:
            mock_new_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_new_scheduler
            
            with patch.object(self.wrapper, '_restore_jobs', return_value=1):
                result = await self.wrapper.graceful_restart("test_reason")
                
                assert result is True
                assert self.wrapper._restart_count == 1
                assert len(self.wrapper._restart_history) == 1
                assert self.wrapper._consecutive_failures == 0
                
                # Verify scheduler was shutdown and new one created
                self.mock_scheduler.shutdown.assert_called_once_with(wait=True)
                mock_new_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graceful_restart_already_restarting(self):
        """Test graceful restart when already restarting."""
        self.wrapper._is_restarting = True
        
        result = await self.wrapper.graceful_restart("test_reason")
        
        assert result is False
        assert self.wrapper._restart_count == 0
    
    @pytest.mark.asyncio
    async def test_graceful_restart_frequency_limit_exceeded(self):
        """Test graceful restart when frequency limit is exceeded."""
        # Set up restart history to exceed limit
        now = datetime.now(timezone.utc)
        self.wrapper._restart_history = [now - timedelta(minutes=i*10) for i in range(5)]
        
        result = await self.wrapper.graceful_restart("test_reason")
        
        assert result is False
        assert self.wrapper._restart_count == 0
    
    @pytest.mark.asyncio
    async def test_emergency_restart_success(self):
        """Test successful emergency restart."""
        # Mock scheduler methods
        self.mock_scheduler.shutdown = MagicMock()
        self.mock_scheduler.start = MagicMock()
        
        with patch('src.scheduler.monitoring.AsyncIOScheduler') as mock_scheduler_class:
            mock_new_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_new_scheduler
            
            with patch.object(self.wrapper, '_restore_jobs', return_value=0):
                result = await self.wrapper.emergency_restart("critical_failure")
                
                assert result is True
                assert self.wrapper._restart_count == 1
                assert len(self.wrapper._restart_history) == 1
                assert self.wrapper._consecutive_failures == 0
                
                # Verify scheduler was shutdown (without wait) and new one created
                self.mock_scheduler.shutdown.assert_called_once_with(wait=False)
                mock_new_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_emergency_restart_handles_exceptions(self):
        """Test emergency restart handles exceptions gracefully."""
        # Mock scheduler methods to raise exceptions
        self.mock_scheduler.shutdown = MagicMock(side_effect=Exception("Shutdown failed"))
        
        with patch('src.scheduler.monitoring.AsyncIOScheduler') as mock_scheduler_class:
            mock_new_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_new_scheduler
            
            with patch.object(self.wrapper, '_restore_jobs', side_effect=Exception("Restore failed")):
                result = await self.wrapper.emergency_restart("critical_failure")
                
                # Should still succeed despite exceptions
                assert result is True
                assert self.wrapper._restart_count == 1
                mock_new_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_health_and_recover_healthy(self):
        """Test health check with healthy scheduler."""
        with patch('src.scheduler.monitoring.health_monitor') as mock_monitor:
            mock_monitor.get_comprehensive_health_status.return_value = {
                "status": "healthy",
                "performance": {"stuck_jobs": 0}
            }
            
            result = await self.wrapper.check_health_and_recover()
            
            assert result is True
            assert self.wrapper._consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_check_health_and_recover_critical(self):
        """Test health check with critical scheduler status."""
        with patch('src.scheduler.monitoring.health_monitor') as mock_monitor:
            mock_monitor.get_comprehensive_health_status.return_value = {
                "status": "critical",
                "performance": {"stuck_jobs": 0}
            }
            
            # First critical status
            result = await self.wrapper.check_health_and_recover()
            assert result is True
            assert self.wrapper._consecutive_failures == 1
            
            # Second critical status
            result = await self.wrapper.check_health_and_recover()
            assert result is True
            assert self.wrapper._consecutive_failures == 2
    
    @pytest.mark.asyncio
    async def test_check_health_and_recover_stuck_jobs(self):
        """Test health check with stuck jobs."""
        with patch('src.scheduler.monitoring.health_monitor') as mock_monitor:
            mock_monitor.get_comprehensive_health_status.return_value = {
                "status": "degraded",
                "performance": {"stuck_jobs": 2}
            }
            
            with patch.object(self.wrapper, 'graceful_restart', new_callable=AsyncMock) as mock_restart:
                mock_restart.return_value = True
                
                result = await self.wrapper.check_health_and_recover()
                
                # Should trigger graceful restart due to stuck jobs
                assert result is True
    
    def test_get_restart_statistics(self):
        """Test getting restart statistics."""
        # Set up some state
        self.wrapper._restart_count = 3
        self.wrapper._consecutive_failures = 1
        self.wrapper._is_restarting = False
        
        now = datetime.now(timezone.utc)
        self.wrapper._restart_history = [
            now - timedelta(minutes=30),
            now - timedelta(minutes=20)
        ]
        self.wrapper._last_successful_run = now - timedelta(minutes=10)
        self.wrapper._job_configs = {"job1": {}, "job2": {}}
        
        stats = self.wrapper.get_restart_statistics()
        
        assert stats["total_restarts"] == 3
        assert stats["restarts_last_hour"] == 2
        assert stats["consecutive_failures"] == 1
        assert stats["is_restarting"] is False
        assert stats["uptime_seconds"] == pytest.approx(600, abs=10)  # ~10 minutes
        assert stats["stored_jobs_count"] == 2
        assert "last_successful_run" in stats
    
    def test_wait_for_jobs_completion_no_jobs(self):
        """Test waiting for job completion when no jobs are running."""
        self.mock_scheduler.get_jobs.return_value = []
        
        # Should return immediately
        start_time = datetime.now()
        self.wrapper._wait_for_jobs_completion(timeout_seconds=5)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        assert elapsed < 1  # Should be very fast
    
    def test_wait_for_jobs_completion_timeout(self):
        """Test waiting for job completion with timeout."""
        # Mock running job
        mock_job = MagicMock()
        mock_job.next_run_time = datetime.now(timezone.utc)
        self.mock_scheduler.get_jobs.return_value = [mock_job]
        
        # Should timeout after specified time
        start_time = datetime.now()
        self.wrapper._wait_for_jobs_completion(timeout_seconds=2)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        assert elapsed >= 2
        assert elapsed < 3  # Should not take much longer than timeout
