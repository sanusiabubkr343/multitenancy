# app/api/v1/router.py
"""
API v1 router configuration.

Reason: Centralized routing for all v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import tenants, users, migrations

router = APIRouter()

# Include all endpoint routers
router.include_router(tenants.router)
router.include_router(users.router)
router.include_router(migrations.router)