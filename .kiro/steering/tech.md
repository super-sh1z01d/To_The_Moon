# Technology Stack

## Backend
- **Python 3.10+** - Main backend language
- **FastAPI** - Web framework for REST API
- **SQLAlchemy 2.x** - ORM with declarative models
- **Alembic** - Database migrations
- **Pydantic v2** - Data validation and settings management
- **APScheduler** - Background task scheduling
- **uvicorn** - ASGI server
- **httpx** - Async HTTP client for external APIs
- **websockets** - WebSocket client for Pump.fun integration

## Frontend
- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **React Router DOM** - Client-side routing

## Database
- **PostgreSQL 14+** - Production database
- **SQLite** - Development database (dev.db)

## Development Tools
- **black** - Code formatting
- **ruff** - Linting
- **pytest** - Testing framework

## Common Commands

### Development Setup
```bash
# Install Python dependencies
python3 -m pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run database migrations
python3 -m alembic upgrade head

# Build frontend
cd frontend && npm install && npm run build && cd -
```

### Running the Application
```bash
# Start development server
PYTHONPATH=. python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000

# Or use Makefile
make run

# Run WebSocket worker (separate process)
PUMPFUN_RUN_SECONDS=120 PYTHONPATH=. python3 -m src.workers.pumpfun_ws
```

### Development Utilities
```bash
# Format code
make format
# or: python3 -m black src

# Lint code
make lint
# or: ruff check src

# Run tests
make test
# or: pytest -q

# Populate test data
PYTHONPATH=. python3 scripts/smoke_db.py
PYTHONPATH=. python3 scripts/dev_mark_active.py
PYTHONPATH=. python3 scripts/update_metrics.py --limit 1
```

### Database Operations
```bash
# Create new migration
python3 -m alembic revision -m "description" --autogenerate

# Apply migrations
python3 -m alembic upgrade head
```

### Production Deployment
```bash
# Quick deploy script
bash scripts/deploy.sh

# One-command server setup
sudo bash scripts/install.sh
```

## Environment Variables
Key variables in `.env`:
- `APP_ENV` - dev/stage/prod
- `LOG_LEVEL` - INFO/DEBUG
- `DATABASE_URL` - Database connection string
- `FRONTEND_DIST_PATH` - Path to built frontend assets
- `SCHEDULER_ENABLED` - Enable background tasks