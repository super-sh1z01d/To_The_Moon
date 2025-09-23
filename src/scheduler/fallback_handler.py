"""
Fallback handler for external dependencies.

Provides fallback mechanisms when external services are unavailable,
including cached data, alternative endpoints, and graceful degradation.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

log = logging.getLogger(__name__)


class FallbackHandler:
    """Обработчик fallback-сценариев для внешних зависимостей."""
    
    def __init__(self):
        self.fallback_data = {}
        self.last_successful_fetch = {}
        self.failure_counts = defaultdict(int)
        self.max_failures = 3
        self.fallback_strategies = {}
        self.dependency_health = {}
        self.fallback_cache_ttl = 3600  # 1 hour
        
        # Initialize structured logger
        from src.monitoring.metrics import get_structured_logger
        self.logger = get_structured_logger("fallback_handler")
        
        # Setup default fallback strategies
        self._setup_default_strategies()
        
    def _setup_default_strategies(self):
        """Setup default fallback strategies for different services."""
        self.fallback_strategies = {
            "dexscreener": {
                "strategy": "cached_data",
                "max_age_hours": 2,
                "fallback_endpoints": [],
                "default_data": None
            },
            "database": {
                "strategy": "readonly_mode",
                "max_age_hours": 24,
                "fallback_endpoints": [],
                "default_data": None
            },
            "external_api": {
                "strategy": "alternative_endpoint",
                "max_age_hours": 1,
                "fallback_endpoints": [],
                "default_data": {}
            }
        }
    
    def register_fallback_strategy(self, service: str, strategy: str, 
                                 max_age_hours: int = 1, 
                                 fallback_endpoints: List[str] = None,
                                 default_data: Any = None):
        """Register a fallback strategy for a service."""
        self.fallback_strategies[service] = {
            "strategy": strategy,
            "max_age_hours": max_age_hours,
            "fallback_endpoints": fallback_endpoints or [],
            "default_data": default_data
        }
        
        self.logger.info(
            f"Fallback strategy registered for {service}",
            service=service,
            strategy=strategy,
            max_age_hours=max_age_hours
        )
    
    def should_use_fallback(self, service: str) -> bool:
        """Определить, следует ли использовать fallback для сервиса."""
        failure_threshold_reached = self.failure_counts[service] >= self.max_failures
        service_unhealthy = self.dependency_health.get(service, {}).get("status") == "unhealthy"
        
        should_fallback = failure_threshold_reached or service_unhealthy
        
        if should_fallback:
            self.logger.warning(
                f"Fallback triggered for {service}",
                service=service,
                failure_count=self.failure_counts[service],
                max_failures=self.max_failures,
                service_health=self.dependency_health.get(service, {})
            )
        
        return should_fallback
    
    def record_success(self, service: str):
        """Записать успешное выполнение для сервиса."""
        self.failure_counts[service] = 0
        self.last_successful_fetch[service] = datetime.now(timezone.utc)
        
        # Update dependency health
        self.dependency_health[service] = {
            "status": "healthy",
            "last_success": datetime.now(timezone.utc),
            "failure_count": 0,
            "error": None
        }
        
        self.logger.debug(
            f"Service success recorded: {service}",
            service=service
        )
    
    def record_failure(self, service: str, error: Exception = None):
        """Записать неудачу для сервиса."""
        self.failure_counts[service] += 1
        
        # Update dependency health
        self.dependency_health[service] = {
            "status": "unhealthy" if self.failure_counts[service] >= self.max_failures else "degraded",
            "last_failure": datetime.now(timezone.utc),
            "failure_count": self.failure_counts[service],
            "error": str(error) if error else None
        }
        
        self.logger.error(
            f"Service failure recorded: {service}",
            service=service,
            failure_count=self.failure_counts[service],
            max_failures=self.max_failures,
            error=error,
            will_use_fallback=self.should_use_fallback(service)
        )
    
    def store_fallback_data(self, service: str, data_type: str, data: Any):
        """Сохранить данные для fallback."""
        if service not in self.fallback_data:
            self.fallback_data[service] = {}
        
        self.fallback_data[service][data_type] = data
        self.last_successful_fetch[f"{service}:{data_type}"] = datetime.now(timezone.utc)
        
        self.logger.debug(
            f"Fallback data stored for {service}:{data_type}",
            service=service,
            data_type=data_type
        )
    
    def get_fallback_data(self, service: str, data_type: str = "default"):
        """Получить fallback-данные для сервиса."""
        strategy = self.fallback_strategies.get(service, {})
        
        if strategy.get("strategy") == "cached_data":
            return self._get_cached_fallback_data(service, data_type, strategy)
        elif strategy.get("strategy") == "alternative_endpoint":
            return self._try_alternative_endpoints(service, data_type, strategy)
        elif strategy.get("strategy") == "default_data":
            return strategy.get("default_data")
        else:
            # Legacy fallback
            service_data = self.fallback_data.get(service, {})
            return service_data.get(data_type)
    
    def _get_cached_fallback_data(self, service: str, data_type: str, strategy: Dict):
        """Get cached fallback data if it's still valid."""
        service_data = self.fallback_data.get(service, {})
        cached_data = service_data.get(data_type)
        
        if not cached_data:
            self.logger.warning(
                f"No cached fallback data available for {service}:{data_type}",
                service=service,
                data_type=data_type
            )
            return strategy.get("default_data")
        
        # Check if cached data is still valid
        last_fetch = self.last_successful_fetch.get(f"{service}:{data_type}")
        if last_fetch:
            age_hours = (datetime.now(timezone.utc) - last_fetch).total_seconds() / 3600
            max_age = strategy.get("max_age_hours", 1)
            
            if age_hours > max_age:
                self.logger.warning(
                    f"Cached fallback data expired for {service}:{data_type}",
                    service=service,
                    data_type=data_type,
                    age_hours=age_hours,
                    max_age_hours=max_age
                )
                return strategy.get("default_data")
        
        self.logger.info(
            f"Using cached fallback data for {service}:{data_type}",
            service=service,
            data_type=data_type
        )
        return cached_data
    
    def _try_alternative_endpoints(self, service: str, data_type: str, strategy: Dict):
        """Try alternative endpoints as fallback."""
        fallback_endpoints = strategy.get("fallback_endpoints", [])
        
        for endpoint in fallback_endpoints:
            try:
                self.logger.info(
                    f"Trying alternative endpoint for {service}",
                    service=service,
                    endpoint=endpoint
                )
                
                # This would be implemented based on specific service needs
                # For now, return cached data or default
                cached_data = self._get_cached_fallback_data(service, data_type, strategy)
                if cached_data:
                    return cached_data
                    
            except Exception as e:
                self.logger.error(
                    f"Alternative endpoint failed for {service}",
                    service=service,
                    endpoint=endpoint,
                    error=e
                )
                continue
        
        self.logger.warning(
            f"All alternative endpoints failed for {service}",
            service=service,
            attempted_endpoints=len(fallback_endpoints)
        )
        return strategy.get("default_data")
    
    def execute_with_fallback(self, service: str, operation: Callable, 
                            fallback_data_type: str = "default", **kwargs):
        """Execute operation with automatic fallback on failure."""
        operation_id = self.logger.start_operation(
            f"execute_with_fallback_{service}",
            service=service,
            operation=operation.__name__ if hasattr(operation, '__name__') else str(operation)
        )
        
        try:
            if self.should_use_fallback(service):
                self.logger.info(
                    f"Using fallback for {service} (service unhealthy)",
                    service=service,
                    operation_id=operation_id
                )
                fallback_data = self.get_fallback_data(service, fallback_data_type)
                self.logger.end_operation(operation_id, success=True, used_fallback=True)
                return fallback_data
            
            # Try normal operation
            result = operation(**kwargs)
            
            # Record success
            self.record_success(service)
            
            # Cache result for future fallback use
            self.store_fallback_data(service, fallback_data_type, result)
            
            self.logger.end_operation(operation_id, success=True, used_fallback=False)
            return result
            
        except Exception as e:
            self.logger.error(
                f"Operation failed for {service}, attempting fallback",
                service=service,
                operation_id=operation_id,
                error=e
            )
            
            # Record failure
            self.record_failure(service, e)
            
            # Try fallback
            try:
                fallback_data = self.get_fallback_data(service, fallback_data_type)
                self.logger.end_operation(
                    operation_id, 
                    success=True, 
                    used_fallback=True,
                    fallback_reason="operation_failed"
                )
                return fallback_data
            except Exception as fallback_error:
                self.logger.error(
                    f"Fallback also failed for {service}",
                    service=service,
                    operation_id=operation_id,
                    original_error=e,
                    fallback_error=fallback_error
                )
                self.logger.end_operation(operation_id, success=False)
                raise e  # Re-raise original exception
    
    def get_dependency_health_status(self) -> Dict[str, Any]:
        """Get health status of all tracked dependencies."""
        now = datetime.now(timezone.utc)
        
        health_summary = {
            "dependencies": {},
            "overall_health": "healthy",
            "unhealthy_count": 0,
            "degraded_count": 0,
            "timestamp": now.isoformat()
        }
        
        for service, health_info in self.dependency_health.items():
            status = health_info.get("status", "unknown")
            health_summary["dependencies"][service] = {
                "status": status,
                "failure_count": self.failure_counts.get(service, 0),
                "last_failure": health_info.get("last_failure").isoformat() if health_info.get("last_failure") else None,
                "last_success": self.last_successful_fetch.get(service).isoformat() if self.last_successful_fetch.get(service) else None,
                "fallback_available": service in self.fallback_strategies,
                "fallback_strategy": self.fallback_strategies.get(service, {}).get("strategy", "none")
            }
            
            if status == "unhealthy":
                health_summary["unhealthy_count"] += 1
                health_summary["overall_health"] = "critical"
            elif status == "degraded":
                health_summary["degraded_count"] += 1
                if health_summary["overall_health"] == "healthy":
                    health_summary["overall_health"] = "degraded"
        
        return health_summary
    
    def reset_service_health(self, service: str):
        """Reset health status for a service."""
        self.failure_counts[service] = 0
        if service in self.dependency_health:
            del self.dependency_health[service]
        
        self.logger.info(
            f"Service health reset: {service}",
            service=service
        )
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get statistics about fallback usage."""
        stats = {
            "services": {},
            "total_failures": sum(self.failure_counts.values()),
            "services_using_fallback": 0,
            "fallback_strategies_configured": len(self.fallback_strategies)
        }
        
        for service, failure_count in self.failure_counts.items():
            using_fallback = self.should_use_fallback(service)
            if using_fallback:
                stats["services_using_fallback"] += 1
            
            stats["services"][service] = {
                "failure_count": failure_count,
                "using_fallback": using_fallback,
                "last_success": self.last_successful_fetch.get(service).isoformat() if self.last_successful_fetch.get(service) else None,
                "strategy": self.fallback_strategies.get(service, {}).get("strategy", "none")
            }
        
        return stats


# Global fallback handler instance
fallback_handler = FallbackHandler()


def get_fallback_handler() -> FallbackHandler:
    """Get the global fallback handler instance."""
    return fallback_handler