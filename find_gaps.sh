#!/bin/bash

# Backend endpoints fájlba
python list_routes.py > backend_endpoints.txt

# Frontend API calls fájlba  
find frontend/src/components/admin/ -name "*.js" -exec grep -ho "api/v1/[^'\"]*" {} \; | sort | uniq > frontend_calls.txt

echo "=== BACKEND VAN, FRONTEND NINCS ==="
while IFS= read -r endpoint; do
  path=$(echo "$endpoint" | awk '{print $2}' | sed 's/^//')
  if ! grep -q "$path" frontend_calls.txt; then
    echo "Backend: $endpoint -> Frontend: MISSING"
  fi
done < backend_endpoints.txt

echo -e "\n=== FRONTEND VAN, BACKEND NINCS ==="
while IFS= read -r call; do
  if ! grep -q "$call" backend_endpoints.txt; then
    echo "Frontend: $call -> Backend: MISSING"
  fi
done < frontend_calls.txt

rm backend_endpoints.txt frontend_calls.txt
