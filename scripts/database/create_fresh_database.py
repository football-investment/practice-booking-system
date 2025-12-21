"""
Create fresh database with all tables using SQLAlchemy models
"""
from sqlalchemy import create_engine, text
from app.database import Base
from app.models.user import User
from app.models.session import Session as SessionModel, SessionType
from app.models.semester import Semester
from app.models.booking import Booking
from app.models.attendance import Attendance
from app.models.quiz import Quiz, QuizQuestion, QuizAttempt, SessionQuiz
from app.models.gamification import GamificationStats
from datetime import datetime, timezone, timedelta
import bcrypt

# New database
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

print("="*60)
print("CREATING FRESH DATABASE: lfa_intern_system")
print("="*60)

# Create engine
engine = create_engine(DATABASE_URL)

# Drop all tables first
print("\n1️⃣ Dropping existing tables...")
Base.metadata.drop_all(engine)
print("✅ All tables dropped")

# Create all tables from models
print("\n2️⃣ Creating all tables from SQLAlchemy models...")
Base.metadata.create_all(engine)
print("✅ All tables created")

# Add instructor materials columns manually (not in models yet)
print("\n3️⃣ Adding instructor materials columns...")
with engine.connect() as conn:
    conn.execute(text("""
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
    """))
    conn.commit()
print("✅ Instructor materials columns added")

# Create test users
print("\n4️⃣ Creating test users...")
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
db = Session()

try:
    # Hash passwords
    admin_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    junior_hash = bcrypt.hashpw("junior123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create users
    admin = User(
        email="admin@lfa.com",
        hashed_password=admin_hash,
        full_name="Admin User",
        user_type="admin",
        is_active=True
    )

    junior = User(
        email="junior.intern@lfa.com",
        hashed_password=junior_hash,
        full_name="Junior Intern",
        user_type="student",
        is_active=True
    )

    grandmaster = User(
        email="grandmaster@lfa.com",
        hashed_password=admin_hash,
        full_name="Grand Master",
        user_type="admin",
        is_active=True
    )

    db.add_all([admin, junior, grandmaster])
    db.commit()

    print(f"✅ Users created:")
    print(f"   - admin@lfa.com (ID: {admin.id})")
    print(f"   - junior.intern@lfa.com (ID: {junior.id})")
    print(f"   - grandmaster@lfa.com (ID: {grandmaster.id})")

    # Create Fall 2025 semester
    print("\n5️⃣ Creating Fall 2025 semester...")
    semester = Semester(
        name="Fall 2025",
        start_date=datetime(2025, 9, 1).date(),
        end_date=datetime(2025, 11, 30).date(),
        is_active=True
    )
    db.add(semester)
    db.commit()
    print(f"✅ Semester created (ID: {semester.id})")

    # Create gamification stats for junior intern
    print("\n6️⃣ Creating gamification stats for Junior Intern...")
    stats = GamificationStats(
        user_id=junior.id,
        total_xp=0,
        level=1,
        semester_id=semester.id
    )
    db.add(stats)
    db.commit()
    print(f"✅ Gamification stats created")

    print("\n" + "="*60)
    print("✅ DATABASE SETUP COMPLETE!")
    print("="*60)
    print(f"\nDatabase: lfa_intern_system")
    print(f"\nUsers:")
    print(f"  - admin@lfa.com / admin123 (admin)")
    print(f"  - junior.intern@lfa.com / junior123 (student)")
    print(f"  - grandmaster@lfa.com / admin123 (admin)")
    print(f"\nSemester: Fall 2025 (ID: {semester.id})")
    print(f"\nNext: Upload HYBRID-1.1 session with TODAY's date")
    print("="*60)

except Exception as e:
    db.rollback()
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
