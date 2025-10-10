from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


UTC_NOW = lambda: datetime.now(tz=timezone.utc)  # noqa: E731


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mint_address: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="monitoring", index=True)
    
    # Extracted fields for fast filtering (from metrics)
    liquidity_usd: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True, index=True)
    primary_dex: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=UTC_NOW, nullable=False, index=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status in ('monitoring','active','archived')",
            name="ck_tokens_status",
        ),
    )

    scores: Mapped[list[TokenScore]] = relationship(
        back_populates="token", cascade="all, delete-orphan", lazy="selectin"
    )  # type: ignore[name-defined]


class TokenScore(Base):
    __tablename__ = "token_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey("tokens.id", ondelete="CASCADE"), index=True, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    smoothed_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True, index=True)
    
    # Use JSONB for PostgreSQL (falls back to JSON for SQLite)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    raw_components: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    smoothed_components: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    # spam_metrics removed - not in PostgreSQL schema yet
    
    scoring_model: Mapped[str] = mapped_column(String(50), default="hybrid_momentum", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=UTC_NOW, nullable=False, index=True)

    token: Mapped[Token] = relationship(back_populates="scores")


class AppSetting(Base):
    __tablename__ = "app_settings"

    # Using text PK to match spec
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
