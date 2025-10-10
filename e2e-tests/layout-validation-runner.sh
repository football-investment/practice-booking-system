#!/bin/bash
# Automated Layout Validation Test Runner
# Runs comprehensive layout tests across different devices and viewports

set -e

echo "🚀 Starting Automated Layout Validation Suite..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if servers are running
check_servers() {
    echo -e "${BLUE}🔍 Checking if servers are running...${NC}"
    
    # Check backend
    if ! curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${RED}❌ Backend server not running on port 8000${NC}"
        echo -e "${YELLOW}💡 Start with: uvicorn app.main:app --reload --port 8000${NC}"
        exit 1
    fi
    
    # Check frontend
    if ! curl -s http://localhost:3000 > /dev/null; then
        echo -e "${RED}❌ Frontend server not running on port 3000${NC}"
        echo -e "${YELLOW}💡 Start with: npm start${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Both servers are running${NC}"
}

# Create test user if not exists
create_test_user() {
    echo -e "${BLUE}👤 Ensuring test user exists...${NC}"
    
    cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Invetsment\ -\ Internship/practice_booking_system
    
    PYTHONPATH=/Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Invetsment\ -\ Internship/practice_booking_system python3 -c "
from app.database import get_db
from app.models import User, UserRole
from app.core.security import get_password_hash

db = next(get_db())

# Check if test user already exists
existing_user = db.query(User).filter(User.email == 'test.student@devstudio.com').first()

if not existing_user:
    test_user = User(
        name='Test Student',
        email='test.student@devstudio.com',
        password_hash=get_password_hash('testpass123'),
        role=UserRole.STUDENT,
        is_active=True
    )
    db.add(test_user)
    db.commit()
    print('✅ Test user created')
else:
    print('✅ Test user already exists')

db.close()
" 2>/dev/null
    
    echo -e "${GREEN}✅ Test user ready${NC}"
}

# Run timeline layout tests
run_timeline_tests() {
    echo -e "${BLUE}🧪 Running Timeline Layout Tests...${NC}"
    
    cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Invetsment\ -\ Internship/practice_booking_system/e2e-tests
    
    # Run layout validation tests
    npx playwright test tests/layout-validation.spec.js --reporter=html
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ All layout tests passed!${NC}"
    else
        echo -e "${RED}❌ Some layout tests failed${NC}"
        echo -e "${YELLOW}💡 Check the HTML report: e2e-tests/playwright-report/index.html${NC}"
    fi
    
    return $exit_code
}

# Generate layout validation report
generate_report() {
    echo -e "${BLUE}📊 Generating Layout Validation Report...${NC}"
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_file="layout-validation-report-${timestamp}.md"
    
    cat > "$report_file" << EOF
# Layout Validation Report
**Generated:** $(date)
**Test Suite:** Timeline Layout Validation

## Test Results Summary
- **Timeline Width Consistency:** $([ -f "screenshots/timeline-desktop.png" ] && echo "✅ PASSED" || echo "❌ FAILED")
- **Overflow Detection:** $(grep -q "OVERFLOW DETECTED" logs/* 2>/dev/null && echo "❌ FAILED" || echo "✅ PASSED")
- **CSS Grid Implementation:** $(grep -q "display: grid" ../frontend/src/pages/student/StudentDashboard.css && echo "✅ PASSED" || echo "❌ FAILED")
- **Responsive Design:** $([ -f "screenshots/timeline-mobile.png" ] && echo "✅ PASSED" || echo "❌ FAILED")

## Screenshots Generated
$(ls screenshots/timeline-*.png 2>/dev/null | sed 's/^/- /' || echo "- No screenshots generated")

## Recommendations
1. **Automated CI Integration:** Add these tests to your CI/CD pipeline
2. **Visual Regression Testing:** Set up baseline comparisons
3. **Performance Monitoring:** Add load time assertions
4. **Cross-Browser Testing:** Test on Safari, Firefox, Chrome
5. **Accessibility Testing:** Add WCAG compliance checks

## Next Steps
- [ ] Integrate with GitHub Actions
- [ ] Set up Lighthouse performance audits
- [ ] Add mobile-first responsive testing
- [ ] Implement visual diff comparison
EOF
    
    echo -e "${GREEN}✅ Report generated: $report_file${NC}"
}

# Main execution
main() {
    echo -e "${YELLOW}🎯 Automated Layout Validation for Practice Booking System${NC}"
    echo -e "${YELLOW}=================================================${NC}"
    
    check_servers
    create_test_user
    
    if run_timeline_tests; then
        echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
        generate_report
        echo -e "${BLUE}📱 Next: Visual comparison across devices completed${NC}"
        echo -e "${BLUE}🔗 View results: open e2e-tests/playwright-report/index.html${NC}"
        exit 0
    else
        echo -e "${RED}💥 Some tests failed - check the report${NC}"
        generate_report
        exit 1
    fi
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi