#!/usr/bin/env python3
"""
Script to reset DexScreener circuit breaker when it's stuck open.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient

def reset_circuit_breaker():
    """Reset the DexScreener circuit breaker."""
    print("🔧 Resetting DexScreener circuit breaker...")
    
    try:
        # Create client instance
        client = ResilientDexScreenerClient(timeout=5.0, cache_ttl=30)
        
        # Check current status
        is_healthy = client.is_healthy()
        print(f"Circuit breaker status before reset: {'CLOSED' if is_healthy else 'OPEN'}")
        
        # Get current stats
        stats = client.get_stats()
        print(f"Current stats: {stats}")
        
        # Reset circuit breaker
        client.reset_circuit_breaker()
        
        # Check status after reset
        is_healthy_after = client.is_healthy()
        print(f"Circuit breaker status after reset: {'CLOSED' if is_healthy_after else 'OPEN'}")
        
        if is_healthy_after:
            print("✅ Circuit breaker successfully reset!")
        else:
            print("❌ Circuit breaker still open after reset")
            
        return is_healthy_after
        
    except Exception as e:
        print(f"❌ Error resetting circuit breaker: {e}")
        return False

if __name__ == "__main__":
    success = reset_circuit_breaker()
    sys.exit(0 if success else 1)