#!/bin/bash

# iOS Header Diagnosis and Testing Script
# Comprehensive testing for iPhone header appearance issues

echo "📱 iOS Header Diagnosis - Comprehensive Testing"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Analyzing iPhone Header Structure...${NC}"

# Check current header CSS structure
echo -e "\n${YELLOW}1. Header CSS Structure Analysis:${NC}"
echo "=================================="

if [[ -f "frontend/src/components/common/AppHeader.css" ]]; then
    echo -e "${GREEN}✅ AppHeader.css found${NC}"
    
    # Check basic header structure
    if grep -q ".app-header" frontend/src/components/common/AppHeader.css; then
        echo -e "${GREEN}✅ Basic header structure present${NC}"
    else
        echo -e "${RED}❌ Basic header structure missing${NC}"
    fi
    
    # Check responsive breakpoints
    echo -e "\n${BLUE}📱 Responsive Breakpoints:${NC}"
    breakpoints=(375 390 428 480 768 1024)
    for bp in "${breakpoints[@]}"; do
        if grep -q "max-width.*${bp}px" frontend/src/components/common/AppHeader.css; then
            echo -e "${GREEN}✅ ${bp}px breakpoint found${NC}"
        else
            echo -e "${RED}❌ ${bp}px breakpoint missing${NC}"
        fi
    done
    
    # Check header layout components
    echo -e "\n${BLUE}🏗️ Header Components:${NC}"
    components=("header-content" "header-left" "header-center" "header-right" "app-logo" "user-info" "theme-controls")
    for component in "${components[@]}"; do
        if grep -q "\.${component}" frontend/src/components/common/AppHeader.css; then
            echo -e "${GREEN}✅ .${component} styled${NC}"
        else
            echo -e "${RED}❌ .${component} missing${NC}"
        fi
    done
    
else
    echo -e "${RED}❌ AppHeader.css not found${NC}"
fi

# Check JavaScript structure
echo -e "\n${YELLOW}2. Header JavaScript Analysis:${NC}"
echo "==============================="

if [[ -f "frontend/src/components/common/AppHeader.js" ]]; then
    echo -e "${GREEN}✅ AppHeader.js found${NC}"
    
    # Check component structure
    js_elements=("header-content" "header-left" "header-center" "header-right" "app-logo" "user-info" "theme-controls")
    for element in "${js_elements[@]}"; do
        if grep -q "\"${element}\"" frontend/src/components/common/AppHeader.js; then
            echo -e "${GREEN}✅ ${element} className present${NC}"
        else
            echo -e "${RED}❌ ${element} className missing${NC}"
        fi
    done
    
else
    echo -e "${RED}❌ AppHeader.js not found${NC}"
fi

# Check iOS optimizations
echo -e "\n${YELLOW}3. iOS Optimization Analysis:${NC}"
echo "============================="

if [[ -f "frontend/src/styles/ios-responsive.css" ]]; then
    echo -e "${GREEN}✅ iOS responsive CSS found${NC}"
    
    # Check iPhone-specific header optimizations
    if grep -q "app-header.*iPhone" frontend/src/styles/ios-responsive.css; then
        echo -e "${GREEN}✅ iPhone-specific header optimizations present${NC}"
    else
        echo -e "${YELLOW}⚠️ iPhone-specific header optimizations may need improvement${NC}"
    fi
    
    # Check safe area implementation
    if grep -q "safe-area" frontend/src/styles/ios-responsive.css; then
        echo -e "${GREEN}✅ Safe area support implemented${NC}"
    else
        echo -e "${RED}❌ Safe area support missing${NC}"
    fi
    
else
    echo -e "${RED}❌ iOS responsive CSS not found${NC}"
fi

# Detailed CSS analysis
echo -e "\n${YELLOW}4. Detailed CSS Analysis:${NC}"
echo "========================="

# Check for potential layout issues
echo -e "\n${BLUE}🔍 Potential Layout Issues:${NC}"

# Check flexbox issues
if grep -q "display.*flex" frontend/src/components/common/AppHeader.css; then
    echo -e "${GREEN}✅ Flexbox layout used${NC}"
    
    # Check flex properties
    flex_props=("justify-content" "align-items" "flex-wrap" "flex-direction")
    for prop in "${flex_props[@]}"; do
        count=$(grep -c "$prop" frontend/src/components/common/AppHeader.css)
        if [[ $count -gt 0 ]]; then
            echo -e "${GREEN}✅ ${prop}: ${count} instances${NC}"
        else
            echo -e "${YELLOW}⚠️ ${prop}: not used${NC}"
        fi
    done
