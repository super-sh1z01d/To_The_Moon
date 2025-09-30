#!/usr/bin/env python3
"""
Diagnostic script to analyze why token scores are so low.
This will help us understand if the issue is in:
1. DexScreener data quality
2. Scoring algorithm parameters  
3. Token selection/filtering
"""

import sys
import os
import json
import requests
from datetime import datetime

def get_token_data():
    """Get current token data from API."""
    try:
        response = requests.get("http://67.213.119.189/tokens?limit=10&sort=score_desc")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching token data: {e}")
        return None

def get_settings():
    """Get current system settings."""
    try:
        response = requests.get("http://67.213.119.189/settings/")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching settings: {e}")
        return None

def analyze_token_scores():
    """Analyze current token scores and identify issues."""
    print("🔍 ANALYZING TOKEN SCORING ISSUES")
    print("=" * 50)
    
    # Get data
    token_data = get_token_data()
    settings = get_settings()
    
    if not token_data or not settings:
        return False
    
    tokens = token_data.get('items', [])
    meta = token_data.get('meta', {})
    
    print(f"📊 **Current System Status:**")
    print(f"   Total tokens: {meta.get('total', 'unknown')}")
    print(f"   Min score filter: {meta.get('min_score', 'unknown')}")
    print(f"   Active model: {settings.get('scoring_model_active', 'unknown')}")
    print()
    
    # Analyze score distribution
    if tokens:
        scores = [t.get('score', 0) for t in tokens if t.get('score') is not None]
        print(f"📈 **Score Distribution:**")
        print(f"   Highest score: {max(scores):.4f}")
        print(f"   Lowest score: {min(scores):.4f}")
        print(f"   Average score: {sum(scores)/len(scores):.4f}")
        print()
        
        # Show top tokens
        print(f"🏆 **Top 5 Tokens:**")
        for i, token in enumerate(tokens[:5]):
            symbol = token.get('symbol', 'unknown')
            score = token.get('score', 0)
            last_processed = token.get('last_processed_at', 'unknown')
            print(f"   {i+1}. {symbol}: {score:.4f} (processed: {last_processed})")
        print()
    
    # Analyze scoring settings
    print(f"⚙️ **Scoring Configuration Analysis:**")
    
    # Hybrid momentum weights
    w_tx = float(settings.get('w_tx', 0))
    w_vol = float(settings.get('w_vol', 0))
    w_fresh = float(settings.get('w_fresh', 0))
    w_oi = float(settings.get('w_oi', 0))
    
    print(f"   Hybrid Momentum Weights:")
    print(f"     w_tx (transactions): {w_tx} ({'🔥 HIGH' if w_tx > 0.5 else '✅ normal' if w_tx > 0.2 else '⚠️ low'})")
    print(f"     w_vol (volume): {w_vol} ({'❌ DISABLED' if w_vol == 0 else '✅ enabled'})")
    print(f"     w_fresh (freshness): {w_fresh} ({'✅ normal' if w_fresh > 0.2 else '⚠️ low'})")
    print(f"     w_oi (order imbalance): {w_oi} ({'❌ DISABLED' if w_oi == 0 else '✅ enabled'})")
    
    total_weight = w_tx + w_vol + w_fresh + w_oi
    print(f"     Total weight: {total_weight} ({'⚠️ NOT 1.0' if abs(total_weight - 1.0) > 0.01 else '✅ normalized'})")
    print()
    
    # Other critical settings
    min_score = float(settings.get('min_score', 0))
    min_pool_liquidity = float(settings.get('min_pool_liquidity_usd', 0))
    ewma_alpha = float(settings.get('ewma_alpha', 0))
    
    print(f"   Critical Thresholds:")
    print(f"     min_score: {min_score} ({'🔥 VERY HIGH' if min_score > 0.15 else '⚠️ high' if min_score > 0.1 else '✅ normal'})")
    print(f"     min_pool_liquidity_usd: ${min_pool_liquidity} ({'⚠️ VERY LOW' if min_pool_liquidity < 100 else '✅ normal'})")
    print(f"     ewma_alpha: {ewma_alpha} ({'🔥 VERY REACTIVE' if ewma_alpha > 0.8 else '✅ normal'})")
    print()
    
    # Identify potential issues
    print(f"🚨 **Potential Issues Identified:**")
    issues = []
    
    if w_vol == 0:
        issues.append("Volume component disabled (w_vol=0) - missing volume signals")
    
    if w_oi == 0:
        issues.append("Order imbalance disabled (w_oi=0) - missing market microstructure")
    
    if w_tx > 0.6:
        issues.append(f"Transaction weight too high ({w_tx}) - over-emphasizing tx activity")
    
    if min_pool_liquidity < 100:
        issues.append(f"Liquidity threshold too low (${min_pool_liquidity}) - including low-quality tokens")
    
    if min_score > 0.15:
        issues.append(f"Score threshold too high ({min_score}) - filtering out too many tokens")
    
    if ewma_alpha > 0.8:
        issues.append(f"EWMA too reactive ({ewma_alpha}) - scores may be unstable")
    
    if abs(total_weight - 1.0) > 0.01:
        issues.append(f"Weights don't sum to 1.0 ({total_weight}) - scoring may be skewed")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("   ✅ No obvious configuration issues detected")
    
    print()
    
    # Recommendations
    print(f"💡 **Recommendations:**")
    
    if w_vol == 0 and w_oi == 0:
        print("   1. Re-enable volume (w_vol=0.15-0.25) and order imbalance (w_oi=0.10-0.15)")
        print("   2. Reduce transaction weight (w_tx=0.40-0.50) to balance components")
    
    if min_pool_liquidity < 200:
        print("   3. Increase liquidity threshold to $200-500 for better token quality")
    
    if min_score > 0.15:
        print("   4. Lower min_score to 0.10-0.15 to see more tokens")
    
    if ewma_alpha > 0.8:
        print("   5. Reduce ewma_alpha to 0.3-0.5 for more stable scores")
    
    print()
    return True

def test_single_token_scoring():
    """Test scoring for a single token to see detailed breakdown."""
    print("🧪 **Single Token Scoring Test:**")
    print("This would require access to the scoring service internals...")
    print("Consider adding a debug endpoint: /debug/score/{mint_address}")
    print()

if __name__ == "__main__":
    print("🔍 Token Scoring Diagnostic Tool")
    print("================================")
    print()
    
    success = analyze_token_scores()
    
    if success:
        print("✅ Analysis completed. Review recommendations above.")
    else:
        print("❌ Analysis failed. Check API connectivity.")
    
    sys.exit(0 if success else 1)