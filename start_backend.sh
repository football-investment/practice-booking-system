#!/bin/bash
##############################################################################
# 🚀 Backend API Server - Indító Script
##############################################################################

# Színek
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          🚀  Backend API Server Indítása  🚀          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Projekt gyökér
PROJECT_ROOT="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
cd "$PROJECT_ROOT" || exit 1

# 1. PostgreSQL ellenőrzés
echo -e "${YELLOW}🔍 PostgreSQL ellenőrzése...${NC}"
if psql -U postgres -d lfa_intern_system -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL fut és az adatbázis elérhető${NC}"
else
    echo -e "${RED}❌ PostgreSQL nem elérhető!${NC}"
    echo -e "${YELLOW}📝 PostgreSQL indítása...${NC}"
    brew services start postgresql@14
    sleep 3

    if psql -U postgres -d lfa_intern_system -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL most már fut${NC}"
    else
        echo -e "${RED}❌ PostgreSQL hiba! Kérlek indítsd el manuálisan:${NC}"
        echo -e "  ${GREEN}brew services start postgresql@14${NC}"
        exit 1
    fi
fi

# 2. Python környezet aktiválás
echo -e "${YELLOW}🐍 Python környezet aktiválása...${NC}"
source implementation/venv/bin/activate
echo -e "${GREEN}✅ Virtual environment aktiválva${NC}"

# 3. Adatbázis URL beállítása
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
echo -e "${GREEN}✅ DATABASE_URL beállítva${NC}"

# 4. Backend indítása
echo -e "${GREEN}🚀 FastAPI backend indítása...${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🌐 API URL:      http://localhost:8000${NC}"
echo -e "${GREEN}  📚 SwaggerUI:    http://localhost:8000/docs${NC}"
echo -e "${GREEN}  📖 ReDoc:        http://localhost:8000/redoc${NC}"
echo -e "${GREEN}  📋 OpenAPI JSON: http://localhost:8000/openapi.json${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}💡 Használati tippek:${NC}"
echo -e "  • SwaggerUI-ban tesztelheted az összes endpoint-ot"
echo -e "  • Interaktív dashboard: ./start_interactive_testing.sh"
echo -e "  • CTRL+C a kilépéshez"
echo ""
echo -e "${YELLOW}📊 Backend indítása...${NC}"
echo ""

# Uvicorn indítása
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
