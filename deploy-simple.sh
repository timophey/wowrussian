#!/bin/bash
# Simple deployment script - minimal version
# Usage: ./deploy-simple.sh

set -e

# Detect Docker Compose command (prefer docker compose v2)
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

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

# Load .env file safely (handles spaces in values)
if [[ -f ".env" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line//[[:space:]]/}" ]] && continue
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        if [[ "$line" == *=* ]]; then
            var_name="${line%%=*}"
            var_value="${line#*=}"
            if [[ "$var_value" =~ ^\".*\"$ ]] || [[ "$var_value" =~ ^\'.*\'$ ]]; then
                var_value="${var_value:1:${#var_value}-2}"
            fi
            export "$var_name"="$var_value"
        fi
    done < ".env"
    echo "Loaded environment from .env"
fi

# Pull latest code
echo "Pulling latest code..."
if [[ -d ".git" ]]; then
    git pull || echo "WARNING: Git pull failed"
else
    echo "WARNING: Not a git repository, skipping git pull"
fi

# Stop containers
echo "Stopping containers..."
$DOCKER_COMPOSE down 2>/dev/null || true

# Pull and rebuild
echo "Pulling images..."
$DOCKER_COMPOSE pull --ignore-pull-failures

echo "Building and starting..."
$DOCKER_COMPOSE up -d --build

# Wait a bit for containers to start
sleep 10

# Show status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get frontend port from environment
local frontend_port="${FRONTEND_PORT:-3000}"
local server_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "  Accessible URLs:"
echo "    • Frontend:  http://localhost:${frontend_port}"
echo "    • Backend:   http://localhost:8000"
echo "    • API Docs:  http://localhost:8000/docs"
echo "    • Health:    http://localhost:8000/health"
echo ""

if [[ -n "$ALLOWED_ORIGINS" ]]; then
    echo "  Allowed Origins (CORS):"
    local origins=$(echo "$ALLOWED_ORIGINS" | sed 's/\[//g; s/\]//g; s/"//g; s/ //g')
    IFS=',' read -ra origin_array <<< "$origins"
    for origin in "${origin_array[@]}"; do
        [[ -n "$origin" ]] && echo "    • $origin"
    done
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Container Status:"
$DOCKER_COMPOSE ps
echo ""

# Cleanup old images
echo "Cleaning up old Docker images..."
docker image prune -a -f

echo ""
echo "✅ All done! Check logs with: $DOCKER_COMPOSE logs -f"
