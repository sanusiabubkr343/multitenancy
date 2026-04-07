# app/models/master_models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

MasterBase = declarative_base()


class Tenant(MasterBase):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    subdomain = Column(String, unique=True, index=True, nullable=False)
    db_url = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Migration tracking
    current_version = Column(String, default="base")
    pending_migrations = Column(JSON, default=list)


class User(MasterBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Super admin can manage all tenants
    is_super_admin = Column(Boolean, default=False)