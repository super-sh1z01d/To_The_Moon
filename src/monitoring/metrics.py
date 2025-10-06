"""
Utilities for collecting and managing health metrics.

This module provides helper functions and classes for collecting,
aggregating, and analyzing system health metrics.
"""

import psutil
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict, deque

from .models import (
    HealthStatus, AlertLevel, HealthAlert, ResourceHealth,
    PerformanceMetrics, PerformanceAlert, MonitoringConfig
)


class MetricsCollector:
    """Collects system metrics for health monitoring."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._start_time = time.time()
    
    def collect_resource_metrics(self) -> ResourceHealth:
        """Collect current system resource metrics with intelligent memory management."""
        # Use intelligent memory manager for memory metrics and optimization
        from .memory_manager import get_memory_manager
        memory_manager = get_memory_manager()
        
        # Check memory and perform optimization if needed
        memory_needs_alert, memory_alerts = memory_manager.check_memory_and_optimize()
        
        # Get current memory snapshot after any optimization
        memory_snapshot = memory_manager.get_current_memory_snapshot()
        memory_mb = memory_snapshot.used_mb
        memory_percent = memory_snapshot.percent_used
        
        # CPU metrics (non-blocking)
        cpu_percent = psutil.cpu_percent(interval=0)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Process metrics
        try:
            process = psutil.Process()
            open_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            max_fds = 1024  # Default, could be read from system limits
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            open_fds = 0
            max_fds = 1024
        
        # Database connections (placeholder - would need actual DB pool)
        db_connections = 0
        max_db_connections = 100
        
        # Determine overall status (memory status now comes from memory manager)
        status = self._determine_resource_status_with_memory_manager(
            memory_needs_alert, cpu_percent, disk_percent
        )
        
        # Combine memory alerts with other resource alerts
        all_alerts = list(memory_alerts)  # Start with intelligent memory alerts
        
        # Add CPU and disk alerts
        cpu_disk_alerts = self._generate_cpu_disk_alerts(cpu_percent, disk_percent)
        all_alerts.extend(cpu_disk_alerts)
        
        return ResourceHealth(
            memory_usage_mb=memory_mb,
            memory_usage_percent=memory_percent,
            cpu_usage_percent=cpu_percent,
            disk_usage_percent=disk_percent,
            database_connections=db_connections,
            max_database_connections=max_db_connections,
            open_file_descriptors=open_fds,
            max_file_descriptors=max_fds,
            status=status,
            alerts=all_alerts
        )
    
    def _determine_resource_status_with_memory_manager(
        self, memory_needs_alert: bool, cpu_percent: float, disk_percent: float
    ) -> HealthStatus:
        """Determine overall resource health status with intelligent memory management."""
        # Check CPU and disk against thresholds
        cpu_critical = cpu_percent >= self.config.cpu_critical_threshold
        cpu_warning = cpu_percent >= self.config.cpu_warning_threshold
        disk_critical = disk_percent >= self.config.disk_critical_threshold
        disk_warning = disk_percent >= self.config.disk_warning_threshold
        
        # Memory status is determined by the intelligent memory manager
        if memory_needs_alert or cpu_critical or disk_critical:
            return HealthStatus.CRITICAL
        
        if cpu_warning or disk_warning:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _determine_resource_status(
        self, memory_mb: float, cpu_percent: float, disk_percent: float
    ) -> HealthStatus:
        """Determine overall resource health status (legacy method)."""
        if (memory_mb >= self.config.memory_critical_threshold or
            cpu_percent >= self.config.cpu_critical_threshold or
            disk_percent >= self.config.disk_critical_threshold):
            return HealthStatus.CRITICAL
        
        if (memory_mb >= self.config.memory_warning_threshold or
            cpu_percent >= self.config.cpu_warning_threshold or
            disk_percent >= self.config.disk_warning_threshold):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _generate_cpu_disk_alerts(
        self, cpu_percent: float, disk_percent: float
    ) -> List[HealthAlert]:
        """Generate alerts for CPU and disk usage (memory handled by memory manager)."""
        alerts = []
        now = datetime.utcnow()
        
        # CPU alerts
        if cpu_percent >= self.config.cpu_critical_threshold:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message=f"CPU usage critical: {cpu_percent:.1f}% (threshold: {self.config.cpu_critical_threshold}%)",
                component="system.cpu",
                timestamp=now
            ))
        elif cpu_percent >= self.config.cpu_warning_threshold:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"CPU usage high: {cpu_percent:.1f}% (threshold: {self.config.cpu_warning_threshold}%)",
                component="system.cpu",
                timestamp=now
            ))
        
        # Disk alerts
        if disk_percent >= self.config.disk_critical_threshold:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message=f"Disk usage critical: {disk_percent:.1f}% (threshold: {self.config.disk_critical_threshold}%)",
                component="system.disk",
                timestamp=now
            ))
        elif disk_percent >= self.config.disk_warning_threshold:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"Disk usage high: {disk_percent:.1f}% (threshold: {self.config.disk_warning_threshold}%)",
                component="system.disk",
                timestamp=now
            ))
        
        return alerts
    
    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self._start_time


class PerformanceAnalyzer:
    """Analyzes performance metrics and detects issues."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._metrics_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
    
    def add_metric(self, component: str, metric_name: str, value: float):
        """Add a metric value to the history."""
        key = f"{component}.{metric_name}"
        self._metrics_history[key].append({
            'value': value,
            'timestamp': datetime.utcnow()
        })
    
    def analyze_trends(self, component: str, metric_name: str) -> Tuple[str, float]:
        """Analyze trend for a specific metric."""
        key = f"{component}.{metric_name}"
        history = self._metrics_history[key]
        
        if len(history) < 3:
            return "stable", 0.0
        
        # Calculate trend over last 5 data points
        recent_values = [item['value'] for item in list(history)[-5:]]
        
        # Simple linear trend calculation
        n = len(recent_values)
        x_sum = sum(range(n))
        y_sum = sum(recent_values)
        xy_sum = sum(i * v for i, v in enumerate(recent_values))
        x2_sum = sum(i * i for i in range(n))
        
        if n * x2_sum - x_sum * x_sum == 0:
            return "stable", 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
        # Determine trend direction
        if abs(slope) < 0.1:  # Threshold for considering stable
            return "stable", slope
        elif slope > 0:
            return "increasing", slope
        else:
            return "decreasing", slope
    
    def detect_performance_issues(
        self, metrics: PerformanceMetrics
    ) -> List[PerformanceAlert]:
        """Detect performance issues from metrics."""
        alerts = []
        now = datetime.utcnow()
        
        # API response time analysis
        avg_response_time = metrics.get_avg_api_response_time()
        if avg_response_time > 0:
            self.add_metric(metrics.component, "api_response_time", avg_response_time)
            trend, slope = self.analyze_trends(metrics.component, "api_response_time")
            
            if avg_response_time >= self.config.api_response_time_critical:
                alerts.append(PerformanceAlert(
                    metric_name="api_response_time",
                    current_value=avg_response_time,
                    threshold_value=self.config.api_response_time_critical,
                    severity=AlertLevel.CRITICAL,
                    message=f"API response time critical: {avg_response_time:.1f}ms",
                    trend_direction=trend
                ))
            elif avg_response_time >= self.config.api_response_time_warning:
                alerts.append(PerformanceAlert(
                    metric_name="api_response_time",
                    current_value=avg_response_time,
                    threshold_value=self.config.api_response_time_warning,
                    severity=AlertLevel.WARNING,
                    message=f"API response time high: {avg_response_time:.1f}ms",
                    trend_direction=trend
                ))
        
        # API error rate analysis
        if metrics.api_success_rate < 100:
            error_rate = 100 - metrics.api_success_rate
            self.add_metric(metrics.component, "api_error_rate", error_rate)
            trend, slope = self.analyze_trends(metrics.component, "api_error_rate")
            
            if error_rate >= self.config.api_error_rate_critical:
                alerts.append(PerformanceAlert(
                    metric_name="api_error_rate",
                    current_value=error_rate,
                    threshold_value=self.config.api_error_rate_critical,
                    severity=AlertLevel.CRITICAL,
                    message=f"API error rate critical: {error_rate:.1f}%",
                    trend_direction=trend
                ))
            elif error_rate >= self.config.api_error_rate_warning:
                alerts.append(PerformanceAlert(
                    metric_name="api_error_rate",
                    current_value=error_rate,
                    threshold_value=self.config.api_error_rate_warning,
                    severity=AlertLevel.WARNING,
                    message=f"API error rate high: {error_rate:.1f}%",
                    trend_direction=trend
                ))
        
        # Processing time analysis
        avg_processing_time = metrics.get_avg_processing_time()
        if avg_processing_time > 0:
            self.add_metric(metrics.component, "processing_time", avg_processing_time)
            
            if avg_processing_time >= self.config.scheduler_processing_time_critical:
                alerts.append(PerformanceAlert(
                    metric_name="processing_time",
                    current_value=avg_processing_time,
                    threshold_value=self.config.scheduler_processing_time_critical,
                    severity=AlertLevel.CRITICAL,
                    message=f"Processing time critical: {avg_processing_time:.1f}s"
                ))
            elif avg_processing_time >= self.config.scheduler_processing_time_warning:
                alerts.append(PerformanceAlert(
                    metric_name="processing_time",
                    current_value=avg_processing_time,
                    threshold_value=self.config.scheduler_processing_time_warning,
                    severity=AlertLevel.WARNING,
                    message=f"Processing time high: {avg_processing_time:.1f}s"
                ))
        
        return alerts


