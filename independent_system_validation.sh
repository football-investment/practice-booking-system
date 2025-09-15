#!/bin/bash

# FÜGGETLEN RENDSZER VALIDÁCIÓ - Claude Code claims ellenőrzése
# Cél: Valós helyzet feltérképezése fresh tesztekkel

echo "=========================================="
echo "🧪 FÜGGETLEN RENDSZER VALIDÁCIÓ"
echo "=========================================="
echo "Dátum: $(date)"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

test_pass() {
    echo -e "${GREEN}✅ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    echo -e "${YELLOW}   Detail: $2${NC}"
    ((TESTS_FAILED++))
}

test_info() {
    echo -e "${BLUE}ℹ️  INFO: $1${NC}"
}

# PHASE 1: BACKEND STATUS CHECK
echo "===========================================" 
echo "PHASE 1: BACKEND STATUS ELLENŐRZÉS"
echo "==========================================="
echo ""

test_info "Backend server állapot ellenőrzése..."

# Check if backend is running
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)

if [ "$BACKEND_STATUS" = "200" ]; then
    test_pass "Backend server fut (port 8000)"
else
    test_fail "Backend server nem fut" "HTTP status: $BACKEND_STATUS"
    echo ""
    echo "❗ Backend elindítása szükséges a teszteléshez:"
    echo "   uvicorn app.main:app --host localhost --port 8000 --reload"
    exit 1
fi

# PHASE 2: AUTHENTICATION TEST
echo ""
echo "==========================================="
echo "PHASE 2: AUTHENTICATION TESZT"
echo "==========================================="
echo ""

test_info "Admin bejelentkezés tesztelése..."

# Get admin token
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"admin123"}' 2>/dev/null)

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
    test_pass "Admin authentication sikeres"
    test_info "Token hossza: ${#TOKEN} karakter"
else
    test_fail "Admin authentication sikertelen" "Response: $AUTH_RESPONSE"
    exit 1
fi

# PHASE 3: ANALYTICS ENDPOINTS VALÓS TESZTELÉSE
echo ""
echo "==========================================="
echo "PHASE 3: ANALYTICS ENDPOINTS VALÓS TESZT"
echo "==========================================="
echo ""

test_info "Mind az 5 analytics endpoint tesztelése fresh token-nel..."

# Fresh token for each test to avoid expiry issues
get_fresh_token() {
    curl -s -X POST http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"email":"admin@company.com","password":"admin123"}' | \
      jq -r '.access_token' 2>/dev/null
}

# Test each analytics endpoint
ENDPOINTS=("metrics" "attendance" "bookings" "utilization" "users")
ENDPOINT_RESULTS=()

echo ""
echo "📊 ANALYTICS ENDPOINT EREDMÉNYEK:"
echo "--------------------------------"

for endpoint in "${ENDPOINTS[@]}"; do
    test_info "Tesztelés: /api/v1/analytics/$endpoint"
    
    # Get fresh token
    FRESH_TOKEN=$(get_fresh_token)
    
    # Test endpoint
    HTTP_CODE=$(curl -s -o /tmp/endpoint_response_$endpoint.json -w "%{http_code}" \
        -H "Authorization: Bearer $FRESH_TOKEN" \
        "http://localhost:8000/api/v1/analytics/$endpoint" 2>/dev/null)
    
    # Check response
    if [ "$HTTP_CODE" = "200" ]; then
        # Check if response contains error
        ERROR_CHECK=$(cat /tmp/endpoint_response_$endpoint.json | jq -r '.error // empty' 2>/dev/null)
        if [ -n "$ERROR_CHECK" ]; then
            test_fail "/analytics/$endpoint" "HTTP 200 de error a válaszban: $ERROR_CHECK"
            ENDPOINT_RESULTS+=("$endpoint:FAIL")
        else
            test_pass "/analytics/$endpoint (HTTP 200, valid JSON)"
            ENDPOINT_RESULTS+=("$endpoint:PASS")
        fi
    else
        # Get error details
        ERROR_MSG=$(cat /tmp/endpoint_response_$endpoint.json 2>/dev/null)
        test_fail "/analytics/$endpoint" "HTTP $HTTP_CODE - $ERROR_MSG"
        ENDPOINT_RESULTS+=("$endpoint:FAIL")
    fi
    
    # Small delay between tests
    sleep 1
