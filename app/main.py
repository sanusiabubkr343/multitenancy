# app/main.py
"""
Main FastAPI application entry point.

Reason: Application initialization, middleware setup, and route registration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.tenant_middleware import TenantMiddleware
from app.core.database import Base, tenant_mgmt_engine
from app.api.v1.router import router as api_v1_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Reason: Initialize resources on startup and cleanup on shutdown.
    """
    # Startup
    logger.info("Starting up application...")

    # Create master database tables if they don't exist
    try:
        Base.metadata.create_all(bind=tenant_mgmt_engine)
        logger.info("Master database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create master database tables: {e}")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Cleanup database connections
    from app.core.database import cleanup_idle_connections
    cleanup_idle_connections()
    logger.info("Database connections cleaned up")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Multi-tenant FastAPI application with separate databases per tenant",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"]  # Configure properly
)

app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(api_v1_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "debug": settings.DEBUG
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "documentation": "/docs" if settings.DEBUG else "Documentation disabled",
        "status": "operational"
    }


