"""
Health monitoring endpoints for system stability tracking.

Provides comprehensive health status information for all system components
including scheduler, resources, APIs, and overall system health.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.monitoring.health_monitor import health_monitor
from src.monitoring.circuit_breaker import get_all_circuit_breakers, get_circuit_breaker_stats
from src.monitoring.retry_manager import get_all_retry_managers, get_retry_manager_stats
from src.monitoring.models import HealthStatus
from src.monitoring.alert_manager import get_alert_manager
from src.adapters.services.resilient_dexscreener_client import get_resilient_dexscreener_client

log = logging.getLogger("health_endpoints")

router = APIRouter(prefix="/health", tags=["Health Monitoring"])


class HealthResponse(BaseModel):
    """Base health response model."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    message: Optional[str] = None


class DetailedHealthResponse(HealthResponse):
    """Detailed health response with component breakdown."""
    components: Dict[str, Any]
    alerts: list[Dict[str, Any]]
    statistics: Dict[str, Any]


@router.get("/", response_model=HealthResponse)
async def get_basic_health():
    """
    Get basic system health status.
    
    Returns a simple health check suitable for load balancers and uptime monitoring.
    """
    try:
        # Get basic health information
        system_health = await health_monitor.get_comprehensive_health_async()
        
        return HealthResponse(
            status=system_health.overall_status.value,
            timestamp=system_health.timestamp,
            uptime_seconds=system_health.uptime_seconds,
            message="System operational" if system_health.overall_status == HealthStatus.HEALTHY else "System degraded"
        )
    except Exception as e:
        log.error(f"Error getting basic health: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/detailed", response_model=DetailedHealthResponse)
async def get_detailed_health():
    """
    Get comprehensive system health with detailed component information.
    
    Includes scheduler health, resource usage, API status, and performance metrics.
    """
    try:
        # Get comprehensive health information
        system_health = await health_monitor.get_comprehensive_health_async()
        
        # Build component details
        components = {
            "scheduler": {
                "status": system_health.scheduler.status.value,
                "hot_group_last_run": system_health.scheduler.hot_group_last_run.isoformat() if system_health.scheduler.hot_group_last_run else None,
                "cold_group_last_run": system_health.scheduler.cold_group_last_run.isoformat() if system_health.scheduler.cold_group_last_run else None,
                "hot_group_processing_time": system_health.scheduler.hot_group_processing_time,
                "cold_group_processing_time": system_health.scheduler.cold_group_processing_time,
                "tokens_processed_per_minute": system_health.scheduler.tokens_processed_per_minute,
                "error_rate": system_health.scheduler.error_rate,
                "active_jobs": system_health.scheduler.active_jobs,
                "failed_jobs_last_hour": system_health.scheduler.failed_jobs_last_hour
            },
            "resources": {
                "status": system_health.resources.status.value,
                "memory_usage_mb": system_health.resources.memory_usage_mb,
                "memory_usage_percent": system_health.resources.memory_usage_percent,
                "cpu_usage_percent": system_health.resources.cpu_usage_percent,
                "disk_usage_percent": system_health.resources.disk_usage_percent,
                "database_connections": system_health.resources.database_connections,
                "max_database_connections": system_health.resources.max_database_connections,
                "open_file_descriptors": system_health.resources.open_file_descriptors,
                "max_file_descriptors": system_health.resources.max_file_descriptors
            },
            "apis": {}
        }
        
        # Add API health information
        for api_name, api_health in system_health.apis.items():
            components["apis"][api_name] = {
                "status": api_health.status.value,
                "average_response_time": api_health.average_response_time,
                "p95_response_time": api_health.p95_response_time,
                "error_rate": api_health.error_rate,
                "circuit_breaker_state": api_health.circuit_breaker_state.value,
                "cache_hit_rate": api_health.cache_hit_rate,
                "requests_per_minute": api_health.requests_per_minute,
                "last_successful_call": api_health.last_successful_call.isoformat() if api_health.last_successful_call else None,
                "consecutive_failures": api_health.consecutive_failures
            }
        
        # Format alerts
        alerts = []
        for alert in system_health.get_all_alerts():
            alerts.append({
                "level": alert.level.value,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat(),
                "correlation_id": alert.correlation_id,
                "context": alert.context
            })
        
        # Get statistics
        statistics = {
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["level"] == "critical"]),
            "uptime_seconds": system_health.uptime_seconds,
            "last_restart": system_health.last_restart.isoformat() if system_health.last_restart else None
        }
        
        return DetailedHealthResponse(
            status=system_health.overall_status.value,
            timestamp=system_health.timestamp,
            uptime_seconds=system_health.uptime_seconds,
            message=f"System {system_health.overall_status.value} with {len(alerts)} alerts",
            components=components,
            alerts=alerts,
            statistics=statistics
        )
    except Exception as e:
        log.error(f"Error getting detailed health: {e}")
        raise HTTPException(status_code=500, detail="Detailed health check failed")


