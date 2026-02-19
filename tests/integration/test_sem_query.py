from app.database import SessionLocal
from app.models.semester import Semester
from datetime import datetime

db = SessionLocal()
current_date = datetime.now().date()

print(f"Current date: {current_date}")

semesters = db.query(Semester).filter(
    Semester.end_date >= current_date
).order_by(Semester.start_date.desc()).all()

print(f"Found {len(semesters)} semesters")

for sem in semesters[:3]:
    print(f"  - {sem.id}: {sem.code} | {sem.status} | {sem.start_date} - {sem.end_date}")
    print(f"    __dict__: {sem.__dict__.keys()}")

db.close()
