#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.metrics.enhanced_dex_aggregator import aggregate_enhanced_metrics
from src.domain.pools.classifier_dex_only import classify_pairs_dex_only, determine_primary_pool_type


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect metrics for active tokens")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    configure_logging(level="INFO")
    log = logging.getLogger("metrics")

    client = DexScreenerClient(timeout=5.0)
    processed = 0
    created = 0

    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        tokens = repo.list_by_status("active", limit=args.limit)
        for t in tokens:
            processed += 1
            pairs = client.get_pairs(t.mint_address)
            if pairs is None:
                log.warning("pairs_fetch_failed", extra={"extra": {"mint": t.mint_address}})
                continue

            enriched_pairs = classify_pairs_dex_only(pairs)
            if not enriched_pairs:
                log.warning("pools_unclassified", extra={"extra": {"mint": t.mint_address}})
                continue

            metrics = aggregate_enhanced_metrics(
                t.mint_address,
                enriched_pairs,
                t.created_at,
                min_liquidity_usd=500.0,
            )
            metrics["pool_classification_source"] = "dexscreener"
            primary_pool_type = determine_primary_pool_type(metrics.get("pools") or [])
            if primary_pool_type:
                metrics["primary_pool_type"] = primary_pool_type

            repo.insert_score_snapshot(token_id=t.id, metrics=metrics, score=None, smoothed_score=None)
            created += 1
            log.info(
                "metrics_collected",
                extra={
                    "extra": {
                        "mint": t.mint_address,
                        "L_tot": metrics.get("L_tot"),
                        "delta_p_5m": metrics.get("delta_p_5m"),
                        "delta_p_15m": metrics.get("delta_p_15m"),
                        "n_5m": metrics.get("n_5m"),
                    }
                },
            )

    log.info("summary", extra={"extra": {"processed": processed, "snapshots": created}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
