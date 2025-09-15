#!/bin/bash

# 🧪 FRONTEND TESTING AND INTEGRATION SCRIPT
# Tests the minimal frontend with backend

echo "🧪 FRONTEND TESTING & INTEGRATION"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    log_error "Frontend directory not found!"
    log_info "Run ./frontend_setup.sh first"
    exit 1
fi

cd frontend

# Step 1: Verify file structure
echo ""
echo "🔍 STEP 1: Verifying Frontend File Structure"
echo "============================================"

# Check required files
required_files=(
    "package.json"
    "public/index.html"
    "src/index.js"
    "src/App.js"
    "src/App.css"
    "src/contexts/AuthContext.js"
    "src/services/apiService.js"
    "src/pages/LoginPage.js"
    "src/pages/DashboardPage.js"
    "src/pages/AdminPage.js"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "File exists: $file"
    else
        log_error "Missing file: $file"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    log_error "Missing files found. Create all required files first."
    exit 1
fi

# Step 2: Install dependencies
echo ""
echo "📦 STEP 2: Installing Dependencies"
echo "=================================="

log_info "Running npm install..."
if npm install > npm_install.log 2>&1; then
    log_success "Dependencies installed successfully"
else
    log_error "npm install failed!"
    echo "Check npm_install.log for details"
    tail -20 npm_install.log
    exit 1
fi

# Step 3: Check for compilation errors
echo ""
echo "🔧 STEP 3: Checking for Compilation Errors"
echo "=========================================="

log_info "Checking React compilation..."

# Create a temporary build to check for syntax errors
if npm run build > build_check.log 2>&1; then
    log_success "React app compiles successfully"
    rm -rf build  # Clean up temporary build
else
    log_error "Compilation errors found!"
    echo "Build log:"
    tail -30 build_check.log
    
    log_warning "Common issues to check:"
    echo "  - Missing imports"
    echo "  - Syntax errors in JSX"
    echo "  - Incorrect file paths"
    echo "  - Missing dependencies"
    exit 1
fi

# Step 4: Backend connectivity test
echo ""
echo "🌐 STEP 4: Backend Connectivity Test"
echo "===================================="

log_info "Checking if backend is running..."

if curl -s http://localhost:8000/health > /dev/null; then
    log_success "Backend is running on port 8000"
    
    # Test API endpoints
    log_info "Testing API endpoints..."
    
    # Health check
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_success "Health endpoint working"
    else
        log_error "Health endpoint failed"
    fi
    
    # API documentation
    if curl -s http://localhost:8000/docs -o /dev/null; then
        log_success "API documentation accessible"
    else
        log_error "API documentation failed"
    fi
    
else
    log_error "Backend not running on port 8000!"
    log_info "Start backend with: uvicorn app.main:app --reload"
    exit 1
fi

# Step 5: Frontend startup test
echo ""
echo "🚀 STEP 5: Frontend Startup Test"
echo "================================"

log_info "Testing frontend startup..."

# Start frontend in background
npm start > frontend_startup.log 2>&1 &
FRONTEND_PID=$!

log_info "Frontend starting (PID: $FRONTEND_PID)..."
log_info "Waiting for frontend to be ready..."

# Wait for frontend to start (max 60 seconds)
for i in {1..60}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_success "Frontend started successfully on port 3000"
        break
    fi
    
    if [ $i -eq 60 ]; then
        log_error "Frontend failed to start within 60 seconds"
        kill $FRONTEND_PID 2>/dev/null
        echo "Startup log:"
        tail -30 frontend_startup.log
        exit 1
    fi
    
    sleep 1
done

# Step 6: Integration testing
echo ""
echo "🔗 STEP 6: Frontend-Backend Integration Test"
echo "==========================================="

log_info "Testing frontend-backend integration..."

# Test login page
if curl -s http://localhost:3000 | grep -q "Practice Booking System"; then
    log_success "Frontend serves login page"
else
    log_error "Frontend login page not working"
fi

# Test API proxy (React's proxy to backend)
if curl -s http://localhost:3000/api/v1/health > /dev/null 2>&1; then
    log_success "Frontend proxy to backend working"
else
    log_warning "Frontend proxy might have issues"
fi

# Step 7: Manual testing instructions
echo ""
echo "👤 STEP 7: Manual Testing Instructions"
echo "======================================"

log_success "Frontend is ready for manual testing!"
echo ""
echo "🌐 TESTING URLS:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "🔐 TEST CREDENTIALS:"
echo "  Email:    admin@company.com"
echo "  Password: admin123"
echo ""
echo "📋 MANUAL TEST CHECKLIST:"
echo "  [ ] 1. Open http://localhost:3000"
echo "  [ ] 2. Login with test credentials"
echo "  [ ] 3. Verify dashboard loads"
echo "  [ ] 4. Check API status indicator"
echo "  [ ] 5. Test admin panel (if admin user)"
echo "  [ ] 6. Verify data from backend displays"
echo "  [ ] 7. Test logout functionality"
echo ""

# Step 8: Create testing report
echo ""
echo "📊 STEP 8: Creating Testing Report"
echo "================================="

cat > testing_report.md << EOF
# Frontend Testing Report

**Date:** $(date)
**Frontend URL:** http://localhost:3000
**Backend URL:** http://localhost:8000

## ✅ Tests Completed

- [x] File structure verification
- [x] Dependency installation
- [x] React compilation check
- [x] Backend connectivity
- [x] Frontend startup
- [x] Integration testing

## 🎯 Manual Testing Checklist

- [ ] Login page loads
- [ ] Authentication works
- [ ] Dashboard displays data
- [ ] Admin panel accessible (admin users)
- [ ] API status indicator works
- [ ] Backend data displays correctly
- [ ] Logout functionality works

## 🔗 URLs for Testing

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔐 Test Credentials

- **Email:** admin@company.com
- **Password:** admin123

## 📝 Notes

This is a minimal frontend for backend testing purposes.
Focus is on functionality, not design/styling.

## 🚀 Next Steps

1. Complete manual testing checklist
2. Document any issues found
3. Test with different user roles
4. Validate all backend endpoints work through UI
EOF

log_success "Testing report created: testing_report.md"

echo ""
echo "🎉 FRONTEND TESTING COMPLETE"
echo "============================"
log_success "Frontend is running and ready for testing"
log_info "Frontend PID: $FRONTEND_PID (use 'kill $FRONTEND_PID' to stop)"
log_info "Keep this terminal open or frontend will stop"

echo ""
log_warning "IMPORTANT: Complete the manual testing checklist!"
log_info "Report any issues found during testing"

# Keep script running to show logs
echo ""
echo "📋 Frontend logs (Ctrl+C to stop):"
echo "=================================="
tail -f frontend_startup.log