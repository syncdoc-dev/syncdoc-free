# Deployment Guide

This guide covers various deployment options for SyncDoc, from simple local setups to production-grade deployments.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Compose Production](#docker-compose-production)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Manual Installation](#manual-installation)
5. [Hetzner VM Deployment](#hetzner-vm-deployment)
6. [Upgrading SyncDoc](#upgrading-syncdoc)
7. [Backup and Recovery](#backup-and-recovery)
8. [Monitoring and Logging](#monitoring-and-logging)

## Local Development

For development purposes, the easiest way to run SyncDoc is with Docker Compose:

```bash
git clone https://github.com/syncdoc-dev/syncdoc-free.git
cd syncdoc-free
cp .env.example .env
# Edit .env as needed
docker-compose up
```

This will start:
- API: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

## Docker Compose Production

For production deployments using Docker Compose, use the production-specific configuration:

```bash
# Copy production environment example
cp .env.example .env.production
# Edit .env.production with your production settings
docker-compose -f docker-compose.prod.yml up -d
```

### Production Docker Compose File (`docker-compose.prod.yml`)

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-syncdoc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-}
      POSTGRES_DB: ${POSTGRES_DB:-syncdoc}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-syncdoc} -d ${POSTGRES_DB:-syncdoc}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD:-}
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD:-}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-p", "6379", "-a", "${REDIS_PASSWORD:-}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

    api:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
      platforms:
        - linux/amd64
        - linux/arm64
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-syncdoc}:${POSTGRES_PASSWORD:-}@postgres:5432/${POSTGRES_DB:-syncdoc}
      REDIS_URL: redis://:${REDIS_PASSWORD:-}@redis:6379/0
      ENVIRONMENT: production
      PYTHONUNBUFFERED: "1"
      # Add other production environment variables here
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
      platforms:
        - linux/amd64
        - linux/arm64
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-syncdoc}:${POSTGRES_PASSWORD:-}@postgres:5432/${POSTGRES_DB:-syncdoc}
      REDIS_URL: redis://:${REDIS_PASSWORD:-}@redis:6379/0
      ENVIRONMENT: production
      PYTHONUNBUFFERED: "1"
      # Add other production environment variables here from .env or ENV_VARS.md
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: celery -A app.celery_app worker --loglevel=info

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    environment:
      VITE_API_URL: https://your-domain.com  # Set to your actual domain
    ports:
      - "80:8080"  # Serving on port 8080 via nginx in container
    depends_on:
      api:
        condition: service_started
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Production Dockerfile (`backend/Dockerfile.prod`)

```dockerfile
# Use multi-stage build for smaller images
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install --no-cache-dir -e ".[dev]"

# Production stage
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/pyproject.toml backend/alembic.ini ./

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Dockerfile (`frontend/Dockerfile.prod`)

```dockerfile
# Build stage
FROM node:24-alpine as builder

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy source code
COPY frontend/ .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

## Kubernetes Deployment

For Kubernetes deployments, you can use the provided Helm chart or Kubernetes manifests.

### Helm Chart (in `infra/helm/syncdoc/`)

```bash
# Add Helm repository (if needed)
helm repo add syncdoc https://syncdoc-dev.github.io/syncdoc-helm-charts
helm repo update

# Install SyncDoc
helm install syncdoc syncdoc/syncdoc \
  --namespace syncdoc --create-namespace \
  -f values-production.yaml
```

### Manual Kubernetes Manifests

See `infra/kubernetes/` for complete manifests including:
- Deployments for API, Worker, Frontend
- Services for internal communication
- Ingress rules for external access
- PersistentVolumeClaims for PostgreSQL and Redis
- ConfigMaps and Secrets for configuration

## Manual Installation

For bare metal or VM installations without containers:

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 14+ with pgvector extension
- Redis 6+
- Git

### Backend Installation

```bash
# Clone repository
git clone https://github.com/syncdoc-dev/syncdoc-free.git
cd syncdoc-free/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp ../.env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start services
# In one terminal:
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal:
celery -A app.celery_app worker --loglevel=info
```

