#!/bin/bash

# LFA Education Center - Start Production Streamlit Frontend
# This script starts the Streamlit production frontend

echo "🚀 Starting LFA Education Center - Streamlit Production Frontend"
echo "================================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please create virtual environment first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "⚠️  Streamlit not found. Installing..."
    pip install streamlit requests
fi

# Set environment variables (optional - can be customized)
export API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "✅ Configuration:"
echo "   - API URL: $API_BASE_URL"
echo "   - Port: 8502"
echo ""

# Start Streamlit app
echo "🎬 Launching Streamlit app..."
echo ""

cd streamlit_app && streamlit run 🏠_Home.py \
    --server.port 8502 \
    --server.address localhost \
    --server.headless false \
    --theme.base light \
    --theme.primaryColor "#1E40AF" \
    --theme.backgroundColor "#F9FAFB" \
    --theme.secondaryBackgroundColor "#FFFFFF"

echo ""
echo "✅ Streamlit frontend stopped"
