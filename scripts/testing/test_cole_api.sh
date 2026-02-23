#!/bin/bash
# Test Cole Palmer /me endpoint

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"cole.palmer@f1rstteam.hu","password":"TestPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', 'NONE'))")

echo "Token: ${TOKEN:0:30}..."

# Get /me
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool \
  | grep -A 50 "licenses"