done

# PHASE 4: SERVER LOG ANALYSIS
echo ""
echo "==========================================="
echo "PHASE 4: SERVER LOG HIBÁK ELLENŐRZÉSE"
echo "==========================================="
echo ""

test_info "Friss 500-as hibák keresése a server log-ban..."

# Check for recent 500 errors in logs
if [ -f "logs/app.log" ]; then
    # Get recent 500 errors (last 100 lines)
    RECENT_500_ERRORS=$(tail -100 logs/app.log | grep -E "(ERROR|500)" | wc -l)
    RECENT_ANALYTICS_ERRORS=$(tail -100 logs/app.log | grep -E "(analytics.*ERROR|analytics.*500)" | wc -l)
    
    if [ "$RECENT_500_ERRORS" -eq 0 ]; then
        test_pass "Nincs friss 500-as hiba a log-ban"
    else
        test_fail "Friss 500-as hibák találhatók" "$RECENT_500_ERRORS darab az utolsó 100 sorban"
        
        echo ""
        echo "🔍 FRISS HIBÁK RÉSZLETEI:"
        echo "------------------------"
        tail -100 logs/app.log | grep -E "(ERROR|500)" | tail -5
    fi
    
    if [ "$RECENT_ANALYTICS_ERRORS" -eq 0 ]; then
        test_pass "Nincs friss analytics hiba"
    else
        test_fail "Friss analytics hibák" "$RECENT_ANALYTICS_ERRORS darab"
    fi
else
    test_fail "logs/app.log fájl nem található" "Log fájl hiányzik"
fi

# PHASE 5: DATABASE ENUM CHECK
echo ""
echo "==========================================="
echo "PHASE 5: DATABASE ENUM KONZISZTENCIA"
echo "==========================================="
echo ""

test_info "BookingStatus enum használat ellenőrzése kódban..."

# Check BookingStatus usage in analytics.py
BOOKING_STATUS_USAGE=$(grep -n "BookingStatus\." app/api/api_v1/endpoints/analytics.py 2>/dev/null | wc -l)
STRING_STATUS_USAGE=$(grep -n "'confirmed'" app/api/api_v1/endpoints/analytics.py 2>/dev/null | wc -l)

if [ "$BOOKING_STATUS_USAGE" -gt 0 ]; then
    test_pass "BookingStatus enum használat található ($BOOKING_STATUS_USAGE sor)"
else
    test_fail "BookingStatus enum használat nem található" "Lehet hogy string-et használ"
fi

if [ "$STRING_STATUS_USAGE" -eq 0 ]; then
    test_pass "Nincs hardcoded 'confirmed' string"
else
    test_fail "Hardcoded 'confirmed' string-ek találhatók" "$STRING_STATUS_USAGE darab"
    echo "🔍 Problémás sorok:"
    grep -n "'confirmed'" app/api/api_v1/endpoints/analytics.py 2>/dev/null || echo "Grep sikertelen"
fi

# PHASE 6: FRONTEND STATUS
echo ""
echo "==========================================="
echo "PHASE 6: FRONTEND STATUS"
echo "==========================================="
echo ""

test_info "Frontend server ellenőrzése..."

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null)

if [ "$FRONTEND_STATUS" = "200" ]; then
    test_pass "Frontend server fut (port 3000)"
else
    test_fail "Frontend server nem fut vagy hibás" "HTTP status: $FRONTEND_STATUS"
fi

# PHASE 7: END-TO-END INTEGRATION TEST
echo ""
echo "==========================================="
echo "PHASE 7: INTEGRATION TESZT"
echo "==========================================="
echo ""

test_info "Összekapcsolt rendszer tesztelése..."

# Test a complete workflow: login -> get users -> get sessions
WORKFLOW_TOKEN=$(get_fresh_token)

