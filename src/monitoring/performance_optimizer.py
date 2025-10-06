"""
Simple performance optimization system.

Provides basic performance optimization including:
- API timeout monitoring
- System resource monitoring  
- Basic optimization recommendations
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

log = logging.getLogger("performance_optimizer")


class SimplePerformanceOptimizer:
    """Simple performance optimizer for basic system monitoring."""
    
    def __init__(self):
        self.optimization_history = []
        
    def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run a simple optimization cycle."""
        try:
            # Get basic system metrics
            metrics = self._get_basic_metrics()
            
            # Check for optimization opportunities
            recommendations = []
            
            # Check CPU usage
            if metrics.get("cpu_usage", 0) > 80:
                recommendations.append("High CPU usage detected - consider reducing load")
            
            # Check memory usage and send Telegram alerts if needed
            memory_mb = metrics.get("memory_mb", 0)
            if memory_mb > 12000:  # >12GB (critical threshold)
                recommendations.append("Critical memory usage - immediate cleanup recommended")
                self._send_memory_alert("critical", memory_mb)
                # Trigger automatic cleanup for critical memory usage
                self._trigger_memory_cleanup_if_needed(memory_mb)
            elif memory_mb > 8000:  # >8GB (warning threshold)
                recommendations.append("High memory usage detected - consider cleanup")
                self._send_memory_alert("warning", memory_mb)
            
            # Log optimization cycle
            log.info(
                "performance_optimization_cycle_completed",
                extra={
                    "cpu_usage": metrics.get("cpu_usage", 0),
                    "memory_mb": metrics.get("memory_mb", 0),
                    "recommendations": len(recommendations)
                }
            )
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics,
                "recommendations": recommendations,
                "optimizations_applied": 0,
                "status": "completed"
            }
            
        except Exception as e:
            log.error(f"Error in optimization cycle: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed"
            }
    
    def _get_basic_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics."""
        try:
            import psutil
            
            return {
                "cpu_usage": psutil.cpu_percent(interval=0),
                "memory_mb": psutil.virtual_memory().used / (1024 * 1024),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            log.warning(f"Could not get system metrics: {e}")
            return {
                "cpu_usage": 0,
                "memory_mb": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _send_memory_alert(self, alert_type: str, memory_mb: float):
        """Send memory usage alert via Telegram."""
        try:
            from src.monitoring.telegram_notifier import get_telegram_notifier
            
            telegram_notifier = get_telegram_notifier()
            if not telegram_notifier.is_configured():
                return
            
            # Get total system memory for percentage calculation
            import psutil
            total_memory_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)
            memory_percent = (memory_mb / (total_memory_gb * 1024)) * 100
            
            # Send memory alert
            telegram_notifier.send_memory_alert(
                alert_type=alert_type,
                current_usage_mb=memory_mb,
                threshold_mb=8000 if alert_type == "warning" else 12000,
                total_memory_gb=total_memory_gb,
                usage_percent=memory_percent,
                component="system.performance_optimizer"
            )
            
            log.info(
                f"memory_alert_sent_via_performance_optimizer",
                extra={
                    "alert_type": alert_type,
                    "memory_mb": memory_mb,
                    "memory_percent": memory_percent,
                    "total_memory_gb": total_memory_gb
                }
            )
            
        except Exception as e:
            log.error(f"Failed to send memory alert: {e}")
    
    def _trigger_memory_cleanup_if_needed(self, memory_mb: float) -> bool:
        """Trigger memory cleanup if memory usage is high."""
        try:
            if memory_mb > 10000:  # >10GB - trigger cleanup
                import gc
                
                # Force garbage collection
                collected = gc.collect()
                
                # Try to trigger memory manager cleanup if available
                try:
                    from src.monitoring.memory_manager import get_memory_manager
                    memory_manager = get_memory_manager()
                    memory_manager.cleanup_memory()
                except Exception:
                    pass  # Memory manager might not be available
                
                log.info(
                    "automatic_memory_cleanup_triggered",
                    extra={
                        "memory_mb_before": memory_mb,
                        "gc_collected": collected,
                        "trigger_threshold": 10000
                    }
                )
                return True
                
        except Exception as e:
            log.error(f"Failed to trigger automatic memory cleanup: {e}")
        
        return False


# Global instance
_optimizer = None


def get_performance_optimizer() -> SimplePerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = SimplePerformanceOptimizer()
    return _optimizer    

    def _send_memory_alert(self, alert_type: str, memory_mb: float):
        """Send memory usage alert via Telegram."""
        try:
            from src.monitoring.telegram_notifier import get_telegram_notifier
            
            telegram_notifier = get_telegram_notifier()
            if not telegram_notifier.is_configured():
                return
            
            # Get total system memory for percentage calculation
            import psutil
            total_memory_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)
            memory_percent = (memory_mb / (total_memory_gb * 1024)) * 100
            
            # Send memory alert
            telegram_notifier.send_memory_alert(
                alert_type=alert_type,
                current_usage_mb=memory_mb,
                threshold_mb=8000 if alert_type == "warning" else 12000,
                total_memory_gb=total_memory_gb,
                usage_percent=memory_percent,
                component="system.performance_optimizer"
            )
            
            log.info(
                f"memory_alert_sent_via_performance_optimizer",
                extra={
                    "alert_type": alert_type,
                    "memory_mb": memory_mb,
                    "memory_percent": memory_percent,
                    "total_memory_gb": total_memory_gb
                }
            )
            
        except Exception as e:
            log.error(f"Failed to send memory alert: {e}")
    
    def _trigger_memory_cleanup_if_needed(self, memory_mb: float) -> bool:
        """Trigger memory cleanup if memory usage is high."""
        try:
            if memory_mb > 10000:  # >10GB - trigger cleanup
                import gc
                
                # Force garbage collection
                collected = gc.collect()
                
                # Try to trigger memory manager cleanup if available
                try:
                    from src.monitoring.memory_manager import get_memory_manager
                    memory_manager = get_memory_manager()
                    memory_manager.cleanup_memory()
                except Exception:
                    pass  # Memory manager might not be available
                
                log.info(
                    "automatic_memory_cleanup_triggered",
                    extra={
                        "memory_mb_before": memory_mb,
                        "gc_collected": collected,
                        "trigger_threshold": 10000
                    }
                )
                return True
                
        except Exception as e:
            log.error(f"Failed to trigger automatic memory cleanup: {e}")
        
        return False