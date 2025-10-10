"""Task for refreshing materialized views."""
from __future__ import annotations

import logging
from sqlalchemy import text

from src.adapters.db.base import SessionLocal


log = logging.getLogger("refresh_views")


def refresh_materialized_views() -> None:
    """Refresh all materialized views for better query performance."""
    with SessionLocal() as sess:
        try:
            # Refresh latest_token_scores view
            sess.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_token_scores"))
            sess.commit()
            log.info("Refreshed materialized view: latest_token_scores")
        except Exception as e:
            log.error(f"Failed to refresh materialized views: {e}")
            sess.rollback()
