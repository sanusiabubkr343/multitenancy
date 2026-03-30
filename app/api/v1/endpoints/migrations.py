# app/api/v1/endpoints/migrations.py
"""
Migration management endpoints.

Reason: Provides API to manage database migrations for tenants,
allowing controlled rollouts and rollbacks.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import List, Optional
from pydantic import BaseModel

from app.services.migration_service import MigrationService
from app.core.dependencies import get_current_tenant

router = APIRouter(prefix="/migrations", tags=["migrations"])


class MigrationRequest(BaseModel):
    """Request model for migration operations."""
    tenant_id: Optional[str] = None
    revision: str = "head"

    class Config:
        schema_extra = {
            "example": {
                "tenant_id": "company1",
                "revision": "head"
            }
        }


class MigrationStatusResponse(BaseModel):
    """Response model for migration status."""
    tenant_id: str
    current_revision: Optional[str]
    latest_revision: str
    needs_upgrade: bool
    migration_history: List[dict] = []


@router.post("/upgrade", summary="Upgrade tenant migrations")
async def upgrade_migrations(
        request: MigrationRequest,
        background_tasks: BackgroundTasks,
        migration_service: MigrationService = Depends()
):
    """
    Upgrade migrations for tenants.

    - If tenant_id provided: upgrade only that tenant
    - If no tenant_id: upgrade all tenants
    """
    try:
        if request.tenant_id:
            # Run in background to avoid timeout
            background_tasks.add_task(
                migration_service.upgrade_tenant,
                request.tenant_id,
                request.revision
            )
            return {
                "message": f"Migration started for tenant {request.tenant_id}",
                "status": "in_progress"
            }
        else:
            background_tasks.add_task(
                migration_service.upgrade_all_tenants,
                request.revision
            )
            return {
                "message": "Migration started for all tenants",
                "status": "in_progress"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status", response_model=List[MigrationStatusResponse])
async def get_migration_status(
        tenant_id: Optional[str] = None,
        migration_service: MigrationService = Depends()
):
    """
    Get migration status for tenants.

    Shows current and latest migration versions for each tenant.
    """
    try:
        status = await migration_service.check_migration_status(tenant_id)
        return [
            MigrationStatusResponse(
                tenant_id=tenant,
                current_revision=info["current"],
                latest_revision=info["latest"],
                needs_upgrade=info["needs_upgrade"],
                migration_history=info.get("history", [])
            )
            for tenant, info in status.items()
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/downgrade", summary="Downgrade tenant migrations")
async def downgrade_migrations(
        request: MigrationRequest,
        migration_service: MigrationService = Depends()
):
    """
    Downgrade migrations for a specific tenant.

    Warning: This can cause data loss. Use with caution.
    """
    if not request.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required for downgrade operation"
        )

    try:
        await migration_service.downgrade_tenant(
            request.tenant_id,
            request.revision
        )
        return {
            "message": f"Downgraded tenant {request.tenant_id} to {request.revision}",
            "status": "completed"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )