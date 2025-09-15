#!/bin/bash

# 👥 PRACTICE BOOKING SYSTEM - PILOT USER SETUP
# Több instructor és student account létrehozása pilot programhoz

echo "👥 PRACTICE BOOKING SYSTEM - PILOT USER SETUP"
echo "============================================="
echo "Több oktató és hallgató account létrehozása a pilot teszteléshez"
echo ""

# Színes output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Environment variables
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@company.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

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

log_user() {
    echo -e "${PURPLE}👤 $1${NC}"
}

# Segédfüggvények
api_call() {
    local method=$1
    local endpoint=$2
    local token=$3
    local data=$4
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer $token" \
             -d "$data" \
             "http://localhost:8000$endpoint"
    else
        curl -s -X "$method" \
             -H "Authorization: Bearer $token" \
             "http://localhost:8000$endpoint"
    fi
}

# Ellenőrzések
echo "🔍 ELŐZETES ELLENŐRZÉSEK"
echo "======================"

# Backend futás ellenőrzés
if ! curl -s http://localhost:8000/health &> /dev/null; then
    log_error "Backend nem fut a localhost:8000-n!"
    log_info "Indítsd el előbb: ./start_backend.sh"
    exit 1
fi
log_success "Backend fut"

# Admin bejelentkezés
log_info "Admin bejelentkezés..."
ADMIN_LOGIN=$(api_call "POST" "/api/v1/auth/login" "" '{"email":"'$ADMIN_EMAIL'","password":"'$ADMIN_PASSWORD'"}')
ADMIN_TOKEN=$(echo $ADMIN_LOGIN | jq -r '.access_token' 2>/dev/null)

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    log_error "Admin bejelentkezés sikertelen!"
    echo "Response: $ADMIN_LOGIN"
    exit 1
fi
log_success "Admin bejelentkezés sikeres"

# User számok meghatározása
echo ""
echo "📊 PILOT PROGRAM MÉRET BEÁLLÍTÁSA"
echo "================================"

echo "Ajánlott pilot méret:"
echo "  - 3-4 oktató (különböző szakterületek)"
echo "  - 12-20 hallgató (különböző csoportokból)"
echo "  - 1-2 admin (monitoring + support)"
echo ""

read -p "Hány oktatót hozzon létre? (alapértelmezett: 4): " INSTRUCTOR_COUNT
INSTRUCTOR_COUNT=${INSTRUCTOR_COUNT:-4}

read -p "Hány hallgatót hozzon létre? (alapértelmezett: 15): " STUDENT_COUNT  
STUDENT_COUNT=${STUDENT_COUNT:-15}

echo ""
log_info "Létrehozandó accountok: $INSTRUCTOR_COUNT oktató + $STUDENT_COUNT hallgató"

# Megerősítés
read -p "Folytatod a létrehozást? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log_info "Felhasználó megszakította"
    exit 0
fi

# Oktató accountok létrehozása
echo ""
echo "👨‍🏫 OKTATÓ ACCOUNTOK LÉTREHOZÁSA"
echo "==============================="

INSTRUCTOR_NAMES=(
    "Dr. Nagy Péter"
    "Prof. Kovács Anna" 
    "Dr. Szabó Márton"
    "Dr. Tóth Eszter"
    "Dr. Kiss János"
    "Prof. Varga Klára"
)

INSTRUCTOR_DOMAINS=(
    "matematika"
    "fizika" 
    "informatika"
    "kemia"
    "biologia"
    "english"
)

INSTRUCTOR_SUCCESS=0
INSTRUCTOR_FAILED=0

