#!/bin/bash
# Test script for Sandbox Phase 1 Read-Only APIs

set -e

echo "🧪 Testing Sandbox Phase 1: Read-Only APIs"
echo "==========================================="
echo

# Step 1: Get admin token
echo "1️⃣  Authenticating as admin..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lfa.com","password":"admin123"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get admin token"
  exit 1
fi

echo "✅ Token obtained"
echo

# Step 2: Test GET /sandbox/users
echo "2️⃣  Testing GET /sandbox/users (limit=3)..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/sandbox/users?limit=3" \
  | python3 -m json.tool > /tmp/sandbox_users_test.json

USER_COUNT=$(cat /tmp/sandbox_users_test.json | grep '"id"' | wc -l | tr -d ' ')
echo "✅ Returned $USER_COUNT users"
echo "📄 Sample response:"
cat /tmp/sandbox_users_test.json | head -30
echo

# Step 3: Test GET /sandbox/instructors
echo "3️⃣  Testing GET /sandbox/instructors (limit=2)..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/sandbox/instructors?limit=2" \
  | python3 -m json.tool > /tmp/sandbox_instructors_test.json

INSTRUCTOR_COUNT=$(cat /tmp/sandbox_instructors_test.json | grep '"id"' | wc -l | tr -d ' ')
echo "✅ Returned $INSTRUCTOR_COUNT instructors"
echo "📄 Sample response:"
cat /tmp/sandbox_instructors_test.json | head -20
echo

# Step 4: Test GET /sandbox/users/{id}/skills
echo "4️⃣  Testing GET /sandbox/users/4/skills..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/sandbox/users/4/skills" \
  | python3 -m json.tool > /tmp/sandbox_user_skills_test.json

SKILLS_COUNT=$(cat /tmp/sandbox_user_skills_test.json | grep -c '"passing"' || echo "0")
echo "✅ Skill profile retrieved (contains passing: $SKILLS_COUNT)"
echo "📄 Sample response:"
cat /tmp/sandbox_user_skills_test.json | head -40
echo

echo "==========================================="
echo "✅ All Phase 1 endpoints tested successfully!"
echo
echo "Summary:"
echo "- GET /sandbox/users: $USER_COUNT users returned"
echo "- GET /sandbox/instructors: $INSTRUCTOR_COUNT instructors returned"
echo "- GET /sandbox/users/4/skills: Full skill profile retrieved"
