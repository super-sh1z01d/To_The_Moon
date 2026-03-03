from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from src.core.config import get_config


class Base(DeclarativeBase):
    pass


def make_engine() -> Engine:
    cfg = get_config()
    url = (cfg.database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL must be set (PostgreSQL only)")
    if not url.startswith("postgresql"):
        raise RuntimeError("Only PostgreSQL is supported. DATABASE_URL must start with 'postgresql'.")
    return create_engine(url, poolclass=NullPool)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
