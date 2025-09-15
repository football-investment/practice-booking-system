#!/bin/bash

# 🔧 POSTGRESQL DEBUG & FIX - macOS Homebrew Issues
# Javítja a tipikus PostgreSQL service indítási problémákat

echo "🔧 POSTGRESQL DEBUG & FIX - macOS"
echo "================================="
echo "PostgreSQL service problémák diagnosztizálása és javítása"
echo ""

# Színes output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
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

log_debug() {
    echo -e "${PURPLE}🔍 $1${NC}"
}

# PHASE 1: DIAGNÓZIS
echo "🔍 PHASE 1: POSTGRESQL DIAGNÓZIS"
echo "==============================="

log_debug "PostgreSQL telepítés ellenőrzése..."
if brew list | grep -q postgresql; then
    PG_VERSION=$(brew list | grep postgresql | head -1)
    log_success "PostgreSQL telepítve: $PG_VERSION"
else
    log_error "PostgreSQL nincs telepítve Homebrew-val"
    exit 1
fi

log_debug "PostgreSQL binárisok ellenőrzése..."
PG_PATH=$(brew --prefix postgresql@14)/bin
if [ -f "$PG_PATH/postgres" ]; then
    log_success "PostgreSQL binárisok: $PG_PATH"
    export PATH="$PG_PATH:$PATH"
else
    log_error "PostgreSQL binárisok nem találhatóak"
fi

log_debug "PostgreSQL process ellenőrzése..."
PG_PROCESSES=$(ps aux | grep postgres | grep -v grep | wc -l | xargs)
if [ "$PG_PROCESSES" -gt 0 ]; then
    log_warning "PostgreSQL processek futnak: $PG_PROCESSES db"
    ps aux | grep postgres | grep -v grep
else
    log_info "Nincs futó PostgreSQL process"
fi

log_debug "PostgreSQL port ellenőrzése..."
if lsof -i :5432 &> /dev/null; then
    log_warning "Port 5432 foglalt:"
    lsof -i :5432
else
    log_info "Port 5432 szabad"
fi

# PHASE 2: SERVICE CLEANUP
echo ""
echo "🧹 PHASE 2: SERVICE CLEANUP"
echo "==========================="

log_info "Meglévő PostgreSQL servicek leállítása..."

# Homebrew service stop
brew services stop postgresql@14 &> /dev/null
brew services stop postgresql &> /dev/null

# Manuel leállítás ha szükséges
if [ "$PG_PROCESSES" -gt 0 ]; then
    log_info "PostgreSQL processek manual leállítása..."
    sudo pkill -f postgres &> /dev/null
    sleep 2
fi

# Port felszabadítás
if lsof -i :5432 &> /dev/null; then
    log_info "Port 5432 felszabadítása..."
    sudo lsof -ti:5432 | xargs sudo kill -9 &> /dev/null
    sleep 1
fi

log_success "Service cleanup befejezve"

# PHASE 3: DATA DIRECTORY CHECK
echo ""
echo "📁 PHASE 3: DATA DIRECTORY ELLENŐRZÉS"
echo "===================================="

PG_DATA_DIR=$(brew --prefix)/var/postgresql@14
log_debug "Data directory: $PG_DATA_DIR"

if [ -d "$PG_DATA_DIR" ]; then
    log_success "PostgreSQL data directory létezik"
    
    # Permissions ellenőrzés
    OWNER=$(ls -ld "$PG_DATA_DIR" | awk '{print $3}')
    CURRENT_USER=$(whoami)
    
    if [ "$OWNER" = "$CURRENT_USER" ]; then
        log_success "Data directory ownership OK ($OWNER)"
    else
        log_warning "Data directory owner: $OWNER (aktuális user: $CURRENT_USER)"
        log_info "Ownership javítása..."
        sudo chown -R $CURRENT_USER "$PG_DATA_DIR"
    fi
    
else
    log_warning "PostgreSQL data directory nem található"
    log_info "Database cluster inicializálása..."
    
    mkdir -p "$PG_DATA_DIR"
    initdb --locale=C -E UTF-8 "$PG_DATA_DIR"
    
    if [ $? -eq 0 ]; then
        log_success "Database cluster inicializálva"
    else
        log_error "Database cluster inicializálás sikertelen"
        exit 1
    fi
fi

# PHASE 4: CONFIGURATION FIX
echo ""
echo "⚙️ PHASE 4: POSTGRESQL KONFIGURÁCIÓS JAVÍTÁSOK"
echo "=============================================="

