#!/bin/bash

# Complete Practice Booking System Journey
# Tests every claim Claude Code made + database validation

echo "🚀 PRACTICE BOOKING SYSTEM - COMPLETE VALIDATION JOURNEY"
echo "============================================================="
echo "Testing Claude Code's claims through real user workflows"
echo "Database queries included for validation"
echo ""

# Colors for better output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_phase() {
    echo ""
    echo -e "${YELLOW}🎯 PHASE $1: $2${NC}"
    echo "----------------------------------------"
}

# Check if server is running
check_server() {
    if curl -s http://localhost:8000/health > /dev/null; then
        log_success "Server is running"
        return 0
    else
        log_error "Server is not running! Start with: uvicorn app.main:app --reload"
        exit 1
    fi
}

# API call helper
api_call() {
    local method=$1
    local endpoint=$2
    local token=$3
    local data=$4
    
    if [ -n "$token" ]; then
        if [ -n "$data" ]; then
            curl -s -X $method "http://localhost:8000$endpoint" \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json" \
                -d "$data"
        else
            curl -s -X $method "http://localhost:8000$endpoint" \
                -H "Authorization: Bearer $token"
        fi
    else
        if [ -n "$data" ]; then
            curl -s -X $method "http://localhost:8000$endpoint" \
                -H "Content-Type: application/json" \
                -d "$data"
        else
            curl -s "http://localhost:8000$endpoint"
        fi
    fi
}

# Database query helper (requires psql connection)
db_query() {
    local query=$1
    log_info "DB Query: $query"
    
    # Try to connect to database and run query
    # Note: This assumes PostgreSQL and connection details from config
    psql postgresql://username:password@localhost:5432/practice_booking_system \
        -c "$query" -t 2>/dev/null || echo "DB connection failed - check credentials"
}

# =============================================================================
# PHASE 1: SYSTEM HEALTH & INFRASTRUCTURE
# =============================================================================

log_phase "1" "System Health & Infrastructure Validation"

check_server

log_info "Testing health endpoints Claude Code created..."

# Basic health
HEALTH_BASIC=$(api_call "GET" "/health")
if echo "$HEALTH_BASIC" | grep -q "healthy"; then
    log_success "Basic health endpoint working"
    echo "Response: $HEALTH_BASIC"
else
    log_error "Basic health endpoint failed"
fi

# Detailed health  
HEALTH_DETAILED=$(api_call "GET" "/health/detailed")
if echo "$HEALTH_DETAILED" | grep -q "database"; then
    log_success "Detailed health endpoint working"
    echo "Database checks included: $(echo $HEALTH_DETAILED | jq -r '.checks.database.status' 2>/dev/null || echo 'parsing failed')"
else
    log_error "Detailed health endpoint failed"
fi

# Ready probe
HEALTH_READY=$(api_call "GET" "/health/ready")
if echo "$HEALTH_READY" | grep -q "ready"; then
    log_success "Ready probe working"
else
    log_error "Ready probe failed"
fi

# Database validation
log_info "Database validation from health endpoint:"
USER_COUNT=$(echo $HEALTH_DETAILED | jq -r '.checks.database.details.users_count' 2>/dev/null || echo 0)
SESSION_COUNT=$(echo $HEALTH_DETAILED | jq -r '.checks.database.details.sessions_count' 2>/dev/null || echo 0)
BOOKING_COUNT=$(echo $HEALTH_DETAILED | jq -r '.checks.database.details.bookings_count' 2>/dev/null || echo 0)

log_info "Current database state:"
log_info "  Users: $USER_COUNT"
log_info "  Sessions: $SESSION_COUNT" 
log_info "  Bookings: $BOOKING_COUNT"

# =============================================================================
# PHASE 2: AUTHENTICATION SYSTEM
# =============================================================================

log_phase "2" "Authentication System Validation"

log_info "Testing admin login..."
ADMIN_LOGIN=$(api_call "POST" "/api/v1/auth/login" "" '{"email":"admin@company.com","password":"admin123"}')
ADMIN_TOKEN=$(echo $ADMIN_LOGIN | jq -r '.access_token' 2>/dev/null)

