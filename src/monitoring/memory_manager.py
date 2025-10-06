"""
Intelligent memory management system with dynamic threshold adjustment.

This module provides automatic memory threshold management, garbage collection,
and memory leak detection to prevent false alerts and optimize memory usage.
"""

import gc
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque

from .models import HealthAlert, AlertLevel
from .config import get_monitoring_config_manager

log = logging.getLogger("memory_manager")


@dataclass
class MemoryUsageSnapshot:
    """Snapshot of memory usage at a specific time."""
    timestamp: datetime
    used_mb: float
    available_mb: float
    total_mb: float
    percent_used: float
    process_memory_mb: float


@dataclass
class MemoryOptimizationResult:
    """Result of memory optimization operation."""
    before_mb: float
    after_mb: float
    recovered_mb: float
    actions_taken: List[str]
    success: bool
    timestamp: datetime


class IntelligentMemoryManager:
    """
    Intelligent memory management with dynamic threshold adjustment.
    
    Features:
    - Dynamic threshold adjustment based on system capacity
    - Automatic garbage collection before alerting
    - Memory leak detection and targeted cleanup
    - Memory usage pattern analysis
    """
    
    def __init__(self):
        self.config_manager = get_monitoring_config_manager()
        
        # Memory usage history for pattern analysis
        self.usage_history: deque = deque(maxlen=100)
        self.optimization_history: List[MemoryOptimizationResult] = []
        
        # System memory info
        self.total_system_memory_gb = psutil.virtual_memory().total / (1024**3)
        self.total_system_memory_mb = psutil.virtual_memory().total / (1024**2)
        
        # Dynamic thresholds
        self._current_warning_threshold_mb = None
        self._current_critical_threshold_mb = None
        self._last_threshold_update = None
        
        # Memory leak detection
        self._baseline_memory = None
        self._leak_detection_samples = deque(maxlen=20)
        
        # Optimization state
        self._last_gc_time = None
        self._gc_cooldown_seconds = 60  # Don't run GC more than once per minute
        
        log.info(
            "memory_manager_initialized",
            extra={
                "total_system_memory_gb": self.total_system_memory_gb,
                "total_system_memory_mb": self.total_system_memory_mb
            }
        )
    
    def get_current_memory_snapshot(self) -> MemoryUsageSnapshot:
        """Get current memory usage snapshot."""
        system_memory = psutil.virtual_memory()
        
        # Get current process memory
        try:
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024**2)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_memory_mb = 0.0
        
        snapshot = MemoryUsageSnapshot(
            timestamp=datetime.utcnow(),
            used_mb=system_memory.used / (1024**2),
            available_mb=system_memory.available / (1024**2),
            total_mb=system_memory.total / (1024**2),
            percent_used=system_memory.percent,
            process_memory_mb=process_memory_mb
        )
        
        # Add to history
        self.usage_history.append(snapshot)
        
        return snapshot
    
    def calculate_dynamic_thresholds(self) -> Tuple[float, float]:
        """
        Calculate dynamic memory thresholds based on system capacity and usage patterns.
        
        Returns:
            Tuple of (warning_threshold_mb, critical_threshold_mb)
        """
        snapshot = self.get_current_memory_snapshot()
        
        # Base thresholds as percentage of available memory
        # For a system with 62GB, we want much higher thresholds
        if self.total_system_memory_gb >= 32:
            # Large memory systems (32GB+)
            warning_percent = 70.0  # 70% of total memory
            critical_percent = 85.0  # 85% of total memory
        elif self.total_system_memory_gb >= 16:
            # Medium memory systems (16-32GB)
            warning_percent = 60.0
            critical_percent = 75.0
        else:
            # Small memory systems (<16GB)
            warning_percent = 50.0
            critical_percent = 65.0
        
        base_warning_mb = (self.total_system_memory_mb * warning_percent) / 100
        base_critical_mb = (self.total_system_memory_mb * critical_percent) / 100
        
        # Adjust based on usage patterns if we have enough history
        if len(self.usage_history) >= 10:
            recent_usage = [s.used_mb for s in list(self.usage_history)[-10:]]
            avg_usage = sum(recent_usage) / len(recent_usage)
            max_usage = max(recent_usage)
            
            # If average usage is much lower than thresholds, we can be more conservative
            if avg_usage < base_warning_mb * 0.3:  # Using less than 30% of warning threshold
                # System is using very little memory, we can set higher thresholds
                warning_mb = max(base_warning_mb, avg_usage * 3)  # 3x current average
                critical_mb = max(base_critical_mb, max_usage * 2)  # 2x recent max
            else:
                # Normal usage patterns
                warning_mb = base_warning_mb
                critical_mb = base_critical_mb
        else:
            # Not enough history, use base thresholds
            warning_mb = base_warning_mb
            critical_mb = base_critical_mb
        
        # Ensure critical is always higher than warning
        if critical_mb <= warning_mb:
            critical_mb = warning_mb * 1.2
        
        # Minimum thresholds to prevent setting them too low
        min_warning_mb = 4096  # 4GB minimum warning
        min_critical_mb = 6144  # 6GB minimum critical
        
        warning_mb = max(warning_mb, min_warning_mb)
        critical_mb = max(critical_mb, min_critical_mb)
        
        log.debug(
            "dynamic_thresholds_calculated",
            extra={
                "warning_mb": warning_mb,
                "critical_mb": critical_mb,
                "warning_percent": (warning_mb / self.total_system_memory_mb) * 100,
                "critical_percent": (critical_mb / self.total_system_memory_mb) * 100,
                "current_usage_mb": snapshot.used_mb,
                "current_usage_percent": snapshot.percent_used
            }
        )
        
        return warning_mb, critical_mb
    
    def update_thresholds_if_needed(self) -> bool:
        """
        Update memory thresholds if needed based on current conditions.
        
        Returns:
            True if thresholds were updated, False otherwise
        """
        now = datetime.utcnow()
        
        # Only update thresholds every 5 minutes to avoid too frequent changes
        if (self._last_threshold_update and 
            now - self._last_threshold_update < timedelta(minutes=5)):
            return False
        
        warning_mb, critical_mb = self.calculate_dynamic_thresholds()
        
        # Get current configured thresholds
        config = self.config_manager.get_monitoring_config()
        current_warning = config.memory_warning_threshold
        current_critical = config.memory_critical_threshold
        
        # Check if thresholds need significant adjustment (>10% change)
        warning_change_percent = abs(warning_mb - current_warning) / current_warning * 100
        critical_change_percent = abs(critical_mb - current_critical) / current_critical * 100
        
        if warning_change_percent > 10 or critical_change_percent > 10:
            # Update thresholds
            try:
                # Update in database settings
                from src.domain.settings.service import SettingsService
                from src.adapters.db.base import SessionLocal
                
                with SessionLocal() as db:
                    settings_service = SettingsService(db)
                    
                    settings_service.set("monitoring_memory_warning_mb", str(int(warning_mb)))
                    settings_service.set("monitoring_memory_critical_mb", str(int(critical_mb)))
                
                self._current_warning_threshold_mb = warning_mb
                self._current_critical_threshold_mb = critical_mb
                self._last_threshold_update = now
                
                log.info(
                    "memory_thresholds_updated",
                    extra={
                        "old_warning_mb": current_warning,
                        "new_warning_mb": warning_mb,
                        "old_critical_mb": current_critical,
                        "new_critical_mb": critical_mb,
                        "warning_change_percent": warning_change_percent,
                        "critical_change_percent": critical_change_percent
                    }
                )
                
                return True
                
            except Exception as e:
                log.error(
                    "failed_to_update_memory_thresholds",
                    extra={"error": str(e)},
                    exc_info=True
                )
                return False
        
        return False
    
    def perform_garbage_collection(self) -> MemoryOptimizationResult:
        """
        Perform garbage collection and return optimization results.
        
        Returns:
            MemoryOptimizationResult with details of the optimization
        """
        now = datetime.utcnow()
        
        # Check cooldown
        if (self._last_gc_time and 
            now - self._last_gc_time < timedelta(seconds=self._gc_cooldown_seconds)):
            return MemoryOptimizationResult(
                before_mb=0,
                after_mb=0,
                recovered_mb=0,
                actions_taken=["skipped_due_to_cooldown"],
                success=False,
                timestamp=now
            )
        
        # Get memory before GC
        before_snapshot = self.get_current_memory_snapshot()
        before_mb = before_snapshot.process_memory_mb
        
        actions_taken = []
        
        try:
            # Force garbage collection
            collected_objects = gc.collect()
            actions_taken.append(f"gc_collect_freed_{collected_objects}_objects")
            
            # Clear any internal caches if available
            try:
                # Clear DexScreener client cache if available
                from src.adapters.services.resilient_dexscreener_client import get_resilient_dexscreener_client
                client = get_resilient_dexscreener_client()
                if hasattr(client, 'clear_cache'):
                    cache_size_before = getattr(client, '_cache_size', 0)
                    client.clear_cache()
                    actions_taken.append(f"cleared_dexscreener_cache_{cache_size_before}_entries")
                else:
                    actions_taken.append("dexscreener_cache_not_available")
            except Exception as e:
                actions_taken.append(f"cache_clear_error_{str(e)[:50]}")
            
            # Clear performance tracker caches
            try:
                from .metrics import get_performance_tracker
                perf_tracker = get_performance_tracker()
                if hasattr(perf_tracker, 'clear_old_metrics'):
                    cleared_count = perf_tracker.clear_old_metrics()
                    actions_taken.append(f"cleared_performance_metrics_{cleared_count}_entries")
            except Exception as e:
                actions_taken.append(f"perf_cache_clear_error_{str(e)[:50]}")
            
            # Clear monitoring history if it's getting too large
            try:
                if len(self.usage_history) > 50:
                    old_size = len(self.usage_history)
                    # Keep only last 25 entries
                    while len(self.usage_history) > 25:
                        self.usage_history.popleft()
                    actions_taken.append(f"trimmed_usage_history_{old_size}_to_{len(self.usage_history)}")
                
                if len(self.optimization_history) > 20:
                    old_size = len(self.optimization_history)
                    # Keep only last 10 entries
                    self.optimization_history = self.optimization_history[-10:]
                    actions_taken.append(f"trimmed_optimization_history_{old_size}_to_{len(self.optimization_history)}")
            except Exception as e:
                actions_taken.append(f"history_trim_error_{str(e)[:50]}")
            
            # Force Python to release memory to OS
            try:
                import ctypes
                if hasattr(ctypes, 'CDLL'):
                    libc = ctypes.CDLL("libc.so.6")
                    if hasattr(libc, 'malloc_trim'):
                        result = libc.malloc_trim(0)
                        actions_taken.append(f"malloc_trim_result_{result}")
            except Exception as e:
                actions_taken.append(f"malloc_trim_error_{str(e)[:30]}")
            
            # Wait a moment for memory to be freed
            time.sleep(1)
            
            # Get memory after GC
            after_snapshot = self.get_current_memory_snapshot()
            after_mb = after_snapshot.process_memory_mb
            
            recovered_mb = before_mb - after_mb
            
            self._last_gc_time = now
            
            result = MemoryOptimizationResult(
                before_mb=before_mb,
                after_mb=after_mb,
                recovered_mb=recovered_mb,
                actions_taken=actions_taken,
                success=True,
                timestamp=now
            )
            
            self.optimization_history.append(result)
            
            log.info(
                "garbage_collection_completed",
                extra={
                    "before_mb": before_mb,
                    "after_mb": after_mb,
                    "recovered_mb": recovered_mb,
                    "actions_taken": actions_taken,
                    "collected_objects": collected_objects
                }
            )
            
            return result
            
        except Exception as e:
            log.error(
                "garbage_collection_failed",
                extra={"error": str(e)},
                exc_info=True
            )
            
            return MemoryOptimizationResult(
                before_mb=before_mb,
                after_mb=before_mb,
                recovered_mb=0,
                actions_taken=actions_taken + [f"error_{str(e)}"],
                success=False,
                timestamp=now
            )
    
    def detect_memory_leak(self) -> Optional[Dict[str, Any]]:
        """
        Detect potential memory leaks based on usage patterns.
        
        Returns:
            Dictionary with leak detection results or None if no leak detected
        """
        if len(self.usage_history) < 10:
            return None
        
        # Analyze recent memory usage trend
        recent_snapshots = list(self.usage_history)[-10:]
        memory_values = [s.process_memory_mb for s in recent_snapshots]
        
        # Calculate trend
        if len(memory_values) >= 5:
            # Simple linear trend calculation
            x_values = list(range(len(memory_values)))
            n = len(memory_values)
            
            sum_x = sum(x_values)
            sum_y = sum(memory_values)
            sum_xy = sum(x * y for x, y in zip(x_values, memory_values))
            sum_x2 = sum(x * x for x in x_values)
            
            # Calculate slope (trend)
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # If slope is positive and significant, might indicate a leak
            if slope > 5:  # More than 5MB increase per measurement
                min_memory = min(memory_values)
                max_memory = max(memory_values)
                increase_percent = ((max_memory - min_memory) / min_memory) * 100
                
                if increase_percent > 20:  # More than 20% increase
                    return {
                        "detected": True,
                        "slope_mb_per_measurement": slope,
                        "total_increase_mb": max_memory - min_memory,
                        "increase_percent": increase_percent,
                        "timespan_minutes": (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds() / 60,
                        "recommendation": "investigate_memory_usage"
                    }
        
        return None
    
    def perform_targeted_cleanup(self, component: str = None) -> MemoryOptimizationResult:
        """
        Perform targeted cleanup for specific components or comprehensive cleanup.
        
        Args:
            component: Specific component to clean up (e.g., 'api_cache', 'metrics', 'all')
            
        Returns:
            MemoryOptimizationResult with cleanup details
        """
        now = datetime.utcnow()
        before_snapshot = self.get_current_memory_snapshot()
        before_mb = before_snapshot.process_memory_mb
        
        actions_taken = []
        
        try:
            if component is None or component == 'all':
                # Comprehensive cleanup
                
                # 1. Clear API caches
                try:
                    from src.adapters.services.resilient_dexscreener_client import get_resilient_dexscreener_client
                    client = get_resilient_dexscreener_client()
                    if hasattr(client, 'clear_cache'):
                        cache_size = getattr(client, '_cache_size', 0)
                        client.clear_cache()
                        actions_taken.append(f"cleared_api_cache_{cache_size}_entries")
                except Exception as e:
                    actions_taken.append(f"api_cache_error_{str(e)[:30]}")
                
                # 2. Clear performance metrics
                try:
                    from .metrics import get_performance_tracker
                    perf_tracker = get_performance_tracker()
                    if hasattr(perf_tracker, 'clear_old_metrics'):
                        cleared = perf_tracker.clear_old_metrics()
                        actions_taken.append(f"cleared_metrics_{cleared}_entries")
                except Exception as e:
                    actions_taken.append(f"metrics_error_{str(e)[:30]}")
                
                # 3. Clear monitoring history
                self._cleanup_monitoring_history()
                actions_taken.append("cleaned_monitoring_history")
                
                # 4. Force garbage collection
                collected = gc.collect()
                actions_taken.append(f"gc_collected_{collected}_objects")
                
                # 5. Try to release memory to OS
                self._release_memory_to_os()
                actions_taken.append("attempted_memory_release")
                
            elif component == 'api_cache':
                # Clear only API caches
                try:
                    from src.adapters.services.resilient_dexscreener_client import get_resilient_dexscreener_client
                    client = get_resilient_dexscreener_client()
                    if hasattr(client, 'clear_cache'):
                        client.clear_cache()
                        actions_taken.append("cleared_api_cache")
                except Exception as e:
                    actions_taken.append(f"api_cache_error_{str(e)[:30]}")
                    
            elif component == 'metrics':
                # Clear only metrics
                try:
                    from .metrics import get_performance_tracker
                    perf_tracker = get_performance_tracker()
                    if hasattr(perf_tracker, 'clear_old_metrics'):
                        cleared = perf_tracker.clear_old_metrics()
                        actions_taken.append(f"cleared_metrics_{cleared}_entries")
                except Exception as e:
                    actions_taken.append(f"metrics_error_{str(e)[:30]}")
            
            # Wait for cleanup to take effect
            time.sleep(1)
            
            # Get memory after cleanup
            after_snapshot = self.get_current_memory_snapshot()
            after_mb = after_snapshot.process_memory_mb
            
            recovered_mb = before_mb - after_mb
            
            result = MemoryOptimizationResult(
                before_mb=before_mb,
                after_mb=after_mb,
                recovered_mb=recovered_mb,
                actions_taken=actions_taken,
                success=True,
                timestamp=now
            )
            
            self.optimization_history.append(result)
            
            log.info(
                "targeted_cleanup_completed",
                extra={
                    "component": component,
                    "before_mb": before_mb,
                    "after_mb": after_mb,
                    "recovered_mb": recovered_mb,
                    "actions_taken": actions_taken
                }
            )
            
            return result
            
        except Exception as e:
            log.error(
                "targeted_cleanup_failed",
                extra={"component": component, "error": str(e)},
                exc_info=True
            )
            
            return MemoryOptimizationResult(
                before_mb=before_mb,
                after_mb=before_mb,
                recovered_mb=0,
                actions_taken=actions_taken + [f"error_{str(e)[:30]}"],
                success=False,
                timestamp=now
            )
    
    def _cleanup_monitoring_history(self):
        """Clean up monitoring history to free memory."""
        # Trim usage history
        if len(self.usage_history) > 25:
            while len(self.usage_history) > 25:
                self.usage_history.popleft()
        
        # Trim optimization history
        if len(self.optimization_history) > 10:
            self.optimization_history = self.optimization_history[-10:]
        
        # Clear leak detection samples
        if len(self._leak_detection_samples) > 10:
            while len(self._leak_detection_samples) > 10:
                self._leak_detection_samples.popleft()
    
    def _release_memory_to_os(self):
        """Try to release memory back to the operating system."""
        try:
            # Try malloc_trim on Linux
            import ctypes
            try:
                libc = ctypes.CDLL("libc.so.6")
                if hasattr(libc, 'malloc_trim'):
                    libc.malloc_trim(0)
            except (OSError, AttributeError):
                # Not on Linux or malloc_trim not available
                pass
        except Exception:
            # Ignore errors in memory release
            pass
    
    def check_memory_and_optimize(self) -> Tuple[bool, List[HealthAlert]]:
        """
        Check memory usage and perform optimization if needed.
        
        Returns:
            Tuple of (needs_alert, alerts_list)
        """
        snapshot = self.get_current_memory_snapshot()
        alerts = []
        
        # Update thresholds if needed
        thresholds_updated = self.update_thresholds_if_needed()
        
        # Get current thresholds
        config = self.config_manager.get_monitoring_config()
        warning_threshold = config.memory_warning_threshold
        critical_threshold = config.memory_critical_threshold
        
        # Check if we need to perform optimization before alerting
        if snapshot.used_mb >= critical_threshold:
            # Perform garbage collection before alerting
            optimization_result = self.perform_garbage_collection()
            
            # Get updated memory usage after optimization
            post_optimization_snapshot = self.get_current_memory_snapshot()
            
            if optimization_result.success and optimization_result.recovered_mb > 0:
                log.info(
                    "memory_optimization_before_alert",
                    extra={
                        "recovered_mb": optimization_result.recovered_mb,
                        "before_mb": snapshot.used_mb,
                        "after_mb": post_optimization_snapshot.used_mb
                    }
                )
                
                # Use post-optimization memory for alerting decision
                snapshot = post_optimization_snapshot
        
        # Check for memory leaks and perform automatic cleanup if detected
        leak_detection = self.detect_memory_leak()
        if leak_detection and leak_detection["detected"]:
            # Perform automatic targeted cleanup when leak is detected
            cleanup_result = self.perform_targeted_cleanup("all")
            
            leak_message = f"Memory leak detected: {leak_detection['increase_percent']:.1f}% increase over {leak_detection['timespan_minutes']:.1f} minutes"
            if cleanup_result.success and cleanup_result.recovered_mb > 0:
                leak_message += f" - Auto-cleanup recovered {cleanup_result.recovered_mb:.1f}MB"
            
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=leak_message,
                component="system.memory.leak_detection",
                timestamp=datetime.utcnow()
            ))
            
            # Send enhanced Telegram notification for memory leak
            try:
                from .telegram_notifier import get_telegram_notifier
                telegram_notifier = get_telegram_notifier()
                telegram_notifier.send_memory_alert(
                    alert_type="leak_detected",
                    current_usage_mb=snapshot.used_mb,
                    threshold_mb=critical_threshold,
                    total_memory_gb=self.total_system_memory_gb,
                    recovered_mb=cleanup_result.recovered_mb if cleanup_result.success else None,
                    actions_taken=cleanup_result.actions_taken if cleanup_result.success else None
                )
            except Exception as e:
                log.error(f"Failed to send Telegram leak detection alert: {e}")
        
        # Generate alerts based on current usage and send Telegram notifications
        if snapshot.used_mb >= critical_threshold:
            alerts.append(HealthAlert(
                level=AlertLevel.CRITICAL,
                message=f"Memory usage critical: {snapshot.used_mb:.1f}MB / {snapshot.total_mb:.1f}MB ({snapshot.percent_used:.1f}%) - threshold: {critical_threshold:.1f}MB",
                component="system.memory",
                timestamp=datetime.utcnow()
            ))
            
            # Send enhanced Telegram notification
            try:
                from .telegram_notifier import get_telegram_notifier
                telegram_notifier = get_telegram_notifier()
                telegram_notifier.send_memory_alert(
                    alert_type="critical",
                    current_usage_mb=snapshot.used_mb,
                    threshold_mb=critical_threshold,
                    total_memory_gb=self.total_system_memory_gb,
                    recovered_mb=optimization_result.recovered_mb if optimization_result and optimization_result.success else None,
                    actions_taken=optimization_result.actions_taken if optimization_result and optimization_result.success else None
                )
            except Exception as e:
                log.error(f"Failed to send Telegram memory alert: {e}")
                
        elif snapshot.used_mb >= warning_threshold:
            alerts.append(HealthAlert(
                level=AlertLevel.WARNING,
                message=f"Memory usage high: {snapshot.used_mb:.1f}MB / {snapshot.total_mb:.1f}MB ({snapshot.percent_used:.1f}%) - threshold: {warning_threshold:.1f}MB",
                component="system.memory",
                timestamp=datetime.utcnow()
            ))
            
            # Send enhanced Telegram notification
            try:
                from .telegram_notifier import get_telegram_notifier
                telegram_notifier = get_telegram_notifier()
                telegram_notifier.send_memory_alert(
                    alert_type="warning",
                    current_usage_mb=snapshot.used_mb,
                    threshold_mb=warning_threshold,
                    total_memory_gb=self.total_system_memory_gb
                )
            except Exception as e:
                log.error(f"Failed to send Telegram memory alert: {e}")
        
        # Add informational alert if thresholds were updated
        if thresholds_updated:
            alerts.append(HealthAlert(
                level=AlertLevel.INFO,
                message=f"Memory thresholds auto-adjusted: warning={warning_threshold:.0f}MB, critical={critical_threshold:.0f}MB",
                component="system.memory.threshold_adjustment",
                timestamp=datetime.utcnow()
            ))
        
        return len(alerts) > 0, alerts
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics and optimization history."""
        snapshot = self.get_current_memory_snapshot()
        config = self.config_manager.get_monitoring_config()
        
        # Calculate usage trends if we have history
        usage_trend = None
        if len(self.usage_history) >= 5:
            recent_usage = [s.used_mb for s in list(self.usage_history)[-5:]]
            usage_trend = {
                "average_mb": sum(recent_usage) / len(recent_usage),
                "min_mb": min(recent_usage),
                "max_mb": max(recent_usage),
                "trend_direction": "increasing" if recent_usage[-1] > recent_usage[0] else "decreasing"
            }
        
        return {
            "current_usage": {
                "used_mb": snapshot.used_mb,
                "available_mb": snapshot.available_mb,
                "total_mb": snapshot.total_mb,
                "percent_used": snapshot.percent_used,
                "process_memory_mb": snapshot.process_memory_mb
            },
            "thresholds": {
                "warning_mb": config.memory_warning_threshold,
                "critical_mb": config.memory_critical_threshold,
                "warning_percent": (config.memory_warning_threshold / snapshot.total_mb) * 100,
                "critical_percent": (config.memory_critical_threshold / snapshot.total_mb) * 100
            },
            "optimization_history": [
                {
                    "timestamp": result.timestamp.isoformat(),
                    "recovered_mb": result.recovered_mb,
                    "success": result.success,
                    "actions": result.actions_taken
                }
                for result in self.optimization_history[-10:]  # Last 10 optimizations
            ],
            "usage_trend": usage_trend,
            "leak_detection": self.detect_memory_leak(),
            "system_info": {
                "total_system_memory_gb": self.total_system_memory_gb,
                "last_threshold_update": self._last_threshold_update.isoformat() if self._last_threshold_update else None,
                "last_gc_time": self._last_gc_time.isoformat() if self._last_gc_time else None
            }
        }


# Global memory manager instance
_memory_manager = None


def get_memory_manager() -> IntelligentMemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = IntelligentMemoryManager()
    return _memory_manager