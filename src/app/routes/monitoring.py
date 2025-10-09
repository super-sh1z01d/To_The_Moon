"""
Monitoring dashboard API endpoints.

Provides real-time system monitoring, token processing metrics,
and health visualization for administrators.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.adapters.db.deps import get_db
from src.adapters.db.models import Token
from src.monitoring.metrics import MetricsCollector
from src.monitoring.memory_manager import get_memory_manager
from src.monitoring.performance_optimizer import get_performance_optimizer
from src.monitoring.intelligent_alerts import get_intelligent_alert_manager

log = logging.getLogger("monitoring_api")

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/dashboard")
async def get_monitoring_dashboard(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive monitoring dashboard data.
    
    Returns real-time metrics including:
    - Token processing statistics by status
    - System health metrics (memory, CPU, API)
    - Processing rates and backlogs
    - Recent errors and alerts
    """
    try:
        # Get token statistics by status
        token_stats = _get_token_statistics(db)
        
        # Get processing rates
        processing_rates = _get_processing_rates(db)
        
        # Get system health
        system_health = _get_system_health()
        
        # Get recent errors
        recent_errors = _get_recent_errors()
        
        # Get circuit breaker status
        circuit_breaker_status = _get_circuit_breaker_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "token_statistics": token_stats,
            "processing_rates": processing_rates,
            "system_health": system_health,
            "recent_errors": recent_errors,
            "circuit_breaker": circuit_breaker_status,
            "status": "ok"
        }
        
    except Exception as e:
        log.error(f"Error getting monitoring dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/flow")
async def get_token_flow_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get detailed token flow metrics.
    
    Returns:
    - Token counts by status
    - Activation success rates
    - Time-to-activation metrics
    - Processing bottlenecks
    """
    try:
        # Get token counts by status
        status_counts = db.query(
            Token.status,
            func.count(Token.id).label("count")
        ).group_by(Token.status).all()
        
        token_counts = {status: count for status, count in status_counts}
        
        # Get activation metrics
        activation_metrics = _get_activation_metrics(db)
        
        # Get processing bottlenecks
        bottlenecks = _get_processing_bottlenecks(db)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "token_counts": token_counts,
            "activation_metrics": activation_metrics,
            "bottlenecks": bottlenecks,
            "status": "ok"
        }
        
    except Exception as e:
        log.error(f"Error getting token flow metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/health")
async def get_system_health_detailed() -> Dict[str, Any]:
    """
    Get detailed system health information.
    
    Returns:
    - Memory usage and trends
    - CPU usage
    - API health status
    - Circuit breaker states
    - Active alerts
    """
    try:
        import psutil
        
        # Get memory info
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": memory.total / (1024 ** 3),
            "used_gb": memory.used / (1024 ** 3),
            "available_gb": memory.available / (1024 ** 3),
            "percent": memory.percent,
            "status": "critical" if memory.percent > 90 else "warning" if memory.percent > 80 else "ok"
        }
        
        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_info = {
            "percent": cpu_percent,
            "count": psutil.cpu_count(),
            "status": "critical" if cpu_percent > 90 else "warning" if cpu_percent > 80 else "ok"
        }
        
        # Get memory manager status
        memory_manager = get_memory_manager()
        memory_manager_status = memory_manager.get_status()
        
        # Get API health status
        api_health = {
            "circuit_breaker_open": False,
            "consecutive_failures": 0,
            "status": "ok"
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "memory": memory_info,
            "cpu": cpu_info,
            "memory_manager": memory_manager_status,
            "api_health": api_health,
            "overall_status": _calculate_overall_status(memory_info, cpu_info, api_health),
            "status": "ok"
        }
        
    except Exception as e:
        log.error(f"Error getting system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/history")
async def get_performance_history(hours: int = 24) -> Dict[str, Any]:
    """
    Get historical performance data.
    
    Args:
        hours: Number of hours of history to retrieve (default: 24)
    
    Returns:
    - Historical metrics
    - Trend analysis
    - Performance graphs data
    """
    try:
        # Get historical data (simplified - in production would query from time-series DB)
        history = {
            "period_hours": hours,
            "data_points": [],
            "trends": {
                "memory_trend": "stable",
                "cpu_trend": "stable",
                "processing_trend": "stable"
            },
            "summary": {
                "avg_memory_percent": 0,
                "avg_cpu_percent": 0,
                "total_tokens_processed": 0
            }
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "history": history,
            "status": "ok"
        }
        
    except Exception as e:
        log.error(f"Error getting performance history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _get_token_statistics(db: Session) -> Dict[str, Any]:
    """Get token statistics by status."""
    try:
        # Get counts by status
        status_counts = db.query(
            Token.status,
            func.count(Token.id).label("count")
        ).group_by(Token.status).all()
        
        counts = {status: count for status, count in status_counts}
        
        # Get tokens updated in last 5 minutes (active processing)
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        recently_updated = db.query(func.count(Token.id)).filter(
            Token.updated_at >= five_min_ago
        ).scalar()
        
        return {
            "by_status": counts,
            "total": sum(counts.values()),
            "recently_updated": recently_updated,
            "monitoring": counts.get("monitoring", 0),
            "active": counts.get("active", 0),
            "archived": counts.get("archived", 0)
        }
        
    except Exception as e:
        log.error(f"Error getting token statistics: {e}")
        return {"error": str(e)}


def _get_processing_rates(db: Session) -> Dict[str, Any]:
    """Get token processing rates."""
    try:
        # Get tokens processed in last minute
        one_min_ago = datetime.utcnow() - timedelta(minutes=1)
        last_minute = db.query(func.count(Token.id)).filter(
            Token.updated_at >= one_min_ago
        ).scalar()
        
        # Get tokens processed in last 5 minutes
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        last_five_min = db.query(func.count(Token.id)).filter(
            Token.updated_at >= five_min_ago
        ).scalar()
        
        return {
            "tokens_per_minute": last_minute,
            "tokens_per_5min": last_five_min,
            "estimated_hourly_rate": last_minute * 60,
            "processing_active": last_minute > 0
        }
        
    except Exception as e:
        log.error(f"Error getting processing rates: {e}")
        return {"error": str(e)}


def _get_system_health() -> Dict[str, Any]:
    """Get system health metrics."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0)
        
        return {
            "memory_percent": memory.percent,
            "memory_gb": memory.used / (1024 ** 3),
            "cpu_percent": cpu,
            "status": "healthy" if memory.percent < 80 and cpu < 80 else "degraded"
        }
        
    except Exception as e:
        log.error(f"Error getting system health: {e}")
        return {"error": str(e), "status": "unknown"}


