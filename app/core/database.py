# app/core/database.py
"""
Database management for multi-tenant architecture.

Reason:
- Centralized database connection management
- Connection pooling for performance
- Per-tenant engine caching
- Automatic tenant database creation/deletion
"""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Dict, Optional
import logging
from contextlib import contextmanager
from app.core.config import settings

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

# Cache for tenant database engines and sessions
_tenant_engines: Dict[str, create_engine] = {}
_tenant_session_factories: Dict[str, sessionmaker] = {}

# Tenant management database engine
tenant_mgmt_engine = create_engine(
    str(settings.TENANT_DATABASE_URL),
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG
)
TenantMgmtSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=tenant_mgmt_engine
)


def get_tenant_database_url(tenant_id: str) -> str:
    """
    Generate database URL for a specific tenant.

    Reason: Centralized URL generation ensures consistency across the application.
    """
    # Sanitize tenant_id to prevent SQL injection
    if not tenant_id.replace('-', '').replace('_', '').isalnum():
        raise ValueError(f"Invalid tenant_id format: {tenant_id}")

    # In production, you might want to read this from a configuration service
    # or have different databases on different hosts
    return f"postgresql://postgres:password@localhost:5432/tenant_{tenant_id}"


def get_tenant_engine(tenant_id: str) -> create_engine:
    """
    Get or create database engine for a tenant.

    Reason: Caching engines prevents connection pool exhaustion and
    improves performance by reusing connections.
    """
    if tenant_id not in _tenant_engines:
        logger.info(f"Creating database engine for tenant: {tenant_id}")

        db_url = get_tenant_database_url(tenant_id)

        try:
            engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,
                echo=settings.DEBUG
            )

            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            _tenant_engines[tenant_id] = engine
            _tenant_session_factories[tenant_id] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )

            logger.info(f"Successfully created engine for tenant: {tenant_id}")

        except Exception as e:
            logger.error(f"Failed to create engine for tenant {tenant_id}: {e}")
            raise

    return _tenant_engines[tenant_id]


def get_tenant_session(tenant_id: str) -> Session:
    """
    Get a database session for a tenant.

    Reason: Provides a clean session interface for tenant database operations.
    """
    if tenant_id not in _tenant_session_factories:
        get_tenant_engine(tenant_id)

    return _tenant_session_factories[tenant_id]()


@contextmanager
def get_tenant_session_context(tenant_id: str):
    """
    Context manager for tenant database sessions.

    Reason: Ensures proper session cleanup even if exceptions occur.
    """
    session = get_tenant_session(tenant_id)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tenant_database(tenant_id: str):
    """
    Create a new database for a tenant.

    Reason: Automates tenant provisioning and ensures database exists
    before tenant can use the system.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import ProgrammingError

    # Validate tenant_id
    if not tenant_id.replace('-', '').replace('_', '').isalnum():
        raise ValueError(f"Invalid tenant_id format: {tenant_id}")

    db_name = f"tenant_{tenant_id}"

    # Connect to default postgres database
    default_engine = create_engine(
        "postgresql://postgres:password@localhost:5432/postgres"
    )

    try:
        with default_engine.connect() as conn:
            # Terminate existing connections to the database
            conn.execute(text("COMMIT"))

            try:
                # Create database
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Created database {db_name}")
            except ProgrammingError as e:
                if "already exists" in str(e):
                    logger.info(f"Database {db_name} already exists")
                else:
                    raise

            # Grant privileges (customize as needed)
            conn.execute(text(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO postgres"))

    except Exception as e:
        logger.error(f"Failed to create database for tenant {tenant_id}: {e}")
        raise
    finally:
        default_engine.dispose()

    # Create tables for the new tenant
    tenant_engine = get_tenant_engine(tenant_id)
    Base.metadata.create_all(bind=tenant_engine)
    logger.info(f"Created tables for tenant: {tenant_id}")


def drop_tenant_database(tenant_id: str):
    """
    Drop a tenant's database.

    Reason: Complete tenant data removal for GDPR compliance or tenant deletion.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import ProgrammingError

    # Remove from cache
    if tenant_id in _tenant_engines:
        _tenant_engines[tenant_id].dispose()
        del _tenant_engines[tenant_id]
    if tenant_id in _tenant_session_factories:
        del _tenant_session_factories[tenant_id]

    db_name = f"tenant_{tenant_id}"

    # Connect to default postgres database
    default_engine = create_engine(
        "postgresql://postgres:password@localhost:5432/postgres"
    )

    try:
        with default_engine.connect() as conn:
            conn.execute(text("COMMIT"))

            # Terminate all connections to the database
            try:
                conn.execute(text(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{db_name}'
                """))
            except Exception:
                pass

            # Drop database
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            logger.info(f"Dropped database {db_name}")

    except Exception as e:
        logger.error(f"Failed to drop database for tenant {tenant_id}: {e}")
        raise
    finally:
        default_engine.dispose()


def cleanup_idle_connections():
    """
    Cleanup idle database connections.

    Reason: Prevent connection pool exhaustion in long-running applications.
    """
    for tenant_id, engine in _tenant_engines.items():
        try:
            engine.dispose()
            logger.debug(f"Cleaned up connections for tenant: {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup connections for tenant {tenant_id}: {e}")