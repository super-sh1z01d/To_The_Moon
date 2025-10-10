-- PostgreSQL Optimization Script
-- Run this after initial migration to add advanced indexes and partitioning

-- ============================================================================
-- PART 1: Additional Indexes for Performance
-- ============================================================================

-- GIN indexes for JSONB columns (PostgreSQL only)
CREATE INDEX IF NOT EXISTS idx_token_scores_metrics_gin 
    ON token_scores USING GIN(metrics);

CREATE INDEX IF NOT EXISTS idx_token_scores_raw_components_gin 
    ON token_scores USING GIN(raw_components);

CREATE INDEX IF NOT EXISTS idx_token_scores_spam_metrics_gin 
    ON token_scores USING GIN(spam_metrics);

-- Partial indexes for active tokens (most queried)
CREATE INDEX IF NOT EXISTS idx_tokens_active_liquidity 
    ON tokens(liquidity_usd DESC) 
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_tokens_active_created 
    ON tokens(created_at DESC) 
    WHERE status = 'active';

-- Index for monitoring tokens
CREATE INDEX IF NOT EXISTS idx_tokens_monitoring_score 
    ON tokens(id) 
    WHERE status = 'monitoring';

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_tokens_status_liquidity 
    ON tokens(status, liquidity_usd DESC);

-- ============================================================================
-- PART 2: Table Partitioning for token_scores
-- ============================================================================

-- Note: This requires recreating the table with partitioning
-- Only run this section if you want to enable partitioning

-- Step 1: Rename existing table
-- ALTER TABLE token_scores RENAME TO token_scores_old;

-- Step 2: Create partitioned table
-- CREATE TABLE token_scores (
--     id BIGSERIAL,
--     token_id INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
--     score NUMERIC(10, 4),
--     smoothed_score NUMERIC(10, 4),
--     metrics JSONB,
--     raw_components JSONB,
--     smoothed_components JSONB,
--     spam_metrics JSONB,
--     scoring_model VARCHAR(50) NOT NULL DEFAULT 'hybrid_momentum',
--     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     PRIMARY KEY (id, created_at)
-- ) PARTITION BY RANGE (created_at);

-- Step 3: Create partitions for current and next months
-- CREATE TABLE token_scores_2024_10 PARTITION OF token_scores
--     FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
-- 
-- CREATE TABLE token_scores_2024_11 PARTITION OF token_scores
--     FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
-- 
-- CREATE TABLE token_scores_2024_12 PARTITION OF token_scores
--     FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- Step 4: Create indexes on partitions
-- CREATE INDEX idx_scores_token_created_2024_10 
--     ON token_scores_2024_10(token_id, created_at DESC);
-- CREATE INDEX idx_scores_smoothed_2024_10 
--     ON token_scores_2024_10(smoothed_score DESC);
-- CREATE INDEX idx_scores_metrics_gin_2024_10 
--     ON token_scores_2024_10 USING GIN(metrics);

-- Step 5: Copy data from old table
-- INSERT INTO token_scores SELECT * FROM token_scores_old;

-- Step 6: Drop old table
-- DROP TABLE token_scores_old;

-- ============================================================================
-- PART 3: Materialized View for Latest Scores
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS latest_token_scores AS
SELECT DISTINCT ON (token_id)
    token_id,
    score,
    smoothed_score,
    metrics,
    raw_components,
    smoothed_components,
    spam_metrics,
    scoring_model,
    created_at
FROM token_scores
ORDER BY token_id, created_at DESC;

-- Indexes on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_latest_scores_token 
    ON latest_token_scores(token_id);

CREATE INDEX IF NOT EXISTS idx_latest_scores_smoothed 
    ON latest_token_scores(smoothed_score DESC) 
    WHERE smoothed_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_latest_scores_score 
    ON latest_token_scores(score DESC) 
    WHERE score IS NOT NULL;

-- ============================================================================
-- PART 4: Performance Monitoring
-- ============================================================================

-- Enable pg_stat_statements for query monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_latest_scores()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY latest_token_scores;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 5: Maintenance Functions
-- ============================================================================

-- Function to create next month's partition
CREATE OR REPLACE FUNCTION create_next_partition()
RETURNS void AS $$
DECLARE
    next_month DATE;
    month_after DATE;
    partition_name TEXT;
BEGIN
    next_month := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    month_after := next_month + INTERVAL '1 month';
    partition_name := 'token_scores_' || TO_CHAR(next_month, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF token_scores
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, next_month, month_after
    );
    
    -- Add indexes to new partition
    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS idx_scores_token_created_%s 
         ON %I(token_id, created_at DESC)',
        TO_CHAR(next_month, 'YYYY_MM'), partition_name
    );
    
    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS idx_scores_smoothed_%s 
         ON %I(smoothed_score DESC)',
        TO_CHAR(next_month, 'YYYY_MM'), partition_name
    );
    
    RAISE NOTICE 'Created partition: %', partition_name;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 6: Verify Optimizations
-- ============================================================================

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Check table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check materialized view freshness
SELECT 
    schemaname,
    matviewname,
    last_refresh
FROM pg_matviews
WHERE schemaname = 'public';
