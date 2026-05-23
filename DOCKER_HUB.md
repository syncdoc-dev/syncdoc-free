# SyncDoc Docker Images

Official Docker images for SyncDoc are available on [Docker Hub](https://hub.docker.com/r/syncdocdev/syncdoc).

## Images

| Image | Description |
|-------|-------------|
| `syncdocdev/syncdoc-api` | Backend API service (FastAPI) |
| `syncdocdev/syncdoc-frontend` | Frontend web application (React) |

## Supported Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent stable release |
| `vX.Y.Z` | Specific version (e.g., `v0.1.0`) |
| `dev` | Development build from main branch |

## Multi-Architecture Support

All images are multi-architecture and support:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/AArch64)

## Usage Examples

### Using Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: syncdoc
      POSTGRES_PASSWORD: syncdoc_dev
      POSTGRES_DB: syncdoc
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:8-alpine
    volumes:
      - redis_data:/data

  api:
    image: syncdocdev/syncdoc-api:latest
    environment:
      DATABASE_URL: postgresql+asyncpg://syncdoc:syncdoc_dev@postgres:5432/syncdoc
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: production
      # Add other required environment variables here
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

    frontend:
    image: syncdocdev/syncdoc-frontend:latest
    environment:
      VITE_API_URL: https://api.yourdomain.com
    ports:
      - "80:8080"
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

Then run:
```bash
docker-compose up -d
```

### Using Kubernetes

Create a deployment using the official images:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: syncdoc-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: syncdoc-api
  template:
    metadata:
      labels:
        app: syncdoc-api
    spec:
      containers:
      - name: api
        image: syncdocdev/syncdoc-api:latest
        env:
        - name: DATABASE_URL
          value: "postgresql+asyncpg://syncdoc:${POSTGRES_PASSWORD}@postgres:5432/syncdoc"
        - name: REDIS_URL
          value: "redis://:${REDIS_PASSWORD}@redis:6379/0"
        - name: ENVIRONMENT
          value: "production"
        ports:
        - containerPort: 8000
```

### Direct Docker Run

For quick testing:
```bash
# Start dependencies
docker run -d --name postgres -e POSTGRES_USER=syncdoc -e POSTGRES_PASSWORD=syncdoc_dev -e POSTGRES_DB=syncdoc pgvector/pgvector:pg16
docker run -d --name redis redis:8-alpine

# Start API
docker run -d --name syncdoc-api \
  -e DATABASE_URL=postgresql+asyncpg://syncdoc:syncdoc_dev@postgres:5432/syncdoc \
  -e REDIS_URL=redis://redis:6379/0 \
  -e ENVIRONMENT=production \
  -p 8000:8000 \
  --link postgres:postgres \
  --link redis:redis \
  syncdocdev/syncdoc-api:latest

# Start Frontend
docker run -d --name syncdoc-frontend \
  -e VITE_API_URL=http://localhost:8000 \
  -p 80:80 \
  --link syncdoc-api:syncdoc-api \
  syncdocdev/syncdoc-frontend:latest
```

## Environment Variables

Refer to [ENV_VARS.md](ENV_VARS.md) for a complete list of supported environment variables.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `REDIS_URL` | Redis connection URL | `redis://:password@host:6379/0` |
| `JWT_SECRET_KEY` | Secret for JWT tokens (change in production!) | `your-random-secret-key-here` |
| `VITE_API_URL` | Frontend: URL of the API backend | `https://api.yourdomain.com` |

### Optional Variables

See [ENV_VARS.md](ENV_VARS.md) for complete list including:
- Email configuration
- LLM/AI settings
- GitHub OAuth
- Monitoring and observability
- Storage providers
- Security settings

## Image Contents

### Backend API Image (`syncdocdev/syncdoc-api`)

Based on `python:3.12-slim`, includes:
- SyncDoc API application
- All Python dependencies
- Alembic for database migrations
- Health check endpoint at `/health`

### Frontend Image (`syncdocdev/syncdoc-frontend`)

Based on `nginx:alpine`, includes:
- Built React application
- Nginx configuration for serving static files
- Health check endpoint at `/`

## Updating Images

To update to the latest version:
```bash
docker-compose pull
docker-compose up -d
```

Or for specific versions:
```bash
# Update to version 0.1.0
docker-compose pull syncdoc-api syncdoc-frontend
docker-compose up -d
```

## Building Images Locally

If you need to build the images yourself:

```bash
# Build backend image
docker build -t syncdocdev/syncdoc-api:local -f backend/Dockerfile.prod backend/

# Build frontend image
docker build -t syncdocdev/syncdoc-frontend:local -f frontend/Dockerfile.prod frontend/
```

## Security Notes

1. **Always change** `JWT_SECRET_KEY` in production
2. Use **strong passwords** for PostgreSQL and Redis
3. Consider using **secrets management** for production deployments
4. Images are built as **non-root users** for security
5. Regularly **update** to get security patches

## Support

For issues with the Docker images:
- Check the [troubleshooting guide](docs/DEPLOYMENT.md#troubleshooting)
- Search [existing issues](https://github.com/syncdoc-dev/syncdoc-free/issues)
- Open a new issue if needed

## License

SyncDoc Docker images are licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) file for details.

---

*Last updated: March 15, 2025*