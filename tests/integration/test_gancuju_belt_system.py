"""
🥋 GANCUJU BELT SYSTEM - Integration Test
Tests the complete belt promotion workflow
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

# Add app directory to path
sys.path.insert(0, '/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system')

from app.services.specs.gancuju_player import GancujuBeltService
from app.models.user import User
from app.models.license import UserLicense
from app.models.belt_promotion import BeltPromotion

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_gancuju_belt_system():
    """Test complete Gancuju Belt System workflow"""

    print("=" * 80)
    print("🥋 GANCUJU BELT SYSTEM - INTEGRATION TEST")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        # 1. Find Gancuju Player license
        print("1️⃣  Finding Gancuju Player license...")
        license = db.query(UserLicense).filter(
            UserLicense.specialization_type == "GANCUJU_PLAYER"
        ).first()

        if not license:
            print("❌ No Gancuju Player license found!")
            return

        user = db.query(User).filter(User.id == license.user_id).first()
        print(f"✅ Found license ID {license.id} for {user.email}")
        print(f"   Current level: {license.current_level}")
        print()

        # 2. Get instructor (Grandmaster)
        print("2️⃣  Finding instructor...")
        instructor = db.query(User).filter(User.email == "grandmaster@lfa.com").first()
        if not instructor:
            print("❌ Grandmaster instructor not found!")
            return
        print(f"✅ Instructor: {instructor.name} (ID: {instructor.id})")
        print()

        # 3. Initialize service
        print("3️⃣  Initializing GancujuBeltService...")
        belt_service = GancujuBeltService(db)
        print("✅ Service initialized")
        print()

        # 4. Check current belt
        print("4️⃣  Getting current belt status...")
        current_belt = belt_service.get_current_belt(license.id)
        belt_info = belt_service.get_belt_info(current_belt)
        print(f"✅ Current Belt: {belt_info['name']} ({belt_info['color']} Belt)")
        print(f"   Stage: {belt_info['stage']}")
        print()

        # 5. Check if initial belt needs assignment
        existing_promotions = db.query(BeltPromotion).filter(
            BeltPromotion.user_license_id == license.id
        ).count()

        if existing_promotions == 0:
            print("5️⃣  No belt history found - assigning initial belt...")
            initial = belt_service.assign_initial_belt(
                user_license_id=license.id,
                assigned_by=instructor.id,
                notes="Initial belt assignment - Welcome to Gancuju training!"
            )
            db.commit()
            print(f"✅ Initial belt assigned: {initial.to_belt}")
            print(f"   Assigned at: {initial.promoted_at}")
            print()
        else:
            print(f"5️⃣  Belt history exists ({existing_promotions} promotions)")
            print()

        # 6. Get belt history
        print("6️⃣  Getting belt promotion history...")
        history = belt_service.get_belt_history(license.id)
        if history:
            print(f"✅ Found {len(history)} promotion(s):")
            for i, promo in enumerate(history, 1):
                print(f"\n   {i}. {promo['from_belt'] or 'INITIAL'} → {promo['to_belt']}")
                print(f"      Date: {promo['promoted_at'][:10]}")
                print(f"      By: {promo['promoter_name']}")
                if promo['exam_score']:
                    print(f"      Exam: {promo['exam_score']}/100")
                if promo['notes']:
                    print(f"      Notes: {promo['notes']}")
        else:
            print("⚠️  No promotion history found")
        print()

        # 7. Get next belt
        print("7️⃣  Checking next belt...")
        next_belt = belt_service.get_next_belt(current_belt)
        if next_belt:
            next_info = belt_service.get_belt_info(next_belt)
            print(f"✅ Next Belt: {next_info['name']} ({next_info['color']} Belt)")
            print(f"   Stage: {next_info['stage']}")

            # 8. Test promotion (if not at max level)
            print()
            print("8️⃣  Testing belt promotion...")
            print(f"\n   Promoting {user.email} to {next_info['name']}...")

            if True:  # Auto-promote for testing
                promotion = belt_service.promote_to_next_belt(
                    user_license_id=license.id,
                    promoted_by=instructor.id,
                    notes=f"Test promotion to {next_info['name']}",
                    exam_score=92,
                    exam_notes="Excellent technique demonstration"
                )
                db.commit()

                print(f"\n✅ PROMOTION SUCCESSFUL!")
                print(f"   From: {promotion.from_belt}")
                print(f"   To: {promotion.to_belt}")
                print(f"   Date: {promotion.promoted_at}")
                print(f"   Exam Score: {promotion.exam_score}/100")

                # Verify license updated
                db.refresh(license)
                print(f"\n✅ License updated:")
                print(f"   Current Level: {license.current_level}")
                print(f"   Max Achieved: {license.max_achieved_level}")
            else:
                print("⏭️  Skipping promotion")
        else:
            print("🏆 Already at maximum belt (Dragon Wisdom)!")

        print()
        print("=" * 80)
        print("✅ TEST COMPLETE!")
        print("=" * 80)

        # Final summary
        print("\n📊 FINAL STATUS:")
        db.refresh(license)
        final_belt = belt_service.get_current_belt(license.id)
        final_info = belt_service.get_belt_info(final_belt)
        final_history = belt_service.get_belt_history(license.id)

        print(f"   Student: {user.email}")
        print(f"   Current Belt: {final_info['name']} ({final_info['color']})")
        print(f"   Level: {license.current_level}/8")
        print(f"   Total Promotions: {len(final_history)}")

        print("\n🌐 Access Belt Status Page:")
        print(f"   http://localhost:8000/instructor/students/{user.id}/belt-status/{license.id}")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    test_gancuju_belt_system()
