from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from src.core.config import get_config
from src.monitoring.health_monitor import health_monitor
from src.monitoring.circuit_breaker import get_all_circuit_breakers, get_circuit_breaker_stats
from src.monitoring.retry_manager import get_all_retry_managers, get_retry_manager_stats


router = APIRouter()


@router.get("/health", tags=["meta"])
async def health() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}


@router.get("/health/comprehensive", tags=["meta"])
async def comprehensive_health() -> Dict[str, Any]:
    """
    Comprehensive system health check including all components.
    
    Returns detailed health information for:
    - Overall system status
    - Scheduler health
    - System resources (CPU, memory, disk)
    - External API health
    - Circuit breaker status
    - Retry manager statistics
    """
    try:
        system_health = await health_monitor.get_comprehensive_health_async()
        
        # Convert to dict for JSON serialization with safe handling
        def serialize_alert(alert):
            return {
                "level": alert.level.value,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat(),
                "correlation_id": alert.correlation_id
            }
        
        health_data = {
            "overall_status": system_health.overall_status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "uptime_seconds": round(system_health.uptime_seconds, 2),
            "last_restart": system_health.last_restart.isoformat() if system_health.last_restart else None,
            
            "scheduler": {
                "status": system_health.scheduler.status.value,
                "hot_group_last_run": system_health.scheduler.hot_group_last_run.isoformat() if system_health.scheduler.hot_group_last_run else None,
                "cold_group_last_run": system_health.scheduler.cold_group_last_run.isoformat() if system_health.scheduler.cold_group_last_run else None,
                "hot_group_processing_time": round(system_health.scheduler.hot_group_processing_time, 2),
                "cold_group_processing_time": round(system_health.scheduler.cold_group_processing_time, 2),
                "tokens_processed_per_minute": round(system_health.scheduler.tokens_processed_per_minute, 2),
                "error_rate": round(system_health.scheduler.error_rate, 2),
                "active_jobs": system_health.scheduler.active_jobs,
                "failed_jobs_last_hour": system_health.scheduler.failed_jobs_last_hour,
                "alerts": [serialize_alert(alert) for alert in system_health.scheduler.alerts]
            },
            
            "resources": {
                "status": system_health.resources.status.value,
                "memory_usage_mb": round(system_health.resources.memory_usage_mb, 2),
                "memory_usage_percent": round(system_health.resources.memory_usage_percent, 2),
                "cpu_usage_percent": round(system_health.resources.cpu_usage_percent, 2),
                "disk_usage_percent": round(system_health.resources.disk_usage_percent, 2),
                "database_connections": system_health.resources.database_connections,
                "max_database_connections": system_health.resources.max_database_connections,
                "open_file_descriptors": system_health.resources.open_file_descriptors,
                "max_file_descriptors": system_health.resources.max_file_descriptors,
                "alerts": [serialize_alert(alert) for alert in system_health.resources.alerts]
            },
            
            "apis": {
                api_name: {
                    "status": api_health.status.value,
                    "average_response_time": round(api_health.average_response_time, 2),
                    "p95_response_time": round(api_health.p95_response_time, 2),
                    "error_rate": round(api_health.error_rate, 2),
                    "circuit_breaker_state": api_health.circuit_breaker_state.value,
                    "cache_hit_rate": round(api_health.cache_hit_rate, 2),
                    "requests_per_minute": round(api_health.requests_per_minute, 2),
                    "last_successful_call": api_health.last_successful_call.isoformat() if api_health.last_successful_call else None,
                    "consecutive_failures": api_health.consecutive_failures,
                    "alerts": [serialize_alert(alert) for alert in api_health.alerts]
                }
                for api_name, api_health in system_health.apis.items()
            },
            
            "alerts": {
                "all_alerts": [serialize_alert(alert) for alert in system_health.get_all_alerts()],
                "critical_alerts": [serialize_alert(alert) for alert in system_health.get_critical_alerts()]
            }
        }
        
        return health_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/health/scheduler", tags=["meta"])
