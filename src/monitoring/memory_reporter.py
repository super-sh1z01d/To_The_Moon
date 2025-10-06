"""
Memory usage reporting and analysis system.

This module provides detailed memory usage reporting, trend analysis,
and automated reporting for memory management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

from .memory_manager import get_memory_manager, MemoryUsageSnapshot, MemoryOptimizationResult

log = logging.getLogger("memory_reporter")


@dataclass
class MemoryReport:
    """Comprehensive memory usage report."""
    timestamp: datetime
    report_period_hours: float
    
    # Current status
    current_usage_mb: float
    current_usage_percent: float
    current_available_mb: float
    
    # Thresholds
    warning_threshold_mb: float
    critical_threshold_mb: float
    
    # Trends over report period
    average_usage_mb: float
    peak_usage_mb: float
    min_usage_mb: float
    usage_trend: str  # "increasing", "decreasing", "stable"
    
    # Optimization activity
    optimizations_count: int
    total_memory_recovered_mb: float
    most_effective_optimization: Optional[str]
    
    # Alerts and issues
    leak_detections: int
    threshold_violations: int
    auto_adjustments: int
    
    # Recommendations
    recommendations: List[str]
    
    # Raw data
    usage_samples: int
    optimization_history: List[Dict[str, Any]]


class MemoryReporter:
    """
    Memory usage reporter with trend analysis and recommendations.
    """
    
    def __init__(self):
        self.memory_manager = get_memory_manager()
        
    def generate_report(self, hours: float = 24.0) -> MemoryReport:
        """
        Generate comprehensive memory usage report for the specified period.
        
        Args:
            hours: Number of hours to analyze (default: 24 hours)
            
        Returns:
            MemoryReport with detailed analysis
        """
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        # Get current memory statistics
        stats = self.memory_manager.get_memory_statistics()
        current_usage = stats['current_usage']
        thresholds = stats['thresholds']
        
        # Analyze usage history
        usage_analysis = self._analyze_usage_history(start_time, now)
        
        # Analyze optimization history
        optimization_analysis = self._analyze_optimization_history(start_time, now)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            current_usage, thresholds, usage_analysis, optimization_analysis
        )
        
        # Count issues
        leak_detections = self._count_leak_detections(start_time, now)
        threshold_violations = self._count_threshold_violations(start_time, now)
        auto_adjustments = self._count_auto_adjustments(start_time, now)
        
        return MemoryReport(
            timestamp=now,
            report_period_hours=hours,
            
            # Current status
            current_usage_mb=current_usage['used_mb'],
            current_usage_percent=current_usage['percent_used'],
            current_available_mb=current_usage['available_mb'],
            
            # Thresholds
            warning_threshold_mb=thresholds['warning_mb'],
            critical_threshold_mb=thresholds['critical_mb'],
            
            # Trends
            average_usage_mb=usage_analysis['average_mb'],
            peak_usage_mb=usage_analysis['peak_mb'],
            min_usage_mb=usage_analysis['min_mb'],
            usage_trend=usage_analysis['trend'],
            
            # Optimization activity
            optimizations_count=optimization_analysis['count'],
            total_memory_recovered_mb=optimization_analysis['total_recovered_mb'],
            most_effective_optimization=optimization_analysis['most_effective'],
            
            # Issues
            leak_detections=leak_detections,
            threshold_violations=threshold_violations,
            auto_adjustments=auto_adjustments,
            
            # Recommendations
            recommendations=recommendations,
            
            # Raw data
            usage_samples=usage_analysis['samples'],
            optimization_history=optimization_analysis['history']
        )
    
    def _analyze_usage_history(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze memory usage history for the specified period."""
        usage_history = list(self.memory_manager.usage_history)
        
        # Filter by time period
        period_usage = [
            snapshot for snapshot in usage_history
            if start_time <= snapshot.timestamp <= end_time
        ]
        
        if not period_usage:
            return {
                'samples': 0,
                'average_mb': 0.0,
                'peak_mb': 0.0,
                'min_mb': 0.0,
                'trend': 'unknown'
            }
        
        usage_values = [s.used_mb for s in period_usage]
        
        # Calculate statistics
        average_mb = sum(usage_values) / len(usage_values)
        peak_mb = max(usage_values)
        min_mb = min(usage_values)
        
        # Determine trend
        trend = self._calculate_trend(period_usage)
        
        return {
            'samples': len(period_usage),
            'average_mb': average_mb,
            'peak_mb': peak_mb,
            'min_mb': min_mb,
            'trend': trend
        }
    
    def _analyze_optimization_history(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze memory optimization history for the specified period."""
        optimization_history = self.memory_manager.optimization_history
        
        # Filter by time period
        period_optimizations = [
            opt for opt in optimization_history
            if start_time <= opt.timestamp <= end_time
        ]
        
        if not period_optimizations:
            return {
                'count': 0,
                'total_recovered_mb': 0.0,
                'most_effective': None,
                'history': []
            }
        
        # Calculate total recovery
        total_recovered = sum(opt.recovered_mb for opt in period_optimizations if opt.recovered_mb > 0)
        
        # Find most effective optimization
        most_effective = None
        if period_optimizations:
            best_opt = max(period_optimizations, key=lambda x: x.recovered_mb if x.recovered_mb > 0 else 0)
            if best_opt.recovered_mb > 0:
                most_effective = f"{best_opt.recovered_mb:.1f}MB recovered via {', '.join(best_opt.actions_taken[:2])}"
        
        # Convert to serializable format
        history = [
            {
                'timestamp': opt.timestamp.isoformat(),
                'recovered_mb': opt.recovered_mb,
                'success': opt.success,
                'actions_count': len(opt.actions_taken)
            }
            for opt in period_optimizations
        ]
        
        return {
            'count': len(period_optimizations),
            'total_recovered_mb': total_recovered,
            'most_effective': most_effective,
            'history': history
        }
    
    def _calculate_trend(self, usage_snapshots: List[MemoryUsageSnapshot]) -> str:
        """Calculate memory usage trend from snapshots."""
        if len(usage_snapshots) < 3:
            return "insufficient_data"
        
        # Use first and last third of samples to determine trend
        third = len(usage_snapshots) // 3
        if third < 1:
            return "insufficient_data"
        
        early_samples = usage_snapshots[:third]
        late_samples = usage_snapshots[-third:]
        
        early_avg = sum(s.used_mb for s in early_samples) / len(early_samples)
        late_avg = sum(s.used_mb for s in late_samples) / len(late_samples)
        
        # Calculate percentage change
        change_percent = ((late_avg - early_avg) / early_avg) * 100
        
        if change_percent > 5:
            return "increasing"
        elif change_percent < -5:
            return "decreasing"
        else:
            return "stable"
    
    def _count_leak_detections(self, start_time: datetime, end_time: datetime) -> int:
        """Count memory leak detections in the period."""
        # This would need to be implemented based on how leak detection alerts are stored
        # For now, return 0 as we don't have persistent alert storage
        return 0
    
    def _count_threshold_violations(self, start_time: datetime, end_time: datetime) -> int:
        """Count threshold violations in the period."""
        # This would need to be implemented based on alert history
        # For now, return 0 as we don't have persistent alert storage
        return 0
    
    def _count_auto_adjustments(self, start_time: datetime, end_time: datetime) -> int:
        """Count automatic threshold adjustments in the period."""
        # This would need to be implemented based on adjustment history
        # For now, return 0 as we don't have persistent adjustment storage
        return 0
    
    def _generate_recommendations(
        self, 
        current_usage: Dict[str, Any], 
        thresholds: Dict[str, Any],
        usage_analysis: Dict[str, Any],
        optimization_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate memory management recommendations based on analysis."""
        recommendations = []
        
        # Current usage recommendations
        usage_percent = (current_usage['used_mb'] / current_usage['total_mb']) * 100
        
        if usage_percent > 80:
            recommendations.append("System memory usage is high (>80%). Consider adding more RAM or optimizing memory-intensive processes.")
        elif usage_percent < 10:
            recommendations.append("System memory usage is very low (<10%). Memory thresholds could be increased for better resource utilization.")
        
        # Threshold recommendations
        warning_percent = (thresholds['warning_mb'] / current_usage['total_mb']) * 100
        critical_percent = (thresholds['critical_mb'] / current_usage['total_mb']) * 100
        
        if warning_percent < 30:
            recommendations.append(f"Warning threshold is low ({warning_percent:.1f}% of total memory). Consider increasing for better early warning.")
        
        if critical_percent < 40:
            recommendations.append(f"Critical threshold is low ({critical_percent:.1f}% of total memory). Consider increasing to prevent false alarms.")
        
        # Trend recommendations
        if usage_analysis['trend'] == 'increasing':
            recommendations.append("Memory usage is trending upward. Monitor for potential memory leaks and consider proactive cleanup.")
        elif usage_analysis['trend'] == 'decreasing':
            recommendations.append("Memory usage is trending downward. Recent optimizations may be effective.")
        
        # Optimization recommendations
        if optimization_analysis['count'] == 0:
            recommendations.append("No memory optimizations performed recently. Consider running periodic cleanup.")
        elif optimization_analysis['total_recovered_mb'] > 100:
            recommendations.append(f"Memory optimizations recovered {optimization_analysis['total_recovered_mb']:.1f}MB. Consider more frequent cleanup.")
        
        # Peak usage recommendations
        if usage_analysis['peak_mb'] > thresholds['critical_mb']:
            recommendations.append("Peak memory usage exceeded critical threshold. Investigate high-memory periods.")
        
        if not recommendations:
            recommendations.append("Memory usage appears healthy. Continue current monitoring practices.")
        
        return recommendations
    
    def log_memory_report(self, hours: float = 1.0):
        """Generate and log a memory report."""
        try:
            report = self.generate_report(hours)
            
            log.info(
                "memory_usage_report",
                extra={
                    "report_period_hours": report.report_period_hours,
                    "current_usage_mb": report.current_usage_mb,
                    "current_usage_percent": report.current_usage_percent,
                    "usage_trend": report.usage_trend,
                    "optimizations_count": report.optimizations_count,
                    "total_recovered_mb": report.total_memory_recovered_mb,
                    "recommendations_count": len(report.recommendations),
                    "usage_samples": report.usage_samples
                }
            )
            
            # Log recommendations if any
            if report.recommendations:
                log.info(
                    "memory_recommendations",
                    extra={
                        "recommendations": report.recommendations
                    }
                )
                
        except Exception as e:
            log.error(
                "memory_report_generation_failed",
                extra={"error": str(e)},
                exc_info=True
            )


# Global memory reporter instance
_memory_reporter = None


def get_memory_reporter() -> MemoryReporter:
    """Get the global memory reporter instance."""
    global _memory_reporter
    if _memory_reporter is None:
        _memory_reporter = MemoryReporter()
    return _memory_reporter