# Multi-Tenant FastAPI Application

A production-ready multi-tenant FastAPI application with separate databases per tenant and comprehensive migration support.

## Features

- **Complete Data Isolation**: Each tenant gets its own dedicated PostgreSQL database
- **Automatic Database Provisioning**: New databases created automatically when tenants register
- **Per-Tenant Migrations**: Independent migration management for each tenant
- **Connection Pooling**: Efficient database connection management
- **Tenant Middleware**: Automatic tenant identification from headers
