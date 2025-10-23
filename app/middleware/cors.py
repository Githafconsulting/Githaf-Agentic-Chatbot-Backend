"""
CORS middleware configuration
"""
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


def add_cors_middleware(app):
    """
    Add CORS middleware to FastAPI app

    Uses allow_origin_regex to allow all origins while maintaining credentials support.
    This is necessary for:
    1. Admin panel authentication (needs credentials)
    2. Widget embedding on third-party sites (needs flexible origins)

    Args:
        app: FastAPI application instance
    """
    # Check if we're using "*" wildcard (can't use with credentials)
    if settings.ALLOWED_ORIGINS == ["*"]:
        # Use regex pattern instead to allow all origins WITH credentials
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r".*",  # Matches any origin
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
    else:
        # Use specific origins list
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
