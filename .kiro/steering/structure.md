# Project Structure

## Architecture Overview

The project follows a clean architecture pattern with clear separation between domain logic, adapters, and application layers. The system is designed without Docker for simplicity, using direct Git deployment.

## Directory Structure

```
src/                    # Main application source code
├── app/               # FastAPI application layer
│   ├── main.py        # Application entry point
│   ├── routes/        # API route handlers
│   ├── logs_buffer.py # In-memory log buffer
│   └── spa.py         # SPA serving logic
├── core/              # Core utilities and configuration
│   ├── config.py      # Application configuration
│   └── json_logging.py # Structured logging setup
├── domain/            # Business logic and domain models
│   ├── metrics/       # Metrics aggregation logic
│   ├── scoring/       # Token scoring algorithms
│   ├── settings/      # Settings management
│   └── validation/    # Data validation rules
├── adapters/          # External integrations
│   ├── db/           # Database models and dependencies
│   ├── repositories/ # Data access layer
│   └── services/     # External API clients
├── scheduler/         # Background task scheduling
└── workers/          # Background workers (WebSocket, etc.)

frontend/              # React SPA
├── src/
│   ├── pages/        # React page components
│   ├── lib/          # Utility libraries
│   └── styles.css    # Global styles
└── dist/             # Built frontend assets

migrations/           # Alembic database migrations
scripts/             # Utility and deployment scripts
tests/               # Test files
```

## Key Architectural Principles

### Layer Separation
- **Domain Layer**: Pure business logic, no external dependencies
- **Adapter Layer**: Handles external integrations (APIs, database)
- **Application Layer**: Orchestrates domain and adapters, handles HTTP

### Database Architecture
- **Models**: SQLAlchemy declarative models in `src/adapters/db/models.py`
- **Repositories**: Data access patterns in `src/adapters/repositories/`
- **Migrations**: Alembic migrations in `migrations/versions/`

### API Structure
- RESTful endpoints following consistent naming
- Pydantic models for request/response validation
- Dependency injection for database sessions
- Structured error handling

### Background Processing
- **Scheduler**: APScheduler for periodic tasks (metrics updates, archival)
- **Workers**: Separate processes for long-running tasks (WebSocket connections)
- **Tasks**: Defined in `src/scheduler/tasks.py`

## File Naming Conventions

- **Python files**: snake_case (e.g., `token_scores.py`)
- **Classes**: PascalCase (e.g., `TokenRepository`)
- **Functions/variables**: snake_case (e.g., `update_metrics`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SCORE_THRESHOLD`)

## Import Organization

Follow this order:
1. Standard library imports
2. Third-party library imports  
3. Local application imports

Example:
```python
import asyncio
from datetime import datetime

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.adapters.db.deps import get_db
```

## Configuration Management

- Environment variables in `.env` files
- Pydantic Settings for type-safe configuration
- Database settings stored in `app_settings` table
- Runtime configuration through `src/core/config.py`

## Logging Structure

- JSON structured logs for production
- Contextual logging with trace IDs
- In-memory log buffer for UI display
- External API call logging with timing/status

## Testing Organization

- Unit tests: Fast, isolated tests for domain logic
- Integration tests: Database and external API interactions
- Utility scripts: `scripts/` directory for testing and diagnostics
- Test fixtures: Temporary databases with rollback