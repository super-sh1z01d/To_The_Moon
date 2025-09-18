# Development Guide

## Getting Started

### Prerequisites
- Python 3.10+ (developed on 3.9.6 with compatibility syntax)
- Node.js 18+ and npm
- PostgreSQL 14+ (optional, SQLite used for development)
- Git

### Development Setup

1. **Clone and setup environment:**
```bash
git clone https://github.com/super-sh1z01d/To_The_Moon.git
cd To_The_Moon
python3 -m pip install -r requirements.txt
cp .env.example .env
```

2. **Database setup:**
```bash
# Apply migrations (creates dev.db SQLite by default)
python3 -m alembic upgrade head

# Optional: Create test data
PYTHONPATH=. python3 scripts/smoke_db.py
PYTHONPATH=. python3 scripts/create_hybrid_test_data.py
```

3. **Frontend setup:**
```bash
cd frontend
npm install
npm run build
cd -
```

4. **Start development server:**
```bash
PYTHONPATH=. python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
```

5. **Access application:**
- Dashboard: http://localhost:8000/app
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Development Workflow

### Code Style
```bash
# Format code
python3 -m black src

# Lint code  
ruff check src

# Or use Makefile
make format
make lint
```

### Testing
```bash
# Run all tests
PYTHONPATH=. python3 -m pytest -v

# Run specific test file
PYTHONPATH=. python3 -m pytest tests/test_component_calculator.py -v

# Run with coverage
PYTHONPATH=. python3 -m pytest --cov=src tests/

# Or use Makefile
make test
```

### Database Operations
```bash
# Create new migration
python3 -m alembic revision -m "description" --autogenerate

# Apply migrations
python3 -m alembic upgrade head

# Rollback migration
python3 -m alembic downgrade -1

# View migration history
python3 -m alembic history
```

### Frontend Development
```bash
cd frontend

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

## Project Structure

### Backend Architecture
```
src/
├── app/                    # FastAPI application layer
│   ├── main.py            # App entry point, middleware
│   ├── routes/            # API endpoints
│   └── spa.py             # SPA serving
├── core/                  # Core utilities
│   ├── config.py          # Configuration management
│   └── json_logging.py    # Structured logging
├── domain/                # Business logic (pure)
│   ├── scoring/           # Scoring models
│   ├── metrics/           # Metrics aggregation
│   ├── settings/          # Settings management
│   └── validation/        # Data validation
├── adapters/              # External integrations
│   ├── db/               # Database layer
│   ├── repositories/     # Data access
│   └── services/         # External APIs
├── scheduler/            # Background tasks
└── workers/              # Background workers
```

### Frontend Architecture
```
frontend/src/
├── pages/                # Page components
│   ├── Dashboard.tsx     # Main dashboard
│   ├── Settings.tsx      # Settings page
│   ├── TokenDetail.tsx   # Token details
│   └── Logs.tsx          # Logs viewer
├── components/           # Reusable components
│   ├── ScoreCell.tsx     # Score visualization
│   ├── ComponentsCell.tsx # Component display
│   └── AgeCell.tsx       # Age with freshness
├── lib/                  # Utilities
│   ├── api.ts            # API client
│   └── scoring-utils.ts  # Scoring utilities
└── styles.css            # Global styles
```

## Development Guidelines

### Code Organization
- **Domain layer**: Pure business logic, no external dependencies
- **Adapter layer**: External integrations (APIs, database)
- **Application layer**: Orchestrates domain and adapters

### Naming Conventions
- **Python files**: snake_case (e.g., `token_scores.py`)
- **Classes**: PascalCase (e.g., `TokenRepository`)
- **Functions/variables**: snake_case (e.g., `update_metrics`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SCORE_THRESHOLD`)

### Import Organization
```python
# Standard library
import asyncio
from datetime import datetime

# Third-party
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Local application
from src.core.config import settings
from src.adapters.db.deps import get_db
```

### Error Handling
```python
# Use structured logging
import structlog
logger = structlog.get_logger(__name__)

try:
    result = risky_operation()
except SpecificError as e:
    logger.error("operation_failed", error=str(e), context={"key": "value"})
    raise HTTPException(status_code=400, detail="Operation failed")
```

### Database Patterns
```python
# Use repository pattern
class TokenRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_mint(self, mint: str) -> Optional[Token]:
        return self.db.query(Token).filter(Token.mint_address == mint).first()
```

## Testing Guidelines

### Unit Tests
```python
# Test file: tests/test_component_calculator.py
import pytest
from src.domain.scoring.component_calculator import ComponentCalculator

class TestComponentCalculator:
    def test_calculate_tx_accel_normal_case(self):
        result = ComponentCalculator.calculate_tx_accel(100, 1200)
        assert result == pytest.approx(1.0, rel=1e-3)
    
    def test_calculate_tx_accel_zero_hour_count(self):
        result = ComponentCalculator.calculate_tx_accel(100, 0)
        assert result == 0.0
```

