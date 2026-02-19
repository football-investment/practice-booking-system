#!/bin/bash

# Final Header Validation - Complete iPhone Compatibility Check
echo "📱 FINAL iPhone Header Compatibility Validation"
echo "================================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Comprehensive iPhone Header Testing...${NC}\n"

# Test files
header_css="frontend/src/components/common/AppHeader.css"
header_js="frontend/src/components/common/AppHeader.js"
ios_css="frontend/src/styles/ios-responsive.css"

# Counters
device_tests=0
device_passed=0
feature_tests=0
feature_passed=0
layout_tests=0
layout_passed=0

# Device-specific tests
echo -e "${YELLOW}📱 DEVICE-SPECIFIC OPTIMIZATIONS:${NC}"

# iPhone SE (375px)
if grep -q "max-width.*375px" "$header_css"; then
    echo -e "${GREEN}✅ iPhone SE (375px) - Breakpoint defined${NC}"
    device_passed=$((device_passed + 1))
    
    # Check SE-specific optimizations
    if grep -A 20 "max-width.*375px" "$header_css" | grep -q "display.*none"; then
        echo -e "${GREEN}  ✅ Title hidden on small screen${NC}"
    else
        echo -e "${RED}  ❌ Title hiding missing${NC}"
    fi
    
    if grep -A 20 "max-width.*375px" "$header_css" | grep -q "font-size.*11px"; then
        echo -e "${GREEN}  ✅ Font sizes optimized${NC}"
    else
        echo -e "${RED}  ❌ Font optimization missing${NC}"
    fi
else
    echo -e "${RED}❌ iPhone SE (375px) - Missing breakpoint${NC}"
fi
device_tests=$((device_tests + 1))

# iPhone 12/13/14 (390px)
if grep -q "390px" "$header_css"; then
    echo -e "${GREEN}✅ iPhone 12/13/14 (390px) - Breakpoint defined${NC}"
    device_passed=$((device_passed + 1))
else
    echo -e "${RED}❌ iPhone 12/13/14 (390px) - Missing breakpoint${NC}"
fi
device_tests=$((device_tests + 1))

# iPhone 11 (414px)
if grep -q "414px" "$header_css"; then
    echo -e "${GREEN}✅ iPhone 11 (414px) - Breakpoint defined${NC}"
    device_passed=$((device_passed + 1))
else
    echo -e "${RED}❌ iPhone 11 (414px) - Missing breakpoint${NC}"
fi
device_tests=$((device_tests + 1))

# iPhone Pro Max (428px)
if grep -q "428px" "$header_css"; then
    echo -e "${GREEN}✅ iPhone Pro Max (428px) - Breakpoint defined${NC}"
    device_passed=$((device_passed + 1))
else
    echo -e "${RED}❌ iPhone Pro Max (428px) - Missing breakpoint${NC}"
fi
device_tests=$((device_tests + 1))

# iOS-specific features
echo -e "\n${YELLOW}🔧 iOS-SPECIFIC FEATURES:${NC}"

# Touch targets
if grep -q "min-height.*44" "$header_css"; then
    echo -e "${GREEN}✅ 44px minimum touch targets${NC}"
    feature_passed=$((feature_passed + 1))
else
    echo -e "${RED}❌ iOS touch targets missing${NC}"
fi
feature_tests=$((feature_tests + 1))

# Text overflow
if grep -q "text-overflow.*ellipsis" "$header_css"; then
    echo -e "${GREEN}✅ Text overflow handling${NC}"
    feature_passed=$((feature_passed + 1))
else
    echo -e "${RED}❌ Text overflow missing${NC}"
fi
feature_tests=$((feature_tests + 1))

# Touch action
if grep -q "touch-action.*manipulation" "$header_css"; then
    echo -e "${GREEN}✅ Touch action optimization${NC}"
    feature_passed=$((feature_passed + 1))
else
    echo -e "${RED}❌ Touch action missing${NC}"
fi
feature_tests=$((feature_tests + 1))

# User selection
if grep -q "user-select.*none" "$header_css"; then
    echo -e "${GREEN}✅ User selection disabled${NC}"
    feature_passed=$((feature_passed + 1))
else
    echo -e "${RED}❌ User selection not disabled${NC}"
fi
feature_tests=$((feature_tests + 1))

# Tap highlight
if grep -q "tap-highlight-color.*transparent" "$header_css"; then
    echo -e "${GREEN}✅ Tap highlight disabled${NC}"
    feature_passed=$((feature_passed + 1))
else
    echo -e "${RED}❌ Tap highlight not disabled${NC}"
fi
feature_tests=$((feature_tests + 1))

# Safe area
if grep -q "safe-area-inset" "$header_css" || grep -q "safe-area-inset" "$ios_css"; then
    echo -e "${GREEN}✅ Safe area support${NC}"
    feature_passed=$((feature_passed + 1))
