# app/schemas/tenant_schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TenantBase(BaseModel):
    name: str
    subdomain: str
    logo_url: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    subdomain: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    id: int
    db_url: str
    is_active: bool
    current_version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]
    total: int
    skip: int
    limit: int