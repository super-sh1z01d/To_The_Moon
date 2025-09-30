#!/usr/bin/env python3
"""
Test ResilientDexScreenerClient directly to see if it works.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_resilient_client():
    """Test the resilient client directly."""
    print("🧪 Testing ResilientDexScreenerClient")
    print("=" * 40)
    
    try:
        from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
        
        # Create client with same settings as production
        client = ResilientDexScreenerClient(
            timeout=8.0,
            cache_ttl=0,
            enable_cache=False,
            enable_circuit_breaker=False
        )
        
        print("✅ Client created successfully")
        
        # Test with a known token
        mint_address = "CKVZPWFPaJArEaPnk16CXpFtFXjuCxCh95vBcS3Ppump"
        print(f"🔍 Testing with mint: {mint_address}")
        
        # Call get_pairs
        pairs = client.get_pairs(mint_address)
        
        if pairs is None:
            print("❌ get_pairs returned None")
            return False
        elif isinstance(pairs, list):
            print(f"✅ get_pairs returned list with {len(pairs)} pairs")
            
            if pairs:
                pair = pairs[0]
                print(f"📊 First pair:")
                print(f"   DEX: {pair.get('dexId', 'unknown')}")
                print(f"   Price USD: ${pair.get('priceUsd', 'unknown')}")
                print(f"   Liquidity: ${pair.get('liquidity', {}).get('usd', 'unknown')}")
                print(f"   Volume 24h: ${pair.get('volume', {}).get('h24', 'unknown')}")
                
                # Check if this data would produce a good score
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                volume_24h = pair.get('volume', {}).get('h24', 0)
                txns_5m = pair.get('txns', {}).get('m5', {})
                buys = txns_5m.get('buys', 0) if txns_5m else 0
                sells = txns_5m.get('sells', 0) if txns_5m else 0
                
                print(f"\n📈 Scoring potential:")
                print(f"   Liquidity: ${liquidity:,.2f} ({'✅ Good' if liquidity > 10000 else '⚠️ Low'})")
                print(f"   Volume 24h: ${volume_24h:,.2f} ({'✅ Good' if volume_24h > 1000 else '⚠️ Low'})")
                print(f"   Transactions 5m: {buys + sells} ({'✅ Active' if buys + sells > 0 else '❌ No activity'})")
                
            return True
        else:
            print(f"❌ get_pairs returned unexpected type: {type(pairs)}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing client: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_resilient_client()
    sys.exit(0 if success else 1)