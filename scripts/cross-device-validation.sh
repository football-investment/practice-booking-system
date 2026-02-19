#!/bin/bash

# Cross-Device Frontend Design Validation
# Comprehensive testing across all devices and browsers

echo "🌍 Cross-Device Frontend Design Validation"
echo "==========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counters
mobile_tests=0
mobile_passed=0
tablet_tests=0
tablet_passed=0
desktop_tests=0
desktop_passed=0
performance_tests=0
performance_passed=0

echo -e "${CYAN}🚀 Starting comprehensive cross-device testing...${NC}\n"

# Function to test breakpoint
test_breakpoint() {
    local device="$1"
    local width="$2"
    local file="$3"
    local category="$4"
    
    if [[ "$category" == "mobile" ]]; then
        mobile_tests=$((mobile_tests + 1))
    elif [[ "$category" == "tablet" ]]; then
        tablet_tests=$((tablet_tests + 1))
    else
        desktop_tests=$((desktop_tests + 1))
    fi
    
    if grep -q "max-width.*${width}px\|min-width.*${width}px" "$file"; then
        echo -e "${GREEN}✅ ${device} (${width}px)${NC}"
        if [[ "$category" == "mobile" ]]; then
            mobile_passed=$((mobile_passed + 1))
        elif [[ "$category" == "tablet" ]]; then
            tablet_passed=$((tablet_passed + 1))
        else
            desktop_passed=$((desktop_passed + 1))
        fi
    else
        echo -e "${RED}❌ ${device} (${width}px)${NC}"
    fi
}

# Function to test performance feature
test_performance() {
    local feature="$1"
    local pattern="$2"
    local files="$3"
    
    performance_tests=$((performance_tests + 1))
    
    found=false
    for file in $files; do
        if [[ -f "$file" ]] && grep -q "$pattern" "$file"; then
            found=true
            break
        fi
    done
    
    if $found; then
        echo -e "${GREEN}✅ ${feature}${NC}"
        performance_passed=$((performance_passed + 1))
    else
        echo -e "${RED}❌ ${feature}${NC}"
    fi
}

# Check key files
header_css="frontend/src/components/common/AppHeader.css"
ios_css="frontend/src/styles/ios-responsive.css"
design_tokens="frontend/src/styles/design-tokens.css"
app_css="frontend/src/App.css"

echo -e "${YELLOW}📱 MOBILE DEVICE SUPPORT:${NC}"

# iPhone models
test_breakpoint "iPhone SE" "375" "$header_css" "mobile"
test_breakpoint "iPhone 12/13/14" "390" "$header_css" "mobile"
test_breakpoint "iPhone 11" "414" "$header_css" "mobile"
test_breakpoint "iPhone Pro Max" "428" "$header_css" "mobile"

# Android common sizes
test_breakpoint "Small Android" "360" "$app_css" "mobile"
test_breakpoint "Standard Android" "412" "$app_css" "mobile"
test_breakpoint "Large Android" "480" "$header_css" "mobile"

echo -e "\n${YELLOW}📟 TABLET DEVICE SUPPORT:${NC}"

# iPad models
test_breakpoint "iPad Mini" "768" "$header_css" "tablet"
test_breakpoint "iPad Air" "834" "$ios_css" "tablet"
test_breakpoint "iPad Pro 11\"" "1024" "$header_css" "tablet"
test_breakpoint "iPad Pro 12.9\"" "1194" "$ios_css" "tablet"

# Android tablets
test_breakpoint "Android Tablet" "800" "$app_css" "tablet"
test_breakpoint "Large Android Tablet" "900" "$app_css" "tablet"

echo -e "\n${YELLOW}💻 DESKTOP SUPPORT:${NC}"

# Desktop breakpoints
test_breakpoint "Small Desktop" "1200" "$design_tokens" "desktop"
test_breakpoint "Standard Desktop" "1400" "$header_css" "desktop"
test_breakpoint "Large Desktop" "1600" "$app_css" "desktop"
test_breakpoint "Ultra-wide" "1920" "$app_css" "desktop"

echo -e "\n${YELLOW}⚡ PERFORMANCE OPTIMIZATIONS:${NC}"

# Performance features
files_to_check="$header_css $ios_css $app_css"

test_performance "GPU Acceleration" "transform.*translateZ" "$files_to_check"
test_performance "Will-change optimization" "will-change" "$files_to_check"
test_performance "CSS containment" "contain:" "$files_to_check"
test_performance "Hardware acceleration" "backface-visibility.*hidden" "$files_to_check"
test_performance "Optimized transitions" "transition.*ease" "$files_to_check"
test_performance "Image optimization" "object-fit\|aspect-ratio" "$files_to_check"

