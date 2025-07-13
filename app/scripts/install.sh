#!/bin/bash

# MARSLOG Installation Script
# This script sets up MARSLOG with ClickHouse backend

set -e

echo "🚀 Starting MARSLOG Installation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    sudo mkdir -p /opt/marslog/app/frontend
    sudo mkdir -p /opt/marslog/app/backend/data
    sudo mkdir -p /opt/marslog/logs
    
    # Set permissions
    sudo chown -R $USER:$USER /opt/marslog
    sudo chmod -R 755 /opt/marslog
    
    print_success "Directories created"
}

# Copy application files
copy_files() {
    print_status "Copying application files..."
    
    # Get the script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    APP_DIR="$(dirname "$SCRIPT_DIR")"
    
    # Copy frontend files
    if [ -d "$APP_DIR/frontend" ]; then
        sudo cp -r "$APP_DIR/frontend"/* /opt/marslog/app/frontend/
    fi
    
    # Copy backend files
    if [ -d "$APP_DIR/backend" ]; then
        sudo cp -r "$APP_DIR/backend"/* /opt/marslog/app/backend/
    fi
    
    # Copy config files
    if [ -d "$APP_DIR/config" ]; then
        sudo cp -r "$APP_DIR/config" /opt/marslog/app/
    fi
    
    print_success "Application files copied"
}

# Setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    cd "$(dirname "$0")/../docker"
    
    # Copy .env.example to .env if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_status "Created .env file from template"
        fi
    fi
    
    print_success "Environment setup complete"
}

# Build and start containers
start_services() {
    print_status "Building and starting MARSLOG services..."
    
    cd "$(dirname "$0")/../docker"
    
    # Pull latest images
    docker-compose pull
    
    # Build custom images
    docker-compose build
    
    # Start services
    docker-compose up -d
    
    print_success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for ClickHouse
    print_status "Waiting for ClickHouse..."
    until docker exec marslog-clickhouse clickhouse-client --query "SELECT 1" &> /dev/null; do
        sleep 2
    done
    print_success "ClickHouse is ready"
    
    # Wait for Flask API
    print_status "Waiting for Flask API..."
    until curl -s http://localhost:5000/health &> /dev/null; do
        sleep 2
    done
    print_success "Flask API is ready"
    
    # Wait for Nginx
    print_status "Waiting for Nginx..."
    until curl -s http://localhost:8885 &> /dev/null; do
        sleep 2
    done
    print_success "Nginx is ready"
}

# Initialize database
init_database() {
    print_status "Initializing ClickHouse database..."
    
    # Execute initialization script
    docker exec marslog-clickhouse clickhouse-client --multiquery < "$(dirname "$0")/../docker/clickhouse/init.sql"
    
    print_success "Database initialized"
}

# Show final status
show_status() {
    echo ""
    echo "🎉 MARSLOG Installation Complete!"
    echo ""
    echo "📊 Access points:"
    echo "   • Web Interface: http://localhost:8885"
    echo "   • API Endpoint:  http://localhost:5000"
    echo "   • ClickHouse:    http://localhost:8123"
    echo ""
    echo "🔧 Management commands:"
    echo "   • View logs:     docker-compose logs -f"
    echo "   • Stop services: docker-compose down"
    echo "   • Restart:       docker-compose restart"
    echo ""
    echo "📝 Configuration files:"
    echo "   • Environment:   ./docker/.env"
    echo "   • AI Config:     ./config/ai_config.json"
    echo "   • Frontend:      ./config/frontend_config.json"
    echo ""
}

# Main installation process
main() {
    echo "🔍 MARSLOG - ClickHouse Log Management System"
    echo "============================================="
    echo ""
    
    check_docker
    create_directories
    copy_files
    setup_environment
    start_services
    wait_for_services
    init_database
    show_status
    
    print_success "Installation completed successfully!"
}

# Run main function
main "$@"