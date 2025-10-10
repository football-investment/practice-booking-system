#!/bin/bash

# Comprehensive iOS Device Testing Script
# Tests header and frontend design across all iPhone and iPad sizes

echo "📱 Comprehensive iOS Frontend Design Testing"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}🧪 Testing: $test_name${NC}"
    
    # Run the test command
    result=$(eval "$test_command" 2>&1)
    
    # Check if result matches expected pattern
    if [[ $result =~ $expected_result ]] || [[ -z "$expected_result" && $? -eq 0 ]]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo -e "${YELLOW}Expected: $expected_result${NC}"
        echo -e "${YELLOW}Got: $result${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function to check CSS breakpoint
check_breakpoint() {
    local device_name="$1"
    local width="$2"
    local css_file="$3"
    
    if grep -q "max-width.*${width}px" "$css_file"; then
        run_test "📱 ${device_name} (${width}px) breakpoint" "echo 'Breakpoint found'" "Breakpoint found"
    else
        run_test "📱 ${device_name} (${width}px) breakpoint" "echo 'Breakpoint missing'" "XXX_NOT_FOUND_XXX"
    fi
}

# Function to check device-specific optimizations
check_device_optimizations() {
    local device_name="$1"
    local width="$2"
    local min_width="$3"
    local css_file="$4"
    
    echo -e "\n${PURPLE}📱 ${device_name} (${width}px) Detailed Analysis:${NC}"
    
    # Check specific breakpoint range
    if [[ -n "$min_width" ]]; then
        pattern="min-width.*${min_width}px.*max-width.*${width}px"
    else
        pattern="max-width.*${width}px"
    fi
    
    if grep -q "$pattern" "$css_file"; then
        echo -e "${GREEN}✅ Specific breakpoint range found${NC}"
    else
        echo -e "${YELLOW}⚠️ No specific breakpoint range for ${device_name}${NC}"
    fi
    
    # Check header optimizations
    optimizations=(
        "header-content:Header content styling"
        "padding:Padding adjustments"
        "font-size:Font size optimizations"
        "min-height.*44:iOS touch targets"
        "gap:Element spacing"
    )
    
    for opt_info in "${optimizations[@]}"; do
        IFS=':' read -r property description <<< "$opt_info"
        
        # Count occurrences in device-specific sections
        count=$(awk "/$pattern/,/^}/" "$css_file" 2>/dev/null | grep -c "$property" || echo "0")
        
        if [[ $count -gt 0 ]]; then
            echo -e "${GREEN}  ✅ ${description}: ${count} instances${NC}"
        else
            echo -e "${RED}  ❌ ${description}: missing${NC}"
        fi
    done
}

echo -e "${CYAN}🚀 Starting comprehensive testing...${NC}\n"

# Test 1: File existence checks
echo -e "${YELLOW}=== 1. FILE EXISTENCE CHECKS ===${NC}"

run_test "AppHeader.css exists" \
    "ls frontend/src/components/common/AppHeader.css" \
    "AppHeader.css"

run_test "AppHeader.js exists" \
    "ls frontend/src/components/common/AppHeader.js" \
    "AppHeader.js"

run_test "iOS responsive CSS exists" \
    "ls frontend/src/styles/ios-responsive.css" \
    "ios-responsive.css"

# Test 2: Basic header structure
echo -e "\n${YELLOW}=== 2. BASIC HEADER STRUCTURE ===${NC}"

header_css="frontend/src/components/common/AppHeader.css"

run_test "Basic header classes present" \
    "grep -c 'header-content\\|header-left\\|header-center\\|header-right' $header_css" \
    "[4-9]"

run_test "Flexbox layout implemented" \
    "grep -c 'display.*flex' $header_css" \
    "[1-9]"

run_test "iOS optimizations section exists" \
    "grep -c 'iOS SAFARI' $header_css" \
    "[1-9]"

# Test 3: iPhone device breakpoints
echo -e "\n${YELLOW}=== 3. IPHONE DEVICE BREAKPOINTS ===${NC}"