if [ "$ADMIN_TOKEN" != "null" ] && [ -n "$ADMIN_TOKEN" ]; then
    log_success "Admin login successful"
    log_info "Token length: ${#ADMIN_TOKEN} characters"
else
    log_error "Admin login failed"
    echo "Response: $ADMIN_LOGIN"
fi

# Test current user endpoint
if [ -n "$ADMIN_TOKEN" ]; then
    CURRENT_USER=$(api_call "GET" "/api/v1/auth/me" "$ADMIN_TOKEN")
    USER_ROLE=$(echo $CURRENT_USER | jq -r '.role' 2>/dev/null)
    
    if [ "$USER_ROLE" = "admin" ]; then
        log_success "Current user endpoint working - Role: $USER_ROLE"
    else
        log_error "Current user endpoint failed"
    fi
fi

# =============================================================================
# PHASE 3: USER MANAGEMENT & ROLE SYSTEM
# =============================================================================

log_phase "3" "User Management & Role System"

if [ -n "$ADMIN_TOKEN" ]; then
    # List existing users
    log_info "Listing existing users..."
    USERS_LIST=$(api_call "GET" "/api/v1/users/" "$ADMIN_TOKEN")
    USERS_TOTAL=$(echo $USERS_LIST | jq -r '.total' 2>/dev/null || echo 0)
    log_info "Total users in system: $USERS_TOTAL"
    
    # Create test instructor
    log_info "Creating test instructor..."
    TIMESTAMP=$(date +%s)
    INSTRUCTOR_DATA='{
        "name": "Test Instructor '${TIMESTAMP}'",
        "email": "instructor'${TIMESTAMP}'@journey.test",
        "password": "instructor123",
        "role": "instructor"
    }'
    
    INSTRUCTOR_CREATED=$(api_call "POST" "/api/v1/users/" "$ADMIN_TOKEN" "$INSTRUCTOR_DATA")
    INSTRUCTOR_ID=$(echo $INSTRUCTOR_CREATED | jq -r '.id' 2>/dev/null)
    
    if [ "$INSTRUCTOR_ID" != "null" ] && [ -n "$INSTRUCTOR_ID" ]; then
        log_success "Instructor created with ID: $INSTRUCTOR_ID"
        
        # Test instructor login
        INSTRUCTOR_LOGIN_DATA='{"email":"instructor'${TIMESTAMP}'@journey.test","password":"instructor123"}'
        INSTRUCTOR_LOGIN=$(api_call "POST" "/api/v1/auth/login" "" "$INSTRUCTOR_LOGIN_DATA")
        INSTRUCTOR_TOKEN=$(echo $INSTRUCTOR_LOGIN | jq -r '.access_token' 2>/dev/null)
        
        if [ -n "$INSTRUCTOR_TOKEN" ]; then
            log_success "Instructor can login"
        else
            log_error "Instructor login failed"
        fi
    else
        log_error "Instructor creation failed"
        echo "Response: $INSTRUCTOR_CREATED"
    fi
    
    # Create test student
    log_info "Creating test student..."
    STUDENT_DATA='{
        "name": "Test Student '${TIMESTAMP}'",
        "email": "student'${TIMESTAMP}'@journey.test", 
        "password": "student123",
        "role": "student"
    }'
    
    STUDENT_CREATED=$(api_call "POST" "/api/v1/users/" "$ADMIN_TOKEN" "$STUDENT_DATA")
    STUDENT_ID=$(echo $STUDENT_CREATED | jq -r '.id' 2>/dev/null)
    
    if [ "$STUDENT_ID" != "null" ] && [ -n "$STUDENT_ID" ]; then
        log_success "Student created with ID: $STUDENT_ID"
        
        # Test student login
        STUDENT_LOGIN_DATA='{"email":"student'${TIMESTAMP}'@journey.test","password":"student123"}'
        STUDENT_LOGIN=$(api_call "POST" "/api/v1/auth/login" "" "$STUDENT_LOGIN_DATA")
        STUDENT_TOKEN=$(echo $STUDENT_LOGIN | jq -r '.access_token' 2>/dev/null)
        
        if [ -n "$STUDENT_TOKEN" ]; then
            log_success "Student can login"
        else
            log_error "Student login failed"
        fi
    else
        log_error "Student creation failed"
    fi
fi

