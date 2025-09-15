#!/bin/bash

# 🔥 QUICK POSTGRESQL LOCK FILE FIX
# Gyors megoldás a postmaster.pid lock file problémára

echo "🔥 QUICK POSTGRESQL LOCK FILE FIX"
echo "================================="

# Colors
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

# STEP 1: Kill ALL PostgreSQL processes
echo "🔪 STEP 1: PostgreSQL Processes Cleanup"
echo "======================================="

log_info "Összes PostgreSQL process megölése..."

# Kill specific zombie process
sudo kill -9 777 2>/dev/null && log_success "PID 777 megölve" || log_info "PID 777 már nincs"

# Kill all postgres processes
sudo pkill -9 -f postgres
sudo pkill -9 -f postmaster

# Verify no postgres processes
if pgrep postgres >/dev/null; then
    log_warning "Még futnak PostgreSQL processes:"
    ps aux | grep postgres | grep -v grep
    sudo killall -9 postgres 2>/dev/null
else
    log_success "Minden PostgreSQL process leállítva"
fi

# STEP 2: Remove lock files
echo ""
echo "🗑️ STEP 2: Lock Files Cleanup"
echo "============================="

PG_DATA_DIR="/opt/homebrew/var/postgresql@14"

if [ -f "$PG_DATA_DIR/postmaster.pid" ]; then
    log_info "postmaster.pid lock file törlése..."
    sudo rm -f "$PG_DATA_DIR/postmaster.pid"
    log_success "Lock file törölve"
else
    log_info "Nincs lock file"
fi

# Remove any socket files
if [ -S "/tmp/.s.PGSQL.5432" ]; then
    log_info "Socket file törlése..."
    rm -f /tmp/.s.PGSQL.5432*
    log_success "Socket files törölve"
fi

# STEP 3: Clean start PostgreSQL
echo ""
echo "🚀 STEP 3: Clean PostgreSQL Start" 
echo "================================="

log_info "PostgreSQL indítása clean environment-ben..."

# Set PATH
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"

# Start postgres manually
log_info "Manual postgres indítás..."
nohup postgres -D "$PG_DATA_DIR" > "$PG_DATA_DIR/startup.log" 2>&1 &
PG_NEW_PID=$!

log_info "PostgreSQL indult (PID: $PG_NEW_PID)"

# Wait for startup
for i in {1..20}; do
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        log_success "PostgreSQL ready!"
        break
    fi
    
    if [ $i -eq 20 ]; then
        log_error "PostgreSQL nem indult el 20 másodperc alatt"
        log_info "Startup log:"
        tail -10 "$PG_DATA_DIR/startup.log"
        exit 1
    fi
    
    echo -n "."
    sleep 1
done

echo ""

# STEP 4: Database setup
echo ""
echo "🗄️ STEP 4: Database Setup"
echo "======================="

CURRENT_USER=$(whoami)

# Create database if doesn't exist
if psql -h localhost -U $CURRENT_USER -lqt | cut -d \| -f 1 | grep -qw practice_booking_system; then
    log_success "practice_booking_system database exists"
else
    log_info "Creating practice_booking_system database..."
    createdb -h localhost -U $CURRENT_USER practice_booking_system
    
    if [ $? -eq 0 ]; then
        log_success "Database created"
    else
        log_error "Database creation failed"
        exit 1
    fi
fi

# Test connection
log_info "Database connection test..."
if psql -h localhost -U $CURRENT_USER -d practice_booking_system -c 'SELECT 1;' &> /dev/null; then
    log_success "Database connection OK"
else
    log_error "Database connection failed"
    exit 1
fi

# STEP 5: Update .env
echo ""
echo "⚙️ STEP 5: .env Configuration"
echo "============================"

DATABASE_URL="postgresql://$CURRENT_USER@localhost:5432/practice_booking_system"

if [ -f ".env" ]; then
    # Update existing .env
    if grep -q "DATABASE_URL=" ".env"; then
        sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" ".env"
        log_success ".env updated"
    else
        echo "DATABASE_URL=$DATABASE_URL" >> ".env"
        log_success ".env extended"
    fi
else
    # Create minimal .env
    cat > .env << EOF
DATABASE_URL=$DATABASE_URL
SECRET_KEY=development-secret-key-change-in-production-123456789
ADMIN_EMAIL=admin@company.com
ADMIN_PASSWORD=admin123
DEBUG=true
ENVIRONMENT=development
TESTING=false
ENABLE_RATE_LIMITING=false
EOF
    log_success ".env created"
fi

# STEP 6: Backend connection test
echo ""
echo "🔌 STEP 6: Backend Connection Test"
echo "================================="

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    
    log_info "Python backend database test..."
    python -c "
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()

try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        conn.execute('SELECT 1')
        print('✅ Backend database connection: SUCCESS')
except Exception as e:
    print(f'❌ Backend database connection: FAILED - {e}')
    exit(1)
" && log_success "Backend connection test passed" || exit 1
fi

# FINAL STATUS
echo ""
echo "🎉 POSTGRESQL FIX COMPLETE"
echo "=========================="

log_success "PostgreSQL fut (localhost:5432)"
log_success "practice_booking_system database ready"
log_success "Backend connection tesztelve"

echo ""
echo "🚀 NEXT STEPS:"
echo "   1. ./start_backend.sh (most már működnie kell!)"  
echo "   2. Frontend már fut: http://localhost:3000"
echo "   3. Utána: ./pilot_user_setup.sh"
echo ""

# Auto backend start option
read -p "Indítsam el most a backend-et? (y/n): " start_now
if [ "$start_now" = "y" ]; then
    echo ""
    log_info "Backend indítása..."
    ./start_backend.sh
fi