#!/bin/bash
# Start Clean Testing Dashboard

echo "🎮 Starting Clean Backend Testing Dashboard..."
echo "📍 URL: http://localhost:8501"
echo ""

cd "$(dirname "$0")"
source implementation/venv/bin/activate

streamlit run clean_testing_dashboard.py --server.port 8501 --server.headless false