### Frontend Installation

```bash
cd ../frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your settings

# Build for production
npm run build

# Serve with your preferred web server (nginx, apache, etc.)
# Or use the dev server for testing:
npm run preview
```

## Hetzner VM Deployment

For deploying SyncDoc on Hetzner Cloud or dedicated servers:

### Step 1: Provision Hetzner Resources

1. **Create a Cloud Server** (CX21 or larger recommended)
   - OS: Ubuntu 22.04 LTS
   - Location: Choose nearest to your users
   - Enable: Private Network, Backups, Monitoring

2. **Set up Firewall**
   - Allow SSH (port 22) from your IP
   - Allow HTTP (80) and HTTPS (443) from anywhere
   - Allow PostgreSQL (5432) and Redis (6379) from private network only

3. **Create Volumes** (optional but recommended)
   - Create separate volumes for PostgreSQL and Redis data
   - Attach to your server

### Step 2: Initial Server Setup

```bash
# Connect via SSH
ssh root@your-hetzner-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    ufw \
    fail2ban \
    postgresql-14 \
    postgresql-client-14 \
    postgresql-contrib-14 \
    redis-server \
    nginx \
    python3.12 \
    python3.12-venv \
    python3.12-pip \
    nodejs \
    npm

# Enable pgvector extension for PostgreSQL
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Configure PostgreSQL
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'strong-postgres-password';"
sudo -u postgres psql -c "CREATE USER syncdoc WITH PASSWORD 'strong-syncdoc-password';"
sudo -u postgres psql -c "CREATE DATABASE syncdoc OWNER syncdoc;"

# Configure Redis
sed -i 's/^# requirepass .*/requirepass strong-redis-password/' /etc/redis/redis.conf
systemctl restart redis

# Configure UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw enable
```

### Step 3: Deploy SyncDoc

```bash
# Create syncdoc user
adduser --disabled-password --gecos "" syncdoc
usermod -aG sudo syncdoc

# Switch to syncdoc user
su - syncdoc

# Clone repository
git clone https://github.com/syncdoc-dev/syncdoc-free.git
cd syncdoc-free

# Set up backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Configure environment
cp ../../.env.example .env
# Edit .env with your settings:
#   DATABASE_URL=postgresql+asyncpg://syncdoc:strong-syncdoc-password@localhost:5432/syncdoc
#   REDIS_URL=redis://:strong-redis-password@localhost:6379/0
#   JWT_SECRET_KEY=your-generated-secret-key
#   ENVIRONMENT=production

# Run migrations
alembic upgrade head

# Set up frontend
cd ../frontend
npm install
npm run build

# Set up systemd services
cd ..
sudo cp infra/systemd/syncdoc-api.service /etc/systemd/system/
sudo cp infra/systemd/syncdoc-worker.service /etc/systemd/system/
sudo cp infra/systemd/syncdoc-frontend.service /etc/systemd/system/

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable syncdoc-api syncdoc-worker syncdoc-frontend
sudo systemctl start syncdoc-api syncdoc-worker syncdoc-frontend

# Set up nginx as reverse proxy
sudo cp infra/nginx/syncdoc.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/syncdoc.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Optional: Set up SSL with Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Step 4: Monitoring and Maintenance

1. **Log Monitoring**
   ```bash
   # View application logs
   journalctl -u syncdoc-api -f
   journalctl -u syncdoc-worker -f
   
   # View nginx logs
   tail -f /var/log/nginx/access.log
   tail -f /var/log/nginx/error.log
   ```

2. **Database Maintenance**
   ```bash
   # Regular vacuuming (add to cron)
   sudo -u postgres vacuumdb --all --analyze-in-stages
   
   # Backup (add to cron)
   sudo -u postgres pg_dump syncdoc > /backups/syncdoc-$(date +%Y%m%d).sql
   ```

3. **Application Updates**
   ```bash
   # As syncdoc user
   cd /home/syncdoc/syncdoc-free
   git pull
   
   # Backend updates
   cd backend
   source venv/bin/activate
   pip install -e ".[dev]" --upgrade
   alembic upgrade head
   
   # Frontend updates
   cd ../frontend
   npm ci
   npm run build
   
   # Restart services
   sudo systemctl restart syncdoc-api syncdoc-worker
   ```

## Upgrading SyncDoc

### Minor/Patch Version Upgrades

```bash
# Pull latest changes
git pull

