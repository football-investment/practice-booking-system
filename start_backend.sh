#!/bin/bash

# 🚀 PRACTICE BOOKING SYSTEM - BACKEND INDÍTÁS
# Egyszerű backend server indítás ellenőrzésekkel

echo "🚀 PRACTICE BOOKING SYSTEM - BACKEND STARTUP"
echo "============================================="

# Színes output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Ellenőrzések
echo ""
echo "🔍 ELŐZETES ELLENŐRZÉSEK"
echo "======================="

# 1. Projekt könyvtár ellenőrzése
if [ ! -f "app/main.py" ]; then
    log_error "Nem vagyunk a practice_booking_system könyvtárban!"
    echo "   Navigálj a projekt root könyvtárába és futtasd újra."
    exit 1
fi
log_success "Projekt könyvtár OK"

# 2. Python ellenőrzés
if ! command -v python3 &> /dev/null; then
    log_error "Python3 nincs telepítve!"
    exit 1
fi
log_success "Python3 telepítve: $(python3 --version)"

# 3. Virtual environment ellenőrzés
if [ ! -d "venv" ]; then
    log_warning "Virtual environment nem található"
    log_info "Létrehozás: python3 -m venv venv"
    
    read -p "Létrehozzam most? (y/n): " create_venv
    if [ "$create_venv" = "y" ]; then
        python3 -m venv venv
        log_success "Virtual environment létrehozva"
    else
        log_error "Virtual environment szükséges a futáshoz"
        exit 1
    fi
fi

# 4. Virtual environment aktiválás
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    log_success "Virtual environment aktiválva"
else
    log_error "Virtual environment aktiválás sikertelen"
    exit 1
fi

# 5. Dependencies ellenőrzés
if ! python -c "import fastapi" &> /dev/null; then
    log_warning "Dependencies hiányoznak"
    log_info "Telepítés: pip install -r requirements.txt"
    
    read -p "Telepítsem most? (y/n): " install_deps
    if [ "$install_deps" = "y" ]; then
        pip install -r requirements.txt
        log_success "Dependencies telepítve"
    else
        log_error "Dependencies szükségesek a futáshoz"
        exit 1
    fi
fi

# 6. Port ellenőrzés
if lsof -i :8000 &> /dev/null; then
    log_warning "Port 8000 már használatban"
    log_info "Leállítom a meglévő folyamatot..."
    
    PID=$(lsof -ti :8000)
    kill -9 $PID 2>/dev/null
    sleep 2
    
    if lsof -i :8000 &> /dev/null; then
        log_error "Nem sikerült felszabadítani a 8000-es portot"
        exit 1
    fi
    log_success "Port felszabadítva"
fi

# 7. Database ellenőrzés
log_info "Database kapcsolat tesztelése..."
if python -c "
from app.database import engine
try:
    with engine.connect() as conn:
        print('Database connection OK')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
" 2>/dev/null; then
    log_success "Database kapcsolat OK"
else
    log_error "Database kapcsolat sikertelen"
    log_info "Ellenőrizd a PostgreSQL státuszát és a .env fájlt"
    exit 1
fi

# SERVER INDÍTÁS
echo ""
echo "🎯 SERVER INDÍTÁS"
echo "================"

log_info "Backend server indítása a http://localhost:8000 címen..."
log_info "API dokumentáció: http://localhost:8000/docs"
log_info ""
log_warning "A server leállításához nyomd meg Ctrl+C"
echo ""

# Indítás verbose móddal
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Ha ide eljutunk, a server leállt
echo ""
log_info "Backend server leállt"