# app/api/v1/endpoints/tenants.py
"""
Tenant management endpoints.

Reason: Provides API for creating, managing, and deleting tenants.
These endpoints operate on the master database, not tenant databases.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from app.core.database import TenantMgmtSessionLocal
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.services.tenant_service import TenantService
from app.services.migration_service import MigrationService

router = APIRouter(prefix="/tenants", tags=["tenants"])


def get_db():
    """Dependency to get master database session."""
    db = TenantMgmtSessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    description="Creates a new tenant with its own dedicated database"
)
async def create_tenant(
        tenant_data: TenantCreate,
        db: Session = Depends(get_db)
):
    """
    Create a new tenant.
    """
    try:
        tenant_service = TenantService(db)
        migration_service = MigrationService()

        tenant = await tenant_service.create_tenant(tenant_data)

        # Run migrations on new tenant database
        await migration_service.upgrade_tenant(tenant.id, "head")

        # Create default admin user
        await tenant_service.create_default_admin(tenant.id)

        return tenant

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[TenantResponse],
    summary="List all tenants"
)
async def list_tenants(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """Get list of all tenants."""
    tenant_service = TenantService(db)
    return tenant_service.list_tenants(skip=skip, limit=limit)


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant details"
)
async def get_tenant(
        tenant_id: str,
        db: Session = Depends(get_db)
):
    """Get details of a specific tenant."""
    try:
        tenant_service = TenantService(db)
        return tenant_service.get_tenant(tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant"
)
async def update_tenant(
        tenant_id: str,
        tenant_update: TenantUpdate,
        db: Session = Depends(get_db)
):
    """Update tenant information."""
    try:
        tenant_service = TenantService(db)
        return tenant_service.update_tenant(tenant_id, tenant_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Permanently deletes a tenant and its database"
)
async def delete_tenant(
        tenant_id: str,
        db: Session = Depends(get_db)
):
    """
    Delete a tenant.

    Warning: This permanently deletes the tenant's database and all data.
    This action cannot be undone.
    """
    try:
        tenant_service = TenantService(db)
        await tenant_service.delete_tenant(tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )