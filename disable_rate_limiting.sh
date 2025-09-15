#!/bin/bash

# 🔧 RATE LIMITING FIX - Development Mode
# Kikapcsolja a rate limiting-et development teszteléshez

echo "🔧 RATE LIMITING FIX - Development Mode"
echo "======================================"

# Színes output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# .env fájl frissítés
log_info "Rate limiting kikapcsolása development módban..."

if [ -f ".env" ]; then
    # Backup
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Rate limiting beállítások frissítése
    sed -i '' 's/ENABLE_RATE_LIMITING=.*/ENABLE_RATE_LIMITING=false/' .env
    sed -i '' 's/LOGIN_RATE_LIMIT_CALLS=.*/LOGIN_RATE_LIMIT_CALLS=1000/' .env
    sed -i '' 's/RATE_LIMIT_CALLS=.*/RATE_LIMIT_CALLS=10000/' .env
    
    # Ha nem léteznek, hozzáadás
    if ! grep -q "ENABLE_RATE_LIMITING" .env; then
        echo "ENABLE_RATE_LIMITING=false" >> .env
    fi
    if ! grep -q "LOGIN_RATE_LIMIT_CALLS" .env; then
        echo "LOGIN_RATE_LIMIT_CALLS=1000" >> .env
    fi
    if ! grep -q "RATE_LIMIT_CALLS" .env; then
        echo "RATE_LIMIT_CALLS=10000" >> .env
    fi
    
    log_success ".env frissítve - rate limiting kikapcsolva"
    
    echo ""
    echo "📋 Frissített beállítások:"
    grep -E "(ENABLE_RATE_LIMITING|LOGIN_RATE_LIMIT_CALLS|RATE_LIMIT_CALLS)" .env
    
else
    echo "❌ .env fájl nem található"
    exit 1
fi

echo ""
echo "🔄 Backend újraindítás szükséges a változások érvényesítéséhez"
echo ""

# Auto restart opció
read -p "Újraindítsam a backend-et most? (y/n): " restart_backend
if [ "$restart_backend" = "y" ]; then
    echo ""
    log_info "Backend újraindítása..."
    
    # Kill current backend
    pkill -f "uvicorn app.main:app"
    sleep 2
    
    # Restart backend
    log_info "Backend indítása új beállításokkal..."
    ./start_backend.sh
fi