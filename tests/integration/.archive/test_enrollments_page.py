#!/usr/bin/env python3
"""
Test script to verify /admin/enrollments page logic
"""
import os
os.environ['DATABASE_URL'] = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.semester import Semester
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import SpecializationType
from sqlalchemy.orm import joinedload

print("🔍 Testing /admin/enrollments page logic...")

db: Session = SessionLocal()

try:
    # Get current semester
    current_semester = db.query(Semester).filter(Semester.is_active == True).first()
    print(f"✅ Current semester: {current_semester.name if current_semester else 'None'}")

    # Get all enrollments
    all_enrollments = []
    if current_semester:
        all_enrollments = (
            db.query(SemesterEnrollment)
            .options(
                joinedload(SemesterEnrollment.user),
                joinedload(SemesterEnrollment.user_license),
                joinedload(SemesterEnrollment.semester)
            )
            .filter(SemesterEnrollment.semester_id == current_semester.id)
            .order_by(SemesterEnrollment.requested_at.desc())
            .all()
        )

    print(f"✅ Total enrollments: {len(all_enrollments)}")

    # Group by specialization
    specialization_groups = {}
    for spec_type in SpecializationType:
        spec_enrollments = [e for e in all_enrollments if e.user_license.specialization_type == spec_type.value]

        pending = [e for e in spec_enrollments if e.request_status == EnrollmentStatus.PENDING]
        active = [e for e in spec_enrollments if e.request_status != EnrollmentStatus.PENDING]
        payment_missing = [e for e in active if not e.payment_verified]

        specialization_groups[spec_type.value] = {
            'pending': pending,
            'active': active,
            'payment_missing_count': len(payment_missing),
            'total_count': len(spec_enrollments)
        }

        print(f"\n{spec_type.value}:")
        print(f"  - Pending: {len(pending)}")
        print(f"  - Active: {len(active)}")
        print(f"  - Payment missing: {len(payment_missing)}")

    print("\n✅ Page logic test PASSED")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
