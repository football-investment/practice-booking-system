#!/bin/bash

# 🎨 MINIMAL FRONTEND SETUP SCRIPT
# Creates basic React frontend for backend testing

echo "🎨 CREATING MINIMAL FRONTEND FOR BACKEND TESTING"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    log_error "Not in practice_booking_system directory!"
    exit 1
fi

# Create frontend directory structure
echo ""
echo "🏗️ Creating frontend directory structure..."

mkdir -p frontend/{src,public,src/components,src/pages,src/services,src/contexts}

# Create directory structure verification
dirs_to_create=(
    "frontend"
    "frontend/public" 
    "frontend/src"
    "frontend/src/components"
    "frontend/src/pages"
    "frontend/src/services"
    "frontend/src/contexts"
)

for dir in "${dirs_to_create[@]}"; do
    if [ -d "$dir" ]; then
        log_success "Directory created: $dir"
    else
        log_error "Failed to create: $dir"
        exit 1
    fi
done

# Create package.json
log_info "Creating package.json..."

cat > frontend/package.json << 'EOF'
{
  "name": "practice-booking-frontend",
  "version": "0.1.0",
  "description": "Minimal frontend for Practice Booking System",
  "main": "index.js",
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "react-router-dom": "^6.8.0",
    "axios": "^1.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "proxy": "http://localhost:8000"
}
EOF

if [ -f "frontend/package.json" ]; then
    log_success "package.json created"
else
    log_error "Failed to create package.json"
    exit 1
fi

# Create public/index.html
log_info "Creating public/index.html..."

cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#000000" />
  <meta name="description" content="Practice Booking System - Testing Frontend" />
  <title>Practice Booking System</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
      background-color: #f5f5f5;
    }
  </style>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
EOF

# Create src/index.js
log_info "Creating src/index.js..."

cat > frontend/src/index.js << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
EOF

# Create basic README for frontend
cat > frontend/README.md << 'EOF'
# Practice Booking System - Minimal Frontend

This is a minimal frontend for testing the Practice Booking System backend.

## Purpose
- Test backend API endpoints
- Provide basic UI for user testing
- Validate authentication and core workflows

## Not Included (intentionally)
- Advanced styling/design
- Complex animations
- Mobile optimization
- Advanced features

## Quick Start
```bash
cd frontend
npm install
npm start
```

## Testing Credentials
- Admin: admin@company.com / admin123
- API Base: http://localhost:8000
EOF

log_success "Frontend project structure created successfully"

# Create installation verification script
cat > frontend/verify_frontend_setup.sh << 'EOF'
#!/bin/bash
echo "🔍 FRONTEND SETUP VERIFICATION"
echo "=============================="

# Check directory structure
dirs=("src" "public" "src/components" "src/pages" "src/services" "src/contexts")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ Directory exists: $dir"
    else
        echo "❌ Missing directory: $dir"
    fi
done

# Check files
files=("package.json" "public/index.html" "src/index.js" "README.md")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ File exists: $file"
    else
        echo "❌ Missing file: $file"
    fi
done

echo ""
echo "📋 Next steps:"
echo "1. cd frontend"
echo "2. npm install"
echo "3. npm start"
echo "4. Verify frontend loads at http://localhost:3000"
EOF

chmod +x frontend/verify_frontend_setup.sh

echo ""
echo "🎯 FRONTEND STRUCTURE SETUP COMPLETE"
echo "====================================="
log_success "Directory structure created"
log_success "Package.json configured"  
log_success "Basic HTML template ready"
log_success "React entry point created"
log_success "Verification script created"

echo ""
echo "📋 NEXT STEPS:"
echo "1. cd frontend"
echo "2. npm install"
echo "3. Run verification: ./verify_frontend_setup.sh"
echo "4. Continue with component creation"

echo ""
log_info "Frontend setup script completed successfully"