def create_correlation_id() -> str:
    """Create a unique correlation ID for tracking related events."""
    import uuid
    return str(uuid.uuid4())[:8]


def aggregate_health_status(statuses: List[HealthStatus]) -> HealthStatus:
    """Aggregate multiple health statuses into overall status."""
    if not statuses:
        return HealthStatus.UNKNOWN
    
    if HealthStatus.CRITICAL in statuses:
        return HealthStatus.CRITICAL
    elif HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    elif all(status == HealthStatus.HEALTHY for status in statuses):
        return HealthStatus.HEALTHY
    else:
        return HealthStatus.UNKNOWN


class PerformanceTracker:
    """
    Comprehensive performance tracking system.
    
    Tracks API call timing, success rates, processing times, and provides
    performance analytics and trend analysis.
    """
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        
        # API call tracking
        self._api_calls: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._api_stats: Dict[str, Dict] = defaultdict(dict)
        
        # Scheduler group tracking
        self._scheduler_executions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._scheduler_stats: Dict[str, Dict] = defaultdict(dict)
        
        # System performance tracking
        self._system_metrics: deque = deque(maxlen=max_history_size)
        
        # Performance baselines
        self._baselines: Dict[str, float] = {}
        
        # Start time for uptime calculation
        self._start_time = time.time()
    
    def record_api_call(self, service: str, response_time: float, success: bool, 
                       error: Optional[str] = None, endpoint: Optional[str] = None):
        """Record an API call for performance tracking."""
        timestamp = time.time()
        
        call_record = {
            'timestamp': timestamp,
            'response_time': response_time,
            'success': success,
            'error': error,
            'endpoint': endpoint
        }
        
        self._api_calls[service].append(call_record)
        self._update_api_stats(service)
    
    def record_scheduler_execution(self, group: str, processing_time: float, 
                                 tokens_processed: int, tokens_updated: int,
                                 error_count: int = 0):
        """Record scheduler group execution for performance tracking."""
        timestamp = time.time()
        
        execution_record = {
            'timestamp': timestamp,
            'processing_time': processing_time,
            'tokens_processed': tokens_processed,
            'tokens_updated': tokens_updated,
            'error_count': error_count,
            'success_rate': (tokens_updated / tokens_processed) if tokens_processed > 0 else 0
        }
        
        self._scheduler_executions[group].append(execution_record)
        self._update_scheduler_stats(group)
    
    def record_system_metrics(self, cpu_percent: float, memory_percent: float, 
                            disk_percent: float, active_connections: int):
        """Record system-level performance metrics."""
        timestamp = time.time()
        
        metrics_record = {
            'timestamp': timestamp,
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'active_connections': active_connections
        }
        
        self._system_metrics.append(metrics_record)
    
    def _update_api_stats(self, service: str):
        """Update cached statistics for an API service."""
        calls = list(self._api_calls[service])
        if not calls:
            return
        
        # Calculate time-based metrics
        now = time.time()
        last_hour = [c for c in calls if now - c['timestamp'] <= 3600]
        last_minute = [c for c in calls if now - c['timestamp'] <= 60]
        
        # Response time statistics
        response_times = [c['response_time'] for c in calls]
        recent_response_times = [c['response_time'] for c in last_hour]
        
        # Success rate statistics
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c['success']])
        recent_successful = len([c for c in last_hour if c['success']])
        
        self._api_stats[service] = {
            'total_calls': total_calls,
            'success_rate': (successful_calls / total_calls) * 100 if total_calls > 0 else 0,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'p95_response_time': self._calculate_percentile(response_times, 95),
            'p99_response_time': self._calculate_percentile(response_times, 99),
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'calls_per_minute': len(last_minute),
            'calls_per_hour': len(last_hour),
            'recent_success_rate': (recent_successful / len(last_hour)) * 100 if last_hour else 0,
            'recent_avg_response_time': sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0,
            'last_call_time': calls[-1]['timestamp'] if calls else 0,
            'error_rate': ((total_calls - successful_calls) / total_calls) * 100 if total_calls > 0 else 0
        }
    
    def _update_scheduler_stats(self, group: str):
        """Update cached statistics for a scheduler group."""
        executions = list(self._scheduler_executions[group])
        if not executions:
            return
        
        # Calculate time-based metrics
        now = time.time()
        last_hour = [e for e in executions if now - e['timestamp'] <= 3600]
        
        # Processing time statistics
        processing_times = [e['processing_time'] for e in executions]
        tokens_processed = [e['tokens_processed'] for e in executions]
        tokens_updated = [e['tokens_updated'] for e in executions]
        error_counts = [e['error_count'] for e in executions]
        
        total_tokens_processed = sum(tokens_processed)
        total_tokens_updated = sum(tokens_updated)
        total_errors = sum(error_counts)
        
        self._scheduler_stats[group] = {
            'total_executions': len(executions),
            'average_processing_time': sum(processing_times) / len(processing_times) if processing_times else 0,
            'p95_processing_time': self._calculate_percentile(processing_times, 95),
            'min_processing_time': min(processing_times) if processing_times else 0,
            'max_processing_time': max(processing_times) if processing_times else 0,
            'total_tokens_processed': total_tokens_processed,
            'total_tokens_updated': total_tokens_updated,
            'overall_success_rate': (total_tokens_updated / total_tokens_processed) * 100 if total_tokens_processed > 0 else 0,
            'total_errors': total_errors,
            'error_rate': (total_errors / len(executions)) * 100 if executions else 0,
            'executions_per_hour': len(last_hour),
            'tokens_per_minute': (sum(e['tokens_processed'] for e in last_hour) / 60) if last_hour else 0,
            'last_execution_time': executions[-1]['timestamp'] if executions else 0
        }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value from a list of numbers."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index >= len(sorted_values):
                return sorted_values[lower_index]
            
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    
    def get_api_performance(self, service: str) -> Dict:
        """Get performance statistics for an API service."""
        if service not in self._api_stats:
            return {}
        
        stats = self._api_stats[service].copy()
        
        # Add trend analysis
        calls = list(self._api_calls[service])
        if len(calls) >= 10:
            recent_calls = calls[-10:]
            older_calls = calls[-20:-10] if len(calls) >= 20 else calls[:-10]
            
            recent_avg = sum(c['response_time'] for c in recent_calls) / len(recent_calls)
            older_avg = sum(c['response_time'] for c in older_calls) / len(older_calls) if older_calls else recent_avg
            
            stats['response_time_trend'] = 'improving' if recent_avg < older_avg else 'degrading' if recent_avg > older_avg else 'stable'
            stats['response_time_change_percent'] = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
        else:
            stats['response_time_trend'] = 'insufficient_data'
            stats['response_time_change_percent'] = 0
        
        return stats
    
    def get_scheduler_performance(self, group: str) -> Dict:
        """Get performance statistics for a scheduler group."""
        if group not in self._scheduler_stats:
            return {}
        
        stats = self._scheduler_stats[group].copy()
        
        # Add trend analysis
        executions = list(self._scheduler_executions[group])
        if len(executions) >= 10:
            recent_executions = executions[-10:]
            older_executions = executions[-20:-10] if len(executions) >= 20 else executions[:-10]
            
            recent_avg = sum(e['processing_time'] for e in recent_executions) / len(recent_executions)
            older_avg = sum(e['processing_time'] for e in older_executions) / len(older_executions) if older_executions else recent_avg
            
            stats['processing_time_trend'] = 'improving' if recent_avg < older_avg else 'degrading' if recent_avg > older_avg else 'stable'
            stats['processing_time_change_percent'] = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
        else:
            stats['processing_time_trend'] = 'insufficient_data'
            stats['processing_time_change_percent'] = 0
        
        return stats
    
    def get_system_performance(self) -> Dict:
        """Get system-level performance statistics."""
        if not self._system_metrics:
            return {}
        
        metrics = list(self._system_metrics)
        now = time.time()
        recent_metrics = [m for m in metrics if now - m['timestamp'] <= 3600]  # Last hour
        
        if not recent_metrics:
            recent_metrics = metrics
        
        # Calculate averages
        avg_cpu = sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m['memory_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m['disk_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_connections = sum(m['active_connections'] for m in recent_metrics) / len(recent_metrics)
        
        # Calculate peaks
        max_cpu = max(m['cpu_percent'] for m in recent_metrics)
        max_memory = max(m['memory_percent'] for m in recent_metrics)
        max_disk = max(m['disk_percent'] for m in recent_metrics)
        max_connections = max(m['active_connections'] for m in recent_metrics)
        
        return {
            'uptime_seconds': time.time() - self._start_time,
            'average_cpu_percent': avg_cpu,
            'average_memory_percent': avg_memory,
            'average_disk_percent': avg_disk,
            'average_connections': avg_connections,
            'peak_cpu_percent': max_cpu,
            'peak_memory_percent': max_memory,
            'peak_disk_percent': max_disk,
            'peak_connections': max_connections,
            'metrics_collected': len(metrics),
            'recent_metrics_count': len(recent_metrics)
        }
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary."""
        summary = {
            'system': self.get_system_performance(),
            'apis': {},
            'scheduler_groups': {},
            'overall_health': 'healthy'
        }
        
        # Add API performance
        for service in self._api_stats.keys():
            summary['apis'][service] = self.get_api_performance(service)
        
        # Add scheduler performance
        for group in self._scheduler_stats.keys():
            summary['scheduler_groups'][group] = self.get_scheduler_performance(group)
        
        # Determine overall health based on performance metrics
        health_issues = []
        
        # Check API health
        for service, stats in summary['apis'].items():
            if stats.get('recent_success_rate', 100) < 95:
                health_issues.append(f"{service} API success rate low")
            if stats.get('recent_avg_response_time', 0) > 5000:  # 5 seconds
                health_issues.append(f"{service} API response time high")
        
        # Check scheduler health
        for group, stats in summary['scheduler_groups'].items():
            if stats.get('error_rate', 0) > 10:  # 10% error rate
                health_issues.append(f"{group} scheduler error rate high")
            if stats.get('average_processing_time', 0) > 300:  # 5 minutes
                health_issues.append(f"{group} scheduler processing time high")
        
        # Check system health
        system_stats = summary['system']
        if system_stats.get('average_cpu_percent', 0) > 80:
            health_issues.append("High CPU usage")
        if system_stats.get('average_memory_percent', 0) > 85:
            health_issues.append("High memory usage")
        
        if health_issues:
            summary['overall_health'] = 'degraded' if len(health_issues) <= 2 else 'critical'
            summary['health_issues'] = health_issues
        
        return summary
    
    def set_performance_baseline(self, metric_name: str, value: float):
        """Set a performance baseline for comparison."""
        self._baselines[metric_name] = value
    
    def get_performance_baseline(self, metric_name: str) -> Optional[float]:
        """Get a performance baseline value."""
        return self._baselines.get(metric_name)
    
    def detect_performance_anomalies(self, service: str = None, group: str = None) -> List[Dict]:
        """Detect performance anomalies based on historical data."""
        anomalies = []
        
        if service and service in self._api_stats:
            api_stats = self.get_api_performance(service)
            
            # Check for response time anomalies
            if api_stats.get('response_time_change_percent', 0) > 50:
                anomalies.append({
                    'type': 'api_response_time_spike',
                    'service': service,
                    'severity': 'high' if api_stats['response_time_change_percent'] > 100 else 'medium',
                    'change_percent': api_stats['response_time_change_percent'],
                    'current_avg': api_stats.get('recent_avg_response_time', 0)
                })
            
            # Check for success rate drops
            if api_stats.get('recent_success_rate', 100) < 90:
                anomalies.append({
                    'type': 'api_success_rate_drop',
                    'service': service,
                    'severity': 'critical' if api_stats['recent_success_rate'] < 80 else 'high',
                    'success_rate': api_stats['recent_success_rate']
                })
        
        if group and group in self._scheduler_stats:
            scheduler_stats = self.get_scheduler_performance(group)
            
            # Check for processing time anomalies
            if scheduler_stats.get('processing_time_change_percent', 0) > 50:
                anomalies.append({
                    'type': 'scheduler_processing_time_spike',
                    'group': group,
                    'severity': 'high' if scheduler_stats['processing_time_change_percent'] > 100 else 'medium',
                    'change_percent': scheduler_stats['processing_time_change_percent'],
                    'current_avg': scheduler_stats.get('average_processing_time', 0)
                })
            
            # Check for error rate spikes
            if scheduler_stats.get('error_rate', 0) > 15:
                anomalies.append({
                    'type': 'scheduler_error_rate_spike',
                    'group': group,
                    'severity': 'critical' if scheduler_stats['error_rate'] > 25 else 'high',
                    'error_rate': scheduler_stats['error_rate']
                })
        
        return anomalies
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old performance data to prevent memory bloat."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0
        
        # Clean API call data
        for service in self._api_calls:
            original_size = len(self._api_calls[service])
            self._api_calls[service] = deque(
                [call for call in self._api_calls[service] if call['timestamp'] > cutoff_time],
                maxlen=self.max_history_size
            )
            cleaned_count += original_size - len(self._api_calls[service])
            
            # Update stats after cleanup
            if self._api_calls[service]:
                self._update_api_stats(service)
        
        # Clean scheduler execution data
        for group in self._scheduler_executions:
            original_size = len(self._scheduler_executions[group])
            self._scheduler_executions[group] = deque(
                [exec for exec in self._scheduler_executions[group] if exec['timestamp'] > cutoff_time],
                maxlen=self.max_history_size
            )
            cleaned_count += original_size - len(self._scheduler_executions[group])
            
            # Update stats after cleanup
            if self._scheduler_executions[group]:
                self._update_scheduler_stats(group)
        
        # Clean system metrics
        original_size = len(self._system_metrics)
        self._system_metrics = deque(
            [metric for metric in self._system_metrics if metric['timestamp'] > cutoff_time],
            maxlen=self.max_history_size
        )
        cleaned_count += original_size - len(self._system_metrics)
        
        return cleaned_count


# Global performance tracker instance
performance_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return performance_tracker


class LoadBasedProcessor:
    """
    Load-based processing adjustment system.
    
    Monitors system load and automatically adjusts processing parameters
    to maintain system stability under high load conditions.
    """
    
    def __init__(self, initial_processing_factor: float = 1.0):
        import logging
        self.log = logging.getLogger("load_processor")
        self.initial_processing_factor = initial_processing_factor
        
        self.cpu_threshold_warning = 70.0  # Start reducing load at 70% CPU
        self.cpu_threshold_critical = 85.0  # Aggressive reduction at 85% CPU
        self.memory_threshold_warning = 75.0  # Start reducing load at 75% memory
        self.memory_threshold_critical = 90.0  # Aggressive reduction at 90% memory
        
        # Processing adjustment factors
        self.normal_processing_factor = 1.0
        self.reduced_processing_factor = 0.7
        self.minimal_processing_factor = 0.3
        
        # Current state
        self.current_load_level = "normal"  # normal, reduced, minimal
        # Initialize processing factor from config or use normal factor
        self.current_processing_factor = getattr(self, 'initial_processing_factor', self.normal_processing_factor)
        self.disabled_features = set()
        
        # Load history for trend analysis
        self.load_history = deque(maxlen=60)  # Last 60 measurements
        
        # Hysteresis to prevent oscillation
        self.hysteresis_margin = 5.0  # 5% margin for state changes
        
        # Feature priorities (higher number = more important)
        self.feature_priorities = {
            "token_scoring": 10,  # Most important
            "metrics_collection": 8,
            "performance_tracking": 6,
            "health_monitoring": 9,
            "alert_processing": 7,
            "api_caching": 4,
            "detailed_logging": 3,
            "background_cleanup": 2,
            "statistics_calculation": 1  # Least important
        }
        
        self.log.info("LoadBasedProcessor initialized")
    
    def assess_system_load(self) -> Dict[str, float]:
        """Assess current system load metrics."""
        try:
            # Get CPU usage (non-blocking)
            cpu_percent = psutil.cpu_percent(interval=0)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage for main partition
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Skip expensive net_connections() call - use cached value or estimate
            connections = getattr(self, '_cached_connections', 50)  # Use reasonable default
            
            # Calculate load score (weighted average)
            load_score = (cpu_percent * 0.4 + memory_percent * 0.4 + 
                         min(disk_percent, 100) * 0.1 + min(connections / 100, 100) * 0.1)
            
            load_metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "connections": connections,
                "load_score": load_score,
                "timestamp": time.time()
            }
            
            # Add to history
            self.load_history.append(load_metrics)
            
            return load_metrics
            
        except Exception as e:
            self.log.error(f"Error assessing system load: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "connections": 0,
                "load_score": 0,
                "timestamp": time.time()
            }
    
    def determine_load_level(self, load_metrics: Dict[str, float]) -> str:
        """Determine appropriate load level based on metrics."""
        cpu_percent = load_metrics["cpu_percent"]
        memory_percent = load_metrics["memory_percent"]
        
        # Check for critical load
        if (cpu_percent >= self.cpu_threshold_critical or 
            memory_percent >= self.memory_threshold_critical):
            return "minimal"
        
        # Check for warning load
        if (cpu_percent >= self.cpu_threshold_warning or 
            memory_percent >= self.memory_threshold_warning):
            return "reduced"
        
        return "normal"
    
    def should_change_load_level(self, new_level: str) -> bool:
        """Determine if load level should change, considering hysteresis."""
        if new_level == self.current_load_level:
            return False
        
        # Get recent load metrics for trend analysis
        if len(self.load_history) < 3:
            return True  # Not enough history, allow change
        
        recent_metrics = list(self.load_history)[-3:]
        
        # Check if the trend is consistent
        if new_level == "minimal":
            # Moving to minimal - check if consistently high
            high_load_count = sum(1 for m in recent_metrics 
                                if m["cpu_percent"] >= self.cpu_threshold_critical - self.hysteresis_margin
                                or m["memory_percent"] >= self.memory_threshold_critical - self.hysteresis_margin)
            return high_load_count >= 2
        
        elif new_level == "reduced":
            if self.current_load_level == "minimal":
                # Moving from minimal to reduced - check if load decreased
                avg_cpu = sum(m["cpu_percent"] for m in recent_metrics) / len(recent_metrics)
                avg_memory = sum(m["memory_percent"] for m in recent_metrics) / len(recent_metrics)
                return (avg_cpu < self.cpu_threshold_critical - self.hysteresis_margin and
                       avg_memory < self.memory_threshold_critical - self.hysteresis_margin)
            else:
                # Moving from normal to reduced - check if consistently elevated
                elevated_count = sum(1 for m in recent_metrics 
                                   if m["cpu_percent"] >= self.cpu_threshold_warning - self.hysteresis_margin
                                   or m["memory_percent"] >= self.memory_threshold_warning - self.hysteresis_margin)
                return elevated_count >= 2
        
        elif new_level == "normal":
            # Moving to normal - check if load consistently decreased
            avg_cpu = sum(m["cpu_percent"] for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m["memory_percent"] for m in recent_metrics) / len(recent_metrics)
            return (avg_cpu < self.cpu_threshold_warning - self.hysteresis_margin and
                   avg_memory < self.memory_threshold_warning - self.hysteresis_margin)
        
        return True
    
    def adjust_processing_parameters(self, load_level: str) -> Dict[str, Any]:
        """Adjust processing parameters based on load level."""
        previous_level = self.current_load_level
        previous_factor = self.current_processing_factor
        
        self.current_load_level = load_level
        
        # Set processing factor
        if load_level == "minimal":
            self.current_processing_factor = self.minimal_processing_factor
        elif load_level == "reduced":
            self.current_processing_factor = self.reduced_processing_factor
        else:
            self.current_processing_factor = self.normal_processing_factor
        
        # Adjust feature availability
        self._adjust_features(load_level)
        
        adjustments = {
            "previous_level": previous_level,
            "new_level": load_level,
            "previous_factor": previous_factor,
            "new_factor": self.current_processing_factor,
            "disabled_features": list(self.disabled_features),
            "timestamp": time.time()
        }
        
        if previous_level != load_level:
            self.log.info(
                "load_level_changed",
                extra={
                    "extra": {
                        "previous_level": previous_level,
                        "new_level": load_level,
                        "processing_factor": self.current_processing_factor,
                        "disabled_features": list(self.disabled_features)
                    }
                }
            )
        
        return adjustments
    
    def _adjust_features(self, load_level: str):
        """Adjust feature availability based on load level."""
        if load_level == "minimal":
            # Disable non-essential features
            features_to_disable = [
                feature for feature, priority in self.feature_priorities.items()
                if priority <= 5  # Disable features with priority 5 or lower
            ]
            self.disabled_features.update(features_to_disable)
            
        elif load_level == "reduced":
            # Disable only least important features
            features_to_disable = [
                feature for feature, priority in self.feature_priorities.items()
                if priority <= 3  # Disable features with priority 3 or lower
            ]
            self.disabled_features.update(features_to_disable)
            
        else:  # normal
            # Enable all features
            self.disabled_features.clear()
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is currently enabled."""
        return feature_name not in self.disabled_features
    
    def get_processing_factor(self) -> float:
        """Get current processing factor."""
        return self.current_processing_factor
    
    def get_adjusted_interval(self, base_interval: float) -> float:
        """Get adjusted interval based on current processing factor."""
        if self.current_processing_factor >= 1.0:
            return base_interval
        
        # Increase interval when processing factor is reduced
        return base_interval / self.current_processing_factor
    
    def get_adjusted_batch_size(self, base_batch_size: int) -> int:
        """Get adjusted batch size based on current processing factor."""
        adjusted_size = int(base_batch_size * self.current_processing_factor)
        return max(1, adjusted_size)  # Ensure at least 1
    
    def should_skip_processing(self, feature_name: str) -> bool:
        """Check if processing should be skipped for a feature."""
        return not self.is_feature_enabled(feature_name)
    
    def process_load_adjustment(self) -> Dict[str, Any]:
        """Main method to assess load and adjust processing."""
        try:
            # Assess current system load
            load_metrics = self.assess_system_load()
            
            # Determine appropriate load level
            new_load_level = self.determine_load_level(load_metrics)
            
            # Check if we should change load level (with hysteresis)
            if self.should_change_load_level(new_load_level):
                adjustments = self.adjust_processing_parameters(new_load_level)
            else:
                adjustments = {
                    "previous_level": self.current_load_level,
                    "new_level": self.current_load_level,
                    "previous_factor": self.current_processing_factor,
                    "new_factor": self.current_processing_factor,
                    "disabled_features": list(self.disabled_features),
                    "timestamp": time.time(),
                    "no_change": True
                }
            
            # Add load metrics to response
            adjustments["load_metrics"] = load_metrics
            
            return adjustments
            
        except Exception as e:
            self.log.error(f"Error processing load adjustment: {e}")
            return {
                "error": str(e),
                "current_level": self.current_load_level,
                "current_factor": self.current_processing_factor,
                "timestamp": time.time()
            }
    
    def get_load_statistics(self) -> Dict[str, Any]:
        """Get load statistics and current state."""
        if not self.load_history:
            return {"error": "No load history available"}
        
        recent_metrics = list(self.load_history)
        
        # Calculate averages
        avg_cpu = sum(m["cpu_percent"] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m["memory_percent"] for m in recent_metrics) / len(recent_metrics)
        avg_load_score = sum(m["load_score"] for m in recent_metrics) / len(recent_metrics)
        
        # Calculate peaks
        max_cpu = max(m["cpu_percent"] for m in recent_metrics)
        max_memory = max(m["memory_percent"] for m in recent_metrics)
        max_load_score = max(m["load_score"] for m in recent_metrics)
        
        # Calculate load level distribution
        level_counts = {"normal": 0, "reduced": 0, "minimal": 0}
        for metrics in recent_metrics:
            level = self.determine_load_level(metrics)
            level_counts[level] += 1
        
        return {
            "current_state": {
                "load_level": self.current_load_level,
                "processing_factor": self.current_processing_factor,
                "disabled_features": list(self.disabled_features),
                "enabled_features": [f for f in self.feature_priorities.keys() 
                                   if f not in self.disabled_features]
            },
            "load_averages": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "load_score": avg_load_score
            },
            "load_peaks": {
                "cpu_percent": max_cpu,
                "memory_percent": max_memory,
                "load_score": max_load_score
            },
            "load_distribution": level_counts,
            "thresholds": {
                "cpu_warning": self.cpu_threshold_warning,
                "cpu_critical": self.cpu_threshold_critical,
                "memory_warning": self.memory_threshold_warning,
                "memory_critical": self.memory_threshold_critical
            },
            "history_size": len(recent_metrics),
            "timestamp": time.time()
        }
    
    def update_thresholds(self, cpu_warning: float = None, cpu_critical: float = None,
                         memory_warning: float = None, memory_critical: float = None):
        """Update load thresholds."""
        if cpu_warning is not None:
            self.cpu_threshold_warning = cpu_warning
        if cpu_critical is not None:
            self.cpu_threshold_critical = cpu_critical
        if memory_warning is not None:
            self.memory_threshold_warning = memory_warning
        if memory_critical is not None:
            self.memory_threshold_critical = memory_critical
        
        self.log.info(
            "load_thresholds_updated",
            extra={
                "extra": {
                    "cpu_warning": self.cpu_threshold_warning,
                    "cpu_critical": self.cpu_threshold_critical,
                    "memory_warning": self.memory_threshold_warning,
                    "memory_critical": self.memory_threshold_critical
                }
            }
        )


    def get_current_load(self) -> Dict[str, float]:
        """Get current system load metrics."""
        return self.assess_system_load()


