# Contributing to SyncDoc

Thank you for your interest in contributing to SyncDoc! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/syncdoc-dev/syncdoc/issues) first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment info (OS, Python version, etc.)

### Suggesting Enhancements

1. Check [discussions](https://github.com/syncdoc-dev/syncdoc/discussions) and existing issues
2. Create a discussion or issue describing:
   - Use case and motivation
   - Proposed solution (if any)
   - Alternatives considered

### Submitting Code Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests: `cd backend && pytest`
5. Commit with clear messages: `git commit -m "description of changes"`
6. Push to your fork
7. Create a Pull Request with:
   - Descriptive title
   - Summary of changes
   - Reference to related issues

## Development Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### Local Development

```bash
# Install dev dependencies
cd backend && pip install -e ".[dev]"

# Start services
docker-compose up

# Install pre-commit hooks if you use them locally
pre-commit install

# Run tests
pytest

# Format code
ruff format .
ruff check . --fix

# Type checking
mypy app/
```

## Code Standards

### Python Code

- Use Python 3.12+ features
- Follow PEP 8 (enforced by Black and Ruff)
- Type hints required for public APIs
- Add docstrings to modules, classes, and public functions

### Git Commits

- Write clear, descriptive commit messages
- Use present tense: "Add feature" not "Added feature"
- Reference issues when applicable: "Fix #123"
- Keep commits focused and atomic

### Testing

- Write tests for new features and bug fixes
- Target >80% code coverage
- Use `pytest` fixtures for setup
- Run full test suite before submitting PR

### Documentation

- Update README and relevant docs for new features
- Add API documentation comments
- Include examples when helpful

## Pull Request Process

1. Keep PRs focused (one feature per PR when possible)
2. Include tests for new code
3. Update documentation
4. Ensure CI passes (lint, tests, type checks)
5. Address reviewer feedback promptly
6. Aim for clear, concise commit history

## Project Structure

```
syncdoc/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers
│   │   ├── connectors/    # IaC source connectors
│   │   ├── core/          # Business logic
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── tasks/         # Celery tasks
│   ├── tests/
│   ├── alembic/           # Database migrations
│   └── pyproject.toml
├── frontend/              # React app (coming soon)
├── infra/                 # Deployment examples and infrastructure modules
└── docs/
    └── README.md
```

## Secrets and Private Data

Do not include real credentials, private hostnames, private IPs, Terraform state, `.env` files,
Doppler exports, Cloudflare tunnel credentials, SSH keys, OAuth secrets, SMTP passwords, GitHub
PATs, or LLM provider keys in issues, pull requests, logs, screenshots, fixtures, or Docker images.

Self-hosted SyncDoc uses bring-your-own LLM provider credentials. SyncDoc-operated LLM keys are only
for hosted SaaS infrastructure and must never be committed or distributed.

## Coding Conventions

### API Endpoints

- Use RESTful conventions
- Return appropriate HTTP status codes
- Include error responses in OpenAPI schema
- Version APIs if breaking changes needed

### Database Models

- Use snake_case for table and column names
- Include `created_at` and `updated_at` timestamps
- Add database indexes for frequently queried columns
- Write migrations for schema changes

### Async Code

- Use async/await consistently
- Don't mix sync and async code
- Test with `pytest-asyncio`

## Questions?

- Open a discussion in [GitHub Discussions](https://github.com/syncdoc-dev/syncdoc/discussions)
- Check [docs/](docs/) for public documentation
- Ask in issues if uncertain

---

Happy contributing!
