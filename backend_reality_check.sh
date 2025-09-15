#!/bin/bash
# BACKEND REALITY CHECK - OBJEKTÍV TESZTELÉS
echo "=== BACKEND STATUS VERIFICATION ==="
echo "Date: $(date)"
echo ""

# 1. Process Check
echo "1. BACKEND PROCESS CHECK:"
BACKEND_PID=$(lsof -ti:8000)
if [ -n "$BACKEND_PID" ]; then
    echo "✅ Backend process found: PID $BACKEND_PID"
    echo "   Command: $(ps -p $BACKEND_PID -o comm=)"
else
    echo "❌ No process listening on port 8000"
fi
echo ""

# 2. Health Check
echo "2. HEALTH ENDPOINT TEST:"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
if [ "$HEALTH_STATUS" = "200" ]; then
    echo "✅ Health endpoint responds: HTTP $HEALTH_STATUS"
    curl -s http://localhost:8000/health | head -3
else
    echo "❌ Health endpoint failed: HTTP $HEALTH_STATUS"
fi
echo ""

# 3. Admin Login Test
echo "3. ADMIN LOGIN TEST:"
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"admin123"}' 2>/dev/null)

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "✅ Admin login successful"
    TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
    echo "   Token length: ${#TOKEN}"
else
    echo "❌ Admin login failed"
    echo "   Response: $LOGIN_RESPONSE"
fi
echo ""

# 4. Analytics Endpoints Test (if login successful)
if [ -n "$TOKEN" ]; then
    echo "4. ANALYTICS ENDPOINTS TEST:"
    
    ENDPOINTS=("utilization" "attendance" "metrics")
    for endpoint in "${ENDPOINTS[@]}"; do
        echo "Testing $endpoint..."
        HTTP_STATUS=$(curl -s -o /tmp/test_$endpoint.json -w "%{http_code}" \
            -H "Authorization: Bearer $TOKEN" \
            "http://localhost:8000/api/v1/analytics/$endpoint?start_date=2025-08-01&end_date=2025-08-31" 2>/dev/null)
        
        if [ "$HTTP_STATUS" = "200" ]; then
            RESPONSE_SIZE=$(wc -c < /tmp/test_$endpoint.json 2>/dev/null || echo "0")
            echo "  ✅ $endpoint: HTTP $HTTP_STATUS, Response: ${RESPONSE_SIZE} bytes"
            # Show first few lines of response
            head -3 /tmp/test_$endpoint.json 2>/dev/null || echo "  (No response content)"
        else
            echo "  ❌ $endpoint: HTTP $HTTP_STATUS"
            head -3 /tmp/test_$endpoint.json 2>/dev/null || echo "  (No response content)"
        fi
    done
else
    echo "4. ANALYTICS ENDPOINTS TEST: SKIPPED (no auth token)"
fi
echo ""

# 5. Recent Log Check
echo "5. RECENT SERVER ACTIVITY:"
if [ -f "logs/app.log" ]; then
    echo "Last 5 log entries:"
    tail -5 logs/app.log | while read line; do
        echo "  $line"
    done
elif [ -f "app.log" ]; then
    echo "Last 5 log entries:"
    tail -5 app.log | while read line; do
        echo "  $line"  
    done
else
    echo "  No log file found in current directory"
fi
echo ""

# 6. Summary
echo "=== SUMMARY ==="
if [ -n "$BACKEND_PID" ] && [ "$HEALTH_STATUS" = "200" ]; then
    echo "🟢 BACKEND IS RUNNING"
    echo "   Process: Active (PID $BACKEND_PID)"
    echo "   Health: OK"
    if [ -n "$TOKEN" ]; then
        echo "   Auth: Working"
        echo "   Analytics: Check individual results above"
    else
        echo "   Auth: Failed"
    fi
else
    echo "🔴 BACKEND IS NOT RUNNING OR BROKEN"
fi

# Cleanup
rm -f /tmp/test_*.json 2>/dev/null