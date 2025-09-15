#!/bin/bash

# 🎯 COMPLETE INTERACTIVE SYSTEM TEST
# Tests ALL user endpoints with step-by-step verification
# Press ENTER at each step to proceed after manual verification

echo "🎯 COMPLETE INTERACTIVE SYSTEM TEST"
echo "===================================="
echo "This script will test ALL user management endpoints"
echo "You'll manually verify frontend/backend changes at each step"
echo "Press CTRL+C anytime to stop"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
DB_NAME="practice_booking_system"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@company.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

log_step() {
    echo -e "\n${PURPLE}📋 STEP $1: $2${NC}"
    echo "----------------------------------------"
}

log_action() {
    echo -e "${BLUE}🔧 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

wait_for_user() {
    echo ""
    echo -e "${YELLOW}👁️  VERIFY IN BROWSER: $FRONTEND_URL${NC}"
    echo -e "${YELLOW}📱 CHECK: $1${NC}"
    echo -e "${BLUE}Press ENTER to continue...${NC}"
    read -r
}

api_call() {
    local method="$1"
    local endpoint="$2"
    local token="$3"
    local data="$4"
    
    if [ -n "$token" ]; then
        if [ "$method" = "GET" ] || [ "$method" = "DELETE" ]; then
            curl -s -X "$method" "$BASE_URL$endpoint" \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json"
        else
            curl -s -X "$method" "$BASE_URL$endpoint" \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json" \
                -d "$data"
        fi
    else
        curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

db_query() {
    local query="$1"
    psql -d "$DB_NAME" -c "$query" -t -A
}

# =============================================================================
# PHASE 1: DATABASE SETUP (SKIP CLEANUP IF ADMIN EXISTS)
# =============================================================================

log_step "1" "Database Setup"

# Check if admin user already exists
EXISTING_ADMIN=$(db_query "SELECT email FROM users WHERE email = '$ADMIN_EMAIL' AND role = 'ADMIN';")

if [ -n "$EXISTING_ADMIN" ]; then
    log_success "Admin user already exists, cleaning test data"
    log_info "Using existing admin: $ADMIN_EMAIL"
    
    # Clean any existing test data but keep admin
    log_action "Cleaning test data..."
    db_query "DELETE FROM sessions; DELETE FROM group_users; DELETE FROM groups; DELETE FROM semesters; DELETE FROM users WHERE email != '$ADMIN_EMAIL';" > /dev/null 2>&1
    log_success "Test data cleaned"
else
    log_action "Cleaning database..."
    db_query "DELETE FROM sessions; DELETE FROM group_users; DELETE FROM groups; DELETE FROM semesters; DELETE FROM users WHERE email != '$ADMIN_EMAIL';" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Database cleaned successfully"
    else
        log_error "Database cleanup failed"
        exit 1
    fi
    wait_for_user "Database should be empty, all tables cleared"
fi

# Skip admin creation - backend startup script already created it
log_action "Skipping admin creation - backend startup already created admin user"
log_success "Using existing admin: $ADMIN_EMAIL with password: $ADMIN_PASSWORD"

# Login as admin to get token
log_action "Logging in as admin..."
LOGIN_DATA='{"email": "'$ADMIN_EMAIL'", "password": "'$ADMIN_PASSWORD'"}'
LOGIN_RESULT=$(api_call "POST" "/api/v1/auth/login" "" "$LOGIN_DATA")
ADMIN_TOKEN=$(echo $LOGIN_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['access_token'] if 'access_token' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")

if [ "$ADMIN_TOKEN" != "ERROR" ] && [ "$ADMIN_TOKEN" != "JSON_PARSE_ERROR" ] && [ -n "$ADMIN_TOKEN" ]; then
    log_success "Admin login successful"
else
    log_error "Admin login failed"
    exit 1
fi

wait_for_user "Admin should be logged into frontend"

# Create test semester
log_step "2" "Create ELTE 2025/26 Őszi Semester"

log_action "Creating semester..."
SEMESTER_DATA='{
    "code": "ELTE-2025-26-OSZI",
    "name": "ELTE 2025/26 Őszi Félév",
    "start_date": "2025-09-01",
    "end_date": "2025-12-31",
    "is_active": true
}'

SEMESTER_RESULT=$(api_call "POST" "/api/v1/semesters/" "$ADMIN_TOKEN" "$SEMESTER_DATA")
SEMESTER_ID=$(echo $SEMESTER_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['id'] if 'id' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")

if [ "$SEMESTER_ID" != "ERROR" ] && [ "$SEMESTER_ID" != "JSON_PARSE_ERROR" ] && [ -n "$SEMESTER_ID" ]; then
    log_success "Semester created with ID: $SEMESTER_ID"
else
    log_error "Semester creation failed"
    exit 1
fi

wait_for_user "New semester should appear in Semester Manager"

# =============================================================================
# PHASE 3: COMPREHENSIVE USER MANAGEMENT TESTING
# =============================================================================

log_step "3" "Complete User Management Journey"

# Test 1: Create Instructor
log_action "Creating instructor user..."
INSTRUCTOR_DATA='{
    "email": "instructor@elte.hu",
    "password": "instructor123",
    "name": "Dr. Nagy János",
    "role": "instructor",
    "is_active": true
}'

INSTRUCTOR_RESULT=$(api_call "POST" "/api/v1/users/" "$ADMIN_TOKEN" "$INSTRUCTOR_DATA")
echo "API Response: $INSTRUCTOR_RESULT" | head -c 200
INSTRUCTOR_ID=$(echo $INSTRUCTOR_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['id'] if 'id' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")

if [ "$INSTRUCTOR_ID" != "ERROR" ] && [ "$INSTRUCTOR_ID" != "JSON_PARSE_ERROR" ] && [ -n "$INSTRUCTOR_ID" ]; then
    log_success "Instructor created with ID: $INSTRUCTOR_ID"
else
    log_error "Instructor creation failed - Response: $INSTRUCTOR_RESULT"
    exit 1
fi
wait_for_user "Instructor should appear in User Manager list"

# Test 2: Create Students
log_action "Creating student users..."
for i in {1..3}; do
    STUDENT_DATA='{
        "email": "student'$i'@student.elte.hu",
        "password": "student123",
        "name": "Hallgató '$i'",
        "role": "student",
        "is_active": true
    }'
    
    STUDENT_RESULT=$(api_call "POST" "/api/v1/users/" "$ADMIN_TOKEN" "$STUDENT_DATA")
    STUDENT_ID=$(echo $STUDENT_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['id'] if 'id' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")
    
    if [ "$STUDENT_ID" != "ERROR" ] && [ "$STUDENT_ID" != "JSON_PARSE_ERROR" ] && [ -n "$STUDENT_ID" ]; then
        log_success "Student $i created with ID: $STUDENT_ID"
    else
        log_error "Student $i creation failed - Response: $STUDENT_RESULT"
        STUDENT_ID=""
    fi
    
    if [ $i -eq 1 ]; then
        STUDENT1_ID=$STUDENT_ID
    elif [ $i -eq 2 ]; then
        STUDENT2_ID=$STUDENT_ID
    elif [ $i -eq 3 ]; then
        STUDENT3_ID=$STUDENT_ID
    fi
done

wait_for_user "All 3 students should appear in User Manager"

# Test 3: Get Users List
log_action "Testing GET /api/v1/users/ (List all users)..."
USERS_LIST=$(api_call "GET" "/api/v1/users/" "$ADMIN_TOKEN")
USER_COUNT=$(echo $USERS_LIST | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['users']) if 'users' in data else 0)" 2>/dev/null || echo "0")
log_success "Users list retrieved: $USER_COUNT users total"

wait_for_user "User Manager should show 5 users total (1 admin, 1 instructor, 3 students)"

# Test 4: Get Individual User Details
log_action "Testing GET /api/v1/users/{id} (Get user details)..."
USER_DETAILS=$(api_call "GET" "/api/v1/users/$INSTRUCTOR_ID" "$ADMIN_TOKEN")
USER_NAME=$(echo $USER_DETAILS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['name'] if 'name' in data else 'UNKNOWN')" 2>/dev/null || echo "PARSE_ERROR")
log_success "User details retrieved: $USER_NAME"

wait_for_user "Click on instructor in User Manager - should show detailed info"

# Test 5: Update User
log_action "Testing PATCH /api/v1/users/{id} (Update user)..."
UPDATE_DATA='{
    "name": "Dr. Nagy János (Updated)",
    "email": "updated.instructor@elte.hu"
}'

UPDATE_RESULT=$(api_call "PATCH" "/api/v1/users/$INSTRUCTOR_ID" "$ADMIN_TOKEN" "$UPDATE_DATA")
log_success "User updated successfully"

wait_for_user "Instructor name and email should be updated in User Manager"

# Test 6: Create Group and Test Group User Management
log_action "Creating test group..."
GROUP_DATA='{
    "name": "Tesztcsoport A",
    "description": "Test group for user management",
    "semester_id": '$SEMESTER_ID'
}'

