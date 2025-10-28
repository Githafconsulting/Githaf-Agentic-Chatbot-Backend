"""
Row Level Security (RLS) Context Middleware
Sets company_id context for PostgreSQL RLS policies on each request
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.database import get_supabase_client
from app.core.security import decode_access_token
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RLSContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set PostgreSQL RLS context variables based on JWT

    Extracts company_id from JWT and sets app.current_company_id
    This enables Row Level Security policies to filter data by company
    """

    # Routes that don't require RLS context (public/auth routes)
    EXCLUDED_PATHS = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/chat/",  # Public chat endpoint
        "/api/v1/feedback/",  # Public feedback endpoint
    ]

    async def dispatch(self, request: Request, call_next):
        """
        Process request and set RLS context before calling endpoint

        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler

        Returns:
            Response from route handler
        """
        # Skip RLS for excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            # No token = no RLS context (will fail at protected routes)
            return await call_next(request)

        token = authorization.split(" ")[1]

        try:
            # Decode JWT
            payload = decode_access_token(token)
            if not payload:
                # Invalid token (will fail at get_current_user dependency)
                return await call_next(request)

            # Extract company_id from token
            company_id = payload.get("company_id")
            role = payload.get("role", "member")

            # Check if user is super admin (can see all companies)
            is_super_admin = role == "super_admin"

            # Set RLS context in PostgreSQL
            if company_id:
                client = get_supabase_client()
                try:
                    # Call the set_company_context function defined in migration SQL
                    client.rpc(
                        "set_company_context",
                        {
                            "p_company_id": company_id,
                            "p_is_super_admin": is_super_admin
                        }
                    ).execute()

                    logger.debug(
                        f"RLS context set: company_id={company_id}, "
                        f"is_super_admin={is_super_admin}, "
                        f"path={request.url.path}"
                    )
                except Exception as e:
                    logger.error(f"Failed to set RLS context: {e}")
                    # Don't fail the request, RLS will use default behavior
                    pass

        except Exception as e:
            logger.error(f"Error in RLS middleware: {e}")
            # Don't fail the request, let route handler deal with auth

        # Proceed to route handler
        response = await call_next(request)
        return response