else
    echo -e "${RED}❌ Flexbox layout not properly implemented${NC}"
fi

# Check overflow issues
if grep -q "overflow" frontend/src/components/common/AppHeader.css; then
    echo -e "${YELLOW}⚠️ Overflow properties detected - check for potential issues${NC}"
else
    echo -e "${GREEN}✅ No overflow issues detected${NC}"
fi

# Check z-index stacking
z_index_count=$(grep -c "z-index" frontend/src/components/common/AppHeader.css)
echo -e "${GREEN}ℹ️ Z-index declarations: ${z_index_count}${NC}"

# Check width constraints
if grep -q "max-width\|min-width\|width" frontend/src/components/common/AppHeader.css; then
    echo -e "${GREEN}✅ Width constraints defined${NC}"
else
    echo -e "${RED}❌ Width constraints missing${NC}"
fi

# iPhone-specific testing simulation
echo -e "\n${YELLOW}5. iPhone Device Simulation Analysis:${NC}"
echo "===================================="

iphone_sizes=(
    "375x667:iPhone SE"
    "390x844:iPhone 12/13/14"
    "428x926:iPhone 12/13/14 Pro Max"
    "414x896:iPhone 11"
    "390x844:iPhone 13 mini"
)

for size_info in "${iphone_sizes[@]}"; do
    IFS=':' read -r size name <<< "$size_info"
    width=$(echo $size | cut -d'x' -f1)
    height=$(echo $size | cut -d'x' -f2)
    
    echo -e "\n${PURPLE}📱 ${name} (${width}x${height}):${NC}"
    
    # Check if specific breakpoint exists
    if grep -q "max-width.*${width}px" frontend/src/components/common/AppHeader.css; then
        echo -e "${GREEN}✅ Specific breakpoint for ${width}px${NC}"
    else
        echo -e "${YELLOW}⚠️ No specific breakpoint for ${width}px${NC}"
    fi
    
    # Check iOS responsive optimizations
    if grep -q "max-width.*${width}px" frontend/src/styles/ios-responsive.css; then
        echo -e "${GREEN}✅ iOS optimization for ${width}px${NC}"
    else
        echo -e "${RED}❌ iOS optimization missing for ${width}px${NC}"
    fi
done

# Common iPhone header issues check
echo -e "\n${YELLOW}6. Common iPhone Header Issues Check:${NC}"
echo "====================================="

issues=(
    "text-overflow:ellipsis:Text overflow handling"
    "white-space:nowrap:Text wrapping prevention"
    "-webkit-text-size-adjust:Font size adjustment"
    "touch-action:Touch optimization"
    "user-select:none:User selection control"
    "-webkit-tap-highlight-color:Tap highlight control"
)

for issue_info in "${issues[@]}"; do
    IFS=':' read -r property value description <<< "$issue_info"
    
    if grep -q "$property" frontend/src/components/common/AppHeader.css || grep -q "$property" frontend/src/styles/ios-responsive.css; then
        echo -e "${GREEN}✅ ${description} (${property})${NC}"
    else
        echo -e "${RED}❌ Missing: ${description} (${property})${NC}"
    fi
done

# Summary and recommendations
echo -e "\n${YELLOW}================================================${NC}"
echo -e "${YELLOW}📋 DIAGNOSIS SUMMARY & RECOMMENDATIONS${NC}"
echo -e "${YELLOW}================================================${NC}"

echo -e "\n${BLUE}🔍 Identified Issues:${NC}"
echo "• Header may not be properly optimized for iPhone sizes"
echo "• Safe area support may need improvement"
echo "• Touch targets may not meet iOS requirements"
echo "• Text overflow handling may be inadequate"

echo -e "\n${BLUE}📝 Recommended Actions:${NC}"
echo "1. Implement iPhone-specific header breakpoints"
echo "2. Add proper safe area padding for notched devices"
echo "3. Ensure 44px minimum touch targets"
echo "4. Add text overflow handling"
echo "5. Implement proper iOS Safari optimizations"

echo -e "\n${GREEN}✅ Diagnosis Complete!${NC}"
echo -e "${BLUE}Next step: Run the header optimization script${NC}"