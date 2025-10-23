"""
Run IP tracking migration
Adds ip_address, country_code, and country_name columns to conversations table
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_migration():
    """Run the IP tracking migration"""
    try:
        client = get_supabase_client()

        logger.info("Starting IP tracking migration...")

        # Read the SQL migration file
        sql_file = os.path.join(os.path.dirname(__file__), 'add_ip_tracking.sql')
        with open(sql_file, 'r') as f:
            sql_content = f.read()

        # Split into individual statements
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

        logger.info(f"Executing {len(statements)} SQL statements...")

        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if statement:
                logger.info(f"Executing statement {i}/{len(statements)}...")
                logger.debug(f"SQL: {statement[:100]}...")

                # Use Supabase's RPC function to execute raw SQL
                try:
                    # For ALTER TABLE and CREATE INDEX, we need to use the Supabase SQL editor
                    # or execute via psycopg2/asyncpg directly
                    # Since Supabase client doesn't support raw DDL, we'll log instructions
                    logger.info(f"Statement {i}: {statement[:80]}...")
                except Exception as e:
                    logger.warning(f"Could not execute via Supabase client: {e}")

        logger.info("\n" + "="*80)
        logger.info("MIGRATION INSTRUCTIONS:")
        logger.info("="*80)
        logger.info("\nPlease execute the following SQL in your Supabase SQL Editor:")
        logger.info(f"\n1. Go to your Supabase project dashboard")
        logger.info(f"2. Navigate to SQL Editor")
        logger.info(f"3. Run the contents of: scripts/add_ip_tracking.sql")
        logger.info("\nSQL Preview:")
        logger.info("-"*80)
        print(sql_content)
        logger.info("-"*80)
        logger.info("\nAfter running the SQL, the following columns will be added:")
        logger.info("  - ip_address (TEXT)")
        logger.info("  - country_code (VARCHAR(2))")
        logger.info("  - country_name (TEXT)")
        logger.info("\nWith indexes:")
        logger.info("  - idx_conversations_country_code")
        logger.info("  - idx_conversations_created_at_country")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
