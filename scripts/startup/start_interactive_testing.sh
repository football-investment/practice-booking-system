#!/bin/bash
##############################################################################
# 🎮 Interaktív Backend Tesztelő Dashboard - Indító Script
##############################################################################

# Színek
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🎮  Interaktív Backend Tesztelő Dashboard  🎮     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Projekt gyökér
PROJECT_ROOT="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
cd "$PROJECT_ROOT" || exit 1

# 1. Ellenőrizzük hogy a backend fut-e
echo -e "${YELLOW}🔍 Backend ellenőrzése...${NC}"
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend fut a http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Backend nem fut!${NC}"
    echo -e "${YELLOW}📝 Backend indítása...${NC}"
    echo ""
    echo -e "${BLUE}Új terminál ablakban futtasd:${NC}"
    echo -e "  ${GREEN}cd \"$PROJECT_ROOT\"${NC}"
    echo -e "  ${GREEN}export DATABASE_URL=\"postgresql://postgres:postgres@localhost:5432/lfa_intern_system\"${NC}"
    echo -e "  ${GREEN}source implementation/venv/bin/activate${NC}"
    echo -e "  ${GREEN}uvicorn app.main:app --reload --host 0.0.0.0 --port 8000${NC}"
    echo ""
    read -p "Nyomd meg az ENTER-t ha a backend már fut..."
fi

# 2. Aktiváljuk a Python környezetet
echo -e "${YELLOW}🐍 Python környezet aktiválása...${NC}"
source implementation/venv/bin/activate

# 3. Ellenőrizzük hogy Streamlit telepítve van-e
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}❌ Streamlit nincs telepítve!${NC}"
    echo -e "${YELLOW}📦 Telepítés...${NC}"
    pip install streamlit pandas plotly requests
fi

# 4. Indítsuk a Streamlit dashboard-ot
echo -e "${GREEN}🚀 Streamlit Dashboard indítása...${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Dashboard URL: http://localhost:8501${NC}"
echo -e "${GREEN}  Backend URL:   http://localhost:8000${NC}"
echo -e "${GREEN}  SwaggerUI URL: http://localhost:8000/docs${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}💡 Használati tippek:${NC}"
echo -e "  • Jelentkezz be a bal oldali menüben"
echo -e "  • Használd a Gyors tesztek tab-ot egyszerű műveletekhez"
echo -e "  • API Explorer tab-ban bármilyen endpoint-ot kipróbálhatsz"
echo -e "  • CTRL+C a kilépéshez"
echo ""

# Indítsuk a Streamlit-et
streamlit run interactive_testing_dashboard.py
