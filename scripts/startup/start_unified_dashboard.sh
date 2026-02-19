#!/bin/bash

echo "=================================================="
echo "   UNIFIED WORKFLOW DASHBOARD"
echo "=================================================="
echo ""
echo "✅ Összes workflow egy helyen:"
echo "   - 🎟️ Invitation Code Registration"
echo "   - 💳 Credit Purchase"
echo "   - 🎓 Specialization Unlock"
echo "   - 👑 Admin Management"
echo "   - 👨‍🏫 Instructor Dashboard"
echo "   - 🧪 Session Rules Testing (ÚJ!)"
echo ""
echo "=================================================="
echo ""

# Activate venv
if [ -d "venv" ]; then
    echo "✅ Virtual environment aktiválása..."
    source venv/bin/activate
else
    echo "❌ Virtual environment nem található!"
    exit 1
fi

# Start the dashboard
echo "🚀 Dashboard indítása: http://localhost:8501"
echo ""
streamlit run unified_workflow_dashboard.py --server.port 8501