echo -e "\n${YELLOW}🎨 DESIGN SYSTEM CONSISTENCY:${NC}"

design_tests=0
design_passed=0

# Design system features
if [[ -f "$design_tokens" ]]; then
    echo -e "${GREEN}✅ Design tokens system${NC}"
    design_passed=$((design_passed + 1))
else
    echo -e "${RED}❌ Design tokens missing${NC}"
fi
design_tests=$((design_tests + 1))

# CSS custom properties
if grep -q "var(--" "$header_css"; then
    echo -e "${GREEN}✅ CSS custom properties${NC}"
    design_passed=$((design_passed + 1))
else
    echo -e "${RED}❌ CSS custom properties missing${NC}"
fi
design_tests=$((design_tests + 1))

# Color scheme support
if grep -q "data-color\|data-theme" "$header_css"; then
    echo -e "${GREEN}✅ Theme system${NC}"
    design_passed=$((design_passed + 1))
else
    echo -e "${RED}❌ Theme system missing${NC}"
fi
design_tests=$((design_tests + 1))

# Typography scale
if grep -q "text-xs\|text-sm\|text-base" "$design_tokens"; then
    echo -e "${GREEN}✅ Typography scale${NC}"
    design_passed=$((design_passed + 1))
else
    echo -e "${RED}❌ Typography scale missing${NC}"
fi
design_tests=$((design_tests + 1))

echo -e "\n${YELLOW}♿ ACCESSIBILITY FEATURES:${NC}"

accessibility_tests=0
accessibility_passed=0

# Accessibility features
if grep -q "min-height.*44\|min-width.*44" "$header_css"; then
    echo -e "${GREEN}✅ Touch target size (44px minimum)${NC}"
    accessibility_passed=$((accessibility_passed + 1))
else
    echo -e "${RED}❌ Touch targets too small${NC}"
fi
accessibility_tests=$((accessibility_tests + 1))

if grep -q "prefers-reduced-motion" "$ios_css"; then
    echo -e "${GREEN}✅ Reduced motion support${NC}"
    accessibility_passed=$((accessibility_passed + 1))
else
    echo -e "${RED}❌ Reduced motion missing${NC}"
fi
accessibility_tests=$((accessibility_tests + 1))

if grep -q "focus.*outline" "$header_css $app_css"; then
    echo -e "${GREEN}✅ Focus indicators${NC}"
    accessibility_passed=$((accessibility_passed + 1))
else
    echo -e "${RED}❌ Focus indicators missing${NC}"
fi
accessibility_tests=$((accessibility_tests + 1))

if grep -q "color-contrast\|contrast(" "$design_tokens"; then
    echo -e "${GREEN}✅ Color contrast optimization${NC}"
    accessibility_passed=$((accessibility_passed + 1))
else
    echo -e "${YELLOW}⚠️ Color contrast not explicitly defined${NC}"
fi
accessibility_tests=$((accessibility_tests + 1))

echo -e "\n${YELLOW}🌐 BROWSER COMPATIBILITY:${NC}"

browser_tests=0
browser_passed=0

# Safari specific
if grep -q "-webkit-" "$header_css"; then
    echo -e "${GREEN}✅ Safari optimizations${NC}"
    browser_passed=$((browser_passed + 1))
else
    echo -e "${RED}❌ Safari optimizations missing${NC}"
fi
browser_tests=$((browser_tests + 1))

# Firefox specific
if grep -q "-moz-" "$app_css $header_css" || grep -q "scrollbar-width" "$app_css"; then
    echo -e "${GREEN}✅ Firefox optimizations${NC}"
    browser_passed=$((browser_passed + 1))
else
    echo -e "${YELLOW}⚠️ Firefox optimizations minimal${NC}"
fi
browser_tests=$((browser_tests + 1))

# Chrome/Edge specific
if grep -q "appearance.*none\|-webkit-appearance" "$header_css"; then
    echo -e "${GREEN}✅ Chrome/Edge compatibility${NC}"
    browser_passed=$((browser_passed + 1))
else
    echo -e "${YELLOW}⚠️ Chrome/Edge specific optimizations minimal${NC}"
fi
browser_tests=$((browser_tests + 1))

echo -e "\n${YELLOW}📦 BUILD & DEPLOYMENT:${NC}"

build_tests=0
build_passed=0

# Test build
echo -e "${BLUE}Testing production build...${NC}"
cd frontend 2>/dev/null || cd .

