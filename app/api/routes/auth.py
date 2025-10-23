"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.models.user import Token
from app.core.database import get_supabase_client
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Admin login endpoint

    Returns JWT access token
    """
    try:
        client = get_supabase_client()

        # Find user by email (username field contains email)
        response = client.table("users").select("*").eq("email", form_data.username).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        user = response.data[0]

        # Convert any bytes fields to strings (Supabase may return bytes)
        for key, value in user.items():
            if isinstance(value, bytes):
                user[key] = value.decode('utf-8')

        # Verify password
        if not verify_password(form_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        # Check if user is active
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["id"])},
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in: {user['email']}")

        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
