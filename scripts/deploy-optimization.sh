#!/bin/bash

# MARSLOG Performance Deployment Script
# Deploys optimized configurations to production

echo "🚀 MARSLOG Performance Optimization Deployment"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DOCKER_DIR="/opt/marslog/app/docker"
BACKUP_DIR="/opt/marslog/backups/$(date +%Y%m%d_%H%M%S)"

# Function to create backup
create_backup() {
    echo -e "\n${BLUE}💾 Creating backup...${NC}"
    mkdir -p "$BACKUP_DIR"
    
    # Backup current configurations
    if [[ -f "$DOCKER_DIR/docker-compose.yml" ]]; then
        cp "$DOCKER_DIR/docker-compose.yml" "$BACKUP_DIR/"
        echo "✅ Backed up docker-compose.yml"
    fi
    
    if [[ -f "$DOCKER_DIR/nginx/nginx.conf" ]]; then
        cp "$DOCKER_DIR/nginx/nginx.conf" "$BACKUP_DIR/"
        echo "✅ Backed up nginx.conf"
    fi
    
    if [[ -f "$DOCKER_DIR/flask-api/Dockerfile" ]]; then
        cp "$DOCKER_DIR/flask-api/Dockerfile" "$BACKUP_DIR/"
        echo "✅ Backed up Dockerfile"
    fi
    
    echo -e "💾 Backup created at: ${GREEN}$BACKUP_DIR${NC}"
}

# Function to deploy PHP optimization
deploy_php_optimization() {
    echo -e "\n${BLUE}�� Deploying PHP optimization...${NC}"
    
    # Create PHP optimization directory
    mkdir -p "$DOCKER_DIR/php-optimization"
    
    # Copy optimized PHP configuration
    cat > "$DOCKER_DIR/php-optimization/php.ini" << 'PHPINI'
[PHP]
; Performance Optimizations for MARSLOG-ClickHouse
memory_limit = 512M
upload_max_filesize = 64M
post_max_size = 128M
max_execution_time = 300
max_input_time = 300
max_input_vars = 3000

; Enable JIT Compilation for performance boost
opcache.enable=1
opcache.enable_cli=1
opcache.memory_consumption=256
opcache.interned_strings_buffer=64
opcache.max_accelerated_files=20000
opcache.revalidate_freq=2
opcache.save_comments=1
opcache.fast_shutdown=1
opcache.validate_timestamps=1
opcache.jit_buffer_size=100M
opcache.jit=1255

; Session Configuration
session.save_handler = redis
session.save_path = "tcp://redis:6379"
session.gc_maxlifetime = 3600
session.cookie_lifetime = 3600
session.cookie_secure = 0
session.cookie_httponly = 1

; Error Handling
display_errors = Off
log_errors = On
error_log = /var/log/php_errors.log

; Security
expose_php = Off
allow_url_fopen = Off
allow_url_include = Off

; Date
date.timezone = Asia/Bangkok
PHPINI

    echo "✅ PHP optimization files deployed"
}

# Function to deploy optimized docker-compose
deploy_docker_compose() {
    echo -e "\n${BLUE}🐳 Deploying optimized Docker Compose...${NC}"
    
    cat > "$DOCKER_DIR/docker-compose-optimized.yml" << 'DOCKERCOMPOSE'
version: '3.8'

services:
  # ClickHouse Database - Optimized
  clickhouse:
    image: yandex/clickhouse-server:25.6.3
    container_name: marslog-clickhouse
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - ./clickhouse/init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./clickhouse/users.xml:/etc/clickhouse-server/users.xml
      - clickhouse_data:/var/lib/clickhouse
    environment:
      CLICKHOUSE_DB: marslog
      CLICKHOUSE_USER: marslog
      CLICKHOUSE_PASSWORD: marslog123
      CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: 1
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    restart: unless-stopped

  # Redis Cache - Optimized
  redis:
    image: redis:7-alpine
    container_name: marslog-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    restart: unless-stopped

  # Nginx - Optimized
  nginx:
    image: nginx:alpine
    container_name: marslog-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ../:/var/www/html:ro
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx-logs:/var/log/nginx
    depends_on:
      - flask-api
    restart: unless-stopped

  # Flask API - Optimized
  flask-api:
    build:
      context: ./flask-api
      dockerfile: Dockerfile
    container_name: marslog-flask-api
    ports:
      - "5000:5000"
    volumes:
      - ../logs:/app/logs
    environment:
      - FLASK_ENV=production
      - CLICKHOUSE_HOST=clickhouse
      - CLICKHOUSE_PORT=8123
      - CLICKHOUSE_USER=marslog
      - CLICKHOUSE_PASSWORD=marslog123
      - CLICKHOUSE_DB=marslog
    depends_on:
      - clickhouse
    restart: unless-stopped

volumes:
  clickhouse_data:
    driver: local
  redis_data:
    driver: local

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
DOCKERCOMPOSE

    echo "✅ Optimized Docker Compose deployed"
}