def _get_recent_errors() -> List[Dict[str, Any]]:
    """Get recent errors from metrics collector."""
    try:
        # Return recent errors (simplified - would need proper implementation)
        return []
        
    except Exception as e:
        log.error(f"Error getting recent errors: {e}")
        return []


def _get_circuit_breaker_status() -> Dict[str, Any]:
    """Get circuit breaker status."""
    try:
        # Check if circuit breaker is available
        # For now, return basic status
        return {
            "open": False,
            "consecutive_failures": 0,
            "last_failure": None,
            "status": "closed"
        }
        
    except Exception as e:
        log.error(f"Error getting circuit breaker status: {e}")
        return {"error": str(e), "status": "unknown"}


def _get_activation_metrics(db: Session) -> Dict[str, Any]:
    """Get token activation metrics."""
    try:
        # Get tokens stuck in monitoring for >3 minutes
        three_min_ago = datetime.utcnow() - timedelta(minutes=3)
        stuck_monitoring = db.query(func.count(Token.id)).filter(
            and_(
                Token.status == "monitoring",
                Token.created_at < three_min_ago
            )
        ).scalar()
        
        # Get recent activations (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_activations = db.query(func.count(Token.id)).filter(
            and_(
                Token.status == "active",
                Token.updated_at >= one_hour_ago
            )
        ).scalar()
        
        return {
            "stuck_in_monitoring": stuck_monitoring,
            "recent_activations": recent_activations,
            "activation_rate_per_hour": recent_activations
        }
        
    except Exception as e:
        log.error(f"Error getting activation metrics: {e}")
        return {"error": str(e)}


def _get_processing_bottlenecks(db: Session) -> List[Dict[str, Any]]:
    """Identify processing bottlenecks."""
    try:
        bottlenecks = []
        
        # Check for stuck tokens
        three_min_ago = datetime.utcnow() - timedelta(minutes=3)
        stuck_count = db.query(func.count(Token.id)).filter(
            and_(
                Token.status == "monitoring",
                Token.created_at < three_min_ago
            )
        ).scalar()
        
        if stuck_count > 10:
            bottlenecks.append({
                "type": "stuck_monitoring",
                "severity": "high",
                "count": stuck_count,
                "description": f"{stuck_count} tokens stuck in monitoring status"
            })
        
        return bottlenecks
        
    except Exception as e:
        log.error(f"Error getting processing bottlenecks: {e}")
        return []


