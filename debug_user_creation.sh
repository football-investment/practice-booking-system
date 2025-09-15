#!/bin/bash

# 🔍 USER CREATION DEBUG SCRIPT
# Diagnosztizálja miért nem sikerülnek a user létrehozások

echo "🔍 USER CREATION DEBUG SCRIPT"
echo "============================="

# Environment variables
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@company.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

# Színek
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

# Backend ellenőrzés
log_info "Backend elérhetőség ellenőrzése..."
if ! curl -s http://localhost:8000/health &> /dev/null; then
    log_error "Backend nem elérhető!"
    exit 1
fi
log_success "Backend elérhető"

# Admin login teszt
log_info "Admin bejelentkezés tesztelése..."
ADMIN_LOGIN=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    http://localhost:8000/api/v1/auth/login)

ADMIN_TOKEN=$(echo $ADMIN_LOGIN | jq -r '.access_token' 2>/dev/null)

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    log_error "Admin login sikertelen!"
    echo "Response: $ADMIN_LOGIN"
    exit 1
fi
log_success "Admin bejelentkezés sikeres"

# API dokumentáció ellenőrzés
log_info "API dokumentáció ellenőrzése..."
API_DOCS=$(curl -s http://localhost:8000/docs)
if echo "$API_DOCS" | grep -q "OpenAPI"; then
    log_success "API dokumentáció elérhető: http://localhost:8000/docs"
else
    log_warning "API dokumentáció problémás"
fi

# User creation endpoint teszt - egyszerű teszt user
echo ""
echo "🧪 USER CREATION ENDPOINT TESZT"
echo "=============================="

log_info "Test user létrehozás..."

TEST_USER_DATA='{
    "name": "Test User",
    "email": "test.debug@pilot.test",
    "password": "testpass123",
    "role": "student"
}'

echo "📤 Küldött adat:"
echo "$TEST_USER_DATA" | jq .

USER_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "$TEST_USER_DATA" \
    http://localhost:8000/api/v1/users/)

echo ""
echo "📥 API válasz:"
echo "$USER_RESPONSE" | jq . 2>/dev/null || echo "$USER_RESPONSE"

# Válasz elemzés
if echo "$USER_RESPONSE" | jq -e '.id' &>/dev/null; then
    USER_ID=$(echo "$USER_RESPONSE" | jq -r '.id')
    log_success "User létrehozás sikeres! ID: $USER_ID"
elif echo "$USER_RESPONSE" | jq -e '.detail' &>/dev/null; then
    ERROR_DETAIL=$(echo "$USER_RESPONSE" | jq -r '.detail')
    log_error "API error: $ERROR_DETAIL"
elif echo "$USER_RESPONSE" | grep -q "validation error"; then
    log_error "Validation error detected"
    echo "$USER_RESPONSE" | jq '.detail' 2>/dev/null || echo "$USER_RESPONSE"
else
    log_warning "Ismeretlen response format"
fi

# Jelenlegi users ellenőrzés
echo ""
echo "👥 JELENLEGI USERS ELLENŐRZÉS"
echo "============================"

USERS_RESPONSE=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "http://localhost:8000/api/v1/users/")

if echo "$USERS_RESPONSE" | jq -e '.users' &>/dev/null; then
    TOTAL_USERS=$(echo "$USERS_RESPONSE" | jq -r '.total')
    log_info "Jelenlegi users száma: $TOTAL_USERS"
    
    echo "📋 User lista:"
    echo "$USERS_RESPONSE" | jq -r '.users[] | "  - \(.name) (\(.email)) [\(.role)]"'
else
    log_error "Users lista lekérés sikertelen"
    echo "Response: $USERS_RESPONSE"
fi

# Email uniqueness teszt
echo ""
echo "📧 EMAIL UNIQUENESS TESZT"
echo "========================="

EXISTING_EMAIL_TEST="{
    \"name\": \"Duplicate Email Test\",
    \"email\": \"$ADMIN_EMAIL\",
    \"password\": \"testpass123\", 
    \"role\": \"student\"
}"

log_info "Duplicate email teszt ($ADMIN_EMAIL)..."
DUPLICATE_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "$EXISTING_EMAIL_TEST" \
    http://localhost:8000/api/v1/users/)

echo "Response:"
echo "$DUPLICATE_RESPONSE" | jq . 2>/dev/null || echo "$DUPLICATE_RESPONSE"

if echo "$DUPLICATE_RESPONSE" | grep -iq "email.*already.*exists\|duplicate\|unique"; then
    log_success "Email uniqueness constraint működik"
else
    log_warning "Email uniqueness response nem egyértelmű"
fi

# Különböző formátumok tesztelése
echo ""
echo "🔍 FORMÁTUM TESZTEK"
echo "=================="

# Magyar karakteres név teszt
MAGYAR_NAME_TEST='{
    "name": "Kovács József",
    "email": "kovacs.jozsef@pilot.test",
    "password": "testpass123",
    "role": "instructor"
}'

log_info "Magyar karakteres név teszt..."
MAGYAR_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "$MAGYAR_NAME_TEST" \
    http://localhost:8000/api/v1/users/)

if echo "$MAGYAR_RESPONSE" | jq -e '.id' &>/dev/null; then
    log_success "Magyar karakteres név OK"
else
    log_error "Magyar karakteres név probléma"
    echo "$MAGYAR_RESPONSE" | jq . 2>/dev/null || echo "$MAGYAR_RESPONSE"
fi

# Backend logs ellenőrzés
echo ""
echo "📝 BACKEND LOGS SUGGESTION"
echo "========================="

log_info "Backend logs ellenőrzéséhez:"
echo "  - Nézd meg a backend terminál ablakot"
echo "  - Keress 422 vagy 500 status code-okat"
echo "  - Validation error üzeneteket"

# Troubleshooting javaslatok
echo ""
echo "🔧 TROUBLESHOOTING JAVASLATOK"
echo "============================"

echo "Ha user létrehozás sikertelen:"
echo "  1. Ellenőrizd a backend logs-ot validation errors-ért"
echo "  2. Próbáld ki az API-t közvetlenül: http://localhost:8000/docs"
echo "  3. Check database constraints és unique indexes"
echo "  4. Verify name/email field requirements"

echo ""
echo "🌐 API DOCS: http://localhost:8000/docs"
echo "🔍 Direct API testing ajánlott a root cause megtalálásához"

log_success "Debug script completed"
echo ""
echo "📋 KÖVETKEZŐ LÉPÉS:"
echo "   1. Elemezd az API response-okat"
echo "   2. Check backend terminal logs"
echo "   3. Try direct API testing at /docs"