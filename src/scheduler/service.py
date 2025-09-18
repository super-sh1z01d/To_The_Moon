from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from src.core.config import get_config
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.metrics.dex_aggregator import aggregate_wsol_metrics
from src.domain.scoring.scorer import compute_score
from src.domain.scoring.scoring_service import ScoringService
from src.domain.settings.service import SettingsService


log = logging.getLogger("scheduler")


async def _process_group(group: str) -> None:
    """Обновить метрики и скор для группы токенов.

    group in {"hot","cold"}
    hot: score >= min_score; cold: иначе (или нет снапшота)
    """
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        scoring_service = ScoringService(repo, settings)
        
        min_score = float(settings.get("min_score") or 0.1)
        min_score_change = float(settings.get("min_score_change") or 0.05)
        
        tokens = repo.list_by_status("active", limit=500)
        client = DexScreenerClient(timeout=5.0)
        
        processed = 0
        updated = 0
        
        active_model = scoring_service.get_active_model()
        log.info("processing_group", extra={"extra": {"group": group, "active_model": active_model, "tokens_count": len(tokens)}})
        
        for t in tokens:
            snap = repo.get_latest_snapshot(t.id)
            last_score = float(snap.score) if (snap and snap.score is not None) else None
            is_hot = last_score is not None and last_score >= min_score
            if group == "hot" and not is_hot:
                continue
            if group == "cold" and is_hot:
                continue

            processed += 1
            pairs = client.get_pairs(t.mint_address)
            if pairs is None:
                log.warning("pairs_fetch_failed", extra={"extra": {"group": group, "mint": t.mint_address}})
                continue
            
            try:
                # Calculate score using unified scoring service
                score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(t, pairs)
                
                # Check if we should skip update due to minimal score change
                from src.domain.validation.data_filters import should_skip_score_update
                if should_skip_score_update(score, last_score, min_score_change):
                    log.debug("score_update_skipped", extra={"extra": {"group": group, "mint": t.mint_address, "change": abs(score - (last_score or 0))}})
                    continue
                
                # Save score result
                snapshot_id = scoring_service.save_score_result(
                    token=t,
                    score=score,
                    smoothed_score=smoothed_score,
                    metrics=metrics,
                    raw_components=raw_components,
                    smoothed_components=smoothed_components
                )
                
                updated += 1
                
                # Log with model-specific information
                log_extra = {
                    "group": group,
                    "mint": t.mint_address,
                    "score": score,
                    "smoothed_score": smoothed_score,
                    "model": active_model,
                    "L_tot": metrics.get("L_tot"),
                    "n_5m": metrics.get("n_5m"),
                    "filtered_pools": metrics.get("pools_filtered_out", 0),
                    "data_quality_ok": not metrics.get("data_quality_warning", False),
                }
                
                # Add hybrid momentum specific metrics to log
                if active_model == "hybrid_momentum" and raw_components:
                    log_extra.update({
                        "tx_accel": raw_components.get("tx_accel"),
                        "vol_momentum": raw_components.get("vol_momentum"),
                        "token_freshness": raw_components.get("token_freshness"),
                        "orderflow_imbalance": raw_components.get("orderflow_imbalance"),
                    })
                
                log.info("token_updated", extra={"extra": log_extra})
                
            except Exception as e:
                log.error(
                    "token_scoring_error",
                    extra={
                        "extra": {
                            "group": group,
                            "mint": t.mint_address,
                            "error": str(e),
                            "model": active_model
                        }
                    }
                )
                continue

        log.info("group_summary", extra={"extra": {"group": group, "processed": processed, "updated": updated, "model": active_model}})


def init_scheduler(app: FastAPI) -> Optional[AsyncIOScheduler]:
    cfg = get_config()
    if not cfg.scheduler_enabled:
        log.info("scheduler_disabled")
        return None
    
    # В multi-worker setup запускаем планировщик только в одном процессе
    # Используем переменную окружения для контроля
    import os
    disable_scheduler = os.environ.get("DISABLE_SCHEDULER_IN_WORKER", "false").lower() == "true"
    if disable_scheduler:
        log.info("scheduler_disabled_by_env_var")
        return None

    with SessionLocal() as sess:
        settings = SettingsService(sess)
        try:
            hot_interval = int(settings.get("hot_interval_sec") or 10)
            cold_interval = int(settings.get("cold_interval_sec") or 45)
        except Exception:
            hot_interval, cold_interval = 10, 45

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_process_group, "interval", seconds=hot_interval, args=["hot"], id="hot_updater", max_instances=1)
    scheduler.add_job(
        _process_group, "interval", seconds=cold_interval, args=["cold"], id="cold_updater", max_instances=1
    )
    # Валидация monitoring → active каждую минуту
    from apscheduler.triggers.interval import IntervalTrigger
    from src.scheduler.tasks import archive_once, enforce_activation_once

    scheduler.add_job(enforce_activation_once, IntervalTrigger(minutes=3), id="activation_enforcer", max_instances=1)
    # Архивация раз в час
    scheduler.add_job(archive_once, IntervalTrigger(hours=1), id="archiver_hourly", max_instances=1)
    scheduler.start()
    app.state.scheduler = scheduler
    log.info(
        "scheduler_started",
        extra={"extra": {"hot_interval": hot_interval, "cold_interval": cold_interval}},
    )
    return scheduler
