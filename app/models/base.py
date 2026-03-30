# app/models/base.py
"""
Base model with common fields and functionality.
"""
from sqlalchemy import Column, Integer, DateTime, String, Boolean
from datetime import datetime
from app.core.database import Base


class BaseModel(Base):
    """Base model with common fields."""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }