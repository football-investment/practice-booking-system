#!/bin/bash

# 🎯 COMPLETE SYSTEM VERIFICATION
# Final test of backend + frontend integration

echo "🎯 COMPLETE SYSTEM VERIFICATION"
echo "==============================="
echo "Testing Claude Code handoff implementation"
echo "Verifying backend + frontend integration"
echo ""

# Environment variables
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@company.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
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

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_phase() {
    echo -e "\n${PURPLE}🎯 $1${NC}"
    echo "----------------------------------------"
}

# Initialize counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
ERRORS=()

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_info "Testing: $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        log_success "$test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        ERRORS+=("$test_name")
        return 1
    fi
}

# Phase 1: Backend Verification
log_phase "PHASE 1: Backend Independent Verification"

if [ -f "backend_verification.py" ]; then
    log_info "Running backend verification script..."
    python3 backend_verification.py > backend_verification_output.txt 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Backend verification script completed"
        
        # Check results
        if [ -f "backend_verification_results.json" ]; then
            log_success "Backend verification results generated"
            
            # Extract success rate (simplified)
            if grep -q '"passed":.*[5-9]' backend_verification_results.json; then
                log_success "Backend verification shows good results (5+ tests passed)"
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                log_error "Backend verification shows poor results (< 5 tests passed)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                ERRORS+=("Backend verification poor results")
            fi
        else
            log_error "Backend verification results file not generated"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            ERRORS+=("Backend verification results missing")
        fi
    else
        log_error "Backend verification script failed"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        ERRORS+=("Backend verification script failure")
    fi
else
    log_error "Backend verification script not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    ERRORS+=("Backend verification script missing")
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Phase 2: Database Direct Verification
log_phase "PHASE 2: Database Direct Verification"

if [ -f "database_direct_verification.py" ]; then
    log_info "Running database direct verification..."
    python3 database_direct_verification.py > database_verification_output.txt 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Database verification successful"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "Database verification failed"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        ERRORS+=("Database verification failure")
    fi
else
    log_error "Database verification script not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    ERRORS+=("Database verification script missing")
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Phase 3: Frontend Structure Verification
log_phase "PHASE 3: Frontend Structure Verification"

run_test "Frontend directory exists" "[ -d 'frontend' ]"
run_test "Package.json exists" "[ -f 'frontend/package.json' ]"
run_test "React App.js exists" "[ -f './frontend/src/App.js' ]"
run_test "AuthContext exists" "[ -f 'frontend/src/contexts/AuthContext.js' ]"
run_test "ApiService exists" "[ -f 'frontend/src/services/apiService.js' ]"
run_test "LoginPage exists" "[ -f './frontend/src/pages/LoginPage.js' ]"
run_test "DashboardPage exists" "[ -f './frontend/src/pages/DashboardPage.js' ]"
run_test "AdminPage exists" "[ -f './frontend/src/pages/AdminPage.js' ]"

# Phase 4: Service Verification
log_phase "PHASE 4: Service Status Verification"

run_test "Backend server running" "curl -s http://localhost:8000/health"
run_test "Backend health endpoint" "curl -s http://localhost:8000/health | grep -q healthy"
run_test "Backend API docs" "curl -s http://localhost:8000/docs -o /dev/null"

# Check if frontend is running
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    run_test "Frontend server running" "curl -s http://localhost:3000"
    run_test "Frontend serves content" "curl -s http://localhost:3000 | grep -q 'Practice Booking System'"
else
    log_warning "Frontend not running - starting it for testing..."
    cd frontend && npm start > ../frontend_test.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # Wait for frontend to start
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    
    run_test "Frontend startup successful" "curl -s http://localhost:3000"
fi

# Phase 5: Integration Testing
log_phase "PHASE 5: Integration Testing"

# Test API connectivity through frontend proxy
run_test "Frontend-Backend proxy" "curl -s http://localhost:3000/health"

# Test authentication endpoint
run_test "Auth endpoint accessible" "curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"'$ADMIN_EMAIL'\",\"password\":\"'$ADMIN_PASSWORD'\"}' | grep -q access_token"

# Phase 6: File Content Verification
log_phase "PHASE 6: File Content Verification"

# Check if files have actual content (not empty)
run_test "App.js has content (>1KB)" "[ $(wc -c < ./frontend/src/App.js) -gt 1000 ]"
run_test "LoginPage has content (>2KB)" "[ $(wc -c < ./frontend/src/pages/LoginPage.js) -gt 2000 ]"
run_test "DashboardPage has content (>3KB)" "[ $(wc -c < ./frontend/src/pages/DashboardPage.js) -gt 3000 ]"
run_test "AdminPage has content (>3KB)" "[ $(wc -c < ./frontend/src/pages/AdminPage.js) -gt 3000 ]"

# Generate Final Report
log_phase "FINAL SYSTEM VERIFICATION REPORT"

SUCCESS_RATE=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)

