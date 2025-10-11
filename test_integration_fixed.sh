#!/bin/bash

echo "🧪 FRONTEND-BACKEND INTEGRATION TEST (FIXED)"
echo "=============================================="
echo ""

# Test with user that HAS competency data (user 52)
TEST_EMAIL="hook_test_1760129050@test.com"
TEST_PASSWORD="HookTest123!"

# Test 1: Health check
echo "✅ Test 1: Backend Health Check"
curl -s http://localhost:8000/api/v1/debug/health | python3 -m json.tool
echo ""

# Test 2: Login
echo "✅ Test 2: Login with test user (has competency data)"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed - no token received"
  exit 1
else
  echo "✅ Login successful - Token received (length: ${#TOKEN})"
fi
echo ""

# Test 3: Get user profile
echo "✅ Test 3: Get Current User"
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -15
echo ""

# Test 4: My Competencies
echo "✅ Test 4: My Competencies (/competency/my-competencies)"
curl -s "http://localhost:8000/api/v1/competency/my-competencies" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# Test 5: Competency Milestones
echo "✅ Test 5: Competency Milestones"
curl -s http://localhost:8000/api/v1/competency/milestones \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# Test 6: Assessment History
echo "✅ Test 6: Assessment History"
curl -s "http://localhost:8000/api/v1/competency/assessment-history?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# Test 7: Radar Chart Data (with specialization)
echo "✅ Test 7: Competency Radar Chart Data (PLAYER specialization)"
curl -s "http://localhost:8000/api/v1/competency/radar-chart-data?specialization_id=PLAYER" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "=============================================="
echo "✅ ALL API INTEGRATION TESTS COMPLETE"
echo "=============================================="
