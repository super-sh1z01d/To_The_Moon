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
        health_ok = await wrapper.check_health_and_recover()
        
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


@router.get("/memory")
async def get_memory_health():
    """
    Get intelligent memory management status and statistics.
    
    Provides detailed memory usage, optimization history, and threshold information.
    """
    try:
        from src.monitoring.memory_manager import get_memory_manager
        
        memory_manager = get_memory_manager()
        memory_stats = memory_manager.get_memory_statistics()
        
        # Get current memory health status
        needs_alert, alerts = memory_manager.check_memory_and_optimize()
        
        # Convert alerts to dict format
        alerts_data = [
            {
                "level": alert.level.value,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in alerts
        ]
        
        # Determine overall status
        if any(alert.level.value == "critical" for alert in alerts):
            status = "critical"
        elif any(alert.level.value == "warning" for alert in alerts):
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "memory_statistics": memory_stats,
            "alerts": alerts_data,
            "needs_alert": needs_alert,
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting memory health: {e}")
        raise HTTPException(status_code=500, detail="Memory health check failed")


@router.post("/memory/optimize")
async def trigger_memory_optimization(component: Optional[str] = Query(None, description="Component to optimize (api_cache, metrics, all, or none for basic GC)")):
    """
    Manually trigger memory optimization (garbage collection and cleanup).
    
    Performs immediate memory optimization and returns results.
    Can target specific components or perform comprehensive cleanup.
    """
    try:
        from src.monitoring.memory_manager import get_memory_manager
        
        memory_manager = get_memory_manager()
        
        if component:
            # Use targeted cleanup
            optimization_result = memory_manager.perform_targeted_cleanup(component)
        else:
            # Use basic garbage collection
            optimization_result = memory_manager.perform_garbage_collection()
        
        return {
            "success": optimization_result.success,
            "before_mb": optimization_result.before_mb,
            "after_mb": optimization_result.after_mb,
            "recovered_mb": optimization_result.recovered_mb,
            "actions_taken": optimization_result.actions_taken,
            "component": component or "basic_gc",
            "timestamp": optimization_result.timestamp.isoformat()
        }
        
    except Exception as e:
        log.error(f"Error triggering memory optimization: {e}")
        raise HTTPException(status_code=500, detail="Memory optimization failed")


@router.post("/memory/update-thresholds")
async def update_memory_thresholds():
    """
    Manually trigger memory threshold recalculation and update.
    
    Forces recalculation of memory thresholds based on current system capacity.
    """
    try:
        from src.monitoring.memory_manager import get_memory_manager
        
        memory_manager = get_memory_manager()
        
        # Force threshold update by clearing the last update time
        memory_manager._last_threshold_update = None
        
        # Trigger threshold update
        updated = memory_manager.update_thresholds_if_needed()
        
        if updated:
            # Get new thresholds
            warning_mb, critical_mb = memory_manager.calculate_dynamic_thresholds()
            
            return {
                "updated": True,
                "new_warning_threshold_mb": warning_mb,
                "new_critical_threshold_mb": critical_mb,
                "message": "Memory thresholds updated successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "updated": False,
                "message": "No threshold update needed",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        log.error(f"Error updating memory thresholds: {e}")
        raise HTTPException(status_code=500, detail="Memory threshold update failed")


@router.get("/memory/report")
async def get_memory_report(hours: float = Query(24.0, description="Number of hours to analyze", ge=0.1, le=168.0)):
    """
    Get comprehensive memory usage report and analysis.
    
    Provides detailed memory usage trends, optimization history, and recommendations.
    """
    try:
        from src.monitoring.memory_reporter import get_memory_reporter
        
        memory_reporter = get_memory_reporter()
        report = memory_reporter.generate_report(hours)
        
        return {
            "report": {
                "timestamp": report.timestamp.isoformat(),
                "period_hours": report.report_period_hours,
                "current_status": {
                    "usage_mb": report.current_usage_mb,
                    "usage_percent": report.current_usage_percent,
                    "available_mb": report.current_available_mb
                },
                "thresholds": {
                    "warning_mb": report.warning_threshold_mb,
                    "critical_mb": report.critical_threshold_mb
                },
                "trends": {
                    "average_usage_mb": report.average_usage_mb,
                    "peak_usage_mb": report.peak_usage_mb,
                    "min_usage_mb": report.min_usage_mb,
                    "trend_direction": report.usage_trend
                },
                "optimization_activity": {
                    "optimizations_count": report.optimizations_count,
                    "total_recovered_mb": report.total_memory_recovered_mb,
                    "most_effective": report.most_effective_optimization
                },
                "issues": {
                    "leak_detections": report.leak_detections,
                    "threshold_violations": report.threshold_violations,
                    "auto_adjustments": report.auto_adjustments
                },
                "recommendations": report.recommendations,
                "data_quality": {
                    "usage_samples": report.usage_samples,
                    "optimization_records": len(report.optimization_history)
                }
            }
        }
        
    except Exception as e:
        log.error(f"Error generating memory report: {e}")
        raise HTTPException(status_code=500, detail="Memory report generation failed")


@router.post("/memory/log-report")
async def trigger_memory_report_logging(hours: float = Query(1.0, description="Number of hours to analyze", ge=0.1, le=24.0)):
    """
    Trigger memory report logging to system logs.
    
    Generates and logs a memory usage report for monitoring and analysis.
    """
    try:
        from src.monitoring.memory_reporter import get_memory_reporter
        
        memory_reporter = get_memory_reporter()
        memory_reporter.log_memory_report(hours)
        
        return {
            "message": f"Memory report logged for {hours} hours period",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error logging memory report: {e}")
        raise HTTPException(status_code=500, detail="Memory report logging failed")


@router.post("/telegram/test")
async def test_telegram_notification(
    level: str = Query("info", description="Alert level: info, warning, error, critical"),
    message: str = Query("Test notification from To The Moon monitoring system", description="Test message to send")
):
    """
    Send a test notification to Telegram to verify integration.
    
    Useful for testing Telegram bot configuration and connectivity.
    """
    try:
        from src.monitoring.alert_manager import get_alert_manager
        from src.monitoring.models import HealthAlert, AlertLevel
        
        # Validate level
        level_map = {
            "info": AlertLevel.INFO,
            "warning": AlertLevel.WARNING,
            "error": AlertLevel.ERROR,
            "critical": AlertLevel.CRITICAL
        }
        
        if level.lower() not in level_map:
            raise HTTPException(status_code=400, detail=f"Invalid level. Must be one of: {list(level_map.keys())}")
        
        alert_level = level_map[level.lower()]
        
        # Create test alert
        test_alert = HealthAlert(
            level=alert_level,
            message=message,
            component="telegram.test",
            timestamp=datetime.utcnow()
        )
        
        # Send alert
        alert_manager = get_alert_manager()
        success = alert_manager.send_alert(test_alert)
        
        return {
            "success": success,
            "level": level,
            "message": message,
            "alert_id": test_alert.correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error sending test Telegram notification: {e}")
        raise HTTPException(status_code=500, detail="Telegram test failed")


@router.post("/telegram/test-memory")
async def test_memory_telegram_notification(
    alert_type: str = Query("critical", description="Memory alert type: critical, warning, optimized, leak_detected")
):
    """
    Send a test memory notification to Telegram with rich formatting.
    
    Tests the enhanced memory notification system.
    """
    try:
        from src.monitoring.telegram_notifier import get_telegram_notifier
        
        telegram_notifier = get_telegram_notifier()
        
        if not telegram_notifier.is_configured():
            raise HTTPException(status_code=400, detail="Telegram not configured")
        
        # Test data
        test_data = {
            "current_usage_mb": 1500.0,
            "threshold_mb": 1400.0,
            "total_memory_gb": 62.7,
            "recovered_mb": 25.5,
            "actions_taken": ["gc_collect", "cache_clear", "history_trim"]
        }
        
        success = telegram_notifier.send_memory_alert(
            alert_type=alert_type,
            **test_data
        )
        
        return {
            "success": success,
            "alert_type": alert_type,
            "test_data": test_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error sending test memory Telegram notification: {e}")
        raise HTTPException(status_code=500, detail="Memory Telegram test failed")


@router.post("/telegram/test-performance")
async def test_performance_telegram_notification():
    """
    Send a test performance notification to Telegram.
    
    Tests the performance notification system.
    """
    try:
        from src.monitoring.telegram_notifier import get_telegram_notifier
        
        telegram_notifier = get_telegram_notifier()
        
        if not telegram_notifier.is_configured():
            raise HTTPException(status_code=400, detail="Telegram not configured")
        
        # Test performance data
        test_metrics = {
            "response_time": 2.5,
            "throughput": 45.2,
            "error_rate": 12.3,
            "cpu_usage": 78.5
        }
        
        test_recommendations = [
            "Increase API timeout settings",
            "Scale processing workers",
            "Optimize database queries"
        ]
        
        success = telegram_notifier.send_performance_alert(
            alert_type="degradation",
            component="api.dexscreener",
            metrics=test_metrics,
            recommendations=test_recommendations
        )
        
        return {
            "success": success,
            "alert_type": "degradation",
            "component": "api.dexscreener",
            "metrics": test_metrics,
            "recommendations": test_recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error sending test performance Telegram notification: {e}")
        raise HTTPException(status_code=500, detail="Performance Telegram test failed")


@router.post("/telegram/test-tokens")
async def test_token_processing_telegram_notification():
    """
    Send a test token processing notification to Telegram.
    
    Tests the token processing notification system.
    """
    try:
        from src.monitoring.telegram_notifier import get_telegram_notifier
        
        telegram_notifier = get_telegram_notifier()
        
        if not telegram_notifier.is_configured():
            raise HTTPException(status_code=400, detail="Telegram not configured")
        
        success = telegram_notifier.send_token_processing_alert(
            alert_type="stuck_tokens",
            tokens_stuck=15,
            processing_rate=2.3,
            backlog_size=45,
            avg_activation_time=125.5
        )
        
        return {
            "success": success,
            "alert_type": "stuck_tokens",
            "tokens_stuck": 15,
            "processing_rate": 2.3,
            "backlog_size": 45,
            "avg_activation_time": 125.5,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error sending test token processing Telegram notification: {e}")
        raise HTTPException(status_code=500, detail="Token processing Telegram test failed")


@router.get("/tokens/monitoring")
async def get_token_processing_metrics():
    """
    Get comprehensive token processing performance metrics.
    
    Provides detailed metrics on token status transitions, processing rates,
    and activation performance.
    """
    try:
        from src.monitoring.token_monitor import get_token_monitor
        
        token_monitor = get_token_monitor()
        performance_summary = token_monitor.get_performance_summary()
        
        return {
            "status": "success",
            "metrics": performance_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting token processing metrics: {e}")
        raise HTTPException(status_code=500, detail="Token processing metrics failed")


@router.get("/tokens/stuck")
async def get_stuck_tokens_analysis(limit: int = Query(20, description="Maximum number of stuck tokens to analyze", ge=1, le=100)):
    """
    Get detailed analysis of tokens stuck in monitoring status.
    
    Provides analysis of why tokens haven't activated and potential blocking conditions.
    """
    try:
        from src.monitoring.token_monitor import get_token_monitor
        
        token_monitor = get_token_monitor()
        stuck_analysis = token_monitor.analyze_stuck_tokens(limit)
        
        # Convert to serializable format
        analysis_data = []
        for analysis in stuck_analysis:
            analysis_data.append({
                "mint_address": analysis.mint_address,
                "status": analysis.status,
                "created_at": analysis.created_at.isoformat(),
                "last_processed_at": analysis.last_processed_at.isoformat(),
                "time_in_monitoring_hours": analysis.time_in_monitoring_hours,
                "time_since_last_process_minutes": analysis.time_since_last_process_minutes,
                "meets_activation_criteria": analysis.meets_activation_criteria,
                "blocking_conditions": analysis.blocking_conditions,
                "pool_count": analysis.pool_count,
                "total_liquidity_usd": analysis.total_liquidity_usd,
                "external_pools_with_liquidity": analysis.external_pools_with_liquidity
            })
        
        return {
            "status": "success",
            "stuck_tokens_count": len(analysis_data),
            "analysis": analysis_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error analyzing stuck tokens: {e}")
        raise HTTPException(status_code=500, detail="Stuck tokens analysis failed")


@router.post("/tokens/record-transition")
async def record_token_transition(
    mint_address: str = Query(..., description="Token mint address"),
    from_status: str = Query(..., description="Previous status"),
    to_status: str = Query(..., description="New status"),
    processing_time_seconds: Optional[float] = Query(None, description="Processing time in seconds"),
    reason: Optional[str] = Query(None, description="Reason for transition")
):
    """
    Record a token status transition for monitoring.
    
    Used by the system to track token processing performance and identify bottlenecks.
    """
    try:
        from src.monitoring.token_monitor import get_token_monitor
        
        token_monitor = get_token_monitor()
        token_monitor.record_status_transition(
            mint_address=mint_address,
            from_status=from_status,
            to_status=to_status,
            processing_time_seconds=processing_time_seconds,
            reason=reason
        )
        
        return {
            "status": "success",
            "message": "Transition recorded",
            "mint_address": mint_address,
            "from_status": from_status,
            "to_status": to_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error recording token transition: {e}")
        raise HTTPException(status_code=500, detail="Token transition recording failed")


@router.get("/alerts/config")
async def get_alert_configuration():
    """
    Get current alert configuration and rules summary.
    
    Shows which components are monitored and alert thresholds.
    """
    try:
        from src.monitoring.alert_config import get_alert_rule_summary
        from src.monitoring.alert_manager import get_alert_manager
        
        # Get configuration summary
        config_summary = get_alert_rule_summary()
        
        # Get current alert manager status
        alert_manager = get_alert_manager()
        manager_stats = alert_manager.get_alert_statistics()
        
        return {
            "configuration": config_summary,
            "current_status": {
                "active_rules": manager_stats.get("active_rules", 0),
                "total_rules": manager_stats.get("total_rules", 0),
                "recent_alerts": manager_stats.get("recent_alerts_last_hour", 0),
                "available_channels": manager_stats.get("available_channels", [])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting alert configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert configuration")


@router.post("/alerts/reload")
async def reload_alert_configuration():
    """
    Reload alert configuration with enhanced rules.
    
    Applies the latest alert rules and returns the new configuration.
    """
    try:
        from src.monitoring.alert_manager import get_alert_manager
        from src.monitoring.alert_config import apply_enhanced_alert_rules, get_alert_rule_summary
        
        alert_manager = get_alert_manager()
        
        # Apply enhanced rules
        rules_applied = apply_enhanced_alert_rules(alert_manager)
        
        # Get new configuration
        config_summary = get_alert_rule_summary()
        
        return {
            "success": True,
            "rules_applied": rules_applied,
            "configuration": config_summary,
            "message": "Alert configuration reloaded successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error reloading alert configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload alert configuration")
@router.get("/performance/optimizer")
async def get_performance_optimizer_status():
    """
    Get current performance optimizer status and settings.
    
    Shows current optimization settings, recent actions, and performance metrics.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Get recent optimization history
        recent_actions = optimizer.optimization_history[-10:]  # Last 10 actions
        
        # Get current metrics
        current_metrics = optimizer.collect_current_metrics()
        
        return {
            "status": "success",
            "current_settings": optimizer.current_settings,
            "thresholds": optimizer.thresholds,
            "current_metrics": {
                "avg_response_time": current_metrics.avg_response_time,
                "cpu_usage": current_metrics.cpu_usage,
                "queue_size": current_metrics.queue_size,
                "processing_rate": current_metrics.processing_rate,
                "error_rate": current_metrics.error_rate,
                "timeout_rate": current_metrics.timeout_rate
            },
            "recent_optimizations": [
                {
                    "timestamp": action.timestamp.isoformat(),
                    "component": action.component,
                    "action_type": action.action_type,
                    "old_value": action.old_value,
                    "new_value": action.new_value,
                    "reason": action.reason,
                    "success": action.success
                }
                for action in recent_actions
            ],
            "cooldown_status": {
                "api_timeout": optimizer._is_in_cooldown("api_timeout"),
                "parallelism": optimizer._is_in_cooldown("parallelism"),
                "load_reduction": optimizer._is_in_cooldown("load_reduction")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting performance optimizer status: {e}")
        raise HTTPException(status_code=500, detail="Performance optimizer status retrieval failed")


@router.post("/performance/optimizer/run")
async def run_performance_optimization():
    """
    Manually trigger a performance optimization cycle.
    
    Runs immediate performance analysis and applies optimizations if needed.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        result = optimizer.run_optimization_cycle()
        
        return {
            "status": "success",
            "optimization_result": result
        }
        
    except Exception as e:
        log.error(f"Error running performance optimization: {e}")
        raise HTTPException(status_code=500, detail="Performance optimization failed")


@router.put("/performance/optimizer/settings")
async def update_optimizer_settings(
    api_timeout: Optional[float] = Query(None, description="API timeout in seconds (5-30)"),
    max_parallel_requests: Optional[int] = Query(None, description="Max parallel requests (2-20)"),
    batch_size: Optional[int] = Query(None, description="Batch size (10-100)"),
    processing_interval: Optional[float] = Query(None, description="Processing interval in seconds (5-30)")
):
    """
    Update performance optimizer settings.
    
    Allows manual adjustment of optimization parameters and thresholds.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Validate and update settings
        updates = {}
        
        if api_timeout is not None:
            if not 5.0 <= api_timeout <= 30.0:
                raise HTTPException(status_code=400, detail="api_timeout must be between 5 and 30 seconds")
            optimizer.current_settings["api_timeout"] = api_timeout
            updates["api_timeout"] = api_timeout
        
        if max_parallel_requests is not None:
            if not 2 <= max_parallel_requests <= 20:
                raise HTTPException(status_code=400, detail="max_parallel_requests must be between 2 and 20")
            optimizer.current_settings["max_parallel_requests"] = max_parallel_requests
            updates["max_parallel_requests"] = max_parallel_requests
        
        if batch_size is not None:
            if not 10 <= batch_size <= 100:
                raise HTTPException(status_code=400, detail="batch_size must be between 10 and 100")
            optimizer.current_settings["batch_size"] = batch_size
            updates["batch_size"] = batch_size
        
        if processing_interval is not None:
            if not 5.0 <= processing_interval <= 30.0:
                raise HTTPException(status_code=400, detail="processing_interval must be between 5 and 30 seconds")
            optimizer.current_settings["processing_interval"] = processing_interval
            updates["processing_interval"] = processing_interval
        
        if not updates:
            raise HTTPException(status_code=400, detail="No valid settings provided for update")
        
        log.info(
            "performance_optimizer_settings_updated",
            extra={
                "updates": updates,
                "new_settings": optimizer.current_settings
            }
        )
        
        return {
            "status": "success",
            "message": "Performance optimizer settings updated",
            "updated_settings": updates,
            "current_settings": optimizer.current_settings,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating optimizer settings: {e}")
        raise HTTPException(status_code=500, detail="Performance optimizer settings update failed")


@router.put("/performance/optimizer/thresholds")
async def update_optimizer_thresholds(
    slow_response_time: Optional[float] = Query(None, description="Slow response time threshold in seconds"),
    high_error_rate: Optional[float] = Query(None, description="High error rate threshold in percent"),
    high_cpu_usage: Optional[float] = Query(None, description="High CPU usage threshold in percent"),
    large_queue_size: Optional[int] = Query(None, description="Large queue size threshold"),
    low_processing_rate: Optional[float] = Query(None, description="Low processing rate threshold")
):
    """
    Update performance optimizer thresholds.
    
    Allows fine-tuning of the thresholds that trigger optimizations.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Validate and update thresholds
        updates = {}
        
        if slow_response_time is not None:
            if not 0.5 <= slow_response_time <= 10.0:
                raise HTTPException(status_code=400, detail="slow_response_time must be between 0.5 and 10 seconds")
            optimizer.thresholds["slow_response_time"] = slow_response_time
            updates["slow_response_time"] = slow_response_time
        
        if high_error_rate is not None:
            if not 1.0 <= high_error_rate <= 50.0:
                raise HTTPException(status_code=400, detail="high_error_rate must be between 1 and 50 percent")
            optimizer.thresholds["high_error_rate"] = high_error_rate
            updates["high_error_rate"] = high_error_rate
        
        if high_cpu_usage is not None:
            if not 50.0 <= high_cpu_usage <= 95.0:
                raise HTTPException(status_code=400, detail="high_cpu_usage must be between 50 and 95 percent")
            optimizer.thresholds["high_cpu_usage"] = high_cpu_usage
            updates["high_cpu_usage"] = high_cpu_usage
        
        if large_queue_size is not None:
            if not 10 <= large_queue_size <= 1000:
                raise HTTPException(status_code=400, detail="large_queue_size must be between 10 and 1000")
            optimizer.thresholds["large_queue_size"] = large_queue_size
            updates["large_queue_size"] = large_queue_size
        
        if low_processing_rate is not None:
            if not 0.1 <= low_processing_rate <= 10.0:
                raise HTTPException(status_code=400, detail="low_processing_rate must be between 0.1 and 10")
            optimizer.thresholds["low_processing_rate"] = low_processing_rate
            updates["low_processing_rate"] = low_processing_rate
        
        if not updates:
            raise HTTPException(status_code=400, detail="No valid thresholds provided for update")
        
        log.info(
            "performance_optimizer_thresholds_updated",
            extra={
                "updates": updates,
                "new_thresholds": optimizer.thresholds
            }
        )
        
        return {
            "status": "success",
            "message": "Performance optimizer thresholds updated",
            "updated_thresholds": updates,
            "current_thresholds": optimizer.thresholds,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating optimizer thresholds: {e}")
        raise HTTPException(status_code=500, detail="Performance optimizer thresholds update failed")


@router.delete("/performance/optimizer/history")
async def clear_optimization_history():
    """
    Clear performance optimization history.
    
    Removes all stored optimization actions and resets statistics.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Clear history
        history_count = len(optimizer.optimization_history)
        optimizer.optimization_history.clear()
        optimizer.metrics_history.clear()
        
        # Reset cooldowns
        for key in optimizer.last_optimizations:
            optimizer.last_optimizations[key] = None
        
        log.info(
            "performance_optimizer_history_cleared",
            extra={
                "cleared_actions": history_count
            }
        )
        
        return {
            "status": "success",
            "message": "Performance optimization history cleared",
            "cleared_actions": history_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error clearing optimization history: {e}")
        raise HTTPException(status_code=500, detail="Performance optimization history clearing failed")

@router.get("/performance/optimizer/database")
async def get_database_performance():
    """
    Get database performance metrics and optimization suggestions.
    
    Provides detailed database performance analysis and recommendations.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Get database metrics
        db_metrics = optimizer._get_database_performance_metrics()
        
        if not db_metrics:
            raise HTTPException(status_code=503, detail="Database metrics unavailable")
        
        # Analyze for optimization opportunities
        recommendations = optimizer._analyze_slow_queries(db_metrics)
        
        # Determine status
        avg_query_time = db_metrics.get("avg_query_time", 0)
        status = "healthy"
        if avg_query_time > 5.0:
            status = "critical"
        elif avg_query_time > 2.0:
            status = "warning"
        
        return {
            "status": status,
            "database_metrics": db_metrics,
            "recommendations": recommendations,
            "performance_analysis": {
                "query_performance": "slow" if avg_query_time > 2.0 else "good",
                "connection_usage": f"{db_metrics.get('active_connections', 0)}/{db_metrics.get('max_connections', 0)}",
                "needs_optimization": len(recommendations) > 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting database performance: {e}")
        raise HTTPException(status_code=500, detail="Database performance retrieval failed")


@router.get("/performance/optimizer/memory")
async def get_memory_analysis():
    """
    Get memory usage analysis and leak detection results.
    
    Provides memory trend analysis and potential leak detection.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Get current metrics
        current_metrics = optimizer.collect_current_metrics()
        
        # Analyze memory trends if we have history
        memory_analysis = {
            "current_usage_mb": current_metrics.memory_usage_mb,
            "current_usage_gb": round(current_metrics.memory_usage_mb / 1024, 2),
            "trend_analysis": None,
            "leak_detected": False,
            "growth_rate_percent": 0.0
        }
        
        if len(optimizer.metrics_history) >= 10:
            # Analyze memory trend
            recent_memory = [m.memory_usage_mb for m in list(optimizer.metrics_history)[-10:]]
            
            if len(recent_memory) >= 5:
                early_avg = sum(recent_memory[:5]) / 5
                late_avg = sum(recent_memory[-5:]) / 5
                growth_rate = (late_avg - early_avg) / early_avg * 100
                
                memory_analysis.update({
                    "trend_analysis": {
                        "early_avg_mb": round(early_avg, 1),
                        "late_avg_mb": round(late_avg, 1),
                        "trend": "increasing" if growth_rate > 5 else "decreasing" if growth_rate < -5 else "stable"
                    },
                    "leak_detected": growth_rate > 10.0 and late_avg > 1000,
                    "growth_rate_percent": round(growth_rate, 2)
                })
        
        # Determine status
        status = "healthy"
        if current_metrics.memory_usage_mb > 10000:  # >10GB
            status = "critical"
        elif current_metrics.memory_usage_mb > 8000:  # >8GB
            status = "warning"
        
        return {
            "status": status,
            "memory_analysis": memory_analysis,
            "recommendations": [
                "Monitor memory usage trends regularly",
                "Consider memory cleanup if growth rate exceeds 10%",
                "Check for memory leaks in long-running processes"
            ] if memory_analysis["leak_detected"] else [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting memory analysis: {e}")
        raise HTTPException(status_code=500, detail="Memory analysis failed")


@router.post("/performance/optimizer/memory/cleanup")
async def trigger_memory_cleanup():
    """
    Manually trigger memory cleanup operations.
    
    Forces garbage collection and memory optimization.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Get memory usage before cleanup
        before_metrics = optimizer.collect_current_metrics()
        before_memory = before_metrics.memory_usage_mb
        
        # Trigger cleanup
        cleanup_success = optimizer._trigger_memory_cleanup()
        
        # Wait a moment and check memory again
        import time
        time.sleep(2)
        
        after_metrics = optimizer.collect_current_metrics()
        after_memory = after_metrics.memory_usage_mb
        
        memory_freed = before_memory - after_memory
        
        return {
            "status": "success" if cleanup_success else "partial",
            "cleanup_result": {
                "memory_before_mb": round(before_memory, 1),
                "memory_after_mb": round(after_memory, 1),
                "memory_freed_mb": round(memory_freed, 1),
                "cleanup_success": cleanup_success
            },
            "message": f"Memory cleanup completed, freed {memory_freed:.1f}MB" if memory_freed > 0 else "Memory cleanup completed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error triggering memory cleanup: {e}")
        raise HTTPException(status_code=500, detail="Memory cleanup failed")


@router.get("/performance/optimizer/resources")
async def get_system_resource_status():
    """
    Get comprehensive system resource status and optimization recommendations.
    
    Provides CPU, memory, database, and overall system health analysis.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        
        # Get current metrics
        current_metrics = optimizer.collect_current_metrics()
        
        # Analyze CPU trends
        cpu_analysis = {
            "current_usage": current_metrics.cpu_usage,
            "status": "healthy",
            "sustained_high": False
        }
        
        if current_metrics.cpu_usage > 90:
            cpu_analysis["status"] = "critical"
        elif current_metrics.cpu_usage > 80:
            cpu_analysis["status"] = "warning"
        
        # Check for sustained high CPU
        if len(optimizer.metrics_history) >= 3:
            recent_cpu = [m.cpu_usage for m in list(optimizer.metrics_history)[-3:]]
            cpu_analysis["sustained_high"] = all(cpu > 80.0 for cpu in recent_cpu)
        
        # Get database metrics
        db_metrics = optimizer._get_database_performance_metrics()
        db_status = "healthy"
        if db_metrics:
            if db_metrics.get("avg_query_time", 0) > 5.0:
                db_status = "critical"
            elif db_metrics.get("avg_query_time", 0) > 2.0:
                db_status = "warning"
        
        # Overall system status
        statuses = [cpu_analysis["status"], db_status]
        if current_metrics.memory_usage_mb > 10000:
            statuses.append("critical")
        elif current_metrics.memory_usage_mb > 8000:
            statuses.append("warning")
        else:
            statuses.append("healthy")
        
        overall_status = "critical" if "critical" in statuses else "warning" if "warning" in statuses else "healthy"
        
        # Generate recommendations
        recommendations = []
        if cpu_analysis["sustained_high"]:
            recommendations.append("CPU usage has been high for multiple measurements - consider load reduction")
        if current_metrics.memory_usage_mb > 8000:
            recommendations.append("Memory usage is high - consider cleanup or optimization")
        if db_metrics and db_metrics.get("avg_query_time", 0) > 2.0:
            recommendations.append("Database queries are slow - consider optimization")
        if current_metrics.queue_size > 100:
            recommendations.append("Processing queue is large - consider increasing parallelism")
        
        return {
            "overall_status": overall_status,
            "resource_analysis": {
                "cpu": cpu_analysis,
                "memory": {
                    "usage_mb": current_metrics.memory_usage_mb,
                    "usage_gb": round(current_metrics.memory_usage_mb / 1024, 2),
                    "status": "critical" if current_metrics.memory_usage_mb > 10000 else "warning" if current_metrics.memory_usage_mb > 8000 else "healthy"
                },
                "database": {
                    "status": db_status,
                    "metrics": db_metrics
                },
                "processing": {
                    "queue_size": current_metrics.queue_size,
                    "processing_rate": current_metrics.processing_rate,
                    "status": "warning" if current_metrics.queue_size > 100 else "healthy"
                }
            },
            "recommendations": recommendations,
            "optimization_opportunities": len(recommendations),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting system resource status: {e}")
        raise HTTPException(status_code=500, detail="System resource status retrieval failed")


@router.get("/performance/optimizer")
async def get_performance_optimizer_status():
    """
    Get current performance optimizer status.
    
    Shows basic performance metrics and optimization recommendations.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        result = optimizer.run_optimization_cycle()
        
        return {
            "status": "success",
            "optimizer_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting performance optimizer status: {e}")
        raise HTTPException(status_code=500, detail="Performance optimizer status retrieval failed")


@router.post("/performance/optimizer/run")
async def run_performance_optimization():
    """
    Manually trigger a performance optimization cycle.
    
    Runs immediate performance analysis and provides recommendations.
    """
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        result = optimizer.run_optimization_cycle()
        
        return {
            "status": "success",
            "optimization_result": result,
            "message": "Performance optimization cycle completed"
        }
        
    except Exception as e:
        log.error(f"Error running performance optimization: {e}")
        raise HTTPException(status_code=500, detail="Performance optimization failed")