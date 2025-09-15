#!/bin/bash

# 🔍 USER DATABASE CHECK SCRIPT
echo "🔍 USER DATABASE CHECK"
echo "======================"

# Database közvetlen lekérdezés
echo "📊 Felhasználók az adatbázisban:"
python3 -c "
import sqlite3
import sys
import os

# Database kapcsolat
try:
    conn = sqlite3.connect('practice_booking.db')
    cursor = conn.cursor()
    
    # Users lekérdezés
    cursor.execute('SELECT id, email, full_name, role, password_hash FROM users')
    users = cursor.fetchall()
    
    print(f'Total users: {len(users)}')
    print('\\nUsers:')
    for user in users:
        user_id, email, name, role, password_hash = user
        print(f'- ID: {user_id} | {email} | {name} | {role} | Password: {password_hash[:20]}...')
    
    conn.close()
    
except Exception as e:
    print(f'Database error: {e}')
    sys.exit(1)
"

echo ""
echo "🔐 LOGIN ENDPOINT TESZT"
echo "======================="

# Backend health check
echo "1. Backend health check:"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Backend running"
    echo "Health response: $HEALTH"
else
    echo "❌ Backend not accessible"
    exit 1
fi

echo ""
echo "2. API docs check:"
curl -s http://localhost:8000/docs -o /dev/null
if [ $? -eq 0 ]; then
    echo "✅ API docs accessible at http://localhost:8000/docs"
else
    echo "❌ API docs not accessible"
fi

echo ""
echo "3. Login endpoint test - Alex:"
ALEX_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com", "password": "password123"}')

echo "Alex login response:"
echo "$ALEX_RESPONSE" | jq '.' 2>/dev/null || echo "$ALEX_RESPONSE"

echo ""
echo "4. Login endpoint test - Admin:"
ADMIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourcompany.com", "password": "admin123"}')

echo "Admin login response:"
echo "$ADMIN_RESPONSE" | jq '.' 2>/dev/null || echo "$ADMIN_RESPONSE"

echo ""
echo "🔄 ALTERNATÍV JELSZAVAK TESZT"
echo "============================="

# Próbáljunk más jelszavakat
PASSWORDS=("password123" "admin123" "password" "admin" "123456")

echo "Próbálunk különböző jelszavakat Alex-hez:"
for pwd in "${PASSWORDS[@]}"; do
    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"alex@example.com\", \"password\": \"$pwd\"}")
    
    TOKEN=$(echo "$RESPONSE" | jq -r '.access_token' 2>/dev/null)
    if [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
        echo "✅ Alex sikeres jelszó: $pwd"
        echo "✅ Alex token: ${TOKEN:0:50}..."
        break
    else
        echo "❌ Alex hibás jelszó: $pwd"
    fi
done

echo ""
echo "Próbálunk különböző jelszavakat Admin-hez:"
for pwd in "${PASSWORDS[@]}"; do
    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"admin@yourcompany.com\", \"password\": \"$pwd\"}")
    
    TOKEN=$(echo "$RESPONSE" | jq -r '.access_token' 2>/dev/null)
    if [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
        echo "✅ Admin sikeres jelszó: $pwd"
        echo "✅ Admin token: ${TOKEN:0:50}..."
        break
    else
        echo "❌ Admin hibás jelszó: $pwd"
    fi
done

echo ""
echo "🎯 KÖVETKEZŐ LÉPÉSEK:"
echo "===================="
echo "1. Ha vannak valid tokenek, használd azokat a feedback teszthez"
echo "2. Ha nincs, ellenőrizd a backend log-okat"
echo "3. Próbáld a frontend login-t: http://localhost:3000"
echo "4. Ha szükséges, futtasd újra az init script-et"