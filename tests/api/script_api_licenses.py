"""Test API /users/me endpoint for license data"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.license import UserLicense
from sqlalchemy.orm import joinedload

db = SessionLocal()

# Get Kylian Mbappé
user = db.query(User).filter(User.email == "kylian.mbappe@f1rstteam.hu").first()

if user:
    print(f"User ID: {user.id}")
    print(f"Email: {user.email}")
    print(f"Onboarding completed (user): {user.onboarding_completed}")

    # Get licenses
    licenses = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
    ).all()

    print(f"\nTotal licenses: {len(licenses)}")
    for lic in licenses:
        print(f"\n  License ID: {lic.id}")
        print(f"  Specialization: {lic.specialization_type}")
        print(f"  Is active: {lic.is_active}")
        print(f"  Payment verified: {lic.payment_verified}")
        print(f"  Onboarding completed: {lic.onboarding_completed}")

    # Now check what the API serializer returns
    print("\n" + "="*60)
    print("WHAT API SHOULD RETURN:")
    print("="*60)

    # Get the first active license
    active_license = next((l for l in licenses if l.is_active), None)
    if active_license:
        from app.schemas.license import UserLicenseResponse
        from datetime import datetime

        # Simulate API response
        license_dict = {
            "id": active_license.id,
            "specialization_type": active_license.specialization_type,
            "is_active": active_license.is_active,
            "payment_verified": active_license.payment_verified,
            "onboarding_completed": active_license.onboarding_completed,
            "current_level": active_license.current_level,
            "started_at": active_license.started_at.isoformat() if active_license.started_at else None,
        }

        print(f"\nActive license data:")
        for key, value in license_dict.items():
            print(f"  {key}: {value}")
    else:
        print("\n❌ NO ACTIVE LICENSE FOUND!")

db.close()
