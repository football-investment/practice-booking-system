#!/bin/bash

# Start Interactive Workflow Testing Dashboard
# Usage: ./start_interactive_workflow.sh

echo "🎮 Starting Interactive Workflow Testing Dashboard..."
echo ""
echo "📍 Dashboard will be available at: http://localhost:8502"
echo ""
echo "⚠️  ADMIN LOGIN REQUIRED"
echo "   Email: admin@lfa.com"
echo "   Password: admin123"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo ""

cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system

source implementation/venv/bin/activate

streamlit run interactive_workflow_dashboard.py --server.port 8502 --server.headless true