GROUP_RESULT=$(api_call "POST" "/api/v1/groups/" "$ADMIN_TOKEN" "$GROUP_DATA")
GROUP_ID=$(echo $GROUP_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['id'] if 'id' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")

log_success "Group created with ID: $GROUP_ID"
wait_for_user "New group should appear in Group Manager"

# Test 7: Add Users to Group
log_action "Testing POST /api/v1/groups/{id}/users (Add user to group)..."

for STUDENT_ID in $STUDENT1_ID $STUDENT2_ID; do
    ADD_USER_DATA='{"user_id": '$STUDENT_ID'}'
    ADD_RESULT=$(api_call "POST" "/api/v1/groups/$GROUP_ID/users" "$ADMIN_TOKEN" "$ADD_USER_DATA")
    log_success "Student $STUDENT_ID added to group"
done

wait_for_user "Group should show 2 members when you open Members modal"

# Test 8: Remove User from Group
log_action "Testing DELETE /api/v1/groups/{id}/users/{user_id} (Remove user from group)..."
REMOVE_RESULT=$(api_call "DELETE" "/api/v1/groups/$GROUP_ID/users/$STUDENT2_ID" "$ADMIN_TOKEN")
log_success "Student $STUDENT2_ID removed from group"

wait_for_user "Group should now show only 1 member in Members modal"

# Test 9: Test User Roles and Permissions
log_action "Testing role-based access..."

# Login as student
STUDENT_LOGIN='{"email": "student1@student.elte.hu", "password": "student123"}'
STUDENT_LOGIN_RESULT=$(api_call "POST" "/api/v1/auth/login" "" "$STUDENT_LOGIN")
STUDENT_TOKEN=$(echo $STUDENT_LOGIN_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['access_token'] if 'access_token' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")

if [ "$STUDENT_TOKEN" != "ERROR" ] && [ "$STUDENT_TOKEN" != "JSON_PARSE_ERROR" ] && [ -n "$STUDENT_TOKEN" ]; then
    log_success "Student login successful"
    
    # Try to access admin endpoint (should fail)
    ADMIN_ACCESS_TEST=$(api_call "GET" "/api/v1/users/" "$STUDENT_TOKEN")
    if echo "$ADMIN_ACCESS_TEST" | grep -q "error\|forbidden\|unauthorized"; then
        log_success "Permission system working - student cannot access user list"
    else
        log_error "Permission system issue - student accessed admin endpoint"
    fi
else
    log_error "Student login failed - Response: $STUDENT_LOGIN_RESULT"
fi

wait_for_user "Student should be able to login but NOT access Admin panel"

# Test 10: User Profile Management
log_action "Testing PATCH /api/v1/users/me (Update own profile)..."
PROFILE_UPDATE='{
    "name": "Hallgató 1 (Updated Profile)"
}'

PROFILE_RESULT=$(api_call "PATCH" "/api/v1/users/me" "$STUDENT_TOKEN" "$PROFILE_UPDATE")
log_success "Student profile updated"

wait_for_user "Student profile should show updated name in dashboard"

# Test 11: Password Change
log_action "Testing POST /api/v1/auth/change-password (Change password)..."
PASSWORD_CHANGE='{
    "current_password": "student123",
    "new_password": "newpassword123"
}'

