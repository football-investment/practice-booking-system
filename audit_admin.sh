#!/bin/bash

echo "=== BACKEND ADMIN ENDPOINTS ==="
grep -r "@router\." app/api/api_v1/endpoints/ | grep -E "(POST|GET|PATCH|DELETE|PUT)" | \
while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1 | xargs basename)
  endpoint=$(echo "$line" | grep -o '/api/v1/[^"]*' | head -1)
  method=$(echo "$line" | grep -o '@router\.[^(]*' | cut -d. -f2)
  echo "$method $endpoint ($file)"
done | sort

echo -e "\n=== FRONTEND ADMIN API CALLS ==="
find frontend/src/components/admin/ -name "*.js" | \
while IFS= read -r file; do
  basename_file=$(basename "$file")
  grep -o "api/v1/[^'\"]*" "$file" 2>/dev/null | \
  sed "s/^/Frontend call: /" | sed "s/$/ ($basename_file)/"
done | sort