@router.get("/data-freshness")
async def get_data_freshness():
    """
    Check for stale data that indicates scheduler problems.
    
    Returns alerts if tokens haven't been updated recently.
    """
    try:
        from src.adapters.db.base import SessionLocal
        from src.adapters.repositories.tokens_repo import TokensRepository
        from datetime import timedelta
        
        with SessionLocal() as db:
            repo = TokensRepository(db)
            now = datetime.now(timezone.utc)
            
            # Check active tokens for stale data
            active_tokens = repo.list_by_status("active", limit=50)
            stale_active = []
            
            for token in active_tokens:
                if token.last_updated_at:
                    # Ensure both datetimes are timezone-aware
                    last_updated = token.last_updated_at
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    age_minutes = (now - last_updated).total_seconds() / 60
                    if age_minutes > 30:  # Alert if not updated in 30+ minutes
                        stale_active.append({
                            "symbol": token.symbol or "[no symbol]",
                            "mint": token.mint_address[:8] + "...",
                            "age_minutes": round(age_minutes, 1),
                            "last_updated": token.last_updated_at.isoformat()
                        })
            
            # Check monitoring tokens
            monitoring_tokens = repo.list_by_status("monitoring", limit=50)
            stale_monitoring = []
            
            for token in monitoring_tokens:
                if token.last_updated_at:
                    # Ensure both datetimes are timezone-aware
                    last_updated = token.last_updated_at
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    age_minutes = (now - last_updated).total_seconds() / 60
                    if age_minutes > 60:  # Alert if not updated in 60+ minutes
                        stale_monitoring.append({
                            "symbol": token.symbol or "[no symbol]",
                            "mint": token.mint_address[:8] + "...",
                            "age_minutes": round(age_minutes, 1),
                            "last_updated": token.last_updated_at.isoformat()
                        })
            
            status = "healthy"
            alerts = []
            
            if stale_active:
                status = "degraded"
                alerts.append({
                    "level": "warning",
                    "message": f"{len(stale_active)} active tokens not updated in 30+ minutes",
                    "details": stale_active[:5]  # Show first 5
                })
            
            if stale_monitoring:
                if len(stale_monitoring) > 10:
                    status = "degraded"
                    alerts.append({
                        "level": "warning", 
                        "message": f"{len(stale_monitoring)} monitoring tokens not updated in 60+ minutes",
                        "details": stale_monitoring[:5]  # Show first 5
                    })
            
            return {
                "status": status,
                "active_tokens_checked": len(active_tokens),
                "stale_active_count": len(stale_active),
                "monitoring_tokens_checked": len(monitoring_tokens),
                "stale_monitoring_count": len(stale_monitoring),
                "alerts": alerts,
                "last_check": now.isoformat()
            }
            
    except Exception as e:
        log.error(f"Error checking data freshness: {e}")
        raise HTTPException(status_code=500, detail="Data freshness check failed")


