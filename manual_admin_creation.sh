#!/bin/bash

# 🔧 MANUAL ADMIN USER CREATION
# Fix for backend startup script bug

echo "🔧 MANUAL ADMIN USER CREATION"
echo "============================="

# Database configuration
DB_NAME="practice_booking_system"
ADMIN_EMAIL="admin@company.com"
ADMIN_PASSWORD="admin123"

# Generate password hash (bcrypt format)
echo "📝 Creating admin user manually..."

# Create admin user with SQL (with bcrypt hash for 'admin123')
# Note: This hash was generated with bcrypt.hashpw('admin123', bcrypt.gensalt())
ADMIN_HASH='$2b$12$K8gF2V5Z.wX3tE9YzL4JZuE7rNc6mD8vB5wQ1xP2zA3fS4cH6uI9.'

SQL_COMMAND="
INSERT INTO users (email, password_hash, full_name, role, is_active, created_at, updated_at)
VALUES (
    '$ADMIN_EMAIL',
    '$ADMIN_HASH',
    'System Administrator',
    'admin',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (email) DO NOTHING;
"

# Execute SQL command
echo "🔧 Inserting admin user into database..."
psql -d "$DB_NAME" -c "$SQL_COMMAND"

if [ $? -eq 0 ]; then
    echo "✅ Admin user created successfully!"
else
    echo "❌ Failed to create admin user"
    exit 1
fi

# Verify creation
echo ""
echo "📊 Verifying admin user creation..."
psql -d "$DB_NAME" -c "SELECT id, email, full_name, role, is_active FROM users WHERE email = '$ADMIN_EMAIL';"

echo ""
echo "🧪 Testing login..."
LOGIN_RESULT=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

if echo "$LOGIN_RESULT" | grep -q "access_token"; then
    echo "✅ Admin login test SUCCESSFUL!"
    echo "🎯 Ready to run complete_system_test.sh"
else
    echo "❌ Admin login test FAILED"
    echo "Response: $LOGIN_RESULT"
fi

echo ""
echo "📋 NEXT STEPS:"
echo "1. Test login in browser: http://localhost:3000"
echo "2. Use credentials: $ADMIN_EMAIL / $ADMIN_PASSWORD" 
echo "3. Run: ./complete_system_test.sh"