async def scheduler_health() -> dict:
    """
    Detailed scheduler health check.
    
    Returns information about scheduler job execution, processing times,
    and any issues with hot/cold group processing.
    """
    try:
        # Use both legacy and new monitoring
        from src.scheduler.monitoring import check_scheduler_health_endpoint
        legacy_health = await check_scheduler_health_endpoint()
        
        # Get enhanced scheduler health
        scheduler_health = await health_monitor.monitor_scheduler_health()
        
        return {
            "legacy": legacy_health,
            "enhanced": {
                "status": scheduler_health.status.value,
                "hot_group_last_run": scheduler_health.hot_group_last_run.isoformat() if scheduler_health.hot_group_last_run else None,
                "cold_group_last_run": scheduler_health.cold_group_last_run.isoformat() if scheduler_health.cold_group_last_run else None,
                "hot_group_processing_time": scheduler_health.hot_group_processing_time,
                "cold_group_processing_time": scheduler_health.cold_group_processing_time,
                "tokens_processed_per_minute": scheduler_health.tokens_processed_per_minute,
                "error_rate": scheduler_health.error_rate,
                "active_jobs": scheduler_health.active_jobs,
                "failed_jobs_last_hour": scheduler_health.failed_jobs_last_hour,
                "alerts": [
                    {
                        "level": alert.level.value,
                        "message": alert.message,
                        "component": alert.component,
                        "timestamp": alert.timestamp.isoformat(),
                        "correlation_id": alert.correlation_id
                    }
                    for alert in scheduler_health.alerts
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduler health check failed: {str(e)}")


@router.get("/health/resources", tags=["meta"])
async def resources_health() -> Dict[str, Any]:
    """
    System resource health check.
    
    Returns information about CPU, memory, disk usage, and database connections.
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
        raise HTTPException(status_code=500, detail=f"Resource health check failed: {str(e)}")


@router.get("/health/apis", tags=["meta"])
async def apis_health() -> Dict[str, Any]:
    """
    External API health check.
    
    Returns information about external API performance, circuit breaker status,
    and error rates.
    """
    try:
        # Get API health for known services
        api_services = ["dexscreener"]
        apis_health = {}
        
        for service in api_services:
            api_health = await health_monitor.monitor_api_health(service)
            apis_health[service] = {
                "status": api_health.status.value,
                "average_response_time": api_health.average_response_time,
                "p95_response_time": api_health.p95_response_time,
                "error_rate": api_health.error_rate,
                "circuit_breaker_state": api_health.circuit_breaker_state.value,
                "cache_hit_rate": api_health.cache_hit_rate,
                "requests_per_minute": api_health.requests_per_minute,
                "last_successful_call": api_health.last_successful_call.isoformat() if api_health.last_successful_call else None,
                "consecutive_failures": api_health.consecutive_failures,
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
        
        return {
            "apis": apis_health,
            "summary": {
                "total_apis": len(apis_health),
                "healthy_apis": len([api for api in apis_health.values() if api["status"] == "healthy"]),
                "degraded_apis": len([api for api in apis_health.values() if api["status"] == "degraded"]),
                "critical_apis": len([api for api in apis_health.values() if api["status"] == "critical"])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API health check failed: {str(e)}")


@router.get("/health/circuit-breakers", tags=["meta"])
async def circuit_breakers_health() -> Dict[str, Any]:
    """
    Circuit breaker status and statistics.
    
    Returns information about all circuit breakers, their current state,
    and performance statistics.
    """
    try:
        circuit_breakers = get_all_circuit_breakers()
        circuit_stats = get_circuit_breaker_stats()
        
        return {
            "circuit_breakers": {
                name: {
                    "state": breaker.state.value,
                    "is_healthy": breaker.is_closed,
                    "failure_rate": breaker.failure_rate,
                    "stats": circuit_stats.get(name, {})
                }
                for name, breaker in circuit_breakers.items()
            },
            "summary": {
                "total_breakers": len(circuit_breakers),
                "closed_breakers": len([b for b in circuit_breakers.values() if b.is_closed]),
                "open_breakers": len([b for b in circuit_breakers.values() if b.is_open]),
                "half_open_breakers": len([b for b in circuit_breakers.values() if b.is_half_open])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Circuit breaker health check failed: {str(e)}")


@router.get("/health/retry-managers", tags=["meta"])
async def retry_managers_health() -> Dict[str, Any]:
    """
    Retry manager statistics and performance.
    
    Returns information about all retry managers and their performance statistics.
    """
    try:
        retry_managers = get_all_retry_managers()
        retry_stats = get_retry_manager_stats()
        
        return {
            "retry_managers": retry_stats,
            "summary": {
                "total_managers": len(retry_managers),
                "total_calls": sum(stats.get("total_calls", 0) for stats in retry_stats.values()),
                "total_retries": sum(stats.get("total_retries", 0) for stats in retry_stats.values()),
                "total_successes": sum(stats.get("total_successes", 0) for stats in retry_stats.values()),
                "total_failures": sum(stats.get("total_failures", 0) for stats in retry_stats.values()),
                "average_success_rate": (
                    sum(stats.get("success_rate", 0) for stats in retry_stats.values()) / len(retry_stats)
                    if retry_stats else 0
                )
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry manager health check failed: {str(e)}")


@router.get("/version", tags=["meta"])
async def version() -> dict:
    cfg = get_config()
    return {"name": cfg.app_name, "version": cfg.app_version, "env": cfg.app_env}