PG_CONF="$PG_DATA_DIR/postgresql.conf"
PG_HBA="$PG_DATA_DIR/pg_hba.conf"

if [ -f "$PG_CONF" ]; then
    log_debug "PostgreSQL konfiguráció javítása..."
    
    # Backup original configs
    cp "$PG_CONF" "$PG_CONF.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$PG_HBA" "$PG_HBA.backup.$(date +%Y%m%d_%H%M%S)"
    
    # PostgreSQL.conf módosítások
    sed -i '' "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "$PG_CONF"
    sed -i '' "s/#port = 5432/port = 5432/" "$PG_CONF"
    sed -i '' "s/#max_connections = 100/max_connections = 100/" "$PG_CONF"
    
    log_success "postgresql.conf frissítve"
    
    # pg_hba.conf módosítások (permissive local access)
    if ! grep -q "local.*all.*all.*trust" "$PG_HBA"; then
        sed -i '' '1i\
# Local connections for development\
local   all             all                                     trust\
host    all             all             127.0.0.1/32            trust\
host    all             all             ::1/128                 trust\
' "$PG_HBA"
        log_success "pg_hba.conf frissítve (trust authentication)"
    fi
else
    log_error "postgresql.conf nem található"
fi

# PHASE 5: MANUAL SERVER START
echo ""
echo "🚀 PHASE 5: POSTGRESQL SERVER INDÍTÁS"
echo "===================================="

log_info "PostgreSQL server manual indítása..."

# Manual postgres indítás a háttérben
nohup postgres -D "$PG_DATA_DIR" > "$PG_DATA_DIR/server.log" 2>&1 &
PG_PID=$!

log_info "PostgreSQL indítás folyamatban (PID: $PG_PID)..."

# Várakozás a server indulására
for i in {1..15}; do
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        log_success "PostgreSQL server fut!"
        break
    fi
    
    if [ $i -eq 15 ]; then
        log_error "PostgreSQL nem indult el 15 másodperc alatt"
        log_info "Server log:"
        tail -20 "$PG_DATA_DIR/server.log"
        exit 1
    fi
    
    sleep 1
done

# PHASE 6: DATABASE SETUP
echo ""
echo "🗄️ PHASE 6: DATABASE LÉTREHOZÁS"  
echo "============================="

log_info "User és database létrehozása..."

# Postgres superuser létrehozás ha szükséges
CURRENT_USER=$(whoami)
if ! psql -h localhost -U $CURRENT_USER -c '\q' &> /dev/null; then
    log_info "PostgreSQL user létrehozása: $CURRENT_USER"
    createuser -h localhost -s $CURRENT_USER &> /dev/null
    
    if [ $? -eq 0 ]; then
        log_success "User létrehozva: $CURRENT_USER"
    else
        log_warning "User létrehozás problémás"
    fi
fi

# Database létrehozás
if psql -h localhost -U $CURRENT_USER -lqt | cut -d \| -f 1 | grep -qw practice_booking_system; then
    log_success "practice_booking_system database már létezik"
else
    log_info "practice_booking_system database létrehozása..."
    createdb -h localhost -U $CURRENT_USER practice_booking_system
    
    if [ $? -eq 0 ]; then
        log_success "practice_booking_system database létrehozva"
    else
        log_error "Database létrehozás sikertelen"
        exit 1
    fi
fi

# Connection teszt
log_info "Database kapcsolat tesztelése..."
if psql -h localhost -U $CURRENT_USER -d practice_booking_system -c 'SELECT version();' &> /dev/null; then
    log_success "Database kapcsolat működik"
    
    # Version info
    PG_VERSION=$(psql -h localhost -U $CURRENT_USER -d practice_booking_system -t -c 'SELECT version();' 2>/dev/null | head -1)
    log_info "PostgreSQL: $PG_VERSION"
else
    log_error "Database kapcsolat teszt sikertelen"
    exit 1
fi

# PHASE 7: .ENV CONFIGURATION
echo ""
echo "⚙️ PHASE 7: .ENV KONFIGURÁCIÓS FÁJL"
echo "=================================="

ENV_FILE=".env"
DATABASE_URL="postgresql://$CURRENT_USER@localhost:5432/practice_booking_system"

log_info ".env fájl beállítása..."

