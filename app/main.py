from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from .config import settings
from .api.api_v1.api import api_router
from .core.init_admin import create_initial_admin
from .core.health import HealthChecker
from .middleware.logging import LoggingMiddleware
from .middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware
)
from .core.exceptions import (
    http_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    pydantic_validation_exception_handler,
    general_exception_handler,
    business_logic_exception_handler,
    BusinessLogicError
)
from .tasks.scheduler import start_scheduler
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Application startup initiated")
    create_initial_admin()

    # Start background scheduler for periodic tasks
    scheduler = None
    try:
        scheduler = start_scheduler()
        logger.info("✅ Background scheduler started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start background scheduler: {e}")
        # Continue without scheduler (non-critical)

    logger.info("✅ Application startup complete")

    yield

    # Shutdown
    logger.info("🔄 Application shutdown initiated")
    if scheduler:
        try:
            scheduler.shutdown()
            logger.info("✅ Background scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}")

    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="GānCuju™© Education Center - Comprehensive Football Education Platform featuring 8-Level GānCuju™© Player System (4000-year Chinese tradition), 8-Level LFA Coach Training, Internship Programs, and Gamification with Parallel Specialization Tracks",
    version="2.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add middleware conditionally based on environment
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

if settings.ENABLE_REQUEST_SIZE_LIMIT:
    app.add_middleware(RequestSizeLimitMiddleware, max_size_mb=10)

if settings.ENABLE_RATE_LIMITING:
    app.add_middleware(
        RateLimitMiddleware, 
        calls=settings.RATE_LIMIT_CALLS, 
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
    )

if settings.ENABLE_STRUCTURED_LOGGING:
    app.add_middleware(LoggingMiddleware)  # Should be after rate limiting for accurate logs

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
app.add_exception_handler(BusinessLogicError, business_logic_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Practice Booking System API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with system metrics"""
    return await HealthChecker.get_comprehensive_health()


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    db_health = await HealthChecker.get_database_health()
    return {
        "status": "ready" if db_health["status"] != "unhealthy" else "not_ready",
        "database": db_health["status"]
    }


@app.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe"""
    return {"status": "alive"}