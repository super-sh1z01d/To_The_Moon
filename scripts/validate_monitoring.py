#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import time
import logging

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.validation.dex_rules import check_activation_conditions


def validate_one(mint: str) -> None:
    log = logging.getLogger("validate")
    client = DexScreenerClient(timeout=5.0)
    pairs = client.get_pairs(mint)
    if pairs is None:
        log.warning("pairs_fetch_failed", extra={"extra": {"mint": mint}})
        return
    ok = check_activation_conditions(mint, pairs)
    log.info("validation_result", extra={"extra": {"mint": mint, "activate": ok, "pairs": len(pairs)}})


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate monitoring tokens via DexScreener")
    parser.add_argument("--mint", help="Specific mint to validate", default=None)
    parser.add_argument("--limit", type=int, default=25, help="Max tokens to validate per run")
    args = parser.parse_args()

    configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    log = logging.getLogger("validate")

    if args.mint:
        validate_one(args.mint)
        return 0

    checked = 0
    activated = 0
    client = DexScreenerClient(timeout=5.0)

    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        tokens = repo.list_by_status("monitoring", limit=args.limit)
        for t in tokens:
            checked += 1
            mint = t.mint_address
            pairs = client.get_pairs(mint)
            if pairs is None:
                # Ошибка сети/лимиты — подождём немного и продолжим
                time.sleep(1.0)
                continue
            ok = check_activation_conditions(mint, pairs)
            if ok:
                repo.set_active(t)
                activated += 1
                log.info("activated", extra={"extra": {"mint": mint}})
            else:
                log.info("kept_monitoring", extra={"extra": {"mint": mint}})

    log.info("summary", extra={"extra": {"checked": checked, "activated": activated}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

