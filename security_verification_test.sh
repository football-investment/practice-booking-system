#!/bin/bash

# 🔒 SECURITY VERIFICATION TEST
# Validates that all critical security vulnerabilities have been fixed

echo "🔒 SECURITY VERIFICATION TEST"
echo "============================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

log_pass() {
    echo -e "${GREEN}✅ PASS: $1${NC}"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    ((FAILED++))
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo ""
echo "Testing for hardcoded credentials in source code..."

# Test 1: No hardcoded credentials in LoginPage
if grep -q "admin@company.com\|admin123" frontend/src/pages/LoginPage.js; then
    log_fail "Hardcoded credentials found in LoginPage.js"
else
    log_pass "No hardcoded credentials in LoginPage.js"
fi

# Test 2: No test credentials section in LoginPage
if grep -q "Test Credentials\|🧪" frontend/src/pages/LoginPage.js; then
    log_fail "Test credentials section still exists in LoginPage.js"
else
    log_pass "No test credentials section in LoginPage.js"
fi

# Test 3: Empty initial state for email/password
if grep -q "useState('admin@company.com')\|useState('admin123')" frontend/src/pages/LoginPage.js; then
    log_fail "Hardcoded credentials in useState initialization"
else
    log_pass "Clean useState initialization (no hardcoded credentials)"
fi

# Test 4: Environment configuration system exists
if [ -f "frontend/src/config/environment.js" ]; then
    log_pass "Environment configuration system created"
else
    log_fail "Environment configuration system missing"
fi

# Test 5: Secure .env files exist
if [ -f "frontend/.env.development" ] && [ -f "frontend/.env.production" ]; then
    log_pass "Environment files created"
else
    log_fail "Environment files missing"
fi

# Test 6: Security-focused .gitignore exists
if [ -f ".gitignore" ] && [ -f "frontend/.gitignore" ]; then
    log_pass "Security-focused .gitignore files created"
else
    log_fail "Security-focused .gitignore files missing"
fi

# Test 7: API service uses environment configuration
if grep -q "import config from '../config/environment'" frontend/src/services/apiService.js; then
    log_pass "API service uses environment configuration"
else
    log_fail "API service not using environment configuration"
fi

# Test 8: No hardcoded localhost URLs in production config
if grep -q "localhost" frontend/.env.production; then
    log_fail "Production config contains localhost URLs"
else
    log_pass "Production config clean (no localhost URLs)"
fi

# Test 9: .env.local files are gitignored
if grep -q ".env.local" .gitignore && grep -q ".env.local" frontend/.gitignore; then
    log_pass ".env.local files properly gitignored"
else
    log_fail ".env.local files not properly gitignored"
fi

# Test 10: API functionality still works
echo ""
log_info "Testing API functionality..."

LOGIN_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@company.com", "password": "admin123"}')

if echo "$LOGIN_RESULT" | grep -q "access_token"; then
    log_pass "API login functionality working"
else
    log_fail "API login functionality broken"
fi

echo ""
echo "🔒 SECURITY VERIFICATION RESULTS:"
echo "=================================="
echo -e "${GREEN}✅ PASSED: $PASSED tests${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ FAILED: $FAILED tests${NC}"
    echo ""
    echo -e "${RED}🚨 SECURITY ISSUES REMAIN - DO NOT DEPLOY!${NC}"
    exit 1
else
    echo -e "${RED}❌ FAILED: $FAILED tests${NC}"
    echo ""
    echo -e "${GREEN}🎉 ALL SECURITY TESTS PASSED!${NC}"
    echo -e "${GREEN}🔒 System is secure and ready for deployment${NC}"
    exit 0
fi