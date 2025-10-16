from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.monitoring.spam_detector import SpamDetector


log = logging.getLogger("archiver")


def archive_once() -> None:
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        min_score = float(settings.get("min_score") or 0.1)
        archive_below_hours = int(settings.get("archive_below_hours") or 12)
        monitoring_timeout_hours = int(settings.get("monitoring_timeout_hours") or 12)

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=archive_below_hours)
        active = repo.list_by_status("active", limit=1000)
        archived = 0
        for t in active:
            if not repo.has_score_ge_since(t.id, min_score=min_score, since_dt=cutoff):
                repo.archive_token(t, reason="low_score_timeout")
                archived += 1
                
                # Record status transition for monitoring
                try:
                    from src.monitoring.token_monitor import get_token_monitor
                    token_monitor = get_token_monitor()
                    token_monitor.record_status_transition(
                        mint_address=t.mint_address,
                        from_status="active",
                        to_status="archived",
                        reason="low_score_timeout"
                    )
                except Exception as e:
                    log.warning(f"Failed to record token transition: {e}")
        log.info("archiver_active", extra={"extra": {"archived": archived, "cutoff": cutoff.isoformat()}})

        mons = repo.list_monitoring_older_than_hours(monitoring_timeout_hours, limit=1000)
        m_arch = 0
        for t in mons:
            repo.archive_token(t, reason="monitoring_timeout")
            m_arch += 1
            
            # Record status transition for monitoring
            try:
                from src.monitoring.token_monitor import get_token_monitor
                token_monitor = get_token_monitor()
                token_monitor.record_status_transition(
                    mint_address=t.mint_address,
                    from_status="monitoring",
                    to_status="archived",
                    reason="monitoring_timeout"
                )
            except Exception as e:
                log.warning(f"Failed to record token transition: {e}")
        log.info("archiver_monitoring", extra={"extra": {"archived": m_arch, "timeout_h": monitoring_timeout_hours}})


def validate_monitoring_once(limit: int = 100) -> None:
    # Сохранён для обратной совместимости; перенаправляем на новый механизм
    enforce_activation_once(limit_monitoring=limit, limit_active=0)


def _external_liq_ge(mint: str, pairs: list[dict], threshold: float) -> bool:
    WS = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
    USD = {"USDC", "usdc"}
    EXCL = {"pumpfun", "pumpfun-amm", "pumpswap", "launchlab"}
    for p in pairs:
        try:
            base = p.get("baseToken") or {}
            quote = p.get("quoteToken") or {}
            if str(base.get("address")) != mint:
                continue
            dex = str(p.get("dexId") or "")
            if dex in EXCL:
                continue
            if str(quote.get("symbol", "")).upper() not in WS | USD:
                continue
            lq = (p.get("liquidity") or {}).get("usd")
            if lq is None:
                continue
            if float(lq) >= threshold:
                return True
        except Exception:
            continue
    return False


async def enforce_activation_async(limit_monitoring: int = 50, limit_active: int = 50) -> None:
    logv = logging.getLogger("activation")
    from src.adapters.services.dexscreener_batch_client import get_batch_client
    from src.adapters.services.dexscreener_client import DexScreenerClient

    batch_client = await get_batch_client()
    fallback_client = DexScreenerClient(timeout=3.0)

    async def ensure_pairs(mint: str, pairs: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
        """Ensure we have full pool list by falling back to token-pairs endpoint if needed."""
        from src.domain.validation.dex_rules import check_activation_conditions, has_external_pools
        
        # Always check if we have external pools in the batch data
        if pairs and has_external_pools(mint, pairs):
            # We have external pools, check activation conditions
            if check_activation_conditions(mint, pairs, threshold):
                return pairs
        
        # Either no external pools found or activation conditions not met
        # Fetch full dataset from token-pairs endpoint (includes all external pools)
        logv.info(
            "fetching_fallback_pairs_for_activation",
            extra={"mint": mint, "batch_pairs_count": len(pairs), "threshold": threshold}
        )
        
        fallback_pairs = await asyncio.to_thread(fallback_client.get_pairs, mint)
        if fallback_pairs:
            logv.info(
                "fallback_pairs_fetched_for_activation", 
                extra={"mint": mint, "fallback_pairs_count": len(fallback_pairs)}
            )
            return fallback_pairs
        
        logv.warning(
            "fallback_pairs_failed_for_activation",
            extra={"mint": mint, "using_batch_pairs": len(pairs)}
        )
        return pairs

    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        try:
            threshold = float(settings.get("activation_min_liquidity_usd") or 200.0)
        except Exception:
            threshold = 200.0

        if limit_monitoring:
            mons = repo.list_monitoring_for_activation(limit=limit_monitoring)
            monitoring_pairs = await batch_client.get_pairs_for_mints([t.mint_address for t in mons])
            promoted = 0
            for t in mons:
                batch_pairs = monitoring_pairs.get(t.mint_address) or []
                pairs = await ensure_pairs(t.mint_address, batch_pairs, threshold)
                
                if not pairs:
                    logv.debug(
                        "no_pairs_found_for_activation",
                        extra={"mint": t.mint_address}
                    )
                    # Avoid keeping the token at the front of the queue forever
                    repo.update_token_timestamp(t.id)
                    continue
                    
                from src.domain.validation.dex_rules import check_activation_conditions
                activation_result = check_activation_conditions(t.mint_address, pairs, threshold)
                
                logv.info(
                    f"activation_check_result: mint={t.mint_address[:8]}... batch={len(batch_pairs)} final={len(pairs)} result={activation_result} threshold={threshold}"
                )
                
                if activation_result:
                    name = None
                    symbol = None
                    for p in pairs:
                        base = (p.get("baseToken") or {})
                        if str(base.get("address")) == t.mint_address:
                            name = name or base.get("name")
                            symbol = symbol or base.get("symbol")
                            if name and symbol:
                                break
                    repo.update_token_fields(t, name=name, symbol=symbol)
                    repo.set_active(t)
                    promoted += 1
                    
                    # Record status transition for monitoring
                    try:
                        from src.monitoring.token_monitor import get_token_monitor
                        token_monitor = get_token_monitor()
                        token_monitor.record_status_transition(
                            mint_address=t.mint_address,
                            from_status="monitoring",
                            to_status="active",
                            reason="liquidity_threshold_met"
                        )
                    except Exception as e:
                        logv.warning(f"Failed to record token transition: {e}")
                    
                    logv.info(
                        "activated_by_liquidity",
                        extra={"extra": {"mint": t.mint_address, "threshold": threshold}},
                    )
                else:
                    # Token checked but still monitoring; bump timestamp so queue rotates
                    repo.update_token_timestamp(t.id)
            logv.info(
                "promotion_summary",
                extra={"extra": {"checked": len(mons), "promoted": promoted, "threshold": threshold}},
            )

        if limit_active:
            acts = repo.list_by_status("active", limit=limit_active)
            active_pairs = await batch_client.get_pairs_for_mints([t.mint_address for t in acts])
            demoted = 0
            from src.domain.validation.dex_rules import check_activation_conditions
            for t in acts:
                pairs = active_pairs.get(t.mint_address)
                if pairs is None:
                    continue
                pairs = await ensure_pairs(t.mint_address, pairs or [], threshold)
                if not check_activation_conditions(t.mint_address, pairs or [], threshold):
                    repo.set_monitoring(t)
                    demoted += 1
                    
                    # Record status transition for monitoring
                    try:
                        from src.monitoring.token_monitor import get_token_monitor
                        token_monitor = get_token_monitor()
                        token_monitor.record_status_transition(
                            mint_address=t.mint_address,
                            from_status="active",
                            to_status="monitoring",
                            reason="liquidity_threshold_not_met"
                        )
                    except Exception as e:
                        logv.warning(f"Failed to record token transition: {e}")
                    
                    logv.info(
                        "demoted_by_liquidity",
                        extra={"extra": {"mint": t.mint_address, "threshold": threshold}},
                    )
            logv.info(
                "demotion_summary",
                extra={"extra": {"checked": len(acts), "demoted": demoted, "threshold": threshold}},
            )


def enforce_activation_once(limit_monitoring: int = 50, limit_active: int = 50) -> None:
    """Backward-compatible entrypoint; schedules async activation when loop is running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(enforce_activation_async(limit_monitoring=limit_monitoring, limit_active=limit_active))
    else:
        loop.create_task(
            enforce_activation_async(limit_monitoring=limit_monitoring, limit_active=limit_active)
        )


def monitor_token_processing_once() -> None:
    """Monitor token processing performance and send alerts if needed."""
    try:
        from src.monitoring.token_monitor import get_token_monitor
        from src.monitoring.telegram_notifier import get_telegram_notifier
        
        token_monitor = get_token_monitor()
        telegram_notifier = get_telegram_notifier()
        
        if not telegram_notifier.is_configured():
            log.debug("Telegram not configured - skipping token processing monitoring")
            return
        
        # Collect current metrics
        metrics = token_monitor.collect_current_metrics()
        
        # Check for stuck tokens (>3 minutes in monitoring)
        if metrics.tokens_stuck_over_3m > 5:  # Alert if more than 5 tokens stuck
            telegram_notifier.send_token_processing_alert(
                alert_type="stuck_tokens",
                tokens_stuck=metrics.tokens_stuck_over_3m,
                processing_rate=metrics.tokens_processed_per_minute,
                backlog_size=metrics.processing_backlog,
                avg_activation_time=metrics.avg_time_to_activation_minutes
            )
            log.info(
                "stuck_tokens_alert_sent",
                extra={"stuck_count": metrics.tokens_stuck_over_3m}
            )
        
        # Check for slow processing (< 0.1 token per minute over 10+ minutes)
        # Only alert if there are many tokens stuck for a long time
        if (metrics.tokens_processed_per_minute < 0.1 and 
            metrics.processing_backlog > 50 and 
            metrics.tokens_stuck_over_3m > 10):  # Only if many tokens are actually stuck
            telegram_notifier.send_token_processing_alert(
                alert_type="slow_processing",
                tokens_stuck=metrics.tokens_stuck_over_3m,
                processing_rate=metrics.tokens_processed_per_minute,
                backlog_size=metrics.processing_backlog,
                avg_activation_time=metrics.avg_time_to_activation_minutes
            )
            log.info(
                "slow_processing_alert_sent",
                extra={
                    "processing_rate": metrics.tokens_processed_per_minute,
                    "backlog": metrics.processing_backlog
                }
            )
        
        # Check for growing backlog (>150 tokens in monitoring)
        if metrics.processing_backlog > 150:
            telegram_notifier.send_token_processing_alert(
                alert_type="backlog_growing",
                tokens_stuck=metrics.tokens_stuck_over_3m,
                processing_rate=metrics.tokens_processed_per_minute,
                backlog_size=metrics.processing_backlog,
                avg_activation_time=metrics.avg_time_to_activation_minutes
            )
            log.info(
                "backlog_growing_alert_sent",
                extra={"backlog_size": metrics.processing_backlog}
            )
        
        log.debug(
            "token_processing_monitoring_completed",
            extra={
                "monitoring_count": metrics.monitoring_count,
                "active_count": metrics.active_count,
                "stuck_tokens": metrics.tokens_stuck_over_3m,
                "processing_rate": metrics.tokens_processed_per_minute
            }
        )
        
    except Exception as e:
        log.error(f"Error in token processing monitoring: {e}", exc_info=True)


def send_system_health_summary_once() -> None:
    """Send periodic system health summary to Telegram."""
    try:
        from src.monitoring.telegram_notifier import get_telegram_notifier
        from src.monitoring.health_monitor import get_health_monitor
        from src.monitoring.token_monitor import get_token_monitor
        
        telegram_notifier = get_telegram_notifier()
        
        if not telegram_notifier.is_configured():
            log.debug("Telegram not configured - skipping health summary")
            return
        
        # Get system health data
        health_monitor = get_health_monitor()
        token_monitor = get_token_monitor()
        
        # Get resource health
        resource_health = health_monitor.metrics_collector.collect_resource_metrics()
        
        # Get token metrics
        token_metrics = token_monitor.collect_current_metrics()
        
        # Determine memory status
        memory_status = "healthy"
        if resource_health.memory_usage_mb > 50000:  # >50GB
            memory_status = "critical"
        elif resource_health.memory_usage_mb > 40000:  # >40GB
            memory_status = "warning"
        
        # Determine API status (simplified)
        api_status = "healthy"  # Could be enhanced with actual API health checks
        
        # Calculate tokens processed in last hour (simplified)
        tokens_processed_last_hour = int(token_metrics.tokens_processed_per_minute * 60)
        
        # Count active alerts (simplified)
        active_alerts = len(resource_health.alerts)
        
        # Send summary
        success = telegram_notifier.send_system_health_summary(
            memory_status=memory_status,
            cpu_usage=resource_health.cpu_usage_percent,
            api_status=api_status,
            tokens_processed_last_hour=tokens_processed_last_hour,
            active_alerts=active_alerts
        )
        
        if success:
            log.info(
                "system_health_summary_sent",
                extra={
                    "memory_status": memory_status,
                    "cpu_usage": resource_health.cpu_usage_percent,
                    "tokens_processed": tokens_processed_last_hour,
                    "active_alerts": active_alerts
                }
            )
        
    except Exception as e:
        log.error(f"Error sending system health summary: {e}", exc_info=True)


# Memory monitoring is now handled by the performance optimizer

def optimize_performance_once() -> None:
    """Run performance optimization cycle."""
    try:
        from src.monitoring.performance_optimizer import get_performance_optimizer
        
        optimizer = get_performance_optimizer()
        result = optimizer.run_optimization_cycle()
        
        if result.get("optimizations_applied", 0) > 0:
            log.info(
                "performance_optimizations_applied",
                extra={
                    "optimizations_count": result["optimizations_applied"],
                    "actions": result.get("actions", []),
                    "current_settings": result.get("current_settings", {})
                }
            )
        else:
            log.debug(
                "performance_optimization_cycle_completed",
                extra={
                    "metrics": result.get("metrics", {}),
                    "no_optimizations_needed": True
                }
            )
        
    except Exception as e:
        log.error(f"Error in performance optimization: {e}", exc_info=True)


async def monitor_spam_once() -> None:
    """Monitor spam levels for top tokens."""
    try:
        with SessionLocal() as sess:
            repo = TokensRepository(sess)
            settings = SettingsService(sess)
            
            # Get minimum score threshold for NotArb config export
            # This is the threshold for tokens that get exported to the bot
            notarb_min_score = float(settings.get("notarb_min_score") or 0.5)
            
            # Get active tokens above NotArb threshold
            tokens = repo.get_active_tokens_above_score(notarb_min_score)
            
            if not tokens:
                log.info("spam_monitor", extra={"extra": {"message": "No tokens to monitor"}})
                return
            
            log.info("spam_monitor_start", extra={"extra": {"token_count": len(tokens)}})
            
            async with SpamDetector() as detector:
                spam_results = []
                
                # Analyze all tokens in parallel for better performance
                async def analyze_and_save(token):
                    """Analyze single token and save results."""
                    try:
                        result = await detector.analyze_token_spam(token.mint_address)
                        
                        if "error" not in result:
                            spam_metrics = result.get("spam_metrics", {})
                            spam_pct = spam_metrics.get("spam_percentage", 0)
                            risk_level = spam_metrics.get("risk_level", "unknown")
                            
                            # Save spam metrics to database
                            try:
                                from datetime import datetime, timezone
                                spam_data = {
                                    "spam_percentage": spam_pct,
                                    "risk_level": risk_level,
                                    "total_instructions": spam_metrics.get("total_instructions", 0),
                                    "compute_budget_count": spam_metrics.get("compute_budget_count", 0),
                                    "analyzed_at": datetime.now(tz=timezone.utc).isoformat()
                                }
                                repo.update_spam_metrics(token.id, spam_data)
                            except Exception as e:
                                log.error(f"Failed to save spam metrics for {token.mint_address}: {e}")
                            
                            # Log high spam tokens
                            if risk_level in ["high", "medium"]:
                                log.warning("high_spam_detected", extra={
                                    "extra": {
                                        "mint_address": token.mint_address,
                                        "spam_percentage": spam_pct,
                                        "risk_level": risk_level
                                    }
                                })
                            
                            return {
                                "mint_address": token.mint_address,
                                "spam_percentage": spam_pct,
                                "risk_level": risk_level
                            }
                        
                    except Exception as e:
                        log.error(f"Error analyzing spam for {token.mint_address}: {e}")
                        return None
                
                # Process all tokens in parallel
                tasks = [analyze_and_save(token) for token in tokens]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Collect successful results
                spam_results = [r for r in results if r and not isinstance(r, Exception)]
                
                # Log summary
                if spam_results:
                    high_spam_count = sum(1 for r in spam_results if r["risk_level"] in ["high", "medium"])
                    avg_spam = sum(r["spam_percentage"] for r in spam_results) / len(spam_results)
                    
                    log.info("spam_monitor_complete", extra={
                        "extra": {
                            "tokens_analyzed": len(spam_results),
                            "high_spam_count": high_spam_count,
                            "average_spam_percentage": round(avg_spam, 1)
                        }
                    })
                
    except Exception as e:
        log.error(f"Spam monitoring failed: {e}")


def run_spam_monitor() -> None:
    """Sync wrapper for spam monitoring."""
    try:
        asyncio.run(monitor_spam_once())
    except Exception as e:
        log.error(f"Failed to run spam monitor: {e}")


async def process_archived_tokens_async(limit: int = 20) -> None:
    """
    Безопасная обработка архивных токенов с более строгими условиями активации.

    Условия активации для archived токенов (все должны выполняться):
    1) Больше одного внешнего пула
    2) Pump.fun и хотя бы один внешний пул
    3) Ликвидность внешнего пула больше заданного порога
    4) Более 300 транзакций за последние 5 минут

    Безопасность:
    - Работает только при CPU < 70%
    - Малый batch size (20 токенов)
    - Обрабатывает самые свежие архивные токены (max 7 дней)
    """
    logv = logging.getLogger("archived_processor")

    # Проверка системной нагрузки
    try:
        from src.monitoring.metrics import get_load_processor
        load_processor = get_load_processor()
        current_load = load_processor.get_current_load()

        cpu_percent = current_load.get("cpu_percent", 100)
        memory_percent = current_load.get("memory_percent", 100)

        # Не запускаем при высокой нагрузке
        if cpu_percent > 70 or memory_percent > 85:
            logv.info(
                "archived_processing_skipped_high_load",
                extra={"cpu": cpu_percent, "memory": memory_percent}
            )
            return

    except Exception as e:
        logv.warning(f"Failed to check system load: {e}")
        return  # Безопасность: не запускаем если не можем проверить нагрузку

    from src.adapters.services.dexscreener_batch_client import get_batch_client
    batch_client = await get_batch_client()

    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)

        # Проверяем, включена ли обработка архивных токенов
        process_archived_enabled = settings.get("process_archived_tokens") == "true"
        if not process_archived_enabled:
            logv.debug("archived_processing_disabled_in_settings")
            return

        try:
            threshold = float(settings.get("activation_min_liquidity_usd") or 500.0)
            min_txns_5m = int(settings.get("archived_min_txns_5m") or 300)
            max_archive_age_days = int(settings.get("archived_max_age_days") or 7)
        except Exception:
            threshold = 500.0
            min_txns_5m = 300
            max_archive_age_days = 7

        # Получаем свежие архивные токены (не старше N дней)
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=max_archive_age_days)
        archived = repo.list_archived_since(cutoff_date, limit=limit)

        if not archived:
            logv.debug("no_archived_tokens_to_process")
            return

        logv.info(
            "archived_processing_started",
            extra={
                "tokens_count": len(archived),
                "threshold": threshold,
                "min_txns_5m": min_txns_5m,
                "max_age_days": max_archive_age_days,
                "cpu": cpu_percent,
                "memory": memory_percent
            }
        )

        # Получаем данные по всем токенам batch-запросом
        archived_pairs = await batch_client.get_pairs_for_mints([t.mint_address for t in archived])

        promoted = 0
        checked = 0

        for t in archived:
            pairs = archived_pairs.get(t.mint_address) or []

            if not pairs:
                continue

            checked += 1

            # Проверяем строгие условия активации для архивных токенов
            from src.domain.validation.dex_rules import check_archived_token_activation

            if check_archived_token_activation(
                t.mint_address,
                pairs,
                min_liquidity_usd=threshold,
                min_txns_5m=min_txns_5m
            ):
                # Обновляем метаданные токена
                name = None
                symbol = None
                for p in pairs:
                    base = (p.get("baseToken") or {})
                    if str(base.get("address")) == t.mint_address:
                        name = name or base.get("name")
                        symbol = symbol or base.get("symbol")
                        if name and symbol:
                            break

                repo.update_token_fields(t, name=name, symbol=symbol)

                # Переводим в monitoring (не сразу в active для проверки)
                repo.set_monitoring(t)
                promoted += 1

                # Record status transition
                try:
                    from src.monitoring.token_monitor import get_token_monitor
                    token_monitor = get_token_monitor()
                    token_monitor.record_status_transition(
                        mint_address=t.mint_address,
                        from_status="archived",
                        to_status="monitoring",
                        reason="archived_reactivation"
                    )
                except Exception as e:
                    logv.warning(f"Failed to record token transition: {e}")

                logv.info(
                    "archived_token_promoted",
                    extra={
                        "mint": t.mint_address,
                        "threshold": threshold,
                        "min_txns_5m": min_txns_5m
                    }
                )

        logv.info(
            "archived_processing_completed",
            extra={
                "checked": checked,
                "promoted": promoted,
                "success_rate": f"{(promoted/checked*100):.1f}%" if checked > 0 else "0%"
            }
        )


def process_archived_tokens_once(limit: int = 20) -> None:
    """Sync wrapper for archived tokens processing."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(process_archived_tokens_async(limit=limit))
    else:
        loop.create_task(process_archived_tokens_async(limit=limit))