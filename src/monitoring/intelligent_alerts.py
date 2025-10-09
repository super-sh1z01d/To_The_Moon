"""
Intelligent Alert Management System.

Provides:
- Alert grouping and summary notifications
- Alert resolution tracking
- Intelligent threshold adjustment suggestions
- Alert escalation management
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from src.monitoring.models import HealthAlert, AlertLevel

log = logging.getLogger("intelligent_alerts")


@dataclass
class AlertGroup:
    """Group of similar alerts."""
    group_id: str
    alert_type: str
    component_pattern: str
    alerts: List[HealthAlert] = field(default_factory=list)
    first_occurrence: datetime = field(default_factory=datetime.utcnow)
    last_occurrence: datetime = field(default_factory=datetime.utcnow)
    count: int = 0
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def add_alert(self, alert: HealthAlert):
        """Add alert to group."""
        self.alerts.append(alert)
        self.count += 1
        self.last_occurrence = datetime.utcnow()
    
    def mark_resolved(self):
        """Mark group as resolved."""
        self.resolved = True
        self.resolved_at = datetime.utcnow()
    
    def get_summary(self) -> str:
        """Get summary of alert group."""
        duration = (self.last_occurrence - self.first_occurrence).total_seconds() / 60
        return (
            f"Alert Group: {self.alert_type}\n"
            f"Component: {self.component_pattern}\n"
            f"Count: {self.count} occurrences\n"
            f"Duration: {duration:.1f} minutes\n"
            f"Status: {'Resolved' if self.resolved else 'Active'}"
        )


@dataclass
class ThresholdSuggestion:
    """Suggestion for threshold adjustment."""
    component: str
    metric: str
    current_threshold: float
    suggested_threshold: float
    reason: str
    confidence: float  # 0.0 to 1.0
    based_on_samples: int


class IntelligentAlertManager:
    """Intelligent alert management with grouping and learning."""
    
    def __init__(self):
        self._alert_groups: Dict[str, AlertGroup] = {}
        self._threshold_history: Dict[str, List[float]] = defaultdict(list)
        self._alert_patterns: Dict[str, int] = defaultdict(int)
        self._maintenance_mode = False
        self._maintenance_until: Optional[datetime] = None
        
    def group_alert(self, alert: HealthAlert) -> Optional[AlertGroup]:
        """
        Group similar alerts together.
        
        Returns existing group if alert matches, or creates new group.
        """
        # Generate group key based on alert type and component
        group_key = f"{alert.component}:{alert.message[:50]}"
        
        if group_key in self._alert_groups:
            group = self._alert_groups[group_key]
            if not group.resolved:
                group.add_alert(alert)
                return group
        
        # Create new group
        new_group = AlertGroup(
            group_id=group_key,
            alert_type=alert.message[:50],
            component_pattern=alert.component
        )
        new_group.add_alert(alert)
        self._alert_groups[group_key] = new_group
        
        return new_group
    
    def should_send_alert(self, group: AlertGroup) -> bool:
        """
        Determine if alert should be sent based on grouping logic.
        
        Sends:
        - First alert immediately
        - Summary after 5 occurrences
        - Summary every 10 occurrences after that
        """
        if self._maintenance_mode:
            return False
        
        count = group.count
        
        # First alert
        if count == 1:
            return True
        
        # Summary at 5, 10, 20, 50, 100, etc.
        if count in [5, 10, 20, 50, 100] or (count > 100 and count % 100 == 0):
            return True
        
        return False
    
    def get_alert_summary(self, group: AlertGroup) -> str:
        """Get formatted summary for alert group."""
        if group.count == 1:
            return group.alerts[0].message
        
        return (
            f"🔔 Alert Summary\n\n"
            f"{group.get_summary()}\n\n"
            f"Latest: {group.alerts[-1].message}"
        )
    
    def mark_resolved(self, component: str, alert_type: str) -> Optional[AlertGroup]:
        """Mark alert group as resolved."""
        group_key = f"{component}:{alert_type[:50]}"
        
        if group_key in self._alert_groups:
            group = self._alert_groups[group_key]
            group.mark_resolved()
            
            log.info(
                "alert_group_resolved",
                extra={
                    "group_id": group.group_id,
                    "count": group.count,
                    "duration_minutes": (
                        (group.resolved_at - group.first_occurrence).total_seconds() / 60
                    )
                }
            )
            
            return group
        
        return None
    
    def get_resolution_notification(self, group: AlertGroup) -> str:
        """Get formatted resolution notification."""
        duration = (group.resolved_at - group.first_occurrence).total_seconds() / 60
        
        return (
            f"✅ Alert Resolved\n\n"
            f"Type: {group.alert_type}\n"
            f"Component: {group.component_pattern}\n"
            f"Total occurrences: {group.count}\n"
            f"Duration: {duration:.1f} minutes\n"
            f"Resolved at: {group.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def enable_maintenance_mode(self, duration_minutes: int = 60):
        """Enable maintenance mode to suppress alerts."""
        self._maintenance_mode = True
        self._maintenance_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        log.info(
            "maintenance_mode_enabled",
            extra={
                "duration_minutes": duration_minutes,
                "until": self._maintenance_until.isoformat()
            }
        )
    
    def disable_maintenance_mode(self):
        """Disable maintenance mode."""
        self._maintenance_mode = False
        self._maintenance_until = None
        
        log.info("maintenance_mode_disabled")
    
    def check_maintenance_mode(self):
        """Check if maintenance mode should be automatically disabled."""
        if self._maintenance_mode and self._maintenance_until:
            if datetime.utcnow() >= self._maintenance_until:
                self.disable_maintenance_mode()
    
    def record_threshold_value(self, component: str, metric: str, value: float):
        """Record threshold value for analysis."""
        key = f"{component}:{metric}"
        self._threshold_history[key].append(value)
        
        # Keep only last 1000 values
        if len(self._threshold_history[key]) > 1000:
            self._threshold_history[key] = self._threshold_history[key][-1000:]
    
    def suggest_threshold_adjustment(
        self,
        component: str,
        metric: str,
        current_threshold: float
    ) -> Optional[ThresholdSuggestion]:
        """
        Suggest threshold adjustment based on historical data.
        
        Analyzes patterns and suggests new threshold if appropriate.
        """
        key = f"{component}:{metric}"
        history = self._threshold_history.get(key, [])
        
        if len(history) < 100:
            # Not enough data
            return None
        
        # Calculate statistics
        import statistics
        
        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        median = statistics.median(history)
        
        # Check if current threshold is frequently exceeded
        exceeds_count = sum(1 for v in history if v > current_threshold)
        exceed_rate = exceeds_count / len(history)
        
        # Suggest adjustment if threshold is exceeded >50% of the time
        if exceed_rate > 0.5:
            # Suggest threshold at 95th percentile
            sorted_history = sorted(history)
            p95_index = int(len(sorted_history) * 0.95)
            suggested = sorted_history[p95_index]
            
            return ThresholdSuggestion(
                component=component,
                metric=metric,
                current_threshold=current_threshold,
                suggested_threshold=suggested,
                reason=f"Current threshold exceeded {exceed_rate*100:.1f}% of the time",
                confidence=min(exceed_rate, 0.95),
                based_on_samples=len(history)
            )
        
        # Suggest lowering if threshold is rarely exceeded
        if exceed_rate < 0.05:
            # Suggest threshold at 75th percentile
            sorted_history = sorted(history)
            p75_index = int(len(sorted_history) * 0.75)
            suggested = sorted_history[p75_index]
            
            if suggested < current_threshold * 0.8:  # Only if significantly lower
                return ThresholdSuggestion(
                    component=component,
                    metric=metric,
                    current_threshold=current_threshold,
                    suggested_threshold=suggested,
                    reason=f"Current threshold rarely exceeded ({exceed_rate*100:.1f}%)",
                    confidence=0.7,
                    based_on_samples=len(history)
                )
        
        return None
    
    def get_active_groups(self) -> List[AlertGroup]:
        """Get all active (unresolved) alert groups."""
        return [
            group for group in self._alert_groups.values()
            if not group.resolved
        ]
    
    def get_resolved_groups(self, hours: int = 24) -> List[AlertGroup]:
        """Get recently resolved alert groups."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            group for group in self._alert_groups.values()
            if group.resolved and group.resolved_at and group.resolved_at >= cutoff
        ]
    
    def cleanup_old_groups(self, days: int = 7):
        """Remove old resolved alert groups."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        to_remove = [
            key for key, group in self._alert_groups.items()
            if group.resolved and group.resolved_at and group.resolved_at < cutoff
        ]
        
        for key in to_remove:
            del self._alert_groups[key]
        
        log.info(
            "alert_groups_cleaned",
            extra={"removed_count": len(to_remove)}
        )
    
    def get_statistics(self) -> Dict:
        """Get alert management statistics."""
        active_groups = self.get_active_groups()
        resolved_groups = self.get_resolved_groups()
        
        return {
            "active_groups": len(active_groups),
            "resolved_last_24h": len(resolved_groups),
            "total_groups": len(self._alert_groups),
            "maintenance_mode": self._maintenance_mode,
            "maintenance_until": (
                self._maintenance_until.isoformat()
                if self._maintenance_until else None
            )
        }


# Global instance
_intelligent_alert_manager = None


def get_intelligent_alert_manager() -> IntelligentAlertManager:
    """Get global intelligent alert manager instance."""
    global _intelligent_alert_manager
    if _intelligent_alert_manager is None:
        _intelligent_alert_manager = IntelligentAlertManager()
    return _intelligent_alert_manager
