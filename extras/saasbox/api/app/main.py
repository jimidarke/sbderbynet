"""
SoapboxDerbyNet SaaS API
Main FastAPI application entry point.
"""
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db, close_db
from app.redis_client import get_redis, close_redis
from middleware.logging import alert_manager, AlertLevel, AlertCategory
from schemas.common import ErrorResponse, ErrorBody, ErrorCodes, HealthResponse


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    await init_db()
    await get_redis()

    yield

    # Shutdown
    await close_db()
    await close_redis()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="SoapboxDerbyNet SaaS API - Race management for soapbox derby events",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request."""
    import uuid
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Timing middleware
@app.middleware("http")
async def add_timing(request: Request, call_next):
    """Add response timing header."""
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors."""
    errors = exc.errors()
    first_error = errors[0] if errors else {}

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error=ErrorBody(
                code=ErrorCodes.VAL_INVALID_INPUT,
                message="Validation error",
                details={
                    "field": ".".join(str(loc) for loc in first_error.get("loc", [])),
                    "reason": first_error.get("msg", "Invalid input"),
                },
            ),
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors."""
    request_id = getattr(request.state, "request_id", None)

    # Log to Alert Manager
    await alert_manager.system_error(
        error=str(exc),
        request_id=request_id,
        traceback=traceback.format_exc(),
    )

    # Don't expose internal errors in production
    message = str(exc) if settings.is_development else "An unexpected error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorBody(
                code=ErrorCodes.SYS_INTERNAL_ERROR,
                message=message,
            ),
            request_id=request_id,
        ).model_dump(mode="json"),
    )


# Health check endpoint (no auth required)
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint for load balancers and monitoring."""
    db_status = "connected"
    redis_status = "connected"

    try:
        # Check Redis
        client = await get_redis()
        await client.ping()
    except Exception:
        redis_status = "disconnected"

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        redis=redis_status,
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """API root - basic info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_v1_prefix}/docs" if settings.is_development else None,
    }


# Import and include routers
from modules.auth.routes import router as auth_router
from modules.events.routes import router as events_router
from modules.races.routes import router as races_router
from modules.favorites.routes import router as favorites_router
from modules.audience.routes import router as audience_router
from modules.notifications.routes import router as notifications_router
from modules.notifications.routes import emergency_router

# Auth routes
app.include_router(
    auth_router,
    prefix=f"{settings.api_v1_prefix}/auth",
    tags=["Auth"],
)

# Events routes (nested under organizations)
app.include_router(
    events_router,
    prefix=f"{settings.api_v1_prefix}/orgs/{{org_id}}/events",
    tags=["Events"],
)

# Races routes (nested under events)
app.include_router(
    races_router,
    prefix=f"{settings.api_v1_prefix}/orgs/{{org_id}}/events/{{event_id}}/races",
    tags=["Races"],
)

# Favorites routes (user's favorites)
app.include_router(
    favorites_router,
    prefix=f"{settings.api_v1_prefix}/me/favorites",
    tags=["Favorites"],
)

# Audience routes (predictions, cheers, polls)
app.include_router(
    audience_router,
    prefix=f"{settings.api_v1_prefix}/orgs/{{org_id}}/events/{{event_id}}/audience",
    tags=["Audience"],
)

# Notification routes (push tokens, preferences, history)
app.include_router(
    notifications_router,
    prefix=f"{settings.api_v1_prefix}/me/notifications",
    tags=["Notifications"],
)

# Emergency broadcast routes (coordinator-only)
app.include_router(
    emergency_router,
    prefix=f"{settings.api_v1_prefix}/orgs/{{org_id}}/events/{{event_id}}/emergency",
    tags=["Emergency"],
)

# TODO: Uncomment as modules are implemented
# from modules.orgs.routes import router as orgs_router
# from modules.racers.routes import router as racers_router
# from modules.donations.routes import router as donations_router
# from modules.devices.routes import router as devices_router
# from modules.admin.routes import router as admin_router

# app.include_router(orgs_router, prefix=f"{settings.api_v1_prefix}/orgs", tags=["Organizations"])
# app.include_router(racers_router, prefix=f"{settings.api_v1_prefix}/orgs/{{org_id}}/events/{{event_id}}/racers", tags=["Racers"])
# app.include_router(donations_router, prefix=f"{settings.api_v1_prefix}/donations", tags=["Donations"])
# app.include_router(devices_router, prefix=f"{settings.api_v1_prefix}/orgs/{{org_id}}/devices", tags=["Devices"])
# app.include_router(admin_router, prefix=f"{settings.api_v1_prefix}/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers if not settings.is_development else 1,
    )
