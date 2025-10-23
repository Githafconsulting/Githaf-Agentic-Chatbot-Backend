"""
Main FastAPI application
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1 import api_router
from app.middleware.cors import add_cors_middleware
from app.middleware.error_handler import add_exception_handlers
from app.middleware.rate_limiter import add_rate_limiter
from app.core.database import test_connection
from app.utils.logger import get_logger
from app.services.scheduler import start_scheduler, stop_scheduler

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Agentic RAG-based customer service chatbot API for Githaf Consulting (Phase 3: Self-Improvement)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
add_cors_middleware(app)
add_rate_limiter(app)
add_exception_handlers(app)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns API status and database connection status
    """
    try:
        db_connected = await test_connection()

        return {
            "status": "healthy",
            "version": "2.0.0",
            "database": "connected" if db_connected else "disconnected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Githaf Consulting Chatbot API - Agentic v2.0",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Phase 1: Observation Layer (Validation & Retry)",
            "Phase 2: Planning Layer (Multi-Step Decomposition)",
            "Phase 3: Self-Improvement Loop (Learning & A/B Testing)"
        ]
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Runs on application startup
    """
    logger.info("=" * 50)
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    logger.info("=" * 50)

    # Test database connection
    try:
        db_connected = await test_connection()
        if db_connected:
            # logger.info("✓ Database connection successful")
            logger.info("[OK] Database connection successful")
        else:
            # logger.warning("✗ Database connection failed")
            logger.warning("[FAIL] Database connection failed")
    except Exception as e:
        # logger.error(f"✗ Database connection error: {e}")
        logger.error(f"[ERROR] Database connection error: {e}")

    # Initialize semantic intent matcher (precompute embeddings)
    try:
        from app.services.semantic_intent_matcher import initialize_intent_embeddings
        await initialize_intent_embeddings()
        logger.info("[OK] Semantic intent matcher initialized")
    except Exception as e:
        logger.warning(f"[WARN] Semantic matcher initialization failed: {e}")

    # Start background scheduler (Phase 3: Self-Improvement Loop)
    try:
        start_scheduler()
        logger.info("[OK] Background scheduler started")
    except Exception as e:
        logger.error(f"[ERROR] Scheduler startup failed: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs on application shutdown
    """
    logger.info("Shutting down application...")

    # Stop background scheduler (Phase 3: Self-Improvement Loop)
    try:
        stop_scheduler()
        logger.info("[OK] Background scheduler stopped")
    except Exception as e:
        logger.error(f"[ERROR] Scheduler shutdown failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