# Function to optimize Nginx configuration
optimize_nginx() {
    echo -e "\n${BLUE}🌐 Optimizing Nginx configuration...${NC}"
    
    # Backup original nginx.conf
    cp "$DOCKER_DIR/nginx/nginx.conf" "$DOCKER_DIR/nginx/nginx.conf.backup"
    
    # Create optimized nginx.conf
    cat > "$DOCKER_DIR/nginx/nginx.conf" << 'NGINXCONF'
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 30;
    keepalive_requests 1000;
    types_hash_max_size 2048;
    server_tokens off;
    
    # Buffer sizes
    client_body_buffer_size 16K;
    client_header_buffer_size 1k;
    client_max_body_size 64M;
    large_client_header_buffers 4 16k;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json
        image/svg+xml;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Cache for static files
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    server {
        listen 80;
        server_name _;
        root /var/www/html;
        index index.php index.html;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Static file caching
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary Accept-Encoding;
            access_log off;
        }

        # API endpoints
        location /api/ {
            proxy_pass http://flask-api:5000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300;
            proxy_connect_timeout 300;
            proxy_send_timeout 300;
        }

        # Security: deny access to sensitive files
        location ~ /\. {
            deny all;
            access_log off;
            log_not_found off;
        }

        location ~ /(config|data)/.*\.json$ {
            deny all;
            access_log off;
            log_not_found off;
        }

        # Default location
        location / {
            try_files $uri $uri/ =404;
        }
    }
}
NGINXCONF

    echo "✅ Nginx optimization completed"
}

# Function to restart services
restart_services() {
    echo -e "\n${BLUE}🔄 Restarting services with optimizations...${NC}"
    
    cd "$DOCKER_DIR"
    
    # Stop current services
    echo "🛑 Stopping current services..."
    docker-compose down
    
    # Start with optimized configuration
    echo "🚀 Starting optimized services..."
    docker-compose -f docker-compose-optimized.yml up -d --build
    
    # Wait for services to start
    echo "⏳ Waiting for services to be ready..."
    sleep 30
    
    # Check if services are running
    echo "🔍 Checking service status..."
    docker-compose -f docker-compose-optimized.yml ps
}

# Function to verify deployment
verify_deployment() {
    echo -e "\n${BLUE}✅ Verifying deployment...${NC}"
    
    # Test web access
    if curl -s http://localhost/ >/dev/null; then
        echo -e "✅ Web server: ${GREEN}Accessible${NC}"
    else
        echo -e "❌ Web server: ${RED}Not accessible${NC}"
    fi
    
    # Test ClickHouse
    if docker exec marslog-clickhouse clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then
        echo -e "✅ ClickHouse: ${GREEN}Connected${NC}"
    else
        echo -e "❌ ClickHouse: ${RED}Connection failed${NC}"
    fi
    
    # Test Redis
    if docker exec marslog-redis redis-cli ping >/dev/null 2>&1; then
        echo -e "✅ Redis: ${GREEN}Connected${NC}"
    else
        echo -e "❌ Redis: ${RED}Connection failed${NC}"
    fi
}

# Function to show next steps
show_next_steps() {
    echo -e "\n${BLUE}🎯 Next Steps:${NC}"
    echo "============="
    echo "1. 🔍 Check logs for any issues"
    echo "2. 🧪 Test all functionality thoroughly"
    echo "3. 📈 Monitor system performance"
    echo ""
    echo -e "📍 Backup location: ${GREEN}$BACKUP_DIR${NC}"
}

# Main execution
main() {
    echo "Starting MARSLOG Performance Optimization Deployment..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ This script must be run as root${NC}"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker ps >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running${NC}"
        exit 1
    fi
    
    create_backup
    deploy_php_optimization
    deploy_docker_compose
    optimize_nginx
    restart_services
    verify_deployment
    show_next_steps
    
    echo -e "\n${GREEN}🎉 Performance optimization deployment completed!${NC}"
    echo "=================================================="
}

# Run main function
main "$@"
