# app/middleware/tenant_middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.database.master_db import SessionLocal
from app.models.master_models import Tenant


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")

        if tenant_id:
            try:
                tenant_id = int(tenant_id)
                # Verify tenant exists and is active
                db = SessionLocal()
                tenant = db.query(Tenant).filter(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True
                ).first()

                if not tenant:
                    raise HTTPException(status_code=404, detail="Tenant not found")

                request.state.tenant_id = tenant_id
                request.state.tenant = tenant
                db.close()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid tenant ID")

        response = await call_next(request)
        return response