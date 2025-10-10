#!/usr/bin/env python3
"""
Export data from SQLite database to CSV files for PostgreSQL migration.
"""

import sqlite3
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# Configuration
SQLITE_DB = "/srv/tothemoon/dev.db"
EXPORT_DIR = "/srv/tothemoon/migration_data"
BATCH_SIZE = 10000

def setup_export_dir():
    """Create export directory if it doesn't exist."""
    export_path = Path(EXPORT_DIR)
    export_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ Export directory: {EXPORT_DIR}")
    return export_path

def export_tokens(conn, export_dir):
    """Export tokens table."""
    print("\n📦 Exporting tokens...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tokens")
    total = cursor.fetchone()[0]
    print(f"   Total tokens: {total}")
    
    cursor.execute("""
        SELECT id, mint_address, name, symbol, status, created_at, last_updated_at
        FROM tokens
        ORDER BY id
    """)
    
    output_file = export_dir / "tokens.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'mint_address', 'name', 'symbol', 'status', 'created_at', 'last_updated_at'])
        
        count = 0
        for row in cursor:
            writer.writerow(row)
            count += 1
            if count % 1000 == 0:
                print(f"   Exported {count}/{total} tokens...")
    
    print(f"✓ Exported {count} tokens to {output_file}")
    return count

def export_token_scores(conn, export_dir):
    """Export token_scores table in batches."""
    print("\n📦 Exporting token_scores...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM token_scores")
    total = cursor.fetchone()[0]
    print(f"   Total scores: {total:,}")
    
    # Export in batches
    batch_num = 0
    offset = 0
    total_exported = 0
    
    while True:
        cursor.execute(f"""
            SELECT id, token_id, score, smoothed_score, metrics, 
                   raw_components, smoothed_components, scoring_model,
                   spam_metrics, created_at
            FROM token_scores
            ORDER BY id
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        
        rows = cursor.fetchall()
        if not rows:
            break
        
        output_file = export_dir / f"token_scores_batch_{batch_num:04d}.csv"
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'token_id', 'score', 'smoothed_score', 'metrics',
                'raw_components', 'smoothed_components', 'scoring_model',
                'spam_metrics', 'created_at'
            ])
            
            for row in rows:
                # Convert dict columns to JSON strings
                row_list = list(row)
                for i in [4, 5, 6, 8]:  # metrics, raw_components, smoothed_components, spam_metrics
                    if row_list[i] is not None:
                        if isinstance(row_list[i], str):
                            # Already a string, verify it's valid JSON
                            try:
                                json.loads(row_list[i])
                            except:
                                row_list[i] = '{}'
                        else:
                            row_list[i] = json.dumps(row_list[i])
                    else:
                        row_list[i] = None
                
                writer.writerow(row_list)
            
            total_exported += len(rows)
            print(f"   Exported batch {batch_num}: {total_exported:,}/{total:,} scores...")
        
        batch_num += 1
        offset += BATCH_SIZE
    
    print(f"✓ Exported {total_exported:,} scores in {batch_num} batches")
    return total_exported

def export_app_settings(conn, export_dir):
    """Export app_settings table."""
    print("\n📦 Exporting app_settings...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM app_settings")
    total = cursor.fetchone()[0]
    print(f"   Total settings: {total}")
    
    cursor.execute("SELECT key, value FROM app_settings ORDER BY key")
    
    output_file = export_dir / "app_settings.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['key', 'value'])
        
        count = 0
        for row in cursor:
            writer.writerow(row)
            count += 1
    
    print(f"✓ Exported {count} settings to {output_file}")
    return count

def create_manifest(export_dir, stats):
    """Create manifest file with export metadata."""
    manifest = {
        'export_date': datetime.now().isoformat(),
        'sqlite_db': SQLITE_DB,
        'stats': stats,
        'batch_size': BATCH_SIZE
    }
    
    manifest_file = export_dir / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✓ Created manifest: {manifest_file}")

def main():
    print("=" * 70)
    print("SQLite to PostgreSQL Data Export")
    print("=" * 70)
    
    # Check if SQLite database exists
    if not Path(SQLITE_DB).exists():
        print(f"❌ Error: SQLite database not found: {SQLITE_DB}")
        sys.exit(1)
    
    # Setup export directory
    export_dir = setup_export_dir()
    
    # Connect to SQLite
    print(f"\n🔌 Connecting to SQLite: {SQLITE_DB}")
    conn = sqlite3.connect(SQLITE_DB)
    
    try:
        # Export tables
        stats = {}
        stats['tokens'] = export_tokens(conn, export_dir)
        stats['token_scores'] = export_token_scores(conn, export_dir)
        stats['app_settings'] = export_app_settings(conn, export_dir)
        
        # Create manifest
        create_manifest(export_dir, stats)
        
        print("\n" + "=" * 70)
        print("✅ Export completed successfully!")
        print("=" * 70)
        print(f"\nExported data:")
        print(f"  - Tokens: {stats['tokens']:,}")
        print(f"  - Token Scores: {stats['token_scores']:,}")
        print(f"  - App Settings: {stats['app_settings']}")
        print(f"\nLocation: {export_dir}")
        
    except Exception as e:
        print(f"\n❌ Error during export: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
