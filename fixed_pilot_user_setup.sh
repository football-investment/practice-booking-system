#!/bin/bash

# 👥 PRACTICE BOOKING SYSTEM - PILOT USER SETUP (FIXED)
# Email domain fix: .test → .example

echo "👥 PRACTICE BOOKING SYSTEM - PILOT USER SETUP (FIXED)"
echo "====================================================="
echo "Email domain fix alkalmazva - valid domains használata"
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

log_user() {
    echo -e "${PURPLE}👤 $1${NC}"
}

# API call helper
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

# Backend check
if ! curl -s http://localhost:8000/health &> /dev/null; then
    log_error "Backend nem fut a localhost:8000-n!"
    log_info "Indítsd el előbb: ./start_backend.sh"
    exit 1
fi
log_success "Backend fut"

# Admin login
log_info "Admin bejelentkezés..."
ADMIN_LOGIN=$(api_call "POST" "/api/v1/auth/login" "" '{"email":"admin@company.com","password":"admin123"}')
ADMIN_TOKEN=$(echo $ADMIN_LOGIN | jq -r '.access_token' 2>/dev/null)

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    log_error "Admin bejelentkezés sikertelen!"
    echo "Response: $ADMIN_LOGIN"
    exit 1
fi
log_success "Admin bejelentkezés sikeres"

# User counts
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

# Confirmation
read -p "Folytatod a létrehozást? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log_info "Felhasználó megszakította"
    exit 0
fi

# INSTRUCTOR CREATION (FIXED EMAIL DOMAINS)
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
    "math"
    "physics"
    "cs"
    "chemistry" 
    "biology"
    "english"
)

INSTRUCTOR_SUCCESS=0
INSTRUCTOR_FAILED=0

for ((i=1; i<=INSTRUCTOR_COUNT; i++)); do
    # Random name and domain selection
    name_idx=$(($i % ${#INSTRUCTOR_NAMES[@]}))
    domain_idx=$(($i % ${#INSTRUCTOR_DOMAINS[@]}))
    
    name="${INSTRUCTOR_NAMES[$name_idx]}"
    domain="${INSTRUCTOR_DOMAINS[$domain_idx]}"
    # FIXED: .test → .example
    email="${domain}.instructor${i}@example.com"
    
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
        echo "   API response: $RESULT"
        INSTRUCTOR_FAILED=$((INSTRUCTOR_FAILED + 1))
    fi
    
    sleep 0.2
done

# STUDENT CREATION (FIXED EMAIL DOMAINS)
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
    # Random name generation
    first_idx=$(($RANDOM % ${#STUDENT_FIRST_NAMES[@]}))
    last_idx=$(($RANDOM % ${#STUDENT_LAST_NAMES[@]}))
    
    first_name="${STUDENT_FIRST_NAMES[$first_idx]}"
    last_name="${STUDENT_LAST_NAMES[$last_idx]}"
    full_name="$first_name $last_name"
    
    # FIXED: .test → .example + proper ASCII conversion
    email_base=$(echo "$first_name$last_name" | tr '[:upper:]' '[:lower:]' | \
        sed 's/á/a/g; s/é/e/g; s/í/i/g; s/ó/o/g; s/ö/o/g; s/ő/o/g; s/ú/u/g; s/ü/u/g; s/ű/u/g')
    email="${email_base}${i}@example.com"
    
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
        if [ $((i % 5)) -eq 0 ]; then  
            log_user "   📧 Email: $email | 🔑 Jelszó: hallgato123"
        fi
        STUDENT_SUCCESS=$((STUDENT_SUCCESS + 1))
    else
        log_error "Hallgató létrehozás sikertelen: $full_name"
        echo "   API response: $RESULT"
        STUDENT_FAILED=$((STUDENT_FAILED + 1))
    fi
    
    # Progress indicator
    if [ $((i % 3)) -eq 0 ]; then
        echo -n "."
    fi
    
    sleep 0.1
done

echo ""

# Database validation
echo ""
echo "🔍 ADATBÁZIS VALIDÁCIÓ"
echo "===================="

log_info "User számok ellenőrzése..."

# Get final user counts
USERS_RESPONSE=$(api_call "GET" "/api/v1/users/" "$ADMIN_TOKEN")
if echo "$USERS_RESPONSE" | jq -e '.total' &>/dev/null; then
    TOTAL_USERS=$(echo "$USERS_RESPONSE" | jq -r '.total')
    
    # Count by role
    ADMIN_COUNT=$(echo "$USERS_RESPONSE" | jq -r '.users[] | select(.role=="admin")' | wc -l | tr -d ' ')
    INSTRUCTOR_COUNT_DB=$(echo "$USERS_RESPONSE" | jq -r '.users[] | select(.role=="instructor")' | wc -l | tr -d ' ')
    STUDENT_COUNT_DB=$(echo "$USERS_RESPONSE" | jq -r '.users[] | select(.role=="student")' | wc -l | tr -d ' ')
    
    log_success "Adatbázis user számok:"
    echo "   👨‍💼 Admin: $ADMIN_COUNT"
    echo "   👨‍🏫 Oktató: $INSTRUCTOR_COUNT_DB"
    echo "   🎓 Hallgató: $STUDENT_COUNT_DB"
    echo "   📊 Összesen: $TOTAL_USERS aktív user"
else
    log_warning "User count lekérés sikertelen"
fi

# Summary report
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
echo "   📧 admin@company.com | 🔑 admin123"
echo ""
echo "👨‍🏫 OKTATÓK (példa):"
echo "   📧 math.instructor1@example.com | 🔑 oktato123"
echo "   📧 physics.instructor2@example.com | 🔑 oktato123" 
echo "   📧 cs.instructor3@example.com | 🔑 oktato123"
echo ""
echo "🎓 HALLGATÓK (példa):"
echo "   📧 áronnag1@example.com | 🔑 hallgato123"
echo "   📧 beatrixkovács2@example.com | 🔑 hallgato123"
echo "   📧 csabatóth3@example.com | 🔑 hallgato123"
echo ""

# Success rate calculation
TOTAL_ATTEMPTED=$((INSTRUCTOR_COUNT + STUDENT_COUNT))
TOTAL_SUCCESS=$((INSTRUCTOR_SUCCESS + STUDENT_SUCCESS))
SUCCESS_RATE=$(( (TOTAL_SUCCESS * 100) / TOTAL_ATTEMPTED ))

echo "📊 SUCCESS RATE: $SUCCESS_RATE% ($TOTAL_SUCCESS/$TOTAL_ATTEMPTED)"

if [ $SUCCESS_RATE -ge 80 ]; then
    log_success "🎉 PILOT PROGRAM READY!"
    echo "   Sikeres user létrehozás - pilot tesztelés kezdhető"
elif [ $SUCCESS_RATE -ge 50 ]; then
    log_warning "⚠️ Partial success - pilot tesztelés lehetséges kisebb csapattal"
else
    log_error "❌ Low success rate - debug szükséges"
fi

echo ""
echo "🌐 TESZTELÉSI URL:"
echo "   http://localhost:3000"
echo ""

log_success "PILOT USER SETUP BEFEJEZVE!"
log_info "A pilot program most $((TOTAL_SUCCESS + $(echo "$USERS_RESPONSE" | jq -r '.total' 2>/dev/null || echo 6))) aktív user-rel tesztelhető"