if [ -n "$WORKFLOW_TOKEN" ]; then
    # Test users endpoint
    USERS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $WORKFLOW_TOKEN" \
        http://localhost:8000/api/v1/users/ 2>/dev/null)
    
    if [ "$USERS_STATUS" = "200" ]; then
        test_pass "Users endpoint (workflow teszt)"
    else
        test_fail "Users endpoint (workflow teszt)" "HTTP $USERS_STATUS"
    fi
    
    # Test sessions endpoint  
    SESSIONS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $WORKFLOW_TOKEN" \
        http://localhost:8000/api/v1/sessions/ 2>/dev/null)
    
    if [ "$SESSIONS_STATUS" = "200" ]; then
        test_pass "Sessions endpoint (workflow teszt)"
    else
        test_fail "Sessions endpoint (workflow teszt)" "HTTP $SESSIONS_STATUS"
    fi
else
    test_fail "Workflow teszt" "Token megszerzése sikertelen"
fi

# FINAL RESULTS
echo ""
echo "==========================================="
echo "🎯 VÉGSŐ EREDMÉNYEK"
echo "==========================================="
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
else
    SUCCESS_RATE=0
fi

echo "📊 TESZT STATISZTIKÁK:"
echo "  ✅ Sikeres tesztek: $TESTS_PASSED"
echo "  ❌ Sikertelen tesztek: $TESTS_FAILED"
echo "  📈 Sikerességi arány: $SUCCESS_RATE%"
echo ""

echo "🔍 ANALYTICS ENDPOINT ÖSSZESÍTŐ:"
echo "--------------------------------"
ANALYTICS_PASS=0
ANALYTICS_FAIL=0

for result in "${ENDPOINT_RESULTS[@]}"; do
    endpoint=$(echo $result | cut -d: -f1)
    status=$(echo $result | cut -d: -f2)
    if [ "$status" = "PASS" ]; then
        echo -e "  ✅ /analytics/$endpoint"
        ((ANALYTICS_PASS++))
    else
        echo -e "  ❌ /analytics/$endpoint"
        ((ANALYTICS_FAIL++))
    fi
done

echo ""
echo "📋 CLAUDE CODE CLAIMS VALIDÁCIÓ:"
echo "--------------------------------"

# Validate Claude Code's specific claims
if [ $ANALYTICS_PASS -eq 5 ]; then
    echo -e "${GREEN}✅ Claude Code claim: '5/5 analytics endpoints working' - IGAZ${NC}"
else
    echo -e "${RED}❌ Claude Code claim: '5/5 analytics endpoints working' - HAMIS${NC}"
    echo -e "   Valóság: $ANALYTICS_PASS/5 endpoint működik"
fi

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Claude Code claim: 'No system errors' - IGAZ${NC}"
else
    echo -e "${RED}❌ Claude Code claim: 'No system errors' - HAMIS${NC}"
    echo -e "   Valóság: $TESTS_FAILED teszt failed"
fi

echo ""
echo "🎯 ÖSSZESÍTŐ EREDMÉNY:"
if [ $SUCCESS_RATE -ge 90 ]; then
    echo -e "${GREEN}🎉 RENDSZER KIVÁLÓ ÁLLAPOTBAN (${SUCCESS_RATE}%)${NC}"
    echo -e "${GREEN}   Claude Code claims nagyrészt igaznak tűnnek${NC}"
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠️  RENDSZER JÓ ÁLLAPOTBAN (${SUCCESS_RATE}%)${NC}"
    echo -e "${YELLOW}   Kisebb problémák vannak${NC}"
else
    echo -e "${RED}🚨 RENDSZER PROBLÉMÁS ÁLLAPOTBAN (${SUCCESS_RATE}%)${NC}"
    echo -e "${RED}   Jelentős hibák szükséges javítani${NC}"
fi

echo ""
echo "💡 KÖVETKEZŐ LÉPÉSEK:"
if [ $ANALYTICS_FAIL -gt 0 ]; then
    echo "  - Javítsd a hibás analytics endpoint-okat ($ANALYTICS_FAIL darab)"
fi
if [ $TESTS_FAILED -gt 2 ]; then
    echo "  - Rendszerszintű debug szükséges"
fi

echo ""
echo "=========================================="
echo "Teszt befejezve: $(date)"
echo "=========================================="

# Cleanup temp files
rm -f /tmp/endpoint_response_*.json 2>/dev/null

exit 0