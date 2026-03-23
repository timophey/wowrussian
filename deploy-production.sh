#!/bin/bash

# Production Deployment Script for WowRussian Application
# This script updates the application via git, rebuilds and restarts containers,
# and cleans up old Docker images.

set -e  # Exit on any error

# Detect Docker Compose command (prefer docker compose v2)
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Configuration
APP_NAME="WowRussian"
DEPLOY_DIR="/home/cloudpanel/domains/yourdomain.com/wowrussian"
LOG_FILE="/var/log/wowrussian-deploy-$(date +%Y%m%d-%H%M%S).log"
ENV_FILE=".env"
BACKUP_DIR="/backup/wowrussian"
RETENTION_DAYS=7  # Keep logs and backups for this many days

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "${BLUE}$1${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$1${NC}"
}

log_warning() {
    log "WARNING" "${YELLOW}$1${NC}"
}

log_error() {
    log "ERROR" "${RED}$1${NC}"
}

# Load environment variables from .env file
load_env() {
    log_info "Loading environment from $ENV_FILE..."
    
    if [[ -f "$ENV_FILE" ]]; then
        # Export all variables from .env file
        set -a
        source "$ENV_FILE"
        set +a
        log_success "Environment loaded"
    else
        log_warning "$ENV_FILE not found, using defaults"
    fi
}

# Check if running as root or with appropriate permissions
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is acceptable but ensure proper ownership."
    fi
    
    if [[ ! -d "$DEPLOY_DIR" ]]; then
        log_error "Deployment directory does not exist: $DEPLOY_DIR"
        exit 1
    fi
    
    if [[ ! -w "$DEPLOY_DIR" ]]; then
        log_error "No write permission to deployment directory: $DEPLOY_DIR"
        exit 1
    fi
}

# Pre-deployment checks
pre_deploy_check() {
    log_info "Running pre-deployment checks..."
    
    # Check if we're in the correct directory
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found. Are you in the correct directory?"
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning ".env file not found. Copying from .env.example..."
        cp .env.example .env
        log_warning "Please review and update .env file with production values!"
        read -p "Press Enter to continue after reviewing .env, or Ctrl+C to abort..."
    fi
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! $DOCKER_COMPOSE version &>/dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check disk space (require at least 2GB free)
    local free_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [[ $free_space -lt 2 ]]; then
        log_warning "Low disk space: ${free_space}GB free. Consider cleanup before deployment."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Pre-deployment checks passed"
}

# Backup database and storage
backup_data() {
    log_info "Creating backup of database and storage..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Get current timestamp
    local backup_timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$BACKUP_DIR/wowrussian-backup-$backup_timestamp.tar.gz"
    
    # Backup database (SQLite)
    if [[ -f "data/app.db" ]]; then
        log_info "Backing up SQLite database..."
        cp data/app.db "$BACKUP_DIR/app.db-$backup_timestamp"
    fi
    
    # Backup storage directory
    if [[ -d "storage" ]]; then
        log_info "Backing up storage directory..."
        tar -czf "$backup_file" storage/ 2>/dev/null || true
    fi
    
    # Keep only recent backups
    find "$BACKUP_DIR" -name "wowrussian-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "app.db-*.db" -mtime +$RETENTION_DAYS -delete
    
    log_success "Backup completed: $backup_file"
}

# Pull latest code from git
git_pull() {
    log_info "Pulling latest code from git repository..."
    
    # Check if we're in a git repository
    if [[ ! -d ".git" ]]; then
        log_warning "Not a git repository. Skipping git pull."
        return 0
    fi
    
    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        log_warning "Uncommitted changes detected:"
        git status --short
        read -p "Stash changes and continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git stash
        else
            log_error "Aborting deployment due to uncommitted changes"
            exit 1
        fi
    fi
    
    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current branch: $current_branch"
    
    # Pull latest changes
    if git pull origin "$current_branch"; then
        log_success "Git pull successful"
    else
        log_error "Git pull failed"
        exit 1
    fi
}

