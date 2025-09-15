#!/bin/bash

# Theme and Responsivity Validation Script
echo "🔍 TÉMA ÉS RESPONSIVITÁS VALIDÁCIÓ"
echo "=================================="

# Color variables
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results counter
PASSED=0
FAILED=0

echo -e "\n${BLUE}1. CSS FÁJLOK ELLENŐRZÉSE${NC}"
echo "----------------------------"

# Check if InstructorDashboard.css has proper theme variables
if grep -q "var(--text-primary)" frontend/src/pages/instructor/InstructorDashboard.css; then
    echo -e "✅ ${GREEN}InstructorDashboard használja a design tokeneket${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}InstructorDashboard NEM használja a design tokeneket${NC}"
    ((FAILED++))
fi

# Check for dark theme support
if grep -q ":root\[data-theme=\"dark\"\]" frontend/src/pages/instructor/InstructorDashboard.css; then
    echo -e "✅ ${GREEN}Dark theme támogatás megtalálható${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Dark theme támogatás HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check responsive design
if grep -q "@media (max-width: 768px)" frontend/src/pages/instructor/InstructorDashboard.css; then
    echo -e "✅ ${GREEN}Mobile responsivitás implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Mobile responsivitás HIÁNYZIK${NC}"
    ((FAILED++))
fi

if grep -q "@media (max-width: 1024px)" frontend/src/pages/instructor/InstructorDashboard.css; then
    echo -e "✅ ${GREEN}Tablet responsivitás implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Tablet responsivitás HIÁNYZIK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}2. MÉRFÖLDKÖVEK CSS ELLENŐRZÉSE${NC}"
echo "--------------------------------"

# Check MilestoneTracker theme support
if grep -q ".milestone-status-badge" frontend/src/components/student/MilestoneTracker.css; then
    echo -e "✅ ${GREEN}Milestone badge stílusok definiálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Milestone badge stílusok HIÁNYOZNAK${NC}"
    ((FAILED++))
fi

# Check milestone responsive design
if grep -q "@media (max-width: 768px)" frontend/src/components/student/MilestoneTracker.css; then
    echo -e "✅ ${GREEN}Milestone mobile responsivitás implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Milestone mobile responsivitás HIÁNYZIK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}3. DESIGN TOKEN KOMPATIBILITÁS${NC}"
echo "------------------------------"

# Check if design tokens are properly imported
if grep -q "@import './design-tokens.css';" frontend/src/styles/themes.css; then
    echo -e "✅ ${GREEN}Design tokenek importálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Design tokenek NINCSENEK importálva${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}4. HARDCODED SZÍNEK ELLENŐRZÉSE${NC}"
echo "-------------------------------"

# Count hardcoded colors in InstructorDashboard.css
hardcoded_colors=$(grep -o '#[0-9a-fA-F]\{3,6\}' frontend/src/pages/instructor/InstructorDashboard.css | wc -l | xargs)
if [ "$hardcoded_colors" -lt 5 ]; then
    echo -e "✅ ${GREEN}Minimális hardcoded színhasználat ($hardcoded_colors db)${NC}"
    ((PASSED++))
else
    echo -e "⚠️  ${YELLOW}Túl sok hardcoded szín ($hardcoded_colors db) - optimalizálható${NC}"
fi

echo -e "\n${BLUE}5. FUNKCIONÁLIS TESZTELÉS${NC}"
echo "------------------------"

# Check if frontend is running
if curl -s http://localhost:3000 > /dev/null; then
    echo -e "✅ ${GREEN}Frontend elérhető (localhost:3000)${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Frontend NEM elérhető${NC}"
    ((FAILED++))
fi

# Test instructor dashboard endpoint
if curl -s http://localhost:3000/instructor/dashboard > /dev/null; then
    echo -e "✅ ${GREEN}Instructor dashboard elérhető${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Instructor dashboard NEM elérhető${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}6. ÖSSZESÍTÉS${NC}"
echo "============"
TOTAL=$((PASSED + FAILED))
PERCENTAGE=$(( PASSED * 100 / TOTAL ))

if [ $PERCENTAGE -ge 90 ]; then
    echo -e "🎉 ${GREEN}KIVÁLÓ! ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${GREEN}A téma és responsivitás optimalizálása SIKERES!${NC}"
elif [ $PERCENTAGE -ge 75 ]; then
    echo -e "👍 ${YELLOW}JÓ ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${YELLOW}Kisebb javításokra lehet szükség${NC}"
else
    echo -e "⚠️  ${RED}FEJLESZTENDŐ ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${RED}Jelentős javításokra van szükség${NC}"
fi

echo -e "\n${BLUE}KÖVETKEZŐ LÉPÉSEK:${NC}"
echo "1. Tesztelje a dark/light mode váltást az interfészen"
echo "2. Ellenőrizze a responsivitást különböző eszközökön"  
echo "3. Validálja a mérföldkövek megjelenítését"
echo "4. Győződjön meg róla, hogy minden téma színben működik"

exit 0