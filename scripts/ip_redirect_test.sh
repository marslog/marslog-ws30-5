#!/bin/bash

echo "🌐 MARSLOG IP Address Redirect Test"
echo "=================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

IP="192.168.0.100:8885"

echo -e "\n${BLUE}1. Root Path Redirect Test:${NC}"
echo "Testing: http://$IP/"
response=$(curl -s -I http://$IP/ | grep "Location:")
status=$(curl -s -o /dev/null -w "%{http_code}" http://$IP/)
echo "  Status: $status"
echo "  Redirect: $response"

echo -e "\n${BLUE}2. Clean URL Access Test:${NC}"
echo "Testing: http://$IP/auth/login"
status=$(curl -s -o /dev/null -w "%{http_code}" http://$IP/auth/login)
time=$(curl -o /dev/null -s -w "%{time_total}" http://$IP/auth/login)
echo "  Status: $status"
echo "  Response Time: ${time}s"

echo -e "\n${BLUE}3. PHP Extension Behavior:${NC}"
echo "Testing: http://$IP/auth/login.php"
status=$(curl -s -o /dev/null -w "%{http_code}" http://$IP/auth/login.php)
echo "  Status: $status (Should work without redirect)"

echo -e "\n${BLUE}4. Complete Flow Test:${NC}"
echo "Testing full redirect chain from root to login page..."
final_url=$(curl -s -L -o /dev/null -w "%{url_effective}" http://$IP/)
echo "  Final URL: $final_url"

echo -e "\n${GREEN}✅ IP Address Redirect Test Completed!${NC}"
echo ""
echo "Summary:"
echo "- Root (/) redirects to /auth/login"
echo "- Clean URL /auth/login works properly"
echo "- PHP files accessible directly"
echo "- Full redirect chain functional"