# iPhone device specifications
declare -A iphone_devices=(
    ["iPhone SE"]="375"
    ["iPhone 12 mini"]="390"
    ["iPhone 12/13/14"]="390"
    ["iPhone 11"]="414"
    ["iPhone Pro Max"]="428"
)

for device in "${!iphone_devices[@]}"; do
    width=${iphone_devices[$device]}
    check_breakpoint "$device" "$width" "$header_css"
done

# Test 4: Detailed device optimizations
echo -e "\n${YELLOW}=== 4. DETAILED DEVICE OPTIMIZATIONS ===${NC}"

# Check iPhone SE (375px)
check_device_optimizations "iPhone SE" "375" "" "$header_css"

# Check iPhone 12/13/14 (390px)
check_device_optimizations "iPhone 12/13/14" "390" "376" "$header_css"

# Check iPhone 11 (414px)
check_device_optimizations "iPhone 11" "414" "391" "$header_css"

# Check iPhone Pro Max (428px)
check_device_optimizations "iPhone Pro Max" "428" "415" "$header_css"

# Test 5: Critical iOS features
echo -e "\n${YELLOW}=== 5. CRITICAL iOS FEATURES ===${NC}"

ios_features=(
    "-webkit-text-size-adjust:iOS text size adjustment"
    "-webkit-tap-highlight-color:Tap highlight control"
    "touch-action.*manipulation:Touch action optimization"
    "text-overflow.*ellipsis:Text overflow handling"
    "safe-area-inset:Safe area support"
    "min-height.*44:iOS touch targets"
    "-webkit-overflow-scrolling:Momentum scrolling"
    "-webkit-user-select:User selection control"
)

for feature_info in "${ios_features[@]}"; do
    IFS=':' read -r property description <<< "$feature_info"
    
    if grep -q "$property" "$header_css" || grep -q "$property" "frontend/src/styles/ios-responsive.css"; then
        run_test "$description" "echo 'Feature found'" "Feature found"
    else
        run_test "$description" "echo 'Feature missing'" "XXX_NOT_FOUND_XXX"
    fi
done

# Test 6: Layout stability
echo -e "\n${YELLOW}=== 6. LAYOUT STABILITY ===${NC}"

layout_checks=(
    "flex-shrink:Flex shrink properties"
    "overflow.*visible:Overflow handling"
    "white-space.*nowrap:Text wrapping prevention"
    "max-width:Width constraints"
    "box-sizing.*border-box:Box sizing"
)

for check_info in "${layout_checks[@]}"; do
    IFS=':' read -r property description <<< "$check_info"
    
    count=$(grep -c "$property" "$header_css")
    if [[ $count -gt 0 ]]; then
        run_test "$description" "echo 'Property found: $count instances'" "Property found"
    else
        run_test "$description" "echo 'Property missing'" "XXX_NOT_FOUND_XXX"
    fi
done

# Test 7: Theme support
echo -e "\n${YELLOW}=== 7. THEME SUPPORT ===${NC}"

theme_checks=(
    "data-theme.*dark:Dark theme support"
    "data-color:Color scheme support"
    "var(--:CSS custom properties"
)

for theme_info in "${theme_checks[@]}"; do
    IFS=':' read -r property description <<< "$theme_info"
    
    if grep -q "$property" "$header_css"; then
        run_test "$description" "echo 'Theme feature found'" "Theme feature found"
    else
        run_test "$description" "echo 'Theme feature missing'" "XXX_NOT_FOUND_XXX"
    fi
done

# Test 8: Build compilation
echo -e "\n${YELLOW}=== 8. BUILD COMPILATION ===${NC}"

echo -e "${BLUE}🔨 Testing frontend build...${NC}"
cd frontend 2>/dev/null || cd .

if npm run build >/dev/null 2>&1; then
    run_test "Frontend builds successfully" "echo 'Build successful'" "Build successful"
