# Deployment Guide - CloudPanel

This guide covers deploying the WowRussian Analyzer on a server with CloudPanel.

## Prerequisites

- A VPS/cloud server (Ubuntu 22.04 recommended)
- Domain name pointing to the server
- CloudPanel installed (https://cloudpanel.io)

## Server Preparation

### 1. Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Create Application Directory

```bash
sudo mkdir -p /home/cloudpanel/domains/yourdomain.com/wowrussian
sudo chown -R cloudpanel:cloudpanel /home/cloudpanel/domains/yourdomain.com/wowrussian
```

## Application Setup

### 1. Upload Project Files

Copy all project files to `/home/cloudpanel/domains/yourdomain.com/wowrussian/`

### 2. Configure Environment

```bash
cd /home/cloudpanel/domains/yourdomain.com/wowrussian
cp .env.example .env
nano .env
```

Update the following variables:
```env
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com
```

### 3. Create Storage Directories

```bash
mkdir -p storage data
chmod 755 storage data
```

### 4. Build and Start Services

```bash
docker-compose up -d --build
```

## CloudPanel Configuration

### 1. Create a New Site in CloudPanel

- Login to CloudPanel dashboard
- Click "Sites" → "Add Site"
- Enter your domain name
- Select "Docker" as the stack type
- Set document root to `/home/cloudpanel/domains/yourdomain.com/wowrussian/frontend/build` (after build)

### 2. Configure Nginx

CloudPanel will create an nginx configuration. You may need to adjust it:

**Location for config:** `/etc/nginx/conf.d/yourdomain.com.conf`

Add proxy configuration for API and WebSocket:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL certificates (CloudPanel usually manages these automatically)
    ssl_certificate /etc/ssl/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/yourdomain.com.key;

    # Frontend (React build)
    root /home/cloudpanel/domains/yourdomain.com/wowrussian/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. Build Frontend

```bash
cd /home/cloudpanel/domains/yourdomain.com/wowrussian/frontend
docker run --rm -v $(pwd):/app -v /app/node_modules -w /app node:18-alpine sh -c "npm ci && npm run build"
```

### 4. Restart Services

```bash
cd /home/cloudpanel/domains/yourdomain.com/wowrussian
docker-compose restart
```

### 5. Test Nginx Configuration

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/TLS with Let's Encrypt

CloudPanel usually handles SSL automatically. If you need to set it up manually:

```bash
# Install certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

## Monitoring

### Check Service Status

```bash
# Docker containers
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f celery
docker-compose logs -f frontend
```

### Database Backup

```bash
# Backup SQLite database
cp /home/cloudpanel/domains/yourdomain.com/wowrussian/data/app.db /backup/path/app-$(date +%Y%m%d).db

# Backup storage
tar -czf /backup/path/storage-$(date +%Y%m%d).tar.gz /home/cloudpanel/domains/yourdomain.com/wowrussian/storage
```

### Health Checks

- Backend health: `https://yourdomain.com/api/health`
- Backend API docs: `https://yourdomain.com/api/docs`

## Troubleshooting

### Common Issues

1. **Permission errors**:
   ```bash
   sudo chown -R cloudpanel:cloudpanel /home/cloudpanel/domains/yourdomain.com/wowrussian
   ```

2. **Port conflicts**:
   Ensure ports 80, 443, 8000 are not used by other services.

3. **Storage full**:
   Monitor disk usage: `df -h`
   Set up log rotation and cleanup old files.

4. **Celery tasks not running**:
   ```bash
   docker-compose logs celery
   # Restart if needed
   docker-compose restart celery
   ```

5. **WebSocket not connecting**:
   - Check nginx proxy configuration for `/ws/`
   - Verify Redis is running: `docker-compose ps redis`
   - Check browser console for errors

### Logs

- **Nginx logs**: `/var/log/nginx/`
- **Docker logs**: `docker-compose logs [service-name]`
- **Application logs**: Check docker-compose output

## Performance Optimization

1. **Increase Celery workers** (in docker-compose.yml):
   ```yaml
   celery:
     command: celery -A app.tasks worker --loglevel=info --concurrency=4
   ```

2. **Enable SQLite WAL mode** (already in code):
   Improves concurrent read/write performance.

3. **Add Redis persistence**:
   ```yaml
   redis:
     command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

4. **Set up CDN** for static assets if needed.

## Security Considerations

1. Change default `SECRET_KEY` in production
2. Enable firewall (UFW):
   ```bash
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```
3. Regular updates:
   ```bash
   sudo apt update && sudo apt upgrade
   docker-compose pull && docker-compose up -d
   ```
4. Use strong passwords for database (if switching to PostgreSQL)
5. Implement rate limiting on nginx if needed

## Updates

To update the application:

1. Pull latest code
2. Rebuild and restart:
   ```bash
   docker-compose pull
   docker-compose up -d --build
   ```
3. Run migrations if needed:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

## Support

For issues and feature requests, please open an issue on GitHub.