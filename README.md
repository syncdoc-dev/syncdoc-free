# SyncDoc - Open Source

SyncDoc is an infrastructure-as-code (IaC) documentation tool that generates living documentation from your Terraform, Docker, and Ansible configurations. This is the open-source version of the SyncDoc application.

## Features

- **Live Infrastructure Documentation** - Auto-generated docs from your IaC
- **Multi-source Support** - Terraform, Docker, Ansible, CloudFormation
- **Search & Navigation** - Full-text search across your infrastructure
- **API-First Architecture** - FastAPI backend with REST API
- **Modern UI** - React + TypeScript frontend
- **Extensible** - Built with connectors pattern for custom sources

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local backend development)
- Node.js 20+ (for local frontend development)

### Run Locally with Docker Compose

The easiest way to run SyncDoc locally is with Docker Compose:

```bash
git clone https://github.com/syncdoc-dev/syncdoc-free.git
cd syncdoc-free

# Copy and configure the environment (optional)
cp .env.example .env

# Start all services
docker-compose up
```

The application will be available at:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Backend Development

For local backend development without Docker:

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload
```

### Frontend Development

For local frontend development:

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Configuration

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

### Optional: AI Features

To enable AI-powered features (documentation generation, analysis), add your LLM API key:

```env
LLM_PROVIDER=openai  # or "anthropic"
LLM_API_KEY=sk-your-openai-key-here
```

AI features are gracefully disabled if no API key is provided.

### Optional: GitHub OAuth

To enable GitHub OAuth login:

```env
GH_CLIENT_ID=your-github-oauth-app-id
GH_CLIENT_SECRET=your-github-oauth-app-secret
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/path/to/test_file.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm run test

# Run with coverage
npm run test:coverage
```

## Code Quality

### Backend

```bash
cd backend

# Lint with Ruff
ruff check .

# Format with Ruff
ruff format .

# Type check with MyPy
mypy app/
```

### Frontend

```bash
cd frontend

# Lint with ESLint
npm run lint

# Type check with TypeScript
npx tsc --noEmit
```

## Architecture

### Backend (Python/FastAPI)

- **`backend/app/api/`** - API endpoints and routers
- **`backend/app/models/`** - SQLAlchemy ORM models
- **`backend/app/schemas/`** - Pydantic request/response schemas
- **`backend/app/services/`** - Business logic layer
- **`backend/app/core/`** - Core utilities (config, database, security)
- **`backend/app/connectors/`** - IaC source connectors

### Frontend (React/TypeScript)

- **`frontend/src/pages/`** - Page components
- **`frontend/src/components/`** - Reusable React components
- **`frontend/src/api/`** - API client for backend communication
- **`frontend/src/types/`** - TypeScript type definitions

## Database

SyncDoc uses PostgreSQL with pgvector for embeddings:

- Default connection: `postgresql://syncdoc:syncdoc_dev@localhost/syncdoc`
- Migrations managed by Alembic (Python)

Running migrations:

```bash
cd backend

# Apply migrations
alembic upgrade head

# Revert migrations
alembic downgrade -1
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "Add my feature"`
3. Push branch: `git push origin feature/my-feature`
4. Open a Pull Request

### Code Style

- **Python**: Black (via Ruff), MyPy type hints required
- **TypeScript**: ESLint, strict type checking
- **Git Commits**: Present tense ("Add feature", not "Added feature")

## Documentation

- **Local Setup Troubleshooting**: See [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md)
- **Release Workflow**: See [docs/RELEASE_WORKFLOW.md](docs/RELEASE_WORKFLOW.md)
- **API Documentation**: Available at `/docs` when running the API
- **Architecture**: See source code comments and docstrings

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/syncdoc-dev/syncdoc-free/issues)
- **Discussions**: [Community discussions](https://github.com/syncdoc-dev/syncdoc-free/discussions)

## License

[See LICENSE file](LICENSE)

## Deployment

For production deployments, see the deployment guide in the private repository (for SyncDoc maintainers only).

## Troubleshooting

### Docker Compose Issues

```bash
# Rebuild images after code changes
docker-compose up --build

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Full reset (delete volumes)
docker-compose down -v
```

### Database Issues

```bash
# Reset database (deletes all data)
docker-compose down -v
docker-compose up -d

# Check database connection
docker-compose exec postgres pg_isready
```

### Port Conflicts

If ports 5173, 8000, 5432, or 6379 are already in use, update `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change from 8000 to 8001
```

## Performance Tips

- Use `docker-compose up --detach` to run in background
- Set `PYTHONUNBUFFERED=1` to see API logs in real-time
- Use `npm run dev` for frontend hot-reload
- Use `uvicorn --reload` for backend hot-reload

## Next Steps

- [Set up GitHub OAuth](docs/LOCAL_SETUP.md#github-oauth)
- [Add custom LLM integration](docs/LOCAL_SETUP.md#llm-setup)
- [Create your first connector](docs/LOCAL_SETUP.md#creating-connectors)
- [Deploy to production](../DEPLOYMENT.md) (private repository)

---

For deployment infrastructure and hosting, see the private SyncDoc repository.