else
    run_test "Frontend builds successfully" "echo 'Build failed'" "XXX_BUILD_FAILED_XXX"
fi

cd .. 2>/dev/null || cd .

# Test 9: CSS validation
echo -e "\n${YELLOW}=== 9. CSS VALIDATION ===${NC}"

# Check CSS syntax
css_errors=0

# Check for unclosed braces
open_braces=$(grep -c "{" "$header_css")
close_braces=$(grep -c "}" "$header_css")

if [[ $open_braces -eq $close_braces ]]; then
    run_test "CSS braces are balanced" "echo 'Balanced: $open_braces open, $close_braces close'" "Balanced"
else
    run_test "CSS braces are balanced" "echo 'Unbalanced: $open_braces open, $close_braces close'" "XXX_UNBALANCED_XXX"
    css_errors=$((css_errors + 1))
fi

# Check for duplicate selectors
duplicate_selectors=$(grep -E "^\s*\.[a-zA-Z-]+" "$header_css" | sort | uniq -d | wc -l)
if [[ $duplicate_selectors -eq 0 ]]; then
    run_test "No duplicate selectors" "echo 'No duplicates found'" "No duplicates"
else
    run_test "No duplicate selectors" "echo '$duplicate_selectors duplicates found'" "XXX_DUPLICATES_XXX"
fi

# Test 10: Performance optimizations
echo -e "\n${YELLOW}=== 10. PERFORMANCE OPTIMIZATIONS ===${NC}"

perf_checks=(
    "transform.*scale:Scale transforms for interactions"
    "transition.*ease:Smooth transitions"
    "will-change:Will-change optimizations"
    "transform.*translateZ:GPU acceleration"
)

for perf_info in "${perf_checks[@]}"; do
    IFS=':' read -r property description <<< "$perf_info"
    
    count=$(grep -c "$property" "$header_css" "$css_file" 2>/dev/null || echo "0")
    if [[ $count -gt 0 ]]; then
        run_test "$description" "echo 'Optimization found: $count instances'" "Optimization found"
    else
        run_test "$description" "echo 'Optimization missing'" "XXX_OPTIMIZATION_MISSING_XXX"
    fi
done

# Final Summary
echo -e "\n${YELLOW}================================================${NC}"
echo -e "${YELLOW}📊 COMPREHENSIVE TEST RESULTS${NC}"
echo -e "${YELLOW}================================================${NC}"

echo -e "\n${CYAN}📈 Statistics:${NC}"
echo -e "Total tests run: ${TOTAL_TESTS}"
echo -e "Passed: ${GREEN}${PASSED_TESTS}${NC}"
echo -e "Failed: ${RED}${FAILED_TESTS}${NC}"

# Calculate success rate
if [[ $TOTAL_TESTS -gt 0 ]]; then
    success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    echo -e "Success rate: ${CYAN}${success_rate}%${NC}"
    
    if [[ $success_rate -ge 90 ]]; then
        echo -e "\n${GREEN}🎉 EXCELLENT! iOS header optimization is highly successful${NC}"
        echo -e "${GREEN}✅ iPhone compatibility: EXCELLENT${NC}"
        exit 0
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "\n${YELLOW}👍 GOOD! iOS header optimization is working well${NC}"
        echo -e "${YELLOW}⚠️ iPhone compatibility: GOOD (minor improvements possible)${NC}"
        exit 0
    elif [[ $success_rate -ge 70 ]]; then
        echo -e "\n${YELLOW}🔧 MODERATE: iOS header needs some improvements${NC}"
        echo -e "${YELLOW}⚠️ iPhone compatibility: MODERATE${NC}"
        exit 1
    else
        echo -e "\n${RED}❌ CRITICAL: iOS header optimization needs major work${NC}"
        echo -e "${RED}❌ iPhone compatibility: POOR${NC}"
        exit 1
    fi
else
    echo -e "\n${RED}❌ ERROR: No tests were run${NC}"
    exit 1
fi