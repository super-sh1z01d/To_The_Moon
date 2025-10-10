#!/usr/bin/env python3
"""
Validate data migration from SQLite to PostgreSQL.
"""

import sqlite3
import psycopg2
import sys
from pathlib import Path

# Configuration
SQLITE_DB = "/srv/tothemoon/dev.db"
DATABASE_URL = "postgresql://tothemoon:PASSWORD@localhost:5432/tothemoon_prod"

def connect_databases():
    """Connect to both databases."""
    print("🔌 Connecting to databases...")
    
    if not Path(SQLITE_DB).exists():
        print(f"❌ SQLite database not found: {SQLITE_DB}")
        sys.exit(1)
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    pg_conn = psycopg2.connect(DATABASE_URL)
    
    print("✓ Connected to both databases")
    return sqlite_conn, pg_conn

def validate_row_counts(sqlite_conn, pg_conn):
    """Compare row counts between databases."""
    print("\n📊 Validating row counts...")
    
    tables = ['tokens', 'token_scores', 'app_settings']
    all_match = True
    
    for table in tables:
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = sqlite_cursor.fetchone()[0]
        
        pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        pg_count = pg_cursor.fetchone()[0]
        
        match = "✓" if sqlite_count == pg_count else "❌"
        print(f"   {match} {table}: SQLite={sqlite_count:,}, PostgreSQL={pg_count:,}")
        
        if sqlite_count != pg_count:
            all_match = False
            print(f"      ⚠️  Difference: {abs(sqlite_count - pg_count):,} rows")
    
    return all_match

def validate_sample_data(sqlite_conn, pg_conn):
    """Compare sample data between databases."""
    print("\n🔍 Validating sample data...")
    
    # Check tokens
    print("   Checking tokens...")
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    sqlite_cursor.execute("SELECT id, mint_address, symbol, status FROM tokens ORDER BY id LIMIT 10")
    sqlite_tokens = sqlite_cursor.fetchall()
    
    pg_cursor.execute("SELECT id, mint_address, symbol, status FROM tokens ORDER BY id LIMIT 10")
    pg_tokens = pg_cursor.fetchall()
    
    tokens_match = sqlite_tokens == pg_tokens
    print(f"   {'✓' if tokens_match else '❌'} First 10 tokens match")
    
    # Check token_scores
    print("   Checking token_scores...")
    sqlite_cursor.execute("SELECT id, token_id, score, smoothed_score FROM token_scores ORDER BY id LIMIT 10")
    sqlite_scores = sqlite_cursor.fetchall()
    
    pg_cursor.execute("SELECT id, token_id, score, smoothed_score FROM token_scores ORDER BY id LIMIT 10")
    pg_scores = pg_cursor.fetchall()
    
    # Convert Decimal to float for comparison
    pg_scores_normalized = [
        (row[0], row[1], float(row[2]) if row[2] else None, float(row[3]) if row[3] else None)
        for row in pg_scores
    ]
    
    scores_match = sqlite_scores == pg_scores_normalized
    print(f"   {'✓' if scores_match else '❌'} First 10 scores match")
    
    return tokens_match and scores_match

def validate_indexes(pg_conn):
    """Check if all required indexes exist."""
    print("\n🔍 Validating indexes...")
    
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename IN ('tokens', 'token_scores')
        ORDER BY indexname
    """)
    
    indexes = [row[0] for row in pg_cursor.fetchall()]
    
    required_indexes = [
        'idx_tokens_liquidity',
        'idx_tokens_primary_dex',
        'idx_token_scores_smoothed',
        'idx_token_scores_token_created',
        'ix_token_scores_token_id'
    ]
    
    all_present = True
    for idx in required_indexes:
        present = idx in indexes
        print(f"   {'✓' if present else '❌'} {idx}")
        if not present:
            all_present = False
    
    print(f"\n   Total indexes found: {len(indexes)}")
    return all_present

def validate_extracted_fields(pg_conn):
    """Check if extracted fields are populated."""
    print("\n🔍 Validating extracted fields...")
    
    pg_cursor = pg_conn.cursor()
    
    # Check liquidity_usd
    pg_cursor.execute("SELECT COUNT(*) FROM tokens WHERE liquidity_usd IS NOT NULL")
    liquidity_count = pg_cursor.fetchone()[0]
    
    pg_cursor.execute("SELECT COUNT(*) FROM tokens WHERE status = 'active'")
    active_count = pg_cursor.fetchone()[0]
    
    print(f"   Tokens with liquidity_usd: {liquidity_count:,}")
    print(f"   Active tokens: {active_count:,}")
    
    # Check primary_dex
    pg_cursor.execute("SELECT COUNT(*) FROM tokens WHERE primary_dex IS NOT NULL")
    dex_count = pg_cursor.fetchone()[0]
    
    print(f"   Tokens with primary_dex: {dex_count:,}")
    
    return liquidity_count > 0 and dex_count > 0

def validate_query_performance(pg_conn):
    """Test query performance."""
    print("\n⚡ Testing query performance...")
    
    pg_cursor = pg_conn.cursor()
    
    # Test the main dashboard query
    import time
    start = time.time()
    
    pg_cursor.execute("""
        SELECT DISTINCT ON (t.id)
            t.id, t.mint_address, t.symbol, t.status,
            ts.score, ts.smoothed_score
        FROM tokens t
        LEFT JOIN token_scores ts ON ts.token_id = t.id
        WHERE t.status = 'active'
        ORDER BY t.id, ts.created_at DESC
        LIMIT 50
    """)
    
    results = pg_cursor.fetchall()
    elapsed = time.time() - start
    
    print(f"   Query returned {len(results)} rows in {elapsed:.3f} seconds")
    
    if elapsed < 1.0:
        print(f"   ✓ Performance target met (<1 second)")
        return True
    else:
        print(f"   ⚠️  Performance target not met (>1 second)")
        return False

def main():
    print("=" * 70)
    print("Migration Validation")
    print("=" * 70)
    
    # Connect to databases
    sqlite_conn, pg_conn = connect_databases()
    
    try:
        results = {}
        
        # Run validations
        results['row_counts'] = validate_row_counts(sqlite_conn, pg_conn)
        results['sample_data'] = validate_sample_data(sqlite_conn, pg_conn)
        results['indexes'] = validate_indexes(pg_conn)
        results['extracted_fields'] = validate_extracted_fields(pg_conn)
        results['performance'] = validate_query_performance(pg_conn)
        
        # Summary
        print("\n" + "=" * 70)
        print("Validation Summary")
        print("=" * 70)
        
        all_passed = all(results.values())
        
        for check, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check.replace('_', ' ').title()}")
        
        print("\n" + "=" * 70)
        if all_passed:
            print("✅ All validations passed!")
            print("=" * 70)
            return 0
        else:
            print("❌ Some validations failed!")
            print("=" * 70)
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    sys.exit(main())
