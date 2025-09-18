# Development Guide

Comprehensive guide for developers working on the To The Moon project.

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and npm
- **PostgreSQL 14+** (production) or SQLite (development)
- **Git**

### Development Setup

```bash
# Clone repository
git clone https://github.com/super-sh1z01d/To_The_Moon.git
cd To_The_Moon

# Setup Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your development settings

# Initialize database
python3 -m alembic upgrade head

# Build frontend (optional)
cd frontend && npm install && npm run build && cd -

# Start development server
make run
# or: PYTHONPATH=. python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Development URLs
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Scheduler Health**: http://localhost:8000/health/scheduler

### Production URLs
- **Dashboard**: https://tothemoon.sh1z01d.ru
- **API Docs**: https://tothemoon.sh1z01d.ru/docs
- **Health Check**: https://tothemoon.sh1z01d.ru/health
- **NotArb API**: https://tothemoon.sh1z01d.ru/notarb/pools

## 🏗️ Project Structure

### Backend Architecture
```
src/
├── app/                    # FastAPI Application Layer
│   ├── main.py            # Application entry point
│   ├── routes/            # API route handlers
│   │   ├── tokens.py      # Token operations
│   │   ├── meta.py        # Health & system endpoints
│   │   ├── settings.py    # Configuration management
│   │   ├── admin.py       # Admin operations
│   │   └── logs.py        # Logging endpoints
│   ├── logs_buffer.py     # In-memory log buffer
│   └── spa.py             # SPA serving logic
├── core/                  # Core Utilities
│   ├── config.py          # Application configuration
│   └── json_logging.py    # Structured logging setup
├── domain/                # Business Logic (Domain Layer)
│   ├── scoring/           # Scoring Models & Services
│   │   ├── scoring_service.py      # Unified scoring interface
│   │   ├── hybrid_momentum_model.py # Advanced scoring model
│   │   ├── component_calculator.py # Component calculations
│   │   ├── ewma_service.py         # EWMA smoothing service
│   │   └── scorer.py               # Legacy scoring logic
│   ├── metrics/           # Metrics Collection & Aggregation
│   │   ├── dex_aggregator.py       # DEX data aggregation
│   │   └── enhanced_dex_aggregator.py # Enhanced metrics
│   ├── validation/        # Data Quality & Validation
│   │   ├── data_filters.py         # Data quality validation
│   │   ├── dex_rules.py           # DEX-specific validation
│   │   └── quality_settings.py    # Quality configuration
│   └── settings/          # Settings Management
│       └── service.py             # Settings service
├── adapters/              # External Integration Layer
│   ├── db/               # Database Layer
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── base.py       # Database configuration
│   │   └── deps.py       # Database dependencies
│   ├── repositories/     # Data Access Layer
│   │   └── tokens_repo.py # Token repository
│   └── services/         # External API Clients
│       └── dexscreener_client.py # DexScreener integration
├── scheduler/            # Background Task Processing
│   ├── service.py        # APScheduler configuration
│   ├── monitoring.py     # Health monitoring
│   ├── fallback_handler.py # Fallback mechanisms
│   └── tasks.py          # Background task definitions
└── workers/              # Background Workers
    └── pumpfun_ws.py     # WebSocket worker for Pump.fun
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/       # Reusable React components
│   ├── pages/           # Page components
│   ├── lib/             # Utilities and API client
│   ├── hooks/           # Custom React hooks
│   └── types/           # TypeScript type definitions
├── public/              # Static assets
├── dist/                # Built assets (generated)
└── package.json         # Frontend dependencies
```

## 🛠️ Development Workflow

### Code Style & Standards

#### Python Code Style
- **Formatter**: Black (line length: 88)
- **Linter**: Ruff with strict settings
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style for classes and complex functions

```bash
# Format code
make format
# or: python3 -m black src

# Lint code
make lint
# or: ruff check src

# Type checking (optional)
mypy src
```

#### Import Organization
Follow this order:
1. Standard library imports
2. Third-party library imports  
3. Local application imports

```python
import asyncio
from datetime import datetime

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.adapters.db.deps import get_db
```

#### Naming Conventions
- **Files**: snake_case (e.g., `token_scores.py`)
- **Classes**: PascalCase (e.g., `TokenRepository`)
- **Functions/variables**: snake_case (e.g., `update_metrics`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SCORE_THRESHOLD`)

