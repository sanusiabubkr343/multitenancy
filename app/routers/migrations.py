# app/routers/migrations.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any, List, Dict
from app.database.master_db import SessionLocal
from app.database.migration_manager import TenantMigrationManager
from app.models.master_models import Tenant, User
from app.utils.security import get_current_super_admin
from app.schemas.migration_schemas import (
    MigrationRequest, 
    MigrationCreateRequest, 
    MigrationResponse, 
    TenantMigrationResponse, 
    TenantVersionResponse
)

router = APIRouter()


def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/create", response_model=MigrationResponse)
async def create_migration(
        request: MigrationCreateRequest,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """Create a new migration for all tenants"""
    migration_manager = TenantMigrationManager(db)
    revision = migration_manager.create_migration(request.message)

    return MigrationResponse(
        message="Migration created successfully",
        revision=revision,
        description=request.message
    )


@router.post("/migrate-all")
async def migrate_all_tenants(
        request: MigrationRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> dict:
    """Migrate all tenants to a specific version"""
    migration_manager = TenantMigrationManager(db)

    def run_migrations():
        results = migration_manager.migrate_all_tenants(request.revision)
        print(f"Migration results: {results}")

    background_tasks.add_task(run_migrations)

    return {
        "message": "Migration started for all tenants",
        "revision": request.revision,
        "status": "background_task_started"
    }


@router.post("/migrate-tenant/{tenant_id}", response_model=TenantMigrationResponse)
async def migrate_single_tenant(
        tenant_id: int,
        request: MigrationRequest,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """Migrate a specific tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    migration_manager = TenantMigrationManager(db)
    success, message = migration_manager.migrate_tenant(
        tenant.name,
        tenant.db_url,
        request.revision
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return TenantMigrationResponse(
        message=message,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        new_version=request.revision
    )


@router.get("/versions")
async def get_migration_versions(
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> dict:
    """Get all available migration versions"""
    migration_manager = TenantMigrationManager(db)
    versions = migration_manager.get_migration_versions()

    return {"versions": versions}


@router.post("/downgrade-tenant/{tenant_id}", response_model=TenantMigrationResponse)
async def downgrade_tenant(
        tenant_id: int,
        request: MigrationRequest,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """Downgrade a specific tenant to a previous version"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    migration_manager = TenantMigrationManager(db)
    success, message = migration_manager.downgrade_tenant(
        tenant.name,
        tenant.db_url,
        request.revision
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return TenantMigrationResponse(
        message=message,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        new_version=request.revision
    )


@router.get("/tenant-version/{tenant_id}", response_model=TenantVersionResponse)
async def get_tenant_version(
        tenant_id: int,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """Get current migration version of a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantVersionResponse(
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        current_version=tenant.current_version
    )