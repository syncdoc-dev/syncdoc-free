# SyncDoc Environment Variables Reference

This document provides a comprehensive reference for all environment variables used by SyncDoc.

## Core Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `ENVIRONMENT` | Application environment (`development`, `staging`, `production`) | `development` | No | Backend |
| `DEBUG` | Enable debug mode | `false` | No | Backend |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `INFO` | No | Backend |

## Database Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `DATABASE_URL` | PostgreSQL connection string (SQLAlchemy format) | `postgresql+asyncpg://syncdoc:syncdoc_dev@localhost:5432/syncdoc` | Yes | Backend, Worker |
| `POSTGRES_USER` | PostgreSQL username (used by docker-compose) | `syncdoc` | No | Postgres Service |
| `POSTGRES_PASSWORD` | PostgreSQL password (used by docker-compose) | `syncdoc_dev` | No | Postgres Service |
| `POSTGRES_DB` | PostgreSQL database name (used by docker-compose) | `syncdoc` | No | Postgres Service |

## Redis Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` | Yes | Backend, Worker |

## Security Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `JWT_SECRET_KEY` | Secret key for JWT token generation | `change-me-in-production` | **Yes (in production)** | Backend, Worker |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration time in minutes | `30` | No | Backend |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiration time in days | `7` | No | Backend |
| `BCRYPT_ROUNDS` | Number of bcrypt rounds for password hashing | `12` | No | Backend |

## Application URLs

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `FRONTEND_URL` | Frontend application URL | `http://localhost:5173` | No | Backend |
| `BACKEND_URL` | Backend API URL | `http://localhost:8000` | No | Backend, Frontend |
| `VITE_API_URL` | Frontend Vite environment variable for API URL | `http://localhost:8000` | No | Frontend |

## User Registration & Authentication

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `ALLOW_SELF_REGISTER` | Whether to allow self-registration | `true` | No | Backend |
| `GH_CLIENT_ID` | GitHub OAuth Client ID | (empty) | No (for GitHub OAuth) | Backend |
| `GH_CLIENT_SECRET` | GitHub OAuth Client Secret | (empty) | No (for GitHub OAuth) | Backend |

## Email Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `EMAIL_ENABLED` | Whether email functionality is enabled | `false` | No | Backend |
| `EMAIL_PROVIDER` | Email provider (`smtp`, `sendgrid`, `mailgun`, `ses`) | `smtp` | No (if EMAIL_ENABLED=true) | Backend |
| `EMAIL_FROM_ADDRESS` | Sender email address | `no-reply@syncdoc.dev` | No (if EMAIL_ENABLED=true) | Backend |
| `EMAIL_FROM_NAME` | Sender name | `SyncDoc` | No (if EMAIL_ENABLED=true) | Backend |
| `EMAIL_REPLY_TO` | Reply-to email address | (empty) | No | Backend |
| `REGISTRATION_NOTIFY_TO` | Email address to notify on new registrations | (empty) | No | Backend |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Password reset token expiration in minutes | `60` | No | Backend |

### SMTP Specific Settings

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `SMTP_HOST` | SMTP server hostname | (empty) | Yes (if EMAIL_PROVIDER=smtp) | Backend |
| `SMTP_PORT` | SMTP server port | `587` | No (if EMAIL_PROVIDER=smtp) | Backend |
| `SMTP_USERNAME` | SMTP username | (empty) | No (if EMAIL_PROVIDER=smtp) | Backend |
| `SMTP_PASSWORD` | SMTP password | (empty) | No (if EMAIL_PROVIDER=smtp) | Backend |
| `SMTP_USE_TLS` | Whether to use TLS | `true` | No (if EMAIL_PROVIDER=smtp) | Backend |
| `SMTP_USE_SSL` | Whether to use SSL | `false` | No (if EMAIL_PROVIDER=smtp) | Backend |

## LLM (AI) Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `LLM_PROVIDER` | LLM provider (`openai`, `anthropic`) | `openai` | No | Backend, Worker |
| `LLM_API_KEY` | API key for LLM provider | (empty) | No (for AI features) | Backend, Worker |
| `LLM_MODEL` | LLM model to use | `gpt-4o` | No | Backend, Worker |
| `LLM_ENDPOINT_URL` | Custom endpoint URL for LLM (for self-hosted models) | (empty) | No | Backend, Worker |
| `LLM_MAX_TOKENS` | Maximum tokens for LLM responses | `2000` | No | Backend, Worker |
| `LLM_TEMPERATURE` | Temperature for LLM responses (0.0-1.0) | `0.7` | No | Backend, Worker |

