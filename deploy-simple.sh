#!/bin/bash
# Simple deployment script - minimal version
# Usage: ./deploy-simple.sh

set -e

echo "=== WowRussian Simple Deploy ==="
date

# Change to your app directory
cd "/home/cloudpanel/domains/yourdomain.com/wowrussian" || exit 1

# Pull latest code
echo "Pulling latest code..."
git pull || echo "Git pull failed or not a git repo"

# Stop containers
echo "Stopping containers..."
docker-compose down 2>/dev/null || true

# Pull and rebuild
echo "Pulling images..."
docker-compose pull --ignore-pull-failures

echo "Building and starting..."
docker-compose up -d --build

# Wait a bit
sleep 10

# Show status
echo ""
echo "=== Container Status ==="
docker-compose ps

# Cleanup old images
echo ""
echo "=== Cleaning up old images ==="
docker image prune -a -f

echo ""
echo "Deployment complete!"