# Database validation for users
log_info "Database validation - User count check:"
db_query "SELECT role, COUNT(*) as count FROM users WHERE is_active = true GROUP BY role;"

# =============================================================================
# PHASE 4: SEMESTER & GROUP MANAGEMENT  
# =============================================================================

log_phase "4" "Semester & Group Management"

if [ -n "$ADMIN_TOKEN" ]; then
    # Create test semester
    log_info "Creating test semester..."
    SEMESTER_DATA='{
        "code": "JOURNEY/'${TIMESTAMP}'",
        "name": "Journey Test Semester",
        "start_date": "2024-09-01",
        "end_date": "2024-12-31",
        "is_active": true
    }'
    
    SEMESTER_CREATED=$(api_call "POST" "/api/v1/semesters/" "$ADMIN_TOKEN" "$SEMESTER_DATA")
    SEMESTER_ID=$(echo $SEMESTER_CREATED | jq -r '.id' 2>/dev/null)
    
    if [ "$SEMESTER_ID" != "null" ] && [ -n "$SEMESTER_ID" ]; then
        log_success "Semester created with ID: $SEMESTER_ID"
        
        # Create test group in semester
        log_info "Creating test group..."
        GROUP_DATA='{
            "name": "Journey Test Group",
            "description": "Test group for journey validation",
            "semester_id": '${SEMESTER_ID}'
        }'
        
        GROUP_CREATED=$(api_call "POST" "/api/v1/groups/" "$ADMIN_TOKEN" "$GROUP_DATA")
        GROUP_ID=$(echo $GROUP_CREATED | jq -r '.id' 2>/dev/null)
        
        if [ "$GROUP_ID" != "null" ] && [ -n "$GROUP_ID" ]; then
            log_success "Group created with ID: $GROUP_ID"
            
            # Add student to group
            if [ -n "$STUDENT_ID" ]; then
                log_info "Adding student to group..."
                ADD_USER_DATA='{"user_id": '${STUDENT_ID}'}'
                ADD_USER_RESULT=$(api_call "POST" "/api/v1/groups/${GROUP_ID}/users" "$ADMIN_TOKEN" "$ADD_USER_DATA")
                
                if echo "$ADD_USER_RESULT" | grep -q "successfully"; then
                    log_success "Student added to group"
                else
                    log_error "Failed to add student to group"
                fi
            fi
        else
            log_error "Group creation failed"
        fi
    else
        log_error "Semester creation failed"
        echo "Response: $SEMESTER_CREATED"
    fi
fi

# Database validation
log_info "Database validation - Semesters and groups:"
db_query "SELECT s.code, s.name, COUNT(g.id) as groups FROM semesters s LEFT JOIN groups g ON s.id = g.semester_id GROUP BY s.id, s.code, s.name;"

# =============================================================================
# PHASE 5: SESSION/PRACTICE MANAGEMENT
# =============================================================================

log_phase "5" "Session/Practice Management"

if [ -n "$ADMIN_TOKEN" ] && [ -n "$SEMESTER_ID" ] && [ -n "$GROUP_ID" ] && [ -n "$INSTRUCTOR_ID" ]; then
    log_info "Creating test session..."
    
    # Calculate future date
    FUTURE_DATE=$(date -d "+1 day" '+%Y-%m-%dT10:00:00')
    END_DATE=$(date -d "+1 day" '+%Y-%m-%dT12:00:00')
    
    SESSION_DATA='{
        "title": "Journey Test Session",
        "description": "Test session for validation journey",
        "date_start": "'${FUTURE_DATE}'",
        "date_end": "'${END_DATE}'",
        "mode": "offline",
        "capacity": 20,
        "location": "Test Room 101",
        "semester_id": '${SEMESTER_ID}',
        "group_id": '${GROUP_ID}',
        "instructor_id": '${INSTRUCTOR_ID}'
    }'
    
    SESSION_CREATED=$(api_call "POST" "/api/v1/sessions/" "$ADMIN_TOKEN" "$SESSION_DATA")
    SESSION_ID=$(echo $SESSION_CREATED | jq -r '.id' 2>/dev/null)
    
    if [ "$SESSION_ID" != "null" ] && [ -n "$SESSION_ID" ]; then
        log_success "Session created with ID: $SESSION_ID"
        
        # List sessions with filters
        log_info "Testing session listing with filters..."
        SESSIONS_LIST=$(api_call "GET" "/api/v1/sessions/?semester_id=${SEMESTER_ID}" "$ADMIN_TOKEN")
        SESSIONS_COUNT=$(echo $SESSIONS_LIST | jq -r '.total' 2>/dev/null || echo 0)
        log_info "Sessions found for semester: $SESSIONS_COUNT"
        
        if [ "$SESSIONS_COUNT" -gt 0 ]; then
            log_success "Session filtering working"
        else
            log_error "Session filtering failed"
        fi
    else
        log_error "Session creation failed"
        echo "Response: $SESSION_CREATED"
    fi