## Monitoring & Observability

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `SENTRY_DSN` | Sentry DSN for error tracking | (empty) | No | Backend, Frontend |
| `SENTRY_ENVIRONMENT` | Sentry environment name | `development` | No | Backend, Frontend |
| `ENABLE_METRICS` | Whether to enable Prometheus metrics | `false` | No | Backend |
| `METRICS_PORT` | Port for Prometheus metrics endpoint | `9090` | No | Backend |

## Worker Configuration

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `CELERY_WORKER_CONCURRENCY` | Number of concurrent worker processes | `2` | No | Worker |
| `CELERY_TASK_ACKS_LATE` | Whether to acknowledge tasks after execution | `true` | No | Worker |
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | Number of tasks to prefetch per worker | `1` | No | Worker |
| `SLACK_WEBHOOK_URL` | Slack webhook URL for notifications | (empty) | No | Worker |

## File Storage

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `STORAGE_PROVIDER` | Storage provider (`local`, `s3`, `gcs`, `azure`) | `local` | No | Backend |
| `STORAGE_BUCKET` | Storage bucket/container name | `syncdoc-storage` | No (if not local) | Backend |
| `STORAGE_REGION` | Storage region (for cloud providers) | `us-east-1` | No (if not local) | Backend |
| `STORAGE_ACCESS_KEY` | Storage access key (for cloud providers) | (empty) | No (if not local) | Backend |
| `STORAGE_SECRET_KEY` | Storage secret key (for cloud providers) | (empty) | No (if not local) | Backend |
| `STORAGE_ENDPOINT_URL` | Custom endpoint URL (for S3-compatible services) | (empty) | No (if not local) | Backend |

## Advanced Features

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `ENABLE_WEBSOCKETS` | Whether to enable WebSocket connections | `true` | No | Backend |
| `WEBSOCKET_PING_INTERVAL` | WebSocket ping interval in seconds | `30` | No | Backend |
| `MAX_UPLOAD_SIZE` | Maximum file upload size in bytes | `10485760` (10MB) | No | Backend |
| `ALLOWED_IMPORT_FORMATS` | Comma-separated list of allowed import formats | `tf,yml,yaml,json,jsonnet` | No | Backend |
| `CACHE_TTL_DEFAULT` | Default cache TTL in seconds | `300` | No | Backend |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per minute per IP | `60` | No | Backend |

## Deployment Specific

| Variable | Description | Default | Required | Scope |
|----------|-------------|---------|----------|-------|
| `DOCKER_BUILD_PLATFORMS` | Docker build platforms (comma-separated) | `linux/amd64,linux/arm64` | No | CI/CD |
| `IMAGE_TAG` | Docker image tag | `latest` | No | CI/CD |
| `REGISTRY_URL` | Docker registry URL | `docker.io` | No | CI/CD |
| `REGISTRY_USERNAME` | Docker registry username | (empty) | No (for private registries) | CI/CD |
| `REGISTRY_PASSWORD` | Docker registry password | (empty) | No (for private registries) | CI/CD |

## Usage Examples

### Development (Docker Compose)
```bash
# Copy example file
cp .env.example .env

# Edit .env to customize settings
# Then start services
docker compose up
```

### Production Environment Variables
```bash
# Core
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Security (CRITICAL - change these!)
JWT_SECRET_KEY=your-super-secret-key-here-change-in-production
BCRYPT_ROUNDS=14

# Database (adjust for your setup)
DATABASE_URL=postgresql+asyncpg://syncdoc:secure-password@postgres-host:5432/syncdoc

# Redis
REDIS_URL=redis://redis-host:6379/0

# Email (if needed)
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
EMAIL_FROM_ADDRESS=no-reply@yourdomain.com
EMAIL_FROM_NAME=SyncDoc

# LLM (for AI features)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-api-key-here
LLM_MODEL=gpt-4o

# GitHub OAuth (optional)
GH_CLIENT_ID=your-github-oauth-client-id
GH_CLIENT_SECRET=your-github-oauth-client-secret
```

### Minimal Production Setup
```bash
# Absolute minimum for production
ENVIRONMENT=production
JWT_SECRET_KEY=generate-a-strong-random-key-here
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
REDIS_URL=redis://host:6379/0
```

## Security Notes

1. **Never commit real secrets** to version control
2. **Always change** `JWT_SECRET_KEY` in production
3. Use **strong, randomly generated** passwords for database and Redis
4. Consider using **secrets management** tools (HashiCorp Vault, AWS Secrets Manager, etc.)
5. Restrict **network access** to database and Redis services
6. Enable **HTTPS/TLS** in production deployments
7. Regularly **rotate** API keys and passwords

## Validation

The application validates critical environment variables on startup and will fail to start if required variables are missing or invalid.

For detailed validation rules, see the backend configuration modules in `backend/app/core/config.py`.