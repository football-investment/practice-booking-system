#!/bin/bash

echo "=================================================="
echo "SETTING UP NEW CLEAN DATABASE: lfa_intern_system"
echo "=================================================="

# Set database URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Activate virtual environment
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate

# Run migrations
echo ""
echo "Step 1: Running Alembic migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed"
    exit 1
fi

# Add instructor materials columns (in case not in migrations)
echo ""
echo "Step 2: Adding instructor materials columns..."
psql $DATABASE_URL <<EOF
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_id_code VARCHAR(50);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS module_number INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS module_name VARCHAR(200);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_number INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS location_type VARCHAR(20);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS location_city VARCHAR(100);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS location_venue VARCHAR(200);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS location_address TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS instructor_role VARCHAR(50);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS instructor_permissions VARCHAR(50);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS student_description TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS instructor_materials JSONB;
CREATE INDEX IF NOT EXISTS ix_sessions_session_id_code ON sessions(session_id_code);
EOF

echo "✅ Instructor materials columns added"

echo ""
echo "Step 3: Creating test users..."
python <<PYTHON
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
import bcrypt

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Hash passwords
    admin_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    junior_hash = bcrypt.hashpw("junior123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create users
    conn.execute(text("""
        INSERT INTO users (email, hashed_password, full_name, user_type, is_active, created_at)
        VALUES
            ('admin@lfa.com', :admin_pwd, 'Admin User', 'admin', true, :now),
            ('junior.intern@lfa.com', :junior_pwd, 'Junior Intern', 'student', true, :now),
            ('grandmaster@lfa.com', :admin_pwd, 'Grand Master', 'admin', true, :now)
        ON CONFLICT (email) DO NOTHING
    """), {
        "admin_pwd": admin_hash,
        "junior_pwd": junior_hash,
        "now": datetime.now(timezone.utc)
    })

    conn.commit()
    print("✅ Users created: admin@lfa.com, junior.intern@lfa.com, grandmaster@lfa.com")
PYTHON

echo ""
echo "Step 4: Creating Fall 2025 semester..."
python <<PYTHON
from sqlalchemy import create_engine, text
from datetime import datetime, timezone

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        INSERT INTO semesters (name, start_date, end_date, is_active, created_at)
        VALUES ('Fall 2025', '2025-09-01', '2025-11-30', true, :now)
        RETURNING id
    """), {"now": datetime.now(timezone.utc)})

    semester_id = result.fetchone()[0]
    conn.commit()
    print(f"✅ Semester created with ID: {semester_id}")
PYTHON

echo ""
echo "=================================================="
echo "✅ DATABASE SETUP COMPLETE!"
echo "=================================================="
echo "Database: lfa_intern_system"
echo "Users:"
echo "  - admin@lfa.com / admin123 (admin)"
echo "  - junior.intern@lfa.com / junior123 (student)"
echo "  - grandmaster@lfa.com / admin123 (admin)"
echo ""
echo "Next: Upload HYBRID-1.1 session with TODAY's date"
echo "=================================================="
