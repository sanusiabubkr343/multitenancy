# app/services/user_service.py
"""
User management service for tenant databases.

Reason: Handles user operations within tenant context with proper isolation.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for user management within a tenant."""

    def __init__(self, db: Session):
        self.db = db

    def get_password_hash(self, password: str) -> str:
        """Hash password for storage."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Reason: User registration with validation.
        """
        # Check if user exists
        existing_user = self.db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()

        if existing_user:
            raise ValueError("User with this email or username already exists")

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=self.get_password_hash(user_data.password),
            is_active=True,
            is_admin=user_data.is_admin if hasattr(user_data, 'is_admin') else False
        )

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Created user: {user.username} (ID: {user.id})")
            return user

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise

    def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def list_users(self, skip: int = 0, limit: int = 100, is_active: bool = None) -> List[User]:
        """List users with filters."""
        query = self.db.query(User)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        """Update user information."""
        user = self.get_user(user_id)

        update_data = user_update.dict(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = self.get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Updated user: {user.username}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update user: {e}")
            raise

    def delete_user(self, user_id: int) -> bool:
        """Soft delete user."""
        user = self.get_user(user_id)

        try:
            user.is_active = False
            self.db.commit()
            logger.info(f"Deleted user: {user.username}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete user: {e}")
            raise

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username/email and password."""
        user = self.get_user_by_username(username)
        if not user:
            user = self.get_user_by_email(username)

        if not user or not user.is_active:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        return user