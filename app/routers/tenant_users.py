# app/routers/tenant_users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.models.tenant_models import TenantUser
from app.schemas.tenant_user_schemas import TenantUserCreate, TenantUserResponse
from app.utils.tenant_security import get_password_hash, get_current_active_tenant_user
from app.dependencies.tenant_db import get_tenant_db

router = APIRouter()


@router.post("/", response_model=TenantUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: TenantUserCreate,
    db: Session = Depends(get_tenant_db),
    current_user: TenantUser = Depends(get_current_active_tenant_user)
) -> Any:
    """Create a new tenant user (authenticated tenant users only)"""
    # Check if user exists
    existing_user = db.query(TenantUser).filter(TenantUser.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new tenant user
    hashed_password = get_password_hash(user_data.password)
    db_user = TenantUser(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/", response_model=List[TenantUserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_tenant_db),
    current_user: TenantUser = Depends(get_current_active_tenant_user)
) -> Any:
    """List all users in the tenant"""
    users = db.query(TenantUser).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=TenantUserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: TenantUser = Depends(get_current_active_tenant_user)
) -> Any:
    """Get a specific tenant user"""
    user = db.query(TenantUser).filter(TenantUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: TenantUser = Depends(get_current_active_tenant_user)
) -> dict:
    """Deactivate a tenant user"""
    user = db.query(TenantUser).filter(TenantUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    return {"message": "User deactivated", "user_id": user_id}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: TenantUser = Depends(get_current_active_tenant_user)
) -> dict:
    """Delete a tenant user"""
    user = db.query(TenantUser).filter(TenantUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()

    return {"message": "User deleted", "user_id": user_id}
