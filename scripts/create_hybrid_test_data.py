#!/usr/bin/env python3
"""
Create test data with Hybrid Momentum components for testing the enhanced dashboard.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from src.adapters.db.base import SessionLocal
from src.adapters.db.models import Token, TokenScore, AppSetting


def main() -> None:
    url = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    print(f"[create_hybrid_test_data] Using DB: {url}")
    
    with SessionLocal() as sess:
        # Create test tokens with different characteristics
        test_tokens = [
            {
                "mint": "HybridTestMint1111111111111111111111111",
                "name": "High Momentum Token",
                "symbol": "HMT",
                "status": "active",
                "score": 0.8500,
                "smoothed_score": 0.8200,
                "raw_components": {
                    "tx_accel": 0.9,
                    "vol_momentum": 0.8,
                    "token_freshness": 0.95,
                    "orderflow_imbalance": 0.75
                },
                "smoothed_components": {
                    "tx_accel": 0.85,
                    "vol_momentum": 0.78,
                    "token_freshness": 0.92,
                    "orderflow_imbalance": 0.72
                },
                "created_hours_ago": 2  # Fresh token
            },
            {
                "mint": "HybridTestMint2222222222222222222222222",
                "name": "Medium Momentum Token", 
                "symbol": "MMT",
                "status": "active",
                "score": 0.4500,
                "smoothed_score": 0.4200,
                "raw_components": {
                    "tx_accel": 0.5,
                    "vol_momentum": 0.4,
                    "token_freshness": 0.0,  # Old token
                    "orderflow_imbalance": 0.6
                },
                "smoothed_components": {
                    "tx_accel": 0.48,
                    "vol_momentum": 0.38,
                    "token_freshness": 0.0,
                    "orderflow_imbalance": 0.58
                },
                "created_hours_ago": 24  # Old token
            },
            {
                "mint": "HybridTestMint3333333333333333333333333",
                "name": "Low Momentum Token",
                "symbol": "LMT", 
                "status": "monitoring",
                "score": 0.2500,
                "smoothed_score": 0.2200,
                "raw_components": {
                    "tx_accel": 0.2,
                    "vol_momentum": 0.3,
                    "token_freshness": 0.5,  # Somewhat fresh
                    "orderflow_imbalance": 0.1
                },
                "smoothed_components": {
                    "tx_accel": 0.18,
                    "vol_momentum": 0.28,
                    "token_freshness": 0.48,
                    "orderflow_imbalance": 0.08
                },
                "created_hours_ago": 4  # Fresh token
            }
        ]
        
        for token_data in test_tokens:
            # Check if token already exists
            existing = sess.scalar(select(Token).where(Token.mint_address == token_data["mint"]))
            if existing:
                print(f"[create_hybrid_test_data] Token {token_data['mint']} already exists, skipping")
                continue
                
            # Create token with specific creation time
            created_at = datetime.now(timezone.utc) - timedelta(hours=token_data["created_hours_ago"])
            token = Token(
                mint_address=token_data["mint"],
                name=token_data["name"],
                symbol=token_data["symbol"],
                status=token_data["status"],
                created_at=created_at
            )
            sess.add(token)
            sess.commit()
            sess.refresh(token)
            print(f"[create_hybrid_test_data] Created token {token.name} (id={token.id})")
            
            # Create score with hybrid momentum components
            score = TokenScore(
                token_id=token.id,
                score=token_data["score"],
                smoothed_score=token_data["smoothed_score"],
                raw_components=token_data["raw_components"],
                smoothed_components=token_data["smoothed_components"],
                scoring_model="hybrid_momentum",
                metrics={
                    "L_tot": 50000.0 + (token_data["score"] * 100000),  # Liquidity based on score
                    "delta_p_5m": (token_data["score"] - 0.5) * 0.1,  # Price change based on score
                    "delta_p_15m": (token_data["score"] - 0.5) * 0.2,
                    "n_5m": int(token_data["score"] * 100),  # Transactions based on score
                    "primary_dex": "raydium",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            sess.add(score)
            sess.commit()
            print(f"[create_hybrid_test_data] Created score for {token.name}")
        
        # Update settings to ensure hybrid momentum is active
        sess.merge(AppSetting(key="scoring_model_active", value="hybrid_momentum"))
        sess.merge(AppSetting(key="min_score", value="0.15"))
        sess.commit()
        
        # Print summary
        cnt_tokens = sess.query(Token).count()
        cnt_scores = sess.query(TokenScore).count()
        print(f"[create_hybrid_test_data] Total: tokens={cnt_tokens}, scores={cnt_scores}")
        print("[create_hybrid_test_data] Test data created successfully!")


if __name__ == "__main__":
    main()