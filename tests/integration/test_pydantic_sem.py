from app.database import SessionLocal
from app.models.semester import Semester
from app.schemas.semester import SemesterWithStats
from datetime import datetime

db = SessionLocal()
current_date = datetime.now().date()

semesters = db.query(Semester).filter(
    Semester.end_date >= current_date
).order_by(Semester.start_date.desc()).limit(3).all()

print(f"Found {len(semesters)} semesters")

semester_stats = []
for semester in semesters:
    print(f"\nProcessing: {semester.code}")
    print(f"  status: {semester.status} (type: {type(semester.status)})")
    
    try:
        # Try to create SemesterWithStats object
        sem_with_stats = SemesterWithStats(
            **semester.__dict__,
            total_groups=0,
            total_sessions=0,
            total_bookings=0,
            active_users=0
        )
        print(f"  ✅ Serialization successful")
        semester_stats.append(sem_with_stats)
    except Exception as e:
        print(f"  ❌ Serialization failed: {e}")
        import traceback
        traceback.print_exc()

print(f"\n✅ Total successfully serialized: {len(semester_stats)}")

db.close()
