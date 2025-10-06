"""
Enhanced Telegram notification system for system monitoring.

This module provides specialized Telegram notifications for memory management,
performance monitoring, and system health alerts with rich formatting and context.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import HealthAlert, AlertLevel
from .alert_manager import get_alert_manager

log = logging.getLogger("telegram_notifier")


@dataclass
class TelegramMessage:
    """Structured Telegram message with formatting."""
    text: str
    parse_mode: str = "Markdown"
    disable_web_page_preview: bool = True


class TelegramNotifier:
    """
    Enhanced Telegram notifier with specialized message formatting.
    
    Provides rich notifications for different types of system events
    with appropriate formatting and context.
    """
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.alert_manager = get_alert_manager()
        
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)
    
    def send_memory_alert(
        self, 
        alert_type: str,
        current_usage_mb: float,
        threshold_mb: float,
        total_memory_gb: float,
        recovered_mb: Optional[float] = None,
        actions_taken: Optional[List[str]] = None
    ) -> bool:
        """
        Send memory-specific alert with detailed context.
        
        Args:
            alert_type: Type of memory alert (critical, warning, optimized, leak_detected)
            current_usage_mb: Current memory usage in MB
            threshold_mb: Memory threshold that was exceeded
            total_memory_gb: Total system memory in GB
            recovered_mb: Memory recovered through optimization (if applicable)
            actions_taken: List of optimization actions taken (if applicable)
        """
        if not self.is_configured():
            log.warning("Telegram not configured - memory alert not sent")
            return False
        
        # Calculate percentages
        usage_percent = (current_usage_mb / (total_memory_gb * 1024)) * 100
        threshold_percent = (threshold_mb / (total_memory_gb * 1024)) * 100
        
        # Format message based on alert type
        if alert_type == "critical":
            emoji = "🚨"
            level = AlertLevel.CRITICAL
            title = "CRITICAL MEMORY USAGE"
            message = f"{emoji} *{title}*\n\n"
            message += f"💾 Usage: `{current_usage_mb:.1f}MB` ({usage_percent:.1f}%)\n"
            message += f"⚠️ Threshold: `{threshold_mb:.1f}MB` ({threshold_percent:.1f}%)\n"
            message += f"🖥️ Total Memory: `{total_memory_gb:.1f}GB`\n"
            
            if recovered_mb and recovered_mb > 0:
                message += f"🔧 Auto-cleanup recovered: `{recovered_mb:.1f}MB`\n"
            
            message += f"\n📊 System requires immediate attention!"
            
        elif alert_type == "warning":
            emoji = "⚠️"
            level = AlertLevel.WARNING
            title = "HIGH MEMORY USAGE"
            message = f"{emoji} *{title}*\n\n"
            message += f"💾 Usage: `{current_usage_mb:.1f}MB` ({usage_percent:.1f}%)\n"
            message += f"⚠️ Threshold: `{threshold_mb:.1f}MB` ({threshold_percent:.1f}%)\n"
            message += f"🖥️ Total Memory: `{total_memory_gb:.1f}GB`\n"
            message += f"\n📈 Monitor for continued growth"
            
        elif alert_type == "optimized":
            emoji = "✅"
            level = AlertLevel.INFO
            title = "MEMORY OPTIMIZATION COMPLETED"
            message = f"{emoji} *{title}*\n\n"
            message += f"💾 Current Usage: `{current_usage_mb:.1f}MB` ({usage_percent:.1f}%)\n"
            message += f"🔧 Memory Recovered: `{recovered_mb:.1f}MB`\n"
            
            if actions_taken:
                message += f"⚙️ Actions: `{', '.join(actions_taken[:3])}`\n"
            
            message += f"🖥️ Total Memory: `{total_memory_gb:.1f}GB`"
            
        elif alert_type == "leak_detected":
            emoji = "🔍"
            level = AlertLevel.WARNING
            title = "MEMORY LEAK DETECTED"
            message = f"{emoji} *{title}*\n\n"
            message += f"💾 Current Usage: `{current_usage_mb:.1f}MB` ({usage_percent:.1f}%)\n"
            message += f"📈 Leak Pattern: Memory increasing over time\n"
            
            if recovered_mb and recovered_mb > 0:
                message += f"🔧 Auto-cleanup recovered: `{recovered_mb:.1f}MB`\n"
            
            message += f"🖥️ Total Memory: `{total_memory_gb:.1f}GB`\n"
            message += f"\n🔍 Investigation recommended"
            
        else:
            # Generic memory alert
            emoji = "💾"
            level = AlertLevel.INFO
            message = f"{emoji} *Memory Status Update*\n\n"
            message += f"💾 Usage: `{current_usage_mb:.1f}MB` ({usage_percent:.1f}%)\n"
            message += f"🖥️ Total Memory: `{total_memory_gb:.1f}GB`"
        
        # Create and send alert
        alert = HealthAlert(
            level=level,
            message=message,
            component="system.memory",
            timestamp=datetime.utcnow()
        )
        
        return self.alert_manager.send_alert(alert)
    
    def send_performance_alert(
        self,
        alert_type: str,
        component: str,
        metrics: Dict[str, Any],
        recommendations: Optional[List[str]] = None
    ) -> bool:
        """
        Send performance-related alert with metrics.
        
        Args:
            alert_type: Type of performance alert (degradation, improvement, bottleneck)
            component: Component experiencing performance issues
            metrics: Performance metrics dictionary
            recommendations: List of recommended actions
        """
        if not self.is_configured():
            log.warning("Telegram not configured - performance alert not sent")
            return False
        
        if alert_type == "degradation":
            emoji = "📉"
            level = AlertLevel.WARNING
            title = "PERFORMANCE DEGRADATION"
            
        elif alert_type == "improvement":
            emoji = "📈"
            level = AlertLevel.INFO
            title = "PERFORMANCE IMPROVEMENT"
            
        elif alert_type == "bottleneck":
            emoji = "🚧"
            level = AlertLevel.ERROR
            title = "PERFORMANCE BOTTLENECK"
            
        else:
            emoji = "📊"
            level = AlertLevel.INFO
            title = "PERFORMANCE UPDATE"
        
        message = f"{emoji} *{title}*\n\n"
        message += f"🔧 Component: `{component}`\n"
        
        # Add key metrics
        if "response_time" in metrics:
            message += f"⏱️ Response Time: `{metrics['response_time']:.2f}s`\n"
        
        if "throughput" in metrics:
            message += f"🚀 Throughput: `{metrics['throughput']:.1f}/min`\n"
        
        if "error_rate" in metrics:
            message += f"❌ Error Rate: `{metrics['error_rate']:.1f}%`\n"
        
        if "cpu_usage" in metrics:
            message += f"🖥️ CPU Usage: `{metrics['cpu_usage']:.1f}%`\n"
        
        # Add recommendations
        if recommendations:
            message += f"\n💡 *Recommendations:*\n"
            for i, rec in enumerate(recommendations[:3], 1):  # Limit to 3
                message += f"{i}. {rec}\n"
        
        # Create and send alert
        alert = HealthAlert(
            level=level,
            message=message,
            component=f"performance.{component}",
            timestamp=datetime.utcnow()
        )
        
        return self.alert_manager.send_alert(alert)
    
    def send_token_processing_alert(
        self,
        alert_type: str,
        tokens_stuck: int = 0,
        processing_rate: float = 0.0,
        backlog_size: int = 0,
        avg_activation_time: Optional[float] = None
    ) -> bool:
        """
        Send token processing-related alert.
        
        Args:
            alert_type: Type of alert (stuck_tokens, slow_processing, backlog_growing)
            tokens_stuck: Number of tokens stuck in monitoring status
            processing_rate: Current processing rate (tokens/minute)
            backlog_size: Size of processing backlog
            avg_activation_time: Average time for token activation in minutes
        """
        if not self.is_configured():
            log.warning("Telegram not configured - token processing alert not sent")
            return False
        
        if alert_type == "stuck_tokens":
            emoji = "🔒"
            level = AlertLevel.WARNING
            title = "TOKENS STUCK IN MONITORING"
            message = f"{emoji} *{title}*\n\n"
            message += f"🔒 Stuck Tokens: `{tokens_stuck}`\n"
            message += f"⏱️ Processing Rate: `{processing_rate:.1f}/min`\n"
            
            if avg_activation_time:
                message += f"⏰ Avg Activation Time: `{avg_activation_time:.1f} min`\n"
            
            message += f"\n🔍 Investigation needed for activation logic"
            
        elif alert_type == "slow_processing":
            emoji = "🐌"
            level = AlertLevel.WARNING
            title = "SLOW TOKEN PROCESSING"
            message = f"{emoji} *{title}*\n\n"
            message += f"⏱️ Processing Rate: `{processing_rate:.1f}/min`\n"
            message += f"📊 Backlog Size: `{backlog_size}`\n"
            
            if avg_activation_time:
                message += f"⏰ Avg Activation Time: `{avg_activation_time:.1f} min`\n"
            
            message += f"\n⚡ Consider increasing processing capacity"
            
        elif alert_type == "backlog_growing":
            emoji = "📈"
            level = AlertLevel.ERROR
            title = "PROCESSING BACKLOG GROWING"
            message = f"{emoji} *{title}*\n\n"
            message += f"📊 Backlog Size: `{backlog_size}`\n"
            message += f"⏱️ Processing Rate: `{processing_rate:.1f}/min`\n"
            message += f"\n🚨 Immediate attention required"
            
        else:
            emoji = "🪙"
            level = AlertLevel.INFO
            title = "TOKEN PROCESSING UPDATE"
            message = f"{emoji} *{title}*\n\n"
            message += f"⏱️ Processing Rate: `{processing_rate:.1f}/min`\n"
            message += f"📊 Backlog Size: `{backlog_size}`\n"
        
        # Create and send alert
        alert = HealthAlert(
            level=level,
            message=message,
            component="token.processing",
            timestamp=datetime.utcnow()
        )
        
        return self.alert_manager.send_alert(alert)
    
    def send_system_health_summary(
        self,
        memory_status: str,
        cpu_usage: float,
        api_status: str,
        tokens_processed_last_hour: int,
        active_alerts: int
    ) -> bool:
        """
        Send periodic system health summary.
        
        Args:
            memory_status: Memory status (healthy, warning, critical)
            cpu_usage: Current CPU usage percentage
            api_status: API health status
            tokens_processed_last_hour: Number of tokens processed in last hour
            active_alerts: Number of active alerts
        """
        if not self.is_configured():
            log.warning("Telegram not configured - health summary not sent")
            return False
        
        # Determine overall status
        if memory_status == "critical" or active_alerts > 5:
            emoji = "🚨"
            level = AlertLevel.CRITICAL
            status = "CRITICAL"
        elif memory_status == "warning" or active_alerts > 2:
            emoji = "⚠️"
            level = AlertLevel.WARNING
            status = "WARNING"
        else:
            emoji = "✅"
            level = AlertLevel.INFO
            status = "HEALTHY"
        
        message = f"{emoji} *System Health Summary*\n\n"
        message += f"🏥 Overall Status: `{status}`\n"
        message += f"💾 Memory: `{memory_status.upper()}`\n"
        message += f"🖥️ CPU Usage: `{cpu_usage:.1f}%`\n"
        message += f"🌐 API Status: `{api_status.upper()}`\n"
        message += f"🪙 Tokens Processed: `{tokens_processed_last_hour}/hour`\n"
        message += f"🚨 Active Alerts: `{active_alerts}`\n"
        message += f"\n📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        
        # Create and send alert
        alert = HealthAlert(
            level=level,
            message=message,
            component="system.health_summary",
            timestamp=datetime.utcnow()
        )
        
        return self.alert_manager.send_alert(alert)


# Global notifier instance
_telegram_notifier = None


def get_telegram_notifier() -> TelegramNotifier:
    """Get the global Telegram notifier instance."""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier