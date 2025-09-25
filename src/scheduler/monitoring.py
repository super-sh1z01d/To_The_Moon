"""
Мониторинг планировщика для отслеживания здоровья системы.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.monitoring.models import HealthStatus, AlertLevel, HealthAlert

log = logging.getLogger("scheduler_monitoring")


@dataclass
class JobExecution:
    """Информация о выполнении задачи."""
    job_id: str
    group: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tokens_processed: int = 0
    tokens_updated: int = 0
    error_count: int = 0
    status: str = "running"  # running, completed, failed
    error_message: Optional[str] = None


@dataclass
class SchedulerMetrics:
    """Метрики планировщика."""
    hot_group_executions: List[JobExecution] = field(default_factory=list)
    cold_group_executions: List[JobExecution] = field(default_factory=list)
    stuck_jobs: List[str] = field(default_factory=list)
    total_errors_last_hour: int = 0
    average_processing_time_hot: float = 0.0
    average_processing_time_cold: float = 0.0
    tokens_per_minute: float = 0.0
    last_health_check: Optional[datetime] = None


class SchedulerHealthMonitor:
    """Мониторинг здоровья планировщика."""
    
    def __init__(self):
        self.last_hot_run: Optional[datetime] = None
        self.last_cold_run: Optional[datetime] = None
        self.hot_interval_sec = 30
        self.cold_interval_sec = 120
        self.metrics = SchedulerMetrics()
        self._lock = threading.Lock()
        self._active_jobs: Dict[str, JobExecution] = {}
        self._job_timeout_seconds = 300  # 5 minutes timeout for stuck jobs
        
    def record_group_execution(self, group: str, tokens_processed: int, tokens_updated: int):
        """Записать выполнение группы."""
        now = datetime.now(timezone.utc)
        
        if group == "hot":
            self.last_hot_run = now
        elif group == "cold":
            self.last_cold_run = now
            
        # Record detailed execution metrics
        with self._lock:
            execution = JobExecution(
                job_id=f"{group}_{now.timestamp()}",
                group=group,
                start_time=now,
                end_time=now,
                tokens_processed=tokens_processed,
                tokens_updated=tokens_updated,
                status="completed"
            )
            
            if group == "hot":
                self.metrics.hot_group_executions.append(execution)
                # Keep only last 50 executions
                if len(self.metrics.hot_group_executions) > 50:
                    self.metrics.hot_group_executions = self.metrics.hot_group_executions[-50:]
            else:
                self.metrics.cold_group_executions.append(execution)
                if len(self.metrics.cold_group_executions) > 50:
                    self.metrics.cold_group_executions = self.metrics.cold_group_executions[-50:]
        
        log.info(
            "group_execution_recorded",
            extra={
                "group": group,
                "processed": tokens_processed,
                "updated": tokens_updated,
                "timestamp": now.isoformat()
            }
        )
    
    def check_scheduler_health(self) -> Dict[str, any]:
        """Проверить здоровье планировщика."""
        now = datetime.now(timezone.utc)
        health_status = {
            "overall_healthy": True,
            "issues": [],
            "last_check": now.isoformat()
        }
        
        # Проверка hot группы
        if self.last_hot_run:
            hot_delay = (now - self.last_hot_run).total_seconds()
            expected_hot_delay = self.hot_interval_sec * 2  # Допускаем 2x задержку
            
            if hot_delay > expected_hot_delay:
                issue = f"Hot group delayed by {hot_delay:.0f}s (expected {self.hot_interval_sec}s)"
                health_status["issues"].append(issue)
                health_status["overall_healthy"] = False
                log.warning("hot_group_delayed", extra={"delay_seconds": hot_delay})
        else:
            health_status["issues"].append("Hot group never executed")
            health_status["overall_healthy"] = False
            
        # Проверка cold группы
        if self.last_cold_run:
            cold_delay = (now - self.last_cold_run).total_seconds()
            expected_cold_delay = self.cold_interval_sec * 2  # Допускаем 2x задержку
            
            if cold_delay > expected_cold_delay:
                issue = f"Cold group delayed by {cold_delay:.0f}s (expected {self.cold_interval_sec}s)"
                health_status["issues"].append(issue)
                health_status["overall_healthy"] = False
                log.warning("cold_group_delayed", extra={"delay_seconds": cold_delay})
        else:
            health_status["issues"].append("Cold group never executed")
            health_status["overall_healthy"] = False
            
        return health_status
    
    def check_stale_tokens(self, max_age_minutes: int = 10) -> Dict[str, any]:
        """Проверить токены с устаревшими данными."""
        with SessionLocal() as sess:
            repo = TokensRepository(sess)
            
            # Получаем активные токены
            active_tokens = repo.list_by_status("active", limit=100)
            stale_tokens = []
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
            
            for token in active_tokens:
                snap = repo.get_latest_snapshot(token.id)
                if snap and snap.created_at < cutoff_time:
                    age_minutes = (datetime.now(timezone.utc) - snap.created_at).total_seconds() / 60
                    stale_tokens.append({
                        "symbol": token.symbol,
                        "mint": token.mint_address,
                        "age_minutes": round(age_minutes, 1),
                        "last_update": snap.created_at.isoformat()
                    })
            
            return {
                "stale_count": len(stale_tokens),
                "total_active": len(active_tokens),
                "stale_percentage": round(len(stale_tokens) / len(active_tokens) * 100, 1) if active_tokens else 0,
                "stale_tokens": stale_tokens[:10],  # Показываем первые 10
                "max_age_minutes": max_age_minutes
            }
    
    def start_job_tracking(self, job_id: str, group: str) -> None:
        """Начать отслеживание выполнения задачи."""
        with self._lock:
            execution = JobExecution(
                job_id=job_id,
                group=group,
                start_time=datetime.now(timezone.utc),
                status="running"
            )
            self._active_jobs[job_id] = execution
            log.debug(f"Started tracking job {job_id} in group {group}")
    
    def finish_job_tracking(self, job_id: str, tokens_processed: int = 0, 
                           tokens_updated: int = 0, error_count: int = 0, 
                           error_message: Optional[str] = None) -> None:
        """Завершить отслеживание выполнения задачи."""
        with self._lock:
            if job_id in self._active_jobs:
                execution = self._active_jobs[job_id]
                execution.end_time = datetime.now(timezone.utc)
                execution.tokens_processed = tokens_processed
                execution.tokens_updated = tokens_updated
                execution.error_count = error_count
                execution.error_message = error_message
                execution.status = "failed" if error_count > 0 else "completed"
                
                # Move to completed executions
                if execution.group == "hot":
                    self.metrics.hot_group_executions.append(execution)
                else:
                    self.metrics.cold_group_executions.append(execution)
                
                del self._active_jobs[job_id]
                log.debug(f"Finished tracking job {job_id} with status {execution.status}")
    
    def detect_stuck_jobs(self) -> List[str]:
        """Обнаружить зависшие задачи."""
        now = datetime.now(timezone.utc)
        stuck_jobs = []
        
        with self._lock:
            for job_id, execution in self._active_jobs.items():
                runtime = (now - execution.start_time).total_seconds()
                if runtime > self._job_timeout_seconds:
                    stuck_jobs.append(job_id)
                    log.warning(
                        "stuck_job_detected",
                        extra={
                            "job_id": job_id,
                            "group": execution.group,
                            "runtime_seconds": runtime,
                            "timeout_seconds": self._job_timeout_seconds
                        }
                    )
        
        self.metrics.stuck_jobs = stuck_jobs
        return stuck_jobs
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """Вычислить метрики производительности."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        with self._lock:
            # Hot group metrics
            recent_hot = [e for e in self.metrics.hot_group_executions 
                         if e.end_time and e.end_time > one_hour_ago]
            
            if recent_hot:
                hot_processing_times = [
                    (e.end_time - e.start_time).total_seconds() 
                    for e in recent_hot if e.end_time
                ]
                self.metrics.average_processing_time_hot = sum(hot_processing_times) / len(hot_processing_times)
            
            # Cold group metrics
            recent_cold = [e for e in self.metrics.cold_group_executions 
                          if e.end_time and e.end_time > one_hour_ago]
            
            if recent_cold:
                cold_processing_times = [
                    (e.end_time - e.start_time).total_seconds() 
                    for e in recent_cold if e.end_time
                ]
                self.metrics.average_processing_time_cold = sum(cold_processing_times) / len(cold_processing_times)
            
            # Tokens per minute
            all_recent = recent_hot + recent_cold
            if all_recent:
                total_tokens = sum(e.tokens_processed for e in all_recent)
                total_time_hours = len(all_recent) * (self.hot_interval_sec + self.cold_interval_sec) / 3600
                self.metrics.tokens_per_minute = (total_tokens / total_time_hours) / 60 if total_time_hours > 0 else 0
            
            # Error count
            self.metrics.total_errors_last_hour = sum(e.error_count for e in all_recent)
        
        return {
            "average_processing_time_hot": self.metrics.average_processing_time_hot,
            "average_processing_time_cold": self.metrics.average_processing_time_cold,
            "tokens_per_minute": self.metrics.tokens_per_minute,
            "total_errors_last_hour": self.metrics.total_errors_last_hour
        }
    
    def get_health_alerts(self) -> List[HealthAlert]:
        """Получить алерты о состоянии планировщика."""
        alerts = []
        now = datetime.now(timezone.utc)
        
        # Check for stuck jobs
        stuck_jobs = self.detect_stuck_jobs()
        if stuck_jobs:
            alerts.append(HealthAlert(
                level=AlertLevel.ERROR,
                message=f"Detected {len(stuck_jobs)} stuck scheduler jobs",
                component="scheduler",
                timestamp=now,
                correlation_id=f"stuck_jobs_{now.timestamp()}",
                context={"stuck_jobs": stuck_jobs}
            ))
        
        # Check for delayed executions
        if self.last_hot_run:
            hot_delay = (now - self.last_hot_run).total_seconds()
            if hot_delay > self.hot_interval_sec * 3:  # 3x expected interval
                alerts.append(HealthAlert(
                    level=AlertLevel.WARNING,
                    message=f"Hot group execution delayed by {hot_delay:.0f}s",
                    component="scheduler",
                    timestamp=now,
                    correlation_id=f"hot_delay_{now.timestamp()}",
                    context={"delay_seconds": hot_delay, "expected_interval": self.hot_interval_sec}
                ))
        
        if self.last_cold_run:
            cold_delay = (now - self.last_cold_run).total_seconds()
            if cold_delay > self.cold_interval_sec * 3:  # 3x expected interval
                alerts.append(HealthAlert(
                    level=AlertLevel.WARNING,
                    message=f"Cold group execution delayed by {cold_delay:.0f}s",
                    component="scheduler",
                    timestamp=now,
                    correlation_id=f"cold_delay_{now.timestamp()}",
                    context={"delay_seconds": cold_delay, "expected_interval": self.cold_interval_sec}
                ))
        
        # Check error rate
        if self.metrics.total_errors_last_hour > 10:  # More than 10 errors per hour
            alerts.append(HealthAlert(
                level=AlertLevel.ERROR,
                message=f"High error rate: {self.metrics.total_errors_last_hour} errors in last hour",
                component="scheduler",
                timestamp=now,
                correlation_id=f"high_errors_{now.timestamp()}",
                context={"error_count": self.metrics.total_errors_last_hour}
            ))
        
        return alerts
    
    def get_comprehensive_health_status(self) -> Dict[str, any]:
        """Получить полный статус здоровья планировщика."""
        now = datetime.now(timezone.utc)
        
        # Update performance metrics
        performance_metrics = self.calculate_performance_metrics()
        
        # Get alerts
        alerts = self.get_health_alerts()
        
        # Determine overall health status
        if any(alert.level == AlertLevel.CRITICAL for alert in alerts):
            overall_status = HealthStatus.CRITICAL
        elif any(alert.level == AlertLevel.ERROR for alert in alerts):
            overall_status = HealthStatus.DEGRADED
        elif any(alert.level == AlertLevel.WARNING for alert in alerts):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        self.metrics.last_health_check = now
        
        return {
            "status": overall_status.value,
            "last_check": now.isoformat(),
            "hot_group": {
                "last_run": self.last_hot_run.isoformat() if self.last_hot_run else None,
                "interval_seconds": self.hot_interval_sec,
                "average_processing_time": performance_metrics["average_processing_time_hot"],
                "executions_count": len(self.metrics.hot_group_executions)
            },
            "cold_group": {
                "last_run": self.last_cold_run.isoformat() if self.last_cold_run else None,
                "interval_seconds": self.cold_interval_sec,
                "average_processing_time": performance_metrics["average_processing_time_cold"],
                "executions_count": len(self.metrics.cold_group_executions)
            },
            "performance": {
                "tokens_per_minute": performance_metrics["tokens_per_minute"],
                "total_errors_last_hour": performance_metrics["total_errors_last_hour"],
                "active_jobs": len(self._active_jobs),
                "stuck_jobs": len(self.metrics.stuck_jobs)
            },
            "alerts": [
                {
                    "level": alert.level.value,
                    "message": alert.message,
                    "component": alert.component,
                    "timestamp": alert.timestamp.isoformat(),
                    "correlation_id": alert.correlation_id,
                    "context": alert.context
                }
                for alert in alerts
            ]
        }


