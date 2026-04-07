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
        # Extract database name from URL
        db_name = db_url.split("/")[-1]
        admin_url = db_url.rsplit("/", 1)[0] + "/postgres"

        engine = create_engine(admin_url)
        with engine.connect() as conn:
            conn.execute(text("commit"))
            conn.execute(f"CREATE DATABASE {db_name}")

        # Initialize alembic for tenant
        self.init_tenant_migrations(tenant_name, db_url)

        # Run initial migration
        self.migrate_tenant(tenant_name, db_url, "head")

    def init_tenant_migrations(self, tenant_name: str, db_url: str):
        """Initialize alembic for a tenant"""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", self.migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Create versions directory if not exists
        os.makedirs(self.migrations_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)

        # Generate alembic.ini for this tenant
        tenant_ini = f"alembic_{tenant_name}.ini"
        with open(tenant_ini, "w") as f:
            f.write(f"""
[alembic]
script_location = {self.migrations_dir}
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = {db_url}

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 88

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")

        command.init(alembic_cfg, directory=self.migrations_dir)

        # Generate initial migration
        command.revision(alembic_cfg, autogenerate=True, message="initial_migration")
        command.upgrade(alembic_cfg, "head")

        # Clean up
        os.remove(tenant_ini)

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