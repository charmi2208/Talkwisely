"""
TalkWiseAI — Main FastAPI Application.

Configures the FastAPI app with:
- CORS middleware
- API router mounting
- Startup/shutdown events
- Global exception handlers
- OpenAPI documentation
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    action_items, ai, analytics, auth, conversations, crm,
    integrations, knowledge_base, meetings, notifications, reports, sales, users
)
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

# Configure logging before anything else
configure_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: setup → serve → teardown."""
    logger.info(
        "TalkWiseAI starting",
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        stt_provider=settings.stt_provider,
        demo_mode=settings.demo_mode_enabled,
    )

    # Create storage directories
    import os
    os.makedirs(settings.storage_local_path, exist_ok=True)
    os.makedirs(f"{settings.storage_local_path}/uploads", exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)

    yield

    logger.info("TalkWiseAI shutting down")


# Create FastAPI application
app = FastAPI(
    title="TalkWiseAI API",
    description=(
        "TalkWiseAI — AI-Powered Meeting, Call & Sales Intelligence Platform. "
        "Transform business conversations into actionable intelligence."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Return a clean error response without leaking stack traces in production."""
    logger.error("Unhandled exception", path=request.url.path, error=str(exc), exc_info=exc)

    if settings.is_development:
        detail = str(exc)
    else:
        detail = "An internal error occurred. Please try again later."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail, "type": "internal_error"},
    )


# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(conversations.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(action_items.router, prefix=API_PREFIX)
app.include_router(knowledge_base.router, prefix=API_PREFIX)
app.include_router(crm.router, prefix=API_PREFIX)
app.include_router(integrations.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(sales.router, prefix=API_PREFIX)
app.include_router(meetings.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "env": settings.app_env,
        "providers": {
            "llm": settings.llm_provider,
            "stt": settings.stt_provider,
            "embedding": settings.embedding_provider,
            "crm": settings.crm_provider,
        },
    }


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — redirect to API docs."""
    return {"message": "TalkWiseAI API. Visit /api/docs for documentation."}