### Integration Tests
```python
# Test API endpoints
def test_get_tokens(client):
    response = client.get("/tokens/?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 5
```

### Test Data Creation
```python
# Use factories for test data
def create_test_token(mint: str = "TestMint123") -> Token:
    return Token(
        mint_address=mint,
        name="Test Token",
        symbol="TEST",
        status="active"
    )
```

## Debugging

### Backend Debugging
```python
# Add debug logging
import structlog
logger = structlog.get_logger(__name__)

def debug_function():
    logger.debug("debug_info", variable=value, context={"key": "value"})
```

### Frontend Debugging
```typescript
// Use console.log for development
console.log('Debug info:', { variable, context });

// Use React DevTools for component debugging
// Install React Developer Tools browser extension
```

### Database Debugging
```bash
# Connect to SQLite dev database
sqlite3 dev.db

# View tables
.tables

# View schema
.schema token_scores

# Query data
SELECT * FROM token_scores LIMIT 5;
```

## Performance Optimization

### Backend Performance
```python
# Use async/await for I/O operations
async def fetch_external_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Use database indexes
class Token(Base):
    mint_address: Mapped[str] = mapped_column(String(44), unique=True, index=True)
```

### Frontend Performance
```typescript
// Use React.memo for expensive components
const ExpensiveComponent = React.memo(({ data }) => {
    return <div>{/* expensive rendering */}</div>;
});

// Use useMemo for expensive calculations
const expensiveValue = useMemo(() => {
    return expensiveCalculation(data);
}, [data]);
```

## Common Development Tasks

### Adding New API Endpoint
1. **Create route handler:**
```python
# src/app/routes/new_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.get("/")
async def get_new_feature():
    return {"message": "New feature"}
```

2. **Register router:**
```python
# src/app/main.py
from src.app.routes import new_feature

app.include_router(new_feature.router)
```

3. **Add tests:**
```python
# tests/test_new_feature.py
def test_get_new_feature(client):
    response = client.get("/new-feature/")
    assert response.status_code == 200
```

### Adding New Scoring Component
1. **Add calculation method:**
```python
# src/domain/scoring/component_calculator.py
@staticmethod
def calculate_new_component(param1: float, param2: float) -> float:
    """Calculate new scoring component."""
    if param2 == 0:
        return 0.0
    return min(param1 / param2, 1.0)
```

2. **Add to model:**
```python
# src/domain/scoring/hybrid_momentum_model.py
def calculate_components(self, metrics: dict) -> dict:
    components = {
        # ... existing components
        "new_component": ComponentCalculator.calculate_new_component(
            metrics.get("param1", 0),
            metrics.get("param2", 1)
        )
    }
    return components
```

3. **Update database model:**
```python
# Create migration
python3 -m alembic revision -m "add new component" --autogenerate
```

4. **Add tests:**
```python
# tests/test_component_calculator.py
def test_calculate_new_component(self):
    result = ComponentCalculator.calculate_new_component(10, 5)
    assert result == 2.0
```

### Adding New Frontend Component
1. **Create component:**
```typescript
// frontend/src/components/NewComponent.tsx
interface NewComponentProps {
    data: any;
}

export default function NewComponent({ data }: NewComponentProps) {
    return <div>{data.value}</div>;
}
```

2. **Add to page:**
```typescript
// frontend/src/pages/Dashboard.tsx
import NewComponent from '../components/NewComponent';

// In render:
<NewComponent data={item} />
```

3. **Add styles:**
```css
/* frontend/src/styles.css */
.new-component {
    /* styles */
}
```

## Deployment

### Development Deployment
```bash
# Quick development deployment
make run

# Or with custom settings
HOST=0.0.0.0 PORT=8001 make run
```

### Production Deployment
```bash
# Use deployment script
bash scripts/deploy.sh

# Or manual steps
git pull
pip install -r requirements.txt
python -m alembic upgrade head
cd frontend && npm ci && npm run build && cd -
systemctl restart tothemoon.service
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=.
python3 -m uvicorn src.app.main:app
```

#### Database Issues
```bash
# Reset database (development only)
rm dev.db
python3 -m alembic upgrade head
```

#### Frontend Build Issues
```bash
# Clear cache and rebuild
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

#### Port Already in Use
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

## Contributing

### Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Run tests: `make test`
5. Format code: `make format`
6. Commit changes: `git commit -m "Add new feature"`
7. Push branch: `git push origin feature/new-feature`
8. Create pull request

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed

## Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

### Tools
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [Pytest Testing](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Ruff Linter](https://docs.astral.sh/ruff/)

### Development Environment
- [VS Code Extensions](https://code.visualstudio.com/docs/python/python-tutorial)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [Node.js Version Management](https://github.com/nvm-sh/nvm)