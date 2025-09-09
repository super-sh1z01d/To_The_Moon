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
    url = cfg.database_url or "sqlite:///dev.db"
    connect_args = {}
    if url.startswith("sqlite"):
        # Allow usage across threads in dev
        connect_args = {"check_same_thread": False}
    return create_engine(url, poolclass=NullPool, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

