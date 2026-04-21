# app/routers/tenant_auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any
from app.models.tenant_models import TenantUser
from app.schemas.tenant_user_schemas import TenantUserCreate, TenantUserResponse, Token
from app.utils.tenant_security import (
    get_password_hash,
    authenticate_tenant_user,
    create_access_token,
    get_current_tenant_user
)
from app.dependencies.tenant_db import get_tenant_db
from app.config import settings

router = APIRouter()


@router.post("/register-admin", response_model=TenantUserResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant_user(
    user_data: TenantUserCreate,
    db: Session = Depends(get_tenant_db)

) -> Any:
    """Register a new tenant user (requires X-Tenant-ID header)"""
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
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.post("/login", response_model=Token)
async def login_tenant_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_tenant_db)
) -> Any:
    """Login tenant user and get access token (requires X-Tenant-ID header)"""
    user = authenticate_tenant_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get tenant_id from request state (set by middleware/dependency)
    tenant_id = getattr(request.state, "tenant_id", None)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "tenant_id": tenant_id,
            "is_tenant_user": True
        },
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=TenantUserResponse)
async def get_current_tenant_user_info(
    current_user: TenantUser = Depends(get_current_tenant_user)
) -> Any:
    """Get current tenant user information"""
    return current_user
