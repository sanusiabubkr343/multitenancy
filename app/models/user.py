# app/models/user.py
"""
User model that exists in each tenant's database.

Reason: Each tenant has its own user table for complete data isolation.
"""
from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime
from app.models.base import BaseModel


class User(BaseModel):
    """User model for tenant databases."""
    __tablename__ = "users"

    email = Column(String(200), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(200))
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    def __repr__(self):
        return f"<User {self.username}: {self.email}>"