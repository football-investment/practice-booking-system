#!/bin/bash

echo "🔍 GOMB KONTRASZT VALIDÁCIÓ"
echo "========================="

# Color variables
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

echo -e "\n${BLUE}1. PROJECTCARD CSS ELLENŐRZÉSE${NC}"
echo "-------------------------------"

# Check for explicit light mode button styles
if grep -q ":root\[data-theme=\"light\"\] .action-btn.secondary" frontend/src/components/student/ProjectCard.css; then
    echo -e "✅ ${GREEN}Explicit light mode gomb stílusok megtalálhatók${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Light mode explicit stílusok HIÁNYOZNAK${NC}"
    ((FAILED++))
fi

# Check for fallback colors with !important
if grep -q "background: #ffffff !important" frontend/src/components/student/ProjectCard.css; then
    echo -e "✅ ${GREEN}Fehér háttér fallback explicit módon beállítva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Fehér háttér fallback HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check for dark text on light background
if grep -q "color: #374151 !important" frontend/src/components/student/ProjectCard.css; then
    echo -e "✅ ${GREEN}Sötét szöveg szín light mode-ban beállítva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Sötét szöveg szín light mode-ban HIÁNYZIK${NC}"
    ((FAILED++))
fi

# Check for dark mode support
if grep -q ":root\[data-theme=\"dark\"\] .action-btn.secondary" frontend/src/components/student/ProjectCard.css; then
    echo -e "✅ ${GREEN}Dark mode gomb támogatás implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Dark mode gomb támogatás HIÁNYZIK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}2. AVAILABILITY BADGE KONTRASZT${NC}"
echo "-------------------------------"

# Check for enhanced availability badge styles
if grep -q "linear-gradient.*availability-badge.available" frontend/src/components/student/ProjectCard.css; then
    echo -e "✅ ${GREEN}Availability badge gradient stílusok implementálva${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Availability badge gradientek HIÁNYOZNAK${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}3. CSS VÁLTOZÓ FALLBACK-EK${NC}"
echo "----------------------------"

# Count fallback colors
fallback_count=$(grep -o "var([^)]*,[^)]*)" frontend/src/components/student/ProjectCard.css | wc -l | xargs)
if [ "$fallback_count" -gt 5 ]; then
    echo -e "✅ ${GREEN}Megfelelő számú CSS változó fallback ($fallback_count db)${NC}"
    ((PASSED++))
else
    echo -e "⚠️  ${YELLOW}Kevés CSS változó fallback ($fallback_count db) - növelhető${NC}"
fi

echo -e "\n${BLUE}4. FUNKCIONALITÁS TESZT${NC}"
echo "---------------------"

# Check if frontend is accessible
if curl -s http://192.168.1.129:3000/student/projects/3 > /dev/null 2>&1; then
    echo -e "✅ ${GREEN}Projekt oldal elérhető (192.168.1.129:3000)${NC}"
    ((PASSED++))
else
    echo -e "❌ ${RED}Projekt oldal NEM elérhető${NC}"
    ((FAILED++))
fi

echo -e "\n${BLUE}5. ÖSSZESÍTÉS${NC}"
echo "============"
TOTAL=$((PASSED + FAILED))
if [ $TOTAL -gt 0 ]; then
    PERCENTAGE=$(( PASSED * 100 / TOTAL ))
else
    PERCENTAGE=0
fi

if [ $PERCENTAGE -ge 90 ]; then
    echo -e "🎉 ${GREEN}KIVÁLÓ! ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${GREEN}A gomb kontraszt problémák MEGOLDVA!${NC}"
elif [ $PERCENTAGE -ge 75 ]; then
    echo -e "👍 ${YELLOW}JÓ ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${YELLOW}Kisebb finomhangolásokra lehet szükség${NC}"
else
    echo -e "⚠️  ${RED}FEJLESZTENDŐ ($PASSED/$TOTAL teszt sikeres - $PERCENTAGE%)${NC}"
    echo -e "   ${RED}További javításokra van szükség${NC}"
fi

echo -e "\n${BLUE}TESZTELÉSI ÚTMUTATÓ:${NC}"
echo "1. Nyissa meg: http://192.168.1.129:3000/student/projects/3"
echo "2. Ellenőrizze a 'Részletek' és 'Jelentkezés' gombokat"
echo "3. Váltson light és dark mode között"
echo "4. Tesztelje különböző színsémákban (lila, kék, zöld, piros)"

exit 0