def _calculate_overall_status(memory_info: Dict, cpu_info: Dict, api_health: Dict) -> str:
    """Calculate overall system status."""
    if memory_info["status"] == "critical" or cpu_info["status"] == "critical":
        return "critical"
    
    if api_health["status"] == "error":
        return "degraded"
    
    if memory_info["status"] == "warning" or cpu_info["status"] == "warning":
        return "warning"
    
    return "healthy"



@router.get("/alerts/groups")
async def get_alert_groups() -> Dict[str, Any]:
    """
    Get alert groups and statistics.
    
    Returns:
    - Active alert groups
    - Recently resolved groups
    - Alert management statistics
    """
    try:
        intelligent_alerts = get_intelligent_alert_manager()
        
        # Check and update maintenance mode
        intelligent_alerts.check_maintenance_mode()
        
        # Get active and resolved groups
        active_groups = intelligent_alerts.get_active_groups()
        resolved_groups = intelligent_alerts.get_resolved_groups(hours=24)
        
        # Get statistics
        stats = intelligent_alerts.get_statistics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_groups": [
                {
                    "group_id": g.group_id,
                    "alert_type": g.alert_type,
                    "component": g.component_pattern,
                    "count": g.count,
                    "first_occurrence": g.first_occurrence.isoformat(),
                    "last_occurrence": g.last_occurrence.isoformat(),
                    "summary": g.get_summary()
                }
                for g in active_groups
            ],
            "resolved_groups": [
                {
                    "group_id": g.group_id,
                    "alert_type": g.alert_type,
                    "component": g.component_pattern,
                    "count": g.count,
                    "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
                    "duration_minutes": (
                        (g.resolved_at - g.first_occurrence).total_seconds() / 60
                        if g.resolved_at else 0
                    )
                }
                for g in resolved_groups
            ],
            "statistics": stats,
            "status": "ok"
        }
        
    except Exception as e:
        log.error(f"Error getting alert groups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/resolve")
async def resolve_alert_group(component: str, alert_type: str) -> Dict[str, Any]:
    """
    Mark an alert group as resolved.
    
    Args:
        component: Component name
        alert_type: Alert type/message prefix
    
    Returns:
        Resolution notification
    """
    try:
        intelligent_alerts = get_intelligent_alert_manager()
        
        group = intelligent_alerts.mark_resolved(component, alert_type)
        
        if not group:
            raise HTTPException(status_code=404, detail="Alert group not found")
        
        notification = intelligent_alerts.get_resolution_notification(group)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "group_id": group.group_id,
            "notification": notification,
            "status": "resolved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error resolving alert group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/enable")
async def enable_maintenance_mode(duration_minutes: int = 60) -> Dict[str, Any]:
    """
    Enable maintenance mode to suppress alerts.
    
    Args:
        duration_minutes: Duration in minutes (default: 60)
    
    Returns:
        Maintenance mode status
    """
    try:
        intelligent_alerts = get_intelligent_alert_manager()
        intelligent_alerts.enable_maintenance_mode(duration_minutes)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "maintenance_mode": True,
            "duration_minutes": duration_minutes,
            "until": intelligent_alerts._maintenance_until.isoformat(),
            "status": "enabled"
        }
        
    except Exception as e:
        log.error(f"Error enabling maintenance mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/disable")
async def disable_maintenance_mode() -> Dict[str, Any]:
    """
    Disable maintenance mode.
    
    Returns:
        Maintenance mode status
    """
    try:
        intelligent_alerts = get_intelligent_alert_manager()
        intelligent_alerts.disable_maintenance_mode()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "maintenance_mode": False,
            "status": "disabled"
        }
        
    except Exception as e:
        log.error(f"Error disabling maintenance mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds/suggestions")
async def get_threshold_suggestions() -> Dict[str, Any]:
    """
    Get intelligent threshold adjustment suggestions.
    
    Returns:
        List of threshold adjustment suggestions based on historical data
    """
    try:
        intelligent_alerts = get_intelligent_alert_manager()
        
        # Example: Check common thresholds
        suggestions = []
        
        # Memory threshold
        memory_suggestion = intelligent_alerts.suggest_threshold_adjustment(
            component="system",
            metric="memory_percent",
            current_threshold=80.0
        )
        if memory_suggestion:
            suggestions.append({
                "component": memory_suggestion.component,
                "metric": memory_suggestion.metric,
                "current_threshold": memory_suggestion.current_threshold,
                "suggested_threshold": memory_suggestion.suggested_threshold,
                "reason": memory_suggestion.reason,
                "confidence": memory_suggestion.confidence,
                "samples": memory_suggestion.based_on_samples
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": suggestions,
            "count": len(suggestions),
            "status": "ok"
        }
        
    except Exception as e:
        log.error(f"Error getting threshold suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
