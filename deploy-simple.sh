#!/bin/bash
# Simple deployment script - minimal version
# Usage: ./deploy-simple.sh

set -e

echo "=== WowRussian Simple Deploy ==="
date

# Load config if exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/deploy-config.sh"

if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
    echo "Loaded config from: $CONFIG_FILE"
fi

# Set default deploy directory if not set
: ${DEPLOY_DIR:="/home/cloudpanel/domains/yourdomain.com/wowrussian"}

echo "Deploy directory: $DEPLOY_DIR"

# Change to app directory
cd "$DEPLOY_DIR" || { echo "ERROR: Cannot change to $DEPLOY_DIR"; exit 1; }

# Pull latest code
echo "Pulling latest code..."
if [[ -d ".git" ]]; then
    git pull || echo "WARNING: Git pull failed"
else
    echo "WARNING: Not a git repository, skipping git pull"
fi

# Stop containers
echo "Stopping containers..."
docker-compose down 2>/dev/null || true

# Pull and rebuild
echo "Pulling images..."
docker-compose pull --ignore-pull-failures

echo "Building and starting..."
docker-compose up -d --build

# Wait a bit for containers to start
sleep 10

# Show status
echo ""
echo "=== Container Status ==="
docker-compose ps

# Cleanup old images
echo ""
echo "=== Cleaning up old Docker images ==="
docker image prune -a -f

# Optional: cleanup volumes (uncomment if needed)
# docker volume prune -f

echo ""
echo "Deployment complete!"
echo "Check logs: docker-compose logs -f"