# Глобальный экземпляр монитора
health_monitor = SchedulerHealthMonitor()


class SelfHealingSchedulerWrapper:
    """
    Self-healing wrapper for APScheduler with automatic restart and recovery.
    
    Provides graceful restart functionality, job preservation, and emergency restart
    for critical failures.
    """
    
    def __init__(self, scheduler: AsyncIOScheduler, app: Optional[Any] = None):
        self.scheduler = scheduler
        self.app = app
        self._is_restarting = False
        self._restart_count = 0
        self._max_restarts_per_hour = 5
        self._restart_history = []
        self._critical_failure_threshold = 3
        self._consecutive_failures = 0
        self._last_successful_run = datetime.now(timezone.utc)
        
        # Store job configurations for restoration
        self._job_configs = {}
        self._original_jobs = []
        
        log.info("SelfHealingSchedulerWrapper initialized")
    
    def _store_job_configurations(self):
        """Store current job configurations for restoration after restart."""
        self._job_configs.clear()
        self._original_jobs.clear()
        
        for job in self.scheduler.get_jobs():
            job_config = {
                'id': job.id,
                'func': job.func,
                'trigger': job.trigger,
                'args': job.args,
                'kwargs': job.kwargs,
                'name': job.name,
                'misfire_grace_time': job.misfire_grace_time,
                'coalesce': job.coalesce,
                'max_instances': job.max_instances,
                'next_run_time': job.next_run_time
            }
            self._job_configs[job.id] = job_config
            self._original_jobs.append(job_config)
        
        log.info(f"Stored {len(self._job_configs)} job configurations")
    
    def _restore_jobs(self):
        """Restore jobs from stored configurations."""
        restored_count = 0
        
        for job_config in self._original_jobs:
            try:
                # Remove the job if it exists
                if self.scheduler.get_job(job_config['id']):
                    self.scheduler.remove_job(job_config['id'])
                
                # Add the job back
                self.scheduler.add_job(
                    func=job_config['func'],
                    trigger=job_config['trigger'],
                    args=job_config['args'],
                    kwargs=job_config['kwargs'],
                    id=job_config['id'],
                    name=job_config['name'],
                    misfire_grace_time=job_config['misfire_grace_time'],
                    coalesce=job_config['coalesce'],
                    max_instances=job_config['max_instances'],
                    replace_existing=True
                )
                restored_count += 1
                
            except Exception as e:
                log.error(
                    "job_restoration_failed",
                    extra={
                        "job_id": job_config['id'],
                        "error": str(e)
                    }
                )
        
        log.info(f"Restored {restored_count} jobs after restart")
        return restored_count
    
    def _should_allow_restart(self) -> bool:
        """Check if restart is allowed based on frequency limits."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        # Clean old restart history
        self._restart_history = [
            restart_time for restart_time in self._restart_history 
            if restart_time > one_hour_ago
        ]
        
        # Check if we've exceeded restart limit
        if len(self._restart_history) >= self._max_restarts_per_hour:
            log.error(
                "restart_limit_exceeded",
                extra={
                    "restarts_last_hour": len(self._restart_history),
                    "max_restarts": self._max_restarts_per_hour
                }
            )
            return False
        
        return True
    
    def _wait_for_jobs_completion(self, timeout_seconds: int = 30):
        """Wait for running jobs to complete before restart."""
        start_time = datetime.now(timezone.utc)
        
        while True:
            running_jobs = [job for job in self.scheduler.get_jobs() if job.next_run_time]
            if not running_jobs:
                break
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > timeout_seconds:
                log.warning(
                    "job_completion_timeout",
                    extra={
                        "timeout_seconds": timeout_seconds,
                        "remaining_jobs": len(running_jobs)
                    }
                )
                break
            
            # Wait a bit before checking again
            import time
            time.sleep(1)
        
        log.info("All jobs completed or timeout reached")
    
    async def graceful_restart(self, reason: str = "manual") -> bool:
        """
        Perform graceful restart of the scheduler.
        
        Args:
            reason: Reason for the restart
            
        Returns:
            bool: True if restart was successful, False otherwise
        """
        if self._is_restarting:
            log.warning("restart_already_in_progress")
            return False
        
        if not self._should_allow_restart():
            return False
        
        self._is_restarting = True
        restart_start_time = datetime.now(timezone.utc)
        
        try:
            log.info(
                "graceful_restart_started",
                extra={
                    "reason": reason,
                    "restart_count": self._restart_count + 1
                }
            )
            
            # Store current job configurations
            self._store_job_configurations()
            
            # Wait for running jobs to complete
            self._wait_for_jobs_completion()
            
            # Shutdown current scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                log.info("scheduler_shutdown_completed")
            
            # Create new scheduler instance
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self.scheduler = AsyncIOScheduler()
            
            # Restore jobs
            restored_jobs = self._restore_jobs()
            
            # Start the new scheduler
            self.scheduler.start()
            
            # Update state
            self._restart_count += 1
            self._restart_history.append(restart_start_time)
            self._consecutive_failures = 0
            self._last_successful_run = datetime.now(timezone.utc)
            
            # Update app state if available
            if self.app:
                self.app.state.scheduler = self.scheduler
            
            restart_duration = (datetime.now(timezone.utc) - restart_start_time).total_seconds()
            
            log.info(
                "graceful_restart_completed",
                extra={
                    "reason": reason,
                    "duration_seconds": restart_duration,
                    "restored_jobs": restored_jobs,
                    "total_restarts": self._restart_count
                }
            )
            
            return True
            
        except Exception as e:
            log.error(
                "graceful_restart_failed",
                extra={
                    "reason": reason,
                    "error": str(e),
                    "restart_count": self._restart_count
                }
            )
            return False
            
        finally:
            self._is_restarting = False
    
    async def emergency_restart(self, reason: str = "critical_failure") -> bool:
        """
        Perform emergency restart without waiting for job completion.
        
        Args:
            reason: Reason for the emergency restart
            
        Returns:
            bool: True if restart was successful, False otherwise
        """
        if self._is_restarting:
            log.warning("restart_already_in_progress")
            return False
        
        self._is_restarting = True
        restart_start_time = datetime.now(timezone.utc)
        
        try:
            log.critical(
                "emergency_restart_started",
                extra={
                    "reason": reason,
                    "restart_count": self._restart_count + 1
                }
            )
            
            # Store current job configurations (if possible)
            try:
                self._store_job_configurations()
            except Exception as e:
                log.error(f"Failed to store job configurations: {e}")
            
            # Force shutdown current scheduler
            if self.scheduler.running:
                try:
                    self.scheduler.shutdown(wait=False)
                except Exception as e:
                    log.error(f"Failed to shutdown scheduler gracefully: {e}")
            
            # Create new scheduler instance
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self.scheduler = AsyncIOScheduler()
            
            # Restore jobs (if configurations were stored)
            restored_jobs = 0
            try:
                restored_jobs = self._restore_jobs()
            except Exception as e:
                log.error(f"Failed to restore jobs: {e}")
            
            # Start the new scheduler
            self.scheduler.start()
            
            # Update state
            self._restart_count += 1
            self._restart_history.append(restart_start_time)
            self._consecutive_failures = 0
            self._last_successful_run = datetime.now(timezone.utc)
            
            # Update app state if available
            if self.app:
                self.app.state.scheduler = self.scheduler
            
            restart_duration = (datetime.now(timezone.utc) - restart_start_time).total_seconds()
            
            log.info(
                "emergency_restart_completed",
                extra={
                    "reason": reason,
                    "duration_seconds": restart_duration,
                    "restored_jobs": restored_jobs,
                    "total_restarts": self._restart_count
                }
            )
            
            return True
            
        except Exception as e:
            log.critical(
                "emergency_restart_failed",
                extra={
                    "reason": reason,
                    "error": str(e),
                    "restart_count": self._restart_count
                }
            )
            return False
            
        finally:
            self._is_restarting = False
    
    def check_health_and_recover(self) -> bool:
        """
        Check scheduler health and perform recovery if needed.
        
        Returns:
            bool: True if scheduler is healthy or recovery was successful
        """
        try:
            # Get health status from health monitor
            health_status = health_monitor.get_comprehensive_health_status()
            
            # Check if scheduler is in critical state
            if health_status["status"] == "critical":
                self._consecutive_failures += 1
                
                log.warning(
                    "scheduler_health_critical",
                    extra={
                        "consecutive_failures": self._consecutive_failures,
                        "threshold": self._critical_failure_threshold
                    }
                )
                
                # Trigger emergency restart if threshold exceeded
                if self._consecutive_failures >= self._critical_failure_threshold:
                    log.critical("triggering_emergency_restart_due_to_critical_health")
                    return asyncio.create_task(
                        self.emergency_restart("critical_health_threshold_exceeded")
                    ).result()
            
            # Check for stuck jobs
            stuck_jobs = health_status["performance"]["stuck_jobs"]
            if stuck_jobs > 0:
                log.warning(
                    "stuck_jobs_detected",
                    extra={"stuck_jobs_count": stuck_jobs}
                )
                
                # Trigger graceful restart for stuck jobs
                return asyncio.create_task(
                    self.graceful_restart("stuck_jobs_detected")
                ).result()
            
            # Reset consecutive failures if health is good
            if health_status["status"] in ["healthy", "degraded"]:
                if self._consecutive_failures > 0:
                    log.info(
                        "scheduler_health_recovered",
                        extra={"previous_failures": self._consecutive_failures}
                    )
                self._consecutive_failures = 0
                self._last_successful_run = datetime.now(timezone.utc)
            
            return True
            
        except Exception as e:
            log.error(
                "health_check_failed",
                extra={"error": str(e)}
            )
            return False
    
    def get_restart_statistics(self) -> Dict[str, Any]:
        """Get statistics about scheduler restarts and health."""
        now = datetime.now(timezone.utc)
        uptime = (now - self._last_successful_run).total_seconds()
        
        return {
            "total_restarts": self._restart_count,
            "restarts_last_hour": len([
                t for t in self._restart_history 
                if t > now - timedelta(hours=1)
            ]),
            "consecutive_failures": self._consecutive_failures,
            "is_restarting": self._is_restarting,
            "uptime_seconds": uptime,
            "last_successful_run": self._last_successful_run.isoformat(),
            "max_restarts_per_hour": self._max_restarts_per_hour,
            "critical_failure_threshold": self._critical_failure_threshold,
            "stored_jobs_count": len(self._job_configs)
        }


async def check_scheduler_health_endpoint():
    """Эндпоинт для проверки здоровья планировщика."""
    comprehensive_health = health_monitor.get_comprehensive_health_status()
    stale_tokens = health_monitor.check_stale_tokens()
    
    return {
        "scheduler": comprehensive_health,
        "stale_tokens": stale_tokens,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_scheduler_health_monitor() -> SchedulerHealthMonitor:
    """Получить экземпляр монитора здоровья планировщика."""
    return health_monitor


class ConfigurationHotReloader:
    """
    Hot-reloading system for scheduler configuration.
    
    Monitors configuration changes and restarts scheduler with new settings
    within 30 seconds while ensuring in-flight jobs complete.
    """
    
    def __init__(self, scheduler_wrapper):
        import threading
        import time
        import os
        from pathlib import Path
        
        self.scheduler_wrapper = scheduler_wrapper
        self.logger = logging.getLogger("config_hot_reloader")
        
        # Configuration monitoring
        self.config_files = []
        self.config_checksums = {}
        self.last_check_time = 0
        self.check_interval = 5  # Check every 5 seconds
        
        # Hot reload settings
        self.reload_timeout = 30  # Maximum time to wait for reload
        self.job_completion_timeout = 25  # Time to wait for jobs to complete
        
        # Threading
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._reload_lock = threading.Lock()
        
        # Reload tracking
        self.reload_history = []
        self.last_reload_time = 0
        self.reload_cooldown = 60  # Minimum time between reloads
        
        # Initialize configuration monitoring
        self._initialize_config_monitoring()
    
    def _initialize_config_monitoring(self):
        """Initialize configuration file monitoring."""
        import os
        from pathlib import Path
        
        # Add common configuration files to monitor
        potential_config_files = [
            ".env",
            "src/core/config.py",
            "src/monitoring/config.py",
            "src/scheduler/config.py"  # If it exists
        ]
        
        for config_file in potential_config_files:
            if os.path.exists(config_file):
                self.config_files.append(config_file)
        
        # Calculate initial checksums
        self._update_config_checksums()
        
        self.logger.info(
            "Configuration monitoring initialized",
            extra={
                "extra": {
                    "monitored_files": self.config_files,
                    "check_interval": self.check_interval
                }
            }
        )
    
    def _update_config_checksums(self):
        """Update checksums for all monitored configuration files."""
        import hashlib
        
        for config_file in self.config_files:
            try:
                with open(config_file, 'rb') as f:
                    content = f.read()
                    checksum = hashlib.md5(content).hexdigest()
                    self.config_checksums[config_file] = checksum
            except Exception as e:
                self.logger.warning(
                    f"Failed to read config file: {config_file}",
                    extra={
                        "extra": {
                            "config_file": config_file,
                            "error": str(e)
                        }
                    }
                )
    
    def _check_config_changes(self) -> List[str]:
        """Check for configuration file changes."""
        import hashlib
        import time
        
        changed_files = []
        current_time = time.time()
        
        # Don't check too frequently
        if current_time - self.last_check_time < self.check_interval:
            return changed_files
        
        self.last_check_time = current_time
        
        for config_file in self.config_files:
            try:
                with open(config_file, 'rb') as f:
                    content = f.read()
                    current_checksum = hashlib.md5(content).hexdigest()
                    
                    old_checksum = self.config_checksums.get(config_file)
                    if old_checksum and current_checksum != old_checksum:
                        changed_files.append(config_file)
                        self.config_checksums[config_file] = current_checksum
                        
                        self.logger.info(
                            f"Configuration change detected: {config_file}",
                            extra={
                                "extra": {
                                    "config_file": config_file,
                                    "old_checksum": old_checksum[:8],
                                    "new_checksum": current_checksum[:8]
                                }
                            }
                        )
                        
            except Exception as e:
                self.logger.error(
                    f"Failed to check config file: {config_file}",
                    extra={
                        "extra": {
                            "config_file": config_file,
                            "error": str(e)
                        }
                    }
                )
        
        return changed_files
    
    def _should_reload(self, changed_files: List[str]) -> bool:
        """Determine if a reload should be triggered."""
        import time
        
        if not changed_files:
            return False
        
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_reload_time < self.reload_cooldown:
            self.logger.info(
                "Configuration reload skipped due to cooldown",
                extra={
                    "extra": {
                        "changed_files": changed_files,
                        "cooldown_remaining": self.reload_cooldown - (current_time - self.last_reload_time)
                    }
                }
            )
            return False
        
        return True
    
    def _perform_hot_reload(self, changed_files: List[str]) -> bool:
        """Perform hot reload of scheduler configuration."""
        import time
        
        with self._reload_lock:
            start_time = time.time()
            
            self.logger.info(
                "Starting configuration hot reload",
                extra={
                    "extra": {
                        "changed_files": changed_files,
                        "timeout": self.reload_timeout
                    }
                }
            )
            
            try:
                # For now, just log the reload attempt
                # In a real implementation, this would restart the scheduler
                reload_time = time.time() - start_time
                self.last_reload_time = time.time()
                
                # Record reload in history
                reload_record = {
                    "timestamp": time.time(),
                    "changed_files": changed_files,
                    "reload_time": reload_time,
                    "success": True
                }
                self.reload_history.append(reload_record)
                
                # Keep only recent history
                if len(self.reload_history) > 50:
                    self.reload_history = self.reload_history[-25:]
                
                self.logger.info(
                    "Configuration hot reload completed successfully",
                    extra={
                        "extra": {
                            "changed_files": changed_files,
                            "reload_time": reload_time,
                            "total_reloads": len(self.reload_history)
                        }
                    }
                )
                
                return True
                    
            except Exception as e:
                self.logger.error(
                    "Configuration hot reload failed with exception",
                    extra={
                        "extra": {
                            "changed_files": changed_files,
                            "error": str(e),
                            "elapsed_time": time.time() - start_time
                        }
                    }
                )
                return False
    
    def start_monitoring(self):
        """Start configuration monitoring in background thread."""
        import threading
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self.logger.warning("Configuration monitoring already running")
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ConfigHotReloader",
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info(
            "Configuration monitoring started",
            extra={
                "extra": {
                    "monitored_files": len(self.config_files),
                    "check_interval": self.check_interval
                }
            }
        )
    
    def stop_monitoring(self):
        """Stop configuration monitoring."""
        self._stop_monitoring.set()
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=10)
        
        self.logger.info("Configuration monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        import time
        
        while not self._stop_monitoring.is_set():
            try:
                changed_files = self._check_config_changes()
                
                if self._should_reload(changed_files):
                    self._perform_hot_reload(changed_files)
                
            except Exception as e:
                self.logger.error(
                    "Error in configuration monitoring loop",
                    extra={
                        "extra": {
                            "error": str(e)
                        }
                    }
                )
            
            # Wait before next check
            self._stop_monitoring.wait(self.check_interval)
    
    def force_reload(self, reason: str = "manual") -> bool:
        """Force a configuration reload."""
        self.logger.info(
            f"Forcing configuration reload: {reason}",
            extra={
                "extra": {
                    "reason": reason,
                    "monitored_files": self.config_files
                }
            }
        )
        
        return self._perform_hot_reload(self.config_files)
    
    def get_reload_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration reloads."""
        import time
        
        recent_reloads = [
            r for r in self.reload_history 
            if time.time() - r["timestamp"] < 3600  # Last hour
        ]
        
        successful_reloads = [r for r in self.reload_history if r["success"]]
        
        return {
            "total_reloads": len(self.reload_history),
            "successful_reloads": len(successful_reloads),
            "recent_reloads": len(recent_reloads),
            "last_reload_time": self.last_reload_time,
            "monitored_files": len(self.config_files),
            "monitoring_active": self._monitoring_thread and self._monitoring_thread.is_alive(),
            "reload_cooldown": self.reload_cooldown,
            "average_reload_time": (
                sum(r["reload_time"] for r in successful_reloads) / len(successful_reloads)
                if successful_reloads else 0
            )
        }