fi

# Database validation
log_info "Database validation - Sessions:"
db_query "SELECT s.title, s.mode, s.capacity, sem.code as semester, g.name as group FROM sessions s JOIN semesters sem ON s.semester_id = sem.id JOIN groups g ON s.group_id = g.id;"

# =============================================================================
# PHASE 6: BOOKING SYSTEM & WORKFLOW
# =============================================================================

log_phase "6" "Booking System & Workflow"

if [ -n "$STUDENT_TOKEN" ] && [ -n "$SESSION_ID" ]; then
    log_info "Student creating booking..."
    
    BOOKING_DATA='{"session_id": '${SESSION_ID}', "notes": "Journey test booking"}'
    BOOKING_CREATED=$(api_call "POST" "/api/v1/bookings/" "$STUDENT_TOKEN" "$BOOKING_DATA")
    BOOKING_ID=$(echo $BOOKING_CREATED | jq -r '.id' 2>/dev/null)
    BOOKING_STATUS=$(echo $BOOKING_CREATED | jq -r '.status' 2>/dev/null)
    
    if [ "$BOOKING_ID" != "null" ] && [ -n "$BOOKING_ID" ]; then
        log_success "Booking created with ID: $BOOKING_ID, Status: $BOOKING_STATUS"
        
        # Test student's own bookings
        log_info "Testing student's booking list..."
        STUDENT_BOOKINGS=$(api_call "GET" "/api/v1/bookings/me" "$STUDENT_TOKEN")
        BOOKINGS_COUNT=$(echo $STUDENT_BOOKINGS | jq -r '.total' 2>/dev/null || echo 0)
        
        if [ "$BOOKINGS_COUNT" -gt 0 ]; then
            log_success "Student can view own bookings: $BOOKINGS_COUNT"
        else
            log_error "Student booking list failed"
        fi
        
        # Admin confirm booking
        if [ -n "$ADMIN_TOKEN" ]; then
            log_info "Admin confirming booking..."
            CONFIRM_RESULT=$(api_call "POST" "/api/v1/bookings/${BOOKING_ID}/confirm" "$ADMIN_TOKEN")
            
            if echo "$CONFIRM_RESULT" | grep -q "successfully"; then
                log_success "Admin can confirm bookings"
            else
                log_error "Admin booking confirmation failed"
            fi
        fi
    else
        log_error "Booking creation failed"
        echo "Response: $BOOKING_CREATED"
    fi
fi

# Database validation
log_info "Database validation - Bookings:"
db_query "SELECT b.status, COUNT(*) as count, s.title FROM bookings b JOIN sessions s ON b.session_id = s.id GROUP BY b.status, s.title;"

# =============================================================================
# PHASE 7: ATTENDANCE TRACKING
# =============================================================================

log_phase "7" "Attendance Tracking"

