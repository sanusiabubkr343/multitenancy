# app/routers/tenant_data.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Any
from pydantic import BaseModel
from datetime import datetime
from app.dependencies.tenant_db import get_tenant_db
from app.models.tenant_models import Product
from app.utils.security import get_current_active_user
from app.models.master_models import User as MasterUser

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    description: str = None
    price: float
    stock_quantity: int = 0


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str = None
    price: float
    stock_quantity: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        tenant_db: Session = Depends(get_tenant_db),
        current_user: MasterUser = Depends(get_current_active_user)
) -> Any:
    """Create a product in the current tenant"""
    db_product = Product(**product.dict())
    tenant_db.add(db_product)
    tenant_db.commit()
    tenant_db.refresh(db_product)
    return db_product


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
        skip: int = 0,
        limit: int = 100,
        tenant_db: Session = Depends(get_tenant_db),
        current_user: MasterUser = Depends(get_current_active_user)
) -> Any:
    """List all products in the current tenant"""
    products = tenant_db.query(Product).offset(skip).limit(limit).all()
    return products


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
        product_id: int,
        tenant_db: Session = Depends(get_tenant_db),
        current_user: MasterUser = Depends(get_current_active_user)
) -> Any:
    """Get a specific product by ID"""
    product = tenant_db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
        product_id: int,
        product_update: ProductCreate,
        tenant_db: Session = Depends(get_tenant_db),
        current_user: MasterUser = Depends(get_current_active_user)
) -> Any:
    """Update a product"""
    product = tenant_db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in product_update.dict().items():
        setattr(product, key, value)

    tenant_db.commit()
    tenant_db.refresh(product)
    return product


@router.delete("/products/{product_id}")
async def delete_product(
        product_id: int,
        tenant_db: Session = Depends(get_tenant_db),
        current_user: MasterUser = Depends(get_current_active_user)
) -> dict:
    """Delete a product"""
    product = tenant_db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    tenant_db.delete(product)
    tenant_db.commit()
    return {"message": "Product deleted", "product_id": product_id}


@router.post("/add-column-test")
async def test_add_column(
        request: Request,
        tenant_db: Session = Depends(get_tenant_db),
        current_user: MasterUser = Depends(get_current_active_user)
) -> dict:
    """Example: This shows what happens when adding a column"""
    return {
        "message": "To add a column, create a migration and then migrate specific tenants",
        "tenant_id": getattr(request.state, "tenant_id", None),
        "steps": [
            "1. Add column to model in app/models/tenant_models.py",
            "2. Create migration: POST /api/migrations/create",
            "3. Check migration versions: GET /api/migrations/versions",
            "4. Migrate specific tenant: POST /api/migrations/migrate-tenant/{tenant_id}",
            "5. Or migrate all: POST /api/migrations/migrate-all"
        ]
    }