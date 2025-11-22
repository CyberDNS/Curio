# Docker Deployment Guide

This guide explains how to deploy Curio using Docker images from GitHub Container Registry.

## Available Images

All images are published to GitHub Container Registry (ghcr.io):

- **Backend**: `ghcr.io/cyberdns/curio-backend:latest`
- **Frontend**: `ghcr.io/cyberdns/curio-frontend:latest`
- **Unraid (All-in-One)**: `ghcr.io/cyberdns/curio:latest`

## Quick Start

### Option 1: Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: curio
      POSTGRES_USER: curio
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  backend:
    image: ghcr.io/cyberdns/curio-backend:latest
    environment:
      # Database
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: curio
      POSTGRES_USER: curio
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

      # Security
      SECRET_KEY: ${SECRET_KEY}

      # OAuth (or DEV_MODE)
      OAUTH_CLIENT_ID: ${OAUTH_CLIENT_ID}
      OAUTH_CLIENT_SECRET: ${OAUTH_CLIENT_SECRET}
      OAUTH_SERVER_METADATA_URL: ${OAUTH_SERVER_METADATA_URL}
      OAUTH_REDIRECT_URI: ${OAUTH_REDIRECT_URI}

      # Or for development
      # DEV_MODE: "true"

      # OpenAI
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
    restart: unless-stopped

  frontend:
    image: ghcr.io/cyberdns/workspace/frontend:latest
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

Create a `.env` file:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_secret_key_min_32_chars

# OAuth Configuration
OAUTH_CLIENT_ID=your_oauth_client_id
OAUTH_CLIENT_SECRET=your_oauth_client_secret
OAUTH_SERVER_METADATA_URL=https://your-oauth-provider/.well-known/openid-configuration
OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key
```

Start the stack:

```bash
docker-compose up -d
```

### Option 2: Unraid All-in-One Container

For Unraid or single-container deployments:

```bash
docker run -d \
  --name curio \
  -p 3000:80 \
  -e POSTGRES_PASSWORD=your_password \
  -e SECRET_KEY=your_secret_key \
  -e OPENAI_API_KEY=your_openai_key \
  -e DEV_MODE=true \
  -v curio-data:/data \
  ghcr.io/cyberdns/curio:latest
```

## Image Tags

### Version Tags

- `latest` - Latest stable release from main branch
- `v1.0.0` - Specific version tag
- `v1.0` - Major.minor version
- `main` - Latest build from main branch
- `main-abc123` - Specific commit from main branch

### Pull Specific Version

```bash
# Latest stable
docker pull ghcr.io/cyberdns/curio-backend:latest

# Specific version
docker pull ghcr.io/cyberdns/curio-backend:v1.0.0

# Latest from main branch
docker pull ghcr.io/cyberdns/curio-backend:main
```

## Environment Variables

### Required

| Variable            | Description                | Example                |
| ------------------- | -------------------------- | ---------------------- |
| `POSTGRES_PASSWORD` | Database password          | `secure_password_123`  |
| `SECRET_KEY`        | JWT secret key (32+ chars) | `your-secret-key-here` |
| `OPENAI_API_KEY`    | OpenAI API key             | `sk-...`               |

### Authentication (Choose One)

**Option A: OAuth (Production)**

| Variable                    | Description         |
| --------------------------- | ------------------- |
| `OAUTH_CLIENT_ID`           | OAuth client ID     |
| `OAUTH_CLIENT_SECRET`       | OAuth client secret |
| `OAUTH_SERVER_METADATA_URL` | OAuth discovery URL |
| `OAUTH_REDIRECT_URI`        | OAuth callback URL  |

**Option B: Dev Mode (Development Only)**

| Variable   | Description                  |
| ---------- | ---------------------------- |
| `DEV_MODE` | Set to `true` to bypass auth |

### Optional

| Variable        | Default                 | Description        |
| --------------- | ----------------------- | ------------------ |
| `POSTGRES_HOST` | `localhost`             | Database host      |
| `POSTGRES_PORT` | `5432`                  | Database port      |
| `POSTGRES_DB`   | `curio`                 | Database name      |
| `POSTGRES_USER` | `curio`                 | Database user      |
| `COOKIE_SECURE` | `true`                  | Use secure cookies |
| `FRONTEND_URL`  | `http://localhost:3000` | Frontend URL       |
| `BACKEND_URL`   | `http://localhost:8000` | Backend URL        |

## Health Checks

### Backend

```bash
curl http://localhost:8000/api/health
```

### Frontend

```bash
curl http://localhost:3000
```

## Logs

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Updates

### Pull Latest Images

```bash
docker-compose pull
docker-compose up -d
```

### Update to Specific Version

```bash
# Edit docker-compose.yml to use specific version tag
# Then:
docker-compose pull
docker-compose up -d
```

## Backup

### Database Backup

```bash
docker exec curio-postgres pg_dump -U curio curio > backup.sql
```

### Restore Database

```bash
docker exec -i curio-postgres psql -U curio curio < backup.sql
```

## Troubleshooting

### Check Container Status

```bash
docker-compose ps
```

### View Container Logs

```bash
docker-compose logs backend
docker-compose logs frontend
```

### Restart Services

```bash
docker-compose restart
```

### Database Connection Issues

```bash
# Test database connection from backend
docker-compose exec backend python -c "from app.core.database import engine; engine.connect()"
```

### Permission Issues

```bash
# Fix volume permissions
docker-compose down
docker volume rm curio_postgres_data
docker-compose up -d
```

## Security Notes

1. **Never use DEV_MODE in production** - Always configure OAuth
2. **Use strong SECRET_KEY** - Generate with: `openssl rand -hex 32`
3. **Secure your .env file** - Never commit it to version control
4. **Use HTTPS in production** - Set `COOKIE_SECURE=true`
5. **Regular updates** - Pull latest images regularly for security patches

## Production Deployment

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name curio.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Using Traefik

```yaml
services:
  frontend:
    image: ghcr.io/cyberdns/curio-frontend:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.curio.rule=Host(`curio.example.com`)"
      - "traefik.http.routers.curio.entrypoints=websecure"
      - "traefik.http.routers.curio.tls.certresolver=letsencrypt"
```

## CI/CD Integration

Images are automatically built and published when:

- Code is pushed to `main` branch
- A version tag is created (e.g., `v1.0.0`)
- Manually triggered via GitHub Actions

### View Published Images

Visit: https://github.com/CyberDNS/curio/pkgs/container/curio

## Support

For issues or questions:

- GitHub Issues: https://github.com/CyberDNS/curio/issues
- Documentation: See project README.md
