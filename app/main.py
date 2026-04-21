# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.middleware.tenant_middleware import TenantMiddleware
from app.database.master_db import init_master_db, SessionLocal
from app.routers import tenants, auth, migrations, tenant_data
from app.config import settings

# Initialize FastAPI with Swagger docs configuration
app = FastAPI(
    title="Multi-Tenant SaaS API",
    description="""
    ## Multi-Tenant SaaS Platform API

    This API provides multi-tenant functionality with separate databases per tenant.

    ### Features:
    * **Tenant Management**: Create and manage tenants
    * **Migration System**: Version-controlled database migrations per tenant
    * **Authentication**: JWT-based authentication
    * **Tenant Isolation**: Complete data isolation between tenants

    ### Headers Required:
    * `X-Tenant-ID`: Tenant identifier for tenant-specific endpoints
    * `Authorization`: Bearer token for authenticated endpoints

    ### Migration Workflow:
    1. Add column to tenant model
    2. Create migration: `POST /api/migrations/create`
    3. Migrate specific tenant: `POST /api/migrations/migrate-tenant/{tenant_id}`
    4. Or migrate all tenants: `POST /api/migrations/migrate-all`
    """,
    version="1.0.0",
    contact={
        "name": "Support Team",
        "email": "support@saas.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc UI
    openapi_url="/openapi.json"  # OpenAPI schema
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Tenant-ID", "X-Migration-Version"],
)

# Tenant middleware - must be added after CORS
app.add_middleware(TenantMiddleware)

# Include routers with tags and prefixes
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)
app.include_router(
    tenants.router,
    prefix="/api/tenants",
    tags=["Tenant Management"],
    responses={404: {"description": "Tenant not found"}}
)
app.include_router(
    migrations.router,
    prefix="/api/migrations",
    tags=["Migration Management"]
)
app.include_router(
    tenant_data.router,
    prefix="/api/tenant",
    tags=["Tenant Data Operations"]
)


# Custom OpenAPI schema to add security schemes
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"] = openapi_schema.get("components", {})
    # Note: BearerAuth is already added by OAuth2PasswordBearer in app/utils/security.py
    # TenantAuth is already added by APIKeyHeader in app/dependencies/tenant_db.py
    
    # Remove global security requirement to allow public endpoints like login/register
    if "security" in openapi_schema:
        del openapi_schema["security"]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.on_event("startup")
async def startup_event():
    """Initialize master database on startup"""
    try:
        init_master_db()
        print("✓ Master database initialized successfully")

        # Optional: Create default admin if not exists
        from app.database.master_db import SessionLocal
        from app.models.master_models import User
        from app.utils.security import get_password_hash

        db = SessionLocal()
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not admin:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_super_admin=True
            )
            db.add(admin_user)
            db.commit()
            print("✓ Default admin user created")
        db.close()

    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        raise e


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down...")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Multi-Tenant SaaS API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "auth": "/api/auth",
            "tenants": "/api/tenants",
            "migrations": "/api/migrations",
            "tenant_data": "/api/tenant"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": getattr(settings, 'ENVIRONMENT', 'development'),
        "database": "connected"
    }


# Optional: Add middleware to log requests
from fastapi import Request
import time


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)