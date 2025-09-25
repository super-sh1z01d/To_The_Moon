from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
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

# Use standard logger for now
# structured_logger = StructuredLogger("scheduler")


async def _process_group(group: str) -> None:
    """Обновить метрики и скор для группы токенов.

    group in {"hot","cold"}
    hot: score >= min_score; cold: иначе (или нет снапшота)
    """
    start_time = datetime.now(timezone.utc)
    
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        scoring_service = ScoringService(repo, settings)
        
        min_score = float(settings.get("min_score") or 0.1)
        min_score_change = float(settings.get("min_score_change") or 0.05)
        
        # Get load-based processing adjustments
        from src.monitoring.metrics import get_load_processor
        load_processor = get_load_processor()
        
        # Adjust batch size based on system load - further reduced to prevent overload
        base_limit = 30 if group == "hot" else 20  # Much smaller batches to prevent system overload
        adjusted_limit = load_processor.get_adjusted_batch_size(base_limit)
        
        # Get priority-based token processing
        from src.scheduler.priority_processor import get_priority_processor
        priority_processor = get_priority_processor()
        
        # Get tokens with priority ordering
        tokens = priority_processor.get_prioritized_tokens(
            repo, group, adjusted_limit, load_processor.get_current_load()
        )
        # Use resilient client with circuit breaker in production
        from src.core.config import get_config
        config = get_config()
        
        if config.app_env == "prod":
            from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
            # Use shorter cache for hot tokens (more frequent updates)
            cache_ttl = 15 if group == "hot" else 30
            client = ResilientDexScreenerClient(timeout=5.0, cache_ttl=cache_ttl)
            log.info(f"Using resilient DexScreener client with circuit breaker and {cache_ttl}s cache for {group} tokens")
        else:
            client = DexScreenerClient(timeout=5.0)
            log.info("Using standard DexScreener client")
        
        processed = 0
        updated = 0
        
        active_model = scoring_service.get_active_model()
        log.info("processing_group", extra={"extra": {"group": group, "active_model": active_model, "tokens_count": len(tokens)}})
        
        # Batch load snapshots to avoid N+1 queries - do this once for both distribution and processing
        token_ids = [t.id for t in tokens]
        snapshots = repo.get_latest_snapshots_batch(token_ids)
        
        # Calculate distribution using pre-loaded snapshots
        hot_count = 0
        cold_count = 0
        for t in tokens:
            snap = snapshots.get(t.id)
            last_score = float(snap.smoothed_score) if (snap and snap.smoothed_score is not None) else None
            if last_score is None:
                last_score = float(snap.score) if (snap and snap.score is not None) else None
            
            is_hot = last_score is not None and last_score >= min_score
            if is_hot:
                hot_count += 1
            else:
                cold_count += 1
        
        log.info("group_distribution", extra={"extra": {"group": group, "hot_tokens": hot_count, "cold_tokens": cold_count, "min_score": min_score}})
        
        for t in tokens:
            snap = snapshots.get(t.id)
            # Используем сглаженный скор для группировки (как в API)
            last_score = float(snap.smoothed_score) if (snap and snap.smoothed_score is not None) else None
            # Фолбэк на сырой скор если сглаженного нет
            if last_score is None:
                last_score = float(snap.score) if (snap and snap.score is not None) else None
            
            is_hot = last_score is not None and last_score >= min_score
            
            # Active tokens should always be processed by hot group regardless of score
            if t.status == "active":
                if group == "cold":
                    continue  # Active tokens don't go to cold group
            else:
                # For monitoring tokens, use score-based filtering
                if group == "hot" and not is_hot:
                    continue
                if group == "cold" and is_hot:
                    continue

            processed += 1
            

            
            # Execute HTTP call in thread pool to avoid blocking event loop
            import asyncio
            pairs = await asyncio.to_thread(client.get_pairs, t.mint_address)
            if pairs is None:
                log.warning("pairs_fetch_failed", extra={"extra": {"group": group, "mint": t.mint_address}})
                continue
            
            try:
                # Calculate score using unified scoring service
                score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(t, pairs)
                
                # Check if we should skip update due to minimal score change
                from src.domain.validation.data_filters import should_skip_score_update
                should_skip = should_skip_score_update(score, last_score, min_score_change)
                
                # For active tokens, always update timestamp even if score didn't change significantly
                # This shows the token is "alive" and being processed
                if should_skip and t.status == "active":
                    # Update only timestamp for active tokens to show they're being processed
                    repo.update_token_timestamp(t.id)
                    log.debug("active_token_timestamp_updated", extra={"extra": {"symbol": t.symbol, "mint": t.mint_address[:8], "score_change": abs(score - (last_score or 0))}})
                    continue
                elif should_skip:
                    # For monitoring tokens, skip as usual
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
                
                # Log with model-specific information (if detailed logging is enabled)
                if load_processor.is_feature_enabled("detailed_logging"):
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
                else:
                    # Minimal logging under high load
                    log.info("token_updated", extra={"extra": {
                        "group": group,
                        "mint": t.mint_address,
                        "score": score,
                        "model": active_model
                    }})
                
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
        
        # Записываем выполнение для мониторинга
        from src.scheduler.monitoring import health_monitor
        health_monitor.record_group_execution(group, processed, updated)
        
        # Record performance metrics
        from src.monitoring.metrics import get_performance_tracker, get_structured_logger, get_performance_optimizer
        performance_tracker = get_performance_tracker()
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        performance_tracker.record_scheduler_execution(group, processing_time, processed, updated)
        
        # Structured logging
        structured_logger = get_structured_logger("scheduler")
        structured_logger.log_scheduler_execution(
            group=group,
            tokens_processed=processed,
            tokens_updated=updated,
            processing_time=processing_time,
            error_count=0,
            batch_size=adjusted_limit
        )
        
        # Performance optimization
        performance_optimizer = get_performance_optimizer()
        optimization_result = performance_optimizer.optimize_service("scheduler")
        
        if optimization_result.get("optimized") and optimization_result.get("changes"):
            structured_logger.info(
                f"Scheduler performance optimized",
                group=group,
                optimization_changes=optimization_result["changes"]
            )
        
        # Performance degradation detection
        from src.monitoring.metrics import get_performance_degradation_detector
        degradation_detector = get_performance_degradation_detector()
        
        # Record performance metrics for degradation analysis
        performance_metrics = {
            "response_time": processing_time,
            "throughput": processed / (processing_time / 60) if processing_time > 0 else 0,  # tokens per minute
            "error_rate": 0,  # Could be calculated from failed token updates
            "cpu_usage": system_metrics.get("cpu_percent", 0) if 'system_metrics' in locals() else 0,
            "memory_usage": system_metrics.get("memory_percent", 0) if 'system_metrics' in locals() else 0
        }
        
        degradation_detector.record_performance_metric("scheduler", performance_metrics)
        
        # Check for predictive alerts
        predictive_alerts = degradation_detector.get_predictive_alerts("scheduler", forecast_minutes=15)
        for alert in predictive_alerts:
            structured_logger.warning(
                f"Predictive performance alert: {alert['message']}",
                group=group,
                alert_type=alert["type"],
                confidence=alert["confidence"],
                projected_value=alert["projected_value"]
            )
        
        # Check if we need to perform health check and recovery
        try:
            from src.app.main import app
            if hasattr(app.state, 'self_healing_wrapper'):
                app.state.self_healing_wrapper.check_health_and_recover()
        except Exception as e:
            # Self-healing is optional, don't fail if not available
            log.debug(f"Self-healing check skipped: {e}")
        
        # Process load-based adjustments
        try:
            from src.monitoring.metrics import get_load_processor
            load_processor = get_load_processor()
            load_adjustments = load_processor.process_load_adjustment()
            
            # Log significant load changes
            if not load_adjustments.get("no_change", False):
                log.info(
                    "load_adjustment_processed",
                    extra={
                        "extra": {
                            "group": group,
                            "load_level": load_adjustments.get("new_level"),
                            "processing_factor": load_adjustments.get("new_factor"),
                            "cpu_percent": load_adjustments.get("load_metrics", {}).get("cpu_percent"),
                            "memory_percent": load_adjustments.get("load_metrics", {}).get("memory_percent")
                        }
                    }
                )
        except Exception as e:
            log.error(f"Load adjustment processing failed: {e}")


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
            base_hot_interval = int(settings.get("hot_interval_sec") or 10)
            base_cold_interval = int(settings.get("cold_interval_sec") or 45)
        except Exception:
            base_hot_interval, base_cold_interval = 10, 45
    
    # Apply load-based adjustments to intervals
    from src.monitoring.metrics import get_load_processor
    load_processor = get_load_processor()
    
    hot_interval = load_processor.get_adjusted_interval(base_hot_interval)
    cold_interval = load_processor.get_adjusted_interval(base_cold_interval)

    scheduler = AsyncIOScheduler()
    
    # Добавляем задачи с проверкой ошибок
    try:
        scheduler.add_job(_process_group, "interval", seconds=hot_interval, args=["hot"], id="hot_updater", max_instances=1)
        log.info("hot_updater_added", extra={"extra": {"interval": hot_interval}})
    except Exception as e:
        log.error(f"Failed to add hot_updater job: {e}")
        
    # Заменяем проблемную задачу cold_updater на множественные задачи
    # Это обходит проблему с APScheduler, когда одна задача не запускается
    try:
        # Создаем несколько задач для холодных токенов с разными ID
        for i in range(3):  # 3 задачи с интервалом 30 секунд = эффективно каждые 10 секунд
            delay = i * (cold_interval // 3)  # Распределяем по времени
            scheduler.add_job(
                _process_group, 
                "interval", 
                seconds=cold_interval, 
                args=["cold"], 
                id=f"cold_updater_{i}",
                max_instances=1,
                next_run_time=datetime.now(timezone.utc) + timedelta(seconds=delay + 10)  # Первый запуск через 10+ секунд
            )
        log.info("cold_updaters_added", extra={"extra": {"interval": cold_interval, "count": 3}})
    except Exception as e:
        log.error(f"Failed to add cold_updater jobs: {e}")
    # Валидация monitoring → active каждую минуту
    from apscheduler.triggers.interval import IntervalTrigger
    from src.scheduler.tasks import archive_once, enforce_activation_once

    scheduler.add_job(enforce_activation_once, IntervalTrigger(minutes=3), id="activation_enforcer", max_instances=1)
    # Архивация раз в час
    scheduler.add_job(archive_once, IntervalTrigger(hours=1), id="archiver_hourly", max_instances=1)
    
    # NotArb pools file updates - simple 15 second interval
    from src.scheduler.notarb_tasks import update_notarb_pools_file
    
    scheduler.add_job(
        update_notarb_pools_file, 
        IntervalTrigger(seconds=5), 
        id="notarb_pools_updater", 
        max_instances=1,  # Prevent concurrent execution
        coalesce=True     # Skip if previous execution is still running
    )
    
    scheduler.start()
    
    # Запускаем независимый процессор холодных токенов
    # Это обходит проблемы с APScheduler
    import asyncio
    from src.scheduler.cold_processor import start_cold_processor
    
    async def init_cold_processor():
        await start_cold_processor(cold_interval)
    
    # Запускаем в фоне
    asyncio.create_task(init_cold_processor())
    log.info("independent_cold_processor_started", extra={"extra": {"interval": cold_interval}})
    
    # Create self-healing wrapper
    from src.scheduler.monitoring import SelfHealingSchedulerWrapper
    self_healing_wrapper = SelfHealingSchedulerWrapper(scheduler, app)
    
    app.state.scheduler = scheduler
    app.state.self_healing_wrapper = self_healing_wrapper
    
    log.info(
        "scheduler_started",
        extra={"extra": {
            "hot_interval": hot_interval, 
            "cold_interval": cold_interval,
            "self_healing_enabled": True
        }},
    )
    return scheduler
