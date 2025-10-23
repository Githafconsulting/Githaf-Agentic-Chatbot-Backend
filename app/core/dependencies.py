"""
FastAPI dependency injection functions
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.core.database import get_supabase_client
from supabase import Client


# Security scheme
security = HTTPBearer()


async def get_db() -> Client:
    """
    Dependency to get database client

    Returns:
        Client: Supabase client instance
    """
    return get_supabase_client()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Client = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP bearer credentials
        db: Database client

    Returns:
        dict: User data

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    try:
        response = db.table("users").select("*").eq("id", user_id).single().execute()
        user = response.data

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get user if authenticated, otherwise None (for optional authentication)

    Args:
        credentials: Optional HTTP bearer credentials

    Returns:
        dict or None: User data if authenticated
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    return payload

async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Verify that current user is an admin"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user