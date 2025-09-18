#!/usr/bin/env python3
"""
Simple CLI script to get pool URLs for NotArb bot
Usage: python scripts/notarb_pools.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.notarb_pools import NotArbPoolsGenerator


def main():
    """Get and print pool URLs for NotArb bot"""
    try:
        generator = NotArbPoolsGenerator()
        
        # Get current minimum score setting
        min_score = generator.get_notarb_min_score()
        print(f"🎯 NotArb minimum score threshold: {min_score}")
        
        # Get top tokens with pools
        tokens_data = generator.get_top_tokens_with_pools(limit=3)
        
        if not tokens_data:
            print("❌ No tokens found above minimum score threshold")
            return 1
        
        print(f"\n📊 Found {len(tokens_data)} tokens:")
        print("-" * 60)
        
        total_pools = 0
        for i, token in enumerate(tokens_data, 1):
            print(f"#{i} {token['symbol']:8s} Score: {token['score']:.3f} Pools: {len(token['pools'])}")
            total_pools += len(token['pools'])
        
        print("-" * 60)
        print(f"Total pools: {total_pools}")
        
        # Generate and print token pools with metadata
        result = generator.generate_token_pools_with_metadata(tokens_data)
        
        print(f"\n🔗 Token pools for NotArb bot:")
        for i, token in enumerate(result.get("tokens", []), 1):
            print(f"{i:2d}. {token['symbol']} ({token['mint_address'][:8]}...)")
            print(f"    Score: {token['score']:.3f}")
            print(f"    Pools: {token['pools']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())