# Backend upgrades
cd backend
source venv/bin/activate
pip install -e ".[dev]" --upgrade
alembic upgrade head

# Frontend upgrades
cd ../frontend
npm ci
npm run build

# Restart services
# Docker Compose:
docker-compose pull && docker-compose up -d --build

# Systemd:
sudo systemctl restart syncdoc-api syncdoc-worker

# Kubernetes:
helm upgrade syncdoc syncdoc/syncdoc -f values-production.yaml
```

### Major Version Upgrades

1. **Read the Changelog** - Check `CHANGELOG.md` for breaking changes
2. **Backup Everything** - Database, configuration, custom code
3. **Review Migration Notes** - Any special upgrade instructions
4. **Test in Staging** - Upgrade a staging environment first
5. **Schedule Downtime** - Major upgrades may require downtime
6. **Follow Standard Upgrade Process** - Then monitor closely

## Backup and Recovery

### Database Backup

```bash
# Using pg_dump
sudo -u postgres pg_dump syncdoc > syncdoc-backup-$(date +%Y%m%d).sql

# Using docker-compose exec (if using Docker)
docker-compose exec postgres pg_dump -U syncdoc syncdoc > backup.sql

# Compressed backup
sudo -u postgres pg_dump syncdoc | gzip > syncdoc-backup-$(date +%Y%m%d).sql.gz
```

### Database Restore

```bash
# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE syncdoc;"
sudo -u postgres psql -c "CREATE DATABASE syncdoc OWNER syncdoc;"
sudo -u postgres psql -d syncdoc -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Restore from backup
sudo -u postgres psql -d syncdoc < backup.sql

# Or for compressed backup
gunzip < syncdoc-backup-20230101.sql.gz | sudo -u postgres psql -d syncdoc
```

### Configuration Backup

```bash
# Backup environment files
cp .env .env.backup-$(date +%Y%m%d)
cp docker-compose.yml docker-compose.yml.backup-$(date +%Y%m%d)

# Backup custom configurations
cp -r infra/custom-configs/ infra/custom-configs.backup-$(date +%Y%m%d)/
```

### File Storage Backup

If using local storage:
```bash
# Backup uploads directory
tar -czf uploads-backup-$(date +%Y%m%d).tar.gz backend/app/uploads/
```

If using S3-compatible storage, use your provider's backup tools or:
```bash
# Using awscli
aws s3 sync s3://your-syncdoc-bucket ./s3-backup-$(date +%Y%m%d) --delete
```

### Full System Backup (for VM deployments)

```bash
# Using rsync (excluding unnecessary directories)
rsync -avh --progress \
    --exclude='/proc/*' \
    --exclude='/sys/*' \
    --exclude='/dev/*' \
    --exclude='/tmp/*' \
    --exclude='/run/*' \
    --exclude='/mnt/*' \
    --exclude='/media/*' \
    --exclude='/lost+found' \
    / root@backup-server:/backups/syncdoc-hostname-$(date +%Y%m%d)/
```

## Monitoring and Logging

### Health Check Endpoints

SyncDoc provides several health check endpoints:

- `GET /health` - Overall application health
- `GET /health/db` - Database connectivity
- `GET /health/redis` - Redis connectivity
- `GET /health/workers` - Celery worker status
- `GET /metrics` - Prometheus metrics (if enabled)

### Logging Configuration

Logs are structured JSON by default in production. Configure via:

```bash
# In .env
LOG_LEVEL=INFO
LOG_FORMAT=json  # or "text" for development
```

### Prometheus Metrics

Enable metrics by setting:
```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

