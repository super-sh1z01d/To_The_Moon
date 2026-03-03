from __future__ import annotations

import os


# Test suite is PostgreSQL-only; provide a non-empty DSN for import-time engine construction.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://user:pass@localhost:5432/tothemoon_test",
)
