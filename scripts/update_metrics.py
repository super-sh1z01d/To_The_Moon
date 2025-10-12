#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.metrics.dex_aggregator import aggregate_wsol_metrics
from src.domain.pools.pool_type_service import PoolTypeService


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
        pool_service = PoolTypeService(sess)
        try:
            tokens = repo.list_by_status("active", limit=args.limit)
            for t in tokens:
                processed += 1
                pairs = client.get_pairs(t.mint_address)
                if pairs is None:
                    log.warning("pairs_fetch_failed", extra={"extra": {"mint": t.mint_address}})
                    continue

                enriched_pairs = pool_service.enrich_pairs(pairs)
                if not enriched_pairs:
                    log.warning("pools_unclassified", extra={"extra": {"mint": t.mint_address}})
                    continue

                metrics = aggregate_wsol_metrics(t.mint_address, enriched_pairs)
                pool_service.insert_primary_pool_type(metrics)

                repo.insert_score_snapshot(token_id=t.id, metrics=metrics, score=None)
                created += 1
                log.info(
                    "metrics_collected",
                    extra={
                        "extra": {
                            "mint": t.mint_address,
                            "L_tot": metrics["L_tot"],
                            "delta_p_5m": metrics["delta_p_5m"],
                            "delta_p_15m": metrics["delta_p_15m"],
                            "n_5m": metrics["n_5m"],
                            "ws_pairs": metrics["ws_pairs"],
                        }
                    },
                )
        finally:
            pool_service.close()

    log.info("summary", extra={"extra": {"processed": processed, "snapshots": created}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
