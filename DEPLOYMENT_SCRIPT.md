# Production Deployment Script

## Overview

The `deploy-production.sh` script automates the deployment process for the WowRussian application on a production server. It handles:

- Git pull with uncommitted changes detection
- Database and storage backup
- Container rebuild and restart
- Health checks
- Cleanup of old Docker images, volumes, and containers
- Log rotation and cleanup

## Prerequisites

- Docker and Docker Compose installed
- Application files uploaded to the server
- Proper permissions to run Docker commands
- Sudo access (if needed)

## Quick Start

1. **Configure the deployment script:**

   ```bash
   # Copy the example config
   cp deploy-config.example.sh deploy-config.sh
   
   # Edit with your settings
   nano deploy-config.sh
   ```

   Update the following variables:
   - `DEPLOY_DIR`: Full path to your application directory
   - `BACKUP_DIR`: Where to store backups (must have enough space)
   - `FRONTEND_PORT`: The port your frontend runs on (from .env)
   - `RETENTION_DAYS`: How long to keep backups (default: 7)

2. **Make the script executable:**

   ```bash
   chmod +x deploy-production.sh
   ```

3. **Run the deployment:**

   ```bash
   sudo ./deploy-production.sh
   ```

   Or with sudo if needed:
   ```bash
   sudo -E ./deploy-production.sh
   ```

## What the Script Does

### 1. Pre-deployment Checks
- Verifies Docker and Docker Compose are installed and running
- Checks for sufficient disk space (warns if < 2GB free)
- Ensures `.env` file exists (creates from `.env.example` if missing)
- Validates write permissions on deployment directory

### 2. Backup
- Creates timestamped backup of SQLite database (`data/app.db`)
- Creates compressed backup of `storage/` directory
- Stores backups in `$BACKUP_DIR`
- Automatically removes backups older than `$RETENTION_DAYS`

### 3. Git Update
- Detects current git branch
- Checks for uncommitted changes (prompts to stash if found)
- Pulls latest changes from remote repository
- Skips if not a git repository

### 4. Container Restart
- Stops all running containers (`docker-compose down`)
- Pulls latest base images
- Rebuilds all services (`docker-compose up -d --build`)
- Removes orphaned containers

### 5. Health Check
- Waits up to 120 seconds for backend `/health` endpoint to respond
- Verifies frontend is responding on configured port
- Shows container logs if health check fails

### 6. Cleanup
- Removes unused Docker images (`docker image prune -a`)
- Removes unused Docker volumes (`docker volume prune`)
- Removes stopped containers (`docker container prune`)
- Deletes old deployment logs from `/var/log/`

### 7. Summary
- Shows running containers status
- Displays disk usage
- Shows Docker system disk usage
- Logs success message

## Logging

All deployment actions are logged to:
```
/var/log/wowrussian-deploy-YYYYMMDD-HHMMSS.log
```

Logs are automatically rotated and deleted after `$RETENTION_DAYS`.

## Configuration Options

You can customize the script by editing the variables at the top, or by creating a `deploy-config.sh` file:

```bash
# In deploy-config.sh
DEPLOY_DIR="/path/to/app"
BACKUP_DIR="/path/to/backups"
RETENTION_DAYS=14
export FRONTEND_PORT=3000
```

The script will automatically load `deploy-config.sh` if it exists in the same directory.

## Rollback

If something goes wrong, you can:

1. **Restore database backup:**
   ```bash
   cp /backup/wowrussian/app.db-YYYYMMDD-HHMMSS.db data/app.db
   ```

2. **Restore storage:**
   ```bash
   tar -xzf /backup/wowrussian/wowrussian-backup-YYYYMMDD-HHMMSS.tar.gz -C .
   ```

3. **Redeploy previous git commit:**
   ```bash
   cd $DEPLOY_DIR
   git log  # Find the commit hash
   git checkout <previous-commit>
   docker-compose up -d --build
   ```

## Troubleshooting

### Permission Denied
Ensure your user is in the `docker` group:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

Or run with sudo:
```bash
sudo ./deploy-production.sh
```

### Low Disk Space
The script will warn you but continue. Consider:
- Manually cleaning Docker: `docker system prune -a`
- Expanding server disk space
- Removing old backups manually

### Health Check Fails
Check container logs:
```bash
docker-compose logs backend
docker-compose logs frontend
docker-compose logs celery
```

### Git Pull Fails
- Check network connectivity
- Verify SSH keys or credentials are set up
- Ensure you have pull permissions on the repository

### Database Migration Issues
The application runs migrations automatically on startup. If they fail:
1. Check the backend logs
2. Manually run migrations if needed (see `docs/DATABASE_MIGRATION.md`)
3. Restore from backup if necessary

## Advanced Usage

### Dry Run
Add `-n` flag to see what would be done without actually doing it:
```bash
# Not currently implemented, but can be added
```

### Custom Environment File
Set `ENV_FILE` variable if using a different environment file:
```bash
ENV_FILE=".env.production" ./deploy-production.sh
```

### Skip Steps
Set these environment variables to skip specific steps:
```bash
SKIP_BACKUP=1 ./deploy-production.sh
SKIP_GIT_PULL=1 ./deploy-production.sh
SKIP_CLEANUP=1 ./deploy-production.sh
```

## Security Considerations

1. **Protect the script:** Set appropriate permissions (750) and ownership
2. **Secure backups:** Ensure backup directory is not publicly accessible
3. **Log rotation:** The script handles its own logs, but consider system-wide log rotation
4. **Secrets:** Never commit `.env` file with production secrets to git
5. **SSH keys:** Use SSH keys with passphrase for git access, or use deploy keys

## Integration with CI/CD

You can integrate this script into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Deploy to Production
  run: |
    ssh user@server "cd /path/to/app && ./deploy-production.sh"
  env:
    DEPLOY_DIR: "/home/cloudpanel/domains/yourdomain.com/wowrussian"
```

Or use webhooks for automatic deployment on git push.

## Support

For issues or questions, refer to:
- `docs/DEPLOYMENT.md` - General deployment guide
- `docs/DATABASE_MIGRATION.md` - Database migration info
- Application logs: `docker-compose logs -f [service]`
