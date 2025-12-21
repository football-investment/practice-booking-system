#!/bin/bash

# Start Invitation Code Workflow Dashboard
# Production-ready user registration testing with invitation codes

echo "🎟️ Starting Invitation Code Workflow Dashboard..."
echo ""
echo "Dashboard URL: http://localhost:8503"
echo ""
echo "==================================="
echo "WORKFLOW STEPS:"
echo "==================================="
echo "Step 1 (ADMIN): Create invitation code"
echo "Step 2 (STUDENT): Register with code"
echo "Step 3 (SYSTEM): Verify registration"
echo ""
echo "==================================="
echo "CREDENTIALS:"
echo "==================================="
echo "Admin: admin@lfa.com / admin123"
echo ""

cd "$(dirname "$0")"

# Kill any existing streamlit on port 8503
lsof -ti :8503 | xargs kill -9 2>/dev/null || true

# Activate virtual environment
source implementation/venv/bin/activate

# Start streamlit
streamlit run invitation_code_workflow_dashboard.py \
    --server.port 8503 \
    --server.headless true \
    --browser.gatherUsageStats false