echo ""
echo "📊 VERIFICATION SUMMARY"
echo "======================"
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"  
echo "Failed: $FAILED_TESTS"
echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ $FAILED_TESTS -gt 0 ]; then
    echo "🚨 FAILED TESTS:"
    for error in "${ERRORS[@]}"; do
        echo "   ❌ $error"
    done
    echo ""
fi

# Determine overall status
if (( $(echo "$SUCCESS_RATE >= 90" | bc -l) )); then
    log_success "🎉 SYSTEM VERIFICATION: EXCELLENT (${SUCCESS_RATE}%)"
    echo "✅ Backend + Frontend integration is working"
    echo "✅ Ready for test semester deployment"
    OVERALL_STATUS="EXCELLENT"
elif (( $(echo "$SUCCESS_RATE >= 70" | bc -l) )); then
    log_warning "⚠️  SYSTEM VERIFICATION: GOOD (${SUCCESS_RATE}%)"  
    echo "✅ Core functionality working"
    echo "🔧 Minor issues need attention"
    OVERALL_STATUS="GOOD"
else
    log_error "🚨 SYSTEM VERIFICATION: NEEDS WORK (${SUCCESS_RATE}%)"
    echo "❌ Significant issues found"
    echo "🔧 Major fixes needed before deployment"
    OVERALL_STATUS="NEEDS_WORK"
fi

# Create comprehensive report file
cat > SYSTEM_VERIFICATION_REPORT.md << EOF
# 🎯 Complete System Verification Report

**Date:** $(date)
**Success Rate:** ${SUCCESS_RATE}%
**Overall Status:** $OVERALL_STATUS

## 📊 Test Results Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS  
- **Failed:** $FAILED_TESTS
- **Success Rate:** ${SUCCESS_RATE}%

## 🔍 Verification Phases Completed

- [x] Backend Independent Verification
- [x] Database Direct Verification  
- [x] Frontend Structure Verification
- [x] Service Status Verification
- [x] Integration Testing
- [x] File Content Verification

## 🌐 System URLs

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

## 🔐 Test Credentials

- **Email:** Use configured admin email from environment
- **Password:** Use configured admin password from environment

## 📋 Manual Testing Checklist

After automated verification, complete these manual tests:

- [ ] Login to frontend works
- [ ] Dashboard displays backend data
- [ ] Admin panel accessible (admin users)
- [ ] API status indicators work
- [ ] User can navigate between pages
- [ ] Logout functionality works
- [ ] Backend API endpoints respond through UI

## 🎯 Verdict

**$OVERALL_STATUS** - System verification complete with ${SUCCESS_RATE}% success rate.

$(if [ "$OVERALL_STATUS" = "EXCELLENT" ]; then
    echo "✅ **READY FOR TEST SEMESTER DEPLOYMENT**"
    echo ""
    echo "The backend and frontend integration is working excellently."
    echo "System is ready for limited pilot testing with real users."
elif [ "$OVERALL_STATUS" = "GOOD" ]; then
    echo "⚠️  **CORE WORKING - MINOR FIXES NEEDED**"  
    echo ""
    echo "Most functionality works, but some issues need attention."
    echo "Review failed tests and fix before full deployment."
else
    echo "🚨 **MAJOR ISSUES - SIGNIFICANT WORK NEEDED**"
    echo ""
    echo "System has serious problems that need fixing."
    echo "Not ready for any user testing until issues resolved."
fi)

## 🚀 Next Steps

1. **Complete manual testing checklist**
2. **Fix any failed automated tests**  
3. **Document any additional issues found**
4. **Plan test semester deployment** (if verification successful)

---

*Automated verification completed on $(date)*
*This report validates Claude Code handoff implementation*
EOF

log_success "Comprehensive report saved: SYSTEM_VERIFICATION_REPORT.md"

echo ""
echo "🎯 CLAUDE CODE HANDOFF VERIFICATION COMPLETE"
echo "============================================"

if [ "$OVERALL_STATUS" = "EXCELLENT" ]; then
    log_success "🎉 Claude Code successfully implemented the backend + frontend!"
    log_success "✅ System ready for test semester deployment"
elif [ "$OVERALL_STATUS" = "GOOD" ]; then
    log_warning "👍 Claude Code implementation mostly successful"
    log_info "🔧 Minor fixes needed before full deployment"
else
    log_error "🚨 Claude Code implementation needs significant work"
    log_error "❌ Major issues must be resolved"
fi

echo ""
log_info "📁 Check these files for detailed results:"
echo "   - SYSTEM_VERIFICATION_REPORT.md"
echo "   - backend_verification_output.txt"
echo "   - database_verification_output.txt"
echo ""
log_info "🌐 Test the system manually at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000/docs"

# Return appropriate exit code
if [ "$OVERALL_STATUS" = "EXCELLENT" ] || [ "$OVERALL_STATUS" = "GOOD" ]; then
    exit 0
else
    exit 1
fi