# Stop running containers
stop_containers() {
    log_info "Stopping running containers..."
    
    if $DOCKER_COMPOSE ps | grep -q "Up"; then
        $DOCKER_COMPOSE down
        log_success "Containers stopped"
    else
        log_info "No running containers found"
    fi
}

# Build and start containers
build_and_start() {
    log_info "Building and starting containers..."
    
    # Pull latest base images
    log_info "Pulling latest base images..."
    $DOCKER_COMPOSE pull --ignore-pull-failures || log_warning "Some images could not be pulled"
    
    # Build and start
    log_info "Building and starting services..."
    if $DOCKER_COMPOSE up -d --build --remove-orphans; then
        log_success "Containers built and started"
    else
        log_error "Failed to build/start containers"
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_health() {
    log_info "Waiting for services to become healthy..."
    
    local max_attempts=60
    local attempt=1
    
    # Wait for backend
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f http://localhost:8000/health &> /dev/null; then
            log_success "Backend is healthy"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Backend failed to become healthy after $max_attempts attempts"
            $DOCKER_COMPOSE logs backend
            exit 1
        fi
        
        sleep 2
        ((attempt++))
    done
    
    # Check frontend
    if curl -s -f http://localhost:${FRONTEND_PORT:-3000} &> /dev/null; then
        log_success "Frontend is responding"
    else
        log_warning "Frontend is not responding on port ${FRONTEND_PORT:-3000}"
    fi
}

# Clean up old Docker images
cleanup_images() {
    log_info "Cleaning up old Docker images..."
    
    # Remove unused images
    local removed_count=$(docker image prune -a -f 2>&1 | grep -E "deleted|reclaimed" | wc -l)
    
    if [[ $removed_count -gt 0 ]]; then
        log_success "Removed $removed_count old/unused Docker images"
    else
        log_info "No old images to remove"
    fi
    
    # Remove unused volumes (with caution)
    local volumes_removed=$(docker volume prune -f 2>&1 | grep -E "deleted|reclaimed" | wc -l)
    if [[ $volumes_removed -gt 0 ]]; then
        log_success "Removed $volumes_removed unused Docker volumes"
    fi
    
    # Remove stopped containers
    local containers_removed=$(docker container prune -f 2>&1 | grep -E "deleted|reclaimed" | wc -l)
    if [[ $containers_removed -gt 0 ]]; then
        log_success "Removed $containers_removed stopped containers"
    fi
}

# Clean up old logs
cleanup_logs() {
    log_info "Cleaning up old deployment logs..."
    
    find /var/log -name "wowrussian-deploy-*.log" -mtime +$RETENTION_DAYS -delete
    log_success "Old logs cleaned (retaining $RETENTION_DAYS days)"
}

# Show deployment summary
show_summary() {
    log_info "=== Deployment Summary ==="
    echo ""
    echo "Application: $APP_NAME"
    echo "Deployed at: $(date)"
    echo "Deploy directory: $DEPLOY_DIR"
    echo "Log file: $LOG_FILE"
    echo ""
    echo "Running containers:"
    $DOCKER_COMPOSE ps
    echo ""
    echo "Disk usage:"
    df -h . | tail -1
    echo ""
    echo "Docker disk usage:"
    docker system df
    echo ""
    log_success "Deployment completed successfully!"
}

# Main deployment function
main() {
    log_info "Starting deployment of $APP_NAME"
    log_info "Deploy directory: $DEPLOY_DIR"
    log_info "Log file: $LOG_FILE"
    
    # Navigate to deploy directory
    cd "$DEPLOY_DIR" || {
        log_error "Cannot change to deployment directory: $DEPLOY_DIR"
        exit 1
    }
    
    # Load environment variables
    load_env
    
    # Execute deployment steps
    pre_deploy_check
    backup_data
    git_pull
    stop_containers
    build_and_start
    wait_for_health
    cleanup_images
    cleanup_logs
    show_summary
    
    log_success "Deployment finished!"
}

# Run main function
main "$@"
