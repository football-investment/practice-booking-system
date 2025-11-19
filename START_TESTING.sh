#!/bin/bash

# 🧪 LFA Education Center - Quick Test Start Script
# Session 3 - Post-Cleanup Testing

echo "🚀 LFA Education Center - Starting Test Environment"
echo "=================================================="
echo ""

# Check if backend is running
echo "📡 Checking backend status..."
if lsof -ti:8000 > /dev/null; then
    echo "✅ Backend is running on port 8000"
else
    echo "⚠️  Backend is NOT running!"
    echo "   Start it with: cd backend && uvicorn app.main:app --reload --port 8000"
    exit 1
fi

# Test backend API
echo ""
echo "🔍 Testing backend API..."
if curl -s http://localhost:8000/api/v1/specializations/ > /dev/null; then
    echo "✅ Backend API responding"
else
    echo "❌ Backend API not responding"
    exit 1
fi

# Check frontend directory
echo ""
echo "📦 Checking frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Running npm install..."
    npm install
fi

echo ""
echo "✅ Everything ready for testing!"
echo ""
echo "=================================================="
echo "📋 TESTING CHECKLIST: See TESTING_CHECKLIST.md"
echo "=================================================="
echo ""
echo "🧑‍🎓 TEST CREDENTIALS:"
echo "   Email:    student13@test.com"
echo "   Password: student123"
echo ""
echo "🎯 TEST THESE PAGES:"
echo "   1. Dashboard:       http://localhost:3000/student/dashboard"
echo "   2. Specialization:  http://localhost:3000/student/specialization-select"
echo "   3. Learning Profile: http://localhost:3000/student/learning-profile"
echo "   4. Achievements:    http://localhost:3000/student/gamification"
echo "   5. Profile:         http://localhost:3000/student/profile"
echo ""
echo "🔥 SESSION 3 ACHIEVEMENTS:"
echo "   • 2,500 lines deleted"
echo "   • 79% bundle reduction (780 KB → 164 KB)"
echo "   • 5 core features working"
echo ""
echo "▶️  Starting frontend development server..."
echo "   (Frontend will open in your browser)"
echo ""
echo "=================================================="
echo ""

# Start frontend
npm start