@router.get("/scheduler")
async def get_scheduler_health():
    """
    Get detailed scheduler health information.
    
    Provides specific information about scheduler performance and status.
    """
    try:
        scheduler_health = await health_monitor.monitor_scheduler_health()
        
        return {
            "status": scheduler_health.status.value,
            "hot_group": {
                "last_run": scheduler_health.hot_group_last_run.isoformat() if scheduler_health.hot_group_last_run else None,
                "processing_time": scheduler_health.hot_group_processing_time
            },
            "cold_group": {
                "last_run": scheduler_health.cold_group_last_run.isoformat() if scheduler_health.cold_group_last_run else None,
                "processing_time": scheduler_health.cold_group_processing_time
            },
            "performance": {
                "tokens_processed_per_minute": scheduler_health.tokens_processed_per_minute,
                "error_rate": scheduler_health.error_rate,
                "active_jobs": scheduler_health.active_jobs,
                "failed_jobs_last_hour": scheduler_health.failed_jobs_last_hour
            },
            "alerts": [
                {
                    "level": alert.level.value,
                    "message": alert.message,
                    "component": alert.component,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in scheduler_health.alerts
            ],
            "last_check": scheduler_health.last_check.isoformat()
        }
    except Exception as e:
        log.error(f"Error getting scheduler health: {e}")
        raise HTTPException(status_code=500, detail="Scheduler health check failed")


@router.get("/scheduler-performance")
async def get_scheduler_performance():
    """
    Check scheduler performance and detect overload issues.
    
    Analyzes recent logs for missed jobs and performance problems.
    """
    try:
        import subprocess
        import re
        
        # Get recent scheduler logs
        result = subprocess.run([
            "journalctl", "-u", "tothemoon.service", "--since", "10 minutes ago"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {"status": "unknown", "error": "Could not read logs"}
        
        logs = result.stdout
        
        # Count missed jobs
        missed_jobs = re.findall(r'was missed by (\d+):(\d+):(\d+\.\d+)', logs)
        missed_count = len(missed_jobs)
        
        # Calculate total missed time
        total_missed_seconds = 0
        for hours, minutes, seconds in missed_jobs:
            total_missed_seconds += int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        
        # Count group summaries (successful executions)
        successful_executions = len(re.findall(r'group_summary', logs))
        
        # Determine status
        status = "healthy"
        alerts = []
        
        if missed_count > 5:
            status = "degraded"
            alerts.append({
                "level": "warning",
                "message": f"{missed_count} scheduler jobs missed in last 10 minutes"
            })
        
        if missed_count > 15:
            status = "critical"
            alerts[-1]["level"] = "critical"
        
        if total_missed_seconds > 60:
            status = "degraded"
            alerts.append({
                "level": "warning", 
                "message": f"Total missed time: {total_missed_seconds:.1f} seconds"
            })
        
        return {
            "status": status,
            "missed_jobs_count": missed_count,
            "total_missed_seconds": round(total_missed_seconds, 1),
            "successful_executions": successful_executions,
            "alerts": alerts,
            "last_check": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        log.error(f"Error checking scheduler performance: {e}")
        return {
            "status": "unknown",
            "error": str(e),
            "last_check": datetime.now(timezone.utc).isoformat()
        }


@router.get("/resources")
async def get_resource_health():
    """
    Get system resource health information.
    
    Provides information about CPU, memory, disk usage and system resources.
    """
    try:
        resource_health = await health_monitor.monitor_resource_usage()
        
        return {
            "status": resource_health.status.value,
            "memory": {
                "usage_mb": resource_health.memory_usage_mb,
                "usage_percent": resource_health.memory_usage_percent
            },
            "cpu": {
                "usage_percent": resource_health.cpu_usage_percent
            },
            "disk": {
                "usage_percent": resource_health.disk_usage_percent
            },
            "database": {
                "connections": resource_health.database_connections,
                "max_connections": resource_health.max_database_connections
            },
            "file_descriptors": {
                "open": resource_health.open_file_descriptors,
                "max": resource_health.max_file_descriptors
            },
            "alerts": [
                {
                    "level": alert.level.value,
                    "message": alert.message,
                    "component": alert.component,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in resource_health.alerts
            ],
            "last_check": resource_health.last_check.isoformat()
        }
    except Exception as e:
        log.error(f"Error getting resource health: {e}")
        raise HTTPException(status_code=500, detail="Resource health check failed")


@router.get("/apis")
async def get_apis_health():
    """
    Get external API health information.
    
    Provides information about external API performance and circuit breaker status.
    """
    try:
        # Get API health from health monitor
        api_health = await health_monitor.monitor_api_health("dexscreener")
        
        # Get resilient client stats
        resilient_client = get_resilient_dexscreener_client()
        client_stats = resilient_client.get_stats()
        
        return {
            "dexscreener": {
                "status": api_health.status.value,
                "performance": {
                    "average_response_time": api_health.average_response_time,
                    "p95_response_time": api_health.p95_response_time,
                    "error_rate": api_health.error_rate,
                    "requests_per_minute": api_health.requests_per_minute
                },
                "circuit_breaker": {
                    "state": api_health.circuit_breaker_state.value,
                    "consecutive_failures": api_health.consecutive_failures
                },
                "cache": {
                    "hit_rate": api_health.cache_hit_rate
                },
                "last_successful_call": api_health.last_successful_call.isoformat() if api_health.last_successful_call else None,
                "client_stats": client_stats,
                "alerts": [
                    {
                        "level": alert.level.value,
                        "message": alert.message,
                        "component": alert.component,
                        "timestamp": alert.timestamp.isoformat()
                    }
                    for alert in api_health.alerts
                ],
                "last_check": api_health.last_check.isoformat()
            }
        }
    except Exception as e:
        log.error(f"Error getting API health: {e}")
        raise HTTPException(status_code=500, detail="API health check failed")


@router.get("/circuit-breakers")
async def get_circuit_breakers_status():
    """
    Get status of all circuit breakers in the system.
    
    Provides detailed information about circuit breaker states and statistics.
    """
    try:
        circuit_breakers = get_all_circuit_breakers()
        stats = get_circuit_breaker_stats()
        
        result = {}
        for name, breaker in circuit_breakers.items():
            result[name] = {
                "state": breaker.state.value,
                "is_healthy": breaker.is_closed,
                "failure_rate": breaker.failure_rate,
                "stats": stats.get(name, {})
            }
        
        return {
            "circuit_breakers": result,
            "summary": {
                "total_breakers": len(circuit_breakers),
                "healthy_breakers": len([b for b in circuit_breakers.values() if b.is_closed]),
                "open_breakers": len([b for b in circuit_breakers.values() if b.is_open]),
                "half_open_breakers": len([b for b in circuit_breakers.values() if b.is_half_open])
            }
        }
    except Exception as e:
        log.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail="Circuit breaker status check failed")


@router.get("/retry-managers")
async def get_retry_managers_status():
    """
    Get status of all retry managers in the system.
    
    Provides detailed information about retry statistics and performance.
    """
    try:
        retry_managers = get_all_retry_managers()
        stats = get_retry_manager_stats()
        
        result = {}
        for name, manager in retry_managers.items():
            manager_stats = stats.get(name, {})
            result[name] = {
                "success_rate": manager_stats.get("success_rate", 0),
                "average_attempts": manager_stats.get("average_attempts", 0),
                "stats": manager_stats
            }
        
        return {
            "retry_managers": result,
            "summary": {
                "total_managers": len(retry_managers),
                "total_calls": sum(stats.get(name, {}).get("total_calls", 0) for name in retry_managers.keys()),
                "total_retries": sum(stats.get(name, {}).get("total_retries", 0) for name in retry_managers.keys()),
                "overall_success_rate": sum(stats.get(name, {}).get("success_rate", 0) for name in retry_managers.keys()) / max(len(retry_managers), 1)
            }
        }
    except Exception as e:
        log.error(f"Error getting retry manager status: {e}")
        raise HTTPException(status_code=500, detail="Retry manager status check failed")


@router.get("/alerts")
async def get_system_alerts(
    level: Optional[str] = Query(None, description="Filter alerts by level (info, warning, error, critical)"),
    component: Optional[str] = Query(None, description="Filter alerts by component"),
    limit: int = Query(50, description="Maximum number of alerts to return")
):
    """
    Get system alerts with optional filtering.
    
    Provides recent alerts from all system components with filtering capabilities.
    """
    try:
        system_health = await health_monitor.get_comprehensive_health_async()
        alerts = system_health.get_all_alerts()
        
        # Apply filters
        if level:
            alerts = [alert for alert in alerts if alert.level.value == level.lower()]
        
        if component:
            alerts = [alert for alert in alerts if component.lower() in alert.component.lower()]
        
        # Limit results
        alerts = alerts[:limit]
        
        # Format response
        formatted_alerts = [
            {
                "level": alert.level.value,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat(),
                "correlation_id": alert.correlation_id,
                "context": alert.context
            }
            for alert in alerts
        ]
        
        return {
            "alerts": formatted_alerts,
            "summary": {
                "total_alerts": len(formatted_alerts),
                "critical_alerts": len([a for a in formatted_alerts if a["level"] == "critical"]),
                "error_alerts": len([a for a in formatted_alerts if a["level"] == "error"]),
                "warning_alerts": len([a for a in formatted_alerts if a["level"] == "warning"]),
                "info_alerts": len([a for a in formatted_alerts if a["level"] == "info"])
            },
            "filters_applied": {
                "level": level,
                "component": component,
                "limit": limit
            }
        }
    except Exception as e:
        log.error(f"Error getting system alerts: {e}")
        raise HTTPException(status_code=500, detail="System alerts check failed")


@router.post("/reset")
async def reset_monitoring_stats():
    """
    Reset monitoring statistics and counters.
    
    Clears all accumulated statistics for circuit breakers, retry managers, and health monitors.
    Use with caution as this will lose historical data.
    """
    try:
        # Reset circuit breaker stats
        from src.monitoring.circuit_breaker import reset_all_circuit_breakers
        reset_all_circuit_breakers()
        
        # Reset retry manager stats
        from src.monitoring.retry_manager import reset_all_retry_stats
        reset_all_retry_stats()
        
        # Reset resilient client stats
        resilient_client = get_resilient_dexscreener_client()
        resilient_client.reset_stats()
        
        log.info("Monitoring statistics reset")
        
        return {
            "message": "Monitoring statistics reset successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "reset_components": [
                "circuit_breakers",
                "retry_managers",
                "resilient_client"
            ]
        }
    except Exception as e:
        log.error(f"Error resetting monitoring stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset monitoring statistics")


@router.get("/status")
async def get_health_status_summary():
    """
    Get a quick health status summary.
    
    Provides a concise overview of system health suitable for dashboards.
    """
    try:
        system_health = await health_monitor.get_comprehensive_health_async()
        
        # Count alerts by level
        all_alerts = system_health.get_all_alerts()
        alert_counts = {
            "critical": len([a for a in all_alerts if a.level.value == "critical"]),
            "error": len([a for a in all_alerts if a.level.value == "error"]),
            "warning": len([a for a in all_alerts if a.level.value == "warning"]),
            "info": len([a for a in all_alerts if a.level.value == "info"])
        }
        
        # Get component status summary
        components_status = {
            "scheduler": system_health.scheduler.status.value,
            "resources": system_health.resources.status.value,
            "apis": {name: api.status.value for name, api in system_health.apis.items()}
        }
        
        return {
            "overall_status": system_health.overall_status.value,
            "uptime_seconds": system_health.uptime_seconds,
            "components_status": components_status,
            "alert_counts": alert_counts,
            "timestamp": system_health.timestamp.isoformat(),
            "healthy_components": len([s for s in [system_health.scheduler.status.value, system_health.resources.status.value] + [api.status.value for api in system_health.apis.values()] if s == "healthy"]),
            "total_components": 2 + len(system_health.apis)  # scheduler + resources + APIs
        }
    except Exception as e:
        log.error(f"Error getting health status summary: {e}")
        raise HTTPException(status_code=500, detail="Health status summary failed")


@router.get("/alert-manager")
async def get_alert_manager_status():
    """
    Get Alert Manager status and statistics.
    
    Provides information about alert rules, history, and performance.
    """
    try:
        alert_manager = get_alert_manager()
        stats = alert_manager.get_alert_statistics()
        
        return {
            "alert_manager": {
                "status": "operational",
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        log.error(f"Error getting alert manager status: {e}")
        raise HTTPException(status_code=500, detail="Alert manager status check failed")


@router.post("/alert-manager/cleanup")
async def cleanup_alert_history(
    days_to_keep: int = Query(7, description="Number of days of history to keep")
):
    """
    Clean up old alert history.
    
    Removes alert history older than the specified number of days.
    """
    try:
        if days_to_keep < 1:
            raise HTTPException(status_code=400, detail="days_to_keep must be at least 1")
        
        alert_manager = get_alert_manager()
        removed_count = alert_manager.cleanup_old_history(days_to_keep)
        
        return {
            "message": f"Alert history cleanup completed",
            "removed_count": removed_count,
            "days_kept": days_to_keep,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error cleaning up alert history: {e}")
        raise HTTPException(status_code=500, detail="Alert history cleanup failed")


@router.post("/alert-manager/suppress")
async def suppress_alerts(
    component: str = Query(..., description="Component pattern to suppress"),
    level: str = Query(..., description="Alert level to suppress (info, warning, error, critical)"),
    message_pattern: str = Query(..., description="Message pattern to suppress")
):
    """
    Manually suppress alerts matching the given criteria.
    
    Suppressed alerts will not be sent through alert channels.
    """
    try:
        from src.monitoring.models import AlertLevel
        
        # Validate alert level
        try:
            alert_level = AlertLevel(level.lower())
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid alert level: {level}. Must be one of: info, warning, error, critical"
            )
        
        alert_manager = get_alert_manager()
        alert_manager.suppress_alert(component, alert_level, message_pattern)
        
        return {
            "message": "Alert suppression added successfully",
            "component": component,
            "level": alert_level.value,
            "message_pattern": message_pattern,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error suppressing alerts: {e}")
        raise HTTPException(status_code=500, detail="Alert suppression failed")


@router.delete("/alert-manager/suppress")
async def unsuppress_alerts(
    component: str = Query(..., description="Component pattern to unsuppress"),
    level: str = Query(..., description="Alert level to unsuppress"),
    message_pattern: str = Query(..., description="Message pattern to unsuppress")
):
    """
    Remove manual suppression for alerts matching the given criteria.
    
    Previously suppressed alerts will be sent through alert channels again.
    """
    try:
        from src.monitoring.models import AlertLevel
        
        # Validate alert level
        try:
            alert_level = AlertLevel(level.lower())
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid alert level: {level}. Must be one of: info, warning, error, critical"
            )
        
        alert_manager = get_alert_manager()
        alert_manager.unsuppress_alert(component, alert_level, message_pattern)
        
        return {
            "message": "Alert suppression removed successfully",
            "component": component,
            "level": alert_level.value,
            "message_pattern": message_pattern,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error unsuppressing alerts: {e}")
        raise HTTPException(status_code=500, detail="Alert unsuppression failed")


@router.get("/scheduler/self-healing")
async def get_self_healing_status():
    """
    Get self-healing scheduler status and statistics.
    
    Provides information about restart history, health checks, and recovery actions.
    """
    try:
        from fastapi import Request
        from src.app.main import app
        
        # Get self-healing wrapper from app state
        if not hasattr(app.state, 'self_healing_wrapper'):
            raise HTTPException(status_code=404, detail="Self-healing scheduler not enabled")
        
        wrapper = app.state.self_healing_wrapper
        stats = wrapper.get_restart_statistics()
        
        return {
            "self_healing_scheduler": {
                "enabled": True,
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting self-healing scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Self-healing scheduler status check failed")


@router.post("/scheduler/restart")
async def restart_scheduler(
    restart_type: str = Query("graceful", description="Type of restart: 'graceful' or 'emergency'"),
    reason: str = Query("manual", description="Reason for restart")
):
    """
    Manually restart the scheduler.
    
    Supports both graceful and emergency restart modes.
    """
    try:
        from src.app.main import app
        
        # Get self-healing wrapper from app state
        if not hasattr(app.state, 'self_healing_wrapper'):
            raise HTTPException(status_code=404, detail="Self-healing scheduler not enabled")
        
        wrapper = app.state.self_healing_wrapper
        
        if restart_type.lower() == "graceful":
            success = await wrapper.graceful_restart(reason)
            restart_method = "graceful"
        elif restart_type.lower() == "emergency":
            success = await wrapper.emergency_restart(reason)
            restart_method = "emergency"
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid restart_type. Must be 'graceful' or 'emergency'"
            )
        
        if success:
            return {
                "message": f"Scheduler {restart_method} restart completed successfully",
                "restart_type": restart_method,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Scheduler {restart_method} restart failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error restarting scheduler: {e}")
        raise HTTPException(status_code=500, detail="Scheduler restart failed")


@router.post("/scheduler/health-check")
async def trigger_health_check():
    """
    Manually trigger scheduler health check and recovery.
    
    Performs health assessment and recovery actions if needed.
    """
    try:
        from src.app.main import app
        
        # Get self-healing wrapper from app state
        if not hasattr(app.state, 'self_healing_wrapper'):
            raise HTTPException(status_code=404, detail="Self-healing scheduler not enabled")
        
        wrapper = app.state.self_healing_wrapper
        health_ok = wrapper.check_health_and_recover()
        
        return {
            "message": "Health check completed",
            "health_status": "healthy" if health_ok else "unhealthy",
            "recovery_triggered": not health_ok,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error triggering health check: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/performance")
async def get_performance_metrics():
    """
    Get comprehensive performance metrics and statistics.
    
    Provides detailed performance data for APIs, scheduler groups, and system resources.
    """
    try:
        from src.monitoring.metrics import get_performance_tracker
        
        performance_tracker = get_performance_tracker()
        summary = performance_tracker.get_performance_summary()
        
        return {
            "performance_metrics": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Performance metrics retrieval failed")



@router.get("/performance/api/{service}")
async def get_api_performance(service: str):
    """
    Get performance metrics for a specific API service.
    
    Provides detailed performance statistics including response times, success rates, and trends.
    """
    try:
        from src.monitoring.metrics import get_performance_tracker
        
        performance_tracker = get_performance_tracker()
        stats = performance_tracker.get_api_performance(service)
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"No performance data found for service: {service}")
        
        return {
            "service": service,
            "performance_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting API performance for {service}: {e}")
        raise HTTPException(status_code=500, detail="API performance retrieval failed")


@router.get("/performance/scheduler/{group}")
async def get_scheduler_performance(group: str):
    """
    Get performance metrics for a specific scheduler group.
    
    Provides detailed performance statistics including processing times, success rates, and trends.
    """
    try:
        from src.monitoring.metrics import get_performance_tracker
        
        performance_tracker = get_performance_tracker()
        stats = performance_tracker.get_scheduler_performance(group)
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"No performance data found for scheduler group: {group}")
        
        return {
            "group": group,
            "performance_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting scheduler performance for {group}: {e}")
        raise HTTPException(status_code=500, detail="Scheduler performance retrieval failed")


@router.get("/performance/anomalies")
async def get_performance_anomalies(
    service: Optional[str] = Query(None, description="API service to check for anomalies"),
    group: Optional[str] = Query(None, description="Scheduler group to check for anomalies")
):
    """
    Detect performance anomalies in the system.
    
    Analyzes performance data to identify unusual patterns or degradations.
    """
    try:
        from src.monitoring.metrics import get_performance_tracker
        
        performance_tracker = get_performance_tracker()
        anomalies = performance_tracker.detect_performance_anomalies(service=service, group=group)
        
        return {
            "anomalies": anomalies,
            "filters": {
                "service": service,
                "group": group
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Error detecting performance anomalies: {e}")
        raise HTTPException(status_code=500, detail="Performance anomaly detection failed")


@router.post("/performance/baseline")
async def set_performance_baseline(
    metric_name: str = Query(..., description="Name of the metric to set baseline for"),
    value: float = Query(..., description="Baseline value for the metric")
):
    """
    Set a performance baseline for comparison.
    
    Establishes a baseline value for performance metrics to help detect anomalies.
    """
    try:
        from src.monitoring.metrics import get_performance_tracker
        
        performance_tracker = get_performance_tracker()
        performance_tracker.set_performance_baseline(metric_name, value)
        
        return {
            "message": f"Performance baseline set successfully",
            "metric_name": metric_name,
            "baseline_value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Error setting performance baseline: {e}")
        raise HTTPException(status_code=500, detail="Performance baseline setting failed")


@router.post("/performance/cleanup")
async def cleanup_performance_data(
    max_age_hours: int = Query(24, description="Maximum age of data to keep in hours")
):
    """
    Clean up old performance data.
    
    Removes performance data older than the specified age to prevent memory bloat.
    """
    try:
        if max_age_hours < 1:
            raise HTTPException(status_code=400, detail="max_age_hours must be at least 1")
        
        from src.monitoring.metrics import get_performance_tracker
        
        performance_tracker = get_performance_tracker()
        cleaned_count = performance_tracker.cleanup_old_data(max_age_hours)
        
        return {
            "message": "Performance data cleanup completed",
            "cleaned_records": cleaned_count,
            "max_age_hours": max_age_hours,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error cleaning up performance data: {e}")
        raise HTTPException(status_code=500, detail="Performance data cleanup failed")


@router.get("/load-adjustment")
async def get_load_adjustment_status():
    """
    Get current load-based processing adjustment status.
    
    Provides information about system load, processing adjustments, and feature states.
    """
    try:
        from src.monitoring.metrics import get_load_processor
        
        load_processor = get_load_processor()
        stats = load_processor.get_load_statistics()
        
        return {
            "load_adjustment": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Error getting load adjustment status: {e}")
        raise HTTPException(status_code=500, detail="Load adjustment status retrieval failed")


@router.post("/load-adjustment/process")
async def trigger_load_adjustment():
    """
    Manually trigger load assessment and processing adjustment.
    
    Forces immediate evaluation of system load and adjustment of processing parameters.
    """
    try:
        from src.monitoring.metrics import get_load_processor
        
        load_processor = get_load_processor()
        adjustments = load_processor.process_load_adjustment()
        
        return {
            "message": "Load adjustment processed",
            "adjustments": adjustments,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Error triggering load adjustment: {e}")
        raise HTTPException(status_code=500, detail="Load adjustment processing failed")


@router.post("/load-adjustment/thresholds")
async def update_load_thresholds(
    cpu_warning: Optional[float] = Query(None, description="CPU warning threshold (0-100)"),
    cpu_critical: Optional[float] = Query(None, description="CPU critical threshold (0-100)"),
    memory_warning: Optional[float] = Query(None, description="Memory warning threshold (0-100)"),
    memory_critical: Optional[float] = Query(None, description="Memory critical threshold (0-100)")
):
    """
    Update load adjustment thresholds.
    
    Allows fine-tuning of the thresholds that trigger processing adjustments.
    """
    try:
        # Validate thresholds
        thresholds = {
            "cpu_warning": cpu_warning,
            "cpu_critical": cpu_critical,
            "memory_warning": memory_warning,
            "memory_critical": memory_critical
        }
        
        for name, value in thresholds.items():
            if value is not None:
                if not 0 <= value <= 100:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"{name} must be between 0 and 100"
                    )
        
        # Validate logical relationships
        if cpu_warning is not None and cpu_critical is not None:
            if cpu_warning >= cpu_critical:
                raise HTTPException(
                    status_code=400,
                    detail="CPU warning threshold must be less than critical threshold"
                )
        
        if memory_warning is not None and memory_critical is not None:
            if memory_warning >= memory_critical:
                raise HTTPException(
                    status_code=400,
                    detail="Memory warning threshold must be less than critical threshold"
                )
        
        from src.monitoring.metrics import get_load_processor
        
        load_processor = get_load_processor()
        load_processor.update_thresholds(
            cpu_warning=cpu_warning,
            cpu_critical=cpu_critical,
            memory_warning=memory_warning,
            memory_critical=memory_critical
        )
        
        return {
            "message": "Load thresholds updated successfully",
            "updated_thresholds": {k: v for k, v in thresholds.items() if v is not None},
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating load thresholds: {e}")
        raise HTTPException(status_code=500, detail="Load threshold update failed")


@router.get("/load-adjustment/features")
async def get_feature_status():
    """
    Get current feature enablement status.
    
    Shows which features are currently enabled or disabled based on system load.
    """
    try:
        from src.monitoring.metrics import get_load_processor
        
        load_processor = get_load_processor()
        
        all_features = load_processor.feature_priorities
        enabled_features = [f for f in all_features.keys() if load_processor.is_feature_enabled(f)]
        disabled_features = list(load_processor.disabled_features)
        
        return {
            "feature_status": {
                "enabled_features": enabled_features,
                "disabled_features": disabled_features,
                "feature_priorities": all_features,
                "current_load_level": load_processor.current_load_level,
                "processing_factor": load_processor.current_processing_factor
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Error getting feature status: {e}")
        raise HTTPException(status_code=500, detail="Feature status retrieval failed")

@router.get("/performance")
async def health_performance():
    """Get performance health status and degradation analysis."""
    try:
        from src.monitoring.metrics import get_performance_degradation_detector
        degradation_detector = get_performance_degradation_detector()
        
        # Get performance health for all services
        services = ["scheduler", "dexscreener", "database", "api_processing"]
        performance_health = {}
        
        for service in services:
            performance_health[service] = degradation_detector.get_performance_health_status(service)
        
        # Get overall statistics
        stats = degradation_detector.get_degradation_statistics()
        
        # Get predictive alerts for all services
        all_predictive_alerts = []
        for service in services:
            service_alerts = degradation_detector.get_predictive_alerts(service, forecast_minutes=30)
            all_predictive_alerts.extend(service_alerts)
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_health": performance_health,
            "statistics": stats,
            "predictive_alerts": all_predictive_alerts
        }
    except Exception as e:
        log.error(f"Performance health check failed: {e}")
        raise HTTPException(status_code=500, detail="Performance health check failed")


@router.get("/performance/{service}")
async def health_performance_service(service: str):
    """Get detailed performance health status for a specific service."""
    try:
        from src.monitoring.metrics import get_performance_degradation_detector
        degradation_detector = get_performance_degradation_detector()
        
        # Get performance health status
        health_status = degradation_detector.get_performance_health_status(service)
        
        # Get predictive alerts
        predictive_alerts = degradation_detector.get_predictive_alerts(service, forecast_minutes=30)
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": service,
            "health_status": health_status,
            "predictive_alerts": predictive_alerts
        }
    except Exception as e:
        log.error(f"Service performance health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service performance health check failed")


@router.get("/priority")
async def health_priority():
    """Get priority processing health status and statistics."""
    try:
        from src.scheduler.monitoring import get_priority_processor
        priority_processor = get_priority_processor()
        
        # Get priority processing statistics
        priority_stats = priority_processor.get_priority_statistics()
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority_processing": priority_stats
        }
    except Exception as e:
        log.error(f"Priority processing health check failed: {e}")
        raise HTTPException(status_code=500, detail="Priority processing health check failed")