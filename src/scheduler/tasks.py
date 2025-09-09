from __future__ import annotations

import logging
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

