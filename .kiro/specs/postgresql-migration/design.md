PostgreSQL Migration & Database Optimization Design
Overview
This document outlines the comprehensive design for migrating To The Moon from SQLite to PostgreSQL with database schema optimization, performance improvements, and preparation for multi-user access. The migration will reduce API response times from 28 seconds to <1 second and establish a foundation for user authentication, API keys, and audit logging.

Architecture
High-Level Architecture
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   FastAPI    │  │  Scheduler   │  │   Workers    │      │
│  │   Routes     │  │   Service    │  │  (WebSocket) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  SQLAlchemy ORM │
                    │  + Repositories │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Connection Pool│
                    │   (5-20 conns)  │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
    │PostgreSQL │     │PostgreSQL │     │PostgreSQL │
    │  Primary  │────▶│  Replica  │     │  Backup   │
    │  (Write)  │     │  (Read)   │     │ (pg_dump) │
    └───────────┘     └───────────┘     └───────────┘
Database Architecture
PostgreSQL 14+ Configuration:

Primary database for writes
Optional read replica for heavy queries
Automated backups with pg_dump
Connection pooling via SQLAlchemy
JSONB for metrics storage
Table partitioning for token_scores
Components and Interfaces
1. Optimized Database Schema
Core Tables (Optimized)
tokens - Token registry with extracted fields

CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    mint_address TEXT UNIQUE NOT NULL,
    name TEXT,
    symbol TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'monitoring'
        CHECK (status IN ('monitoring', 'active', 'archived')),
    
    -- Extracted from metrics for fast filtering
    liquidity_usd NUMERIC(20, 2),
    primary_dex VARCHAR(50),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT tokens_pkey PRIMARY KEY (id)
);

CREATE UNIQUE INDEX idx_tokens_mint ON tokens(mint_address);
CREATE INDEX idx_tokens_status ON tokens(status) WHERE status != 'archived';
CREATE INDEX idx_tokens_liquidity ON tokens(liquidity_usd DESC) WHERE status = 'active';
CREATE INDEX idx_tokens_created ON tokens(created_at DESC);
token_scores - Partitioned by month for performance

CREATE TABLE token_scores (
    id BIGSERIAL,
    token_id INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    score NUMERIC(10, 4),
    smoothed_score NUMERIC(10, 4),
    
    -- JSONB for flexible metrics (indexed)
    metrics JSONB,
    raw_components JSONB,
    smoothed_components JSONB,
    spam_metrics JSONB,
    
    scoring_model VARCHAR(50) NOT NULL DEFAULT 'hybrid_momentum',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE token_scores_2024_10 PARTITION OF token_scores
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');

CREATE TABLE token_scores_2024_11 PARTITION OF token_scores
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');

-- Indexes on each partition
CREATE INDEX idx_scores_token_created_2024_10 
    ON token_scores_2024_10(token_id, created_at DESC);
CREATE INDEX idx_scores_smoothed_2024_10 
    ON token_scores_2024_10(smoothed_score DESC) WHERE smoothed_score IS NOT NULL;

-- GIN index for JSONB queries
CREATE INDEX idx_scores_metrics_2024_10 
    ON token_scores_2024_10 USING GIN(metrics);
app_settings - System configuration

CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_settings_updated ON app_settings(updated_at DESC);
Future-Ready Tables
users - User authentication and management

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'premium', 'admin')),
    
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    -- Profile
    display_name VARCHAR(100),
    avatar_url TEXT
);

CREATE UNIQUE INDEX idx_users_email ON users(LOWER(email));
CREATE INDEX idx_users_role ON users(role) WHERE is_active = TRUE;
CREATE INDEX idx_users_created ON users(created_at DESC);
api_keys - API access management

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL, -- First 8 chars for display
    
    name VARCHAR(100),
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    rate_limit_per_day INTEGER NOT NULL DEFAULT 10000,
    
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_apikeys_user ON api_keys(user_id) WHERE is_active = TRUE;
CREATE UNIQUE INDEX idx_apikeys_hash ON api_keys(key_hash);
CREATE INDEX idx_apikeys_expires ON api_keys(expires_at) WHERE is_active = TRUE;
user_favorites - User's favorite tokens

CREATE TABLE user_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_id INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, token_id)
);

CREATE INDEX idx_favorites_user ON user_favorites(user_id, created_at DESC);
CREATE INDEX idx_favorites_token ON user_favorites(token_id);
audit_logs - User action tracking

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
    
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id TEXT,
    
    ip_address INET,
    user_agent TEXT,
    
    request_method VARCHAR(10),
    request_path TEXT,
    response_status INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Monthly partitions for audit logs
CREATE TABLE audit_logs_2024_10 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');

