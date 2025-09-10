from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.validation.dex_rules import check_activation_conditions


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
    logv = logging.getLogger("validator")
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        tokens = repo.list_by_status("monitoring", limit=limit)
        client = DexScreenerClient(timeout=5.0)
        checked = 0
        activated = 0
        for t in tokens:
            checked += 1
            pairs = client.get_pairs(t.mint_address)
            if pairs is None:
                logv.warning("pairs_fetch_failed", extra={"extra": {"mint": t.mint_address}})
                continue
            ok = check_activation_conditions(t.mint_address, pairs)
            if ok:
                # Пробуем обновить name/symbol из данных пары (если пусто)
                name = None
                symbol = None
                try:
                    # берем первое вхождение baseToken.name/symbol, где адрес совпадает
                    for p in pairs:
                        base = (p.get("baseToken") or {})
                        if str(base.get("address")) == t.mint_address:
                            name = base.get("name") or name
                            symbol = base.get("symbol") or symbol
                            if name or symbol:
                                break
                except Exception:
                    pass
                repo.update_token_fields(t, name=name, symbol=symbol)
                repo.set_active(t)
                activated += 1
                logv.info("activated", extra={"extra": {"mint": t.mint_address, "name": name, "symbol": symbol}})
            else:
                logv.info("kept_monitoring", extra={"extra": {"mint": t.mint_address}})
        logv.info("validator_summary", extra={"extra": {"checked": checked, "activated": activated}})
