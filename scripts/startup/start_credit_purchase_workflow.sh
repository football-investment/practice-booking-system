#!/bin/bash

# 💳 Credit Purchase Workflow Dashboard Starter
# ==============================================

echo "💳 Starting Credit Purchase Workflow Dashboard..."
echo ""

# Activate virtual environment
source implementation/venv/bin/activate

# Set database URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Start Streamlit on port 8504 (different from invitation workflow on 8503)
streamlit run credit_purchase_workflow_dashboard.py --server.port 8504 --server.headless true --browser.gatherUsageStats false

echo ""
echo "✅ Credit Purchase Workflow Dashboard started on http://localhost:8504"
