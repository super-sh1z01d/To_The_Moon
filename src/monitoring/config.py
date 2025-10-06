"""
Configuration management system for monitoring components.

This module provides configuration loading, validation, and hot-reloading
capabilities for the monitoring system, integrating with the existing
settings infrastructure.
"""

import logging
import os
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.config import get_config
from src.domain.settings.service import SettingsService
from .models import MonitoringConfig, RecoveryConfig, CircuitBreakerConfig

log = logging.getLogger("monitoring.config")


class MonitoringSettings(BaseSettings):
    """
    Monitoring system settings with environment variable support.
    
    These settings can be overridden by environment variables with
    MONITORING_ prefix (e.g., MONITORING_HEALTH_CHECK_INTERVAL).
    """
    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Health check intervals
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    resource_check_interval: int = Field(default=60, description="Resource check interval in seconds")
    performance_check_interval: int = Field(default=120, description="Performance check interval in seconds")
    alert_cooldown: int = Field(default=300, description="Alert cooldown period in seconds")
    
    # Resource thresholds (updated for servers with large memory)
    memory_warning_threshold: float = Field(default=8000.0, description="Memory warning threshold in MB")
    memory_critical_threshold: float = Field(default=12000.0, description="Memory critical threshold in MB")
    cpu_warning_threshold: float = Field(default=70.0, description="CPU warning threshold in percentage")
    cpu_critical_threshold: float = Field(default=80.0, description="CPU critical threshold in percentage")
    disk_warning_threshold: float = Field(default=80.0, description="Disk warning threshold in percentage")
    disk_critical_threshold: float = Field(default=90.0, description="Disk critical threshold in percentage")
    
    # API performance thresholds
    api_response_time_warning: float = Field(default=2000.0, description="API response time warning in ms")
    api_response_time_critical: float = Field(default=5000.0, description="API response time critical in ms")
    api_error_rate_warning: float = Field(default=10.0, description="API error rate warning in percentage")
    api_error_rate_critical: float = Field(default=20.0, description="API error rate critical in percentage")
    
    # Scheduler thresholds
    scheduler_processing_time_warning: float = Field(default=300.0, description="Scheduler processing time warning in seconds")
    scheduler_processing_time_critical: float = Field(default=600.0, description="Scheduler processing time critical in seconds")
    tokens_per_minute_warning: float = Field(default=1.0, description="Minimum expected tokens per minute")
    
    # Recovery settings
    max_restart_attempts: int = Field(default=3, description="Maximum restart attempts")
    restart_cooldown: int = Field(default=300, description="Restart cooldown in seconds")
    graceful_shutdown_timeout: int = Field(default=30, description="Graceful shutdown timeout in seconds")
    emergency_restart_threshold: int = Field(default=600, description="Emergency restart threshold in seconds")
    
    # Circuit breaker settings
    circuit_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_recovery_timeout: int = Field(default=60, description="Circuit breaker recovery timeout in seconds")
    circuit_half_open_max_calls: int = Field(default=3, description="Circuit breaker half-open max calls")
    
    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    base_retry_delay: float = Field(default=1.0, description="Base retry delay in seconds")
    max_retry_delay: float = Field(default=30.0, description="Maximum retry delay in seconds")
    retry_exponential_base: float = Field(default=2.0, description="Retry exponential backoff base")
    
    # Monitoring features
    enable_external_monitoring: bool = Field(default=True, description="Enable external monitoring script")
    enable_systemd_watchdog: bool = Field(default=True, description="Enable systemd watchdog integration")
    enable_performance_tracking: bool = Field(default=True, description="Enable performance tracking")
    enable_predictive_alerts: bool = Field(default=True, description="Enable predictive alerting")
    
    @field_validator('memory_critical_threshold')
    @classmethod
    def memory_critical_must_be_higher(cls, v, info):
        if info.data and 'memory_warning_threshold' in info.data and v <= info.data['memory_warning_threshold']:
            raise ValueError('memory_critical_threshold must be higher than memory_warning_threshold')
        return v
    
    @field_validator('cpu_critical_threshold')
    @classmethod
    def cpu_critical_must_be_higher(cls, v, info):
        if info.data and 'cpu_warning_threshold' in info.data and v <= info.data['cpu_warning_threshold']:
            raise ValueError('cpu_critical_threshold must be higher than cpu_warning_threshold')
        return v
    
    @field_validator('api_response_time_critical')
    @classmethod
    def api_critical_must_be_higher(cls, v, info):
        if info.data and 'api_response_time_warning' in info.data and v <= info.data['api_response_time_warning']:
            raise ValueError('api_response_time_critical must be higher than api_response_time_warning')
        return v