if [ -n "$INSTRUCTOR_TOKEN" ] && [ -n "$BOOKING_ID" ] && [ -n "$SESSION_ID" ] && [ -n "$STUDENT_ID" ]; then
    log_info "Instructor marking attendance..."
    
    ATTENDANCE_DATA='{
        "user_id": '${STUDENT_ID}',
        "session_id": '${SESSION_ID}',
        "booking_id": '${BOOKING_ID}',
        "status": "present",
        "notes": "Journey test attendance"
    }'
    
    ATTENDANCE_CREATED=$(api_call "POST" "/api/v1/attendance/" "$INSTRUCTOR_TOKEN" "$ATTENDANCE_DATA")
    ATTENDANCE_ID=$(echo $ATTENDANCE_CREATED | jq -r '.id' 2>/dev/null)
    
    if [ "$ATTENDANCE_ID" != "null" ] && [ -n "$ATTENDANCE_ID" ]; then
        log_success "Attendance recorded with ID: $ATTENDANCE_ID"
        
        # View attendance for session
        log_info "Testing attendance list for session..."
        SESSION_ATTENDANCE=$(api_call "GET" "/api/v1/attendance/?session_id=${SESSION_ID}" "$INSTRUCTOR_TOKEN")
        ATTENDANCE_COUNT=$(echo $SESSION_ATTENDANCE | jq -r '.total' 2>/dev/null || echo 0)
        
        if [ "$ATTENDANCE_COUNT" -gt 0 ]; then
            log_success "Attendance list working: $ATTENDANCE_COUNT records"
        else
            log_error "Attendance list failed"
        fi
    else
        log_error "Attendance recording failed"
        echo "Response: $ATTENDANCE_CREATED"
    fi
fi

# Database validation
log_info "Database validation - Attendance:"
db_query "SELECT a.status, COUNT(*) as count, s.title FROM attendance a JOIN sessions s ON a.session_id = s.id GROUP BY a.status, s.title;"

# =============================================================================
# PHASE 8: FEEDBACK SYSTEM
# =============================================================================

log_phase "8" "Feedback System"

if [ -n "$STUDENT_TOKEN" ] && [ -n "$SESSION_ID" ]; then
    log_info "Student submitting feedback..."
    
    FEEDBACK_DATA='{
        "session_id": '${SESSION_ID}',
        "rating": 4.5,
        "comment": "Journey test feedback - great session!",
        "is_anonymous": false
    }'
    
    FEEDBACK_CREATED=$(api_call "POST" "/api/v1/feedback/" "$STUDENT_TOKEN" "$FEEDBACK_DATA")
    FEEDBACK_ID=$(echo $FEEDBACK_CREATED | jq -r '.id' 2>/dev/null)
    
    if [ "$FEEDBACK_ID" != "null" ] && [ -n "$FEEDBACK_ID" ]; then
        log_success "Feedback submitted with ID: $FEEDBACK_ID"
        
        # Test feedback summary
        if [ -n "$INSTRUCTOR_TOKEN" ]; then
            log_info "Testing feedback summary..."
            FEEDBACK_SUMMARY=$(api_call "GET" "/api/v1/sessions/${SESSION_ID}/feedback/summary" "$INSTRUCTOR_TOKEN")
            AVG_RATING=$(echo $FEEDBACK_SUMMARY | jq -r '.average_rating' 2>/dev/null)
            
            if [ "$AVG_RATING" != "null" ] && [ "$AVG_RATING" != "0" ]; then
                log_success "Feedback summary working - Average rating: $AVG_RATING"
            else
                log_error "Feedback summary failed"
            fi
        fi
    else
        log_error "Feedback submission failed"
        echo "Response: $FEEDBACK_CREATED"
    fi
fi

# Database validation
log_info "Database validation - Feedback:"
db_query "SELECT AVG(rating) as avg_rating, COUNT(*) as feedback_count, s.title FROM feedback f JOIN sessions s ON f.session_id = s.id GROUP BY s.title;"

# =============================================================================
# PHASE 9: REPORTING SYSTEM
# =============================================================================

log_phase "9" "Reporting System"

