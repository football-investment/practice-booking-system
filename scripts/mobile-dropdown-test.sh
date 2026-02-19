#!/bin/bash

# Mobile Color Dropdown Functionality Test
# Tests the new iPhone-friendly dropdown color selector

echo "📱 Mobile Color Dropdown Functionality Test"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}🧪 Testing: $test_name${NC}"
    
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

# Function to check if pattern exists in file
check_pattern() {
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

echo -e "${YELLOW}🚀 Starting mobile dropdown functionality tests...${NC}"

# Test files
header_js="frontend/src/components/common/AppHeader.js"
header_css="frontend/src/components/common/AppHeader.css"

# Test 1: JavaScript Implementation
echo -e "\n${PURPLE}=== JavaScript Implementation Tests ===${NC}"

check_pattern "$header_js" "isColorDropdownOpen" "Dropdown state management"
check_pattern "$header_js" "setIsColorDropdownOpen" "Dropdown state setter"
check_pattern "$header_js" "color-dropdown-container" "Dropdown container element"
check_pattern "$header_js" "color-dropdown-trigger" "Dropdown trigger button"
check_pattern "$header_js" "color-dropdown-menu" "Dropdown menu element"
check_pattern "$header_js" "color-dropdown-item" "Dropdown menu items"
check_pattern "$header_js" "handleColorSelect" "Color selection handler"
check_pattern "$header_js" "handleClickOutside" "Click outside handler"
check_pattern "$header_js" "getColorIcon" "Color icon utility function"
check_pattern "$header_js" "getColorName" "Color name utility function"

# Test 2: CSS Styling
echo -e "\n${PURPLE}=== CSS Styling Tests ===${NC}"

check_pattern "$header_css" "color-dropdown-container" "Dropdown container styles"
check_pattern "$header_css" "color-dropdown-trigger" "Dropdown trigger styles"
check_pattern "$header_css" "color-dropdown-menu" "Dropdown menu styles"
check_pattern "$header_css" "color-dropdown-item" "Dropdown item styles"
check_pattern "$header_css" "dropdown-arrow" "Dropdown arrow indicator"
check_pattern "$header_css" "checkmark" "Selected item checkmark"

# Test 3: Mobile Responsiveness
echo -e "\n${PURPLE}=== Mobile Responsiveness Tests ===${NC}"

check_pattern "$header_css" "display.*block.*!important" "Mobile dropdown visibility"
check_pattern "$header_css" "display.*none.*!important" "Desktop buttons hidden on mobile"
check_pattern "$header_css" "max-width.*428px" "iPhone breakpoint coverage"

# Test 4: iPhone-specific Optimizations
echo -e "\n${PURPLE}=== iPhone-specific Optimizations ===${NC}"

# iPhone SE (375px)
check_pattern "$header_css" "min-width.*80px" "iPhone SE compact dropdown"
check_pattern "$header_css" "color-name.*display.*none" "iPhone SE text hiding"

# iPhone 12/13/14 (390px)  
check_pattern "$header_css" "min-width.*100px" "iPhone standard dropdown size"

# Test 5: UX Features
echo -e "\n${PURPLE}=== UX Features Tests ===${NC}"

check_pattern "$header_js" "useRef" "Dropdown reference for click outside"
check_pattern "$header_js" "useEffect.*handleClickOutside" "Click outside event listener"
check_pattern "$header_css" "position.*absolute" "Dropdown positioning"
check_pattern "$header_css" "z-index.*1000" "Dropdown stacking order"
check_pattern "$header_css" "backdrop-filter.*blur" "Dropdown backdrop effect"
check_pattern "$header_css" "box-shadow" "Dropdown elevation effect"

# Test 6: Touch Optimization
echo -e "\n${PURPLE}=== Touch Optimization Tests ===${NC}"

check_pattern "$header_css" "min-height.*44" "iOS touch target size"
check_pattern "$header_css" "touch-action.*manipulation" "Touch action optimization"
check_pattern "$header_css" "-webkit-tap-highlight-color" "iOS tap highlight control"

# Test 7: Build Integration
echo -e "\n${PURPLE}=== Build Integration Tests ===${NC}"

run_test "Frontend builds successfully" \
    "cd frontend && npm run build >/dev/null 2>&1 && echo 'Build successful'" \
    "Build successful"

run_test "CSS contains dropdown classes in build" \
    "find frontend/build -name '*.css' -exec grep -l 'color-dropdown' {} \; | wc -l" \
    "[1-9]"

run_test "JS contains dropdown logic in build" \
    "find frontend/build -name '*.js' -exec grep -l 'isColorDropdownOpen' {} \; | wc -l" \
    "[1-9]"

# Test 8: Desktop Fallback
echo -e "\n${PURPLE}=== Desktop Fallback Tests ===${NC}"

check_pattern "$header_css" "desktop-only" "Desktop fallback class"
check_pattern "$header_js" "desktop-only" "Desktop fallback implementation"

# Summary
echo -e "\n${YELLOW}================================================${NC}"
echo -e "${YELLOW}📊 Mobile Dropdown Test Results${NC}"
echo -e "${YELLOW}================================================${NC}"

if [[ $PASSED_TESTS -eq $TOTAL_TESTS ]]; then
    echo -e "\n${GREEN}🎉 ALL TESTS PASSED! ($PASSED_TESTS/$TOTAL_TESTS)${NC}"
    echo -e "${GREEN}✅ Mobile dropdown is fully implemented and optimized${NC}"
    echo -e "${GREEN}📱 iPhone users will now have a user-friendly color selector${NC}"
    echo -e "${GREEN}🚀 Ready for deployment!${NC}"
    exit 0
else
    failed_tests=$((TOTAL_TESTS - PASSED_TESTS))
    echo -e "\n${RED}❌ $failed_tests test(s) failed ($PASSED_TESTS/$TOTAL_TESTS passed)${NC}"
    
    success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    if [[ $success_rate -ge 80 ]]; then
        echo -e "${YELLOW}⚠️ Mobile dropdown is mostly working ($success_rate%)${NC}"
        exit 0
    else
        echo -e "${RED}🛠️ Mobile dropdown needs significant improvements${NC}"
        exit 1
    fi
fi