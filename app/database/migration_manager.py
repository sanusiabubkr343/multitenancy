# app/database/migration_manager.py
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import shutil
from typing import List, Dict
import json


class TenantMigrationManager:
    def __init__(self, master_session):
        self.master_session = master_session
        self.migrations_dir = "migrations/tenant"
        self.template_dir = "migrations/tenant/versions"

    def create_tenant_database(self, tenant_name: str, db_url: str):
        """Create a new tenant database"""
        from app.models.tenant_models import TenantBase

        # Extract database name from URL
        db_name = db_url.split("/")[-1]
        admin_url = db_url.rsplit("/", 1)[0] + "/postgres"

        # Create database
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            exists = result.fetchone() is not None

            if not exists:
                conn.execute(text(f"CREATE DATABASE {db_name}"))

        # Create tables in the new database using SQLAlchemy
        tenant_engine = create_engine(db_url)
        TenantBase.metadata.create_all(bind=tenant_engine)
        tenant_engine.dispose()

    def init_tenant_migrations(self, tenant_name: str, db_url: str):
        """Initialize alembic for a tenant"""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", self.migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Check if alembic is already initialized
        alembic_ini_path = os.path.join(self.migrations_dir, "alembic.ini")
        env_py_path = os.path.join(self.migrations_dir, "env.py")

        # Only initialize if not already set up
        if not os.path.exists(env_py_path):
            # Create versions directory if not exists
            os.makedirs(self.migrations_dir, exist_ok=True)
            os.makedirs(self.template_dir, exist_ok=True)

            command.init(alembic_cfg, directory=self.migrations_dir)

    def create_migration(self, message: str) -> str:
        """Create a new migration revision for tenants"""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", self.migrations_dir)

        # Create revision
        revision = command.revision(alembic_cfg, autogenerate=True, message=message)
        return str(revision)

    def migrate_tenant(self, tenant_name: str, db_url: str, revision: str = "head"):
        """Migrate a specific tenant"""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", self.migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        try:
            command.upgrade(alembic_cfg, revision)

            # Update tenant's current version in master DB
            from app.models.master_models import Tenant
            tenant = self.master_session.query(Tenant).filter(Tenant.name == tenant_name).first()
            if tenant:
                tenant.current_version = revision
                self.master_session.commit()

            return True, f"Tenant {tenant_name} migrated to {revision}"
        except Exception as e:
            return False, str(e)

    def migrate_all_tenants(self, revision: str = "head"):
        """Migrate all active tenants"""
        from app.models.master_models import Tenant

        tenants = self.master_session.query(Tenant).filter(Tenant.is_active == True).all()
        results = []

        for tenant in tenants:
            success, message = self.migrate_tenant(tenant.name, tenant.db_url, revision)
            results.append({
                "tenant": tenant.name,
                "success": success,
                "message": message
            })

        return results

    def get_migration_versions(self) -> List[Dict]:
        """Get all available migration versions"""
        versions_dir = f"{self.migrations_dir}/versions"
        versions = []

        if os.path.exists(versions_dir):
            for file in sorted(os.listdir(versions_dir)):
                if file.endswith(".py") and file != "__init__.py":
                    versions.append({
                        "file": file,
                        "revision": file.split("_")[0],
                        "description": "_".join(file.split("_")[1:]).replace(".py", "")
                    })

        return versions

    def downgrade_tenant(self, tenant_name: str, db_url: str, revision: str):
        """Downgrade a tenant to a specific version"""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", self.migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        try:
            command.downgrade(alembic_cfg, revision)

            # Update tenant's current version
            from app.models.master_models import Tenant
            tenant = self.master_session.query(Tenant).filter(Tenant.name == tenant_name).first()
            if tenant:
                tenant.current_version = revision
                self.master_session.commit()

            return True, f"Tenant {tenant_name} downgraded to {revision}"
        except Exception as e:
            return False, str(e)