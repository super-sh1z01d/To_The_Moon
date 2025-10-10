# PostgreSQL Migration Implementation Plan

- [-] 1. Preparation and Environment Setup
- [x] 1.1 Install PostgreSQL 14+ on server
  - Install postgresql, postgresql-contrib packages
  - Start and enable PostgreSQL service
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 1.2 Create database and user
  - Create database tothemoon_prod
  - Create user with password
  - Grant all privileges
  - _Requirements: 1.1, 1.2_

- [ ] 1.3 Configure PostgreSQL for production
  - Update postgresql.conf (shared_buffers, work_mem, etc.)
  - Configure pg_hba.conf for local access
  - Set up connection limits
  - _Requirements: 1.1, 12.1_

- [x] 1.4 Install Python PostgreSQL dependencies
  - Add psycopg2-binary to requirements.txt
  - Install on server
  - _Requirements: 5.1_

- [ ] 1.5 Backup current SQLite database
  - Create /srv/tothemoon/backups/ directory
  - Copy dev.db to backup with timestamp
  - Verify backup integrity
  - _Requirements: 7.1, 7.4_

- [x] 2. Schema Migration and Optimization
- [x] 2.1 Create Alembic migration for PostgreSQL schema
  - Update models.py to use JSONB instead of JSON
  - Add extracted fields (liquidity_usd, primary_dex) to tokens table
  - Create migration script
  - _Requirements: 2.2, 2.3, 8.2_

- [x] 2.2 Add optimized indexes
  - Create composite index on (token_id, created_at DESC)
  - Create index on tokens.status
  - Create index on smoothed_score
  - Create GIN indexes on JSONB columns
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 2.3 Implement table partitioning for token_scores
  - Create partitioned table structure
  - Create current and next month partitions
  - Add indexes to each partition
  - _Requirements: 8.3, 10.2_

- [x] 2.4 Create materialized view for latest scores
  - Create latest_token_scores materialized view
  - Add indexes to materialized view
  - _Requirements: 6.1, 4.5_

- [x] 3. Data Migration Scripts
- [x] 3.1 Create data export script from SQLite
  - Export tokens table to CSV
  - Export token_scores in batches to CSV
  - Export app_settings to CSV
  - Verify export completeness
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3.2 Create data import script for PostgreSQL
  - Import tokens using COPY command
  - Import token_scores in batches (10K rows)
  - Import app_settings
  - Handle JSONB conversion
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3.3 Create data validation script
  - Compare row counts between SQLite and PostgreSQL
  - Verify sample queries return identical results
  - Check data integrity with checksums
  - _Requirements: 3.4, 11.1, 11.2_

- [ ] 4. Query Optimization
- [ ] 4.1 Update TokensRepository to use DISTINCT ON
  - Replace GROUP BY + JOIN with DISTINCT ON
  - Update list_non_archived_with_latest_scores method
  - Add query hints for index usage
  - _Requirements: 6.1, 6.5_

- [ ] 4.2 Add materialized view refresh task
  - Create background task to refresh every 30 seconds
  - Add to scheduler
  - Handle concurrent refresh
  - _Requirements: 6.1_

- [ ] 4.3 Optimize JSONB queries
  - Use JSONB operators (->, ->>) instead of JSON
  - Add GIN indexes where needed
  - Update queries to leverage indexes
  - _Requirements: 6.4, 4.4_

- [ ] 5. Connection Pooling Configuration
- [ ] 5.1 Update database configuration
  - Configure SQLAlchemy engine with QueuePool
  - Set pool_size=5, max_overflow=15
  - Add pool_recycle=300, pool_pre_ping=True
  - _Requirements: 12.1, 12.2, 12.3_

- [ ] 5.2 Add connection pool monitoring
  - Expose pool metrics via /health endpoint
  - Log pool exhaustion events
  - Add alerts for connection leaks
  - _Requirements: 12.4, 12.5_

- [ ] 6. Application Configuration Updates
- [ ] 6.1 Update environment configuration
  - Add DATABASE_URL for PostgreSQL
  - Keep SQLITE_DATABASE_URL as fallback
  - Update .env.example
  - _Requirements: 5.1, 5.2_

- [ ] 6.2 Update database initialization
  - Add PostgreSQL-specific initialization
  - Handle connection errors gracefully
  - Add retry logic with exponential backoff
  - _Requirements: 5.2, 5.5_

- [ ] 6.3 Update Alembic configuration
  - Point to PostgreSQL database
  - Test migrations on clean database
  - _Requirements: 2.1_

- [ ] 7. Migration Execution
- [ ] 7.1 Pre-migration checklist
  - Verify disk space (need 3x current DB size)
  - Stop scheduler to prevent new writes
  - Create final SQLite backup
  - _Requirements: 7.5, 3.5_

- [ ] 7.2 Run schema migration
  - Apply Alembic migrations to PostgreSQL
  - Verify all tables and indexes created
  - Check partition structure
  - _Requirements: 2.1, 2.2, 2.5_

- [ ] 7.3 Run data migration
  - Execute export script
  - Execute import script
  - Run validation script
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 7.4 Application cutover
  - Update DATABASE_URL in production .env
  - Restart application services
  - Monitor logs for errors
  - _Requirements: 5.1, 5.5_

- [ ] 7.5 Post-migration validation
  - Run performance tests
  - Verify API response times < 1 second
  - Check all endpoints return correct data
  - _Requirements: 11.3, 11.4, 11.5_

- [ ] 8. Performance Testing and Validation
- [ ] 8.1 Benchmark critical queries
  - Test /tokens endpoint with various filters
  - Measure query execution time
  - Verify index usage with EXPLAIN ANALYZE
  - _Requirements: 4.5, 11.3_

- [ ] 8.2 Load testing
  - Simulate 50 concurrent users
  - Test connection pool under load
  - Verify no connection leaks
  - _Requirements: 12.3, 12.5_

- [ ] 8.3 Monitor database performance
  - Enable pg_stat_statements
  - Track slow queries
  - Monitor table/index sizes
  - _Requirements: 11.4_

- [ ] 9. Backup and Monitoring Setup
- [ ] 9.1 Configure automated backups
  - Set up daily pg_dump backups
  - Rotate backups (keep 7 days)
  - Test restore procedure
  - _Requirements: 7.2, 7.3_

- [ ] 9.2 Set up partition management
  - Create script to auto-create next month's partition
  - Add to cron (run monthly)
  - Test partition creation
  - _Requirements: 10.2_

- [ ] 9.3 Configure monitoring alerts
  - Alert on connection pool exhaustion
  - Alert on slow queries (>5 seconds)
  - Alert on disk space low
  - _Requirements: 12.4, 10.5_

- [ ] 10. Documentation and Rollback Plan
- [ ] 10.1 Document migration process
  - Create migration runbook
  - Document rollback procedure
  - Update deployment documentation
  - _Requirements: 7.3_

- [ ] 10.2 Test rollback procedure
  - Verify application can switch back to SQLite
  - Test with backup database
  - Document any issues
  - _Requirements: 7.3_

- [ ] 10.3 Update README and architecture docs
  - Update database section
  - Add PostgreSQL setup instructions
  - Document new environment variables
  - _Requirements: 5.1_
