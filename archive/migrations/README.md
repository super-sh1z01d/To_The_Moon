# Migration Guides Archive

This directory contains historical migration guides for older versions of the To The Moon system.

## 📋 Migration Files

- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migration guide for version 2.0 transition

## ⚠️ Important Notes

### Current Migration Information
For current database migrations, use:
```bash
# Apply current migrations
python3 -m alembic upgrade head

# Create new migration
python3 -m alembic revision -m "description" --autogenerate
```

### Historical Context
The migration guides in this archive were created for:
- Major version transitions
- Breaking changes in older versions
- Legacy system upgrades

### Superseded Information
- **Database Migrations**: Now handled by Alembic (see [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md))
- **Configuration Changes**: See current [README.md](../../README.md#configuration)
- **API Changes**: See [CHANGELOG.md](../../CHANGELOG.md)

## 🔗 Current Documentation

For current migration and upgrade procedures:
- **[Deployment Guide](../../docs/DEPLOYMENT.md)** - Production deployment and updates
- **[Development Guide](../../docs/DEVELOPMENT.md)** - Database migrations and development setup
- **[Changelog](../../CHANGELOG.md)** - Version history and breaking changes