class ConfigurationManager:
    """
    Manages monitoring configuration with hot-reloading capabilities.
    
    Integrates with the existing settings system and provides configuration
    change detection and notification.
    """
    
    def __init__(self, db_session_factory: Optional[Callable] = None):
        self._settings = MonitoringSettings()
        self._db_session_factory = db_session_factory
        self._config_cache: Optional[Dict[str, Any]] = None
        self._last_reload = datetime.utcnow()
        self._change_callbacks: Dict[str, Callable] = {}
        
        # Load initial configuration
        self._reload_config()
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        config_dict = self._get_effective_config()
        
        return MonitoringConfig(
            health_check_interval=config_dict["health_check_interval"],
            resource_check_interval=config_dict["resource_check_interval"],
            performance_check_interval=config_dict["performance_check_interval"],
            alert_cooldown=config_dict["alert_cooldown"],
            memory_warning_threshold=config_dict["memory_warning_threshold"],
            memory_critical_threshold=config_dict["memory_critical_threshold"],
            cpu_warning_threshold=config_dict["cpu_warning_threshold"],
            cpu_critical_threshold=config_dict["cpu_critical_threshold"],
            disk_warning_threshold=config_dict["disk_warning_threshold"],
            disk_critical_threshold=config_dict["disk_critical_threshold"],
            api_response_time_warning=config_dict["api_response_time_warning"],
            api_response_time_critical=config_dict["api_response_time_critical"],
            api_error_rate_warning=config_dict["api_error_rate_warning"],
            api_error_rate_critical=config_dict["api_error_rate_critical"],
            scheduler_processing_time_warning=config_dict["scheduler_processing_time_warning"],
            scheduler_processing_time_critical=config_dict["scheduler_processing_time_critical"],
            tokens_per_minute_warning=config_dict["tokens_per_minute_warning"]
        )
    
    def get_recovery_config(self) -> RecoveryConfig:
        """Get recovery configuration."""
        config_dict = self._get_effective_config()
        
        return RecoveryConfig(
            max_restart_attempts=config_dict["max_restart_attempts"],
            restart_cooldown=config_dict["restart_cooldown"],
            graceful_shutdown_timeout=config_dict["graceful_shutdown_timeout"],
            emergency_restart_threshold=config_dict["emergency_restart_threshold"],
            circuit_failure_threshold=config_dict["circuit_failure_threshold"],
            circuit_recovery_timeout=config_dict["circuit_recovery_timeout"],
            circuit_half_open_max_calls=config_dict["circuit_half_open_max_calls"],
            max_retries=config_dict["max_retries"],
            base_retry_delay=config_dict["base_retry_delay"],
            max_retry_delay=config_dict["max_retry_delay"],
            retry_exponential_base=config_dict["retry_exponential_base"]
        )
    
    def get_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Get circuit breaker configuration."""
        config_dict = self._get_effective_config()
        
        return CircuitBreakerConfig(
            failure_threshold=config_dict["circuit_failure_threshold"],
            recovery_timeout=config_dict["circuit_recovery_timeout"],
            half_open_max_calls=config_dict["circuit_half_open_max_calls"],
            success_threshold=2,  # Fixed value for now
            call_timeout=10.0,  # Fixed value for now
            slow_call_threshold=5.0,  # Fixed value for now
            slow_call_rate_threshold=50.0  # Fixed value for now
        )
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a monitoring feature is enabled."""
        config_dict = self._get_effective_config()
        feature_key = f"enable_{feature}"
        return config_dict.get(feature_key, True)
    
    def register_change_callback(self, key: str, callback: Callable[[str, Any, Any], None]):
        """Register callback for configuration changes."""
        self._change_callbacks[key] = callback
        log.info(f"Registered configuration change callback for {key}")
    
    def unregister_change_callback(self, key: str):
        """Unregister configuration change callback."""
        if key in self._change_callbacks:
            del self._change_callbacks[key]
            log.info(f"Unregistered configuration change callback for {key}")
    
    def reload_config(self) -> bool:
        """Manually reload configuration and detect changes."""
        return self._reload_config()
    
    def _reload_config(self) -> bool:
        """Internal method to reload configuration."""
        old_config = self._config_cache.copy() if self._config_cache else {}
        
        # Reload from environment and database
        new_settings = MonitoringSettings()
        new_config = self._merge_with_database_settings(new_settings.model_dump())
        
        # Detect changes
        changes_detected = False
        if old_config != new_config:
            changes_detected = True
            self._notify_config_changes(old_config, new_config)
        
        self._config_cache = new_config
        self._last_reload = datetime.utcnow()
        
        if changes_detected:
            log.info("Configuration reloaded with changes detected")
        else:
            log.debug("Configuration reloaded, no changes detected")
        
        return changes_detected
    
    def _get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration, reloading if necessary."""
        # Check if we need to reload (every 30 seconds)
        if (datetime.utcnow() - self._last_reload).total_seconds() > 30:
            self._reload_config()
        
        return self._config_cache or {}
    
    def _merge_with_database_settings(self, env_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment configuration with database settings."""
        if not self._db_session_factory:
            return env_config
        
        try:
            from src.adapters.db.base import SessionLocal
            session_factory = self._db_session_factory or SessionLocal
            
            with session_factory() as session:
                settings_service = SettingsService(session)
                
                # Define mapping from database settings to monitoring config
                db_mapping = {
                    "monitoring_health_check_interval": "health_check_interval",
                    "monitoring_resource_check_interval": "resource_check_interval",
                    "monitoring_alert_cooldown": "alert_cooldown",
                    "monitoring_memory_warning_mb": "memory_warning_threshold",
                    "monitoring_memory_critical_mb": "memory_critical_threshold",
                    "monitoring_cpu_warning_percent": "cpu_warning_threshold",
                    "monitoring_cpu_critical_percent": "cpu_critical_threshold",
                    "monitoring_api_response_warning_ms": "api_response_time_warning",
                    "monitoring_api_response_critical_ms": "api_response_time_critical",
                    "monitoring_api_error_warning_percent": "api_error_rate_warning",
                    "monitoring_api_error_critical_percent": "api_error_rate_critical",
                    "monitoring_enable_external": "enable_external_monitoring",
                    "monitoring_enable_systemd_watchdog": "enable_systemd_watchdog",
                    "monitoring_enable_performance_tracking": "enable_performance_tracking",
                    "monitoring_enable_predictive_alerts": "enable_predictive_alerts"
                }
                
                # Override with database values
                merged_config = env_config.copy()
                for db_key, config_key in db_mapping.items():
                    db_value = settings_service.get(db_key)
                    if db_value is not None:
                        try:
                            # Convert to appropriate type
                            if config_key.startswith("enable_"):
                                merged_config[config_key] = db_value.lower() in ("true", "1", "yes", "on")
                            elif "threshold" in config_key or "warning" in config_key or "critical" in config_key:
                                merged_config[config_key] = float(db_value)
                            elif "interval" in config_key or "cooldown" in config_key:
                                merged_config[config_key] = int(db_value)
                            else:
                                merged_config[config_key] = db_value
                        except (ValueError, TypeError) as e:
                            log.warning(f"Invalid database setting {db_key}={db_value}: {e}")
                
                return merged_config
                
        except Exception as e:
            log.warning(f"Failed to load database settings: {e}")
            return env_config
    
    def _notify_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """Notify registered callbacks about configuration changes."""
        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                log.info(f"Configuration changed: {key} = {old_value} -> {new_value}")
                
                # Notify callbacks
                for callback_key, callback in self._change_callbacks.items():
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        log.error(f"Error in configuration change callback {callback_key}: {e}")
    
    def validate_configuration(self) -> Dict[str, str]:
        """Validate current configuration and return any errors."""
        errors = {}
        config_dict = self._get_effective_config()
        
        try:
            # Validate monitoring config
            MonitoringConfig(**{
                k: v for k, v in config_dict.items() 
                if k in MonitoringConfig.__dataclass_fields__
            })
        except Exception as e:
            errors["monitoring"] = str(e)
        
        try:
            # Validate recovery config
            RecoveryConfig(**{
                k: v for k, v in config_dict.items() 
                if k in RecoveryConfig.__dataclass_fields__
            })
        except Exception as e:
            errors["recovery"] = str(e)
        
        try:
            # Validate circuit breaker config
            CircuitBreakerConfig(
                failure_threshold=config_dict["circuit_failure_threshold"],
                recovery_timeout=config_dict["circuit_recovery_timeout"],
                half_open_max_calls=config_dict["circuit_half_open_max_calls"]
            )
        except Exception as e:
            errors["circuit_breaker"] = str(e)
        
        return errors
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration for debugging/backup."""
        return {
            "effective_config": self._get_effective_config(),
            "last_reload": self._last_reload.isoformat(),
            "validation_errors": self.validate_configuration()
        }


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_monitoring_config_manager() -> ConfigurationManager:
    """Get global monitoring configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_monitoring_config() -> MonitoringConfig:
    """Get current monitoring configuration."""
    return get_monitoring_config_manager().get_monitoring_config()


def get_recovery_config() -> RecoveryConfig:
    """Get current recovery configuration."""
    return get_monitoring_config_manager().get_recovery_config()


def get_circuit_breaker_config() -> CircuitBreakerConfig:
    """Get current circuit breaker configuration."""
    return get_monitoring_config_manager().get_circuit_breaker_config()


def is_monitoring_feature_enabled(feature: str) -> bool:
    """Check if a monitoring feature is enabled."""
    return get_monitoring_config_manager().is_feature_enabled(feature)