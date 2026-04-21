# app/dependencies/tenant_db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.tenant_models import TenantBase
from app.models.master_models import Tenant
from fastapi import HTTPException, Request, Depends
from fastapi.security import APIKeyHeader
from typing import Optional
from app.database.master_db import SessionLocal

header_scheme = APIKeyHeader(
    name="X-Tenant-ID", 
    description="Tenant identifier for tenant-specific endpoints",
    scheme_name="TenantAuth"
)


class TenantDatabaseManager:
    def __init__(self):
        self.tenant_sessions = {}
        self.tenant_engines = {}  # Add engine cache

    def get_tenant_db_url(self, tenant_id: int) -> Optional[str]:
        """Get tenant database URL from master DB"""
        # Create a new master session instead of accepting one as parameter
        master_db = SessionLocal()
        try:
            tenant = master_db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant and tenant.is_active:
                return tenant.db_url
            return None
        finally:
            master_db.close()

    def get_tenant_session(self, tenant_id: int) -> Session:
        """Get or create a session for a tenant"""
        db_url = self.get_tenant_db_url(tenant_id)
        if not db_url:
            raise HTTPException(status_code=404, detail="Tenant not found or inactive")

        # Cache engine and session for performance
        if tenant_id not in self.tenant_engines:
            self.tenant_engines[tenant_id] = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True  # Helps with connection reliability
            )
            self.tenant_sessions[tenant_id] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.tenant_engines[tenant_id]
            )

        return self.tenant_sessions[tenant_id]()


tenant_db_manager = TenantDatabaseManager()


def get_tenant_db(request: Request):
    """
    Dependency to get tenant database session.
    This is used as a FastAPI dependency.
    Requires X-Tenant-ID header to be set by TenantMiddleware.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # If middleware didn't set it, try to get it from header directly
    if not tenant_id:
        tenant_id_header = request.headers.get("X-Tenant-ID")
        if tenant_id_header:
            try:
                tenant_id = int(tenant_id_header)
                request.state.tenant_id = tenant_id
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid tenant ID format")
        else:
            raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    # Convert tenant_id to int if it's a string
    if isinstance(tenant_id, str):
        try:
            tenant_id = int(tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    db = tenant_db_manager.get_tenant_session(tenant_id)
    try:
        yield db
    finally:
        db.close()