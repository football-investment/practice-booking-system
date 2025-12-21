#!/bin/bash

# LFA Education Center - Streamlit App Starter Script
# IMPORTANT: This starts from the LOGIN page (🏠_Home.py)

echo "🚀 Starting LFA Education Center Streamlit App..."

# Navigate to streamlit_app directory
cd "$(dirname "$0")/streamlit_app"

# Activate virtual environment
source ../venv/bin/activate

# Start Streamlit app from HOME page (login screen)
streamlit run 🏠_Home.py --server.port 8505 --server.headless false

echo "✅ Streamlit app started!"
echo "📍 URL: http://localhost:8505"
echo ""
echo "🔑 Login credentials:"
echo "   Email: admin@lfa.com"
echo "   Password: adminpassword"
