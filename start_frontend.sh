#!/bin/bash

# 🎨 PRACTICE BOOKING SYSTEM - FRONTEND INDÍTÁS  
# Egyszerű React frontend indítás ellenőrzésekkel

echo "🎨 PRACTICE BOOKING SYSTEM - FRONTEND STARTUP"
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
if [ ! -d "frontend" ]; then
    log_error "Frontend könyvtár nem található!"
    echo "   Futtasd ezt a scriptet a practice_booking_system root könyvtárából."
    exit 1
fi
log_success "Frontend könyvtár OK"

# 2. Node.js ellenőrzés
if ! command -v node &> /dev/null; then
    log_error "Node.js nincs telepítve!"
    log_info "Telepítsd a Node.js-t: https://nodejs.org"
    exit 1
fi
log_success "Node.js telepítve: $(node --version)"

# 3. npm ellenőrzés
if ! command -v npm &> /dev/null; then
    log_error "npm nincs telepítve!"
    exit 1
fi
log_success "npm telepítve: $(npm --version)"

# 4. Frontend könyvtárba váltás
cd frontend
log_success "Frontend könyvtárba váltás"

# 5. package.json ellenőrzés
if [ ! -f "package.json" ]; then
    log_error "package.json nem található!"
    log_info "Futtasd előbb a frontend_setup.sh scriptet"
    exit 1
fi
log_success "package.json OK"

# 6. Dependencies ellenőrzés
if [ ! -d "node_modules" ]; then
    log_warning "node_modules könyvtár hiányzik"
    log_info "Dependencies telepítése..."
    
    npm install
    
    if [ $? -eq 0 ]; then
        log_success "Dependencies telepítve"
    else
        log_error "Dependencies telepítése sikertelen"
        exit 1
    fi
else
    log_success "node_modules OK"
fi

# 7. Port ellenőrzés  
if lsof -i :3000 &> /dev/null; then
    log_warning "Port 3000 már használatban"
    log_info "Leállítom a meglévő folyamatot..."
    
    PID=$(lsof -ti :3000)
    kill -9 $PID 2>/dev/null
    sleep 2
    
    if lsof -i :3000 &> /dev/null; then
        log_error "Nem sikerült felszabadítani a 3000-es portot"
        exit 1
    fi
    log_success "Port felszabadítva"
fi

# 8. Backend kapcsolat ellenőrzés
log_info "Backend elérhetőség tesztelése..."
if curl -s http://localhost:8000/health &> /dev/null; then
    log_success "Backend elérhető a localhost:8000-n"
else
    log_warning "Backend nem elérhető!"
    log_info "Ellenőrizd, hogy fut-e a backend server (localhost:8000)"
    log_info "Ha nem fut, indítsd el külön terminálban: ./start_backend.sh"
    echo ""
    read -p "Folytatod a frontend indítását backend nélkül? (y/n): " continue_anyway
    if [ "$continue_anyway" != "y" ]; then
        exit 1
    fi
fi

# 9. React app compilation teszt
log_info "React app szintaxis ellenőrzés..."
if npm run build --silent &> /dev/null; then
    log_success "React app fordul"
    rm -rf build  # Cleanup
else
    log_error "React app compilation errors"
    log_info "Futtasd: npm run build a részletes hibákért"
    exit 1
fi

# FRONTEND INDÍTÁS
echo ""
echo "🎯 FRONTEND INDÍTÁS"
echo "=================="

log_info "React development server indítása..."
log_info "Frontend URL: http://localhost:3000"
log_info "Backend proxy: http://localhost:8000"
log_info ""
log_info "🔐 TESZT BEJELENTKEZÉS:"
log_info "Email:    admin@company.com"
log_info "Jelszó:   admin123"
log_info ""
log_warning "A frontend leállításához nyomd meg Ctrl+C"
echo ""

# React dev server indítás
npm start

# Ha ide eljutunk, a server leállt
echo ""
log_info "Frontend server leállt"