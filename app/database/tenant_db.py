# app/routers/tenant_data.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.dependencies.tenant_db import get_tenant_db
from app.models.tenant_models import Product, Order, TenantUser
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    description: str = None
    price: float
    stock_quantity: int = 0


class ProductResponse(ProductCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/products", response_model=ProductResponse)
async def create_product(
        product: ProductCreate,
        tenant_db: Session = Depends(get_tenant_db)
):
    db_product = Product(**product.dict())
    tenant_db.add(db_product)
    tenant_db.commit()
    tenant_db.refresh(db_product)
    return db_product


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
        skip: int = 0,
        limit: int = 100,
        tenant_db: Session = Depends(get_tenant_db)
):
    products = tenant_db.query(Product).offset(skip).limit(limit).all()
    return products


@router.post("/add-column-test")
async def test_add_column(
        tenant_db: Session = Depends(get_tenant_db)
):
    """Example: This shows what happens when adding a column"""
    # When you add a column to TenantBase model, e.g.:
    # class Product(TenantBase):
    #     new_column = Column(String, nullable=True)

    # Then you need to create a migration:
    # POST /api/migrations/create with message "add_new_column_to_products"

    # Then migrate specific tenant:
    # POST /api/migrations/migrate-tenant/{tenant_id}

    return {
        "message": "To add a column, create a migration and then migrate specific tenants",
        "steps": [
            "1. Add column to model in app/models/tenant_models.py",
            "2. Create migration: POST /api/migrations/create",
            "3. Check migration versions: GET /api/migrations/versions",
            "4. Migrate specific tenant: POST /api/migrations/migrate-tenant/{tenant_id}",
            "5. Or migrate all: POST /api/migrations/migrate-all"
        ]
    }