# app/services/tenant_service.py
"""
Tenant management service.

Reason: Business logic for tenant operations including creation,
deletion, and management with database provisioning.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.core.database import create_tenant_database, drop_tenant_database, get_tenant_session
from app.core.config import settings

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TenantService:
    """Service for tenant management operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        """
        Create a new tenant with dedicated database.

        Reason: Complete tenant provisioning including database creation.
        """
        # Check if tenant already exists
        existing_tenant = self.db.query(Tenant).filter(
            Tenant.id == tenant_data.id
        ).first()

        if existing_tenant:
            raise ValueError(f"Tenant with ID {tenant_data.id} already exists")

        # Check email uniqueness
        existing_email = self.db.query(Tenant).filter(
            Tenant.email == tenant_data.email
        ).first()

        if existing_email:
            raise ValueError(f"Email {tenant_data.email} already registered")

        # Create tenant in master database
        tenant = Tenant(
            id=tenant_data.id,
            name=tenant_data.name,
            email=tenant_data.email,
            is_active=True
        )

        try:
            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)

            # Create dedicated database for tenant
            create_tenant_database(tenant.id)

            logger.info(f"Successfully created tenant: {tenant.id}")
            return tenant

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create tenant {tenant_data.id}: {e}")
            raise

    async def create_default_admin(self, tenant_id: str):
        """
        Create default admin user for a tenant.

        Reason: Provide initial admin access for new tenants.
        """
        from app.models.user import User

        try:
            db = get_tenant_session(tenant_id)

            # Check if admin already exists
            existing_admin = db.query(User).filter(
                User.email == settings.DEFAULT_ADMIN_EMAIL
            ).first()

            if existing_admin:
                logger.info(f"Admin already exists for tenant {tenant_id}")
                return

            # Create admin user
            admin = User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                username="admin",
                full_name="System Administrator",
                hashed_password=pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD),
                is_active=True,
                is_admin=True
            )

            db.add(admin)
            db.commit()
            db.refresh(admin)

            logger.info(f"Created default admin for tenant {tenant_id}")

        except Exception as e:
            logger.error(f"Failed to create admin for tenant {tenant_id}: {e}")
            raise
        finally:
            db.close()

    def get_tenant(self, tenant_id: str) -> Tenant:
        """Get tenant by ID."""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        return tenant

    def list_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """List all tenants with pagination."""
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    def update_tenant(self, tenant_id: str, tenant_update: TenantUpdate) -> Tenant:
        """Update tenant information."""
        tenant = self.get_tenant(tenant_id)

        update_data = tenant_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Updated tenant: {tenant_id}")
        return tenant

    async def delete_tenant(self, tenant_id: str):
        """
        Delete tenant and its database.

        Reason: Complete tenant removal with data cleanup.
        """
        tenant = self.get_tenant(tenant_id)

        try:
            # Drop tenant's database
            drop_tenant_database(tenant_id)

            # Delete from master database
            self.db.delete(tenant)
            self.db.commit()

            logger.info(f"Deleted tenant: {tenant_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise

    def get_tenant_stats(self, tenant_id: str) -> dict:
        """
        Get statistics for a tenant.

        Reason: Monitor tenant usage and database size.
        """
        from app.core.database import get_tenant_engine

        tenant = self.get_tenant(tenant_id)
        engine = get_tenant_engine(tenant_id)

        stats = {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "created_at": tenant.created_at,
            "is_active": tenant.is_active
        }

        try:
            # Get database size
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT pg_database_size(current_database()) as size
                """))
                db_size = result.fetchone()[0]
                stats["database_size_bytes"] = db_size
                stats["database_size_mb"] = round(db_size / (1024 * 1024), 2)

                # Get table counts
                result = conn.execute(text("""
                                           SELECT table_name, (SELECT COUNT(*) FROM information_schema.tables)
                                           FROM information_schema.tables
                                           WHERE table_schema = 'public'
                                           """))
                stats["table_count"] = len(result.fetchall())

        except Exception as e:
            logger.error(f"Failed to get stats for tenant {tenant_id}: {e}")
            stats["error"] = str(e)

        return stats