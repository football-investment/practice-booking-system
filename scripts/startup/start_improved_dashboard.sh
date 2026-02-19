#!/bin/bash

# Start Improved Unified Workflow Dashboard
# Separate pages for each role to prevent interface mixing

echo "🎯 Starting LFA Testing Dashboard (Improved Role Separation)..."
echo ""
echo "✅ Features:"
echo "  - Separate pages for Admin, Student, Instructor"
echo "  - No more interface mixing"
echo "  - Clear role separation"
echo "  - Better navigation"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Streamlit dashboard
streamlit run unified_workflow_dashboard_improved.py \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false

echo ""
echo "Dashboard stopped."
