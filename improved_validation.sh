#!/bin/bash

# 🎯 IMPROVED BACKEND VALIDATION
# Rate limiting friendly validation script

echo "🎯 IMPROVED PRACTICE BOOKING SYSTEM VALIDATION"
echo "=============================================="

# Set development environment variables
export TESTING=false
export ENVIRONMENT=development
export DEBUG=true
export ENABLE_RATE_LIMITING=false

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if server is running
if curl -s http://localhost:8000/health > /dev/null; then
    log_success "Server is running"
else
    log_error "Server is not running!"
    log_info "Start server with: uvicorn app.main:app --reload"
    exit 1
fi

# Basic tests with delays to avoid rate limiting
log_info "Running improved validation tests..."

echo ""
echo "1. Health Check"
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    log_success "Health endpoint working"
else
    log_error "Health endpoint failed"
fi

sleep 1

echo ""
echo "2. Detailed Health Check" 
HEALTH_DETAILED=$(curl -s http://localhost:8000/health/detailed)
if echo "$HEALTH_DETAILED" | grep -q "database"; then
    log_success "Detailed health endpoint working"
    log_info "Database status included"
else
    log_error "Detailed health endpoint failed"
fi

sleep 1

echo ""
echo "3. API Documentation"
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$DOCS_STATUS" = "200" ]; then
    log_success "API documentation available"
else
    log_error "API documentation failed"
fi

sleep 1

echo ""
echo "4. Authentication Test"
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@company.com", "password": "admin123"}')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    log_success "Authentication working"
    TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
    
    sleep 1
    
    echo ""
    echo "5. Authenticated API Test"
    USERS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/users/)
    if echo "$USERS_RESPONSE" | grep -q "users"; then
        log_success "User management API working"
    else
        log_error "User management API failed"
    fi
else
    log_error "Authentication failed"
    log_info "Response: $LOGIN_RESPONSE"
fi

sleep 1

echo ""
echo "6. Rate Limiting Test (Should NOT block)"
for i in {1..5}; do
    HEALTH_RAPID=$(curl -s http://localhost:8000/health)
    if echo "$HEALTH_RAPID" | grep -q "healthy"; then
        log_success "Request $i successful"
    else
        log_error "Request $i failed - rate limiting too strict"
    fi
    sleep 0.2
done

echo ""
echo "=============================================="
log_success "Improved validation completed!"
echo ""
log_info "API Documentation: http://localhost:8000/docs"
log_info "Health Monitoring: http://localhost:8000/health/detailed"
echo ""