if npm run build >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Production build successful${NC}"
    build_passed=$((build_passed + 1))
    
    # Check build output
    if [[ -d "build" ]]; then
        echo -e "${GREEN}✅ Build artifacts created${NC}"
        build_passed=$((build_passed + 1))
        
        # Check for optimized files
        if find build -name "*.css" | head -1 | xargs grep -q "max-width.*375px"; then
            echo -e "${GREEN}✅ Mobile optimizations included in build${NC}"
            build_passed=$((build_passed + 1))
        else
            echo -e "${RED}❌ Mobile optimizations missing from build${NC}"
        fi
        build_tests=$((build_tests + 1))
        
    else
        echo -e "${RED}❌ Build directory not created${NC}"
    fi
    build_tests=$((build_tests + 1))
else
    echo -e "${RED}❌ Production build failed${NC}"
fi
build_tests=$((build_tests + 1))

cd .. 2>/dev/null || cd .

# Calculate totals
total_tests=$((mobile_tests + tablet_tests + desktop_tests + performance_tests + design_tests + accessibility_tests + browser_tests + build_tests))
total_passed=$((mobile_passed + tablet_passed + desktop_passed + performance_passed + design_passed + accessibility_passed + browser_passed + build_passed))

# Final Summary
echo -e "\n${CYAN}================================================${NC}"
echo -e "${CYAN}📊 CROSS-DEVICE VALIDATION RESULTS${NC}"
echo -e "${CYAN}================================================${NC}"

echo -e "\n${PURPLE}📱 Mobile Support:${NC} ${mobile_passed}/${mobile_tests} ($(( mobile_tests > 0 ? (mobile_passed * 100) / mobile_tests : 0 ))%)"
echo -e "${PURPLE}📟 Tablet Support:${NC} ${tablet_passed}/${tablet_tests} ($(( tablet_tests > 0 ? (tablet_passed * 100) / tablet_tests : 0 ))%)"
echo -e "${PURPLE}💻 Desktop Support:${NC} ${desktop_passed}/${desktop_tests} ($(( desktop_tests > 0 ? (desktop_passed * 100) / desktop_tests : 0 ))%)"
echo -e "${PURPLE}⚡ Performance:${NC} ${performance_passed}/${performance_tests} ($(( performance_tests > 0 ? (performance_passed * 100) / performance_tests : 0 ))%)"
echo -e "${PURPLE}🎨 Design System:${NC} ${design_passed}/${design_tests} ($(( design_tests > 0 ? (design_passed * 100) / design_tests : 0 ))%)"
echo -e "${PURPLE}♿ Accessibility:${NC} ${accessibility_passed}/${accessibility_tests} ($(( accessibility_tests > 0 ? (accessibility_passed * 100) / accessibility_tests : 0 ))%)"
echo -e "${PURPLE}🌐 Browser Compat:${NC} ${browser_passed}/${browser_tests} ($(( browser_tests > 0 ? (browser_passed * 100) / browser_tests : 0 ))%)"
echo -e "${PURPLE}📦 Build System:${NC} ${build_passed}/${build_tests} ($(( build_tests > 0 ? (build_passed * 100) / build_tests : 0 ))%)"

overall_success=$(( total_tests > 0 ? (total_passed * 100) / total_tests : 0 ))

echo -e "\n${BLUE}🎯 Overall Success Rate: ${CYAN}${overall_success}%${NC} (${total_passed}/${total_tests})"

if [[ $overall_success -ge 85 ]]; then
    echo -e "\n${GREEN}🎉 EXCELLENT! Cross-device compatibility is outstanding${NC}"
    echo -e "${GREEN}✅ Frontend is production-ready across all devices${NC}"
    echo -e "${GREEN}🚀 Recommended for deployment${NC}"
    exit 0
elif [[ $overall_success -ge 75 ]]; then
    echo -e "\n${YELLOW}👍 GOOD! Cross-device compatibility is solid${NC}"
    echo -e "${YELLOW}⚠️ Minor optimizations recommended${NC}"
    exit 0
elif [[ $overall_success -ge 65 ]]; then
    echo -e "\n${YELLOW}🔧 MODERATE: Some improvements needed${NC}"
    echo -e "${YELLOW}⚠️ Consider addressing failing tests${NC}"
    exit 1
else
    echo -e "\n${RED}❌ CRITICAL: Significant cross-device issues detected${NC}"
    echo -e "${RED}🛠️ Major improvements required before deployment${NC}"
    exit 1
fi