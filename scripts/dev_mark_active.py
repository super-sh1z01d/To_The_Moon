#!/usr/bin/env python3
from __future__ import annotations

from sqlalchemy import select
from src.adapters.db.base import SessionLocal
from src.adapters.db.models import Token
from src.adapters.repositories.tokens_repo import TokensRepository


def main() -> int:
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        t = sess.query(Token).first()
        if not t:
            print("no tokens found; run scripts/smoke_db.py first")
            return 1
        repo.set_active(t)
        print(f"token {t.mint_address} set to active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

