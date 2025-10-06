"""
Enhanced alert configuration for comprehensive monitoring.

This module provides improved alert rules that ensure all important
alerts are sent to Telegram while preventing spam.
"""

import os
import logging
from typing import List

from .alert_manager import AlertRule, AlertLevel, AlertChannel

log = logging.getLogger("alert_config")


def get_enhanced_alert_rules() -> List[AlertRule]:
    """
    Get enhanced alert rules with proper Telegram integration.
    
    Returns:
        List of AlertRule objects configured for comprehensive monitoring
    """
    # Check Telegram configuration
    telegram_available = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
    
    if telegram_available:
        log.info("Telegram configuration found - enabling comprehensive Telegram alerts")
        # Use Telegram + fallback channels
        critical_channels = [AlertChannel.TELEGRAM, AlertChannel.LOG, AlertChannel.CONSOLE]
        error_channels = [AlertChannel.TELEGRAM, AlertChannel.LOG]
        warning_channels = [AlertChannel.TELEGRAM, AlertChannel.LOG]
        info_channels = [AlertChannel.LOG]  # Info only to logs
    else:
        log.warning("Telegram configuration missing - using LOG/CONSOLE only")
        # Fallback to LOG/CONSOLE only
        critical_channels = [AlertChannel.LOG, AlertChannel.CONSOLE]
        error_channels = [AlertChannel.LOG]
        warning_channels = [AlertChannel.LOG]
        info_channels = [AlertChannel.LOG]
    
    rules = [
        # Critical alerts - immediate notification
        AlertRule(
            component_pattern="*",
            min_level=AlertLevel.CRITICAL,
            cooldown_minutes=2,  # Shorter cooldown for critical
            max_frequency_per_hour=20,  # Allow more critical alerts
            channels=critical_channels
        ),
        
        # System memory alerts - important for stability
        AlertRule(
            component_pattern="system.memory*",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=10,
            max_frequency_per_hour=6,
            channels=warning_channels
        ),
        
        # Scheduler alerts - include WARNING level for delays
        AlertRule(
            component_pattern="scheduler*",
            min_level=AlertLevel.WARNING,  # Changed from ERROR to WARNING
            cooldown_minutes=5,  # Shorter cooldown for scheduler issues
            max_frequency_per_hour=8,  # Allow more scheduler alerts
            channels=warning_channels
        ),
        
        # DexScreener API alerts
        AlertRule(
            component_pattern="dexscreener*",
            min_level=AlertLevel.ERROR,
            cooldown_minutes=10,
            max_frequency_per_hour=6,
            channels=error_channels
        ),
        
        # Database alerts - critical for system operation
        AlertRule(
            component_pattern="database*",
            min_level=AlertLevel.WARNING,  # Include warnings for DB
            cooldown_minutes=5,
            max_frequency_per_hour=10,
            channels=error_channels  # Treat DB warnings as errors
        ),
        
        # Token processing alerts - important for business logic
        AlertRule(
            component_pattern="token*",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=15,
            max_frequency_per_hour=4,
            channels=warning_channels
        ),
        
        # API circuit breaker alerts
        AlertRule(
            component_pattern="*.circuit_breaker",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=10,
            max_frequency_per_hour=6,
            channels=warning_channels
        ),
        
        # Memory leak detection alerts
        AlertRule(
            component_pattern="*.memory.leak_detection",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=30,
            max_frequency_per_hour=2,
            channels=warning_channels
        ),
        
        # Performance degradation alerts
        AlertRule(
            component_pattern="performance*",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=20,
            max_frequency_per_hour=3,
            channels=warning_channels
        ),
        
        # Catch-all for other system components
        AlertRule(
            component_pattern="system*",
            min_level=AlertLevel.WARNING,
            cooldown_minutes=15,
            max_frequency_per_hour=4,
            channels=warning_channels
        )
    ]
    
    log.info(
        f"Generated {len(rules)} enhanced alert rules",
        extra={
            "telegram_enabled": telegram_available,
            "rules_count": len(rules)
        }
    )
    
    return rules


def apply_enhanced_alert_rules(alert_manager) -> int:
    """
    Apply enhanced alert rules to the alert manager.
    
    Args:
        alert_manager: AlertManager instance
        
    Returns:
        Number of rules applied
    """
    try:
        # Clear existing rules
        alert_manager._alert_rules.clear()
        
        # Get and apply enhanced rules
        rules = get_enhanced_alert_rules()
        
        for rule in rules:
            alert_manager.add_alert_rule(rule)
        
        log.info(
            f"Applied {len(rules)} enhanced alert rules successfully",
            extra={"rules_applied": len(rules)}
        )
        
        return len(rules)
        
    except Exception as e:
        log.error(
            "Failed to apply enhanced alert rules",
            extra={"error": str(e)},
            exc_info=True
        )
        return 0


def get_alert_rule_summary() -> dict:
    """Get a summary of current alert rule configuration."""
    telegram_available = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
    rules = get_enhanced_alert_rules()
    
    summary = {
        "telegram_enabled": telegram_available,
        "total_rules": len(rules),
        "rules_by_level": {
            "critical": len([r for r in rules if r.min_level == AlertLevel.CRITICAL]),
            "error": len([r for r in rules if r.min_level == AlertLevel.ERROR]),
            "warning": len([r for r in rules if r.min_level == AlertLevel.WARNING]),
            "info": len([r for r in rules if r.min_level == AlertLevel.INFO])
        },
        "components_covered": [
            "scheduler (WARNING+)",
            "system.memory (WARNING+)",
            "database (WARNING+)",
            "dexscreener (ERROR+)",
            "token processing (WARNING+)",
            "circuit breakers (WARNING+)",
            "memory leaks (WARNING+)",
            "performance (WARNING+)",
            "all critical (CRITICAL)"
        ]
    }
    
    return summary