"""
RepCheck Backend API
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
    logger.info("Starting RepCheck API...")

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
    logger.info("Shutting down RepCheck API...")


# Disable OpenAPI docs in production to reduce attack surface
_is_production = settings.ENVIRONMENT == "production"

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for RepCheck - Legislative tracking and voting app",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    lifespan=lifespan
)

# Configure CORS — restrict to actual HTTP methods and headers used by the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Admin-Key"],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)


# Rate limiting middleware — global + stricter limits for sensitive endpoints
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Per-IP rate limiting via Redis. Passes through if Redis is down."""
    from app.core.cache import get_redis

    client_ip = request.client.host if request.client else "unknown"
    r = await get_redis()
    if r is not None:
        try:
            path = request.url.path

            # Stricter rate limits for auth endpoints (brute-force protection)
            if path.endswith("/auth/login") or path.endswith("/auth/signup"):
                auth_key = f"rl:auth:{client_ip}"
                auth_count = await r.incr(auth_key)
                if auth_count == 1:
                    await r.expire(auth_key, 300)  # 5 minute window
                if auth_count > 10:  # 10 auth attempts per 5 minutes
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many authentication attempts. Try again in a few minutes."}
                    )

            # Global rate limit
            key = f"rl:{client_ip}"
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


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add standard security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if _is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
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


# Metrics endpoint — hidden in production, requires admin API key
@app.get("/api/v1/metrics", tags=["Monitoring"], include_in_schema=not _is_production)
async def get_metrics(request: Request):
    """Get application metrics (requires X-Admin-Key header in production)"""
    if _is_production:
        admin_key = request.headers.get("X-Admin-Key")
        if not admin_key or admin_key != settings.SECRET_KEY:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
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
