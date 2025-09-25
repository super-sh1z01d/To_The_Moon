#!/usr/bin/env python3
"""
Test script for Telegram alerts.

Usage:
1. Set environment variables:
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"

2. Run: python scripts/test_telegram_alert.py
"""

import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, 'src')

from monitoring.alert_manager import AlertManager, AlertChannel, AlertRule, AlertLevel
from monitoring.models import HealthAlert

def test_telegram_alert():
    """Test sending a Telegram alert."""
    
    # Check if Telegram is configured
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ Telegram not configured!")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        return False
    
    print(f"✅ Telegram configured: bot_token={bot_token[:10]}..., chat_id={chat_id}")
    
    # Create alert manager
    alert_manager = AlertManager()
    
    # Add rule for test alerts with Telegram channel
    test_rule = AlertRule(
        component_pattern="test_*",
        min_level=AlertLevel.INFO,
        cooldown_minutes=0,  # No cooldown for testing
        channels=[AlertChannel.TELEGRAM, AlertChannel.CONSOLE]
    )
    alert_manager.add_alert_rule(test_rule)
    
    # Create test alert
    test_alert = HealthAlert(
        component="test_component",
        level=AlertLevel.WARNING,
        message="🧪 Test alert from To The Moon monitoring system",
        context={
            "test_type": "telegram_integration",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": "production"
        },
        timestamp=datetime.now(timezone.utc)
    )
    
    # Send alert
    print("📤 Sending test alert...")
    success = alert_manager.send_alert(test_alert)
    
    if success:
        print("✅ Test alert sent successfully!")
        print("Check your Telegram chat for the message.")
    else:
        print("❌ Failed to send test alert")
    
    return success

if __name__ == "__main__":
    test_telegram_alert()