### Git Workflow

#### Branch Strategy
- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/**: Feature branches (`feature/new-scoring-model`)
- **hotfix/**: Critical fixes (`hotfix/fix-scheduler-crash`)

#### Commit Messages
Follow conventional commits:
```
feat: add hybrid momentum scoring model
fix: resolve scheduler memory leak
docs: update API documentation
refactor: simplify token validation logic
test: add integration tests for scoring
```

#### Pull Request Process
1. Create feature branch from `develop`
2. Implement changes with tests
3. Update documentation if needed
4. Run full test suite
5. Create PR with clear description
6. Address review feedback
7. Merge to `develop` after approval

### Testing Strategy

#### Test Structure
```
tests/
├── unit/               # Fast, isolated tests
│   ├── domain/        # Business logic tests
│   ├── adapters/      # Integration tests
│   └── app/           # API endpoint tests
├── integration/       # End-to-end tests
├── fixtures/          # Test data and utilities
└── conftest.py        # Pytest configuration
```

#### Running Tests
```bash
# Run all tests
make test
# or: pytest -q

# Run specific test file
pytest tests/unit/domain/test_scoring.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run integration tests only
pytest tests/integration/ -v
```

#### Test Guidelines
- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions
- **Fixtures**: Use pytest fixtures for test data
- **Mocking**: Mock external APIs and database calls
- **Coverage**: Aim for >80% code coverage

### Database Development

#### Migration Workflow
```bash
# Create new migration
python3 -m alembic revision -m "add token scoring history" --autogenerate

# Review generated migration
# Edit migration file if needed

# Apply migration
python3 -m alembic upgrade head

# Rollback if needed
python3 -m alembic downgrade -1
```

#### Database Guidelines
- **Models**: Use SQLAlchemy declarative models
- **Relationships**: Define clear foreign key relationships
- **Indexes**: Add indexes for query performance
- **Constraints**: Use database constraints for data integrity
- **Migrations**: Always review auto-generated migrations

#### Development Data
```bash
# Populate test data
PYTHONPATH=. python3 scripts/smoke_db.py

# Mark tokens as active for testing
PYTHONPATH=. python3 scripts/dev_mark_active.py

# Update metrics for testing
PYTHONPATH=. python3 scripts/update_metrics.py --limit 5
```

### API Development

#### FastAPI Guidelines
- **Route Organization**: Group related endpoints in separate files
- **Dependency Injection**: Use FastAPI dependencies for common logic
- **Pydantic Models**: Define request/response models
- **Error Handling**: Use consistent error response format
- **Documentation**: Add docstrings and examples

#### API Testing
```bash
# Start development server
make run

# Test endpoints manually
curl http://localhost:8000/health
curl http://localhost:8000/tokens/?limit=5

# Use interactive docs
open http://localhost:8000/docs
```

### Frontend Development

#### React Development
```bash
# Install dependencies
cd frontend && npm install

# Start development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

#### Frontend Guidelines
- **Components**: Create reusable, typed components
- **State Management**: Use React hooks and context
- **API Integration**: Use custom hooks for API calls
- **Styling**: Use CSS modules or styled-components
- **TypeScript**: Strict type checking enabled

### Background Services

#### Scheduler Development
```bash
# Run scheduler in development
SCHEDULER_ENABLED=true make run

# Test specific tasks
PYTHONPATH=. python3 -c "
from src.scheduler.tasks import update_all_tokens
update_all_tokens()
"

# Monitor scheduler health
curl http://localhost:8000/health/scheduler
```

#### WebSocket Worker
```bash
# Run WebSocket worker
PUMPFUN_RUN_SECONDS=60 PYTHONPATH=. python3 -m src.workers.pumpfun_ws

# Test with limited runtime for development
PUMPFUN_RUN_SECONDS=30 python3 -m src.workers.pumpfun_ws
```

## 🔧 Configuration Management

### Environment Variables

#### Development (.env)
```bash
# Application
APP_ENV=dev
LOG_LEVEL=DEBUG
PYTHONPATH=.

# Database
DATABASE_URL=sqlite:///dev.db

# Features
SCHEDULER_ENABLED=true
FRONTEND_DIST_PATH=frontend/dist

# External APIs
DEXSCREENER_BASE_URL=https://api.dexscreener.com
DEXSCREENER_RATE_LIMIT=2.0

# WebSocket
PUMPFUN_WS_URL=wss://pumpportal.fun/api/data
PUMPFUN_RUN_SECONDS=3600
```

#### Production Environment
```bash
# Application
APP_ENV=prod
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost/tothemoon

# Security
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=your-domain.com

# Performance
WORKERS=4
MAX_CONNECTIONS=100
```

### Settings Management
- **Database Settings**: Stored in `app_settings` table
- **Environment Variables**: System configuration
- **Runtime Settings**: Configurable via API
- **Default Values**: Defined in domain models

## 🐛 Debugging & Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database status
python3 -c "
from src.adapters.db.base import engine
print(engine.execute('SELECT 1').scalar())
"

# Reset database
rm dev.db
python3 -m alembic upgrade head
```

#### Scheduler Not Running
```bash
# Check scheduler status
curl http://localhost:8000/health/scheduler

# Enable scheduler
export SCHEDULER_ENABLED=true

# Check logs
curl http://localhost:8000/logs?logger=scheduler&limit=20
```

#### External API Issues
```bash
# Test DexScreener API
curl "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"

# Check rate limiting
curl http://localhost:8000/logs?search=rate_limit&limit=10
```

### Logging & Monitoring

#### Log Levels
- **DEBUG**: Detailed execution information
- **INFO**: General operational messages
- **WARNING**: Potential issues or degraded performance
- **ERROR**: Error conditions that need attention

#### Structured Logging
```python
import logging
from src.core.json_logging import get_logger

logger = get_logger(__name__)

# Log with context
logger.info("Token updated", extra={
    "mint": token.mint_address,
    "score": token.score,
    "model": "hybrid_momentum"
})
```

#### Monitoring Endpoints
```bash
# System health
curl http://localhost:8000/health

# Scheduler health with diagnostics
curl http://localhost:8000/health/scheduler

# Recent logs
curl http://localhost:8000/logs?level=ERROR&limit=10

# Application metrics
curl http://localhost:8000/tokens/?limit=1  # Check response time
```

### Performance Optimization

#### Database Performance
- **Indexes**: Add indexes for frequently queried columns
- **Query Optimization**: Use SQLAlchemy query profiling
- **Connection Pooling**: Configure appropriate pool sizes
- **Batch Operations**: Use bulk operations for large datasets

#### API Performance
- **Caching**: Implement response caching for expensive operations
- **Pagination**: Use efficient pagination for large result sets
- **Async Operations**: Use async/await for I/O operations
- **Rate Limiting**: Implement rate limiting for external APIs

#### Memory Management
- **Object Lifecycle**: Monitor object creation/destruction
- **Memory Leaks**: Use memory profiling tools
- **Garbage Collection**: Monitor GC performance
- **Resource Cleanup**: Ensure proper cleanup of resources

## 🚀 Deployment

### Development Deployment
```bash
# Quick development setup
make setup-dev

# Run with auto-reload
make run-dev

# Run all services
make run-all
```

### Production Deployment
```bash
# Production setup
sudo bash scripts/install.sh

# Deploy updates
bash scripts/deploy.sh

# Service management
sudo systemctl status tothemoon
sudo systemctl restart tothemoon
```

## 📚 Additional Resources

### Documentation
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Architecture Guide](ARCHITECTURE.md)** - System design and data flow
- **[Scoring Model](SCORING_MODEL.md)** - Hybrid momentum scoring details
- **[Deployment Guide](DEPLOYMENT.md)** - Production setup and configuration

### External Resources
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)**
- **[SQLAlchemy Documentation](https://docs.sqlalchemy.org/)**
- **[React Documentation](https://react.dev/)**
- **[Alembic Documentation](https://alembic.sqlalchemy.org/)**

### Development Tools
- **[Postman Collection](../postman/)** - API testing collection
- **[VS Code Settings](../.vscode/)** - Recommended IDE configuration
- **[Docker Compose](../docker-compose.dev.yml)** - Development containers (optional)

## 🤝 Contributing

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Set up development environment
4. Make your changes
5. Add tests for new functionality
6. Update documentation
7. Submit a pull request

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass and coverage is maintained
- [ ] Documentation is updated
- [ ] No breaking changes without migration path
- [ ] Performance impact is considered
- [ ] Security implications are reviewed

### Release Process
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Deploy to staging
6. Create GitHub release
7. Deploy to production

For detailed contributing guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).