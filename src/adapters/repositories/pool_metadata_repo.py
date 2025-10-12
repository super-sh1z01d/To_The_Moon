from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from src.adapters.db.models import PoolMetadata


class PoolMetadataRepository:
    """Persistence layer for Solana pool program owners and resolved types."""

    _table_ready: bool = False

    def __init__(self, db: Session):
        self.db = db
        self._log = logging.getLogger("pool_metadata_repo")
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create supporting table if it does not exist yet."""
        if type(self)._table_ready:
            return

        ddl = text(
            """
            CREATE TABLE IF NOT EXISTS pool_metadata (
                pool_address TEXT PRIMARY KEY,
                owner_program TEXT NOT NULL,
                pool_type TEXT NOT NULL,
                fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        index_sql = text(
            """
            CREATE INDEX IF NOT EXISTS idx_pool_metadata_owner
                ON pool_metadata (owner_program);
            CREATE INDEX IF NOT EXISTS idx_pool_metadata_type
                ON pool_metadata (pool_type);
            """
        )

        try:
            self.db.execute(ddl)
            self.db.execute(index_sql)
            self.db.commit()
        except ProgrammingError as exc:  # pragma: no cover - defensive
            self.db.rollback()
            self._log.error("pool_metadata_table_creation_failed", exc_info=exc)
            raise
        else:
            type(self)._table_ready = True

    def get_many(self, addresses: Iterable[str]) -> Dict[str, Dict[str, str]]:
        """Return mapping pool_address -> metadata."""
        address_list = [addr for addr in addresses if addr]
        if not address_list:
            return {}

        stmt = (
            select(PoolMetadata.pool_address, PoolMetadata.owner_program, PoolMetadata.pool_type)
            .where(PoolMetadata.pool_address.in_(address_list))
        )
        rows = self.db.execute(stmt).all()

        return {
            row.pool_address: {
                "owner_program": row.owner_program,
                "pool_type": row.pool_type,
            }
            for row in rows
        }

    def upsert(
        self,
        pool_address: str,
        owner_program: str,
        pool_type: str,
        fetched_at: Optional[datetime] = None,
        commit: bool = True,
    ) -> None:
        """Create or update metadata for a pool."""
        if not pool_address:
            return

        fetched_at = fetched_at or datetime.now(timezone.utc)

        record = self.db.get(PoolMetadata, pool_address)
        if record:
            record.owner_program = owner_program
            record.pool_type = pool_type
            record.fetched_at = fetched_at
        else:
            record = PoolMetadata(
                pool_address=pool_address,
                owner_program=owner_program,
                pool_type=pool_type,
                fetched_at=fetched_at,
            )
            self.db.add(record)

        if commit:
            self.db.commit()

    def bulk_upsert(self, items: Iterable[tuple[str, str, str]]) -> None:
        """Upsert multiple metadata items in a single transaction."""
        now = datetime.now(timezone.utc)
        for pool_address, owner_program, pool_type in items:
            self.upsert(pool_address, owner_program, pool_type, fetched_at=now, commit=False)
        self.db.commit()

    def delete(self, pool_address: str) -> None:
        """Remove metadata for a pool (useful for reclassification)."""
        if not pool_address:
            return
        record = self.db.get(PoolMetadata, pool_address)
        if record:
            self.db.delete(record)
            self.db.commit()
