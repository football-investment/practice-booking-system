#!/bin/bash

# Master script to run all validation tests

echo "🎯 PRACTICE BOOKING SYSTEM - MASTER VALIDATION"
echo "==============================================="
echo "This will run all validation tests to verify Claude Code's claims"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if server is running
check_server() {
    echo -e "${BLUE}Checking if server is running...${NC}"
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✅ Server is running${NC}"
        return 0
    else
        echo -e "${RED}❌ Server is not running!${NC}"
        echo ""
        echo "Please start the server first:"
        echo "1. source venv/bin/activate"
        echo "2. uvicorn app.main:app --reload"
        echo ""
        exit 1
    fi
}

# Make scripts executable
make_executable() {
    echo -e "${BLUE}Making scripts executable...${NC}"
    chmod +x quick_validation.sh 2>/dev/null || echo "quick_validation.sh not found"
    chmod +x database_validation.sh 2>/dev/null || echo "database_validation.sh not found"  
    chmod +x complete_system_journey.sh 2>/dev/null || echo "complete_system_journey.sh not found"
}

echo "Select validation type:"
echo ""
echo "1. 🚀 Quick Validation (2 minutes) - Essential tests"
echo "2. 🗄️  Database Validation (1 minute) - Database state check"  
echo "3. 🎯 Complete Journey (10 minutes) - Full system test"
echo "4. 📊 All Tests (15 minutes) - Everything"
echo ""
echo -n "Enter choice (1-4): "
read choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}🚀 RUNNING QUICK VALIDATION${NC}"
        echo "=========================="
        check_server
        
        # Quick validation inline
        echo ""
        echo "⚡ QUICK SYSTEM VALIDATION - Claude Code Claims Test"
        echo "=================================================="
        
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
        else
            echo -e "${RED}❌ Cannot test endpoints without admin token${NC}"
            ((FAILED+=2))
        fi
        
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
            else
                echo -e "${RED}⚠️  CLAUDE CODE CLAIMS QUESTIONABLE${NC}"
            fi
        fi
        ;;
        
    2)
        echo ""
        echo -e "${YELLOW}🗄️ RUNNING DATABASE VALIDATION${NC}"
        echo "==============================="
        
        echo "Checking database connection and state..."
        python3 -c "
import sys
sys.path.append('.')
try:
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    from app.models.semester import Semester
    from app.models.session import Session
    from app.models.booking import Booking
    
    db = SessionLocal()
    
    print('✅ Database connection successful')
    print('📊 Current database state:')
    
    users = db.query(User).count()
    semesters = db.query(Semester).count() 
    sessions = db.query(Session).count()
    bookings = db.query(Booking).count()
    
    print(f'   Users: {users}')
    print(f'   Semesters: {semesters}') 
    print(f'   Sessions: {sessions}')
    print(f'   Bookings: {bookings}')
    
    # User roles
    admins = db.query(User).filter(User.role == UserRole.ADMIN).count()
    instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR).count()
    students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    
    print(f'📋 User roles:')
    print(f'   Admins: {admins}')
    print(f'   Instructors: {instructors}')
    print(f'   Students: {students}')
    
    print(f'👥 Sample users:')
    sample_users = db.query(User).limit(3).all()
    for user in sample_users:
        print(f'   {user.name} ({user.email}) - {user.role.value}')
    
    db.close()
    
    if users > 0:
        print('🎉 Database validation successful!')
    else:
        print('⚠️  Database appears empty')
    
except Exception as e:
    print(f'❌ Database validation failed: {e}')
"
        ;;
        
    3)
        echo ""
        echo -e "${YELLOW}🎯 RUNNING COMPLETE JOURNEY${NC}"
        echo "============================"
        echo "This will take ~10 minutes and test everything..."
        echo ""
        check_server
        
        if [ -f "complete_system_journey.sh" ]; then
            ./complete_system_journey.sh
        else
            echo -e "${RED}❌ complete_system_journey.sh not found${NC}"
            echo "Please save the complete journey script first"
        fi
        ;;
        
    4)
        echo ""
        echo -e "${YELLOW}📊 RUNNING ALL TESTS${NC}"
        echo "==================="
        echo "This will run all validation tests..."
        echo ""
        check_server
        
        # Run all tests in sequence
        echo -e "${BLUE}Step 1: Quick validation...${NC}"
        if [ -f "quick_validation.sh" ]; then
            ./quick_validation.sh
        fi
        
        echo ""
        echo -e "${BLUE}Step 2: Database validation...${NC}"
        if [ -f "database_validation.sh" ]; then
            ./database_validation.sh
        fi
        
        echo ""
        echo -e "${BLUE}Step 3: Complete journey (if available)...${NC}"
        if [ -f "complete_system_journey.sh" ]; then
            echo "Starting complete journey in 5 seconds... (Ctrl+C to skip)"
            sleep 5
            ./complete_system_journey.sh
        else
            echo "Complete journey script not available"
        fi
        ;;
        
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "==============================================="
echo "🏁 VALIDATION COMPLETE"
echo "==============================================="
echo ""
echo "Next steps:"
echo "- Check API docs: http://localhost:8000/docs"
echo "- Monitor health: http://localhost:8000/health/detailed"
echo "- View test results above"
echo ""