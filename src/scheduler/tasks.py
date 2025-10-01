from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta, timezone

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService


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
        log.info("archiver_active", extra={"extra": {"archived": archived, "cutoff": cutoff.isoformat()}})

        mons = repo.list_monitoring_older_than_hours(monitoring_timeout_hours, limit=1000)
        m_arch = 0
        for t in mons:
            repo.archive_token(t, reason="monitoring_timeout")
            m_arch += 1
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

    batch_client = await get_batch_client()

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
                pairs = monitoring_pairs.get(t.mint_address) or []
                if not pairs:
                    continue
                from src.domain.validation.dex_rules import check_activation_conditions
                if check_activation_conditions(t.mint_address, pairs, threshold):
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
                    logv.info(
                        "activated_by_liquidity",
                        extra={"extra": {"mint": t.mint_address, "threshold": threshold}},
                    )
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
                if not check_activation_conditions(t.mint_address, pairs or [], threshold):
                    repo.set_monitoring(t)
                    demoted += 1
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
