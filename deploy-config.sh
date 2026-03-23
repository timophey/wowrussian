# Deployment Configuration
# Copy this file to deploy-config.sh and customize for your environment

# Application deployment directory on the production server
DEPLOY_DIR="/home/timophey/Documents/WEB/wowrussian"

# Backup directory (must be writable)
BACKUP_DIR="/home/timophey/Documents/WEB/wowrussian.bac"

# Retention period for backups and logs (in days)
RETENTION_DAYS=7

# Frontend port (as defined in .env)
export FRONTEND_PORT=3000

# Optional: Git branch to deploy (defaults to current branch)
# DEPLOY_BRANCH="main"

# Optional: Additional docker-compose files to include
# COMPOSE_FILES="-f docker-compose.prod.yml"
