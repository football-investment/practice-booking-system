#!/bin/bash

# 🗄️ PRACTICE BOOKING SYSTEM - POSTGRESQL SETUP (macOS)
# Automatikus PostgreSQL telepítés és beállítás macOS-re

echo "🗄️ PRACTICE BOOKING SYSTEM - POSTGRESQL SETUP"
echo "============================================="
echo "Automatikus PostgreSQL beállítás macOS-re"
echo ""

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

# macOS verzió ellenőrzés
echo "🔍 RENDSZER ELLENŐRZÉS"
echo "====================="

if [[ "$OSTYPE" != "darwin"* ]]; then
    log_error "Ez a script csak macOS-re készült!"
    exit 1
fi
log_success "macOS detected: $(sw_vers -productVersion)"

# Homebrew ellenőrzés
if ! command -v brew &> /dev/null; then
    log_warning "Homebrew nincs telepítve"
    log_info "Homebrew telepítése..."
    
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    if [ $? -eq 0 ]; then
        log_success "Homebrew telepítve"
    else
        log_error "Homebrew telepítés sikertelen"
        exit 1
    fi
else
    log_success "Homebrew telepítve"
fi

# PostgreSQL státusz ellenőrzés
echo ""
echo "🔍 POSTGRESQL STÁTUSZ ELLENŐRZÉS"
echo "==============================="

if command -v pg_isready &> /dev/null; then
    log_info "PostgreSQL már telepítve van"
    
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        log_success "PostgreSQL fut"
        PG_RUNNING=true
    else
        log_warning "PostgreSQL telepítve, de nem fut"
        PG_RUNNING=false
    fi
else
    log_warning "PostgreSQL nincs telepítve"
    PG_RUNNING=false
fi

# PostgreSQL telepítés ha szükséges
if ! command -v pg_isready &> /dev/null; then
    echo ""
    echo "📦 POSTGRESQL TELEPÍTÉS"
    echo "======================"
    
    log_info "PostgreSQL telepítése Homebrew-val..."
    brew install postgresql@14
    
    if [ $? -eq 0 ]; then
        log_success "PostgreSQL telepítve"
    else
        log_error "PostgreSQL telepítés sikertelen"
        exit 1
    fi
    
    # PATH frissítés
    echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
    export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
    
    log_success "PostgreSQL PATH beállítva"
fi

# PostgreSQL indítás
if [ "$PG_RUNNING" != true ]; then
    echo ""
    echo "🚀 POSTGRESQL INDÍTÁS"
    echo "===================="
    
    log_info "PostgreSQL service indítása..."
    
    # Homebrew service indítás
    brew services start postgresql@14
    
    if [ $? -eq 0 ]; then
        log_success "PostgreSQL service elindítva"
        
        # Várakozás a szolgáltatás elindulására
        log_info "Várakozás a PostgreSQL elindulására..."
        for i in {1..10}; do
            if pg_isready -h localhost -p 5432 &> /dev/null; then
                log_success "PostgreSQL elérhető"
                break
            fi
            sleep 1
        done
        
        if ! pg_isready -h localhost -p 5432 &> /dev/null; then
            log_error "PostgreSQL nem indult el 10 másodperc alatt"
            exit 1
        fi
        
    else
        log_error "PostgreSQL indítás sikertelen"
        exit 1
    fi
fi

# Database létrehozás
echo ""
echo "🗄️ DATABASE LÉTREHOZÁS"
echo "====================="

# Postgres user létrehozás ha nem létezik
if ! psql -h localhost -U postgres -c '\q' &> /dev/null; then
    log_info "Default postgres user beállítása..."
    
    # Alapértelmezett user (aktuális macOS user)
    current_user=$(whoami)
    log_info "Aktuális user: $current_user"
    
    # Próbáljunk kapcsolódni az aktuális user-rel
    if psql -h localhost -U $current_user -c '\q' &> /dev/null; then
        log_success "Database kapcsolat OK ($current_user user-rel)"
        DB_USER=$current_user
    else
        log_warning "Próbálkozás alapértelmezett postgres user-rel..."
        
        # Postgres user létrehozás
        createuser -s postgres 2>/dev/null
        
        if psql -h localhost -U postgres -c '\q' &> /dev/null; then
            log_success "postgres user létrehozva"
            DB_USER="postgres"
        else
            log_error "Nem sikerült database user-t beállítani"
            exit 1
        fi
    fi
else
    log_success "postgres user már létezik"
    DB_USER="postgres"
fi

