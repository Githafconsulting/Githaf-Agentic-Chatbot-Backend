"""
Supabase database client configuration
"""
from supabase import create_client, Client
from app.core.config import settings


# Supabase client singleton
_supabase_client: Client = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance

    Returns:
        Client: Supabase client instance
    """
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY
        )

    return _supabase_client


async def test_connection() -> bool:
    """
    Test database connection

    Returns:
        bool: True if connection successful
    """
    try:
        client = get_supabase_client()
        # Try a simple query
        response = client.table("documents").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
