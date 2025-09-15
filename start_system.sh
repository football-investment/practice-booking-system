#!/bin/bash

# Practice Booking System - Complete Startup Script
# Usage: ./start_system.sh

echo "🚀 PRACTICE BOOKING SYSTEM STARTUP"
echo "=================================="
echo "Starting both backend and frontend..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Create logs directory
mkdir -p logs
echo -e "${BLUE}✅ Logs directory ready${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run: python -m venv venv${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${BLUE}✅ Virtual environment activated${NC}"

# Check database
echo -e "${BLUE}🔍 Checking database connection...${NC}"
python -c "from app.database import engine; engine.connect(); print('Database connected')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database connection OK${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    echo "Please check your DATABASE_URL in app/config.py"
    exit 1
fi

# Start backend in background
echo -e "${BLUE}🚀 Starting FastAPI backend...${NC}"
nohup uvicorn app.main:app --host localhost --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Check if backend is running
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Backend started successfully (port 8000)${NC}"
else
    echo -e "${RED}❌ Backend failed to start${NC}"
    exit 1
fi

# Start frontend in background
echo -e "${BLUE}🚀 Starting React frontend...${NC}"
cd frontend
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
cd ..

# Wait for frontend to start
sleep 5

# Check if frontend is running
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Frontend started successfully (port 3000)${NC}"
else
    echo -e "${RED}❌ Frontend failed to start${NC}"
fi

echo ""
echo "🎉 SYSTEM STARTUP COMPLETE!"
echo "=========================="
echo "📊 Backend:  http://localhost:8000"
echo "🌐 Frontend: http://localhost:3000"
echo "📋 API Docs: http://localhost:8000/api/v1/docs"
echo ""
echo "📋 Process IDs:"
echo "  Backend PID:  $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "📄 Log files:"
echo "  Backend:  logs/backend.log"
echo "  Frontend: logs/frontend.log"
echo "  App logs: logs/app.log"
echo ""
echo "🛑 To stop the system:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "💡 Or use: pkill -f 'uvicorn' && pkill -f 'react-scripts'"