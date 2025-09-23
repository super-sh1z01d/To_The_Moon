"""
Alert Manager for centralized alert handling and distribution.

Provides alert deduplication, cooldown management, and multiple alert channels.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from src.monitoring.models import HealthAlert, AlertLevel

log = logging.getLogger("alert_manager")


class AlertChannel(Enum):
    """Available alert channels."""
    LOG = "log"
    CONSOLE = "console"
    # Future: EMAIL = "email", SLACK = "slack", etc.


@dataclass
class AlertRule:
    """Configuration for alert handling."""
    component_pattern: str  # Pattern to match component names
    min_level: AlertLevel  # Minimum alert level to process
    cooldown_minutes: int = 5  # Cooldown period between same alerts
    max_frequency_per_hour: int = 10  # Maximum alerts per hour for this rule
    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG])
    enabled: bool = True


@dataclass
class AlertHistory:
    """History of an alert for deduplication and cooldown."""
    alert_key: str
    last_sent: datetime
    count_last_hour: int = 0
    total_count: int = 0
    first_occurrence: datetime = field(default_factory=datetime.utcnow)
    last_occurrence: datetime = field(default_factory=datetime.utcnow)


class AlertManager:
    """Centralized alert management system."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._alert_history: Dict[str, AlertHistory] = {}
        self._alert_rules: List[AlertRule] = []
        self._alert_handlers: Dict[AlertChannel, Callable] = {}
        self._suppressed_alerts: Set[str] = set()
        
        # Setup default alert rules
        self._setup_default_rules()
        
        # Setup default alert handlers
        self._setup_default_handlers()
    
    def _setup_default_rules(self):
        """Setup default alert rules."""
        self._alert_rules = [
            # Critical alerts - immediate notification, low cooldown
            AlertRule(
                component_pattern="*",
                min_level=AlertLevel.CRITICAL,
                cooldown_minutes=1,
                max_frequency_per_hour=20,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE]
            ),
            
            # Error alerts - moderate cooldown
            AlertRule(
                component_pattern="*",
                min_level=AlertLevel.ERROR,
                cooldown_minutes=5,
                max_frequency_per_hour=15,
                channels=[AlertChannel.LOG]
            ),
            
            # Warning alerts - higher cooldown
            AlertRule(
                component_pattern="*",
                min_level=AlertLevel.WARNING,
                cooldown_minutes=10,
                max_frequency_per_hour=10,
                channels=[AlertChannel.LOG]
            ),
            
            # Info alerts - highest cooldown, limited frequency
            AlertRule(
                component_pattern="*",
                min_level=AlertLevel.INFO,
                cooldown_minutes=30,
                max_frequency_per_hour=5,
                channels=[AlertChannel.LOG]
            ),
            
            # Scheduler-specific rules with lower cooldown
            AlertRule(
                component_pattern="scheduler*",
                min_level=AlertLevel.WARNING,
                cooldown_minutes=3,
                max_frequency_per_hour=20,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE]
            ),
            
            # API-specific rules
            AlertRule(
                component_pattern="*api*",
                min_level=AlertLevel.ERROR,
                cooldown_minutes=2,
                max_frequency_per_hour=25,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE]
            )
        ]
    
    def _setup_default_handlers(self):
        """Setup default alert handlers."""
        self._alert_handlers = {
            AlertChannel.LOG: self._handle_log_alert,
            AlertChannel.CONSOLE: self._handle_console_alert
        }
    
    def _handle_log_alert(self, alert: HealthAlert, rule: AlertRule) -> None:
        """Handle alert by logging it."""
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(alert.level, logging.INFO)
        
        log.log(
            log_level,
            "alert_triggered",
            extra={
                "extra": {
                    "alert_level": alert.level.value,
                    "component": alert.component,
                    "message": alert.message,
                    "correlation_id": alert.correlation_id,
                    "context": alert.context,
                    "timestamp": alert.timestamp.isoformat()
                }
            }
        )
    
    def _handle_console_alert(self, alert: HealthAlert, rule: AlertRule) -> None:
        """Handle alert by printing to console."""
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_symbol = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }.get(alert.level, "ℹ️")
        
        print(f"{level_symbol} [{timestamp}] {alert.level.value.upper()}: {alert.message}")
        print(f"   Component: {alert.component}")
        if alert.context:
            print(f"   Context: {alert.context}")
        print(f"   Correlation ID: {alert.correlation_id}")
        print()
    
    def _generate_alert_key(self, alert: HealthAlert) -> str:
        """Generate unique key for alert deduplication."""
        # Use component, level, and a hash of the message for deduplication
        import hashlib
        message_hash = hashlib.md5(alert.message.encode()).hexdigest()[:8]
        return f"{alert.component}:{alert.level.value}:{message_hash}"
    
    def _matches_pattern(self, component: str, pattern: str) -> bool:
        """Check if component matches pattern (simple wildcard matching)."""
        if pattern == "*":
            return True
        
        if "*" in pattern:
            # Simple wildcard matching
            if pattern.startswith("*"):
                return component.endswith(pattern[1:])
            elif pattern.endswith("*"):
                return component.startswith(pattern[:-1])
            else:
                # Pattern has * in the middle
                parts = pattern.split("*")
                return component.startswith(parts[0]) and component.endswith(parts[1])
        
        return component == pattern
    
    def _find_matching_rule(self, alert: HealthAlert) -> Optional[AlertRule]:
        """Find the most specific matching rule for an alert."""
        matching_rules = []
        
        for rule in self._alert_rules:
            if (rule.enabled and 
                alert.level.value >= rule.min_level.value and
                self._matches_pattern(alert.component, rule.component_pattern)):
                matching_rules.append(rule)
        
        if not matching_rules:
            return None
        
        # Return the most specific rule (least wildcards)
        return min(matching_rules, key=lambda r: r.component_pattern.count("*"))
    
    def _should_suppress_alert(self, alert: HealthAlert, rule: AlertRule) -> bool:
        """Check if alert should be suppressed due to cooldown or frequency limits."""
        alert_key = self._generate_alert_key(alert)
        now = datetime.utcnow()
        
        # Check if alert is manually suppressed
        if alert_key in self._suppressed_alerts:
            return True
        
        with self._lock:
            history = self._alert_history.get(alert_key)
            
            if history is None:
                # First occurrence of this alert
                self._alert_history[alert_key] = AlertHistory(
                    alert_key=alert_key,
                    last_sent=now,
                    count_last_hour=1,
                    total_count=1,
                    first_occurrence=now,
                    last_occurrence=now
                )
                return False
            
            # Update history
            history.last_occurrence = now
            history.total_count += 1
            
            # Check cooldown period
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            if now - history.last_sent < cooldown_delta:
                log.debug(
                    "alert_suppressed_cooldown",
                    extra={
                        "extra": {
                            "alert_key": alert_key,
                            "cooldown_minutes": rule.cooldown_minutes,
                            "time_since_last": (now - history.last_sent).total_seconds()
                        }
                    }
                )
                return True
            
            # Check frequency limit (reset hourly counter if needed)
            one_hour_ago = now - timedelta(hours=1)
            if history.last_sent < one_hour_ago:
                history.count_last_hour = 0
            
            if history.count_last_hour >= rule.max_frequency_per_hour:
                log.debug(
                    "alert_suppressed_frequency",
                    extra={
                        "extra": {
                            "alert_key": alert_key,
                            "count_last_hour": history.count_last_hour,
                            "max_frequency": rule.max_frequency_per_hour
                        }
                    }
                )
                return True
            
            # Update counters
            history.last_sent = now
            history.count_last_hour += 1
            
            return False
    
    def send_alert(self, alert: HealthAlert) -> bool:
        """Send an alert through appropriate channels."""
        try:
            # Find matching rule
            rule = self._find_matching_rule(alert)
            if rule is None:
                log.debug(
                    "alert_no_matching_rule",
                    extra={
                        "extra": {
                            "component": alert.component,
                            "level": alert.level.value,
                            "message": alert.message
                        }
                    }
                )
                return False
            
            # Check if alert should be suppressed
            if self._should_suppress_alert(alert, rule):
                return False
            
            # Send alert through configured channels
            sent_successfully = False
            for channel in rule.channels:
                handler = self._alert_handlers.get(channel)
                if handler:
                    try:
                        handler(alert, rule)
                        sent_successfully = True
                        log.debug(
                            "alert_sent",
                            extra={
                                "extra": {
                                    "channel": channel.value,
                                    "component": alert.component,
                                    "level": alert.level.value,
                                    "correlation_id": alert.correlation_id
                                }
                            }
                        )
                    except Exception as e:
                        log.error(
                            "alert_handler_error",
                            extra={
                                "extra": {
                                    "channel": channel.value,
                                    "error": str(e),
                                    "alert_correlation_id": alert.correlation_id
                                }
                            }
                        )
            
            return sent_successfully
            
        except Exception as e:
            log.error(
                "alert_send_error",
                extra={
                    "extra": {
                        "error": str(e),
                        "alert_component": alert.component,
                        "alert_level": alert.level.value
                    }
                }
            )
            return False
    
    def send_alerts(self, alerts: List[HealthAlert]) -> int:
        """Send multiple alerts and return count of successfully sent alerts."""
        sent_count = 0
        for alert in alerts:
            if self.send_alert(alert):
                sent_count += 1
        return sent_count
    
    def suppress_alert(self, component: str, level: AlertLevel, message_pattern: str) -> None:
        """Manually suppress alerts matching the given criteria."""
        # Generate a suppression key
        import hashlib
        pattern_hash = hashlib.md5(message_pattern.encode()).hexdigest()[:8]
        suppression_key = f"{component}:{level.value}:{pattern_hash}"
        
        with self._lock:
            self._suppressed_alerts.add(suppression_key)
        
        log.info(
            "alert_suppressed",
            extra={
                "extra": {
                    "component": component,
                    "level": level.value,
                    "message_pattern": message_pattern,
                    "suppression_key": suppression_key
                }
            }
        )
    
    def unsuppress_alert(self, component: str, level: AlertLevel, message_pattern: str) -> None:
        """Remove manual suppression for alerts matching the given criteria."""
        import hashlib
        pattern_hash = hashlib.md5(message_pattern.encode()).hexdigest()[:8]
        suppression_key = f"{component}:{level.value}:{pattern_hash}"
        
        with self._lock:
            self._suppressed_alerts.discard(suppression_key)
        
        log.info(
            "alert_unsuppressed",
            extra={
                "extra": {
                    "component": component,
                    "level": level.value,
                    "message_pattern": message_pattern,
                    "suppression_key": suppression_key
                }
            }
        )
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add a new alert rule."""
        with self._lock:
            self._alert_rules.append(rule)
        
        log.info(
            "alert_rule_added",
            extra={
                "extra": {
                    "component_pattern": rule.component_pattern,
                    "min_level": rule.min_level.value,
                    "cooldown_minutes": rule.cooldown_minutes,
                    "channels": [c.value for c in rule.channels]
                }
            }
        )
    
    def remove_alert_rule(self, component_pattern: str, min_level: AlertLevel) -> bool:
        """Remove an alert rule."""
        with self._lock:
            for i, rule in enumerate(self._alert_rules):
                if (rule.component_pattern == component_pattern and 
                    rule.min_level == min_level):
                    removed_rule = self._alert_rules.pop(i)
                    log.info(
                        "alert_rule_removed",
                        extra={
                            "extra": {
                                "component_pattern": removed_rule.component_pattern,
                                "min_level": removed_rule.min_level.value
                            }
                        }
                    )
                    return True
        return False
    
    def add_alert_handler(self, channel: AlertChannel, handler: Callable[[HealthAlert, AlertRule], None]) -> None:
        """Add a custom alert handler for a channel."""
        self._alert_handlers[channel] = handler
        log.info(
            "alert_handler_added",
            extra={
                "extra": {
                    "channel": channel.value,
                    "handler": handler.__name__
                }
            }
        )
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get statistics about alert history and performance."""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        with self._lock:
            total_alerts = len(self._alert_history)
            recent_alerts = sum(
                1 for h in self._alert_history.values() 
                if h.last_occurrence > one_hour_ago
            )
            
            alerts_by_level = defaultdict(int)
            alerts_by_component = defaultdict(int)
            
            for history in self._alert_history.values():
                if history.last_occurrence > one_day_ago:
                    # Extract level and component from alert key
                    parts = history.alert_key.split(":")
                    if len(parts) >= 2:
                        component = parts[0]
                        level = parts[1]
                        alerts_by_level[level] += history.total_count
                        alerts_by_component[component] += history.total_count
            
            return {
                "total_unique_alerts": total_alerts,
                "recent_alerts_last_hour": recent_alerts,
                "suppressed_alert_keys": len(self._suppressed_alerts),
                "active_rules": len([r for r in self._alert_rules if r.enabled]),
                "total_rules": len(self._alert_rules),
                "alerts_by_level_last_24h": dict(alerts_by_level),
                "alerts_by_component_last_24h": dict(alerts_by_component),
                "available_channels": [c.value for c in self._alert_handlers.keys()],
                "last_updated": now.isoformat()
            }
    
    def cleanup_old_history(self, days_to_keep: int = 7) -> int:
        """Clean up old alert history to prevent memory bloat."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        removed_count = 0
        
        with self._lock:
            keys_to_remove = [
                key for key, history in self._alert_history.items()
                if history.last_occurrence < cutoff_date
            ]
            
            for key in keys_to_remove:
                del self._alert_history[key]
                removed_count += 1
        
        if removed_count > 0:
            log.info(
                "alert_history_cleaned",
                extra={
                    "extra": {
                        "removed_count": removed_count,
                        "days_to_keep": days_to_keep,
                        "remaining_count": len(self._alert_history)
                    }
                }
            )
        
        return removed_count


# Global alert manager instance
alert_manager = AlertManager()


def send_alert(alert: HealthAlert) -> bool:
    """Convenience function to send an alert through the global alert manager."""
    return alert_manager.send_alert(alert)


def send_alerts(alerts: List[HealthAlert]) -> int:
    """Convenience function to send multiple alerts through the global alert manager."""
    return alert_manager.send_alerts(alerts)


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    return alert_manager


# Intelligent Alerting Extensions

@dataclass
class ThresholdRule:
    """Threshold-based alerting rule with hysteresis."""
    metric_name: str
    component_pattern: str
    upper_threshold: float
    lower_threshold: float  # For hysteresis
    alert_level: AlertLevel
    evaluation_window_minutes: int = 5
    min_data_points: int = 3
    enabled: bool = True


@dataclass
class TrendRule:
    """Trend-based predictive alerting rule."""
    metric_name: str
    component_pattern: str
    trend_threshold: float  # Rate of change per minute
    alert_level: AlertLevel
    correlation_threshold: float = 0.6  # Minimum correlation for trend validity
    forecast_minutes: int = 15
    evaluation_window_minutes: int = 10
    enabled: bool = True


@dataclass
class EscalationRule:
    """Alert escalation rule for repeated failures."""
    component_pattern: str
    initial_level: AlertLevel
    escalated_level: AlertLevel
    failure_count_threshold: int = 3
    time_window_minutes: int = 30
    escalation_cooldown_minutes: int = 60
    enabled: bool = True


class IntelligentAlertingEngine:
    """
    Intelligent alerting engine with threshold-based alerting with hysteresis,
    trend-based predictive alerting, and alert escalation for repeated failures.
    """
    
    def __init__(self, alert_manager: AlertManager):
        import threading
        from collections import defaultdict, deque
        
        self.alert_manager = alert_manager
        self.logger = logging.getLogger("intelligent_alerting")
        
        # Rules storage
        self.threshold_rules: List[ThresholdRule] = []
        self.trend_rules: List[TrendRule] = []
        self.escalation_rules: List[EscalationRule] = []
        
        # Metric storage for evaluation
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.threshold_states: Dict[str, bool] = {}  # Track if threshold is currently breached
        self.escalation_counters: Dict[str, Dict] = defaultdict(dict)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Setup default rules
        self._setup_default_intelligent_rules()
    
    def _setup_default_intelligent_rules(self):
        """Setup default intelligent alerting rules."""
        # CPU threshold rules with hysteresis
        self.threshold_rules.extend([
            ThresholdRule(
                metric_name="cpu_usage",
                component_pattern="*",
                upper_threshold=80.0,
                lower_threshold=70.0,  # Hysteresis
                alert_level=AlertLevel.WARNING,
                evaluation_window_minutes=3
            ),
            ThresholdRule(
                metric_name="cpu_usage",
                component_pattern="*",
                upper_threshold=95.0,
                lower_threshold=85.0,
                alert_level=AlertLevel.CRITICAL,
                evaluation_window_minutes=2
            ),
            
            # Memory threshold rules
            ThresholdRule(
                metric_name="memory_usage",
                component_pattern="*",
                upper_threshold=85.0,
                lower_threshold=75.0,
                alert_level=AlertLevel.WARNING,
                evaluation_window_minutes=5
            ),
            ThresholdRule(
                metric_name="memory_usage",
                component_pattern="*",
                upper_threshold=95.0,
                lower_threshold=90.0,
                alert_level=AlertLevel.CRITICAL,
                evaluation_window_minutes=2
            ),
            
            # Response time thresholds
            ThresholdRule(
                metric_name="response_time",
                component_pattern="*",
                upper_threshold=5.0,
                lower_threshold=3.0,
                alert_level=AlertLevel.WARNING,
                evaluation_window_minutes=3
            ),
            
            # Error rate thresholds
            ThresholdRule(
                metric_name="error_rate",
                component_pattern="*",
                upper_threshold=0.05,  # 5%
                lower_threshold=0.02,  # 2%
                alert_level=AlertLevel.ERROR,
                evaluation_window_minutes=5
            )
        ])
        
        # Trend-based predictive rules
        self.trend_rules.extend([
            TrendRule(
                metric_name="cpu_usage",
                component_pattern="*",
                trend_threshold=2.0,  # 2% increase per minute
                alert_level=AlertLevel.WARNING,
                forecast_minutes=10
            ),
            TrendRule(
                metric_name="memory_usage",
                component_pattern="*",
                trend_threshold=1.5,  # 1.5% increase per minute
                alert_level=AlertLevel.WARNING,
                forecast_minutes=15
            ),
            TrendRule(
                metric_name="error_rate",
                component_pattern="*",
                trend_threshold=0.01,  # 1% increase per minute
                alert_level=AlertLevel.ERROR,
                forecast_minutes=5
            )
        ])
        
        # Escalation rules
        self.escalation_rules.extend([
            EscalationRule(
                component_pattern="scheduler*",
                initial_level=AlertLevel.WARNING,
                escalated_level=AlertLevel.ERROR,
                failure_count_threshold=3,
                time_window_minutes=15
            ),
            EscalationRule(
                component_pattern="*api*",
                initial_level=AlertLevel.ERROR,
                escalated_level=AlertLevel.CRITICAL,
                failure_count_threshold=5,
                time_window_minutes=10
            )
        ])
    
    def record_metric(self, component: str, metric_name: str, value: float, timestamp: float = None):
        """Record a metric value for intelligent alerting evaluation."""
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        metric_key = f"{component}:{metric_name}"
        
        with self._lock:
            self.metric_history[metric_key].append({
                "value": value,
                "timestamp": timestamp
            })
        
        # Evaluate rules for this metric
        self._evaluate_threshold_rules(component, metric_name, value, timestamp)
        self._evaluate_trend_rules(component, metric_name, timestamp)
    
    def _evaluate_threshold_rules(self, component: str, metric_name: str, value: float, timestamp: float):
        """Evaluate threshold rules with hysteresis."""
        for rule in self.threshold_rules:
            if not rule.enabled:
                continue
            
            if (rule.metric_name == metric_name and 
                self.alert_manager._matches_pattern(component, rule.component_pattern)):
                
                state_key = f"{component}:{metric_name}:{rule.upper_threshold}"
                currently_breached = self.threshold_states.get(state_key, False)
                
                # Check for threshold breach with hysteresis
                should_alert = False
                new_state = currently_breached
                
                if not currently_breached and value > rule.upper_threshold:
                    # Threshold breached for the first time
                    should_alert = True
                    new_state = True
                elif currently_breached and value < rule.lower_threshold:
                    # Threshold recovered (hysteresis)
                    new_state = False
                    # Send recovery alert
                    self._send_threshold_recovery_alert(component, rule, value)
                
                self.threshold_states[state_key] = new_state
                
                if should_alert:
                    self._send_threshold_alert(component, rule, value)
    
    def _evaluate_trend_rules(self, component: str, metric_name: str, timestamp: float):
        """Evaluate trend-based predictive rules."""
        for rule in self.trend_rules:
            if not rule.enabled:
                continue
            
            if (rule.metric_name == metric_name and 
                self.alert_manager._matches_pattern(component, rule.component_pattern)):
                
                trend_analysis = self._analyze_metric_trend(component, metric_name, rule)
                
                if trend_analysis and trend_analysis["should_alert"]:
                    self._send_trend_alert(component, rule, trend_analysis)
    
    def _analyze_metric_trend(self, component: str, metric_name: str, rule: TrendRule) -> Optional[Dict]:
        """Analyze trend for a specific metric."""
        import time
        
        metric_key = f"{component}:{metric_name}"
        current_time = time.time()
        cutoff_time = current_time - (rule.evaluation_window_minutes * 60)
        
        with self._lock:
            recent_data = [
                point for point in self.metric_history[metric_key]
                if point["timestamp"] > cutoff_time
            ]
        
        if len(recent_data) < rule.min_data_points:
            return None
        
        # Calculate trend (simple linear regression)
        values = [point["value"] for point in recent_data]
        timestamps = [point["timestamp"] for point in recent_data]
        
        # Normalize timestamps to minutes from start
        start_time = min(timestamps)
        normalized_times = [(t - start_time) / 60 for t in timestamps]
        
        # Calculate trend slope and correlation
        n = len(values)
        if n < 2:
            return None
        
        # Simple linear regression
        x_mean = sum(normalized_times) / n
        y_mean = sum(values) / n
        
        numerator = sum((normalized_times[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        x_variance = sum((x - x_mean) ** 2 for x in normalized_times)
        y_variance = sum((y - y_mean) ** 2 for y in values)
        
        if x_variance == 0 or y_variance == 0:
            return None
        
        slope = numerator / x_variance  # Change per minute
        correlation = numerator / (x_variance * y_variance) ** 0.5
        
        # Check if trend is significant and concerning
        should_alert = (
            abs(correlation) >= rule.correlation_threshold and
            slope > rule.trend_threshold
        )
        
        if should_alert:
            # Project future value
            projected_value = values[-1] + (slope * rule.forecast_minutes)
            
            return {
                "should_alert": True,
                "slope": slope,
                "correlation": correlation,
                "current_value": values[-1],
                "projected_value": projected_value,
                "forecast_minutes": rule.forecast_minutes
            }
        
        return {"should_alert": False}
    
    def _send_threshold_alert(self, component: str, rule: ThresholdRule, value: float):
        """Send threshold-based alert."""
        alert = HealthAlert(
            level=rule.alert_level,
            component=component,
            message=f"Threshold breached: {rule.metric_name} = {value:.2f} (threshold: {rule.upper_threshold})",
            context={
                "metric_name": rule.metric_name,
                "current_value": value,
                "threshold": rule.upper_threshold,
                "alert_type": "threshold_breach"
            }
        )
        
        # Check for escalation
        escalated_alert = self._check_escalation(component, alert)
        self.alert_manager.send_alert(escalated_alert or alert)
    
    def _send_threshold_recovery_alert(self, component: str, rule: ThresholdRule, value: float):
        """Send threshold recovery alert."""
        alert = HealthAlert(
            level=AlertLevel.INFO,
            component=component,
            message=f"Threshold recovered: {rule.metric_name} = {value:.2f} (below {rule.lower_threshold})",
            context={
                "metric_name": rule.metric_name,
                "current_value": value,
                "recovery_threshold": rule.lower_threshold,
                "alert_type": "threshold_recovery"
            }
        )
        
        self.alert_manager.send_alert(alert)
    
    def _send_trend_alert(self, component: str, rule: TrendRule, trend_analysis: Dict):
        """Send trend-based predictive alert."""
        alert = HealthAlert(
            level=rule.alert_level,
            component=component,
            message=(
                f"Concerning trend detected: {rule.metric_name} increasing at "
                f"{trend_analysis['slope']:.2f}/min, projected to reach "
                f"{trend_analysis['projected_value']:.2f} in {rule.forecast_minutes} minutes"
            ),
            context={
                "metric_name": rule.metric_name,
                "current_value": trend_analysis["current_value"],
                "projected_value": trend_analysis["projected_value"],
                "trend_slope": trend_analysis["slope"],
                "correlation": trend_analysis["correlation"],
                "forecast_minutes": rule.forecast_minutes,
                "alert_type": "trend_prediction"
            }
        )
        
        # Check for escalation
        escalated_alert = self._check_escalation(component, alert)
        self.alert_manager.send_alert(escalated_alert or alert)
    
    def _check_escalation(self, component: str, alert: HealthAlert) -> Optional[HealthAlert]:
        """Check if alert should be escalated based on escalation rules."""
        import time
        
        current_time = time.time()
        
        for rule in self.escalation_rules:
            if not rule.enabled:
                continue
            
            if (alert.level == rule.initial_level and
                self.alert_manager._matches_pattern(component, rule.component_pattern)):
                
                escalation_key = f"{component}:{rule.initial_level.value}"
                
                with self._lock:
                    if escalation_key not in self.escalation_counters:
                        self.escalation_counters[escalation_key] = {
                            "count": 0,
                            "first_occurrence": current_time,
                            "last_escalation": 0
                        }
                    
                    counter = self.escalation_counters[escalation_key]
                    
                    # Reset counter if time window has passed
                    if current_time - counter["first_occurrence"] > rule.time_window_minutes * 60:
                        counter["count"] = 0
                        counter["first_occurrence"] = current_time
                    
                    counter["count"] += 1
                    
                    # Check if escalation is needed
                    if (counter["count"] >= rule.failure_count_threshold and
                        current_time - counter["last_escalation"] > rule.escalation_cooldown_minutes * 60):
                        
                        counter["last_escalation"] = current_time
                        
                        # Create escalated alert
                        escalated_alert = HealthAlert(
                            level=rule.escalated_level,
                            component=alert.component,
                            message=f"ESCALATED: {alert.message} (repeated {counter['count']} times)",
                            context={
                                **alert.context,
                                "escalation_reason": "repeated_failures",
                                "failure_count": counter["count"],
                                "time_window_minutes": rule.time_window_minutes,
                                "original_level": rule.initial_level.value,
                                "escalated_level": rule.escalated_level.value
                            },
                            correlation_id=alert.correlation_id
                        )
                        
                        return escalated_alert
        
        return None
    
    def add_threshold_rule(self, rule: ThresholdRule):
        """Add a new threshold rule."""
        with self._lock:
            self.threshold_rules.append(rule)
        
        self.logger.info(
            "threshold_rule_added",
            extra={
                "extra": {
                    "metric_name": rule.metric_name,
                    "component_pattern": rule.component_pattern,
                    "upper_threshold": rule.upper_threshold,
                    "lower_threshold": rule.lower_threshold,
                    "alert_level": rule.alert_level.value
                }
            }
        )
    
    def add_trend_rule(self, rule: TrendRule):
        """Add a new trend rule."""
        with self._lock:
            self.trend_rules.append(rule)
        
        self.logger.info(
            "trend_rule_added",
            extra={
                "extra": {
                    "metric_name": rule.metric_name,
                    "component_pattern": rule.component_pattern,
                    "trend_threshold": rule.trend_threshold,
                    "alert_level": rule.alert_level.value
                }
            }
        )
    
    def add_escalation_rule(self, rule: EscalationRule):
        """Add a new escalation rule."""
        with self._lock:
            self.escalation_rules.append(rule)
        
        self.logger.info(
            "escalation_rule_added",
            extra={
                "extra": {
                    "component_pattern": rule.component_pattern,
                    "initial_level": rule.initial_level.value,
                    "escalated_level": rule.escalated_level.value,
                    "failure_threshold": rule.failure_count_threshold
                }
            }
        )
    
    def get_intelligent_alerting_statistics(self) -> Dict[str, Any]:
        """Get statistics about intelligent alerting."""
        with self._lock:
            return {
                "threshold_rules": len(self.threshold_rules),
                "trend_rules": len(self.trend_rules),
                "escalation_rules": len(self.escalation_rules),
                "active_threshold_states": len([s for s in self.threshold_states.values() if s]),
                "escalation_counters": len(self.escalation_counters),
                "metrics_tracked": len(self.metric_history),
                "total_metric_points": sum(len(history) for history in self.metric_history.values())
            }


# Global intelligent alerting engine
intelligent_alerting_engine = None


def get_intelligent_alerting_engine() -> IntelligentAlertingEngine:
    """Get the global intelligent alerting engine instance."""
    global intelligent_alerting_engine
    if intelligent_alerting_engine is None:
        intelligent_alerting_engine = IntelligentAlertingEngine(get_alert_manager())
    return intelligent_alerting_engine