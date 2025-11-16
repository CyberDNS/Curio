# Deployment Guide

## Table of Contents
- [Docker Compose](#docker-compose)
- [Unraid](#unraid)
- [Home Assistant](#home-assistant)
- [Manual Deployment](#manual-deployment)
- [Reverse Proxy Setup](#reverse-proxy-setup)

## Docker Compose

### Production Deployment

1. **Prepare environment:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

2. **Important: Set secure values:**
   ```env
   POSTGRES_PASSWORD=your-very-secure-password
   SECRET_KEY=generate-a-random-secret-key
   OPENAI_API_KEY=sk-your-api-key
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop services:**
   ```bash
   docker-compose down
   ```

### Updating

```bash
git pull
docker-compose pull
docker-compose up -d --build
```

## Unraid

### Template Installation

1. **Add Custom Repository**
   - Go to **Docker** tab
   - Click **Add Container**
   - Toggle **Advanced View**

2. **Configuration:**
   ```
   Name: Curio
   Repository: yourusername/curio:latest
   Network Type: bridge

   Port Mappings:
   - Container Port: 3000, Host Port: 3000 (Frontend)
   - Container Port: 8000, Host Port: 8000 (Backend)

   Volume Mappings:
   - Container Path: /var/lib/postgresql/data
     Host Path: /mnt/user/appdata/curio/postgres

   Environment Variables:
   - POSTGRES_USER: curio
   - POSTGRES_PASSWORD: your-password
   - POSTGRES_DB: curio
   - OPENAI_API_KEY: sk-your-key
   - SECRET_KEY: your-secret
   ```

3. **Apply and Start**

### Using docker-compose in Unraid

Place `docker-compose.yml` and `.env` in `/mnt/user/appdata/curio/`:

```bash
cd /mnt/user/appdata/curio
docker-compose up -d
```

## Home Assistant

### Add-on Installation

1. **Create add-on structure:**
   ```
   /addons/curio/
   ├── config.json
   ├── Dockerfile
   ├── run.sh
   └── README.md
   ```

2. **config.json:**
   ```json
   {
     "name": "Curio News Aggregator",
     "version": "1.0.0",
     "slug": "curio",
     "description": "AI-powered personalized news aggregator",
     "url": "https://github.com/yourusername/curio",
     "arch": ["amd64", "armv7", "aarch64"],
     "startup": "application",
     "boot": "auto",
     "ports": {
       "3000/tcp": 3000,
       "8000/tcp": 8000
     },
     "ports_description": {
       "3000/tcp": "Frontend UI",
       "8000/tcp": "Backend API"
     },
     "options": {
       "openai_api_key": "",
       "llm_model": "gpt-4-turbo-preview",
       "rss_fetch_interval": 60
     },
     "schema": {
       "openai_api_key": "str",
       "llm_model": "str",
       "rss_fetch_interval": "int(1,1440)"
     },
     "image": "yourusername/curio"
   }
   ```

3. **run.sh:**
   ```bash
   #!/usr/bin/with-contenv bashio

   export OPENAI_API_KEY=$(bashio::config 'openai_api_key')
   export LLM_MODEL=$(bashio::config 'llm_model')
   export RSS_FETCH_INTERVAL=$(bashio::config 'rss_fetch_interval')

   cd /app
   docker-compose up
   ```

4. **Install in Home Assistant:**
   - Add repository to Add-on Store
   - Install Curio add-on
   - Configure in add-on settings
   - Start add-on

## Manual Deployment

### Requirements
- Python 3.12+
- Node.js 20+
- PostgreSQL 16+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/curio"
export OPENAI_API_KEY="sk-your-key"
export SECRET_KEY="your-secret"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Serve with any static server
npx serve -s dist -l 3000
```

### Process Manager (PM2)

```bash
# Install PM2
npm install -g pm2

# Start backend
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name curio-backend

# Start frontend
pm2 start "npx serve -s dist -l 3000" --name curio-frontend

# Save configuration
pm2 save
pm2 startup
```

## Reverse Proxy Setup

### Nginx

```nginx
server {
    listen 80;
    server_name curio.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000/api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Traefik (Docker)

Add labels to `docker-compose.yml`:

```yaml
services:
  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.curio.rule=Host(`curio.yourdomain.com`)"
      - "traefik.http.routers.curio.entrypoints=websecure"
      - "traefik.http.routers.curio.tls.certresolver=letsencrypt"
      - "traefik.http.services.curio.loadbalancer.server.port=3000"

  backend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.curio-api.rule=Host(`curio.yourdomain.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.curio-api.entrypoints=websecure"
      - "traefik.http.routers.curio-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.curio-api.loadbalancer.server.port=8000"
```

### Caddy

```
curio.yourdomain.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy localhost:3000
}
```

## SSL/TLS with Let's Encrypt

### Using Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d curio.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## Backup and Restore

### Backup Database

```bash
docker-compose exec db pg_dump -U curio curio > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker-compose exec -T db psql -U curio curio
```

### Full Backup

```bash
# Stop services
docker-compose down

# Backup volumes
docker run --rm -v curio_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/curio-backup.tar.gz /data

# Restart services
docker-compose up -d
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore volume
docker run --rm -v curio_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/curio-backup.tar.gz -C /

# Start services
docker-compose up -d
```

## Monitoring

### Health Checks

```bash
# Check frontend
curl http://localhost:3000

# Check backend
curl http://localhost:8000/health

# Check database
docker-compose exec db pg_isready -U curio
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

## Performance Tuning

### PostgreSQL

Edit `docker-compose.yml`:

```yaml
db:
  command: postgres -c shared_buffers=256MB -c max_connections=200
```

### Backend Workers

```yaml
backend:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Security Checklist

- [ ] Change default passwords
- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS
- [ ] Configure firewall
- [ ] Regular backups
- [ ] Keep Docker images updated
- [ ] Monitor API usage/costs
- [ ] Use environment variables (never commit secrets)
- [ ] Enable PostgreSQL authentication
- [ ] Set up fail2ban (if exposed to internet)

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart backend
```

### Database connection issues

```bash
# Check if DB is running
docker-compose exec db pg_isready

# Check environment variables
docker-compose exec backend env | grep DATABASE_URL
```

### Permission issues

```bash
# Fix volume permissions
sudo chown -R 1000:1000 ./backend
```