Then scrape `http://your-host:9090/metrics` with Prometheus.

### Recommended Monitoring Stack

1. **Infrastructure Monitoring**
   - Host-level: Prometheus Node Exporter
   - Container-level: cAdvisor or built-in Docker stats
   - Orchestration: kube-state-metrics (for Kubernetes)

2. **Application Monitoring**
   - SyncDoc's built-in metrics endpoint
   - Application Performance Monitoring (APM) tools
   - Custom business metrics

3. **Logging**
   - Centralized: ELK Stack (Elasticsearch, Logstash, Kibana) or Loki
   - Application logs: Fluentd/Fluent Bit agents
   - System logs: journald forwarding

4. **Alerting**
   - Alertmanager for Prometheus alerts
   - Dead man's snitch for cron jobs
   - Synthetic monitoring for uptime checks

5. **Visualization**
   - Grafana dashboards for metrics
   - Kibana for log exploration

### Key Metrics to Monitor

**Application Metrics:**
- Request rate, error rate, duration (RED metrics)
- Database connection pool usage
- Redis memory usage and hit rate
- Celery queue depths and processing rates
- Active WebSocket connections
- File upload/storage usage

**System Metrics:**
- CPU, memory, disk utilization
- Network I/O
- Process counts
- File descriptor usage

**Business Metrics:**
- Number of projects/documentation items
- User registration and activation rates
- AI feature usage (if enabled)
- API usage by endpoint

### Log Levels

- `ERROR`: Critical issues requiring immediate attention
- `WARNING`: Potential issues that may need investigation
- `INFO`: General operational information
- `DEBUG`: Detailed information for troubleshooting
- `TRACE`: Very detailed information (development only)

### Log Rotation

Ensure logs are rotated to prevent disk space issues:

```bash
# For systemd journals
sudo journalctl --vacuum-time=30 days

# For application logs (if writing to files)
# Configure logrotate or use copyingtruncate in logging config

# Example logrotate config (/etc/logrotate.d/syncdoc)
/var/log/syncdoc/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 syncdoc adm
    sharedscripts
    postrotate
        systemctl kill -s HUP syncdoc-api syncdoc-worker >/dev/null 2>&1 || true
    endscript
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   - Check `DATABASE_URL` format
   - Verify PostgreSQL is running and accessible
   - Check network/firewall rules
   - Validate credentials in environment variables

2. **Redis Connection Issues**
   - Verify `REDIS_URL` format
   - Check if Redis authentication is required
   - Validate network connectivity
   - Check Redis memory limits

3. **Container Startup Failures**
   - Check container logs: `docker-compose logs api`
   - Validate environment variables
   - Check for port conflicts
   - Ensure sufficient resources (memory/CPU)

4. **Performance Issues**
   - Monitor database slow queries
   - Check Redis memory usage and eviction policies
   - Review application logs for errors
   - Consider horizontal scaling (more workers/replicas)

5. **Upload Failures**
   - Check file storage permissions
   - Verify available disk space
   - Check MIME type validation
   - Review upload size limits

### Getting Help

1. **Documentation**
   - Check this guide for deployment-specific issues
   - Review API docs at `/docs` when running
   - Consult `CONTRIBUTING.md` for development guidance

2. **Community Support**
   - GitHub Discussions: https://github.com/syncdoc-dev/syncdoc-free/discussions
   - GitHub Issues: https://github.com/syncdoc-dev/syncdoc-free/issues
   - Stack Overflow (tag: syncdoc)

3. **Professional Support**
   - Available for hosted version customers
   - Contact: support@syncdoc.dev
   - Enterprise SLAs available

## License

SyncDoc is released under the Apache License 2.0. See the [LICENSE](../LICENSE) file for details.

---

*Last updated: $(date +%Y-%m-%d)*