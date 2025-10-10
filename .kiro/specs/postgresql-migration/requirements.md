# PostgreSQL Migration & Database Optimization Requirements

## Introduction

Migrate the To The Moon application from SQLite to PostgreSQL with comprehensive database redesign to improve performance, scalability, and prepare for multi-user access with authentication. Current SQLite database (1.4GB, 847K score records) causes 28-second API response times. The redesigned PostgreSQL schema with proper indexing, partitioning, and optimization should reduce this to <1 second and support future features like user accounts, API keys, rate limiting, and audit logs.

## Requirements

### Requirement 1: PostgreSQL Setup

**User Story:** As a system administrator, I want PostgreSQL installed and configured on the server, so that the application can use it as the primary database.

#### Acceptance Criteria

1. WHEN PostgreSQL 14+ is installed THEN it SHALL be accessible on localhost:5432
2. WHEN database user is created THEN it SHALL have full permissions on the application database
3. WHEN database is created THEN it SHALL use UTF-8 encoding
4. IF connection pooling is needed THEN pgbouncer SHALL be configured
5. WHEN PostgreSQL is running THEN it SHALL start automatically on system boot

### Requirement 2: Schema Migration

**User Story:** As a developer, I want the existing SQLite schema migrated to PostgreSQL, so that all tables and constraints are preserved.

#### Acceptance Criteria

1. WHEN schema is migrated THEN all tables (tokens, token_scores, app_settings) SHALL exist in PostgreSQL
2. WHEN constraints are migrated THEN all CHECK constraints, FOREIGN KEYS, and UNIQUE constraints SHALL be preserved
3. WHEN JSON columns are migrated THEN they SHALL use JSONB type for better performance
4. WHEN indexes are created THEN they SHALL include optimized composite indexes for common queries
5. IF migration fails THEN the system SHALL rollback and preserve SQLite data

### Requirement 3: Data Migration

**User Story:** As a system administrator, I want all existing data migrated from SQLite to PostgreSQL, so that no historical data is lost.

#### Acceptance Criteria

1. WHEN data migration starts THEN all 2,391 tokens SHALL be migrated
2. WHEN score data is migrated THEN all 847,080 token_scores records SHALL be transferred
3. WHEN settings are migrated THEN all app_settings SHALL be preserved
4. WHEN migration completes THEN data integrity SHALL be verified with checksums
5. IF migration fails THEN SQLite database SHALL remain as backup

### Requirement 4: Performance Optimization

**User Story:** As a user, I want fast API responses, so that the dashboard loads quickly.

#### Acceptance Criteria

1. WHEN composite index on (token_id, created_at DESC) is created THEN MAX(created_at) queries SHALL be 100x faster
2. WHEN index on tokens.status is created THEN status filtering SHALL be 10x faster
3. WHEN index on smoothed_score is created THEN sorting SHALL be 5x faster
4. WHEN GIN index on JSONB columns is created THEN JSON queries SHALL be 3x faster
5. WHEN API endpoint /tokens is called THEN response time SHALL be < 3 seconds

### Requirement 5: Application Configuration

**User Story:** As a developer, I want the application configured to use PostgreSQL, so that it connects to the new database.

#### Acceptance Criteria

1. WHEN DATABASE_URL is set THEN application SHALL connect to PostgreSQL
2. WHEN connection fails THEN application SHALL log error and retry
3. WHEN queries are executed THEN they SHALL use PostgreSQL-specific optimizations
4. IF SQLite-specific code exists THEN it SHALL be updated for PostgreSQL compatibility
5. WHEN application starts THEN it SHALL verify database connection

### Requirement 6: Query Optimization

**User Story:** As a developer, I want optimized queries for PostgreSQL, so that the application leverages PostgreSQL features.

#### Acceptance Criteria

1. WHEN fetching latest scores THEN query SHALL use DISTINCT ON instead of GROUP BY + JOIN
2. WHEN filtering by status THEN query SHALL use indexed column
3. WHEN sorting by score THEN query SHALL use indexed column
4. WHEN accessing JSON fields THEN query SHALL use JSONB operators
5. WHEN query plan is analyzed THEN it SHALL use indexes (no sequential scans)

### Requirement 7: Backup and Rollback

**User Story:** As a system administrator, I want backup and rollback procedures, so that I can recover if migration fails.

#### Acceptance Criteria

1. WHEN migration starts THEN SQLite database SHALL be backed up
2. WHEN PostgreSQL is populated THEN a pg_dump backup SHALL be created
3. WHEN rollback is needed THEN application SHALL be able to switch back to SQLite
4. WHEN backup is created THEN it SHALL be stored in /srv/tothemoon/backups/
5. IF disk space is low THEN migration SHALL not proceed

### Requirement 8: Schema Redesign and Optimization

**User Story:** As a developer, I want an optimized database schema, so that the system is ready for production scale and future features.

#### Acceptance Criteria

1. WHEN schema is reviewed THEN legacy/unused fields SHALL be identified and removed
2. WHEN JSON columns are analyzed THEN frequently accessed fields SHALL be extracted to indexed columns
3. WHEN table partitioning is evaluated THEN token_scores SHALL be partitioned by created_at (monthly)
4. WHEN relationships are reviewed THEN all foreign keys SHALL have proper indexes
5. IF redundant data exists THEN it SHALL be normalized or removed

### Requirement 9: Future-Ready Schema

**User Story:** As a product owner, I want the database ready for user authentication and multi-tenancy, so that external users can access the system.

#### Acceptance Criteria

1. WHEN users table is designed THEN it SHALL support email, password_hash, api_key, and role fields
2. WHEN API keys are designed THEN they SHALL have rate_limit, expires_at, and last_used_at fields
3. WHEN audit logging is designed THEN it SHALL track user actions with timestamp and IP
4. WHEN user_favorites is designed THEN users SHALL be able to save favorite tokens
5. IF multi-tenancy is needed THEN schema SHALL support organization/workspace isolation

### Requirement 10: Data Retention and Archival

**User Story:** As a system administrator, I want automated data retention policies, so that the database doesn't grow indefinitely.

#### Acceptance Criteria

1. WHEN retention policy is defined THEN archived token scores older than 30 days SHALL be moved to cold storage
2. WHEN partitions are created THEN old partitions SHALL be droppable without affecting active data
3. WHEN archival runs THEN it SHALL use pg_dump for historical data backup
4. WHEN cold storage is accessed THEN it SHALL be queryable but not indexed
5. IF disk space is low THEN automated cleanup SHALL trigger

### Requirement 11: Monitoring and Validation

**User Story:** As a developer, I want to validate the migration, so that I can ensure data integrity and performance.

#### Acceptance Criteria

1. WHEN migration completes THEN row counts SHALL match between SQLite and PostgreSQL
2. WHEN data is validated THEN sample queries SHALL return identical results
3. WHEN performance is tested THEN API response time SHALL be < 1 second
4. WHEN indexes are checked THEN all planned indexes SHALL exist and be used
5. WHEN application runs THEN no database errors SHALL occur in logs

### Requirement 12: Connection Pooling and Scalability

**User Story:** As a system administrator, I want efficient connection management, so that the system handles concurrent users.

#### Acceptance Criteria

1. WHEN connection pool is configured THEN it SHALL support min 5, max 20 connections
2. WHEN connection is idle THEN it SHALL be recycled after 300 seconds
3. WHEN pool is exhausted THEN new requests SHALL queue with timeout
4. WHEN monitoring is enabled THEN connection pool metrics SHALL be exposed
5. IF connection leaks occur THEN they SHALL be detected and logged
