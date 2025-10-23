"""
Rate limiting middleware
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Create limiter instance
limiter = Limiter(key_func=get_remote_address)


def add_rate_limiter(app):
    """
    Add rate limiting to FastAPI app

    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
