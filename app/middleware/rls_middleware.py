"""
Row Level Security (RLS) Middleware

This middleware extracts the company_id from JWT tokens and sets the
PostgreSQL session context for Row Level Security policies.

IMPORTANT: This middleware must run on EVERY authenticated request to
ensure proper multi-tenant data isolation.
"""
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from app.core.security import decode_access_token
from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RLSMiddleware(BaseHTTPMiddleware):
    """
    Row Level Security Middleware

    Extracts company_id and role from JWT token and sets PostgreSQL
    session context for RLS policies.

    How it works:
    1. Checks if request has Authorization header
    2. Decodes JWT token to get user_id, company_id, and role
    3. Calls set_company_context() Supabase RPC function
    4. Sets session variables: app.current_company_id, app.is_super_admin
    5. All subsequent queries respect RLS policies

    Example JWT payload:
    {
        "sub": "user_id",
        "company_id": "00000000-0000-0000-0000-000000000001",
        "role": "owner",
        "exp": 1696867200
    }
    """

    # Paths that don't require RLS context (public endpoints)
    EXCLUDED_PATHS = [
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/chat/",  # Public chat endpoint (no auth required)
        "/api/v1/feedback/",  # Public feedback endpoint
    ]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process each request and set RLS context if authenticated

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response: HTTP response
        """
        # Skip RLS context for excluded paths
        if self._is_excluded_path(request.url.path):
            logger.debug(f"Skipping RLS for public path: {request.url.path}")
            return await call_next(request)

        # Extract JWT token from Authorization header
        token = self._extract_token(request)

        if token:
            # Decode token and set RLS context
            try:
                await self._set_rls_context(token)
                logger.debug(f"RLS context set for path: {request.url.path}")
            except HTTPException as e:
                # Return 401 if token is invalid
                return Response(
                    content=str(e.detail),
                    status_code=e.status_code,
                    media_type="application/json"
                )
            except Exception as e:
                logger.error(f"RLS middleware error: {e}")
                # Continue without RLS context (will fail if protected route)
        else:
            logger.debug(f"No token found for path: {request.url.path}")

        # Continue to next middleware/route
        response = await call_next(request)
        return response

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path should skip RLS context

        Args:
            path: Request path

        Returns:
            bool: True if path is excluded
        """
        # Exact match or prefix match
        for excluded in self.EXCLUDED_PATHS:
            if path == excluded or path.startswith(excluded):
                return True
        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header

        Args:
            request: FastAPI request object

        Returns:
            str or None: JWT token if present
        """
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        # Expected format: "Bearer <token>"
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    async def _set_rls_context(self, token: str):
        """
        Decode JWT and set PostgreSQL RLS context

        Args:
            token: JWT token string

        Raises:
            HTTPException: If token is invalid or user not found
        """
        # Decode token
        payload = decode_access_token(token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Get Supabase client
        db = get_supabase_client()

        # Fetch user to get company_id and role
        try:
            response = db.table("users").select("id, company_id, role").eq("id", user_id).single().execute()
            user = response.data

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            company_id = user.get("company_id")
            role = user.get("role", "member")

            # Determine if user is super admin (bypasses RLS)
            is_super_admin = (role == "super_admin")

            # Set PostgreSQL session context via RPC function
            if company_id:
                try:
                    db.rpc('set_company_context', {
                        'p_company_id': company_id,
                        'p_is_super_admin': is_super_admin
                    }).execute()

                    logger.info(
                        f"RLS context set - User: {user_id}, "
                        f"Company: {company_id}, "
                        f"Role: {role}, "
                        f"SuperAdmin: {is_super_admin}"
                    )
                except Exception as e:
                    logger.error(f"Failed to set RLS context: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to set security context"
                    )
            else:
                # User has no company (should not happen in production)
                logger.warning(f"User {user_id} has no company_id")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not associated with a company"
                )

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error fetching user for RLS: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )


def add_rls_middleware(app):
    """
    Add RLS middleware to FastAPI application

    IMPORTANT: This should be added BEFORE route handlers but AFTER
    CORS middleware to ensure proper execution order.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(RLSMiddleware)
    logger.info("RLS middleware registered")
