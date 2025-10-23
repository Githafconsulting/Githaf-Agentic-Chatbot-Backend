"""
Apply Soft Delete System Migration
Executes SQL migration to add soft delete functionality
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_supabase_client

def apply_migration():
    """Execute the soft delete migration SQL"""
    print("=" * 70)
    print("APPLYING SOFT DELETE SYSTEM MIGRATION")
    print("=" * 70)
    print()

    # Read SQL file
    sql_file = Path(__file__).parent / "add_soft_delete_system.sql"
    if not sql_file.exists():
        print(f"[X] ERROR: SQL file not found: {sql_file}")
        return False

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split into individual statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

    print(f"[INFO] Found {len(statements)} SQL statements to execute")
    print()

    client = get_supabase_client()
    success_count = 0
    error_count = 0

    for i, statement in enumerate(statements, 1):
        # Skip empty statements and comments
        if not statement or statement.startswith('--'):
            continue

        # Get statement type for logging
        stmt_type = statement.split()[0].upper() if statement else 'UNKNOWN'

        try:
            # Execute via Supabase RPC if it's a SELECT, otherwise use direct execution
            # Note: Supabase client doesn't directly support DDL, so we'll use the REST API
            print(f"[{i}/{len(statements)}] Executing {stmt_type}... ", end='', flush=True)

            # For Supabase, we need to use the SQL editor or psycopg2
            # Since we can't execute DDL via Supabase Python client, we'll show instructions instead
            print("SKIPPED (requires manual execution via Supabase SQL Editor)")

        except Exception as e:
            error_count += 1
            print(f"[X] FAILED: {str(e)[:100]}")

    print()
    print("=" * 70)
    print(f"MIGRATION STATUS:")
    print(f"  Total Statements: {len(statements)}")
    print(f"  Note: DDL statements must be executed via Supabase SQL Editor")
    print("=" * 70)
    print()
    print("[INFO] NEXT STEPS:")
    print("1. Go to Supabase Dashboard: https://app.supabase.com")
    print("2. Select your project")
    print("3. Navigate to SQL Editor (left sidebar)")
    print("4. Click 'New query'")
    print("5. Copy the contents of: add_soft_delete_system.sql")
    print("6. Paste into SQL Editor")
    print("7. Click 'Run' to execute the migration")
    print()
    print("=" * 70)

    return True

if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as e:
        print(f"\n[X] ERROR: {e}\n")
        sys.exit(1)