# Practice booking database létrehozás
log_info "practice_booking_system database létrehozása..."

if psql -h localhost -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw practice_booking_system; then
    log_success "practice_booking_system database már létezik"
else
    createdb -h localhost -U $DB_USER practice_booking_system
    
    if [ $? -eq 0 ]; then
        log_success "practice_booking_system database létrehozva"
    else
        log_error "Database létrehozás sikertelen"
        exit 1
    fi
fi

# Database connection teszt
log_info "Database kapcsolat tesztelése..."
if psql -h localhost -U $DB_USER -d practice_booking_system -c 'SELECT 1;' &> /dev/null; then
    log_success "Database kapcsolat működik"
else
    log_error "Database kapcsolat teszt sikertelen"
    exit 1
fi

# .env fájl létrehozás/frissítés
echo ""
echo "⚙️ KONFIGURÁCIÓS FÁJL BEÁLLÍTÁS"
echo "=============================="

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    log_info ".env fájl létrehozása..."
    
    cat > $ENV_FILE << EOF
# DATABASE CONFIGURATION - macOS Setup
DATABASE_URL=postgresql://$DB_USER@localhost:5432/practice_booking_system

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

# DEVELOPMENT SETTINGS - macOS
TESTING=false
ENABLE_RATE_LIMITING=false
ENABLE_SECURITY_HEADERS=true
ENABLE_REQUEST_SIZE_LIMIT=false
ENABLE_STRUCTURED_LOGGING=true

# PERMISSIVE RATE LIMITING FOR DEVELOPMENT  
RATE_LIMIT_CALLS=1000
RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_CALLS=100
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
EOF
    
    log_success ".env fájl létrehozva"
else
    log_info ".env fájl már létezik - ellenőrzés..."
    
    # Database URL frissítés ha szükséges
    if grep -q "DATABASE_URL=" $ENV_FILE; then
        if ! grep -q "postgresql://$DB_USER@localhost:5432/practice_booking_system" $ENV_FILE; then
            log_info "Database URL frissítése..."
            sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER@localhost:5432/practice_booking_system|" $ENV_FILE
            log_success "Database URL frissítve"
        else
            log_success ".env database konfiguráció OK"
        fi
    else
        echo "DATABASE_URL=postgresql://$DB_USER@localhost:5432/practice_booking_system" >> $ENV_FILE
        log_success "Database URL hozzáadva"
    fi
fi

# Database inicializálás
echo ""
echo "🔄 DATABASE INICIALIZÁLÁS"
echo "========================"

log_info "Virtual environment aktiválása..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    log_success "Virtual environment aktiválva"
else
    log_error "Virtual environment nem található"
    log_info "Futtasd előbb: python3 -m venv venv"
    exit 1
fi

# Alembic migráció
if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
    log_info "Database schema migráció..."
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log_success "Database schema frissítve"
    else
        log_warning "Database migráció problémás - próbálkozás init script-tel"
    fi
fi

# Init script futtatás
if [ -f "init_db.py" ]; then
    log_info "Database inicializálás..."
    python init_db.py
    
    if [ $? -eq 0 ]; then
        log_success "Database inicializálva"
    else
        log_warning "Database inicializálás problémás"
    fi
fi

# Végső ellenőrzés
echo ""
echo "🔍 VÉGSŐ ELLENŐRZÉS"
echo "=================="

# PostgreSQL status
if pg_isready -h localhost -p 5432 &> /dev/null; then
    log_success "PostgreSQL fut"
else
    log_error "PostgreSQL nem fut"
fi

# Database connection
if python -c "
from app.database import engine
try:
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
        print('Database connection: OK')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
" 2>/dev/null; then
    log_success "Database kapcsolat működik"
else
    log_error "Database kapcsolat problémás"
fi

# Összefoglaló
echo ""
echo "🎉 POSTGRESQL SETUP BEFEJEZVE"
echo "============================="

log_success "PostgreSQL telepítve és fut"
log_success "practice_booking_system database létrehozva"
log_success ".env fájl konfigurálva"

echo ""
echo "📋 DATABASE INFO:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: practice_booking_system"
echo "   User: $DB_USER"
echo "   Password: nincs (local connection)"
echo ""

echo "🚀 KÖVETKEZŐ LÉPÉSEK:"
echo "   1. ./start_backend.sh (backend indítás)"
echo "   2. ./start_frontend.sh (frontend indítás)"
echo "   3. ./pilot_user_setup.sh (user accountok)"
echo ""

log_success "PostgreSQL setup sikeres! 🎊"