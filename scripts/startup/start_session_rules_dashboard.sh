#!/bin/bash

echo "=================================================="
echo "   SESSION RULES TESTING DASHBOARD"
echo "=================================================="
echo ""
echo "✅ Mind a 6 szabály tesztelhető!"
echo "✅ Minden user típus (Student, Instructor, Admin)"
echo ""
echo "Teszt accountok:"
echo "  - Instructor: grandmaster@lfa.com / grandmaster2024"
echo "  - Student:    V4lv3rd3jr@f1stteam.hu / grandmaster2024"
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
streamlit run session_rules_testing_dashboard.py --server.port 8501