CREATE INDEX idx_audit_user_2024_10 ON audit_logs_2024_10(user_id, created_at DESC);
CREATE INDEX idx_audit_action_2024_10 ON audit_logs_2024_10(action, created_at DESC);
2. Optimized Queries
Current Slow Query (28 seconds)
-- OLD: SQLite with GROUP BY + multiple JOINs
SELECT t.*, ts.*
FROM tokens t
LEFT JOIN (
    SELECT token_id, MAX(created_at) as max_created_at
    FROM token_scores
    GROUP BY token_id  -- Scans 847K rows!
) sub ON sub.token_id = t.id
LEFT JOIN token_scores ts 
    ON ts.token_id = sub.token_id 
    AND ts.created_at = sub.max_created_at
WHERE t.status = 'active'
ORDER BY COALESCE(ts.smoothed_score, ts.score) DESC
LIMIT 50;
Optimized Query (<1 second)
-- NEW: PostgreSQL with DISTINCT ON + indexes
SELECT DISTINCT ON (t.id) 
    t.*,
    ts.score,
    ts.smoothed_score,
    ts.metrics,
    ts.spam_metrics
FROM tokens t
LEFT JOIN token_scores ts ON ts.token_id = t.id
WHERE t.status = 'active'
ORDER BY t.id, ts.created_at DESC
LIMIT 50;

-- Then sort in application or use window function
Even Better: Materialized View
CREATE MATERIALIZED VIEW latest_token_scores AS
SELECT DISTINCT ON (token_id)
    token_id,
    score,
    smoothed_score,
    metrics,
    spam_metrics,
    created_at
FROM token_scores
ORDER BY token_id, created_at DESC;

CREATE UNIQUE INDEX idx_latest_scores_token ON latest_token_scores(token_id);
CREATE INDEX idx_latest_scores_smoothed ON latest_token_scores(smoothed_score DESC);

-- Refresh every 30 seconds
REFRESH MATERIALIZED VIEW CONCURRENTLY latest_token_scores;
3. Connection Pooling
SQLAlchemy Configuration:

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,          # Minimum connections
    max_overflow=15,      # Maximum total = 20
    pool_timeout=30,      # Wait 30s for connection
    pool_recycle=300,     # Recycle after 5 minutes
    pool_pre_ping=True,   # Verify connection before use
    echo_pool=True        # Log pool events
)
4. Data Migration Strategy
Phase 1: Setup PostgreSQL

Install PostgreSQL 14+
Create database and user
Configure pg_hba.conf for local access
Set up automated backups
Phase 2: Schema Migration

Create new Alembic migration
Apply schema to PostgreSQL
Create all indexes
Create partitions for current/next month
Create materialized views
Phase 3: Data Migration

Stop scheduler (prevent new writes)
Backup SQLite database
Export data using custom script:
Tokens: Direct copy
Token_scores: Batch insert (10K rows at a time)
App_settings: Direct copy
Verify row counts match
Verify sample queries return same results
Phase 4: Cutover

Update DATABASE_URL in .env
Restart application
Monitor logs for errors
Run performance tests
Keep SQLite as backup for 7 days
Data Models
SQLAlchemy Models (Updated)
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True)
    mint_address = Column(Text, unique=True, nullable=False, index=True)
    name = Column(Text)
    symbol = Column(Text)
    status = Column(String(20), nullable=False, default="monitoring", index=True)
    
    # Extracted for performance
    liquidity_usd = Column(Numeric(20, 2), index=True)
    primary_dex = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        CheckConstraint("status IN ('monitoring', 'active', 'archived')"),
    )
    
    scores = relationship("TokenScore", back_populates="token", cascade="all, delete-orphan")

class TokenScore(Base):
    __tablename__ = "token_scores"
    
    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Numeric(10, 4))
    smoothed_score = Column(Numeric(10, 4), index=True)
    
    # JSONB for PostgreSQL
    metrics = Column(JSONB)
    raw_components = Column(JSONB)
    smoothed_components = Column(JSONB)
    spam_metrics = Column(JSONB)
    
    scoring_model = Column(String(50), nullable=False, default="hybrid_momentum")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    token = relationship("Token", back_populates="scores")
    
    __table_args__ = (
        Index('idx_token_scores_token_created', 'token_id', 'created_at'),
    )
Error Handling
Migration Errors
Connection failure: Retry with exponential backoff
Data integrity: Rollback and restore from SQLite
Disk space: Pre-check available space (need 3x current DB size)
Timeout: Increase statement_timeout for large batches
Runtime Errors
Connection pool exhausted: Queue requests with timeout
Deadlock: Retry transaction up to 3 times
Partition missing: Auto-create next month's partition
Materialized view stale: Refresh in background task
Testing Strategy
Pre-Migration Tests
Schema validation: Verify all tables/indexes created
Data integrity: Compare row counts and checksums
Query performance: Benchmark critical queries
Connection pool: Load test with 50 concurrent requests
Post-Migration Tests
Functional tests: All API endpoints return correct data
Performance tests: Response time < 1 second for /tokens
Load tests: Handle 100 concurrent users
Failover tests: Verify backup/restore procedures
Monitoring
Query performance (pg_stat_statements)
Connection pool metrics
Table/index sizes
Partition health
Replication lag (if using replica)