if [ -f "$ENV_FILE" ]; then
    # Backup existing .env
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update DATABASE_URL
    if grep -q "DATABASE_URL=" "$ENV_FILE"; then
        sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" "$ENV_FILE"
        log_success ".env DATABASE_URL frissítve"
    else
        echo "DATABASE_URL=$DATABASE_URL" >> "$ENV_FILE"
        log_success ".env DATABASE_URL hozzáadva"
    fi
else
    # Create new .env
    cat > "$ENV_FILE" << EOF
# DATABASE CONFIGURATION - PostgreSQL Fix
DATABASE_URL=$DATABASE_URL

# JWT SECURITY
SECRET_KEY=development-secret-key-change-in-production-123456789
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# APPLICATION SETTINGS
APP_NAME="Practice Booking System"
DEBUG=true
API_V1_STR=/api/v1
ENVIRONMENT=development

# ADMIN USER
ADMIN_EMAIL=admin@company.com
ADMIN_PASSWORD=admin123
ADMIN_NAME=System Administrator

# BUSINESS RULES
MAX_BOOKINGS_PER_SEMESTER=10
BOOKING_DEADLINE_HOURS=24

# DEVELOPMENT SETTINGS
TESTING=false
ENABLE_RATE_LIMITING=false
ENABLE_SECURITY_HEADERS=true
ENABLE_REQUEST_SIZE_LIMIT=false
ENABLE_STRUCTURED_LOGGING=true

# PERMISSIVE RATE LIMITING
RATE_LIMIT_CALLS=1000
RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_CALLS=100
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
EOF
    
    log_success ".env fájl létrehozva"
fi

# PHASE 8: BACKEND CONNECTION TEST
echo ""
echo "🔌 PHASE 8: BACKEND CONNECTION TESZT"
echo "==================================="

log_info "Python backend database connection teszt..."

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    log_info "Virtual environment aktiválva"
    
    # Test database connection
    python -c "
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv('DATABASE_URL')

try:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1 as test'))
        print('✅ Backend database connection: SUCCESS')
except Exception as e:
    print(f'❌ Backend database connection: FAILED - {e}')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "Backend connection teszt sikeres"
    else
        log_error "Backend connection teszt sikertelen"
    fi
else
    log_warning "Virtual environment nem található"
fi

# PHASE 9: HOMEBREW SERVICE SETUP
echo ""
echo "🔧 PHASE 9: HOMEBREW SERVICE BEÁLLÍTÁS"  
echo "====================================="

log_info "Homebrew PostgreSQL service beállítása..."

# Stop manual process
if [ -n "$PG_PID" ]; then
    log_info "Manual PostgreSQL process leállítása..."
    kill $PG_PID &> /dev/null
    sleep 2
fi

# Start via Homebrew
log_info "PostgreSQL indítása Homebrew service-ként..."
brew services restart postgresql@14

if [ $? -eq 0 ]; then
    log_success "PostgreSQL Homebrew service elindítva"
    
    # Wait for service
    for i in {1..10}; do
        if pg_isready -h localhost -p 5432 &> /dev/null; then
            log_success "PostgreSQL service ready"
            break
        fi
        sleep 1
    done
else
    log_warning "Homebrew service indítás problémás - manual mode marad"
fi

# FINAL STATUS CHECK
echo ""
echo "🎉 VÉGSŐ STÁTUSZ ELLENŐRZÉS"
echo "=========================="

# PostgreSQL service status
if pg_isready -h localhost -p 5432 &> /dev/null; then
    log_success "PostgreSQL fut és elérhető"
else
    log_error "PostgreSQL nem elérhető"
    exit 1
fi

# Database list
log_info "Elérhető databases:"
psql -h localhost -U $CURRENT_USER -l | grep practice_booking_system && log_success "practice_booking_system database OK"

# Connection info
echo ""
echo "📋 POSTGRESQL CONNECTION INFO:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: practice_booking_system"
echo "   User: $CURRENT_USER"  
echo "   Connection: $DATABASE_URL"
echo ""

log_success "🎊 POSTGRESQL JAVÍTÁS BEFEJEZVE!"
echo ""
echo "🚀 KÖVETKEZŐ LÉPÉSEK:"
echo "   1. ./start_backend.sh (most már működnie kell)"
echo "   2. ./start_frontend.sh (frontend indítás)"
echo "   3. ./pilot_user_setup.sh (pilot user accountok)"
echo ""

# Auto-restart backend ha kérjük
read -p "Indítsam el most a backend-et? (y/n): " start_backend
if [ "$start_backend" = "y" ]; then
    log_info "Backend indítása..."
    ./start_backend.sh
fi