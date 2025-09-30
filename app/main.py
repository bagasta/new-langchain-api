from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional
import time
from urllib.parse import urlparse

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api import api_router
from app.core.logging import logger
from app.core.database import get_db
from app.core.deps import get_auth_service
from app.services.auth_service import AuthService
from app.api.v1.auth import process_google_callback
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("Starting up LangChain Agent API")

    # Create database tables
    init_db()
    logger.info("Database initialised")

    yield

    # Shutdown
    logger.info("Shutting down LangChain Agent API")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A scalable API for creating and managing AI agents with dynamic tool integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"https?://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )

    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )

    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), url=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


redirect_path = urlparse(settings.GOOGLE_REDIRECT_URI).path or ""
if redirect_path and not redirect_path.startswith("/"):
    redirect_path = f"/{redirect_path}"
default_redirect_path = f"{settings.API_V1_STR}/auth/google/callback"

# Normalise for comparison while preserving the configured path for routing
normalised_redirect = redirect_path.rstrip("/") or "/"
normalised_default = default_redirect_path.rstrip("/") or "/"

if (
    redirect_path
    and normalised_redirect != normalised_default
    and redirect_path != "/"
):
    logger.info(
        "Registering additional Google OAuth callback path",
        configured_path=redirect_path,
        default_path=default_redirect_path,
    )

    @app.get(redirect_path, include_in_schema=False)
    async def google_callback_alias(
        code: str,
        state: str,
        scope: Optional[str] = None,
        db: Session = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
    ):
        return await process_google_callback(code, state, db, auth_service, scope)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LangChain Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.options("/{path:path}")
async def preflight_handler(path: str) -> Response:
    """Handle CORS preflight requests with an empty 204 response."""
    return Response(status_code=204)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return empty response for favicon requests."""
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
