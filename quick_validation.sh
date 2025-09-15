#!/bin/bash

# Quick 5-minute validation of Claude Code's key claims

echo "⚡ QUICK SYSTEM VALIDATION - Claude Code Claims Test"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ $1${NC}"
        ((FAILED++))
    fi
}

echo ""
echo "1. SERVER HEALTH TEST:"
echo "---------------------"
curl -s http://localhost:8000/health | grep -q "healthy"
test_result "Basic health endpoint"

curl -s http://localhost:8000/health/detailed | grep -q "database"
test_result "Detailed health with database check"

echo ""
echo "2. AUTHENTICATION TEST:"
echo "-----------------------"
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@company.com","password":"admin123"}' | \
    jq -r '.access_token' 2>/dev/null)

if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    echo -e "${GREEN}✅ Admin login successful${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Admin login failed${NC}"
    ((FAILED++))
fi

echo ""
echo "3. API ENDPOINTS TEST:"
echo "---------------------"
if [ -n "$ADMIN_TOKEN" ]; then
    # Test user list
    curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
        http://localhost:8000/api/v1/users/ | grep -q "total"
    test_result "Users list endpoint"
    
    # Test semesters
    curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
        http://localhost:8000/api/v1/semesters/ | grep -q "semesters"
    test_result "Semesters list endpoint"
    
    # Test sessions
    curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
        http://localhost:8000/api/v1/sessions/ | grep -q "sessions"
    test_result "Sessions list endpoint"
else
    echo -e "${RED}❌ Cannot test endpoints without admin token${NC}"
    ((FAILED+=3))
fi

echo ""
echo "4. RATE LIMITING TEST:"
echo "---------------------"
# Test that rate limiting doesn't break normal usage
for i in {1..3}; do
    curl -s http://localhost:8000/health > /dev/null
    if [ $? -eq 0 ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    fi
done

if [ "$SUCCESS_COUNT" -eq 3 ]; then
    echo -e "${GREEN}✅ Rate limiting allows normal usage${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Rate limiting too restrictive${NC}"
    ((FAILED++))
fi

echo ""
echo "5. API DOCUMENTATION TEST:"
echo "--------------------------"
curl -s http://localhost:8000/docs | grep -q "swagger"
test_result "Swagger UI accessible"

echo ""
echo "=================================================="
echo "QUICK VALIDATION RESULTS:"
echo "=================================================="
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"

TOTAL=$((PASSED + FAILED))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$((PASSED * 100 / TOTAL))
    echo "📊 Success Rate: ${SUCCESS_RATE}%"
    
    if [ $SUCCESS_RATE -ge 80 ]; then
        echo -e "${GREEN}🎉 CLAUDE CODE CLAIMS VALIDATED!${NC}"
        echo "System appears to be working as advertised"
    else
        echo -e "${RED}⚠️  CLAUDE CODE CLAIMS QUESTIONABLE${NC}"
        echo "Significant issues found"
    fi
fi

echo ""
echo "Next steps:"
echo "- Run full journey: ./complete_system_journey.sh"
echo "- Check API docs: http://localhost:8000/docs"
echo "- Monitor health: http://localhost:8000/health/detailed"