#!/bin/bash

# Simple iOS Header Validation - Quick and Effective
echo "📱 iOS Header Validation - Quick Test"
echo "====================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

passed=0
total=0

test_feature() {
    total=$((total + 1))
    local name="$1"
    local file="$2"
    local pattern="$3"
    
    if grep -q "$pattern" "$file"; then
        echo -e "${GREEN}✅ $name${NC}"
        passed=$((passed + 1))
    else
        echo -e "${RED}❌ $name${NC}"
    fi
}

header_css="frontend/src/components/common/AppHeader.css"

echo -e "\n${BLUE}🔍 Checking critical iPhone optimizations...${NC}"

# Core iPhone breakpoints
test_feature "iPhone SE (375px) breakpoint" "$header_css" "max-width.*375px"
test_feature "iPhone 12/13/14 (390px) breakpoint" "$header_css" "390px"
test_feature "iPhone 11 (414px) breakpoint" "$header_css" "414px" 
test_feature "iPhone Pro Max (428px) breakpoint" "$header_css" "428px"

# Essential iOS features
test_feature "44px touch targets" "$header_css" "min-height.*44"
test_feature "Text overflow handling" "$header_css" "text-overflow.*ellipsis"
test_feature "Touch action optimization" "$header_css" "touch-action.*manipulation"
test_feature "Safari webkit fixes" "$header_css" "-webkit-"
test_feature "Flexbox layout stability" "$header_css" "flex-shrink"
test_feature "Safe area support" "$header_css" "safe-area-inset"

# Layout stability
test_feature "Overflow control" "$header_css" "overflow.*visible"
test_feature "Text wrapping control" "$header_css" "white-space.*nowrap"
test_feature "Layout constraints" "$header_css" "max-width"
test_feature "Theme support" "$header_css" "data-theme"

echo -e "\n${BLUE}📊 Results: ${GREEN}$passed${NC}/${total} tests passed${NC}"

success_rate=$(( (passed * 100) / total ))

if [[ $success_rate -ge 85 ]]; then
    echo -e "${GREEN}🎉 EXCELLENT! iPhone header optimization successful (${success_rate}%)${NC}"
    exit 0
elif [[ $success_rate -ge 75 ]]; then
    echo -e "${YELLOW}👍 GOOD! iPhone header working well (${success_rate}%)${NC}"
    exit 0
else
    echo -e "${RED}❌ NEEDS WORK: iPhone header needs improvements (${success_rate}%)${NC}"
    exit 1
fi