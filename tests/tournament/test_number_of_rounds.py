#!/usr/bin/env python3
"""
Test that SQLAlchemy can read number_of_rounds from database
"""
import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

from app.database import SessionLocal
from app.models.semester import Semester

db = SessionLocal()

tournament = db.query(Semester).filter(Semester.id == 18).first()

if tournament:
    print(f"✅ Tournament ID: {tournament.id}")
    print(f"✅ Tournament Name: {tournament.name}")
    print(f"✅ Format: {tournament.format}")
    print(f"✅ Number of Rounds: {tournament.number_of_rounds}")

    if tournament.number_of_rounds == 3:
        print("\n🎉 SUCCESS: SQLAlchemy correctly read number_of_rounds = 3 from database!")
    else:
        print(f"\n❌ ERROR: Expected number_of_rounds = 3, got {tournament.number_of_rounds}")
else:
    print("❌ Tournament not found")

db.close()
