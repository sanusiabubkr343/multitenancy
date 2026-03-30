# migrations/env.py
"""
Alembic migration environment configuration.

Reason: Support multi-tenant migrations with per-tenant version tracking.
"""
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine, text
from alembic import context
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
from app.models import user, product  # Import all models to register them

# Alembic Config object
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger(__name__)

# Set target metadata
target_metadata = Base.metadata


def get_tenant_databases():
    """Get list of all tenant databases."""
    try:
        tenant_engine = create_engine(str(settings.TENANT_DATABASE_URL))
        with tenant_engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM tenants WHERE is_active = true"))
            tenants = [row[0] for row in result]
            tenant_engine.dispose()
            return tenants
    except Exception as e:
        logger.error(f"Failed to get tenant databases: {e}")
        return []


def get_tenant_db_url(tenant_id: str) -> str:
    """Get database URL for a specific tenant."""
    return f"postgresql://postgres:password@localhost:5432/tenant_{tenant_id}"


def run_migrations_offline(tenant_id: str = None):
    """Run migrations in offline mode."""
    if tenant_id:
        tenants = [tenant_id]
    else:
        tenants = get_tenant_databases()

    if not tenants:
        logger.warning("No tenants found to migrate")
        return

    for tenant in tenants:
        logger.info(f"Running offline migrations for tenant: {tenant}")
        url = get_tenant_db_url(tenant)

        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            version_table=f"{tenant}_alembic_version",
            version_table_schema=None
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online(tenant_id: str = None):
    """Run migrations in online mode."""
    if tenant_id:
        tenants = [tenant_id]
    else:
        tenants = get_tenant_databases()

    if not tenants:
        logger.warning("No tenants found to migrate")
        return

    for tenant in tenants:
        logger.info(f"Running online migrations for tenant: {tenant}")
        url = get_tenant_db_url(tenant)

        # Create engine for this tenant
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = url

        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table=f"{tenant}_alembic_version",
                compare_type=True,
                compare_server_default=True
            )

            with context.begin_transaction():
                context.run_migrations()

        connectable.dispose()


# Determine mode and run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()