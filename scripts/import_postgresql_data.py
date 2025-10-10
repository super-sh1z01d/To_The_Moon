#!/usr/bin/env python3
"""
Import data from CSV files into PostgreSQL database.
"""

import psycopg2
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# Configuration
IMPORT_DIR = "/srv/tothemoon/migration_data"
DATABASE_URL = "postgresql://tothemoon:PASSWORD@localhost:5432/tothemoon_prod"

def connect_postgresql():
    """Connect to PostgreSQL database."""
    print(f"🔌 Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        print("✓ Connected to PostgreSQL")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)

def import_tokens(conn, import_dir):
    """Import tokens from CSV."""
    print("\n📥 Importing tokens...")
    cursor = conn.cursor()
    
    input_file = import_dir / "tokens.csv"
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        return 0
    
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            cursor.execute("""
                INSERT INTO tokens (id, mint_address, name, symbol, status, created_at, last_updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (mint_address) DO NOTHING
            """, (
                row['id'],
                row['mint_address'],
                row['name'] if row['name'] else None,
                row['symbol'] if row['symbol'] else None,
                row['status'],
                row['created_at'],
                row['last_updated_at'] if row['last_updated_at'] else None
            ))
            count += 1
            
            if count % 1000 == 0:
                conn.commit()
                print(f"   Imported {count} tokens...")
        
        conn.commit()
    
    # Update sequence
    cursor.execute("SELECT setval('tokens_id_seq', (SELECT MAX(id) FROM tokens))")
    conn.commit()
    
    print(f"✓ Imported {count} tokens")
    return count

def import_token_scores(conn, import_dir):
    """Import token_scores from CSV batches."""
    print("\n📥 Importing token_scores...")
    cursor = conn.cursor()
    
    # Find all batch files
    batch_files = sorted(import_dir.glob("token_scores_batch_*.csv"))
    if not batch_files:
        print("❌ No token_scores batch files found")
        return 0
    
    print(f"   Found {len(batch_files)} batch files")
    
    total_count = 0
    for batch_file in batch_files:
        print(f"   Processing {batch_file.name}...")
        
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            batch_count = 0
            
            for row in reader:
                # Parse JSON fields
                metrics = json.loads(row['metrics']) if row['metrics'] else None
                raw_components = json.loads(row['raw_components']) if row['raw_components'] else None
                smoothed_components = json.loads(row['smoothed_components']) if row['smoothed_components'] else None
                spam_metrics = json.loads(row['spam_metrics']) if row['spam_metrics'] else None
                
                cursor.execute("""
                    INSERT INTO token_scores 
                    (id, token_id, score, smoothed_score, metrics, raw_components, 
                     smoothed_components, scoring_model, spam_metrics, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row['id'],
                    row['token_id'],
                    row['score'] if row['score'] else None,
                    row['smoothed_score'] if row['smoothed_score'] else None,
                    json.dumps(metrics) if metrics else None,
                    json.dumps(raw_components) if raw_components else None,
                    json.dumps(smoothed_components) if smoothed_components else None,
                    row['scoring_model'],
                    json.dumps(spam_metrics) if spam_metrics else None,
                    row['created_at']
                ))
                batch_count += 1
                
                if batch_count % 1000 == 0:
                    conn.commit()
            
            conn.commit()
            total_count += batch_count
            print(f"   ✓ Imported {batch_count} scores from {batch_file.name}")
    
    # Update sequence
    cursor.execute("SELECT setval('token_scores_id_seq', (SELECT MAX(id) FROM token_scores))")
    conn.commit()
    
    print(f"✓ Imported {total_count:,} token_scores")
    return total_count

def import_app_settings(conn, import_dir):
    """Import app_settings from CSV."""
    print("\n📥 Importing app_settings...")
    cursor = conn.cursor()
    
    input_file = import_dir / "app_settings.csv"
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        return 0
    
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            cursor.execute("""
                INSERT INTO app_settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (row['key'], row['value']))
            count += 1
        
        conn.commit()
    
    print(f"✓ Imported {count} settings")
    return count

def update_extracted_fields(conn):
    """Update extracted fields in tokens table from latest metrics."""
    print("\n🔄 Updating extracted fields in tokens...")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tokens t
        SET 
            liquidity_usd = (
                SELECT (ts.metrics->>'L_tot')::numeric
                FROM token_scores ts
                WHERE ts.token_id = t.id
                ORDER BY ts.created_at DESC
                LIMIT 1
            ),
            primary_dex = (
                SELECT ts.metrics->>'primary_dex'
                FROM token_scores ts
                WHERE ts.token_id = t.id
                ORDER BY ts.created_at DESC
                LIMIT 1
            )
        WHERE EXISTS (
            SELECT 1 FROM token_scores ts WHERE ts.token_id = t.id
        )
    """)
    
    updated = cursor.rowcount
    conn.commit()
    print(f"✓ Updated {updated} tokens with extracted fields")
    return updated

def main():
    print("=" * 70)
    print("PostgreSQL Data Import")
    print("=" * 70)
    
    # Check import directory
    import_dir = Path(IMPORT_DIR)
    if not import_dir.exists():
        print(f"❌ Import directory not found: {IMPORT_DIR}")
        sys.exit(1)
    
    # Check manifest
    manifest_file = import_dir / "manifest.json"
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
            print(f"\n📋 Import manifest:")
            print(f"   Export date: {manifest['export_date']}")
            print(f"   Tokens: {manifest['stats']['tokens']:,}")
            print(f"   Token Scores: {manifest['stats']['token_scores']:,}")
            print(f"   App Settings: {manifest['stats']['app_settings']}")
    
    # Connect to PostgreSQL
    conn = connect_postgresql()
    
    try:
        # Import tables
        stats = {}
        stats['tokens'] = import_tokens(conn, import_dir)
        stats['token_scores'] = import_token_scores(conn, import_dir)
        stats['app_settings'] = import_app_settings(conn, import_dir)
        stats['updated_fields'] = update_extracted_fields(conn)
        
        print("\n" + "=" * 70)
        print("✅ Import completed successfully!")
        print("=" * 70)
        print(f"\nImported data:")
        print(f"  - Tokens: {stats['tokens']:,}")
        print(f"  - Token Scores: {stats['token_scores']:,}")
        print(f"  - App Settings: {stats['app_settings']}")
        print(f"  - Updated extracted fields: {stats['updated_fields']:,}")
        
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
