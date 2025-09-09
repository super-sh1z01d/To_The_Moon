#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timezone
from sqlalchemy import select
from src.adapters.db.base import SessionLocal, engine
from src.adapters.db.models import Token, TokenScore, AppSetting


def main() -> None:
    url = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    print(f"[smoke_db] Using DB: {url}")
    with SessionLocal() as sess:
        # Insert app settings sample
        sess.merge(AppSetting(key="min_score", value="0.1"))
        sess.commit()

        # Insert a token in monitoring
        t = Token(mint_address="TestMint1111111111111111111111111111111", name="Test", symbol="TST", status="monitoring")
        sess.add(t)
        sess.commit()
        sess.refresh(t)
        print(f"[smoke_db] Inserted token id={t.id}")

        # Insert a score snapshot (no real metrics yet)
        s = TokenScore(token_id=t.id, score=None, metrics={"note": "placeholder"})
        sess.add(s)
        sess.commit()

        # Query back
        cnt_tokens = sess.scalar(select(Token).count()) if hasattr(select(Token), 'count') else sess.query(Token).count()
        cnt_scores = sess.query(TokenScore).count()
        cnt_settings = sess.query(AppSetting).count()
        print(f"[smoke_db] Counts: tokens={cnt_tokens}, token_scores={cnt_scores}, app_settings={cnt_settings}")

        # Cleanup (optional): keep data for inspection


if __name__ == "__main__":
    main()