# Global load-based processor instance
load_processor = LoadBasedProcessor()


def get_load_processor() -> LoadBasedProcessor:
    """Get the global load-based processor instance."""
    return load_processor

class PerformanceOptimizer:
    """
    Automatic performance optimization system.
    
    Monitors system performance and automatically adjusts processing
    parameters to maintain optimal performance under varying loads.
    """
    
    def __init__(self):
        import threading
        import time
        
        # Avoid circular import - initialize logger later
        self.logger = None
        self.performance_tracker = get_performance_tracker()
        self.load_processor = get_load_processor()
        
        # Optimization parameters
        self.batch_sizes = {}
        self.parallelism_levels = {}
        self.memory_thresholds = {}
        
        # Performance history for trend analysis
        self.performance_history = {}
        self.optimization_history = {}
        
        # Optimization settings
        self.min_batch_size = 10
        self.max_batch_size = 1000
        self.default_batch_size = 100
        
        self.min_parallelism = 1
        self.max_parallelism = 10
        self.default_parallelism = 3
        
        # Thresholds for optimization triggers
        self.cpu_threshold_high = 80.0
        self.cpu_threshold_low = 40.0
        self.memory_threshold_high = 85.0
        self.memory_threshold_low = 60.0
        self.response_time_threshold = 5.0  # seconds
        
        # Optimization intervals
        self.optimization_interval = 60  # seconds
        self.last_optimization = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize default settings
        self._initialize_defaults()
    
    def _initialize_logger(self):
        """Initialize logger to avoid circular imports."""
        if self.logger is None:
            self.logger = get_structured_logger("performance_optimizer")
    
    def _initialize_defaults(self):
        """Initialize default optimization parameters."""
        default_services = ["scheduler", "dexscreener", "database", "api_processing"]
        
        for service in default_services:
            self.batch_sizes[service] = self.default_batch_size
            self.parallelism_levels[service] = self.default_parallelism
            self.memory_thresholds[service] = self.memory_threshold_high
            self.performance_history[service] = []
            self.optimization_history[service] = []
            self.last_optimization[service] = 0
    
    def should_optimize(self, service: str) -> bool:
        """Check if optimization should be performed for a service."""
        import time
        
        current_time = time.time()
        last_opt = self.last_optimization.get(service, 0)
        
        # Don't optimize too frequently
        if current_time - last_opt < self.optimization_interval:
            return False
        
        # Check if performance metrics indicate need for optimization
        recent_metrics = self._get_recent_performance_metrics(service)
        if not recent_metrics:
            return False
        
        # Check for performance degradation
        avg_response_time = sum(m.get("response_time", 0) for m in recent_metrics) / len(recent_metrics)
        avg_cpu_usage = sum(m.get("cpu_usage", 0) for m in recent_metrics) / len(recent_metrics)
        avg_memory_usage = sum(m.get("memory_usage", 0) for m in recent_metrics) / len(recent_metrics)
        
        needs_optimization = (
            avg_response_time > self.response_time_threshold or
            avg_cpu_usage > self.cpu_threshold_high or
            avg_memory_usage > self.memory_threshold_high
        )
        
        if needs_optimization:
            self._initialize_logger()
            self.logger.info(
                f"Optimization needed for {service}",
                service=service,
                avg_response_time=avg_response_time,
                avg_cpu_usage=avg_cpu_usage,
                avg_memory_usage=avg_memory_usage
            )
        
        return needs_optimization
    
    def _get_recent_performance_metrics(self, service: str, minutes: int = 5) -> List[Dict]:
        """Get recent performance metrics for a service."""
        import time
        
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = []
        
        for metric in self.performance_history.get(service, []):
            if metric.get("timestamp", 0) > cutoff_time:
                recent_metrics.append(metric)
        
        return recent_metrics[-20:]  # Last 20 metrics
    
    def optimize_batch_size(self, service: str, current_performance: Dict[str, float]) -> int:
        """Optimize batch size based on current performance."""
        current_batch_size = self.batch_sizes.get(service, self.default_batch_size)
        
        cpu_usage = current_performance.get("cpu_usage", 0)
        memory_usage = current_performance.get("memory_usage", 0)
        response_time = current_performance.get("response_time", 0)
        throughput = current_performance.get("throughput", 0)
        
        new_batch_size = current_batch_size
        
        # Reduce batch size if system is under stress
        if cpu_usage > self.cpu_threshold_high or memory_usage > self.memory_threshold_high:
            reduction_factor = 0.8
            new_batch_size = max(self.min_batch_size, int(current_batch_size * reduction_factor))
            
        # Reduce batch size if response time is too high
        elif response_time > self.response_time_threshold:
            reduction_factor = 0.7
            new_batch_size = max(self.min_batch_size, int(current_batch_size * reduction_factor))
            
        # Increase batch size if system has capacity and performance is good
        elif (cpu_usage < self.cpu_threshold_low and 
              memory_usage < self.memory_threshold_low and 
              response_time < self.response_time_threshold * 0.5):
            increase_factor = 1.2
            new_batch_size = min(self.max_batch_size, int(current_batch_size * increase_factor))
        
        # Don't make drastic changes
        max_change = max(10, current_batch_size * 0.3)
        if abs(new_batch_size - current_batch_size) > max_change:
            if new_batch_size > current_batch_size:
                new_batch_size = current_batch_size + int(max_change)
            else:
                new_batch_size = current_batch_size - int(max_change)
        
        self.batch_sizes[service] = new_batch_size
        
        if new_batch_size != current_batch_size:
            self.logger.info(
                f"Batch size optimized for {service}",
                service=service,
                old_batch_size=current_batch_size,
                new_batch_size=new_batch_size,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                response_time=response_time
            )
        
        return new_batch_size
    
    def optimize_parallelism(self, service: str, current_performance: Dict[str, float]) -> int:
        """Optimize parallelism level based on current performance."""
        current_parallelism = self.parallelism_levels.get(service, self.default_parallelism)
        
        cpu_usage = current_performance.get("cpu_usage", 0)
        memory_usage = current_performance.get("memory_usage", 0)
        queue_length = current_performance.get("queue_length", 0)
        
        new_parallelism = current_parallelism
        
        # Reduce parallelism if system is under stress
        if cpu_usage > self.cpu_threshold_high or memory_usage > self.memory_threshold_high:
            new_parallelism = max(self.min_parallelism, current_parallelism - 1)
            
        # Increase parallelism if system has capacity and there's a queue
        elif (cpu_usage < self.cpu_threshold_low and 
              memory_usage < self.memory_threshold_low and 
              queue_length > 0):
            new_parallelism = min(self.max_parallelism, current_parallelism + 1)
        
        self.parallelism_levels[service] = new_parallelism
        
        if new_parallelism != current_parallelism:
            self.logger.info(
                f"Parallelism optimized for {service}",
                service=service,
                old_parallelism=current_parallelism,
                new_parallelism=new_parallelism,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                queue_length=queue_length
            )
        
        return new_parallelism
    
    def perform_memory_cleanup(self, service: str, current_performance: Dict[str, float]):
        """Perform memory cleanup when usage is high."""
        memory_usage = current_performance.get("memory_usage", 0)
        
        if memory_usage > self.memory_threshold_high:
            import gc
            
            self.logger.info(
                f"Performing memory cleanup for {service}",
                service=service,
                memory_usage=memory_usage
            )
            
            # Force garbage collection
            collected = gc.collect()
            
            # Clear old performance history
            self._cleanup_old_metrics(service)
            
            self.logger.info(
                f"Memory cleanup completed for {service}",
                service=service,
                objects_collected=collected,
                memory_usage_before=memory_usage
            )
    
    def _cleanup_old_metrics(self, service: str, keep_hours: int = 24):
        """Clean up old performance metrics to free memory."""
        import time
        
        cutoff_time = time.time() - (keep_hours * 3600)
        
        # Clean performance history
        if service in self.performance_history:
            old_count = len(self.performance_history[service])
            self.performance_history[service] = [
                m for m in self.performance_history[service] 
                if m.get("timestamp", 0) > cutoff_time
            ]
            new_count = len(self.performance_history[service])
            
            if old_count > new_count:
                self.logger.debug(
                    f"Cleaned up old performance metrics for {service}",
                    service=service,
                    removed_metrics=old_count - new_count
                )
        
        # Clean optimization history
        if service in self.optimization_history:
            old_count = len(self.optimization_history[service])
            self.optimization_history[service] = [
                m for m in self.optimization_history[service] 
                if m.get("timestamp", 0) > cutoff_time
            ]
            new_count = len(self.optimization_history[service])
            
            if old_count > new_count:
                self.logger.debug(
                    f"Cleaned up old optimization history for {service}",
                    service=service,
                    removed_entries=old_count - new_count
                )
    
    def optimize_service(self, service: str) -> Dict[str, Any]:
        """Perform comprehensive optimization for a service."""
        import time
        
        with self._lock:
            if not self.should_optimize(service):
                return {"optimized": False, "reason": "optimization_not_needed"}
            
            # Get current performance metrics
            current_performance = self._get_current_performance(service)
            
            optimization_result = {
                "service": service,
                "timestamp": time.time(),
                "optimized": True,
                "changes": {}
            }
            
            # Optimize batch size
            old_batch_size = self.batch_sizes.get(service, self.default_batch_size)
            new_batch_size = self.optimize_batch_size(service, current_performance)
            if new_batch_size != old_batch_size:
                optimization_result["changes"]["batch_size"] = {
                    "old": old_batch_size,
                    "new": new_batch_size
                }
            
            # Optimize parallelism
            old_parallelism = self.parallelism_levels.get(service, self.default_parallelism)
            new_parallelism = self.optimize_parallelism(service, current_performance)
            if new_parallelism != old_parallelism:
                optimization_result["changes"]["parallelism"] = {
                    "old": old_parallelism,
                    "new": new_parallelism
                }
            
            # Perform memory cleanup if needed
            memory_usage = current_performance.get("memory_usage", 0)
            if memory_usage > self.memory_threshold_high:
                self.perform_memory_cleanup(service, current_performance)
                optimization_result["changes"]["memory_cleanup"] = True
            
            # Record optimization
            self.last_optimization[service] = time.time()
            self.optimization_history[service].append(optimization_result)
            
            # Keep only recent optimization history
            if len(self.optimization_history[service]) > 100:
                self.optimization_history[service] = self.optimization_history[service][-50:]
            
            self.logger.info(
                f"Service optimization completed: {service}",
                service=service,
                changes=optimization_result["changes"],
                performance_metrics=current_performance
            )
            
            return optimization_result
    
    def _get_current_performance(self, service: str) -> Dict[str, float]:
        """Get current performance metrics for a service."""
        # Get system metrics
        system_metrics = self.load_processor.get_current_load()
        
        # Get service-specific metrics from performance tracker
        service_stats = self.performance_tracker.get_service_statistics(service)
        
        return {
            "cpu_usage": system_metrics.get("cpu_percent", 0),
            "memory_usage": system_metrics.get("memory_percent", 0),
            "response_time": service_stats.get("avg_response_time", 0),
            "throughput": service_stats.get("requests_per_minute", 0),
            "error_rate": service_stats.get("error_rate", 0),
            "queue_length": service_stats.get("queue_length", 0)
        }
    
    def get_optimization_recommendations(self, service: str) -> List[Dict[str, Any]]:
        """Get optimization recommendations for a service."""
        current_performance = self._get_current_performance(service)
        recommendations = []
        
        cpu_usage = current_performance.get("cpu_usage", 0)
        memory_usage = current_performance.get("memory_usage", 0)
        response_time = current_performance.get("response_time", 0)
        error_rate = current_performance.get("error_rate", 0)
        
        # CPU recommendations
        if cpu_usage > self.cpu_threshold_high:
            recommendations.append({
                "type": "cpu_optimization",
                "priority": "high",
                "description": "High CPU usage detected",
                "suggested_actions": [
                    "Reduce batch size",
                    "Decrease parallelism",
                    "Enable load-based processing reduction"
                ],
                "current_value": cpu_usage,
                "threshold": self.cpu_threshold_high
            })
        
        # Memory recommendations
        if memory_usage > self.memory_threshold_high:
            recommendations.append({
                "type": "memory_optimization",
                "priority": "high",
                "description": "High memory usage detected",
                "suggested_actions": [
                    "Perform memory cleanup",
                    "Reduce batch size",
                    "Clear old cached data"
                ],
                "current_value": memory_usage,
                "threshold": self.memory_threshold_high
            })
        
        # Response time recommendations
        if response_time > self.response_time_threshold:
            recommendations.append({
                "type": "response_time_optimization",
                "priority": "medium",
                "description": "High response time detected",
                "suggested_actions": [
                    "Reduce batch size",
                    "Optimize database queries",
                    "Enable caching"
                ],
                "current_value": response_time,
                "threshold": self.response_time_threshold
            })
        
        # Error rate recommendations
        if error_rate > 0.05:  # 5% error rate
            recommendations.append({
                "type": "error_rate_optimization",
                "priority": "high",
                "description": "High error rate detected",
                "suggested_actions": [
                    "Enable circuit breaker",
                    "Increase retry delays",
                    "Check external service health"
                ],
                "current_value": error_rate,
                "threshold": 0.05
            })
        
        return recommendations
    
    def get_current_settings(self, service: str) -> Dict[str, Any]:
        """Get current optimization settings for a service."""
        return {
            "service": service,
            "batch_size": self.batch_sizes.get(service, self.default_batch_size),
            "parallelism": self.parallelism_levels.get(service, self.default_parallelism),
            "memory_threshold": self.memory_thresholds.get(service, self.memory_threshold_high),
            "last_optimization": self.last_optimization.get(service, 0),
            "optimization_count": len(self.optimization_history.get(service, []))
        }
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get overall optimization statistics."""
        import time
        
        total_optimizations = sum(len(history) for history in self.optimization_history.values())
        
        recent_optimizations = 0
        cutoff_time = time.time() - 3600  # Last hour
        
        for service_history in self.optimization_history.values():
            recent_optimizations += sum(
                1 for opt in service_history 
                if opt.get("timestamp", 0) > cutoff_time
            )
        
        return {
            "total_services": len(self.batch_sizes),
            "total_optimizations": total_optimizations,
            "recent_optimizations": recent_optimizations,
            "services_with_recent_optimization": len([
                service for service, last_opt in self.last_optimization.items()
                if last_opt > cutoff_time
            ]),
            "average_batch_size": sum(self.batch_sizes.values()) / len(self.batch_sizes) if self.batch_sizes else 0,
            "average_parallelism": sum(self.parallelism_levels.values()) / len(self.parallelism_levels) if self.parallelism_levels else 0
        }


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    return performance_optimizer


class PerformanceDegradationDetector:
    """
    Performance degradation detection system.
    
    Monitors performance trends and provides predictive alerting
    for potential performance issues before they become critical.
    """
    
    def __init__(self):
        import threading
        import time
        from collections import deque
        
        # Avoid circular import - initialize logger later
        self.logger = None
        self.performance_tracker = get_performance_tracker()
        # Avoid circular import - initialize alert manager later
        self.alert_manager = None
        
        # Performance history storage
        self.performance_windows = {}  # service -> deque of metrics
        self.trend_analysis = {}       # service -> trend data
        self.degradation_alerts = {}   # service -> alert history
        
        # Configuration
        self.window_size = 50          # Number of metrics to keep for trend analysis
        self.trend_window_minutes = 30 # Minutes to look back for trend analysis
        self.alert_cooldown = 300      # 5 minutes between similar alerts
        
        # Degradation thresholds
        self.response_time_degradation_threshold = 0.3  # 30% increase
        self.throughput_degradation_threshold = 0.2     # 20% decrease
        self.error_rate_degradation_threshold = 0.1     # 10% increase
        self.cpu_degradation_threshold = 0.25           # 25% increase
        self.memory_degradation_threshold = 0.2         # 20% increase
        
        # Trend detection parameters
        self.min_data_points = 10      # Minimum points needed for trend analysis
        self.trend_significance = 0.05 # Statistical significance level
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize default services
        self._initialize_services()
    
    def _initialize_logger(self):
        """Initialize logger to avoid circular imports."""
        if self.logger is None:
            self.logger = get_structured_logger("performance_degradation_detector")
    
    def _initialize_alert_manager(self):
        """Initialize alert manager to avoid circular imports."""
        if self.alert_manager is None:
            from .alert_manager import get_alert_manager
            self.alert_manager = get_alert_manager()
    
    def _initialize_services(self):
        """Initialize performance tracking for default services."""
        default_services = ["scheduler", "dexscreener", "database", "api_processing"]
        
        for service in default_services:
            self.performance_windows[service] = deque(maxlen=self.window_size)
            self.trend_analysis[service] = {}
            self.degradation_alerts[service] = {}
    
    def record_performance_metric(self, service: str, metrics: Dict[str, float]):
        """Record a performance metric for trend analysis."""
        import time
        
        with self._lock:
            if service not in self.performance_windows:
                self.performance_windows[service] = deque(maxlen=self.window_size)
                self.trend_analysis[service] = {}
                self.degradation_alerts[service] = {}
            
            # Add timestamp to metrics
            timestamped_metrics = {
                **metrics,
                "timestamp": time.time()
            }
            
            self.performance_windows[service].append(timestamped_metrics)
            
            # Perform degradation analysis if we have enough data
            if len(self.performance_windows[service]) >= self.min_data_points:
                self._analyze_performance_trends(service)
    
    def _analyze_performance_trends(self, service: str):
        """Analyze performance trends for a service."""
        import time
        import statistics
        
        current_time = time.time()
        cutoff_time = current_time - (self.trend_window_minutes * 60)
        
        # Get recent metrics within the trend window
        recent_metrics = [
            m for m in self.performance_windows[service]
            if m.get("timestamp", 0) > cutoff_time
        ]
        
        if len(recent_metrics) < self.min_data_points:
            return
        
        # Calculate trends for key metrics
        trends = {}
        
        # Response time trend
        response_times = [m.get("response_time", 0) for m in recent_metrics if m.get("response_time") is not None]
        if len(response_times) >= self.min_data_points:
            trends["response_time"] = self._calculate_trend(response_times)
        
        # Throughput trend
        throughputs = [m.get("throughput", 0) for m in recent_metrics if m.get("throughput") is not None]
        if len(throughputs) >= self.min_data_points:
            trends["throughput"] = self._calculate_trend(throughputs)
        
        # Error rate trend
        error_rates = [m.get("error_rate", 0) for m in recent_metrics if m.get("error_rate") is not None]
        if len(error_rates) >= self.min_data_points:
            trends["error_rate"] = self._calculate_trend(error_rates)
        
        # CPU usage trend
        cpu_usages = [m.get("cpu_usage", 0) for m in recent_metrics if m.get("cpu_usage") is not None]
        if len(cpu_usages) >= self.min_data_points:
            trends["cpu_usage"] = self._calculate_trend(cpu_usages)
        
        # Memory usage trend
        memory_usages = [m.get("memory_usage", 0) for m in recent_metrics if m.get("memory_usage") is not None]
        if len(memory_usages) >= self.min_data_points:
            trends["memory_usage"] = self._calculate_trend(memory_usages)
        
        # Store trend analysis
        self.trend_analysis[service] = {
            "timestamp": current_time,
            "trends": trends,
            "data_points": len(recent_metrics),
            "window_minutes": self.trend_window_minutes
        }
        
        # Check for degradation patterns
        self._check_degradation_patterns(service, trends, recent_metrics)
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, float]:
        """Calculate trend statistics for a series of values."""
        import statistics
        
        if len(values) < 2:
            return {"slope": 0, "correlation": 0, "recent_avg": 0, "baseline_avg": 0}
        
        # Simple linear regression to calculate slope
        n = len(values)
        x_values = list(range(n))
        
        # Calculate means
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        # Calculate slope and correlation
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        x_variance = sum((x - x_mean) ** 2 for x in x_values)
        y_variance = sum((y - y_mean) ** 2 for y in values)
        
        slope = numerator / x_variance if x_variance != 0 else 0
        
        correlation = 0
        if x_variance != 0 and y_variance != 0:
            correlation = numerator / (x_variance * y_variance) ** 0.5
        
        # Calculate recent vs baseline averages
        split_point = max(1, n // 3)
        baseline_avg = statistics.mean(values[:split_point])
        recent_avg = statistics.mean(values[-split_point:])
        
        return {
            "slope": slope,
            "correlation": correlation,
            "recent_avg": recent_avg,
            "baseline_avg": baseline_avg,
            "change_percent": ((recent_avg - baseline_avg) / baseline_avg * 100) if baseline_avg != 0 else 0
        }
    
    def _check_degradation_patterns(self, service: str, trends: Dict, recent_metrics: List[Dict]):
        """Check for performance degradation patterns."""
        import time
        
        current_time = time.time()
        degradations_detected = []
        
        # Check response time degradation
        if "response_time" in trends:
            rt_trend = trends["response_time"]
            if (rt_trend["change_percent"] > self.response_time_degradation_threshold * 100 and
                rt_trend["correlation"] > 0.5):  # Strong positive correlation
                degradations_detected.append({
                    "type": "response_time_degradation",
                    "severity": "warning" if rt_trend["change_percent"] < 50 else "error",
                    "change_percent": rt_trend["change_percent"],
                    "correlation": rt_trend["correlation"],
                    "current_avg": rt_trend["recent_avg"],
                    "baseline_avg": rt_trend["baseline_avg"]
                })
        
        # Check throughput degradation
        if "throughput" in trends:
            tp_trend = trends["throughput"]
            if (tp_trend["change_percent"] < -self.throughput_degradation_threshold * 100 and
                tp_trend["correlation"] < -0.5):  # Strong negative correlation
                degradations_detected.append({
                    "type": "throughput_degradation",
                    "severity": "warning" if abs(tp_trend["change_percent"]) < 30 else "error",
                    "change_percent": tp_trend["change_percent"],
                    "correlation": tp_trend["correlation"],
                    "current_avg": tp_trend["recent_avg"],
                    "baseline_avg": tp_trend["baseline_avg"]
                })
        
        # Check error rate degradation
        if "error_rate" in trends:
            er_trend = trends["error_rate"]
            if (er_trend["change_percent"] > self.error_rate_degradation_threshold * 100 and
                er_trend["correlation"] > 0.3):
                degradations_detected.append({
                    "type": "error_rate_degradation",
                    "severity": "error" if er_trend["recent_avg"] > 0.1 else "warning",
                    "change_percent": er_trend["change_percent"],
                    "correlation": er_trend["correlation"],
                    "current_avg": er_trend["recent_avg"],
                    "baseline_avg": er_trend["baseline_avg"]
                })
        
        # Check CPU usage degradation
        if "cpu_usage" in trends:
            cpu_trend = trends["cpu_usage"]
            if (cpu_trend["change_percent"] > self.cpu_degradation_threshold * 100 and
                cpu_trend["correlation"] > 0.4):
                degradations_detected.append({
                    "type": "cpu_usage_degradation",
                    "severity": "warning" if cpu_trend["recent_avg"] < 80 else "error",
                    "change_percent": cpu_trend["change_percent"],
                    "correlation": cpu_trend["correlation"],
                    "current_avg": cpu_trend["recent_avg"],
                    "baseline_avg": cpu_trend["baseline_avg"]
                })
        
        # Check memory usage degradation
        if "memory_usage" in trends:
            mem_trend = trends["memory_usage"]
            if (mem_trend["change_percent"] > self.memory_degradation_threshold * 100 and
                mem_trend["correlation"] > 0.4):
                degradations_detected.append({
                    "type": "memory_usage_degradation",
                    "severity": "warning" if mem_trend["recent_avg"] < 85 else "error",
                    "change_percent": mem_trend["change_percent"],
                    "correlation": mem_trend["correlation"],
                    "current_avg": mem_trend["recent_avg"],
                    "baseline_avg": mem_trend["baseline_avg"]
                })
        
        # Send alerts for detected degradations
        for degradation in degradations_detected:
            self._send_degradation_alert(service, degradation, current_time)
        
        # Record metrics for intelligent alerting
        try:
            from src.monitoring.alert_manager import get_intelligent_alerting_engine
            intelligent_engine = get_intelligent_alerting_engine()
            
            # Record current performance metrics for intelligent alerting
            for metric_name, trend in trends.items():
                current_value = trend.get("recent_avg", 0)
                intelligent_engine.record_metric(service, metric_name, current_value, current_time)
                
        except Exception as e:
            # Initialize logger if not already done
            self._initialize_logger()
            if self.logger:
                self.logger.error(
                    f"Failed to record metrics for intelligent alerting: {service}",
                    extra={"service": service, "error": str(e)}
                )
    
    def _send_degradation_alert(self, service: str, degradation: Dict, current_time: float):
        """Send alert for detected performance degradation."""
        alert_key = f"{service}_{degradation['type']}"
        
        # Check alert cooldown
        last_alert_time = self.degradation_alerts[service].get(alert_key, 0)
        if current_time - last_alert_time < self.alert_cooldown:
            return
        
        # Create alert message
        alert_message = (
            f"Performance degradation detected in {service}: "
            f"{degradation['type'].replace('_', ' ').title()}"
        )
        
        alert_details = {
            "service": service,
            "degradation_type": degradation["type"],
            "change_percent": round(degradation["change_percent"], 2),
            "correlation": round(degradation["correlation"], 3),
            "current_value": round(degradation["current_avg"], 3),
            "baseline_value": round(degradation["baseline_avg"], 3),
            "trend_strength": "strong" if abs(degradation["correlation"]) > 0.7 else "moderate"
        }
        
        # Send alert through alert manager
        try:
            self._initialize_alert_manager()
            if degradation["severity"] == "error":
                self.alert_manager.send_alert(
                    "ERROR",
                    alert_message,
                    **alert_details
                )
            else:
                self.alert_manager.send_alert(
                    "WARNING",
                    alert_message,
                    **alert_details
                )
            
            # Record alert time
            self.degradation_alerts[service][alert_key] = current_time
            
            self.logger.warning(
                f"Performance degradation alert sent: {service}",
                service=service,
                degradation_type=degradation["type"],
                severity=degradation["severity"],
                **alert_details
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to send degradation alert for {service}",
                service=service,
                error=e,
                degradation_type=degradation["type"]
            )
    
    def get_performance_health_status(self, service: str) -> Dict[str, Any]:
        """Get current performance health status for a service."""
        import time
        
        if service not in self.trend_analysis:
            return {
                "service": service,
                "status": "unknown",
                "message": "No performance data available"
            }
        
        trend_data = self.trend_analysis[service]
        trends = trend_data.get("trends", {})
        
        # Determine overall health status
        warning_count = 0
        error_count = 0
        
        for metric_name, trend in trends.items():
            change_percent = abs(trend.get("change_percent", 0))
            correlation = abs(trend.get("correlation", 0))
            
            # Check if this metric shows concerning trends
            if correlation > 0.5 and change_percent > 20:
                if change_percent > 50:
                    error_count += 1
                else:
                    warning_count += 1
        
        if error_count > 0:
            status = "critical"
            message = f"Severe performance degradation detected in {error_count} metrics"
        elif warning_count > 0:
            status = "degraded"
            message = f"Performance degradation detected in {warning_count} metrics"
        else:
            status = "healthy"
            message = "Performance trends are stable"
        
        return {
            "service": service,
            "status": status,
            "message": message,
            "trends": trends,
            "data_points": trend_data.get("data_points", 0),
            "last_analysis": trend_data.get("timestamp", 0),
            "warning_metrics": warning_count,
            "error_metrics": error_count
        }
    
    def get_predictive_alerts(self, service: str, forecast_minutes: int = 30) -> List[Dict[str, Any]]:
        """Generate predictive alerts based on current trends."""
        if service not in self.trend_analysis:
            return []
        
        trends = self.trend_analysis[service].get("trends", {})
        predictive_alerts = []
        
        for metric_name, trend in trends.items():
            slope = trend.get("slope", 0)
            correlation = trend.get("correlation", 0)
            current_avg = trend.get("recent_avg", 0)
            
            # Only predict if we have a strong trend
            if abs(correlation) < 0.6:
                continue
            
            # Project future value
            projected_value = current_avg + (slope * forecast_minutes)
            
            # Check if projected value crosses critical thresholds
            alert = None
            
            if metric_name == "response_time" and projected_value > current_avg * 1.5:
                alert = {
                    "type": "predictive_response_time_alert",
                    "metric": metric_name,
                    "current_value": current_avg,
                    "projected_value": projected_value,
                    "forecast_minutes": forecast_minutes,
                    "confidence": abs(correlation),
                    "severity": "warning",
                    "message": f"Response time may increase by {((projected_value - current_avg) / current_avg * 100):.1f}% in {forecast_minutes} minutes"
                }
            
            elif metric_name == "error_rate" and projected_value > 0.1:  # 10% error rate
                alert = {
                    "type": "predictive_error_rate_alert",
                    "metric": metric_name,
                    "current_value": current_avg,
                    "projected_value": projected_value,
                    "forecast_minutes": forecast_minutes,
                    "confidence": abs(correlation),
                    "severity": "error",
                    "message": f"Error rate may reach {projected_value:.2%} in {forecast_minutes} minutes"
                }
            
            elif metric_name == "cpu_usage" and projected_value > 90:
                alert = {
                    "type": "predictive_cpu_alert",
                    "metric": metric_name,
                    "current_value": current_avg,
                    "projected_value": projected_value,
                    "forecast_minutes": forecast_minutes,
                    "confidence": abs(correlation),
                    "severity": "warning",
                    "message": f"CPU usage may reach {projected_value:.1f}% in {forecast_minutes} minutes"
                }
            
            elif metric_name == "memory_usage" and projected_value > 95:
                alert = {
                    "type": "predictive_memory_alert",
                    "metric": metric_name,
                    "current_value": current_avg,
                    "projected_value": projected_value,
                    "forecast_minutes": forecast_minutes,
                    "confidence": abs(correlation),
                    "severity": "error",
                    "message": f"Memory usage may reach {projected_value:.1f}% in {forecast_minutes} minutes"
                }
            
            if alert:
                predictive_alerts.append(alert)
        
        return predictive_alerts
    
    def get_degradation_statistics(self) -> Dict[str, Any]:
        """Get overall degradation detection statistics."""
        import time
        
        current_time = time.time()
        total_services = len(self.performance_windows)
        services_with_data = sum(1 for window in self.performance_windows.values() if len(window) > 0)
        
        # Count recent alerts
        recent_alerts = 0
        cutoff_time = current_time - 3600  # Last hour
        
        for service_alerts in self.degradation_alerts.values():
            recent_alerts += sum(
                1 for alert_time in service_alerts.values()
                if alert_time > cutoff_time
            )
        
        # Count services with concerning trends
        concerning_services = 0
        for service in self.trend_analysis:
            health_status = self.get_performance_health_status(service)
            if health_status["status"] in ["degraded", "critical"]:
                concerning_services += 1
        
        return {
            "total_services": total_services,
            "services_with_data": services_with_data,
            "services_with_concerning_trends": concerning_services,
            "recent_alerts": recent_alerts,
            "window_size": self.window_size,
            "trend_window_minutes": self.trend_window_minutes,
            "alert_cooldown_seconds": self.alert_cooldown
        }


# Global performance degradation detector instance
performance_degradation_detector = PerformanceDegradationDetector()


def get_performance_degradation_detector() -> PerformanceDegradationDetector:
    """Get the global performance degradation detector instance."""
    return performance_degradation_detector


# Simple structured logger implementation
import logging

class SimpleStructuredLogger:
    """Simple structured logger for compatibility."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set logging context."""
        self.context.update(kwargs)
    
    def log_scheduler_execution(self, **kwargs):
        """Log scheduler execution."""
        self.logger.info(f"Scheduler execution: {kwargs}")
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)


def get_structured_logger(name: str) -> SimpleStructuredLogger:
    """Get a simple structured logger instance."""
    return SimpleStructuredLogger(name)