# Deployment Scripts

This directory contains automated deployment scripts for the WowRussian application.

## Files

- `deploy-production.sh` - Full-featured production deployment script with backups, health checks, and comprehensive cleanup
- `deploy-simple.sh` - Minimal deployment script for quick updates
- `deploy-config.example.sh` - Example configuration file for customizing deployments

## Quick Comparison

| Feature | deploy-production.sh | deploy-simple.sh |
|---------|---------------------|------------------|
| Backups | ✅ Database & storage | ❌ None |
| Health checks | ✅ Comprehensive | ❌ None |
| Git handling | ✅ Smart (stash changes) | ✅ Basic pull |
| Logging | ✅ Detailed logs | ❌ Minimal |
| Cleanup | ✅ Images, volumes, containers | ✅ Images only |
| Interactive | ✅ Prompts for decisions | ❌ Fully automatic |
| Best for | Production servers | Development/staging |

## Recommended: Full Production Script

For production servers, always use `deploy-production.sh` as it includes:
- Automatic backups before deployment
- Health checks to ensure services are running
- Comprehensive cleanup of Docker resources
- Detailed logging for troubleshooting
- Safety checks and prompts

### Setup

1. **Configure the script:**
   ```bash
   cp deploy-config.example.sh deploy-config.sh
   nano deploy-config.sh
   ```

   Edit these key variables:
   ```bash
   DEPLOY_DIR="/home/cloudpanel/domains/yourdomain.com/wowrussian"
   BACKUP_DIR="/backup/wowrussian"
   FRONTEND_PORT=3000  # Match your .env file
   ```

2. **Make executable:**
   ```bash
   chmod +x deploy-production.sh
   ```

3. **Run deployment:**
   ```bash
   cd /path/to/script
   sudo ./deploy-production.sh
   ```

   Or with custom config:
   ```bash
   DEPLOY_DIR="/custom/path" ./deploy-production.sh
   ```

### What Happens

The full script performs these steps in order:

1. **Pre-flight checks** - Verifies Docker, disk space, permissions
2. **Backup** - Saves database and storage to `$BACKUP_DIR`
3. **Git pull** - Updates code, offers to stash uncommitted changes
4. **Stop containers** - Gracefully stops all services
5. **Build & start** - Rebuilds images and starts containers
6. **Health check** - Waits for backend/frontend to respond
7. **Cleanup** - Removes old Docker images, volumes, containers
8. **Report** - Shows status, disk usage, and logs success

### Logs

All actions are logged to:
```
/var/log/wowrussian-deploy-YYYYMMDD-HHMMSS.log
```

Check this file if anything goes wrong.

## Simple Script

For development or when you need a quick update without backups:

```bash
chmod +x deploy-simple.sh
./deploy-simple.sh
```

**Warning:** This script does NOT create backups. Use only when you can afford to lose data or have separate backup processes.

## Configuration

You can configure the deployment by:

1. **Editing the script directly** - Change variables at the top
2. **Using a config file** - Create `deploy-config.sh` in the same directory:
   ```bash
   # deploy-config.sh
   DEPLOY_DIR="/custom/path"
   BACKUP_DIR="/custom/backups"
   FRONTEND_PORT=3000
   ```
3. **Environment variables** - Override at runtime:
   ```bash
   DEPLOY_DIR="/custom/path" ./deploy-production.sh
   ```

### Available Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOY_DIR` | `/home/cloudpanel/domains/yourdomain.com/wowrussian` | Application directory |
| `BACKUP_DIR` | `/backup/wowrussian` | Where to store backups |
| `LOG_FILE` | Auto-generated | Deployment log path |
| `RETENTION_DAYS` | `7` | Days to keep backups/logs |
| `ENV_FILE` | `.env` | Environment file name |
| `FRONTEND_PORT` | `3000` | Frontend container port |

## Environment Variables

The script respects these environment variables:

- `DEPLOY_DIR` - Override deployment directory
- `BACKUP_DIR` - Override backup directory
- `RETENTION_DAYS` - Override retention period
- `FRONTEND_PORT` - Frontend port for health check
- `SKIP_BACKUP` - Set to `1` to skip backup step
- `SKIP_GIT_PULL` - Set to `1` to skip git pull
- `SKIP_CLEANUP` - Set to `1` to skip Docker cleanup

Example:
```bash
SKIP_BACKUP=1 DEPLOY_DIR="/tmp/test" ./deploy-production.sh
```

## Troubleshooting

### Permission Denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in, or use:
sudo ./deploy-production.sh
```

### Git Pull Fails
- Check SSH keys: `ssh -T git@github.com`
- Verify repository access
- Use HTTPS instead of SSH if needed

### Health Check Timeout
- Check logs: `docker-compose logs backend`
- Increase timeout in script (change `max_attempts`)
- Verify `.env` settings (DEBUG, SECRET_KEY, etc.)

### Disk Space Issues
```bash
# Check free space
df -h

# Manual Docker cleanup
docker system prune -a

# Remove old backups
rm -rf /backup/wowrussian/*
```

### Container Won't Start
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Rebuild without cache
docker-compose build --no-cache
```

## Automation

### Cron Job

Set up automatic deployments:

```bash
# Edit crontab
crontab -e

# Run daily at 2 AM
0 2 * * * /path/to/deploy-production.sh >> /var/log/wowrussian-cron.log 2>&1
```

### Webhook

Trigger deployment on git push via webhook:

```bash
# Create a webhook endpoint (using a simple server or service like webhook.site)
# Or use a CI/CD system (GitHub Actions, GitLab CI, etc.)

# Example with GitHub Actions:
# .github/workflows/deploy.yml
```

## Rollback

If deployment fails:

1. **Restore database:**
   ```bash
   ls -la /backup/wowrussian/app.db-*.db  # Find latest
   cp /backup/wowrussian/app.db-YYYYMMDD-HHMMSS.db data/app.db
   ```

2. **Restore storage:**
   ```bash
   tar -xzf /backup/wowrussian/wowrussian-backup-YYYYMMDD-HHMMSS.tar.gz -C /path/to/app
   ```

3. **Redeploy previous version:**
   ```bash
   cd $DEPLOY_DIR
   git log --oneline  # Find previous commit
   git checkout <commit-hash>
   docker-compose up -d --build
   ```

## Best Practices

1. **Always use the full script in production** - It includes backups and health checks
2. **Test in staging first** - Deploy to a non-production environment first
3. **Monitor after deployment** - Check logs and application health
4. **Keep backups** - Retain at least 7 days of backups
5. **Secure the script** - Set proper permissions (750) and ownership
6. **Use SSH keys** - For git access, use deploy keys with limited permissions
7. **Regular cleanup** - The script handles this, but monitor disk usage

## Security Notes

- The script may run with elevated privileges (sudo)
- Store it in a secure location with restricted access
- Never commit `.env` or `deploy-config.sh` with real secrets
- Use environment variables for sensitive data
- Consider using a secrets manager for production

## Support

For more information:
- See `docs/DEPLOYMENT.md` for manual deployment steps
- See `docs/DATABASE_MIGRATION.md` for database migration info
- Check application logs: `docker-compose logs -f`

## License

Part of the WowRussian project. See main project license.
