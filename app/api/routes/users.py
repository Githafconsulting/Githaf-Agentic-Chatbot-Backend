"""
User management API endpoints
"""
from app.core.dependencies import get_current_user, get_current_admin_user
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import UserCreate, User
from app.core.database import get_supabase_client
from app.core.security import get_password_hash
from app.utils.logger import get_logger
from datetime import datetime
from typing import List

router = APIRouter()
logger = get_logger(__name__)

# @router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin_user)])
async def create_user(user_data: UserCreate):
    """
    Create a new user

    **Public endpoint** - can be used to register users

    Request body:
    - email: Valid email address
    - password: Minimum 8 characters
    - full_name: Optional full name
    - is_admin: Optional admin flag (default: false)
    """
    try:
        client = get_supabase_client()

        # Check if user already exists
        existing = client.table("users").select("*").eq("email", user_data.email).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {user_data.email} already exists"
            )

        # Hash password
        password_hash = get_password_hash(user_data.password)

        # Create user record
        data = {
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name,
            "is_active": True,
            "is_admin": user_data.is_admin,
            "created_at": datetime.utcnow().isoformat()
        }

        response = client.table("users").insert(data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        user = response.data[0]

        logger.info(f"User created: {user['email']}")

        return {
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "is_admin": user["is_admin"],
                "created_at": user["created_at"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
        


# @router.get("/", response_model=List[dict])
@router.get("/", response_model=List[dict], dependencies=[Depends(get_current_admin_user)])
async def list_users():
    """
    List all users (without password hashes)

    **Note**: This should be protected in production
    """
    try:
        client = get_supabase_client()

        response = client.table("users").select(
            "id, email, full_name, is_active, is_admin, created_at"
        ).execute()

        return response.data if response.data else []

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


# @router.delete("/{user_id}")
@router.delete("/{user_id}", dependencies=[Depends(get_current_admin_user)])
async def delete_user(user_id: str):
    """
    Delete a user by ID

    **Note**: This should be protected in production
    """
    try:
        client = get_supabase_client()

        response = client.table("users").delete().eq("id", user_id).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User deleted: {user_id}")

        return {
            "success": True,
            "message": "User deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
