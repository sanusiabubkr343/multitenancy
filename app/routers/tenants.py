# app/routers/tenants.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.config import settings
from app.database.master_db import SessionLocal
from app.models.master_models import Tenant, User
from app.schemas.tenant_schemas import TenantCreate, TenantResponse
from app.database.migration_manager import TenantMigrationManager
from app.utils.security import get_current_super_admin

router = APIRouter()


def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
        tenant_data: TenantCreate,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """Create a new tenant (Super Admin only)"""
    # Check if tenant exists
    existing = db.query(Tenant).filter(
        (Tenant.name == tenant_data.name) |
        (Tenant.subdomain == tenant_data.subdomain)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Tenant already exists")

    # Create database URL
    # Use internal URL template if running in Docker, otherwise use localhost template
    is_docker = settings.MASTER_DATABASE_URL.find("postgres:5432") != -1
    template = settings.TENANT_DB_INTERNAL_URL_TEMPLATE if is_docker else settings.TENANT_DB_URL_TEMPLATE
    db_url = template.format(tenant_name=tenant_data.name)

    # Create tenant record
    tenant = Tenant(
        name=tenant_data.name,
        subdomain=tenant_data.subdomain,
        db_url=db_url,
        logo_url=tenant_data.logo_url
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Create tenant database and run migrations
    try:
        migration_manager = TenantMigrationManager(db)
        migration_manager.create_tenant_database(tenant.name, db_url)
    except Exception as e:
        # Rollback tenant creation if database creation fails
        db.delete(tenant)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to create tenant database: {str(e)}")

    return tenant


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """List all tenants (Super Admin only)"""
    tenants = db.query(Tenant).offset(skip).limit(limit).all()
    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
        tenant_id: int,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> Any:
    """Get tenant details (Super Admin only)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}/deactivate")
async def deactivate_tenant(
        tenant_id: int,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> dict:
    """Deactivate a tenant (Super Admin only)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.is_active = False
    db.commit()

    return {"message": "Tenant deactivated", "tenant_id": tenant_id}


@router.delete("/{tenant_id}")
async def delete_tenant(
        tenant_id: int,
        db: Session = Depends(get_master_db),
        current_user: User = Depends(get_current_super_admin)
) -> dict:
    """Delete a tenant (Super Admin only)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    db.delete(tenant)
    db.commit()

    return {"message": "Tenant deleted", "tenant_id": tenant_id}