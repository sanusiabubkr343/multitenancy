# app/core/tenant_middleware.py
"""
Tenant identification middleware.

Reason: Intercepts all requests, extracts tenant ID, and makes it
available throughout the request lifecycle.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to handle tenant identification."""

    # Paths that don't require tenant identification
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/tenants"
    }

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add tenant information to request state.
        """
        # Skip tenant validation for public paths
        if request.url.path in self.PUBLIC_PATHS:
            request.state.tenant_id = None
            return await call_next(request)

        # For paths that start with /api/v1/tenants, also skip if it's a POST (create)
        if request.url.path.startswith("/api/v1/tenants") and request.method == "POST":
            request.state.tenant_id = None
            return await call_next(request)

        # Extract tenant ID from header
        tenant_id = request.headers.get(settings.TENANT_HEADER)

        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Missing tenant identifier",
                    "message": f"Please provide {settings.TENANT_HEADER} header"
                }
            )

        # Validate tenant ID format
        if not tenant_id.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid tenant ID",
                    "message": "Tenant ID must contain only alphanumeric characters, hyphens, and underscores"
                }
            )

        # Store tenant ID in request state for later use
        request.state.tenant_id = tenant_id

        # Log tenant access (for auditing)
        logger.info(f"Request from tenant: {tenant_id} to {request.url.path}")

        # Process request
        response = await call_next(request)

        # Add tenant ID to response headers for debugging
        response.headers[settings.TENANT_HEADER] = tenant_id

        return response