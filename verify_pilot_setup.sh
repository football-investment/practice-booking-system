#!/bin/bash

# 🔍 PRACTICE BOOKING SYSTEM - PILOT SETUP VERIFICATION
# Komplett rendszer ellenőrzés a pilot program indítása előtt

echo "🔍 PRACTICE BOOKING SYSTEM - PILOT SETUP VERIFICATION"
echo "====================================================="
echo "Komplett rendszer állapot ellenőrzése pilot program előtt"
echo ""

# Színes output
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
    echo -e "${BLUE}ℹ️ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_test() {
    echo -e "${PURPLE}🧪 $1${NC}"
}

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

run_check() {
    local description=$1
    local command=$2
    local expected_result=$3
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_test "Testing: $description"
    
    if eval "$command"; then
        if [ -n "$expected_result" ]; then
            if eval "$command" | grep -q "$expected_result"; then
                log_success "$description"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
                return 0
            else
                log_error "$description (unexpected result)"
                FAILED_CHECKS=$((FAILED_CHECKS + 1))
                return 1
            fi
        else
            log_success "$description"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        fi
    else
        log_error "$description"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# =============================================================================
# PHASE 1: FILE SYSTEM VERIFICATION
# =============================================================================

echo "📁 PHASE 1: File System Verification"
echo "===================================="

run_check "Project root directory" "[ -f 'app/main.py' ]"
run_check "Backend startup script" "[ -f 'start_backend.sh' ]"
run_check "Frontend startup script" "[ -f 'start_frontend.sh' ]"  
run_check "Combined startup script" "[ -f 'start_both.sh' ]"
run_check "Pilot user setup script" "[ -f 'pilot_user_setup.sh' ]"
run_check "Frontend directory" "[ -d 'frontend' ]"
run_check "Frontend package.json" "[ -f 'frontend/package.json' ]"

# Script permissions
if [ -x "start_backend.sh" ] && [ -x "start_frontend.sh" ] && [ -x "start_both.sh" ]; then
    log_success "All scripts have execute permissions"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warning "Some scripts missing execute permissions"
    log_info "Fix with: chmod +x *.sh"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# =============================================================================
# PHASE 2: SYSTEM DEPENDENCIES VERIFICATION
# =============================================================================

echo ""
echo "🔧 PHASE 2: System Dependencies Verification"
echo "==========================================="

run_check "Python3 installed" "command -v python3"
run_check "Node.js installed" "command -v node"
run_check "npm installed" "command -v npm"
run_check "curl installed" "command -v curl"
run_check "jq installed" "command -v jq"

# Virtual environment
if [ -d "venv" ]; then
    log_success "Virtual environment exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warning "Virtual environment not found"
    log_info "Create with: python3 -m venv venv"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Frontend dependencies
if [ -d "frontend/node_modules" ]; then
    log_success "Frontend dependencies installed"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warning "Frontend dependencies not installed"
    log_info "Install with: cd frontend && npm install"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# =============================================================================
# PHASE 3: SERVICE AVAILABILITY VERIFICATION
# =============================================================================

echo ""
echo "🌐 PHASE 3: Service Availability Verification"
echo "============================================="

# Backend health check
run_check "Backend service running" "curl -s http://localhost:8000/health"
run_check "Backend health status" "curl -s http://localhost:8000/health" "healthy"
run_check "Backend API docs accessible" "curl -s http://localhost:8000/docs -o /dev/null"

# Frontend check
if curl -s http://localhost:3000 &> /dev/null; then
    run_check "Frontend service running" "curl -s http://localhost:3000"
    run_check "Frontend serves content" "curl -s http://localhost:3000" "Practice Booking System"
else
    log_warning "Frontend not running"
    log_info "Start with: ./start_frontend.sh"
    WARNINGS=$((WARNINGS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 2))
fi

# =============================================================================
# PHASE 4: AUTHENTICATION VERIFICATION
# =============================================================================

echo ""
echo "🔐 PHASE 4: Authentication Verification"  
echo "======================================"

# Admin login test
log_test "Testing: Admin login functionality"
ADMIN_LOGIN=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@company.com","password":"admin123"}' \
    http://localhost:8000/api/v1/auth/login)

ADMIN_TOKEN=$(echo $ADMIN_LOGIN | jq -r '.access_token' 2>/dev/null)

if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    log_success "Admin login successful"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    # Test protected endpoint
    USER_INFO=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
        http://localhost:8000/api/v1/auth/me)
    
    if echo "$USER_INFO" | jq -r '.role' | grep -q "admin"; then
        log_success "Admin token validation"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_error "Admin token validation failed"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
else
    log_error "Admin login failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# =============================================================================
# PHASE 5: DATABASE STATE VERIFICATION
# =============================================================================

echo ""
echo "📊 PHASE 5: Database State Verification"
echo "======================================"

if [ -n "$ADMIN_TOKEN" ]; then
    # User count verification
    USER_LIST=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
        "http://localhost:8000/api/v1/users/")
    
    if echo "$USER_LIST" | jq -r '.users' &> /dev/null; then
        TOTAL_USERS=$(echo "$USER_LIST" | jq -r '.total' 2>/dev/null)
        
        if [ -n "$TOTAL_USERS" ] && [ "$TOTAL_USERS" -gt 0 ]; then
            log_success "Database has $TOTAL_USERS users"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            
            # Role distribution check
            ADMIN_COUNT=$(echo "$USER_LIST" | jq -r '.users[] | select(.role=="admin")' | wc -l | tr -d ' ')
            INSTRUCTOR_COUNT=$(echo "$USER_LIST" | jq -r '.users[] | select(.role=="instructor")' | wc -l | tr -d ' ')
            STUDENT_COUNT=$(echo "$USER_LIST" | jq -r '.users[] | select(.role=="student")' | wc -l | tr -d ' ')
            
            log_info "User distribution: $ADMIN_COUNT admin, $INSTRUCTOR_COUNT instructors, $STUDENT_COUNT students"
            
            if [ "$INSTRUCTOR_COUNT" -ge 3 ] && [ "$STUDENT_COUNT" -ge 10 ]; then
                log_success "Sufficient users for pilot program"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warning "Consider running pilot_user_setup.sh for more users"
                WARNINGS=$((WARNINGS + 1))
            fi
            TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
            
        else
            log_error "No users found in database"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
    else
        log_error "Cannot retrieve user list from API"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    # Semester check
    SEMESTER_LIST=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
        "http://localhost:8000/api/v1/semesters/")
    
    if echo "$SEMESTER_LIST" | jq -r '.[0].id' &> /dev/null; then
        SEMESTER_COUNT=$(echo "$SEMESTER_LIST" | jq -r '. | length' 2>/dev/null)
        log_success "Database has $SEMESTER_COUNT semesters"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warning "No semesters found - create through admin panel"
        WARNINGS=$((WARNINGS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

# =============================================================================
# PHASE 6: FRONTEND INTEGRATION VERIFICATION  
# =============================================================================

echo ""
echo "🖥️ PHASE 6: Frontend Integration Verification"
echo "============================================="

if curl -s http://localhost:3000 &> /dev/null; then
    # Frontend proxy to backend
    run_check "Frontend proxy to backend" "curl -s http://localhost:3000/api/v1/health"
    
    # React compilation check
    log_test "Testing: React app compilation"
    cd frontend
    if npm run build --silent &> /dev/null; then
        log_success "React app compiles without errors"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        rm -rf build  # Cleanup
    else
        log_error "React compilation errors"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    cd ..
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
else
    log_info "Frontend not running - skipping integration tests"
fi

# =============================================================================
# FINAL SUMMARY AND RECOMMENDATIONS
# =============================================================================

echo ""
echo "📋 VERIFICATION SUMMARY"
echo "======================"

echo ""
echo "📊 TEST RESULTS:"
echo "   Total checks: $TOTAL_CHECKS"
echo "   ✅ Passed: $PASSED_CHECKS"
echo "   ❌ Failed: $FAILED_CHECKS" 
echo "   ⚠️ Warnings: $WARNINGS"
echo ""

# Calculate success rate
if [ $TOTAL_CHECKS -gt 0 ]; then
    SUCCESS_RATE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    echo "🎯 Success Rate: $SUCCESS_RATE%"
else
    SUCCESS_RATE=0
fi

echo ""

# Overall assessment
if [ $SUCCESS_RATE -ge 90 ] && [ $FAILED_CHECKS -eq 0 ]; then
    log_success "🎉 PILOT PROGRAM READY!"
    echo "   All critical systems operational"
    echo "   Ready for pilot user testing"
    
elif [ $SUCCESS_RATE -ge 70 ] && [ $FAILED_CHECKS -le 2 ]; then
    log_warning "⚠️ PILOT PROGRAM MOSTLY READY"
    echo "   Minor issues detected but non-blocking"
    echo "   Consider fixing warnings before full pilot"
    
else
    log_error "❌ PILOT PROGRAM NOT READY"
    echo "   Critical issues need resolution"
    echo "   Fix failed checks before pilot launch"
fi

echo ""
echo "🔧 RECOMMENDED ACTIONS:"

if [ $FAILED_CHECKS -gt 0 ]; then
    echo "   1. ❌ Fix failed system checks first"
fi

if [ $WARNINGS -gt 0 ]; then
    echo "   2. ⚠️ Address warnings for optimal setup"
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "   3. 📦 Install frontend dependencies: cd frontend && npm install"
fi

# Check user count
if [ -n "$TOTAL_USERS" ] && [ "$TOTAL_USERS" -lt 15 ]; then
    echo "   4. 👥 Create more pilot users: ./pilot_user_setup.sh"
fi

echo "   5. 🚀 Start services: ./start_both.sh"
echo "   6. 🌐 Open browser: http://localhost:3000"
echo "   7. 🔐 Login as admin: admin@company.com / admin123"

echo ""
echo "📚 PILOT TESTING CHECKLIST:"
echo "   [ ] Admin can manage users"
echo "   [ ] Instructors can create sessions" 
echo "   [ ] Students can book sessions"
echo "   [ ] Attendance tracking works"
echo "   [ ] Feedback system functional"
echo "   [ ] Reports generation works"

echo ""
if [ $SUCCESS_RATE -ge 90 ]; then
    echo "🎯 STATUS: ✅ READY FOR PILOT PROGRAM"
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo "🎯 STATUS: ⚠️ MOSTLY READY (minor fixes needed)"
else
    echo "🎯 STATUS: ❌ NEEDS FIXES BEFORE PILOT"
fi

echo ""
log_info "Verification complete! 🎉"