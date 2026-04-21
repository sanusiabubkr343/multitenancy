# app/schemas/migration_schemas.py
from pydantic import BaseModel
from typing import Optional


class MigrationRequest(BaseModel):
    revision: str = "head"


class MigrationCreateRequest(BaseModel):
    message: str


class MigrationResponse(BaseModel):
    message: str
    revision: str
    description: Optional[str] = None


class TenantMigrationResponse(BaseModel):
    message: str
    tenant_id: int
    tenant_name: str
    new_version: str


class TenantVersionResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    current_version: Optional[str] = None
