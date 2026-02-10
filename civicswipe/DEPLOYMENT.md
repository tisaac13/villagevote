# RepCheck Deployment Guide

This guide covers deploying RepCheck to production.

## Quick Start

### Option 1: Deploy to Fly.io (Recommended for MVP)

Fly.io offers easy deployment with automatic SSL and global edge distribution.

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login to Fly
fly auth login

# Launch the app (first time)
cd backend
fly launch --name civicswipe-api

# Set secrets
fly secrets set \
  SECRET_KEY="$(openssl rand -hex 64)" \
  POSTGRES_PASSWORD="$(openssl rand -hex 32)" \
  REDIS_PASSWORD="$(openssl rand -hex 32)" \
  CONGRESS_API_KEY="your-key" \
  OPENSTATES_API_KEY="your-key" \
  ANTHROPIC_API_KEY="your-key"

# Deploy
fly deploy
```

### Option 2: Deploy with Docker Compose

```bash
# Copy and configure environment
cp backend/.env.production.template backend/.env.production
# Edit .env.production with your values

# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Option 3: Deploy to AWS/GCP/Azure

See platform-specific sections below.

---

## Pre-Deployment Checklist

- [ ] Generate new SECRET_KEY: `openssl rand -hex 64`
- [ ] Generate strong database password
- [ ] Generate strong Redis password
- [ ] Obtain production API keys (Congress.gov, Open States, Anthropic)
- [ ] Set up SSL certificate for your domain
- [ ] Configure DNS for your domain
- [ ] Set up error monitoring (Sentry recommended)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Review and update CORS_ORIGINS

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (64+ chars) | `openssl rand -hex 64` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://:password@host:6379/0` |
| `CONGRESS_API_KEY` | Congress.gov API key | Get from api.congress.gov |
| `OPENSTATES_API_KEY` | Open States API key | Get from openstates.org |
| `ANTHROPIC_API_KEY` | Anthropic API key | Get from anthropic.com |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Set to `production` |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SENTRY_DSN` | - | Sentry error tracking DSN |

---

## Database Setup

### Initial Schema

The database schema is automatically applied via Docker:

```bash
# If using docker-compose
docker-compose -f docker-compose.prod.yml up postgres -d

# The schema in database/001_initial_schema.sql is applied automatically
```

### Migrations (if needed)

```bash
# Enter the API container
docker exec -it civicswipe-api-prod bash

# Run Alembic migrations
alembic upgrade head
```

### Backup Strategy

```bash
# Manual backup
docker exec civicswipe-postgres-prod pg_dump -U civicswipe civicswipe > backup_$(date +%Y%m%d).sql

# Automated backup with cron (add to host crontab)
0 2 * * * docker exec civicswipe-postgres-prod pg_dump -U civicswipe civicswipe | gzip > /backups/civicswipe_$(date +\%Y\%m\%d).sql.gz
```

---

## SSL/TLS Setup

### Using Let's Encrypt (recommended)

```bash
# Install certbot
apt-get install certbot

# Get certificate
certbot certonly --standalone -d civicswipe.com -d www.civicswipe.com

# Copy to nginx ssl directory
cp /etc/letsencrypt/live/civicswipe.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/civicswipe.com/privkey.pem nginx/ssl/

# Set up auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

---

## Platform-Specific Deployment

### AWS (ECS + RDS + ElastiCache)

1. **Create RDS PostgreSQL instance**
   - Engine: PostgreSQL 15
   - Instance: db.t3.micro (dev) or db.r6g.large (prod)
   - Enable Multi-AZ for production

2. **Create ElastiCache Redis cluster**
   - Engine: Redis 7
   - Node type: cache.t3.micro (dev) or cache.r6g.large (prod)

3. **Create ECS cluster and deploy**
   ```bash
   # Build and push to ECR
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
   docker build -t civicswipe-api backend/
   docker tag civicswipe-api:latest <account>.dkr.ecr.us-west-2.amazonaws.com/civicswipe-api:latest
   docker push <account>.dkr.ecr.us-west-2.amazonaws.com/civicswipe-api:latest
   ```

### Google Cloud (Cloud Run + Cloud SQL)

```bash
# Build with Cloud Build
gcloud builds submit --tag gcr.io/PROJECT_ID/civicswipe-api backend/

# Deploy to Cloud Run
gcloud run deploy civicswipe-api \
  --image gcr.io/PROJECT_ID/civicswipe-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances=PROJECT_ID:us-central1:civicswipe-db \
  --set-env-vars="DATABASE_URL=..." \
  --set-secrets="SECRET_KEY=secret-key:latest,ANTHROPIC_API_KEY=anthropic-key:latest"
```

### DigitalOcean (App Platform)

1. Create a new App from the repository
2. Select Docker as the build type
3. Add environment variables in the App settings
4. Add a managed PostgreSQL database
5. Add a managed Redis database

---

## Monitoring & Logging

### Setting up Sentry

```python
# Already configured in app/core/config.py
# Just set the SENTRY_DSN environment variable

SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

### Health Checks

The API provides a health endpoint at `/api/v1/health`:

```bash
curl https://civicswipe.com/api/v1/health
# Returns: {"status": "healthy", "database": "connected", "redis": "connected"}
```

### Log Aggregation

```bash
# View logs in real-time
docker-compose -f docker-compose.prod.yml logs -f api

# Export logs
docker-compose -f docker-compose.prod.yml logs api > api_logs.txt
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.prod.yml - scale API
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Or use Kubernetes for more advanced orchestration
```

### Celery Workers

```bash
# Scale workers based on queue depth
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

---

## Security Checklist

- [ ] SECRET_KEY is unique and random (64+ characters)
- [ ] All API keys are from production accounts (not dev/test)
- [ ] Database password is strong (32+ characters)
- [ ] Redis password is set
- [ ] HTTPS is enforced (HTTP redirects to HTTPS)
- [ ] CORS is configured for production domains only
- [ ] Rate limiting is enabled
- [ ] SQL injection prevention (handled by SQLAlchemy)
- [ ] XSS prevention headers are set in nginx
- [ ] Sensitive data is not logged
- [ ] API docs are restricted in production (optional)

---

## Mobile App Deployment

### iOS (App Store)

```bash
# Build for iOS
cd mobile
eas build --platform ios --profile production

# Submit to App Store
eas submit --platform ios
```

### Android (Play Store)

```bash
# Build for Android
cd mobile
eas build --platform android --profile production

# Submit to Play Store
eas submit --platform android
```

### Configure API URL

Update `mobile/src/services/api.ts`:

```typescript
const API_BASE_URL = __DEV__
  ? 'http://localhost:8000/api/v1'
  : 'https://api.civicswipe.com/api/v1';
```

---

## Troubleshooting

### Common Issues

**Database connection failed**
```bash
# Check if postgres is running
docker-compose -f docker-compose.prod.yml ps postgres

# Check postgres logs
docker-compose -f docker-compose.prod.yml logs postgres
```

**Celery tasks not running**
```bash
# Check worker status
docker-compose -f docker-compose.prod.yml logs celery-worker

# Check Redis connection
docker exec -it civicswipe-redis-prod redis-cli -a $REDIS_PASSWORD ping
```

**API returning 500 errors**
```bash
# Check API logs
docker-compose -f docker-compose.prod.yml logs api

# Check if all environment variables are set
docker-compose -f docker-compose.prod.yml exec api env | grep -E "(API_KEY|SECRET)"
```

---

## Support

For issues or questions:
- GitHub Issues: [your-repo/issues]
- Email: support@civicswipe.com
