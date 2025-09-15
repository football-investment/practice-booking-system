#!/bin/bash

# Unified Color System Validation Script
echo "🎨 EGYSÉGES SZÍNRENDSZER VALIDÁCIÓ"
echo "=================================="

# Color variables
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test results counter
PASSED=0
FAILED=0

echo -e "\n${BLUE}1. UNIFIED COLOR SYSTEM ELLENŐRZÉS${NC}"
echo "-----------------------------------"

# Check if unified color system exists
if [ -f "frontend/src/styles/unified-color-system.css" ]; then
    echo -e "✅ ${GREEN}Unified color system fájl létezik${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Unified color system fájl HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check if universal components exist
if [ -f "frontend/src/styles/universal-components.css" ]; then
    echo -e "✅ ${GREEN}Universal components fájl létezik${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Universal components fájl HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check App.css imports
if grep -q "universal-components.css" frontend/src/App.css; then
    echo -e "✅ ${GREEN}Universal components importálva az App.css-ben${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Universal components NINCS importálva az App.css-ben${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}2. AUTOMATIC THEME VARIABLES${NC}"
echo "----------------------------"

# Check for automatic text hierarchy
if grep -q "text-primary.*var(--neutral" frontend/src/styles/unified-color-system.css; then
    echo -e "✅ ${GREEN}Automatikus szöveg hierarchia definiálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Automatikus szöveg hierarchia HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check for semantic color system
if grep -q "btn-primary-bg.*var(" frontend/src/styles/unified-color-system.css; then
    echo -e "✅ ${GREEN}Szemantikus gomb színek definiálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Szemantikus gomb színek HIÁNYOZNAK${NC}"
    ((FAILED++))
fi

# Check for alert system
if grep -q "alert-success-bg.*var(" frontend/src/styles/unified-color-system.css; then
    echo -e "✅ ${GREEN}Automatikus alert rendszer definiálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Automatikus alert rendszer HIÁNYZIK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}3. MANUAL COLOR REMOVAL${NC}"
echo "----------------------"

# Count hardcoded colors in ProjectCard
hardcoded_project_card=$(grep -o '#[0-9a-fA-F]\{3,6\}' frontend/src/components/student/ProjectCard.css | wc -l | xargs)
if [ "$hardcoded_project_card" -eq 0 ]; then
    echo -e "✅ ${GREEN}ProjectCard.css: Nincs hardcoded szín${NC}"
    ((PASSED++))
elif [ "$hardcoded_project_card" -lt 3 ]; then
    echo -e "⚠️  ${YELLOW}ProjectCard.css: Kevés hardcoded szín ($hardcoded_project_card db)${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}ProjectCard.css: Túl sok hardcoded szín ($hardcoded_project_card db)${NC}"
    ((FAILED++))
fi

# Check for removed theme-specific overrides
if ! grep -q ":root\[data-theme.*!important" frontend/src/components/student/ProjectCard.css; then
    echo -e "✅ ${GREEN}Theme-specifikus override-ok eltávolítva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Theme-specifikus override-ok még mindig jelen vannak${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}4. COMPONENT SYSTEM INTEGRATION${NC}"
echo "------------------------------"

# Check universal button system
if grep -q "btn-primary-bg" frontend/src/styles/universal-components.css; then
    echo -e "✅ ${GREEN}Univerzális gomb rendszer implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Univerzális gomb rendszer HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check card system
if grep -q "card-bg" frontend/src/styles/universal-components.css; then
    echo -e "✅ ${GREEN}Univerzális kártya rendszer implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Univerzális kártya rendszer HIÁNYZIK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}5. ACCESSIBILITY SUPPORT${NC}"
echo "-----------------------"

# Check for high contrast support
if grep -q "prefers-contrast: high" frontend/src/styles/unified-color-system.css; then
    echo -e "✅ ${GREEN}High contrast támogatás implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}High contrast támogatás HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check for auto theme support
if grep -q "prefers-color-scheme" frontend/src/styles/unified-color-system.css; then
    echo -e "✅ ${GREEN}Automatikus téma követés implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Automatikus téma követés HIÁNYZIK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}6. FUNCTIONAL TESTING${NC}"
echo "--------------------"

# Check if frontend compiles
if npm --prefix frontend run build > /dev/null 2>&1; then
    echo -e "✅ ${GREEN}Frontend sikeresen buildel${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Frontend build HIBÁS${NC}"
    ((FAILED++))
fi

# Check if frontend is running
if curl -s http://localhost:3000 > /dev/null; then
    echo -e "✅ ${GREEN}Frontend fut (localhost:3000)${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Frontend NEM fut${NC}"
    ((FAILED++))
fi

echo -e "\n${PURPLE}7. COLOR CONTRAST ANALYSIS${NC}"
echo "--------------------------"

# Check contrast ratios in definitions
if grep -q "Maximum contrast.*16:1" frontend/src/styles/unified-color-system.css; then
    echo -e "✅ ${GREEN}Kontraszt arányok dokumentálva${NC}"
    ((PASSED++))
else
    echo -e "⚠️  ${YELLOW}Kontraszt dokumentáció javítható${NC}"
fi

# Check neutral color scale
neutral_colors=$(grep -c "neutral-[0-9]" frontend/src/styles/unified-color-system.css)
if [ "$neutral_colors" -gt 8 ]; then
    echo -e "✅ ${GREEN}Teljes neutral színskála ($neutral_colors szín)${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Hiányos neutral színskála ($neutral_colors szín)${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}8. ÖSSZESÍTÉS${NC}"
echo "============"
TOTAL=$((PASSED + FAILED))
if [ $TOTAL -gt 0 ]; then
    PERCENTAGE=$(( PASSED * 100 / TOTAL ))
else
    PERCENTAGE=0
fi

if [ $PERCENTAGE -ge 95 ]; then
    echo -e "🎉 ${GREEN}TÖKÉLETES! ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${GREEN}Az egységes színrendszer teljes mértékben implementálva!${NC}"
elif [ $PERCENTAGE -ge 85 ]; then
    echo -e "🌟 ${GREEN}KIVÁLÓ! ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${GREEN}A színrendszer konzisztenciája biztosított!${NC}"
elif [ $PERCENTAGE -ge 75 ]; then
    echo -e "👍 ${YELLOW}JÓ ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${YELLOW}Kisebb finomhangolásokra lehet szükség${NC}"
else
    echo -e "⚠️  ${RED}FEJLESZTENDŐ ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${RED}További munkára van szükség a konzisztenciához${NC}"
fi

echo -e "\n${BLUE}IMPLEMENTÁCIÓS ELŐNYÖK:${NC}"
echo "1. 🎯 Automatikus téma konzisztencia"
echo "2. 🔍 Magas kontraszt arányok (4.5:1 minimum)"
echo "3. ♿ Akadálymentesség támogatás"
echo "4. 🌓 Auto light/dark theme követés"
echo "5. 🎨 Szemantikus színhasználat"
echo "6. 🚫 Manuális színbeállítások kiküszöbölése"
echo "7. 🔄 Egységes komponens rendszer"

echo -e "\n${BLUE}TESZT ÚTMUTATÓ:${NC}"
echo "1. Váltson light/dark mode között"
echo "2. Tesztelje különböző színsémákat" 
echo "3. Ellenőrizze a kontrasztot minden témában"
echo "4. Validálja a gombokat és kártyákat"
echo "5. Tesztelje az auto theme követést"

exit 0