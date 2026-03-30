# app/models/product.py
"""
Product model example showing tenant-specific business data.

Reason: Demonstrates how to add tenant-specific models for business logic.
"""
from sqlalchemy import Column, String, Float, Boolean, Text,Integer
from app.models.base import BaseModel


class Product(BaseModel):
    """Product model for tenant databases."""
    __tablename__ = "products"

    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    stock_quantity = Column(Integer, default=0)

    def __repr__(self):
        return f"<Product {self.name} (SKU: {self.sku})>"