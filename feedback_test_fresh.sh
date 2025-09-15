#!/bin/bash

# 🧪 FRESH FEEDBACK BUSINESS LOGIC TEST SCRIPT (macOS Compatible)
echo "🧪 FRESH FEEDBACK BUSINESS LOGIC TESTING"
echo "========================================"

BASE_URL="http://localhost:8000/api/v1"

echo ""
echo "🔐 STEP 1: Friss tokenek generálása"
echo "====================================="

# Alex login
echo "Alex belépés..."
ALEX_LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com", "password": "password123"}')
  
ALEX_TOKEN=$(echo "$ALEX_LOGIN" | jq -r '.access_token')
echo "Alex token: ${ALEX_TOKEN:0:50}..."

# Admin login
echo "Admin belépés..."
ADMIN_LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourcompany.com", "password": "admin123"}')
  
ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | jq -r '.access_token')
echo "Admin token: ${ADMIN_TOKEN:0:50}..."

if [ "$ALEX_TOKEN" == "null" ] || [ "$ADMIN_TOKEN" == "null" ]; then
  echo "❌ Token generálás sikertelen!"
  exit 1
fi

echo ""
echo "🔍 STEP 2: Alex jelenlegi booking adatai"
echo "----------------------------------------"

ALEX_BOOKINGS=$(curl -s -H "Authorization: Bearer $ALEX_TOKEN" "$BASE_URL/bookings/me")
echo "Alex bookings response:"
echo "$ALEX_BOOKINGS" | jq '.'

echo ""
echo "📊 STEP 3: Booking státusz elemzés"
echo "----------------------------------"

# Bookingok elemzése
BOOKING_COUNT=$(echo "$ALEX_BOOKINGS" | jq -r '.bookings | length')
echo "Total bookings: $BOOKING_COUNT"

# Jelenlegi dátum
CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S")
echo "Current date: $CURRENT_DATE"

echo ""
echo "🕐 STEP 4: Past vs Future sessions"
echo "--------------------------------"

# Past sessions keresése
echo "Past sessions:"
echo "$ALEX_BOOKINGS" | jq -r '.bookings[]? | select(.session.date_start < "'$CURRENT_DATE'") | "PAST: \(.session.title) - \(.session.date_start) - Attended: \(.attended)"'

echo ""
echo "Future sessions:"
echo "$ALEX_BOOKINGS" | jq -r '.bookings[]? | select(.session.date_start >= "'$CURRENT_DATE'") | "FUTURE: \(.session.title) - \(.session.date_start)"'

echo ""
echo "🎯 STEP 5: Awaiting feedback kandidátusok"
echo "----------------------------------------"

# Sessions awaiting feedback
AWAITING_COUNT=$(echo "$ALEX_BOOKINGS" | jq -r '[.bookings[]? | select(.attended == true and .session.date_start < "'$CURRENT_DATE'")] | length')
echo "Current awaiting feedback sessions: $AWAITING_COUNT"

if [ "$AWAITING_COUNT" -gt 0 ]; then
  echo "$ALEX_BOOKINGS" | jq -r '.bookings[]? | select(.attended == true and .session.date_start < "'$CURRENT_DATE'") | "AWAITING FEEDBACK: \(.session.title) - \(.session.date_start)"'
else
  echo "❌ Jelenleg nincs session ami awaiting feedback-et igényelne"
fi

echo ""
echo "📝 STEP 6: Alex feedback history"
echo "-------------------------------"

ALEX_FEEDBACK=$(curl -s -H "Authorization: Bearer $ALEX_TOKEN" "$BASE_URL/feedback/me")
echo "Alex feedback response:"
echo "$ALEX_FEEDBACK" | jq '.'

FEEDBACK_COUNT=$(echo "$ALEX_FEEDBACK" | jq -r '.feedbacks | length')
echo "Alex total feedback count: $FEEDBACK_COUNT"

echo ""
echo "🧪 STEP 7: Teszt scenario létrehozás"
echo "====================================="

echo "Létrehozunk egy múltbeli session-t Alex-szel, attendance = present"

# 1. Múltbeli session létrehozás (macOS kompatibilis)
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  PAST_DATE=$(date -u -v-2d +"%Y-%m-%dT10:00:00")
  PAST_END=$(date -u -v-2d +"%Y-%m-%dT11:00:00")
else
  # Linux
  PAST_DATE=$(date -u -d "2 days ago" +"%Y-%m-%dT10:00:00")
  PAST_END=$(date -u -d "2 days ago" +"%Y-%m-%dT11:00:00")
fi

echo "Past session dátum: $PAST_DATE"

SESSION_DATA='{
  "title": "FEEDBACK TEST SESSION - Past Session",
  "description": "Testing feedback awaiting logic",
  "date_start": "'$PAST_DATE'",
  "date_end": "'$PAST_END'",
  "capacity": 20,
  "group_id": 1,
  "mode": "on_site",
  "location": "Test Location"
}'

echo "Creating past session..."
CREATED_SESSION=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$SESSION_DATA" "$BASE_URL/sessions/")
SESSION_ID=$(echo "$CREATED_SESSION" | jq -r '.id')
echo "Created session response: $CREATED_SESSION"
echo "Created session ID: $SESSION_ID"

if [ "$SESSION_ID" != "null" ] && [ -n "$SESSION_ID" ]; then
  # 2. Alex booking létrehozás
  BOOKING_DATA='{"session_id": '$SESSION_ID'}'
  echo "Creating Alex booking..."
  CREATED_BOOKING=$(curl -s -X POST -H "Authorization: Bearer $ALEX_TOKEN" -H "Content-Type: application/json" -d "$BOOKING_DATA" "$BASE_URL/bookings/")
  BOOKING_ID=$(echo "$CREATED_BOOKING" | jq -r '.id')
  echo "Created booking response: $CREATED_BOOKING"
  echo "Created booking ID: $BOOKING_ID"
  
  if [ "$BOOKING_ID" != "null" ] && [ -n "$BOOKING_ID" ]; then
    # 3. Attendance rögzítés
    ATTENDANCE_DATA='{
      "user_id": 4,
      "session_id": '$SESSION_ID',
      "booking_id": '$BOOKING_ID',
      "status": "present",
      "notes": "Feedback test attendance"
    }'
    
    echo "Recording attendance..."
    CREATED_ATTENDANCE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$ATTENDANCE_DATA" "$BASE_URL/attendance/")
    echo "Attendance response: $CREATED_ATTENDANCE"
    
    # 4. Ellenőrzés - Alex új booking adatok
    echo ""
    echo "🔍 STEP 8: Teszt utáni állapot ellenőrzés"
    echo "----------------------------------------"
    
    sleep 3  # Várakozás az adatbázis frissülésére
    
    NEW_ALEX_BOOKINGS=$(curl -s -H "Authorization: Bearer $ALEX_TOKEN" "$BASE_URL/bookings/me")
    NEW_BOOKING_COUNT=$(echo "$NEW_ALEX_BOOKINGS" | jq -r '.bookings | length')
    echo "Alex NEW total bookings: $NEW_BOOKING_COUNT"
    
    # Awaiting feedback check
    NEW_AWAITING_COUNT=$(echo "$NEW_ALEX_BOOKINGS" | jq -r '[.bookings[]? | select(.attended == true and .session.date_start < "'$CURRENT_DATE'")] | length')
    echo "NEW awaiting feedback sessions: $NEW_AWAITING_COUNT"
    
    if [ "$NEW_AWAITING_COUNT" -gt 0 ]; then
      echo "✅ SIKER! Sessions NOW awaiting feedback:"
      echo "$NEW_ALEX_BOOKINGS" | jq -r '.bookings[]? | select(.attended == true and .session.date_start < "'$CURRENT_DATE'") | "AWAITING: \(.session.title) - \(.session.date_start) - Attended: \(.attended)"'
    else
      echo "❌ Hiba: Még mindig nincs awaiting feedback session"
      echo "Ellenőrizzük a létrehozott booking részleteit:"
      echo "$NEW_ALEX_BOOKINGS" | jq -r '.bookings[]? | select(.id == '$BOOKING_ID') | "Test booking: \(.session.title) - \(.session.date_start) - Attended: \(.attended)"'
    fi
    
    echo ""
    echo "🎯 FRONTEND TESZT"
    echo "================"
    echo "Most nyisd meg: http://localhost:3000/student/feedback"
    echo "Alex bejelentkezéssel: alex@example.com / password123"
    echo ""
    echo "✅ TESZT BEFEJEZETT!"
    echo "Session ID: $SESSION_ID"
    echo "Booking ID: $BOOKING_ID"
  else
    echo "❌ Booking létrehozás sikertelen"
  fi
else
  echo "❌ Session létrehozás sikertelen"
fi