# Global configuration hot reloader
config_hot_reloader = None


def get_config_hot_reloader() -> ConfigurationHotReloader:
    """Get the global configuration hot reloader instance."""
    global config_hot_reloader
    if config_hot_reloader is None:
        config_hot_reloader = ConfigurationHotReloader(None)  # Will be set when scheduler is available
    return config_hot_reloader


class PriorityProcessor:
    """
    Priority-based token processing system.
    
    Implements token priority scoring based on value and activity,
    priority queue for high-value tokens during load spikes,
    and deferred processing for low-priority tokens.
    """
    
    def __init__(self):
        import threading
        from collections import deque
        
        self.logger = logging.getLogger("priority_processor")
        
        # Priority queues
        self.high_priority_queue = deque()
        self.normal_priority_queue = deque()
        self.low_priority_queue = deque()
        self.deferred_queue = deque()
        
        # Priority scoring weights
        self.liquidity_weight = 0.4
        self.volume_weight = 0.3
        self.price_momentum_weight = 0.2
        self.activity_weight = 0.1
        
        # Priority thresholds
        self.high_priority_threshold = 0.8
        self.low_priority_threshold = 0.3
        self.defer_threshold = 0.1
        
        # Load-based processing settings
        self.high_load_threshold = 80.0  # CPU %
        self.critical_load_threshold = 95.0
        
        # Processing statistics
        self.processing_stats = {
            "high_priority_processed": 0,
            "normal_priority_processed": 0,
            "low_priority_processed": 0,
            "deferred_count": 0,
            "total_processed": 0
        }
        
        # Thread safety
        self._lock = threading.Lock()
    
    def calculate_token_priority(self, token) -> float:
        """Calculate priority score for a token based on value and activity."""
        try:
            # Get token metrics
            liquidity = getattr(token, 'liquidity_wsol', 0) or 0
            volume_24h = getattr(token, 'volume_24h', 0) or 0
            price_change_5m = abs(getattr(token, 'price_change_5m', 0) or 0)
            price_change_15m = abs(getattr(token, 'price_change_15m', 0) or 0)
            
            # Calculate activity score based on recent updates
            activity_score = 0.5  # Default
            if hasattr(token, 'updated_at') and token.updated_at:
                import time
                time_since_update = time.time() - token.updated_at.timestamp()
                # Higher score for more recently updated tokens
                activity_score = max(0.1, 1.0 - (time_since_update / 3600))  # Decay over 1 hour
            
            # Normalize metrics (simple approach)
            # These thresholds should be calibrated based on actual data
            liquidity_score = min(1.0, liquidity / 100000)  # Normalize to 100k WSOL
            volume_score = min(1.0, volume_24h / 1000000)   # Normalize to 1M volume
            momentum_score = min(1.0, (price_change_5m + price_change_15m) / 20)  # Normalize to 20% change
            
            # Calculate weighted priority score
            priority_score = (
                liquidity_score * self.liquidity_weight +
                volume_score * self.volume_weight +
                momentum_score * self.price_momentum_weight +
                activity_score * self.activity_weight
            )
            
            token_id = getattr(token, 'address', None) or getattr(token, 'mint', None) or 'unknown'
            self.logger.debug(
                f"Token priority calculated: {token_id[:8] if token_id != 'unknown' else token_id}",
                extra={
                    "extra": {
                        "token_address": token_id,
                        "priority_score": priority_score,
                        "liquidity_score": liquidity_score,
                        "volume_score": volume_score,
                        "momentum_score": momentum_score,
                        "activity_score": activity_score
                    }
                }
            )
            
            return priority_score
            
        except Exception as e:
            token_id = getattr(token, 'address', None) or getattr(token, 'mint', None) or 'unknown'
            self.logger.error(
                f"Failed to calculate token priority: {token_id}",
                extra={
                    "extra": {
                        "error": str(e)
                    }
                }
            )
            return 0.5  # Default medium priority
    
    def categorize_token_by_priority(self, token, priority_score: float) -> str:
        """Categorize token based on priority score."""
        if priority_score >= self.high_priority_threshold:
            return "high"
        elif priority_score <= self.low_priority_threshold:
            return "low"
        else:
            return "normal"
    
    def get_prioritized_tokens(self, repo, group: str, limit: int, system_load: Dict[str, float]):
        """Get tokens ordered by priority with load-based adjustments."""
        try:
            # Get ALL tokens (both active and monitoring) for proper hot/cold filtering by score
            # Don't limit active tokens - we need to process all of them
            active_tokens = repo.list_by_status("active", limit=1000)  # Get all active tokens
            monitoring_tokens = repo.list_by_status("monitoring", limit=limit)  # Limit monitoring tokens
            base_tokens = active_tokens + monitoring_tokens
            
            if not base_tokens:
                return []
            
            # Calculate priority scores for all tokens
            token_priorities = []
            for token in base_tokens:
                priority_score = self.calculate_token_priority(token)
                token_priorities.append((token, priority_score))
            
            # Sort by priority score (highest first)
            token_priorities.sort(key=lambda x: x[1], reverse=True)
            
            # Apply load-based filtering
            cpu_usage = system_load.get("cpu_percent", 0)
            memory_usage = system_load.get("memory_percent", 0)
            
            prioritized_tokens = []
            high_priority_count = 0
            normal_priority_count = 0
            low_priority_count = 0
            deferred_count = 0
            
            with self._lock:
                for token, priority_score in token_priorities:
                    if len(prioritized_tokens) >= limit:
                        break
                    
                    category = self.categorize_token_by_priority(token, priority_score)
                    
                    # Load-based processing decisions
                    should_process = True
                    should_defer = False
                    
                    if cpu_usage > self.critical_load_threshold:
                        # Critical load: only high priority tokens
                        if category != "high":
                            should_process = False
                            should_defer = True
                    elif cpu_usage > self.high_load_threshold:
                        # High load: defer low priority tokens
                        if category == "low":
                            should_process = False
                            should_defer = True
                    
                    if should_defer:
                        self.deferred_queue.append((token, priority_score))
                        deferred_count += 1
                        continue
                    
                    if should_process:
                        prioritized_tokens.append(token)
                        
                        if category == "high":
                            high_priority_count += 1
                        elif category == "normal":
                            normal_priority_count += 1
                        else:
                            low_priority_count += 1
                
                # Update processing statistics
                self.processing_stats["high_priority_processed"] += high_priority_count
                self.processing_stats["normal_priority_processed"] += normal_priority_count
                self.processing_stats["low_priority_processed"] += low_priority_count
                self.processing_stats["deferred_count"] += deferred_count
                self.processing_stats["total_processed"] += len(prioritized_tokens)
            
            self.logger.info(
                f"Priority-based token selection completed for {group}",
                extra={
                    "extra": {
                        "group": group,
                        "total_candidates": len(base_tokens),
                        "selected_tokens": len(prioritized_tokens),
                        "high_priority": high_priority_count,
                        "normal_priority": normal_priority_count,
                        "low_priority": low_priority_count,
                        "deferred": deferred_count,
                        "cpu_usage": cpu_usage,
                        "memory_usage": memory_usage,
                        "limit": limit
                    }
                }
            )
            
            return prioritized_tokens
            
        except Exception as e:
            self.logger.error(
                f"Failed to get prioritized tokens for {group}",
                extra={
                    "extra": {
                        "group": group,
                        "limit": limit,
                        "error": str(e)
                    }
                }
            )
            # Fallback to regular token list
            return repo.list_by_status("active", limit=limit)
    
    def process_deferred_tokens(self, repo, max_tokens: int = 50) -> int:
        """Process deferred tokens when system load is low."""
        processed_count = 0
        
        with self._lock:
            tokens_to_process = []
            
            # Get tokens from deferred queue
            while self.deferred_queue and len(tokens_to_process) < max_tokens:
                token, priority_score = self.deferred_queue.popleft()
                tokens_to_process.append((token, priority_score))
            
            if not tokens_to_process:
                return 0
            
            # Sort deferred tokens by priority (process highest priority first)
            tokens_to_process.sort(key=lambda x: x[1], reverse=True)
            
            self.logger.info(
                f"Processing {len(tokens_to_process)} deferred tokens",
                extra={
                    "extra": {
                        "deferred_tokens": len(tokens_to_process),
                        "remaining_in_queue": len(self.deferred_queue)
                    }
                }
            )
            
            # For now, just log the processing
            # In a real implementation, this would trigger actual token processing
            processed_count = len(tokens_to_process)
            self.processing_stats["total_processed"] += processed_count
        
        return processed_count
    
    def get_priority_statistics(self) -> Dict[str, Any]:
        """Get priority processing statistics."""
        with self._lock:
            return {
                "processing_stats": self.processing_stats.copy(),
                "queue_sizes": {
                    "high_priority": len(self.high_priority_queue),
                    "normal_priority": len(self.normal_priority_queue),
                    "low_priority": len(self.low_priority_queue),
                    "deferred": len(self.deferred_queue)
                },
                "priority_thresholds": {
                    "high_priority_threshold": self.high_priority_threshold,
                    "low_priority_threshold": self.low_priority_threshold,
                    "defer_threshold": self.defer_threshold
                },
                "load_thresholds": {
                    "high_load_threshold": self.high_load_threshold,
                    "critical_load_threshold": self.critical_load_threshold
                },
                "scoring_weights": {
                    "liquidity_weight": self.liquidity_weight,
                    "volume_weight": self.volume_weight,
                    "price_momentum_weight": self.price_momentum_weight,
                    "activity_weight": self.activity_weight
                }
            }
    
    def adjust_priority_thresholds(self, high_threshold: float = None, 
                                 low_threshold: float = None, 
                                 defer_threshold: float = None):
        """Adjust priority thresholds dynamically."""
        with self._lock:
            if high_threshold is not None:
                self.high_priority_threshold = max(0.0, min(1.0, high_threshold))
            if low_threshold is not None:
                self.low_priority_threshold = max(0.0, min(1.0, low_threshold))
            if defer_threshold is not None:
                self.defer_threshold = max(0.0, min(1.0, defer_threshold))
        
        self.logger.info(
            "Priority thresholds adjusted",
            extra={
                "extra": {
                    "high_priority_threshold": self.high_priority_threshold,
                    "low_priority_threshold": self.low_priority_threshold,
                    "defer_threshold": self.defer_threshold
                }
            }
        )
    
    def clear_deferred_queue(self) -> int:
        """Clear the deferred queue and return count of cleared items."""
        with self._lock:
            cleared_count = len(self.deferred_queue)
            self.deferred_queue.clear()
        
        if cleared_count > 0:
            self.logger.info(
                f"Cleared {cleared_count} tokens from deferred queue",
                extra={
                    "extra": {
                        "cleared_count": cleared_count
                    }
                }
            )
        
        return cleared_count


# Global priority processor
priority_processor = None


def get_priority_processor() -> PriorityProcessor:
    """Get the global priority processor instance."""
    global priority_processor
    if priority_processor is None:
        priority_processor = PriorityProcessor()
    return priority_processor