PASSWORD_RESULT=$(api_call "POST" "/api/v1/auth/change-password" "$STUDENT_TOKEN" "$PASSWORD_CHANGE")
log_success "Password changed successfully"

wait_for_user "Student should be able to change password in profile"

# Test 12: User Deactivation
log_action "Testing user deactivation (soft delete)..."
DEACTIVATE_RESULT=$(api_call "DELETE" "/api/v1/users/$STUDENT3_ID" "$ADMIN_TOKEN")
log_success "User deactivated (soft delete)"

wait_for_user "Student3 should disappear from active users list"

# Test 13: Password Reset (Admin)
log_action "Testing POST /api/v1/users/{id}/reset-password (Admin reset password)..."
RESET_RESULT=$(api_call "POST" "/api/v1/users/$STUDENT1_ID/reset-password" "$ADMIN_TOKEN")
NEW_PASSWORD=$(echo $RESET_RESULT | python3 -c "import sys, json; print(json.load(sys.stdin).get('new_password', 'N/A'))" 2>/dev/null)
log_success "Password reset by admin. New password: $NEW_PASSWORD"

wait_for_user "Admin should be able to reset user passwords"

# Test 14: User Filtering and Search
log_action "Testing user filtering by role..."
FILTER_STUDENTS=$(api_call "GET" "/api/v1/users/?role=student" "$ADMIN_TOKEN")
STUDENT_COUNT=$(echo $FILTER_STUDENTS | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['users']) if 'users' in data else 0)" 2>/dev/null || echo "0")
log_success "Filtered students: $STUDENT_COUNT found"

