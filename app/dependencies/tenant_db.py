# app/dependencies/tenant_db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.tenant_models import TenantBase
from app.models.master_models import Tenant
from fastapi import HTTPException, Request
from typing import Optional


class TenantDatabaseManager:
    def __init__(self):
        self.tenant_sessions = {}

    def get_tenant_db_url(self, tenant_id: int, master_session: Session) -> Optional[str]:
        tenant = master_session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.is_active:
            return tenant.db_url
        return None

    def get_tenant_session(self, tenant_id: int, master_session: Session) -> Session:
        db_url = self.get_tenant_db_url(tenant_id, master_session)
        if not db_url:
            raise HTTPException(status_code=404, detail="Tenant not found or inactive")

        # Cache session for performance
        if tenant_id not in self.tenant_sessions:
            engine = create_engine(db_url)
            self.tenant_sessions[tenant_id] = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        return self.tenant_sessions[tenant_id]()


tenant_db_manager = TenantDatabaseManager()


def get_tenant_db(request: Request, master_db: Session):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    db = tenant_db_manager.get_tenant_session(tenant_id, master_db)
    try:
        yield db
    finally:
        db.close()