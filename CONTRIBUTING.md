# Contributing to To The Moon

Thank you for your interest in contributing to To The Moon! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (for production testing)
- Git

### Development Setup
1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/To_The_Moon.git
   cd To_The_Moon
   ```

2. **Setup Environment**
   ```bash
   python3 -m pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Initialize Database**
   ```bash
   python3 -m alembic upgrade head
   ```

4. **Build Frontend** (optional)
   ```bash
   cd frontend && npm install && npm run build && cd -
   ```

5. **Run Development Server**
   ```bash
   make run
   ```

## 📋 Development Guidelines

### Code Standards

#### Python Backend
- **Formatting**: Use `black` for code formatting
- **Linting**: Use `ruff` for linting
- **Type Hints**: Use type hints for all function parameters and returns
- **Docstrings**: Use Google-style docstrings for classes and functions

```bash
# Format code
make format
# or: python3 -m black src

# Lint code  
make lint
# or: ruff check src
```

#### TypeScript Frontend
- **Formatting**: Use Prettier
- **Linting**: Use ESLint
- **Types**: Prefer explicit types over `any`
- **Components**: Use functional components with hooks

#### Database
- **Migrations**: Always use Alembic for schema changes
- **Models**: Use SQLAlchemy declarative models
- **Naming**: Use snake_case for table and column names

### Project Structure
```
src/
├── app/                    # FastAPI application layer
├── core/                   # Core utilities and configuration
├── domain/                 # Business logic (scoring, metrics, validation)
├── adapters/              # External integrations (DB, APIs)
├── scheduler/             # Background task scheduling
└── workers/               # Background workers
```

### Commit Guidelines
- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Keep commits atomic and focused
- Write clear, descriptive commit messages

Examples:
```
feat(scoring): add hybrid momentum model
fix(scheduler): resolve token grouping logic
docs(api): update endpoint documentation
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
make test
# or: pytest -q

# Run specific test file
pytest tests/test_scoring.py

# Run with coverage
pytest --cov=src tests/
```

### Test Guidelines
- Write tests for all new features
- Maintain >80% code coverage
- Use descriptive test names
- Mock external dependencies
- Test both success and error cases

### Test Structure
```
tests/
├── unit/                   # Unit tests
├── integration/           # Integration tests
├── fixtures/              # Test fixtures
└── conftest.py           # Pytest configuration
```

## 📝 Documentation

### Documentation Standards
- Update documentation for all new features
- Use clear, concise language
- Include code examples where helpful
- Keep documentation current with code changes

### Documentation Types
- **API Documentation**: Update `docs/API_REFERENCE.md` for new endpoints
- **Architecture**: Update `docs/ARCHITECTURE.md` for system changes
- **User Guides**: Update relevant guides for user-facing changes
- **Code Comments**: Use inline comments for complex logic

## 🔄 Pull Request Process

### Before Submitting
1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation

3. **Test Locally**
   ```bash
   make test
   make lint
   make format
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

### Pull Request Guidelines
- **Title**: Use descriptive title following conventional commit format
- **Description**: Explain what changes were made and why
- **Testing**: Describe how the changes were tested
- **Documentation**: Note any documentation updates
- **Breaking Changes**: Clearly mark any breaking changes

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Documentation
- [ ] Documentation updated
- [ ] API documentation updated (if applicable)
```

## 🐛 Bug Reports

### Before Reporting
1. Check existing issues
2. Reproduce the bug
3. Gather system information

### Bug Report Template
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS, Ubuntu]
- Python version: [e.g., 3.10.5]
- Node.js version: [e.g., 18.17.0]

## Additional Context
Any other relevant information
```

## 💡 Feature Requests

### Feature Request Template
```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this feature needed?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Other approaches that were considered

## Additional Context
Any other relevant information
```

## 🏗️ Architecture Guidelines

### Domain-Driven Design
- Keep business logic in the `domain/` layer
- Use adapters for external integrations
- Maintain clear separation of concerns

### API Design
- Follow RESTful conventions
- Use consistent response formats
- Include proper error handling
- Document all endpoints

### Database Design
- Use migrations for all schema changes
- Follow normalization principles
- Use appropriate indexes
- Consider performance implications

### Performance Considerations
- Profile code for performance bottlenecks
- Use appropriate caching strategies
- Optimize database queries
- Consider async operations for I/O

## 🔒 Security Guidelines

### Security Best Practices
- Validate all input data
- Use parameterized queries
- Implement proper error handling
- Follow principle of least privilege
- Keep dependencies updated

### Sensitive Data
- Never commit secrets or API keys
- Use environment variables for configuration
- Sanitize logs to remove sensitive information

## 📞 Getting Help

### Communication Channels
- **Issues**: GitHub Issues for bugs and feature requests
- **Discussions**: GitHub Discussions for questions and ideas
- **Code Review**: Pull request comments for code-specific discussions

### Response Times
- **Bug Reports**: We aim to respond within 48 hours
- **Feature Requests**: We aim to respond within 1 week
- **Pull Requests**: We aim to review within 3-5 business days

## 🎉 Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Project documentation

Thank you for contributing to To The Moon! 🚀