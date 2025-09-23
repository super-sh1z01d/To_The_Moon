"""
Data models for system health monitoring and performance tracking.

This module defines all the data structures used for monitoring system health,
tracking performance metrics, and managing alerts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from decimal import Decimal


class HealthStatus(str, Enum):
    """Health status levels for system components."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HealthAlert:
    """Individual health alert with context."""
    level: AlertLevel
    message: str
    component: str
    timestamp: datetime
    correlation_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulerHealth:
    """Health status for the scheduler component."""
    status: HealthStatus
    hot_group_last_run: Optional[datetime]
    cold_group_last_run: Optional[datetime]
    hot_group_processing_time: float  # seconds
    cold_group_processing_time: float  # seconds
    tokens_processed_per_minute: float
    error_rate: float  # percentage (0-100)
    active_jobs: int
    failed_jobs_last_hour: int
    alerts: List[HealthAlert] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourceHealth:
    """System resource health status."""
    memory_usage_mb: float
    memory_usage_percent: float
    cpu_usage_percent: float
    disk_usage_percent: float
    database_connections: int
    max_database_connections: int
    open_file_descriptors: int
    max_file_descriptors: int
    status: HealthStatus
    alerts: List[HealthAlert] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.utcnow)


@dataclass
class APIHealth:
    """External API health status."""
    service_name: str
    status: HealthStatus
    average_response_time: float  # milliseconds
    p95_response_time: float  # milliseconds
    error_rate: float  # percentage (0-100)
    circuit_breaker_state: CircuitState
    cache_hit_rate: float  # percentage (0-100)
    requests_per_minute: float
    last_successful_call: Optional[datetime]
    consecutive_failures: int
    alerts: List[HealthAlert] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SystemHealth:
    """Comprehensive system health status."""
    overall_status: HealthStatus
    scheduler: SchedulerHealth
    resources: ResourceHealth
    apis: Dict[str, APIHealth]  # keyed by service name
    uptime_seconds: float
    last_restart: Optional[datetime]
    alerts: List[HealthAlert] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def get_all_alerts(self) -> List[HealthAlert]:
        """Get all alerts from all components."""
        all_alerts = list(self.alerts)
        all_alerts.extend(self.scheduler.alerts)
        all_alerts.extend(self.resources.alerts)
        for api_health in self.apis.values():
            all_alerts.extend(api_health.alerts)
        return sorted(all_alerts, key=lambda x: x.timestamp, reverse=True)

    def get_critical_alerts(self) -> List[HealthAlert]:
        """Get only critical and error level alerts."""
        return [
            alert for alert in self.get_all_alerts()
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.ERROR]
        ]


@dataclass
class PerformanceMetrics:
    """Performance metrics for system components."""
    component: str
    timestamp: datetime
    
    # API performance
    api_response_times: List[float] = field(default_factory=list)  # milliseconds
    api_success_rate: float = 0.0  # percentage (0-100)
    api_calls_per_minute: float = 0.0
    
    # Processing performance
    processing_times: List[float] = field(default_factory=list)  # seconds
    throughput_per_minute: float = 0.0
    queue_size: int = 0
    
    # Resource usage
    memory_usage_trend: List[float] = field(default_factory=list)  # MB
    cpu_usage_trend: List[float] = field(default_factory=list)  # percentage
    
    # Database performance
    db_query_times: List[float] = field(default_factory=list)  # milliseconds
    db_connection_pool_usage: float = 0.0  # percentage

    def get_avg_api_response_time(self) -> float:
        """Calculate average API response time."""
        return sum(self.api_response_times) / len(self.api_response_times) if self.api_response_times else 0.0

    def get_p95_api_response_time(self) -> float:
        """Calculate 95th percentile API response time."""
        if not self.api_response_times:
            return 0.0
        sorted_times = sorted(self.api_response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]

    def get_avg_processing_time(self) -> float:
        """Calculate average processing time."""
        return sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0.0


@dataclass
class PerformanceAlert:
    """Alert for performance degradation."""
    metric_name: str
    current_value: float
    threshold_value: float
    severity: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trend_direction: str = "stable"  # "increasing", "decreasing", "stable"


@dataclass
class MonitoringConfig:
    """Configuration for monitoring system."""
    health_check_interval: int = 30  # seconds
    resource_check_interval: int = 60  # seconds
    performance_check_interval: int = 120  # seconds
    alert_cooldown: int = 300  # seconds
    
    # Resource thresholds
    memory_warning_threshold: float = 800.0  # MB
    memory_critical_threshold: float = 1000.0  # MB
    cpu_warning_threshold: float = 70.0  # percentage
    cpu_critical_threshold: float = 80.0  # percentage
    disk_warning_threshold: float = 80.0  # percentage
    disk_critical_threshold: float = 90.0  # percentage
    
    # Performance thresholds
    api_response_time_warning: float = 2000.0  # milliseconds
    api_response_time_critical: float = 5000.0  # milliseconds
    api_error_rate_warning: float = 10.0  # percentage
    api_error_rate_critical: float = 20.0  # percentage
    
    # Scheduler thresholds
    scheduler_processing_time_warning: float = 300.0  # seconds
    scheduler_processing_time_critical: float = 600.0  # seconds
    tokens_per_minute_warning: float = 1.0  # minimum expected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }


@dataclass
class RecoveryConfig:
    """Configuration for recovery and self-healing."""
    max_restart_attempts: int = 3
    restart_cooldown: int = 300  # seconds
    graceful_shutdown_timeout: int = 30  # seconds
    emergency_restart_threshold: int = 600  # seconds
    
    # Circuit breaker settings
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: int = 60  # seconds
    circuit_half_open_max_calls: int = 3
    
    # Retry settings
    max_retries: int = 3
    base_retry_delay: float = 1.0  # seconds
    max_retry_delay: float = 30.0  # seconds
    retry_exponential_base: float = 2.0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    success_threshold: int = 2  # successes needed to close circuit
    
    # Timeout settings
    call_timeout: float = 10.0  # seconds
    slow_call_threshold: float = 5.0  # seconds
    slow_call_rate_threshold: float = 50.0  # percentage