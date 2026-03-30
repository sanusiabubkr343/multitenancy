# app/models/tenant.py
"""
Tenant model for managing tenants in the master database.

Reason: This model lives in the tenant management database and
tracks all tenants with their database configurations.
"""
from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base


class Tenant(Base):
    """Tenant model for master database."""
    __tablename__ = "tenants"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    database_url = Column(String(500), nullable=True)  # Optional: override default URL
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tenant {self.id}: {self.name}>"