#!/usr/bin/env python3
"""
Script to toggle between acceleration and arbitrage activity scoring modes.

Usage:
    python scripts/toggle_arbitrage_mode.py --mode acceleration
    python scripts/toggle_arbitrage_mode.py --mode arbitrage_activity
    python scripts/toggle_arbitrage_mode.py --status  # Show current mode
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from adapters.db.base import SessionLocal
from domain.settings.service import SettingsService


def show_current_mode():
    """Show current scoring mode and settings."""
    with SessionLocal() as sess:
        settings = SettingsService(sess)
        
        current_mode = settings.get("tx_calculation_mode") or "acceleration"
        min_tx = settings.get("arbitrage_min_tx_5m") or "50"
        optimal_tx = settings.get("arbitrage_optimal_tx_5m") or "200"
        accel_weight = settings.get("arbitrage_acceleration_weight") or "0.3"
        
        print("=== CURRENT SCORING MODE ===")
        print(f"Mode: {current_mode}")
        print()
        
        if current_mode == "arbitrage_activity":
            print("🎯 ARBITRAGE MODE ACTIVE")
            print(f"  Minimum threshold: {min_tx} TX per 5 minutes")
            print(f"  Optimal threshold: {optimal_tx} TX per 5 minutes")
            print(f"  Acceleration weight: {float(accel_weight)*100:.0f}%")
            print(f"  Absolute activity weight: {(1-float(accel_weight))*100:.0f}%")
        else:
            print("📈 ACCELERATION MODE ACTIVE (default)")
            print("  Using traditional log-based acceleration formula")
        
        print()
        print("To switch modes:")
        print("  python scripts/toggle_arbitrage_mode.py --mode arbitrage_activity")
        print("  python scripts/toggle_arbitrage_mode.py --mode acceleration")


def set_mode(mode: str):
    """Set the scoring mode."""
    if mode not in ["acceleration", "arbitrage_activity"]:
        print(f"❌ Invalid mode: {mode}")
        print("Valid modes: acceleration, arbitrage_activity")
        return False
    
    with SessionLocal() as sess:
        settings = SettingsService(sess)
        
        old_mode = settings.get("tx_calculation_mode") or "acceleration"
        
        if old_mode == mode:
            print(f"✅ Mode already set to: {mode}")
            return True
        
        # Set the new mode
        settings.set("tx_calculation_mode", mode)
        
        print(f"✅ Scoring mode changed: {old_mode} → {mode}")
        print()
        
        if mode == "arbitrage_activity":
            print("🎯 ARBITRAGE MODE ACTIVATED")
            print("  Optimized for high-frequency arbitrage bots")
            print("  Focuses on absolute transaction volume + acceleration")
            print("  Tokens with 200+ TX per 5min get maximum scores")
        else:
            print("📈 ACCELERATION MODE ACTIVATED")
            print("  Traditional logarithmic acceleration formula")
            print("  Focuses on transaction rate changes over time")
        
        print()
        print("⚠️  Changes will take effect on next scoring cycle")
        print("   (within 15-45 seconds depending on token group)")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Toggle transaction scoring mode")
    parser.add_argument(
        "--mode", 
        choices=["acceleration", "arbitrage_activity"],
        help="Set scoring mode"
    )
    parser.add_argument(
        "--status", 
        action="store_true",
        help="Show current mode and settings"
    )
    
    args = parser.parse_args()
    
    if args.status or not args.mode:
        show_current_mode()
    else:
        set_mode(args.mode)


if __name__ == "__main__":
    main()