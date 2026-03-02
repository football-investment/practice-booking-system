#!/usr/bin/env python3
"""
Test Payment Reference Code System

This script demonstrates the payment code generation and verification workflow:
1. Creates a test enrollment
2. Generates payment code
3. Shows payment instructions
4. Simulates admin verification
"""
import os
os.environ['DATABASE_URL'] = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.semester import Semester
from app.models.user import User
from app.models.license import UserLicense
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from datetime import datetime, timezone

print("🧪 Testing Payment Reference Code System\n")
print("=" * 60)

db: Session = SessionLocal()

try:
    # Get test data
    student = db.query(User).filter(User.email == "junior.intern@lfa.com").first()
    current_semester = db.query(Semester).filter(Semester.is_active == True).first()

    if not student:
        print("❌ Test student not found! Run setup_test_scenarios.py first")
        exit(1)

    if not current_semester:
        print("❌ No active semester found!")
        exit(1)

    print(f"✅ Test Student: {student.name} ({student.email})")
    print(f"✅ Current Semester: {current_semester.name}")
    print()

    # Get student's INTERNSHIP license
    internship_license = db.query(UserLicense).filter(
        UserLicense.user_id == student.id,
        UserLicense.specialization_type == 'INTERNSHIP'
    ).first()

    if not internship_license:
        print("❌ Student has no INTERNSHIP license!")
        exit(1)

    print(f"✅ License Found: INTERNSHIP (ID: {internship_license.id})")
    print()

    # Check if enrollment already exists
    existing_enrollment = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == student.id,
        SemesterEnrollment.semester_id == current_semester.id,
        SemesterEnrollment.user_license_id == internship_license.id
    ).first()

    if existing_enrollment:
        print(f"ℹ️  Enrollment already exists (ID: {existing_enrollment.id})")
        enrollment = existing_enrollment
    else:
        # Create new enrollment
        enrollment = SemesterEnrollment(
            user_id=student.id,
            semester_id=current_semester.id,
            user_license_id=internship_license.id,
            request_status=EnrollmentStatus.PENDING,
            is_active=False,
            payment_verified=False
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        print(f"✅ Created New Enrollment (ID: {enrollment.id})")

    print()
    print("=" * 60)
    print("STEP 1: Generate Payment Code")
    print("=" * 60)

    # Generate payment code
    payment_code = enrollment.set_payment_code()
    db.commit()
    db.refresh(enrollment)

    print(f"\n💳 Payment Reference Code: {payment_code}")
    print(f"   Format breakdown:")
    print(f"   - LFA: Platform identifier")
    print(f"   - INT: Specialization code (INTERNSHIP)")
    print(f"   - S{enrollment.semester_id}: Semester ID")
    print(f"   - {str(enrollment.user_id).zfill(3)}: User ID (zero-padded)")
    print(f"   - Checksum: MD5 hash for validation")

    print()
    print("=" * 60)
    print("STEP 2: Payment Instructions for Student")
    print("=" * 60)

    print(f"""
📄 PAYMENT INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Student: {student.name}
Email: {student.email}
Specialization: Internship Program
Semester: {current_semester.name}

Amount: 50,000 HUF
Bank Account: 12345678-12345678-12345678
Account Holder: LFA Education Center Kft.
Bank: OTP Bank
SWIFT: OTPVHUHB

⚠️  IMPORTANT: Include this EXACT code in the transfer comment:

    {payment_code}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hungarian Instructions:
Kérjük, utalja át a 50,000 HUF összeget a fenti számlaszámra,
és a közleményben PONTOSAN tüntesse fel ezt a kódot:

    {payment_code}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

    print()
    print("=" * 60)
    print("STEP 3: Check Current Payment Status")
    print("=" * 60)
    print(f"\nPayment Verified: {'✅ YES' if enrollment.payment_verified else '❌ NO'}")
    print(f"Request Status: {enrollment.request_status.value.upper()}")
    print(f"Is Active: {'✅ YES' if enrollment.is_active else '❌ NO'}")

    print()
    print("=" * 60)
    print("STEP 4: Admin Can Verify Payment Using Code")
    print("=" * 60)
    print(f"""
Admin Workflow:
1. Receive bank transfer with comment: {payment_code}
2. Go to /admin/enrollments
3. Enter code in "Quick Payment Verification" box
4. Click "Verify Payment"
5. System automatically:
   - Finds the enrollment
   - Marks payment as verified
   - Shows student details
   - Updates enrollment status

API Endpoint: POST /api/v1/semester-enrollments/verify-by-code
Payload: payment_code={payment_code}
""")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"""
✅ Payment code system is ready!

Next Steps:
1. Go to http://localhost:8000/admin/enrollments
2. Test the "Quick Payment Verification" feature
3. Enter this code: {payment_code}
4. Verify it works correctly

Database Records:
- Enrollment ID: {enrollment.id}
- Payment Code: {payment_code}
- Student: {student.name}
- Semester: {current_semester.name}
""")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
