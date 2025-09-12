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
        min_score = float(settings.get("min_score") or 0.1)
        smoothing_alpha = float(settings.get("score_smoothing_alpha") or 0.3)
        
        # Настройки фильтрации данных
        min_pool_liquidity = float(settings.get("min_pool_liquidity_usd") or 500)
        max_price_change = float(settings.get("max_price_change_5m") or 0.5)
        min_score_change = float(settings.get("min_score_change") or 0.05)
        
        weights = {
            "weight_s": float(settings.get("weight_s") or 0.35),
            "weight_l": float(settings.get("weight_l") or 0.25),
            "weight_m": float(settings.get("weight_m") or 0.20),
            "weight_t": float(settings.get("weight_t") or 0.20),
        }
        tokens = repo.list_by_status("active", limit=500)

        client = DexScreenerClient(timeout=5.0)
        processed = 0
        updated = 0
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
            
            # Получаем предыдущий сглаженный скор для данного токена
            previous_smoothed_score = repo.get_previous_smoothed_score(t.id)
            
            # Агрегируем метрики с фильтрацией данных
            metrics = aggregate_wsol_metrics(
                t.mint_address, 
                pairs, 
                min_liquidity_usd=min_pool_liquidity,
                max_price_change=max_price_change
            )
            
            # Проверяем качество данных
            if metrics.get("data_quality_warning"):
                log.warning("data_quality_issue", extra={"extra": {"group": group, "mint": t.mint_address}})
                # Можно пропустить обновление при серьезных проблемах с данными
                # continue
            
            score, comps = compute_score(metrics, weights)
            
            # Проверяем, стоит ли пропустить обновление из-за незначительных изменений
            from src.domain.validation.data_filters import should_skip_score_update
            if should_skip_score_update(score, last_score, min_score_change):
                log.debug("score_update_skipped", extra={"extra": {"group": group, "mint": t.mint_address, "change": abs(score - (last_score or 0))}})
                continue
            
            # Вычисляем сглаженный скор
            from src.domain.scoring.scorer import compute_smoothed_score
            smoothed_score = compute_smoothed_score(score, previous_smoothed_score, smoothing_alpha)
            
            snapshot_id = repo.insert_score_snapshot(
                token_id=t.id, 
                metrics=metrics, 
                score=score, 
                smoothed_score=smoothed_score
            )
            
            updated += 1
            log.info(
                "token_updated",
                extra={
                    "extra": {
                        "group": group,
                        "mint": t.mint_address,
                        "score": score,
                        "smoothed_score": smoothed_score,
                        "alpha": smoothing_alpha,
                        "L_tot": metrics["L_tot"],
                        "n_5m": metrics["n_5m"],
                        "filtered_pools": metrics.get("pools_filtered_out", 0),
                        "data_quality_ok": not metrics.get("data_quality_warning", False),
                    }
                },
            )

        log.info("group_summary", extra={"extra": {"group": group, "processed": processed, "updated": updated}})


def init_scheduler(app: FastAPI) -> Optional[AsyncIOScheduler]:
    cfg = get_config()
    if not cfg.scheduler_enabled:
        log.info("scheduler_disabled")
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

    scheduler.add_job(enforce_activation_once, IntervalTrigger(minutes=1), id="activation_enforcer", max_instances=1)
    # Архивация раз в час
    scheduler.add_job(archive_once, IntervalTrigger(hours=1), id="archiver_hourly", max_instances=1)
    scheduler.start()
    app.state.scheduler = scheduler
    log.info(
        "scheduler_started",
        extra={"extra": {"hot_interval": hot_interval, "cold_interval": cold_interval}},
    )
    return scheduler
