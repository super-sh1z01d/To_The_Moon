from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
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
    
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    raw_components: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    smoothed_components: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # spam_metrics removed - not in PostgreSQL schema yet
    
    scoring_model: Mapped[str] = mapped_column(String(50), default="hybrid_momentum", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=UTC_NOW, nullable=False, index=True)

    token: Mapped[Token] = relationship(back_populates="scores")


class AppSetting(Base):
    __tablename__ = "app_settings"

    # Using text PK to match spec
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Nullable for OAuth users
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # "user" or "admin"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=UTC_NOW, nullable=False)

    # OAuth fields
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="email", nullable=False)  # "email" or "google"
    profile_picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=UTC_NOW, nullable=False, index=True)
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    token_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True, index=True
    )
    leased_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=UTC_NOW, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=UTC_NOW, onupdate=UTC_NOW, nullable=False, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('queued','leased','retry','done','deadletter','cancelled')",
            name="ck_processing_jobs_status",
        ),
    )


class TokenRuntimeState(Base):
    __tablename__ = "token_runtime_state"

    token_id: Mapped[int] = mapped_column(
        ForeignKey("tokens.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    last_scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_activation_check_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    score_band: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    backoff_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=UTC_NOW, onupdate=UTC_NOW, nullable=False, index=True
    )
