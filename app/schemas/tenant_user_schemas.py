# app/schemas/tenant_user_schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class TenantUserBase(BaseModel):
    email: EmailStr
    full_name: str


class TenantUserCreate(TenantUserBase):
    password: str


class TenantUserResponse(TenantUserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    is_tenant_user: bool = False
