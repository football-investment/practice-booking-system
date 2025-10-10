#!/bin/bash

# iOS Safari Responsive Design Validation Test
# Tests the responsive design optimizations for iOS Safari

echo "🍎 iOS Safari Responsive Design Validation Test"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}Testing: $test_name${NC}"
    
    # Run the test command
    result=$(eval "$test_command" 2>&1)
    
    # Check if result matches expected pattern
    if [[ $result =~ $expected_pattern ]] || [[ -z "$expected_pattern" && $? -eq 0 ]]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo "Expected pattern: $expected_pattern"
        echo "Actual result: $result"
        return 1
    fi
}

# Function to check if file exists and contains pattern
check_file_content() {
    local file_path="$1"
    local pattern="$2"
    local description="$3"
    
    if [[ -f "$file_path" ]]; then
        if grep -q "$pattern" "$file_path"; then
            run_test "$description" "echo 'Pattern found'" "Pattern found"
        else
            run_test "$description" "echo 'Pattern not found'" "XXX_WILL_NOT_MATCH_XXX"
        fi
    else
        run_test "$description" "echo 'File not found'" "XXX_WILL_NOT_MATCH_XXX"
    fi
}

# Start tests
echo -e "${YELLOW}Starting iOS Safari validation tests...${NC}"

# Test 1: Check if iOS responsive CSS file exists
run_test "iOS responsive CSS file exists" \
    "ls frontend/src/styles/ios-responsive.css" \
    "ios-responsive.css"

# Test 2: Check if CSS file is imported in index.css
check_file_content "frontend/src/index.css" \
    "@import './styles/ios-responsive.css'" \
    "iOS CSS imported in index.css"

# Test 3: Check for iPhone-specific breakpoints
check_file_content "frontend/src/styles/ios-responsive.css" \
    "@media.*max-width.*375px" \
    "iPhone SE breakpoint (375px) defined"

check_file_content "frontend/src/styles/ios-responsive.css" \
    "@media.*max-width.*390px" \
    "iPhone 12/13/14 breakpoint (390px) defined"

check_file_content "frontend/src/styles/ios-responsive.css" \
    "@media.*max-width.*428px" \
    "iPhone Pro Max breakpoint (428px) defined"

# Test 4: Check for safe area support
check_file_content "frontend/src/styles/ios-responsive.css" \
    "env(safe-area-inset" \
    "Safe area inset support implemented"

# Test 5: Check for touch target optimization
check_file_content "frontend/src/styles/ios-responsive.css" \
    "min-height.*44px" \
    "44px minimum touch targets for iOS"

# Test 6: Check for Safari-specific fixes
check_file_content "frontend/src/styles/ios-responsive.css" \
    "-webkit-overflow-scrolling.*touch" \
    "Safari momentum scrolling optimizations"

# Test 7: Check HTML viewport meta tag
check_file_content "frontend/public/index.html" \
    "viewport-fit=cover" \
    "Viewport fit cover for notched devices"

# Test 8: Check for iOS web app meta tags
check_file_content "frontend/public/index.html" \
    "apple-mobile-web-app" \
    "iOS web app meta tags present"

# Test 9: Check for iOS optimization JavaScript
run_test "iOS optimization JS file exists" \
    "ls frontend/src/utils/iosOptimizations.js" \
    "iosOptimizations.js"

# Test 10: Check if JS optimizations are imported
check_file_content "frontend/src/App.js" \
    "iosOptimizations" \
    "iOS optimizations imported in App.js"

# Test 11: Check for dynamic viewport height support
check_file_content "frontend/public/index.html" \
    "--vh.*window.innerHeight" \
    "Dynamic viewport height calculation"

# Test 12: Check for performance optimizations
check_file_content "frontend/src/utils/iosOptimizations.js" \
    "prefers-reduced-motion" \
    "Reduced motion optimization for low-power devices"

# Test 13: Check AppHeader iOS optimizations
check_file_content "frontend/src/components/common/AppHeader.css" \
    "iPhone SE.*375px" \
    "AppHeader iPhone SE optimizations"

# Test 14: Check for touch action optimizations
check_file_content "frontend/src/styles/ios-responsive.css" \
    "touch-action.*manipulation" \
    "Touch action manipulation to prevent zoom"

# Test 15: Check for backdrop-filter Safari support
check_file_content "frontend/src/components/common/AppHeader.css" \
    "-webkit-backdrop-filter" \
    "Safari backdrop-filter support"

# Test 16: Run frontend build to check for compilation errors
echo -e "\n${BLUE}Testing: Frontend build compilation${NC}"
cd frontend 2>/dev/null || cd .
if npm run build >/dev/null 2>&1; then
    run_test "Frontend builds without errors" "echo 'Build successful'" "Build successful"
else
    run_test "Frontend builds without errors" "echo 'Build failed'" "XXX_WILL_NOT_MATCH_XXX"
fi
cd .. 2>/dev/null || cd .

# Test 17: Check CSS validity (basic syntax check)
echo -e "\n${BLUE}Testing: CSS syntax validation${NC}"
css_errors=$(grep -n "}" frontend/src/styles/ios-responsive.css | wc -l)
css_opens=$(grep -n "{" frontend/src/styles/ios-responsive.css | wc -l)

if [[ $css_errors -eq $css_opens ]]; then
    run_test "CSS brackets are balanced" "echo 'Balanced'" "Balanced"
else
    run_test "CSS brackets are balanced" "echo 'Unbalanced'" "XXX_WILL_NOT_MATCH_XXX"
fi

# Test 18: Check for specific iOS device optimizations
echo -e "\n${BLUE}Device-specific optimization tests:${NC}"

check_file_content "frontend/src/styles/ios-responsive.css" \
    "iphone-se.*375px" \
    "iPhone SE specific optimizations"

check_file_content "frontend/src/styles/ios-responsive.css" \
    "iphone-standard.*390px" \
    "iPhone standard size optimizations"

check_file_content "frontend/src/styles/ios-responsive.css" \
    "iphone-pro-max.*428px" \
    "iPhone Pro Max optimizations"

# Test 19: Check for accessibility improvements
check_file_content "frontend/src/utils/iosOptimizations.js" \
    "aria-label" \
    "Accessibility enhancements for VoiceOver"

# Test 20: Check for keyboard handling
check_file_content "frontend/src/utils/iosOptimizations.js" \
    "keyboard.*appearance" \
    "Virtual keyboard handling optimizations"

# Summary
echo -e "\n${YELLOW}================================================${NC}"
echo -e "${YELLOW}iOS Safari Validation Test Results${NC}"
echo -e "${YELLOW}================================================${NC}"

if [[ $PASSED_TESTS -eq $TOTAL_TESTS ]]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! ($PASSED_TESTS/$TOTAL_TESTS)${NC}"
    echo -e "${GREEN}✅ iOS Safari responsive design is fully optimized${NC}"
    exit 0
else
    echo -e "${RED}❌ $((TOTAL_TESTS - PASSED_TESTS)) test(s) failed ($PASSED_TESTS/$TOTAL_TESTS passed)${NC}"
    echo -e "${YELLOW}⚠️  iOS Safari optimizations need attention${NC}"
    exit 1
fi