for ((i=1; i<=INSTRUCTOR_COUNT; i++)); do
    # Random név és domain választás
    name_idx=$(($i % ${#INSTRUCTOR_NAMES[@]}))
    domain_idx=$(($i % ${#INSTRUCTOR_DOMAINS[@]}))
    
    name="${INSTRUCTOR_NAMES[$name_idx]}"
    domain="${INSTRUCTOR_DOMAINS[$domain_idx]}"
    email="${domain}.oktato${i}@pilot.test"
    
    log_info "Oktató létrehozása: $name ($email)"
    
    USER_DATA="{
        \"name\": \"$name\",
        \"email\": \"$email\",
        \"password\": \"oktato123\",
        \"role\": \"instructor\"
    }"
    
    RESULT=$(api_call "POST" "/api/v1/users/" "$ADMIN_TOKEN" "$USER_DATA")
    USER_ID=$(echo $RESULT | jq -r '.id' 2>/dev/null)
    
    if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
        log_success "Oktató létrehozva: $name (ID: $USER_ID)"
        log_user "   📧 Email: $email | 🔑 Jelszó: oktato123"
        INSTRUCTOR_SUCCESS=$((INSTRUCTOR_SUCCESS + 1))
    else
        log_error "Oktató létrehozás sikertelen: $name"
        INSTRUCTOR_FAILED=$((INSTRUCTOR_FAILED + 1))
    fi
    
    # Rövid várakozás az API rate limiting elkerülésére  
    sleep 0.2
done

# Hallgató accountok létrehozása
echo ""
echo "🎓 HALLGATÓ ACCOUNTOK LÉTREHOZÁSA"
echo "=============================="

STUDENT_FIRST_NAMES=(
    "Áron" "Bence" "Csaba" "Dániel" "Erik" "Ferenc"
    "Gábor" "Henrik" "István" "János" "Kristóf" "László"
    "Anna" "Beatrix" "Csilla" "Dorina" "Eszter" "Fanni"
    "Gréta" "Hanna" "Ildikó" "Judit" "Kata" "Lilla"
)

STUDENT_LAST_NAMES=(
    "Nagy" "Kovács" "Tóth" "Szabó" "Horváth" "Varga"
    "Kiss" "Molnár" "Németh" "Farkas" "Balogh" "Papp"
    "Takács" "Juhász" "Lakatos" "Mészáros" "Oláh" "Simon"
)

STUDENT_SUCCESS=0
STUDENT_FAILED=0

for ((i=1; i<=STUDENT_COUNT; i++)); do
    # Random név generálás
    first_idx=$(($RANDOM % ${#STUDENT_FIRST_NAMES[@]}))
    last_idx=$(($RANDOM % ${#STUDENT_LAST_NAMES[@]}))
    
    first_name="${STUDENT_FIRST_NAMES[$first_idx]}"
    last_name="${STUDENT_LAST_NAMES[$last_idx]}"
    full_name="$first_name $last_name"
    
    # Email generálás
    email_base=$(echo "$first_name$last_name" | tr '[:upper:]' '[:lower:]' | sed 's/[áéíóöőüű]/a/g')
    email="${email_base}${i}@pilot.test"
    
    log_info "Hallgató létrehozása: $full_name ($email)"
    
    USER_DATA="{
        \"name\": \"$full_name\",
        \"email\": \"$email\",
        \"password\": \"hallgato123\",
        \"role\": \"student\"
    }"
    
    RESULT=$(api_call "POST" "/api/v1/users/" "$ADMIN_TOKEN" "$USER_DATA")
    USER_ID=$(echo $RESULT | jq -r '.id' 2>/dev/null)
    
    if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
        log_success "Hallgató létrehozva: $full_name (ID: $USER_ID)"
        if [ $((i % 5)) -eq 0 ]; then  # Minden 5. hallgatónál mutassa az adatokat
            log_user "   📧 Email: $email | 🔑 Jelszó: hallgato123"
        fi
        STUDENT_SUCCESS=$((STUDENT_SUCCESS + 1))
    else
        log_error "Hallgató létrehozás sikertelen: $full_name"
        STUDENT_FAILED=$((STUDENT_FAILED + 1))
    fi
    
    # Progress indicator
    if [ $((i % 3)) -eq 0 ]; then
        echo -n "."
    fi
    
    # Rövid várakozás
    sleep 0.1
done

echo ""

# Database validáció
echo ""
echo "🔍 ADATBÁZIS VALIDÁCIÓ"  
echo "===================="

log_info "User számok ellenőrzése az adatbázisban..."

# Python script a számok ellenőrzésére
cat > temp_user_count.py << EOF
from app.database import SessionLocal
from app.models.user import User, UserRole

db = SessionLocal()
try:
    total = db.query(User).filter(User.is_active == True).count()
    admins = db.query(User).filter(User.role == UserRole.ADMIN, User.is_active == True).count()
    instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR, User.is_active == True).count()
    students = db.query(User).filter(User.role == UserRole.STUDENT, User.is_active == True).count()
    
    print(f"TOTAL:{total}")
    print(f"ADMIN:{admins}")
    print(f"INSTRUCTOR:{instructors}")
    print(f"STUDENT:{students}")
finally:
    db.close()
EOF

DB_RESULT=$(python temp_user_count.py 2>/dev/null)
rm temp_user_count.py

if [ -n "$DB_RESULT" ]; then
    TOTAL_DB=$(echo "$DB_RESULT" | grep "TOTAL:" | cut -d: -f2)
    ADMIN_DB=$(echo "$DB_RESULT" | grep "ADMIN:" | cut -d: -f2)
    INSTRUCTOR_DB=$(echo "$DB_RESULT" | grep "INSTRUCTOR:" | cut -d: -f2)
    STUDENT_DB=$(echo "$DB_RESULT" | grep "STUDENT:" | cut -d: -f2)
    
    log_success "Adatbázis user számok:"
    echo "   👨‍💼 Admin: $ADMIN_DB"
    echo "   👨‍🏫 Oktató: $INSTRUCTOR_DB"  
    echo "   🎓 Hallgató: $STUDENT_DB"
    echo "   📊 Összesen: $TOTAL_DB aktív user"
else
    log_warning "Adatbázis ellenőrzés sikertelen"
fi

# Összefoglaló jelentés
echo ""
echo "📋 PILOT SETUP ÖSSZEFOGLALÓ"
echo "=========================="

log_success "Oktató accountok: $INSTRUCTOR_SUCCESS/$INSTRUCTOR_COUNT sikeres"
log_success "Hallgató accountok: $STUDENT_SUCCESS/$STUDENT_COUNT sikeres"

if [ $INSTRUCTOR_FAILED -gt 0 ] || [ $STUDENT_FAILED -gt 0 ]; then
    log_warning "Sikertelen létrehozások: $((INSTRUCTOR_FAILED + STUDENT_FAILED))"
fi

echo ""
echo "🔐 BEJELENTKEZÉSI ADATOK"
echo "======================="
echo ""
echo "👨‍💼 ADMIN:"
echo "   📧 $ADMIN_EMAIL | 🔑 $ADMIN_PASSWORD"
echo ""
echo "👨‍🏫 OKTATÓK (példa):"
echo "   📧 matematika.oktato1@pilot.test | 🔑 oktato123"
echo "   📧 fizika.oktato2@pilot.test | 🔑 oktato123"
echo "   📧 informatika.oktato3@pilot.test | 🔑 oktato123"
echo ""
echo "🎓 HALLGATÓK (példa):"  
echo "   📧 áronnag1@pilot.test | 🔑 hallgato123"
echo "   📧 beatrixkovács2@pilot.test | 🔑 hallgato123"
echo "   📧 csabatóth3@pilot.test | 🔑 hallgato123"
echo ""

# Pilot tesztelési instrukciók
echo "🎯 PILOT TESZTELÉSI INSTRUKCIÓK"
echo "=============================="
echo ""
echo "1. 📱 ADMIN FELADATOK:"
echo "   - Szemeszter létrehozás (2024 őszi szemeszter)"
echo "   - Csoportok kialakítása (4-5 hallgató/csoport)"
echo "   - Oktatók hozzárendelése csoportokhoz"
echo ""
echo "2. 👨‍🏫 OKTATÓ FELADATOK:"  
echo "   - Practice session-ök létrehozása"
echo "   - Időpontok és helyszínek beállítása"
echo "   - Kapacitások meghatározása"
echo ""
echo "3. 🎓 HALLGATÓ FELADATOK:"
echo "   - Regisztráció gyakorlatokra"
echo "   - Lemondások tesztelése"
echo "   - Feedback küldés"
echo ""

# Login URL információ
echo "🌐 TESZTELÉSI URL:"
echo "   http://localhost:3000"
echo ""

log_success "PILOT USER SETUP BEFEJEZVE!"
log_info "A pilot program most $((INSTRUCTOR_SUCCESS + STUDENT_SUCCESS + 1)) aktív user-rel tesztelhető"