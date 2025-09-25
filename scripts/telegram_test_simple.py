#!/usr/bin/env python3
"""
Simple Telegram test that works with explicit credentials.
"""

import httpx
import sys
import os

# Explicit credentials
BOT_TOKEN = "8024053739:AAHju6Np8QS50SuBsCoIOlvQ1e1eQOSL51o"
CHAT_ID = "132303842"

def send_telegram_message(message):
    """Send message to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"✅ Message sent successfully!")
                    print(f"Message ID: {result['result']['message_id']}")
                    return True
                else:
                    print(f"❌ Telegram API error: {result}")
                    return False
            else:
                print(f"❌ HTTP error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    message = """🚨 **CRITICAL ALERT**

🎯 **To The Moon Production System**
📍 Component: `telegram_test`
🕐 Time: Production Ready
📋 Status: `All systems operational`

✅ Telegram alerts are now **ACTIVE** and working!

This is a test of the emergency alert system. 
In case of real emergency, you will receive notifications here.

🔗 System: Production Ready"""

    print("📤 Sending production-ready Telegram alert...")
    success = send_telegram_message(message)
    
    if success:
        print("\n🎉 SUCCESS! Telegram alerts are working!")
        print("Check your Telegram for the alert message.")
    else:
        print("\n❌ FAILED! Check the error messages above.")