if [ -n "$ADMIN_TOKEN" ] && [ -n "$SEMESTER_ID" ] && [ -n "$STUDENT_ID" ]; then
    log_info "Testing semester report..."
    
    SEMESTER_REPORT=$(api_call "GET" "/api/v1/reports/semester/${SEMESTER_ID}" "$ADMIN_TOKEN")
    TOTAL_SESSIONS=$(echo $SEMESTER_REPORT | jq -r '.overview.total_sessions' 2>/dev/null || echo 0)
    TOTAL_BOOKINGS=$(echo $SEMESTER_REPORT | jq -r '.overview.total_bookings' 2>/dev/null || echo 0)
    
    if [ "$TOTAL_SESSIONS" -gt 0 ]; then
        log_success "Semester report working - Sessions: $TOTAL_SESSIONS, Bookings: $TOTAL_BOOKINGS"
    else
        log_error "Semester report failed"
    fi
    
    # Test user report
    log_info "Testing user participation report..."
    USER_REPORT=$(api_call "GET" "/api/v1/reports/user/${STUDENT_ID}" "$ADMIN_TOKEN")
    USER_BOOKINGS=$(echo $USER_REPORT | jq -r '.booking_statistics.total_bookings' 2>/dev/null || echo 0)
    
    if [ "$USER_BOOKINGS" -gt 0 ]; then
        log_success "User report working - User bookings: $USER_BOOKINGS"
    else
        log_error "User report failed"
    fi
    
    # Test CSV export
    log_info "Testing CSV export..."
    CSV_EXPORT=$(api_call "GET" "/api/v1/reports/export/sessions?semester_id=${SEMESTER_ID}" "$ADMIN_TOKEN")
    
    if echo "$CSV_EXPORT" | grep -q "Session ID"; then
        log_success "CSV export working"
        log_info "CSV headers: $(echo $CSV_EXPORT | head -n1)"
    else
        log_error "CSV export failed"
    fi
fi

# =============================================================================
# PHASE 10: PERMISSION TESTING
# =============================================================================

log_phase "10" "Permission & Security Testing"

# Test student trying to access admin functions
if [ -n "$STUDENT_TOKEN" ]; then
    log_info "Testing student permission boundaries..."
    
    STUDENT_ADMIN_TEST=$(api_call "GET" "/api/v1/users/" "$STUDENT_TOKEN")
    
    if echo "$STUDENT_ADMIN_TEST" | grep -q "403"; then
        log_success "Student properly blocked from admin functions"
    else
        log_error "Student permission boundary failed"
    fi
fi

# Test instructor trying to access admin reports
if [ -n "$INSTRUCTOR_TOKEN" ] && [ -n "$SEMESTER_ID" ]; then
    log_info "Testing instructor permission boundaries..."
    
    INSTRUCTOR_REPORT_TEST=$(api_call "GET" "/api/v1/reports/semester/${SEMESTER_ID}" "$INSTRUCTOR_TOKEN")
    
    if echo "$INSTRUCTOR_REPORT_TEST" | grep -q "403"; then
        log_success "Instructor properly blocked from admin reports"
    else
        log_error "Instructor permission boundary failed"
    fi
fi

# =============================================================================
# FINAL SUMMARY & DATABASE STATE
# =============================================================================

log_phase "FINAL" "Journey Summary & Database State"

# Final database state
log_info "Final database state summary:"
db_query "
SELECT 
    'Users' as entity,
    COUNT(*) as total,
    SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admins,
    SUM(CASE WHEN role = 'instructor' THEN 1 ELSE 0 END) as instructors,
    SUM(CASE WHEN role = 'student' THEN 1 ELSE 0 END) as students
FROM users WHERE is_active = true
UNION ALL
SELECT 
    'Sessions',
    COUNT(*),
    SUM(CASE WHEN mode = 'online' THEN 1 ELSE 0 END),
    SUM(CASE WHEN mode = 'offline' THEN 1 ELSE 0 END),
    SUM(CASE WHEN mode = 'hybrid' THEN 1 ELSE 0 END)
FROM sessions
UNION ALL
SELECT 
    'Bookings',
    COUNT(*),
    SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END),
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END),
    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)
FROM bookings;"

# Journey results
echo ""
echo "============================================================="
echo -e "${YELLOW}🎯 COMPLETE JOURNEY RESULTS${NC}"
echo "============================================================="
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
    echo "📊 Success Rate: ${SUCCESS_RATE}%"
fi

echo ""
if [ $TESTS_PASSED -gt $TESTS_FAILED ]; then
    echo -e "${GREEN}🎉 JOURNEY SUCCESS: Claude Code claims largely validated!${NC}"
    echo "✅ System is genuinely functional and production-ready"
else
    echo -e "${RED}⚠️  JOURNEY MIXED: Some Claude Code claims failed validation${NC}"
    echo "🔍 System has issues that need attention"
fi

echo ""
echo "📚 Full API Documentation: http://localhost:8000/docs"
echo "🏥 Health Monitoring: http://localhost:8000/health/detailed"
echo ""
echo "============================================================="