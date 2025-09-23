"""
Enhanced health monitoring system for comprehensive system stability tracking.

This module provides the main HealthMonitor class that orchestrates monitoring
of all system components including scheduler, resources, and external APIs.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.settings.service import SettingsService

from .models import (
    HealthStatus, AlertLevel, CircuitState, HealthAlert,
    SchedulerHealth, ResourceHealth, APIHealth, SystemHealth,
    MonitoringConfig
)
from .metrics import (
    MetricsCollector, PerformanceAnalyzer, 
    create_correlation_id, aggregate_health_status,
    get_performance_tracker
)
from .alert_manager import get_alert_manager

log = logging.getLogger("health_monitor")


class HealthMonitor:
    """
    Comprehensive health monitoring system.
    
    Monitors scheduler health, system resources, API health, and provides
    aggregated system health status with intelligent alerting.
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.metrics_collector = MetricsCollector(self.config)
        self.performance_analyzer = PerformanceAnalyzer(self.config)
        
        # Tracking state
        self._start_time = time.time()
        self._last_restart: Optional[datetime] = None
        self._scheduler_execution_history: Dict[str, List[datetime]] = defaultdict(list)
        self._api_call_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._alert_cooldowns: Dict[str, datetime] = {}
        
        # Integration with existing scheduler monitor
        self._legacy_monitor: Optional[Any] = None
        try:
            from src.scheduler.monitoring import health_monitor
            self._legacy_monitor = health_monitor
        except ImportError:
            log.warning("Legacy scheduler monitor not available")
    
    def record_scheduler_execution(self, group: str, tokens_processed: int, tokens_updated: int, processing_time: float):
        """Record scheduler group execution for health tracking."""
        now = datetime.utcnow()
        
        # Keep last 50 executions for analysis
        history = self._scheduler_execution_history[group]
        history.append(now)
        if len(history) > 50:
            history.pop(0)
        
        # Also record in legacy monitor for backward compatibility
        if self._legacy_monitor:
            self._legacy_monitor.record_group_execution(group, tokens_processed, tokens_updated)
        
        log.info(
            "scheduler_execution_recorded",
            extra={
                "group": group,
                "processed": tokens_processed,
                "updated": tokens_updated,
                "processing_time": processing_time,
                "timestamp": now.isoformat()
            }
        )
    
    def record_api_call(self, service: str, success: bool, response_time: float, error: Optional[str] = None):
        """Record API call for health tracking."""
        now = datetime.utcnow()
        
        call_record = {
            "timestamp": now,
            "success": success,
            "response_time": response_time,
            "error": error
        }
        
        # Keep last 100 API calls for analysis
        history = self._api_call_history[service]
        history.append(call_record)
        if len(history) > 100:
            history.pop(0)
        
        # Track performance metrics
        self.performance_analyzer.add_metric(service, "api_response_time", response_time)
        if not success:
            self.performance_analyzer.add_metric(service, "api_error_rate", 1.0)
        
        # Record in performance tracker
        performance_tracker = get_performance_tracker()
        performance_tracker.record_api_call(service, response_time, success, error)
    
    async def monitor_scheduler_health(self) -> SchedulerHealth:
        """Monitor scheduler component health."""
        now = datetime.utcnow()
        alerts = []
        
        # Import scheduler health monitor
        try:
            from src.scheduler.monitoring import get_scheduler_health_monitor
            scheduler_monitor = get_scheduler_health_monitor()
            
            # Get comprehensive health status from scheduler monitor
            scheduler_status = scheduler_monitor.get_comprehensive_health_status()
            
            # Extract data for SchedulerHealth model
            hot_last_run = None
            cold_last_run = None
            
            if scheduler_status["hot_group"]["last_run"]:
                hot_last_run = datetime.fromisoformat(scheduler_status["hot_group"]["last_run"].replace('Z', '+00:00'))
            
            if scheduler_status["cold_group"]["last_run"]:
                cold_last_run = datetime.fromisoformat(scheduler_status["cold_group"]["last_run"].replace('Z', '+00:00'))
            
            hot_processing_time = scheduler_status["hot_group"]["average_processing_time"]
            cold_processing_time = scheduler_status["cold_group"]["average_processing_time"]
            tokens_per_minute = scheduler_status["performance"]["tokens_per_minute"]
            error_rate = scheduler_status["performance"]["total_errors_last_hour"]
            active_jobs = scheduler_status["performance"]["active_jobs"]
            failed_jobs = scheduler_status["performance"]["stuck_jobs"]
            
            # Convert scheduler alerts to HealthAlert objects
            for alert_data in scheduler_status["alerts"]:
                alerts.append(HealthAlert(
                    level=AlertLevel(alert_data["level"]),
                    message=alert_data["message"],
                    component=alert_data["component"],
                    timestamp=datetime.fromisoformat(alert_data["timestamp"].replace('Z', '+00:00')),
                    correlation_id=alert_data["correlation_id"],
                    context=alert_data.get("context", {})
                ))
                
        except ImportError:
            # Fallback to basic monitoring if scheduler monitor not available
            hot_history = self._scheduler_execution_history.get("hot", [])
            cold_history = self._scheduler_execution_history.get("cold", [])
            
            hot_last_run = hot_history[-1] if hot_history else None
            cold_last_run = cold_history[-1] if cold_history else None
            
            # Calculate processing times (average of last 5 runs)
            hot_processing_time = self._calculate_avg_processing_time("hot")
            cold_processing_time = self._calculate_avg_processing_time("cold")
            
            # Calculate tokens processed per minute
            tokens_per_minute = self._calculate_tokens_per_minute()
            
            # Calculate error rate from recent executions
            error_rate = self._calculate_error_rate()
            
            # Get active and failed job counts
            active_jobs, failed_jobs = self._get_job_counts()
        
        # Check for scheduler health issues
        if hot_last_run:
            hot_delay = (now - hot_last_run).total_seconds()
            expected_delay = self.config.health_check_interval * 2
            
            if hot_delay > expected_delay:
                alerts.append(HealthAlert(
                    level=AlertLevel.WARNING if hot_delay < expected_delay * 2 else AlertLevel.CRITICAL,
                    message=f"Hot group delayed by {hot_delay:.0f}s (expected {self.config.health_check_interval}s)",
                    component="scheduler.hot_group",
                    timestamp=now,
                    correlation_id=create_correlation_id()
                ))
        else:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message="Hot group has never executed",
                component="scheduler.hot_group",
                timestamp=now,
                correlation_id=create_correlation_id()
            ))
        
        if cold_last_run:
            cold_delay = (now - cold_last_run).total_seconds()
            expected_delay = self.config.resource_check_interval * 2
            
            if cold_delay > expected_delay:
                alerts.append(HealthAlert(
                    level=AlertLevel.WARNING if cold_delay < expected_delay * 2 else AlertLevel.CRITICAL,
                    message=f"Cold group delayed by {cold_delay:.0f}s (expected {self.config.resource_check_interval}s)",
                    component="scheduler.cold_group",
                    timestamp=now,
                    correlation_id=create_correlation_id()
                ))
        else:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message="Cold group has never executed",
                component="scheduler.cold_group",
                timestamp=now,
                correlation_id=create_correlation_id()
            ))
        
        # Check processing time thresholds
        if hot_processing_time > self.config.scheduler_processing_time_critical:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message=f"Hot group processing time critical: {hot_processing_time:.1f}s",
                component="scheduler.performance",
                timestamp=now
            ))
        elif hot_processing_time > self.config.scheduler_processing_time_warning:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"Hot group processing time high: {hot_processing_time:.1f}s",
                component="scheduler.performance",
                timestamp=now
            ))
        
        # Check tokens per minute threshold
        if tokens_per_minute < self.config.tokens_per_minute_warning:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"Low token processing rate: {tokens_per_minute:.1f}/min",
                component="scheduler.throughput",
                timestamp=now
            ))
        
        # Determine overall scheduler status
        if any(alert.level == AlertLevel.CRITICAL for alert in alerts):
            status = HealthStatus.CRITICAL
        elif any(alert.level == AlertLevel.ERROR for alert in alerts):
            status = HealthStatus.DEGRADED
        elif any(alert.level == AlertLevel.WARNING for alert in alerts):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        # Send alerts through alert manager
        if alerts:
            alert_manager = get_alert_manager()
            sent_count = alert_manager.send_alerts(alerts)
            log.debug(
                "scheduler_alerts_sent",
                extra={
                    "extra": {
                        "total_alerts": len(alerts),
                        "sent_alerts": sent_count,
                        "scheduler_status": status.value
                    }
                }
            )
        
        return SchedulerHealth(
            status=status,
            hot_group_last_run=hot_last_run,
            cold_group_last_run=cold_last_run,
            hot_group_processing_time=hot_processing_time,
            cold_group_processing_time=cold_processing_time,
            tokens_processed_per_minute=tokens_per_minute,
            error_rate=error_rate,
            active_jobs=active_jobs,
            failed_jobs_last_hour=failed_jobs,
            alerts=alerts
        )
    
    async def monitor_resource_usage(self) -> ResourceHealth:
        """Monitor system resource usage."""
        return self.metrics_collector.collect_resource_metrics()
    
    async def monitor_api_health(self, service: str = "dexscreener") -> APIHealth:
        """Monitor external API health."""
        now = datetime.utcnow()
        history = self._api_call_history.get(service, [])
        
        if not history:
            return APIHealth(
                service_name=service,
                status=HealthStatus.UNKNOWN,
                average_response_time=0.0,
                p95_response_time=0.0,
                error_rate=0.0,
                circuit_breaker_state=CircuitState.CLOSED,
                cache_hit_rate=0.0,
                requests_per_minute=0.0,
                last_successful_call=None,
                consecutive_failures=0
            )
        
        # Analyze recent calls (last 10 minutes)
        recent_cutoff = now - timedelta(minutes=10)
        recent_calls = [call for call in history if call["timestamp"] > recent_cutoff]
        
        if not recent_calls:
            return APIHealth(
                service_name=service,
                status=HealthStatus.UNKNOWN,
                average_response_time=0.0,
                p95_response_time=0.0,
                error_rate=0.0,
                circuit_breaker_state=CircuitState.CLOSED,
                cache_hit_rate=0.0,
                requests_per_minute=0.0,
                last_successful_call=None,
                consecutive_failures=0
            )
        
        # Calculate metrics
        response_times = [call["response_time"] for call in recent_calls]
        avg_response_time = sum(response_times) / len(response_times)
        
        sorted_times = sorted(response_times)
        p95_index = int(0.95 * len(sorted_times))
        p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
        
        successful_calls = [call for call in recent_calls if call["success"]]
        error_rate = ((len(recent_calls) - len(successful_calls)) / len(recent_calls)) * 100
        
        requests_per_minute = len(recent_calls) / 10.0  # 10-minute window
        
        last_successful_call = None
        if successful_calls:
            last_successful_call = max(call["timestamp"] for call in successful_calls)
        
        # Count consecutive failures from the end
        consecutive_failures = 0
        for call in reversed(history):
            if call["success"]:
                break
            consecutive_failures += 1
        
        # Determine circuit breaker state (simplified)
        if consecutive_failures >= 5:
            circuit_state = CircuitState.OPEN
        elif consecutive_failures >= 3:
            circuit_state = CircuitState.HALF_OPEN
        else:
            circuit_state = CircuitState.CLOSED
        
        # Generate alerts
        alerts = []
        if error_rate >= self.config.api_error_rate_critical:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message=f"{service} API error rate critical: {error_rate:.1f}%",
                component=f"api.{service}",
                timestamp=now
            ))
        elif error_rate >= self.config.api_error_rate_warning:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"{service} API error rate high: {error_rate:.1f}%",
                component=f"api.{service}",
                timestamp=now
            ))
        
        if avg_response_time >= self.config.api_response_time_critical:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message=f"{service} API response time critical: {avg_response_time:.1f}ms",
                component=f"api.{service}",
                timestamp=now
            ))
        elif avg_response_time >= self.config.api_response_time_warning:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"{service} API response time high: {avg_response_time:.1f}ms",
                component=f"api.{service}",
                timestamp=now
            ))
        
        # Determine overall API status
        if circuit_state == CircuitState.OPEN or error_rate >= self.config.api_error_rate_critical:
            status = HealthStatus.CRITICAL
        elif error_rate >= self.config.api_error_rate_warning or avg_response_time >= self.config.api_response_time_warning:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        # Send alerts through alert manager
        if alerts:
            alert_manager = get_alert_manager()
            sent_count = alert_manager.send_alerts(alerts)
            log.debug(
                "api_alerts_sent",
                extra={
                    "extra": {
                        "service": service,
                        "total_alerts": len(alerts),
                        "sent_alerts": sent_count,
                        "api_status": status.value
                    }
                }
            )
        
        return APIHealth(
            service_name=service,
            status=status,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            error_rate=error_rate,
            circuit_breaker_state=circuit_state,
            cache_hit_rate=0.0,  # TODO: Implement cache hit rate tracking
            requests_per_minute=requests_per_minute,
            last_successful_call=last_successful_call,
            consecutive_failures=consecutive_failures,
            alerts=alerts
        )
    
    def get_comprehensive_health(self) -> SystemHealth:
        """Get complete system health status."""
        # This method should be called from an async context
        # For now, we'll create a synchronous version that can be called from async
        return asyncio.create_task(self._get_comprehensive_health_async()).result()
    
    async def get_comprehensive_health_async(self) -> SystemHealth:
        """Get complete system health status (async version)."""
        return await self._get_comprehensive_health_async()
    
    async def _get_comprehensive_health_async(self) -> SystemHealth:
        """Internal async method for getting comprehensive health."""
        # Gather all health checks concurrently
        scheduler_health_task = self.monitor_scheduler_health()
        resource_health_task = self.monitor_resource_usage()
        api_health_task = self.monitor_api_health("dexscreener")
        
        scheduler_health, resource_health, api_health = await asyncio.gather(
            scheduler_health_task, resource_health_task, api_health_task
        )
        
        # Aggregate overall status
        component_statuses = [
            scheduler_health.status,
            resource_health.status,
            api_health.status
        ]
        overall_status = aggregate_health_status(component_statuses)
        
        # Calculate uptime
        uptime_seconds = time.time() - self._start_time
        
        return SystemHealth(
            overall_status=overall_status,
            scheduler=scheduler_health,
            resources=resource_health,
            apis={"dexscreener": api_health},
            uptime_seconds=uptime_seconds,
            last_restart=self._last_restart
        )
    
    def _calculate_avg_processing_time(self, group: str) -> float:
        """Calculate average processing time for a scheduler group."""
        # This is a placeholder - in real implementation, we'd track actual processing times
        # For now, return reasonable defaults based on group type
        if group == "hot":
            return 25.0  # seconds
        else:
            return 90.0  # seconds
    
    def _calculate_tokens_per_minute(self) -> float:
        """Calculate tokens processed per minute."""
        # This is a placeholder - in real implementation, we'd track actual token processing
        return 3.5
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate from recent scheduler executions."""
        # This is a placeholder - in real implementation, we'd track actual errors
        return 2.0  # 2% error rate
    
    def _get_job_counts(self) -> tuple[int, int]:
        """Get active and failed job counts."""
        # This is a placeholder - in real implementation, we'd query the actual scheduler
        return 4, 1  # 4 active jobs, 1 failed in last hour
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Check if alert should be sent based on cooldown."""
        now = datetime.utcnow()
        last_sent = self._alert_cooldowns.get(alert_key)
        
        if not last_sent:
            self._alert_cooldowns[alert_key] = now
            return True
        
        cooldown_seconds = self.config.alert_cooldown
        if (now - last_sent).total_seconds() >= cooldown_seconds:
            self._alert_cooldowns[alert_key] = now
            return True
        
        return False


# Global health monitor instance
health_monitor = HealthMonitor()


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    return health_monitor