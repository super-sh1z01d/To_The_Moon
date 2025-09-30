#!/usr/bin/env python3
"""
Debug script to check DexScreener data quality and API responses.
This will help us understand if the issue is in the data we're getting.
"""

import sys
import os
import json
import requests
from datetime import datetime

def test_dexscreener_api():
    """Test DexScreener API directly with a known token."""
    print("🔍 TESTING DEXSCREENER API DIRECTLY")
    print("=" * 40)
    
    # Get a token from our system first
    try:
        response = requests.get("http://67.213.119.189/tokens?limit=1")
        response.raise_for_status()
        tokens = response.json().get('items', [])
        
        if not tokens:
            print("❌ No tokens found in system")
            return False
            
        token = tokens[0]
        mint_address = token.get('mint_address')
        symbol = token.get('symbol', 'unknown')
        
        print(f"📋 Testing with token: {symbol} ({mint_address})")
        print()
        
    except Exception as e:
        print(f"❌ Error getting token from system: {e}")
        return False
    
    # Test DexScreener API directly
    try:
        dex_url = f"https://api.dexscreener.com/token-pairs/v1/solana/{mint_address}"
        print(f"🌐 Calling DexScreener API: {dex_url}")
        
        response = requests.get(dex_url, timeout=10)
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            
            print(f"📈 Found {len(pairs)} pairs")
            
            if pairs:
                # Analyze first pair
                pair = pairs[0] if isinstance(pairs, list) else pairs
                print(f"🔍 First pair analysis:")
                print(f"   DEX: {pair.get('dexId', 'unknown')}")
                print(f"   Base token: {pair.get('baseToken', {}).get('symbol', 'unknown')}")
                print(f"   Quote token: {pair.get('quoteToken', {}).get('symbol', 'unknown')}")
                print(f"   Price USD: ${pair.get('priceUsd', 'unknown')}")
                print(f"   Liquidity USD: ${pair.get('liquidity', {}).get('usd', 'unknown')}")
                print(f"   Volume 24h: ${pair.get('volume', {}).get('h24', 'unknown')}")
                print(f"   Price change 5m: {pair.get('priceChange', {}).get('m5', 'unknown')}%")
                print(f"   Transactions 5m: {pair.get('txns', {}).get('m5', {}).get('buys', 'unknown')} buys, {pair.get('txns', {}).get('m5', {}).get('sells', 'unknown')} sells")
                
                # Check for data quality issues
                liquidity = pair.get('liquidity', {}).get('usd')
                volume_24h = pair.get('volume', {}).get('h24')
                txns_5m = pair.get('txns', {}).get('m5', {})
                
                print(f"\n🔍 Data Quality Check:")
                if liquidity is None or liquidity == 0:
                    print(f"   ⚠️ No liquidity data")
                else:
                    print(f"   ✅ Liquidity: ${liquidity:,.2f}")
                
                if volume_24h is None or volume_24h == 0:
                    print(f"   ⚠️ No volume data")
                else:
                    print(f"   ✅ Volume 24h: ${volume_24h:,.2f}")
                
                buys = txns_5m.get('buys', 0) if txns_5m else 0
                sells = txns_5m.get('sells', 0) if txns_5m else 0
                if buys == 0 and sells == 0:
                    print(f"   ⚠️ No transaction data")
                else:
                    print(f"   ✅ Transactions 5m: {buys + sells} total")
                
            else:
                print("❌ No pairs found for this token")
                
        elif response.status_code == 429:
            print("❌ Rate limited (429) - too many requests")
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Error calling DexScreener API: {e}")
        return False
    
    print()
    return True

def check_recent_logs():
    """Check recent logs for API issues."""
    print("📋 CHECKING RECENT API LOGS")
    print("=" * 30)
    
    try:
        response = requests.get("http://67.213.119.189/logs/?limit=50")
        response.raise_for_status()
        logs = response.json()
        
        # Count different types of messages
        api_success = 0
        api_failures = 0
        pairs_failed = 0
        circuit_breaker = 0
        
        for log in logs:
            msg = log.get('msg', '')
            if 'HTTP/1.1 200 OK' in msg:
                api_success += 1
            elif 'pairs_fetch_failed' in msg:
                pairs_failed += 1
            elif 'circuit breaker' in msg.lower():
                circuit_breaker += 1
            elif any(code in msg for code in ['429', '500', '502', '503']):
                api_failures += 1
        
        print(f"📊 Recent API Activity (last 50 logs):")
        print(f"   ✅ Successful API calls: {api_success}")
        print(f"   ❌ Failed API calls: {api_failures}")
        print(f"   ⚠️ Pairs fetch failed: {pairs_failed}")
        print(f"   🔒 Circuit breaker events: {circuit_breaker}")
        
        if api_success == 0:
            print(f"\n🚨 CRITICAL: No successful API calls detected!")
        elif pairs_failed > api_success:
            print(f"\n⚠️ WARNING: More failures than successes")
        else:
            print(f"\n✅ API seems to be working")
            
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False
    
    print()
    return True

def analyze_token_processing():
    """Analyze how tokens are being processed."""
    print("🔄 ANALYZING TOKEN PROCESSING")
    print("=" * 35)
    
    try:
        # Get tokens and check processing times
        response = requests.get("http://67.213.119.189/tokens?limit=10")
        response.raise_for_status()
        data = response.json()
        tokens = data.get('items', [])
        
        if not tokens:
            print("❌ No tokens found")
            return False
        
        now = datetime.utcnow()
        
        print(f"📊 Processing Analysis:")
        recent_count = 0
        old_count = 0
        
        for token in tokens:
            last_processed = token.get('last_processed_at')
            if last_processed:
                # Parse timestamp
                try:
                    processed_time = datetime.fromisoformat(last_processed.replace('Z', '+00:00'))
                    age_minutes = (now - processed_time.replace(tzinfo=None)).total_seconds() / 60
                    
                    if age_minutes < 5:
                        recent_count += 1
                    else:
                        old_count += 1
                        
                except Exception:
                    old_count += 1
            else:
                old_count += 1
        
        print(f"   🕐 Recently processed (< 5 min): {recent_count}")
        print(f"   🕕 Older processing (> 5 min): {old_count}")
        
        if recent_count == 0:
            print(f"\n🚨 CRITICAL: No tokens processed recently!")
        elif recent_count < len(tokens) / 2:
            print(f"\n⚠️ WARNING: Most tokens not recently processed")
        else:
            print(f"\n✅ Tokens are being processed regularly")
            
    except Exception as e:
        print(f"❌ Error analyzing processing: {e}")
        return False
    
    print()
    return True

if __name__ == "__main__":
    print("🔍 DexScreener Data Quality Diagnostic")
    print("=====================================")
    print()
    
    success = True
    
    success &= check_recent_logs()
    success &= test_dexscreener_api()
    success &= analyze_token_processing()
    
    if success:
        print("✅ Diagnostic completed. Check results above for issues.")
    else:
        print("❌ Diagnostic failed. Check API connectivity.")
    
    sys.exit(0 if success else 1)