#!/bin/bash
# Restore database from E2E test checkpoint

set -e  # Exit on error

CHECKPOINT_NAME="${1:-after_onboarding}"
CHECKPOINT_FILE="tests/e2e/snapshots/${CHECKPOINT_NAME}.sql"
META_FILE="tests/e2e/snapshots/${CHECKPOINT_NAME}.meta"

echo "============================================"
echo "🔄 Restoring E2E Test Checkpoint"
echo "============================================"
echo ""
echo "Checkpoint: $CHECKPOINT_NAME"
echo "SQL File: $CHECKPOINT_FILE"
echo ""

# Check if checkpoint file exists
if [ ! -f "$CHECKPOINT_FILE" ]; then
    echo "❌ ERROR: Checkpoint file not found: $CHECKPOINT_FILE"
    echo ""
    echo "Available checkpoints:"
    ls -1 tests/e2e/snapshots/*.sql 2>/dev/null | sed 's/tests\/e2e\/snapshots\//  - /' | sed 's/\.sql//' || echo "  (none)"
    exit 1
fi

# Show metadata if available
if [ -f "$META_FILE" ]; then
    echo "📋 Checkpoint metadata:"
    cat "$META_FILE" | sed 's/^/  /'
    echo ""
fi

# Confirm restoration
echo "⚠️  This will ERASE the current database and restore from checkpoint!"
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Restore cancelled"
    exit 0
fi

echo ""
echo "🔄 Dropping and recreating database..."

# Drop and recreate database
PGDATABASE=postgres psql -U postgres -h localhost -c "DROP DATABASE IF EXISTS lfa_intern_system;" 2>/dev/null || true
PGDATABASE=postgres psql -U postgres -h localhost -c "CREATE DATABASE lfa_intern_system;" 2>/dev/null

echo "✅ Database recreated"
echo ""
echo "📥 Restoring from checkpoint: $CHECKPOINT_NAME"

# Restore from checkpoint
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -f "$CHECKPOINT_FILE" > /dev/null 2>&1

echo "✅ Checkpoint restored successfully!"
echo ""
echo "📊 Database contents:"
echo ""

# Show table counts
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
SELECT
    'Users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Tournaments', COUNT(*) FROM tournaments
UNION ALL
SELECT 'Locations', COUNT(*) FROM locations
UNION ALL
SELECT 'Campuses', COUNT(*) FROM campuses
UNION ALL
SELECT 'User Licenses', COUNT(*) FROM user_licenses
UNION ALL
SELECT 'Semester Enrollments', COUNT(*) FROM semester_enrollments
ORDER BY table_name;
" 2>/dev/null

echo ""
echo "✅✅✅ Ready to run tests from checkpoint: $CHECKPOINT_NAME"
echo ""
