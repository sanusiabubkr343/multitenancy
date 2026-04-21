# app/schemas/__init__.py
from app.schemas.tenant_schemas import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse
)
from app.schemas.migration_schemas import (
    MigrationRequest,
    MigrationCreateRequest,
    MigrationResponse,
    TenantMigrationResponse,
    TenantVersionResponse
)
from app.schemas.product_schemas import (
    ProductBase,
    ProductCreate,
    ProductResponse
)