else
    echo -e "${RED}❌ Safe area support missing${NC}"
fi
feature_tests=$((feature_tests + 1))

# Layout stability
echo -e "\n${YELLOW}⚖️ LAYOUT STABILITY:${NC}"

# Flexbox
if grep -q "display.*flex" "$header_css"; then
    echo -e "${GREEN}✅ Flexbox layout${NC}"
    layout_passed=$((layout_passed + 1))
else
    echo -e "${RED}❌ Flexbox missing${NC}"
fi
layout_tests=$((layout_tests + 1))

# Flex shrink
if grep -q "flex-shrink" "$header_css"; then
    echo -e "${GREEN}✅ Flex shrink control${NC}"
    layout_passed=$((layout_passed + 1))
else
    echo -e "${RED}❌ Flex shrink missing${NC}"
fi
layout_tests=$((layout_tests + 1))

# Overflow control
if grep -q "overflow.*visible" "$header_css"; then
    echo -e "${GREEN}✅ Overflow control${NC}"
    layout_passed=$((layout_passed + 1))
else
    echo -e "${RED}❌ Overflow control missing${NC}"
fi
layout_tests=$((layout_tests + 1))

# Text wrapping
if grep -q "white-space.*nowrap" "$header_css"; then
    echo -e "${GREEN}✅ Text wrapping prevention${NC}"
    layout_passed=$((layout_passed + 1))
else
    echo -e "${RED}❌ Text wrapping control missing${NC}"
fi
layout_tests=$((layout_tests + 1))

# Max width constraints
if grep -q "max-width" "$header_css"; then
    echo -e "${GREEN}✅ Width constraints${NC}"
    layout_passed=$((layout_passed + 1))
else
    echo -e "${RED}❌ Width constraints missing${NC}"
fi
layout_tests=$((layout_tests + 1))

# Component structure check
echo -e "\n${YELLOW}🏗️ COMPONENT STRUCTURE:${NC}"

structure_tests=0
structure_passed=0

# Check JS component structure
js_elements=("header-content" "header-left" "header-center" "header-right")
for element in "${js_elements[@]}"; do
    structure_tests=$((structure_tests + 1))
    if grep -q "\"${element}\"" "$header_js"; then
        echo -e "${GREEN}✅ ${element} component${NC}"
        structure_passed=$((structure_passed + 1))
    else
        echo -e "${RED}❌ ${element} missing${NC}"
    fi
done

# Build test
echo -e "\n${YELLOW}🔨 BUILD VERIFICATION:${NC}"

echo -e "${BLUE}Testing frontend build...${NC}"
cd frontend 2>/dev/null || cd .

build_success=false
if npm run build >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend builds successfully${NC}"
    build_success=true
else
    echo -e "${RED}❌ Frontend build failed${NC}"
fi

cd .. 2>/dev/null || cd .

# Final Results
echo -e "\n${CYAN}================================================${NC}"
echo -e "${CYAN}📊 FINAL RESULTS SUMMARY${NC}"
echo -e "${CYAN}================================================${NC}"

total_tests=$((device_tests + feature_tests + layout_tests + structure_tests + 1))
total_passed=$((device_passed + feature_passed + layout_passed + structure_passed))

if $build_success; then
    total_passed=$((total_passed + 1))
fi

echo -e "\n${PURPLE}📱 Device Support:${NC} ${device_passed}/${device_tests} ($(( (device_passed * 100) / device_tests ))%)"
echo -e "${PURPLE}🔧 iOS Features:${NC} ${feature_passed}/${feature_tests} ($(( (feature_passed * 100) / feature_tests ))%)"
echo -e "${PURPLE}⚖️ Layout Stability:${NC} ${layout_passed}/${layout_tests} ($(( (layout_passed * 100) / layout_tests ))%)"
echo -e "${PURPLE}🏗️ Component Structure:${NC} ${structure_passed}/${structure_tests} ($(( (structure_passed * 100) / structure_tests ))%)"

overall_success=$(( (total_passed * 100) / total_tests ))

echo -e "\n${BLUE}Overall Success Rate: ${CYAN}${overall_success}%${NC} (${total_passed}/${total_tests})"

if [[ $overall_success -ge 90 ]]; then
    echo -e "\n${GREEN}🎉 EXCELLENT! iPhone header is fully optimized${NC}"
    echo -e "${GREEN}✅ Ready for production deployment${NC}"
    exit 0
elif [[ $overall_success -ge 80 ]]; then
    echo -e "\n${YELLOW}👍 GOOD! iPhone header is well optimized${NC}"
    echo -e "${YELLOW}⚠️ Minor improvements recommended${NC}"
    exit 0
elif [[ $overall_success -ge 70 ]]; then
    echo -e "\n${YELLOW}🔧 MODERATE: Header needs some improvements${NC}"
    exit 1
else
    echo -e "\n${RED}❌ CRITICAL: Header needs significant work${NC}"
    exit 1
fi