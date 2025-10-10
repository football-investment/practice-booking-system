#!/bin/bash
# 🚀 LFA Pre-Deployment Comprehensive Check
# Verifies all components before live testing 2025.09.20-22

echo "🔍 LFA Pre-Deployment Verification Started"
echo "========================================="
echo "📅 Check Time: $(date)"
echo "🎯 Target: 2-day live testing (2025.09.20-22)"
echo ""

ERRORS=0
WARNINGS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((ERRORS++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. Database Connectivity Check
echo "📊 Testing database connection..."
if python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        database='practice_booking_system',
        user='lovas.zoltan'
    )
    print('Database connection successful')
    conn.close()
    exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" >/dev/null 2>&1; then
    print_success "Database connection OK"
else
    print_error "Database connection failed"
fi

# 2. LFA Test Users Verification
echo "👥 Verifying LFA test users..."
USER_COUNT=$(python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='practice_booking_system', user='lovas.zoltan')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM users WHERE email LIKE '%@lfa.test'\")
count = cur.fetchone()[0]
print(count)
cur.close()
conn.close()
" 2>/dev/null)

if [ "$USER_COUNT" -eq 9 ]; then
    print_success "All 9 LFA test users present"
else
    print_error "Expected 9 LFA users, found $USER_COUNT"
fi

# 3. Football Sessions Verification
echo "⚽ Verifying football sessions..."
SESSION_COUNT=$(python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='practice_booking_system', user='lovas.zoltan')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM sessions WHERE title LIKE '%Taktikai%' OR title LIKE '%Labdabirtoklás%' OR title LIKE '%Kondicionálás%' OR title LIKE '%Mérkőzés%' OR title LIKE '%Cross-Semester%'\")
count = cur.fetchone()[0]
print(count)
cur.close()
conn.close()
" 2>/dev/null)

if [ "$SESSION_COUNT" -ge 6 ]; then
    print_success "Football sessions found: $SESSION_COUNT"
else
    print_warning "Expected 6+ football sessions, found $SESSION_COUNT"
fi

# 4. Football Projects Verification
echo "📚 Verifying football projects..."
PROJECT_COUNT=$(python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='practice_booking_system', user='lovas.zoltan')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM projects WHERE title LIKE '%Barcelona%' OR title LIKE '%Real Madrid%' OR title LIKE '%Liverpool%' OR title LIKE '%Cross-Semester%'\")
count = cur.fetchone()[0]
print(count)
cur.close()
conn.close()
" 2>/dev/null)

if [ "$PROJECT_COUNT" -ge 3 ]; then
    print_success "Football projects found: $PROJECT_COUNT"
else
    print_error "Expected 3+ football projects, found $PROJECT_COUNT"
fi

# 5. Test Semesters Verification
echo "📅 Verifying test semesters..."
SEMESTER_COUNT=$(python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='practice_booking_system', user='lovas.zoltan')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM semesters WHERE code LIKE '%TEST%' OR code LIKE '%DEMO%' OR code LIKE '%CROSS%'\")
count = cur.fetchone()[0]
print(count)
cur.close()
conn.close()
" 2>/dev/null)

if [ "$SEMESTER_COUNT" -ge 4 ]; then
    print_success "Test semesters configured: $SEMESTER_COUNT"
else
    print_error "Expected 4 test semesters, found $SEMESTER_COUNT"
fi

# 6. Password Hash Verification
echo "🔐 Verifying password hashes..."
HASH_CHECK=$(python3 -c "
import psycopg2
from app.core.security import verify_password
conn = psycopg2.connect(host='localhost', database='practice_booking_system', user='lovas.zoltan')
cur = conn.cursor()
cur.execute(\"SELECT password_hash FROM users WHERE email = 'messi@lfa.test'\")
hash_val = cur.fetchone()[0]
if verify_password('FootballMaster2025!', hash_val):
    print('Password verification successful')
    exit(0)
else:
    print('Password verification failed')
    exit(1)
cur.close()
conn.close()
" 2>/dev/null)

if [ $? -eq 0 ]; then
    print_success "Password hashes verified"
else
    print_error "Password hash verification failed"
fi

# 7. Required Tables Check
echo "🗃️  Verifying database schema..."
REQUIRED_TABLES="users semesters groups sessions bookings projects project_milestones project_enrollments attendance feedback"
MISSING_TABLES=""

for table in $REQUIRED_TABLES; do
    if python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='practice_booking_system', user='lovas.zoltan')
cur = conn.cursor()
cur.execute(\"SELECT 1 FROM $table LIMIT 1\")
cur.close()
conn.close()
" >/dev/null 2>&1; then
        continue
    else
        MISSING_TABLES="$MISSING_TABLES $table"
    fi
done

if [ -z "$MISSING_TABLES" ]; then
    print_success "All required database tables present"
else
    print_error "Missing tables:$MISSING_TABLES"
fi

# 8. Cross-Semester Logic Check
echo "🌐 Verifying cross-semester implementation..."
if grep -q "mbappe@lfa.test" app/api/api_v1/endpoints/sessions.py; then
    print_success "Cross-semester logic implemented for Mbappé"
else
    print_error "Cross-semester logic missing in sessions endpoint"
fi

if grep -q "Cross-semester.*enrollment.*not.*allowed" app/api/api_v1/endpoints/projects.py; then
    print_success "Project enrollment restrictions implemented"
else
    print_error "Project enrollment restrictions missing"
fi

# 9. Frontend Build Check
echo "🎨 Checking frontend build status..."
if [ -d "build" ] || [ -d "dist" ] || [ -d "frontend/build" ] || [ -d "frontend/dist" ]; then
    print_success "Frontend build directory found"
elif [ -f "frontend/package.json" ]; then
    print_warning "Frontend source found but no build directory"
    print_info "Run: cd frontend && npm run build"
else
    print_error "Frontend files not found"
fi

# 10. Environment Configuration Check
echo "⚙️  Checking environment configuration..."
if [ -f ".env" ] || [ -f ".env.local" ] || [ -f "app/config.py" ]; then
    print_success "Environment configuration files present"
else
    print_warning "Environment configuration may be missing"
fi

# 11. Python Dependencies Check
echo "🐍 Checking Python dependencies..."
if python3 -c "
import fastapi, sqlalchemy, psycopg2, passlib, jose
print('Core dependencies available')
" >/dev/null 2>&1; then
    print_success "Core Python dependencies installed"
else
    print_error "Missing Python dependencies"
    print_info "Run: pip install -r requirements.txt"
fi

# 12. Test Script Verification
echo "🧪 Verifying test scripts..."
if [ -f "lfa_test_verification.py" ]; then
    print_success "LFA test verification script present"
else
    print_error "LFA test verification script missing"
fi

if [ -f "generate_password_hashes.py" ]; then
    print_success "Password hash generator present"
else
    print_warning "Password hash generator missing"
fi

# Summary Report
echo ""
echo "========================================="
echo "🏁 Pre-Deployment Check Summary"
echo "========================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED - READY FOR LIVE TESTING!${NC}"
    echo ""
    echo "✅ Database: Fully configured with 9 futballista accounts"
    echo "✅ Sessions: Football-themed sessions created"
    echo "✅ Projects: Realistic football projects with milestones"
    echo "✅ Logic: Cross-semester access (Mbappé) & restrictions implemented"
    echo "✅ Security: Password authentication working"
    echo ""
    echo "🚀 Next Steps:"
    echo "1. Start backend: uvicorn app.main:app --reload"
    echo "2. Start frontend: cd frontend && npm start"
    echo "3. Run tests: python3 lfa_test_verification.py"
    echo "4. Begin live testing with futballista accounts"
    echo ""
    echo "🔑 Login Credentials:"
    echo "   Email: messi@lfa.test (or any @lfa.test account)"
    echo "   Password: FootballMaster2025!"
    
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS DETECTED - REVIEW BEFORE DEPLOYMENT${NC}"
    echo "❓ $WARNINGS warnings found (see above)"
    echo "✅ No critical errors"
    echo ""
    echo "💡 Consider addressing warnings for optimal testing experience"
    
else
    echo -e "${RED}❌ CRITICAL ERRORS DETECTED - FIX BEFORE DEPLOYMENT${NC}"
    echo "🚨 $ERRORS critical errors found"
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠️  $WARNINGS warnings also detected"
    fi
    echo ""
    echo "🔧 Fix all errors before proceeding with live testing"
fi

echo "========================================="
echo "📊 Final Status: $ERRORS errors, $WARNINGS warnings"
echo "📅 Check completed: $(date)"

# Exit with appropriate code
if [ $ERRORS -eq 0 ]; then
    exit 0
else
    exit 1
fi