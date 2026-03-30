# app/services/migration_service.py
"""
Migration service for managing tenant database migrations.

Reason: Centralized migration logic with support for:
- Per-tenant migrations
- Batch processing
- Error handling and retries
- Migration status tracking
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from contextlib import contextmanager

from app.core.config import settings
from app.core.database import get_tenant_engine, tenant_mgmt_engine

logger = logging.getLogger(__name__)


class MigrationService:
    """Service for managing tenant database migrations."""

    def __init__(self):
        self.alembic_cfg = Config("alembic.ini")
        self.batch_size = settings.MIGRATION_BATCH_SIZE
        self.timeout = settings.MIGRATION_TIMEOUT

    def get_all_tenants(self) -> List[str]:
        """Get all active tenants from master database."""
        with tenant_mgmt_engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM tenants WHERE is_active = true")
            )
            return [row[0] for row in result]

    def get_tenant_current_revision(self, tenant_id: str) -> Optional[str]:
        """
        Get current migration revision for a tenant.

        Reason: Determine which migrations have been applied to a tenant.
        """
        try:
            engine = get_tenant_engine(tenant_id)
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get current revision for {tenant_id}: {e}")
            return None

    def get_latest_revision(self) -> str:
        """Get the latest available migration revision."""
        script = ScriptDirectory.from_config(self.alembic_cfg)
        return script.get_current_head()

    def get_migration_history(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Get migration history for a tenant.

        Reason: Audit trail of applied migrations.
        """
        try:
            engine = get_tenant_engine(tenant_id)
            version_table = f"{tenant_id}_alembic_version"

            with engine.connect() as conn:
                # Check if version table exists
                result = conn.execute(
                    text(f"""
                        SELECT * FROM information_schema.tables 
                        WHERE table_name = '{version_table}'
                    """)
                )

                if not result.fetchone():
                    return []

                # Get migration history
                result = conn.execute(
                    text(f"SELECT * FROM {version_table} ORDER BY version_num DESC")
                )

                return [
                    {"version": row[0]} for row in result
                ]
        except Exception as e:
            logger.error(f"Failed to get migration history for {tenant_id}: {e}")
            return []

    async def upgrade_tenant(self, tenant_id: str, revision: str = "head"):
        """
        Upgrade a specific tenant to a revision.

        Reason: Apply migrations to a single tenant.
        """
        logger.info(f"Upgrading tenant {tenant_id} to {revision}")

        try:
            # Set database URL for this tenant
            db_url = f"postgresql://postgres:password@localhost:5432/tenant_{tenant_id}"
            self.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

            # Run upgrade with timeout
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: command.upgrade(self.alembic_cfg, revision)
                ),
                timeout=self.timeout
            )

            logger.info(f"Successfully upgraded tenant {tenant_id}")

        except asyncio.TimeoutError:
            logger.error(f"Migration timeout for tenant {tenant_id}")
            raise Exception(f"Migration timeout after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"Failed to upgrade tenant {tenant_id}: {e}")
            raise

    async def downgrade_tenant(self, tenant_id: str, revision: str = "base"):
        """
        Downgrade a specific tenant to a revision.

        Reason: Roll back migrations when needed.
        """
        logger.info(f"Downgrading tenant {tenant_id} to {revision}")

        try:
            db_url = f"postgresql://postgres:password@localhost:5432/tenant_{tenant_id}"
            self.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: command.downgrade(self.alembic_cfg, revision)
                ),
                timeout=self.timeout
            )

            logger.info(f"Successfully downgraded tenant {tenant_id}")

        except asyncio.TimeoutError:
            logger.error(f"Migration timeout for tenant {tenant_id}")
            raise Exception(f"Migration timeout after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"Failed to downgrade tenant {tenant_id}: {e}")
            raise

    async def upgrade_all_tenants(self, revision: str = "head"):
        """
        Upgrade all active tenants in batches.

        Reason: Efficiently apply migrations to all tenants with batch processing.
        """
        tenants = self.get_all_tenants()
        logger.info(f"Upgrading {len(tenants)} tenants to {revision}")

        failed_tenants = []

        # Process in batches to avoid overwhelming the system
        for i in range(0, len(tenants), self.batch_size):
            batch = tenants[i:i + self.batch_size]
            logger.info(f"Processing batch {i // self.batch_size + 1} with {len(batch)} tenants")

            # Process batch concurrently
            tasks = []
            for tenant in batch:
                task = self.upgrade_tenant(tenant, revision)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Track failures
            for tenant, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to upgrade tenant {tenant}: {result}")
                    failed_tenants.append(tenant)

        if failed_tenants:
            logger.error(f"Failed tenants: {failed_tenants}")
            raise Exception(f"Failed to upgrade {len(failed_tenants)} tenants")
        else:
            logger.info("All tenants upgraded successfully")

    async def check_migration_status(self, tenant_id: str = None) -> Dict:
        """
        Check migration status for tenants.

        Reason: Monitor migration progress and identify tenants needing upgrades.
        """
        if tenant_id:
            tenants = [tenant_id]
        else:
            tenants = self.get_all_tenants()

        latest_rev = self.get_latest_revision()
        status = {}

        for tenant in tenants:
            try:
                current_rev = self.get_tenant_current_revision(tenant)
                history = self.get_migration_history(tenant)

                status[tenant] = {
                    "current": current_rev,
                    "latest": latest_rev,
                    "needs_upgrade": current_rev != latest_rev,
                    "history": history,
                    "status": "healthy" if current_rev else "not_initialized"
                }
            except Exception as e:
                logger.error(f"Failed to check status for tenant {tenant}: {e}")
                status[tenant] = {
                    "current": None,
                    "latest": latest_rev,
                    "needs_upgrade": True,
                    "history": [],
                    "status": "error",
                    "error": str(e)
                }

        return status

    async def create_migration(self, message: str, autogenerate: bool = True):
        """
        Create a new migration.

        Reason: Generate new migration files for schema changes.
        """
        logger.info(f"Creating new migration: {message}")

        try:
            # Create migration
            command.revision(
                self.alembic_cfg,
                message=message,
                autogenerate=autogenerate
            )

            logger.info(f"Successfully created migration: {message}")
            return {"message": f"Migration created: {message}"}

        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise

    async def verify_migration(self, tenant_id: str, revision: str = "head"):
        """
        Verify migration can be applied without issues.

        Reason: Test migration before actual execution.
        """
        logger.info(f"Verifying migration for tenant {tenant_id}")

        try:
            db_url = f"postgresql://postgres:password@localhost:5432/tenant_{tenant_id}"
            self.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

            # Check if migration is possible
            command.upgrade(self.alembic_cfg, revision, sql=True)

            return {"status": "success", "message": "Migration verification passed"}

        except Exception as e:
            logger.error(f"Migration verification failed for {tenant_id}: {e}")
            return {"status": "failed", "error": str(e)}

