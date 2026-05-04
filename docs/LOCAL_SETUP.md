# Local Setup Troubleshooting & Configuration

This guide covers common setup issues and optional configurations for running SyncDoc locally.

## Common Docker Compose Issues

### Port Already in Use

If you see an error like `bind: address already in use`:

**Solution:** Update `docker-compose.yml` to use different ports:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change frontend port from 5173 to 5174, etc.
  
  frontend:
    ports:
      - "5174:5173"
  
  postgres:
    ports:
      - "5433:5432"
  
  redis:
    ports:
      - "6380:6379"
```

### Database Connection Refused

If the backend can't connect to PostgreSQL:

```bash
# Check if postgres container is running
docker-compose ps

# Check postgres logs
docker-compose logs postgres

# Ensure postgres is ready
docker-compose exec postgres pg_isready
```

### Reset Everything

To completely reset and start fresh:

```bash
# Stop and remove all containers, volumes, and networks
docker-compose down -v

# Start fresh
docker-compose up
```

## Optional Configuration

### GitHub OAuth Setup

To enable GitHub login (optional):

1. **Create GitHub OAuth App:**
   - Go to https://github.com/settings/developers
   - Click "New OAuth App"
   - Set Authorization callback URL to: `http://localhost:8000/api/auth/github/callback`
   - Copy **Client ID** and **Client Secret**

2. **Configure .env:**

```env
GH_CLIENT_ID=your-client-id-here
GH_CLIENT_SECRET=your-client-secret-here
```

3. **Restart services:**

```bash
docker-compose restart api
```

### AI Features (LLM Integration)

To enable AI-powered features, add your LLM API key:

#### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-your-openai-api-key-here
LLM_ENDPOINT_URL=https://api.openai.com/v1
```

#### Anthropic Claude

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229
LLM_API_KEY=sk-ant-your-anthropic-key-here
LLM_ENDPOINT_URL=https://api.anthropic.com
```

#### Local LM Studio

If you're running LM Studio locally:

```env
LLM_PROVIDER=openai
LLM_MODEL=your-local-model-name
LLM_API_KEY=dummy-key-for-local
LLM_ENDPOINT_URL=http://localhost:1234/v1
```

**Note:** AI features gracefully disable if no API key is provided. You can use SyncDoc without AI features.

### Email/SMTP Configuration (Optional)

To enable email notifications:

```env
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=SyncDoc
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

For Gmail:
1. Enable 2-factor authentication
2. Create an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password as `SMTP_PASSWORD`

## Database Access

### Using psql

To access the database directly:

```bash
# Connect to postgres container
docker-compose exec postgres psql -U syncdoc -d syncdoc

# Useful commands:
# \dt - List tables
# \df - List functions
# SELECT * FROM users; - Query example
```

### Using DBeaver or pgAdmin

**Connection Details:**
- Host: `localhost`
- Port: `5432` (or your custom port)
- Username: `syncdoc`
- Password: `syncdoc_dev`
- Database: `syncdoc`

## Viewing Logs

### Backend API Logs

```bash
docker-compose logs -f api
```

### Frontend Logs

```bash
docker-compose logs -f frontend
```

### All Services

```bash
docker-compose logs -f
```

### Search in Logs

```bash
# Grep for error
docker-compose logs api | grep -i error

# Tail last 100 lines
docker-compose logs --tail=100 api
```

## Performance & Memory

If SyncDoc is slow or consuming too much memory:

1. **Check memory usage:**

```bash
docker-compose stats
```

2. **Limit memory per service** (in docker-compose.yml):

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1g
    reservations:
      memory: 512m
```

3. **Rebuild images:**

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## Redis Issues

### Clear Redis Cache

```bash
docker-compose exec redis redis-cli FLUSHALL
```

### Monitor Redis

```bash
docker-compose exec redis redis-cli MONITOR
```

## Development Mode

### Hot Reload

Both services support hot-reload:

**Backend:** Changes to `backend/app/` automatically reload
**Frontend:** Changes to `frontend/src/` automatically rebuild

### Disable Hot Reload

If hot-reload causes issues:

```bash
# Backend
docker-compose stop api
cd backend && uvicorn app.main:app --host 0.0.0.0

# Frontend
docker-compose stop frontend
cd frontend && npm run dev
```

## Testing

### Run Backend Tests

```bash
docker-compose exec api pytest tests/ -v
```

### Run Frontend Tests

```bash
docker-compose exec frontend npm run test
```

### Full Test Suite

```bash
docker-compose exec api pytest tests/ -v --cov=app
docker-compose exec frontend npm run test:coverage
```

## Debugging

### Add Breakpoints

For backend debugging with pdb:

```python
# In backend/app/services/example.py
import pdb; pdb.set_trace()  # Python debugger
```

```bash
# Then run interactively
docker-compose run --rm api bash
```

### Browser DevTools

Frontend debugging:
1. Open browser DevTools (F12)
2. Check **Console** for errors
3. Check **Network** tab for API calls
4. Use React DevTools browser extension

## Migration Issues

### Database Migrations Failed

```bash
# Check migration status
docker-compose exec api alembic current

# Downgrade to previous version
docker-compose exec api alembic downgrade -1

# Upgrade to latest
docker-compose exec api alembic upgrade head
```

### Create New Migration

```bash
docker-compose exec api alembic revision --autogenerate -m "Your migration message"
```

## Cleaning Up

### Remove All Containers

```bash
docker-compose down
```

### Remove with Volumes (Delete Data)

```bash
docker-compose down -v
```

### Remove Images

```bash
docker-compose down --rmi all
```

## Getting Help

- Check logs: `docker-compose logs -f`
- Review `.env` file (ensure it's set correctly)
- Open an issue: https://github.com/syncdoc-dev/syncdoc-free/issues
- Search existing issues: https://github.com/syncdoc-dev/syncdoc-free/issues?q=

## Next Steps

- Explore the API: http://localhost:8000/docs
- Check API health: `curl http://localhost:8000/health`
- Try uploading your first IaC file
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) to contribute
