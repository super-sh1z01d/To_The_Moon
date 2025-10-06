#!/usr/bin/env python3
"""
Test script to verify spam data in API response.
"""

import sys
import os
import requests
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_tokens_api():
    """Test tokens API for spam data."""
    print("🔍 Testing tokens API for spam data...")
    
    try:
        # Test local API
        response = requests.get("http://localhost:8000/tokens?limit=5")
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            return
        
        data = response.json()
        tokens = data.get("items", [])
        
        print(f"✅ Got {len(tokens)} tokens from API")
        
        spam_count = 0
        for token in tokens:
            mint = token.get("mint_address", "unknown")[:8] + "..."
            name = token.get("name", "Unknown")
            spam_metrics = token.get("spam_metrics")
            
            if spam_metrics:
                spam_pct = spam_metrics.get("spam_percentage", 0)
                risk_level = spam_metrics.get("risk_level", "unknown")
                print(f"📊 {name} ({mint}): {spam_pct:.1f}% spam ({risk_level})")
                spam_count += 1
            else:
                print(f"⚪ {name} ({mint}): No spam data")
        
        print(f"\n📈 Summary: {spam_count}/{len(tokens)} tokens have spam data")
        
        if spam_count > 0:
            print("✅ Spam data is working in API!")
        else:
            print("⚠️  No spam data found - run spam monitoring first")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API - make sure server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")


def main():
    """Main test function."""
    test_tokens_api()


if __name__ == "__main__":
    main()