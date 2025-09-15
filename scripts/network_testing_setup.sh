#!/bin/bash

# 🌐 NETWORK TESTING SETUP SCRIPT
# Configures both backend and frontend for IP-based access

echo "🌐 Setting up network testing environment..."

# Get current IP address
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
echo "📍 Local IP detected: $LOCAL_IP"

# Create environment file for frontend
cat > frontend/.env.local << EOF
# Network testing configuration
REACT_APP_API_URL=http://$LOCAL_IP:8000
REACT_APP_BACKEND_URL=http://$LOCAL_IP:8000
GENERATE_SOURCEMAP=false
EOF

echo "✅ Frontend .env.local created with IP: $LOCAL_IP"

# Backend CORS configuration check
echo "🔍 Checking backend CORS configuration..."

# Test if backend accepts IP connections
echo "🧪 Testing backend IP access..."
curl -s -o /dev/null -w "%{http_code}" http://$LOCAL_IP:8000/health || echo "❌ Backend not accessible via IP"

echo ""
echo "📋 TESTING URLS:"
echo "Frontend (localhost): http://localhost:3000"
echo "Frontend (IP): http://$LOCAL_IP:3000"
echo "Backend (localhost): http://localhost:8000"
echo "Backend (IP): http://$LOCAL_IP:8000"
echo ""
echo "🧪 TESTING CHECKLIST:"
echo "□ Chrome Desktop (localhost + IP)"
echo "□ Firefox Desktop (localhost + IP)"
echo "□ Safari Desktop (localhost + IP)"
echo "□ iOS Safari (IP only)"
echo "□ Chrome iOS (IP only)"
echo "□ iPad Safari (IP only)"
echo ""
echo "🚀 Start frontend with: HOST=0.0.0.0 npm start"
echo "📱 Access from mobile: http://$LOCAL_IP:3000"