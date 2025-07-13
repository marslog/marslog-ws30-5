#!/bin/bash

# MARSLOG Login Performance Monitor
# ตรวจสอบ performance bottlenecks ในระบบ login

echo "🚀 MARSLOG Login Performance Analysis"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to check login page response time
check_login_response_time() {
    echo -e "\n${BLUE}⏱️  Login Page Response Times:${NC}"
    echo "==============================="
    
    for i in {1..5}; do
        echo -n "Test $i: "
        time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:8885/auth/login)
        if (( $(echo "$time < 0.5" | bc -l) )); then
            echo -e "${GREEN}${time}s (Excellent)${NC}"
        elif (( $(echo "$time < 1.0" | bc -l) )); then
            echo -e "${YELLOW}${time}s (Good)${NC}"
        else
            echo -e "${RED}${time}s (Needs improvement)${NC}"
        fi
    done
}

# Function to check PHP-FPM performance
check_php_performance() {
    echo -e "\n${BLUE}🐘 PHP-FPM Performance:${NC}"
    echo "======================="
    
    if docker exec marslog-php php -v >/dev/null 2>&1; then
        # Check PHP-FPM status
        echo "PHP-FPM Status:"
        docker exec marslog-php pgrep php-fpm | wc -l | xargs echo "  Active processes:"
        
        # Check memory usage
        mem_usage=$(docker stats marslog-php --no-stream --format "table {{.MemUsage}}" | tail -1)
        echo "  Memory usage: $mem_usage"
        
        # Check OPcache status
        opcache_hits=$(docker exec marslog-php php -r "
        \$status = opcache_get_status();
        if (\$status && isset(\$status['opcache_statistics'])) {
            \$stats = \$status['opcache_statistics'];
            \$hit_rate = (\$stats['hits'] / (\$stats['hits'] + \$stats['misses'])) * 100;
            echo 'Hit rate: ' . round(\$hit_rate, 2) . '%';
        } else {
            echo 'OPcache not available';
        }
        " 2>/dev/null || echo "  OPcache: Not available")
        echo "  $opcache_hits"
        
    else
        echo -e "${RED}❌ Cannot connect to PHP container${NC}"
    fi
}

# Function to check database performance
check_database_performance() {
    echo -e "\n${BLUE}🏠 Database Performance:${NC}"
    echo "======================="
    
    # Test ClickHouse response time
    echo "ClickHouse Response Time:"
    start_time=$(date +%s.%N)
    if docker exec marslog-clickhouse clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then
        end_time=$(date +%s.%N)
        response_time=$(echo "$end_time - $start_time" | bc)
        echo "  Query time: ${response_time}s"
        
        # Check active connections
        connections=$(docker exec marslog-clickhouse clickhouse-client --query "SELECT value FROM system.metrics WHERE metric = 'TCPConnection'" 2>/dev/null || echo "0")
        echo "  Active connections: $connections"
    else
        echo -e "  ${RED}❌ ClickHouse not responding${NC}"
    fi
    
    # Test Redis response time
    echo "Redis Response Time:"
    start_time=$(date +%s.%N)
    if docker exec marslog-redis redis-cli ping >/dev/null 2>&1; then
        end_time=$(date +%s.%N)
        response_time=$(echo "$end_time - $start_time" | bc)
        echo "  Ping time: ${response_time}s"
        
        # Check memory usage
        memory_usage=$(docker exec marslog-redis redis-cli info memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
        echo "  Memory usage: $memory_usage"
        
        # Check connected clients
        clients=$(docker exec marslog-redis redis-cli info clients | grep "connected_clients" | cut -d: -f2 | tr -d '\r')
        echo "  Connected clients: $clients"
    else
        echo -e "  ${RED}❌ Redis not responding${NC}"
    fi
}

# Function to check nginx performance
check_nginx_performance() {
    echo -e "\n${BLUE}🌐 Nginx Performance:${NC}"
    echo "===================="
    
    # Check nginx access logs for response times
    if docker exec marslog-nginx test -f /var/log/nginx/access.log; then
        echo "Recent response times from access log:"
        docker exec marslog-nginx tail -10 /var/log/nginx/access.log | while read line; do
            # Extract response time from log if available
            echo "  $line" | grep -o '[0-9]\+\.[0-9]\+' | tail -1 | xargs echo "    Response time: "
        done 2>/dev/null || echo "  No response time data available"
    fi
    
    # Check nginx worker processes
    workers=$(docker exec marslog-nginx pgrep nginx | wc -l)
    echo "  Active nginx workers: $workers"
    
    # Check if gzip is working
    gzip_test=$(curl -H "Accept-Encoding: gzip" -s -I http://localhost:8885/auth/login | grep "Content-Encoding: gzip")
    if [[ -n "$gzip_test" ]]; then
        echo -e "  Gzip compression: ${GREEN}Enabled${NC}"
    else
        echo -e "  Gzip compression: ${YELLOW}Disabled${NC}"
    fi
}

# Function to check asset loading performance
check_asset_performance() {
    echo -e "\n${BLUE}📦 Asset Loading Performance:${NC}"
    echo "============================="
    
    # Check CSS loading time
    css_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:8885/assets/css/login.css 2>/dev/null || echo "N/A")
    echo "  CSS loading time: ${css_time}s"
    
    # Check JS loading time
    js_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:8885/assets/js/login.js 2>/dev/null || echo "N/A")
    echo "  JS loading time: ${js_time}s"
    
    # Check image loading time
    img_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:8885/assets/image/MARSLOGS.png 2>/dev/null || echo "N/A")
    echo "  Logo loading time: ${img_time}s"
    
    # Check total page size
    total_size=$(curl -s http://localhost:8885/auth/login | wc -c)
    echo "  Page size: $(echo "scale=2; $total_size/1024" | bc)KB"
}

# Function to check authentication performance
check_auth_performance() {
    echo -e "\n${BLUE}🔐 Authentication Performance:${NC}"
    echo "=============================="
    
    # Test authentication endpoint response time
    auth_time=$(curl -o /dev/null -s -w "%{time_total}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"test"}' \
        http://localhost:8885/backend/auth/authenticate.php 2>/dev/null || echo "N/A")
    echo "  Auth endpoint response: ${auth_time}s"
    
    # Check session handler file size
    session_file_size=$(ls -la ../backend/auth/session_handler.php | awk '{print $5}')
    echo "  Session handler size: $(echo "scale=2; $session_file_size/1024" | bc)KB"
    
    # Check user data file size
    user_file_size=$(ls -la ../data/users/users.json | awk '{print $5}' 2>/dev/null || echo "0")
    echo "  User data size: $(echo "scale=2; $user_file_size/1024" | bc)KB"
}

# Function to provide optimization recommendations
show_optimization_recommendations() {
    echo -e "\n${BLUE}💡 Performance Optimization Recommendations:${NC}"
    echo "============================================="
    
    echo "1. 🚀 Frontend Optimizations:"
    echo "   - Implement lazy loading for images"
    echo "   - Minify CSS and JavaScript files"
    echo "   - Use local fonts instead of CDN"
    echo "   - Implement service worker for caching"
    
    echo "2. 🐘 Backend Optimizations:"
    echo "   - Enable PHP JIT compilation"
    echo "   - Optimize session storage with Redis"
    echo "   - Implement database connection pooling"
    echo "   - Add response caching for static content"
    
    echo "3. 🌐 Infrastructure Optimizations:"
    echo "   - Enable HTTP/2 in nginx"
    echo "   - Implement CDN for static assets"
    echo "   - Add load balancing for high traffic"
    echo "   - Monitor and optimize Docker resources"
}

# Main execution
main() {
    check_login_response_time
    check_php_performance
    check_database_performance
    check_nginx_performance
    check_asset_performance
    check_auth_performance
    show_optimization_recommendations
    
    echo -e "\n${GREEN}✅ Performance analysis completed!${NC}"
    echo "Check the results above for bottlenecks and optimization opportunities."
}

# Run main function
main "$@"
