"""
CivicSwipe Backend API
Main application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import uuid

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, get_logger
from app.core.monitoring import init_sentry, capture_exception, metrics, track_api_request

# Set up structured logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting CivicSwipe API...")

    # Initialize Sentry for error tracking
    init_sentry()

    # Initialize database connection
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis cache (graceful — app works without it)
    from app.core.cache import get_redis, close_redis
    await get_redis()

    # Initialize shared httpx connection pools on service singletons
    from app.services.congress_api import congress_api_service
    from app.services.geocoding import geocoding_service
    await congress_api_service.startup()
    await geocoding_service.startup()

    yield

    # Cleanup
    await congress_api_service.shutdown()
    await geocoding_service.shutdown()
    await close_redis()
    logger.info("Shutting down CivicSwipe API...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for CivicSwipe - Legislative tracking and voting app",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware (simple per-IP, 60 req/min)
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Per-IP rate limiting via Redis. Passes through if Redis is down."""
    from app.core.cache import get_redis

    client_ip = request.client.host if request.client else "unknown"
    r = await get_redis()
    if r is not None:
        key = f"rl:{client_ip}"
        try:
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 60)
            if count > 120:  # 120 requests per minute
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        except Exception:
            pass  # Fail open — don't block requests if Redis errors

    return await call_next(request)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Add request ID to state
    request.state.request_id = request_id

    response = await call_next(request)

    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000

    # Track metrics
    track_api_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    # Log request
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Global exception: {exc}", exc_info=True, extra={"request_id": request_id})

    # Send to Sentry
    capture_exception(exc, extra={"request_id": request_id, "path": str(request.url)})

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred",
                "request_id": request_id,
                "details": {}
            }
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


# Metrics endpoint
@app.get("/api/v1/metrics", tags=["Monitoring"])
async def get_metrics():
    """Get application metrics"""
    return metrics.get_all()


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
