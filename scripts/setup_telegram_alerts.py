#!/usr/bin/env python3
"""
Setup Telegram alerts for critical system events.
"""

import sys
sys.path.insert(0, 'src')

from monitoring.alert_manager import get_alert_manager, AlertRule, AlertLevel, AlertChannel

def setup_production_alerts():
    """Setup alert rules for production monitoring."""
    
    alert_manager = get_alert_manager()
    
    # Critical system alerts - send to Telegram immediately
    critical_rule = AlertRule(
        component_pattern="*",  # All components
        min_level=AlertLevel.CRITICAL,
        cooldown_minutes=5,  # 5 min cooldown for critical alerts
        max_frequency_per_hour=12,  # Max 12 critical alerts per hour
        channels=[AlertChannel.TELEGRAM, AlertChannel.LOG, AlertChannel.CONSOLE]
    )
    
    # API errors - send to Telegram for ERROR and above
    api_rule = AlertRule(
        component_pattern="dexscreener*",
        min_level=AlertLevel.ERROR,
        cooldown_minutes=10,  # 10 min cooldown for API errors
        max_frequency_per_hour=6,  # Max 6 API error alerts per hour
        channels=[AlertChannel.TELEGRAM, AlertChannel.LOG]
    )
    
    # Scheduler issues - send to Telegram for ERROR and above
    scheduler_rule = AlertRule(
        component_pattern="scheduler*",
        min_level=AlertLevel.ERROR,
        cooldown_minutes=15,  # 15 min cooldown for scheduler issues
        max_frequency_per_hour=4,  # Max 4 scheduler alerts per hour
        channels=[AlertChannel.TELEGRAM, AlertChannel.LOG]
    )
    
    # Database issues - send to Telegram immediately
    database_rule = AlertRule(
        component_pattern="database*",
        min_level=AlertLevel.ERROR,
        cooldown_minutes=5,  # 5 min cooldown for DB issues
        max_frequency_per_hour=8,  # Max 8 DB alerts per hour
        channels=[AlertChannel.TELEGRAM, AlertChannel.LOG, AlertChannel.CONSOLE]
    )
    
    # System resource alerts - WARNING and above
    system_rule = AlertRule(
        component_pattern="system*",
        min_level=AlertLevel.WARNING,
        cooldown_minutes=30,  # 30 min cooldown for system resources
        max_frequency_per_hour=2,  # Max 2 system alerts per hour
        channels=[AlertChannel.TELEGRAM, AlertChannel.LOG]
    )
    
    # Add all rules
    rules = [critical_rule, api_rule, scheduler_rule, database_rule, system_rule]
    
    for rule in rules:
        alert_manager.add_alert_rule(rule)
        print(f"✅ Added alert rule: {rule.component_pattern} (min_level: {rule.min_level.value})")
    
    print(f"\n🚀 Setup complete! {len(rules)} alert rules configured for Telegram notifications.")
    print("\nAlert rules:")
    print("- 🚨 CRITICAL: All components → Telegram + Log + Console")
    print("- ❌ ERROR: API issues → Telegram + Log") 
    print("- ❌ ERROR: Scheduler issues → Telegram + Log")
    print("- ❌ ERROR: Database issues → Telegram + Log + Console")
    print("- ⚠️ WARNING: System resources → Telegram + Log")

if __name__ == "__main__":
    setup_production_alerts()