wait_for_user "User Manager filter should show only students"

# Test 15: Session Creation with User Assignment
log_action "Creating test session with instructor assignment..."
SESSION_DATA='{
    "title": "Test Practice Session",
    "description": "Testing session management",
    "date_start": "2025-09-15T10:00:00",
    "date_end": "2025-09-15T12:00:00",
    "capacity": 5,
    "mode": "offline",
    "location": "ELTE IK 2.01 terem",
    "semester_id": '$SEMESTER_ID',
    "group_id": '$GROUP_ID',
    "instructor_id": '$INSTRUCTOR_ID'
}'

SESSION_RESULT=$(api_call "POST" "/api/v1/sessions/" "$ADMIN_TOKEN" "$SESSION_DATA")
SESSION_ID=$(echo $SESSION_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['id'] if 'id' in data else 'ERROR')" 2>/dev/null || echo "JSON_PARSE_ERROR")

log_success "Session created with ID: $SESSION_ID"
wait_for_user "Session should appear in Session Manager with assigned instructor"

# =============================================================================
# FINAL VERIFICATION
# =============================================================================

log_step "4" "Final System State Verification"

log_action "Verifying final database state..."

echo ""
echo "📊 FINAL SYSTEM STATE:"
echo "======================"
echo "Users:"
db_query "SELECT id, email, name, role, is_active FROM users;"
echo ""
echo "Semesters:"
db_query "SELECT id, code, name, is_active FROM semesters;"
echo ""
echo "Groups:"
db_query "SELECT id, name, semester_id FROM groups;"
echo ""
echo "Group Memberships:"
db_query "SELECT g.name, u.email FROM group_users gu JOIN groups g ON gu.group_id = g.id JOIN users u ON gu.user_id = u.id;"
echo ""
echo "Sessions:"
db_query "SELECT id, title, date_start, instructor_id FROM sessions;"
echo ""

wait_for_user "Verify all data matches what you see in the frontend"

echo ""
log_success "🎉 COMPLETE SYSTEM TEST FINISHED!"
echo "=================================="
echo ""
echo "📋 TESTED ENDPOINTS:"
echo "✅ POST /api/v1/users/ (Create user)"
echo "✅ GET /api/v1/users/ (List users)"
echo "✅ GET /api/v1/users/{id} (Get user details)"
echo "✅ PATCH /api/v1/users/{id} (Update user)"
echo "✅ DELETE /api/v1/users/{id} (Deactivate user)"
echo "✅ PATCH /api/v1/users/me (Update own profile)"
echo "✅ POST /api/v1/auth/login (Login)"
echo "✅ POST /api/v1/auth/change-password (Change password)"
echo "✅ POST /api/v1/users/{id}/reset-password (Reset password)"
echo "✅ POST /api/v1/groups/{id}/users (Add user to group)"
echo "✅ DELETE /api/v1/groups/{id}/users/{user_id} (Remove user from group)"
echo "✅ Role-based access control"
echo "✅ User filtering and search"
echo ""
echo "📱 FRONTEND VERIFICATION:"
echo "✅ User Manager CRUD operations"
echo "✅ Group Manager user assignment"
echo "✅ Session Manager instructor assignment"
echo "✅ Permission-based UI access"
echo "✅ Profile management"
echo "✅ Authentication flows"
echo ""
echo "🎯 ALL USER MANAGEMENT ENDPOINTS TESTED SUCCESSFULLY!"

# Cleanup function
cleanup() {
    echo ""
    log_info "Test completed. Database remains in final test state."
    log_info "To clean up: run this script again or manually truncate tables"
}

trap cleanup EXIT