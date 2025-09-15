#!/bin/bash

# 🚀 PRACTICE BOOKING SYSTEM - KOMBINÁLT INDÍTÁS
# Backend és Frontend együttes indítás külön terminálokban

echo "🚀 PRACTICE BOOKING SYSTEM - TELJES INDÍTÁS"
echo "==========================================="

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

# Alapvető ellenőrzések
echo ""
echo "🔍 ALAPVETŐ ELLENŐRZÉSEK"  
echo "======================"

if [ ! -f "app/main.py" ]; then
    log_error "Nem vagyunk a practice_booking_system könyvtárban!"
    exit 1
fi
log_success "Projekt könyvtár OK"

if [ ! -f "start_backend.sh" ]; then
    log_error "start_backend.sh nem található!"
    exit 1
fi
log_success "Backend script OK"

if [ ! -f "start_frontend.sh" ]; then
    log_error "start_frontend.sh nem található!"
    exit 1
fi
log_success "Frontend script OK"

# Executable permissions beállítás
chmod +x start_backend.sh start_frontend.sh
log_success "Script permissions beállítva"

# Port tisztítás
echo ""
echo "🧹 PORT TISZTÍTÁS"
echo "================"

if lsof -i :8000 &> /dev/null; then
    log_info "Port 8000 tisztítása..."
    kill -9 $(lsof -ti :8000) 2>/dev/null
fi

if lsof -i :3000 &> /dev/null; then
    log_info "Port 3000 tisztítása..."
    kill -9 $(lsof -ti :3000) 2>/dev/null
fi

sleep 2
log_success "Portok tisztítva"

# Terminal ellenőrzés (macOS/Linux különbség kezelés)
echo ""
echo "🖥️ TERMINÁL DETECTION"
echo "===================="

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    TERMINAL_CMD="osascript -e 'tell application \"Terminal\" to do script"
    OS_TYPE="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - több terminal emulator support
    if command -v gnome-terminal &> /dev/null; then
        TERMINAL_CMD="gnome-terminal --"
        OS_TYPE="Linux (GNOME)"
    elif command -v xterm &> /dev/null; then
        TERMINAL_CMD="xterm -e"
        OS_TYPE="Linux (xterm)"
    elif command -v konsole &> /dev/null; then
        TERMINAL_CMD="konsole -e"
        OS_TYPE="Linux (KDE)"
    else
        TERMINAL_CMD=""
        OS_TYPE="Linux (unknown terminal)"
    fi
else
    TERMINAL_CMD=""
    OS_TYPE="Unknown OS"
fi

log_info "Detected OS: $OS_TYPE"

# Indítási mód választás
echo ""
echo "🎯 INDÍTÁSI MÓD VÁLASZTÁS"
echo "======================="
echo "1) Automatikus indítás új terminálokban (ajánlott)"
echo "2) Backend indítás ebben a terminálban"
echo "3) Frontend indítás ebben a terminálban"
echo "4) Manual setup instrukciók"
echo ""

read -p "Válaszd ki az opciót (1-4): " choice

case $choice in
    1)
        if [ -n "$TERMINAL_CMD" ]; then
            log_info "Automatikus indítás új terminálokban..."
            
            # Backend indítás új terminálban
            if [[ "$OSTYPE" == "darwin"* ]]; then
                osascript -e "tell application \"Terminal\" to do script \"cd $(pwd) && ./start_backend.sh\""
            else
                $TERMINAL_CMD "bash -c 'cd $(pwd) && ./start_backend.sh; exec bash'" &
            fi
            
            sleep 3
            
            # Frontend indítás új terminálban  
            if [[ "$OSTYPE" == "darwin"* ]]; then
                osascript -e "tell application \"Terminal\" to do script \"cd $(pwd) && ./start_frontend.sh\""
            else
                $TERMINAL_CMD "bash -c 'cd $(pwd) && ./start_frontend.sh; exec bash'" &
            fi
            
            log_success "Backend és Frontend új terminálokban elindítva!"
            
        else
            log_warning "Automatikus terminal indítás nem támogatott ezen a rendszeren"
            log_info "Használd a manual setup opciót (4)"
            exit 1
        fi
        ;;
    
    2)
        log_info "Backend indítása ebben a terminálban..."
        exec ./start_backend.sh
        ;;
        
    3)
        log_info "Frontend indítása ebben a terminálban..."
        exec ./start_frontend.sh
        ;;
        
    4)
        echo ""
        echo "📋 MANUAL SETUP INSTRUKCIÓK"
        echo "=========================="
        echo ""
        echo "TERMINAL 1 (Backend):"
        echo "   ./start_backend.sh"
        echo ""
        echo "TERMINAL 2 (Frontend):"  
        echo "   ./start_frontend.sh"
        echo ""
        echo "URLs elindítás után:"
        echo "   Backend:  http://localhost:8000"
        echo "   Frontend: http://localhost:3000"
        echo "   API Docs: http://localhost:8000/docs"
        echo ""
        echo "🔐 Teszt bejelentkezés:"
        echo "   Email:    admin@company.com"
        echo "   Jelszó:   admin123"
        ;;
        
    *)
        log_error "Érvénytelen választás!"
        exit 1
        ;;
esac

# Információk a futó rendszerről
if [ "$choice" = "1" ]; then
    echo ""
    echo "ℹ️ FONTOS INFORMÁCIÓK"
    echo "===================="
    echo ""
    echo "📊 Rendszer állapot ellenőrzés (5 másodperc múlva):"
    echo "   Backend: http://localhost:8000/health"
    echo "   Frontend: http://localhost:3000"
    echo ""
    echo "🔧 Ha valamelyik nem indul el:"
    echo "   1. Ellenőrizd a terminal ablakokat hibaüzenetekért"
    echo "   2. Futtasd külön: ./start_backend.sh majd ./start_frontend.sh"
    echo "   3. Ellenőrizd a requirements.txt és package.json dependencies-eket"
    echo ""
    
    # Várakozás a szolgáltatások elindulására
    sleep 5
    
    echo "🔍 ÁLLAPOT ELLENŐRZÉS"
    echo "==================="
    
    # Backend ellenőrzés
    if curl -s http://localhost:8000/health &> /dev/null; then
        log_success "Backend működik: http://localhost:8000"
    else
        log_warning "Backend még nem elérhető"
    fi
    
    # Frontend ellenőrzés
    if curl -s http://localhost:3000 &> /dev/null; then
        log_success "Frontend működik: http://localhost:3000"
    else
        log_warning "Frontend még nem elérhető (indulási idő: ~30s)"
    fi
    
    echo ""
    echo "🎉 RENDSZER INDÍTÁS BEFEJEZVE"
    echo "============================"
    log_success "Mindkét szolgáltatás elindításra került!"
    log_info "Nyisd meg a böngészőben: http://localhost:3000"
    
fi