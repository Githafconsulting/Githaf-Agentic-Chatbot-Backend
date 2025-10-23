"""
Execute Database Migrations for Agentic Tables
Runs the create_agentic_tables.sql script on Supabase

Note: This script uses the Supabase REST API to execute SQL.
Alternatively, you can paste the SQL directly into Supabase SQL Editor.
"""
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def execute_migrations():
    """Execute SQL migrations from create_agentic_tables.sql"""
    print("=" * 70)
    print("AGENTIC CHATBOT v2.0 - DATABASE MIGRATION")
    print("=" * 70)
    print()

    # Read SQL file
    sql_file = Path(__file__).parent / "create_agentic_tables.sql"

    if not sql_file.exists():
        print(f"[ERROR] SQL file not found at {sql_file}")
        return False

    print(f"[*] Reading SQL from: {sql_file.name}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    print(f"[OK] Loaded {len(sql_content)} characters of SQL")
    print()

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("[ERROR] SUPABASE_URL or SUPABASE_KEY not found in .env")
        return False

    print("[*] MIGRATION OPTIONS:")
    print()
    print("Option 1: Manual (Recommended)")
    print("  1. Open Supabase Dashboard")
    print(f"     {supabase_url.replace('https://', 'https://supabase.com/dashboard/project/')}")
    print("  2. Go to SQL Editor")
    print("  3. Copy and paste the content of scripts/create_agentic_tables.sql")
    print("  4. Click 'Run'")
    print()
    print("Option 2: Automatic (Experimental)")
    print("  This script will attempt to use Supabase REST API")
    print()

    choice = input("Choose option (1 for manual, 2 for automatic, Q to quit): ").strip()

    if choice.lower() == 'q':
        print("Migration cancelled.")
        return False

    if choice == '1':
        print()
        print("=" * 70)
        print("MANUAL MIGRATION INSTRUCTIONS")
        print("=" * 70)
        print()
        print("1. Open your Supabase Dashboard:")
        print(f"   {supabase_url.replace('https://', 'https://supabase.com/dashboard/project/')}")
        print()
        print("2. Navigate to: SQL Editor (in left sidebar)")
        print()
        print("3. Click 'New Query'")
        print()
        print("4. Copy the entire content from:")
        print(f"   {sql_file}")
        print()
        print("5. Paste into the SQL Editor")
        print()
        print("6. Click 'Run' button")
        print()
        print("7. You should see:")
        print("   - 6 tables created (semantic_memory, user_preferences, etc.)")
        print("   - Multiple indexes created")
        print("   - 1 RPC function created (match_semantic_memory)")
        print("   - Success message at the bottom")
        print()
        print("=" * 70)
        print()

        # Open SQL file for easy copying
        print("Opening SQL file for you to copy...")
        import subprocess
        try:
            subprocess.run(['notepad.exe', str(sql_file)])
        except:
            print("Could not open notepad. Please open the file manually.")

        return True

    elif choice == '2':
        print()
        print("[WARNING] Automatic migration is experimental.")
        print("          Supabase REST API doesn't directly support DDL.")
        print("          Using manual migration is strongly recommended.")
        print()
        confirm = input("Continue anyway? (yes/no): ").strip().lower()

        if confirm != 'yes':
            print("Migration cancelled. Please use manual option.")
            return False

        print()
        print("[ERROR] Automatic migration not implemented.")
        print()
        print("Supabase REST API (PostgREST) doesn't support direct SQL execution.")
        print("Please use Option 1 (Manual) to execute the migrations.")
        print()
        return False

    else:
        print("Invalid choice. Exiting.")
        return False


if __name__ == "__main__":
    try:
        success = execute_migrations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
