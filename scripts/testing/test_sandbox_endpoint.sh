#!/bin/bash

# Test sandbox endpoint
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lfa.com","password":"admin123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtained: ${TOKEN:0:50}..."

echo ""
echo "Calling /api/v1/sandbox/run-test..."
echo ""

curl -s -X POST http://localhost:8000/api/v1/sandbox/run-test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tournament_type": "league",
    "skills_to_test": ["passing", "dribbling"],
    "player_count": 8
  }' | python3 -m json.tool
