# Multi-Tenant SaaS API

A robust FastAPI-based multi-tenant SaaS architecture utilizing a **database-per-tenant** strategy. This project provides complete data isolation, dynamic tenant creation, and shared master database for tenant management and authentication.

## 🚀 Features

- **Multi-Tenancy**: Database-per-tenant isolation using PostgreSQL.
- **Dynamic Tenant Management**: Create, list, and manage tenants through a dedicated API.
- **Migration System**: Integrated Alembic-based migration system that allows applying schema changes to all tenants or specific ones.
- **Security**: JWT-based authentication with support for Super Admins and regular users.
- **Middleware-driven Routing**: Automatically identifies the tenant based on the `X-Tenant-ID` header.
- **Consolidated Schemas**: All Pydantic models are organized in the `app/schemas` directory following best practices.

## 🏗️ Architecture

- **App**: FastAPI application.
- **Master Database**: Stores tenant metadata, global users (Super Admins), and tenant connection strings.
- **Tenant Databases**: Each tenant has its own isolated database for business data.
- **Middleware**: Intercepts requests to set up the correct database connection based on the tenant context.

## 📁 Project Structure

```text
.
├── app
│   ├── config.py             # Application settings (Environment variables)
│   ├── database              # Database connections and migration manager
│   ├── dependencies          # FastAPI dependencies (e.g., get_tenant_db)
│   ├── middleware            # Tenant identification middleware
│   ├── models                # SQLAlchemy models (Master and Tenant)
│   ├── routers               # API route handlers
│   ├── schemas               # Pydantic schemas (Consolidated)
│   │   ├── migration_schemas.py
│   │   ├── product_schemas.py
│   │   ├── tenant_schemas.py
│   │   └── user_schemas.py
│   ├── utils                 # Security and helper functions
│   └── main.py               # Application entry point
├── migrations                # Alembic migration environment
├── Dockerfile                # Containerization config
└── docker-compose.yml        # Multi-container orchestration
```

## 🛠️ Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables in `.env` (or use defaults in `app/config.py`).
4. Run the application:
   ```bash
   # Option 1: Direct run
   uvicorn app.main:app --reload

   # Option 2: Run via main script
   python app/main.py
   ```

## 🔌 API Usage

### Headers

Most tenant-specific endpoints require the following header:
- `X-Tenant-ID`: The ID of the tenant (e.g., `1`).

Authenticated endpoints require:
- `Authorization`: `Bearer <your_jwt_token>`

### Common Endpoints

- **Auth**:
  - `POST /api/auth/register`: Register a new user.
  - `POST /api/auth/login`: Login and receive a JWT token.
- **Tenants** (Super Admin Only):
  - `POST /api/tenants/`: Create a new tenant (and its database).
  - `GET /api/tenants/`: List all tenants.
- **Migrations** (Super Admin Only):
  - `POST /api/migrations/create`: Create a new migration revision.
  - `POST /api/migrations/migrate-all`: Apply pending migrations to all tenants.
- **Tenant Data**:
  - `GET /api/tenant/products`: List products for the current tenant.

## 🔄 Migration Workflow

1. Modify the models in `app/models/tenant_models.py`.
2. Generate a migration script:
   ```bash
   # Via API
   POST /api/migrations/create {"message": "add_description_to_products"}
   ```
3. Apply to tenants:
   ```bash
   # Via API
   POST /api/migrations/migrate-all
   ```

## 🛡️ Best Practices Applied

- **Separation of Concerns**: Decoupled models, schemas, and logic.
- **Pydantic V2**: Uses modern Pydantic patterns (e.g., `model_config`).
- **Standardized Responses**: Consistent API response models.
- **Dependency Injection**: Efficient database session management.
- **Automatic Documentation**: Enhanced Swagger/OpenAPI configuration with security schemes.
