# app/api/v1/endpoints/users.py
"""
User management endpoints for tenant context.

Reason: Provide CRUD operations for users within a tenant's database.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.dependencies import get_tenant_db, get_current_tenant
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user"
)
async def create_user(
        user_data: UserCreate,
        db: Session = Depends(get_tenant_db),
        tenant_id: str = Depends(get_current_tenant)
):
    """
    Create a new user in the current tenant.

    - **email**: Must be unique within tenant
    - **username**: Must be unique within tenant
    - **password**: Will be hashed before storage
    """
    try:
        user_service = UserService(db)
        return user_service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List users"
)
async def list_users(
        skip: int = 0,
        limit: int = 100,
        is_active: bool = None,
        db: Session = Depends(get_tenant_db),
        tenant_id: str = Depends(get_current_tenant)
):
    """
    List users with pagination.

    - **skip**: Number of users to skip
    - **limit**: Maximum users to return
    - **is_active**: Filter by active status
    """
    user_service = UserService(db)
    return user_service.list_users(skip=skip, limit=limit, is_active=is_active)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID"
)
async def get_user(
        user_id: int,
        db: Session = Depends(get_tenant_db),
        tenant_id: str = Depends(get_current_tenant)
):
    """Get a specific user by ID."""
    try:
        user_service = UserService(db)
        return user_service.get_user(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user"
)
async def update_user(
        user_id: int,
        user_update: UserUpdate,
        db: Session = Depends(get_tenant_db),
        tenant_id: str = Depends(get_current_tenant)
):
    """Update user information."""
    try:
        user_service = UserService(db)
        return user_service.update_user(user_id, user_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user"
)
async def delete_user(
        user_id: int,
        db: Session = Depends(get_tenant_db),
        tenant_id: str = Depends(get_current_tenant)
):
    """Soft delete a user."""
    try:
        user_service = UserService(db)
        user_service.delete_user(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )