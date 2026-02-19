#!/usr/bin/env python3
"""
Test License Authorization Service
===================================
Tests the license authorization logic for Grand Master.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.models.user import User
from app.services.license_authorization_service import LicenseAuthorizationService

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def test_grand_master_authorization():
    """
    Test Grand Master's authorization for various scenarios.
    """
    session = Session()

    try:
        print("=" * 80)
        print("LICENSE AUTHORIZATION TEST - GRAND MASTER")
        print("=" * 80)
        print()

        # Get Grand Master
        grand_master = session.query(User).filter(
            User.email == "grandmaster@lfa.com"
        ).first()

        if not grand_master:
            print("❌ Grand Master not found!")
            return

        print(f"👤 Testing authorization for: {grand_master.name} (ID: {grand_master.id})")
        print()

        # Test scenarios
        scenarios = [
            # LFA PLAYER scenarios
            {
                "name": "LFA PLAYER PRE Semester",
                "specialization": "LFA_PLAYER_PRE",
                "age_group": "PRE"
            },
            {
                "name": "LFA PLAYER YOUTH Semester",
                "specialization": "LFA_PLAYER_YOUTH",
                "age_group": "YOUTH"
            },
            {
                "name": "LFA PLAYER AMATEUR Semester",
                "specialization": "LFA_PLAYER_AMATEUR",
                "age_group": "AMATEUR"
            },
            {
                "name": "LFA PLAYER PRO Semester",
                "specialization": "LFA_PLAYER_PRO",
                "age_group": "PRO"
            },
            # GānCuju PLAYER scenarios
            {
                "name": "GANCUJU PLAYER PRE Semester",
                "specialization": "GANCUJU_PLAYER_PRE",
                "age_group": "PRE"
            },
            {
                "name": "GANCUJU PLAYER YOUTH Semester",
                "specialization": "GANCUJU_PLAYER_YOUTH",
                "age_group": "YOUTH"
            },
            # COACH scenarios
            {
                "name": "LFA COACH PRE Semester",
                "specialization": "LFA_COACH_PRE",
                "age_group": "PRE"
            },
            {
                "name": "LFA COACH PRO Semester",
                "specialization": "LFA_COACH_PRO",
                "age_group": "PRO"
            },
            # INTERNSHIP scenarios
            {
                "name": "INTERNSHIP Semester",
                "specialization": "INTERNSHIP",
                "age_group": None
            }
        ]

        print("📋 TEST SCENARIOS:")
        print("=" * 80)
        print()

        for scenario in scenarios:
            print(f"🔍 Scenario: {scenario['name']}")
            print(f"   Specialization: {scenario['specialization']}")
            print(f"   Age Group: {scenario['age_group'] or 'N/A'}")

            # Test authorization
            result = LicenseAuthorizationService.can_be_master_instructor(
                instructor=grand_master,
                semester_specialization=scenario['specialization'],
                semester_age_group=scenario['age_group'],
                db=session
            )

            if result['authorized']:
                print(f"   ✅ AUTHORIZED")
                print(f"   Reason: {result['reason']}")
                if result['matching_licenses']:
                    print(f"   Matching Licenses ({len(result['matching_licenses'])}):")
                    for lic in result['matching_licenses']:
                        print(f"      - {lic.specialization_type} Level {lic.current_level} (Active: {lic.is_active})")
            else:
                print(f"   ❌ NOT AUTHORIZED")
                print(f"   Reason: {result['reason']}")

            print()

        print("=" * 80)
        print("TEST SCENARIOS COMPLETED")
        print("=" * 80)
        print()

        # Additional tests: Session teaching
        print("=" * 80)
        print("SESSION TEACHING AUTHORIZATION")
        print("=" * 80)
        print()

        session_scenarios = [
            {
                "name": "PLAYER PRE Session",
                "specialization": "LFA_PLAYER_PRE",
                "is_mixed": False
            },
            {
                "name": "COACH YOUTH Session",
                "specialization": "LFA_COACH_YOUTH",
                "is_mixed": False
            },
            {
                "name": "Mixed Session (All Specializations)",
                "specialization": None,
                "is_mixed": True
            },
            {
                "name": "INTERNSHIP Session",
                "specialization": "INTERNSHIP",
                "is_mixed": False
            }
        ]

        for scenario in session_scenarios:
            print(f"🔍 Session: {scenario['name']}")

            result = LicenseAuthorizationService.can_teach_session(
                instructor=grand_master,
                session_specialization=scenario['specialization'],
                is_mixed_session=scenario['is_mixed'],
                db=session
            )

            if result['authorized']:
                print(f"   ✅ CAN TEACH")
                print(f"   Reason: {result['reason']}")
            else:
                print(f"   ❌ CANNOT TEACH")
                print(f"   Reason: {result['reason']}")

            print()

        print("=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_grand_master_authorization()
