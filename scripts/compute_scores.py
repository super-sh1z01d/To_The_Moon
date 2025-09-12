#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from typing import Optional

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.domain.scoring.scorer import compute_score
from src.domain.validation.data_filters import should_skip_score_update


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute scores for active tokens using latest metrics")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--insert-new", action="store_true", help="create new snapshot instead of updating latest")
    args = parser.parse_args()

    configure_logging(level="INFO")
    log = logging.getLogger("scoring")

    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        smoothing_alpha = float(settings.get("score_smoothing_alpha") or 0.3)
        min_score_change = float(settings.get("min_score_change") or 0.05)
        
        weights = {
            "weight_s": float(settings.get("weight_s") or 0.35),
            "weight_l": float(settings.get("weight_l") or 0.25),
            "weight_m": float(settings.get("weight_m") or 0.20),
            "weight_t": float(settings.get("weight_t") or 0.20),
        }
        tokens = repo.list_by_status("active", limit=args.limit)
        processed = 0
        scored = 0
        for t in tokens:
            processed += 1
            snap = repo.get_latest_snapshot(t.id)
            if not snap or not snap.metrics:
                log.info("no_metrics", extra={"extra": {"token_id": t.id, "mint": t.mint_address}})
                continue
            
            # Get previous smoothed score
            previous_smoothed_score = repo.get_previous_smoothed_score(t.id)
            
            score, comps = compute_score(snap.metrics, weights)
            
            # Check if we should skip minor score changes (unless forced with --insert_new)
            if not args.insert_new and should_skip_score_update(score, snap.score, min_score_change):
                log.debug("score_update_skipped", extra={"extra": {"mint": t.mint_address, "change": abs(score - (snap.score or 0))}})
                continue
            
            # Compute smoothed score
            from src.domain.scoring.scorer import compute_smoothed_score
            smoothed_score = compute_smoothed_score(score, previous_smoothed_score, smoothing_alpha)
            
            if args.insert_new:
                repo.insert_score_snapshot(
                    token_id=t.id, 
                    metrics=snap.metrics, 
                    score=score, 
                    smoothed_score=smoothed_score
                )
            else:
                repo.update_snapshot_score(
                    snapshot_id=snap.id, 
                    score=score, 
                    smoothed_score=smoothed_score
                )
            scored += 1
            log.info(
                "score_computed",
                extra={
                    "extra": {
                        "mint": t.mint_address,
                        "score": score,
                        "smoothed_score": smoothed_score,
                        "alpha": smoothing_alpha,
                        "l": comps["l"],
                        "s": comps["s"],
                        "m": comps["m"],
                        "t": comps["t"],
                        "Ws": weights["weight_s"],
                        "Wl": weights["weight_l"],
                        "Wm": weights["weight_m"],
                        "Wt": weights["weight_t"],
                    }
                },
            )

    log.info("summary", extra={"extra": {"processed": processed, "scored": scored}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

