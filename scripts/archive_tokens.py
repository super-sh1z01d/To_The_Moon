#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive tokens by rules from spec")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist changes, only log decisions")
    args = parser.parse_args()

    configure_logging(level="INFO")
    log = logging.getLogger("archiver")

    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        min_score = float(settings.get("min_score") or 0.1)
        archive_below_hours = int(settings.get("archive_below_hours") or 12)
        monitoring_timeout_hours = int(settings.get("monitoring_timeout_hours") or 12)

        # Rule 1: Archive active tokens with score < min_score during archive_below_hours
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=archive_below_hours)
        active = repo.list_by_status("active", limit=1000)
        a_checked = 0
        a_archived = 0
        for t in active:
            a_checked += 1
            ok = repo.has_score_ge_since(t.id, min_score=min_score, since_dt=cutoff)
            if not ok:
                a_archived += 1
                log.info(
                    "archive_candidate_active",
                    extra={"extra": {"mint": t.mint_address, "since": cutoff.isoformat(), "min_score": min_score}},
                )
                if not args.dry_run:
                    repo.archive_token(t, reason="low_score_timeout")
        log.info("active_archive_summary", extra={"extra": {"checked": a_checked, "archived": a_archived}})

        # Rule 2: Archive monitoring tokens older than monitoring_timeout_hours
        mons = repo.list_monitoring_older_than_hours(monitoring_timeout_hours, limit=1000)
        m_archived = 0
        for t in mons:
            m_archived += 1
            log.info(
                "archive_candidate_monitoring",
                extra={"extra": {"mint": t.mint_address, "created_at": t.created_at.isoformat()}},
            )
            if not args.dry_run:
                repo.archive_token(t, reason="monitoring_timeout")
        log.info("monitoring_archive_summary", extra={"extra": {"archived": m_archived}})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

