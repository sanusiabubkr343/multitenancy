# app/core/dependencies.py
"""
Dependency injection for FastAPI routes.

Reason: Centralizes tenant extraction and database session management,
ensuring consistent access across all endpoints.
"""
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.config import settings
from app.core.database import get_tenant_session

logger = logging.getLogger(__name__)


async def get_current_tenant(request: Request) -> str:
    """
    Extract current tenant ID from request headers.

    Reason: All tenant-specific endpoints need to know which tenant's
    data to operate on.
    """
    tenant_id = request.headers.get(settings.TENANT_HEADER)

    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail=f"{settings.TENANT_HEADER} header is required"
        )

    # Validate tenant_id format
    if not tenant_id.replace('-', '').replace('_', '').isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant ID format"
        )

    return tenant_id


async def get_tenant_db(request: Request) -> Session:
    """
    Get tenant database session.

    Reason: Provides database session for tenant-specific operations.
    """
    tenant_id = request.state.tenant_id if hasattr(request.state, 'tenant_id') else None

    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="No tenant ID found in request state"
        )

    try:
        db = get_tenant_session(tenant_id)
        return db
    except Exception as e:
        logger.error(f"Failed to get database session for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database connection error"
        )


async def get_current_user(
        db: Session = Depends(get_tenant_db),
        tenant_id: str = Depends(get_current_tenant)
):
    """
    Get current authenticated user.

    Reason: Authentication and authorization for user-specific operations.
    """
    # This is a placeholder - implement actual JWT token validation
    # For now, return None and let endpoints handle authentication
    return None