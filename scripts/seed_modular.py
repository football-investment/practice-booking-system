#!/usr/bin/env python3
"""
Modular Data-Driven Database Seeder

Supports loading data from multiple modular JSON files.

Usage:
    # Single fixture (backward compatible)
    DATABASE_URL="postgresql://..." python scripts/seed_modular.py --fixture=seed_data_simple

    # Modular approach (load specific components)
    DATABASE_URL="postgresql://..." python scripts/seed_modular.py --modules users locations tournaments_simple

    # Mix and match
    DATABASE_URL="postgresql://..." python scripts/seed_modular.py --modules users locations tournaments_full coupons

Features:
    ✅ Load only what you need
    ✅ Mix different tournament configs (simple vs full workflow)
    ✅ Faster iteration during testing
    ✅ Backward compatible with single-file fixtures
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base
from app.models.user import User
from app.models.location import Location
from app.models.campus import Campus
from app.models.semester import Semester
from app.models.license import UserLicense
from app.models.coupon import Coupon
from app.core.security import get_password_hash


def load_seed_data(fixture_name: str = "seed_data") -> Dict[str, Any]:
    """Load seed data from JSON file"""
    json_path = project_root / "tests" / "playwright" / "fixtures" / f"{fixture_name}.json"

    if not json_path.exists():
        raise FileNotFoundError(f"Seed data file not found: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_modular_data(module_names: List[str], skip_players: bool = False) -> Dict[str, Any]:
    """
    Load and merge data from multiple modular JSON files.

    Args:
        module_names: List of module names to load (e.g., ['users', 'locations', 'tournaments_simple'])
        skip_players: If True, skip seeding student/player users (for E2E tests that create users via UI)

    Returns:
        Merged data dictionary with all loaded entities
    """
    merged_data = {
        "users": [],
        "locations": [],
        "tournaments": [],
        "semesters": [],
        "coupons": []
    }

    for module in module_names:
        json_path = project_root / "tests" / "playwright" / "fixtures" / f"{module}.json"

        if not json_path.exists():
            print(f"   ⚠️  Module '{module}.json' not found, skipping")
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            module_data = json.load(f)

        # Handle nested users structure (tournament_test_data.json format)
        if "users" in module_data and isinstance(module_data["users"], dict):
            # Nested format: {"users": {"admins": [...], "instructors": [...], "players": [...]}}
            users_nested = module_data["users"]
            flat_users = []
            flat_users.extend(users_nested.get("admins", []))
            flat_users.extend(users_nested.get("instructors", []))

            # Conditionally skip players (for E2E tests where Playwright creates users via UI)
            if not skip_players:
                flat_users.extend(users_nested.get("players", []))
            else:
                players_count = len(users_nested.get("players", []))
                if players_count > 0:
                    print(f"   ⚠️  Skipping {players_count} players (will be created by Playwright tests)")

            merged_data["users"].extend(flat_users)
        elif "users" in module_data and isinstance(module_data["users"], list):
            # Flat format: {"users": [...]}
            merged_data["users"].extend(module_data["users"])

        # Merge other entity types (locations, tournaments, coupons)
        for key in ["locations", "tournaments", "semesters", "coupons"]:
            if key in module_data:
                merged_data[key].extend(module_data[key])

        print(f"   ✅ Loaded module: {module}.json")

    return merged_data


def seed_users(db, users_data: List[Dict]) -> Dict[str, User]:
    """Create users from JSON, returns email->User map for FK resolution"""
    print(f"\n📊 Creating {len(users_data)} users...")
    user_map = {}

    for user_data in users_data:
        email = user_data["email"]

        # Check if user exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"   ⚠️  User {email} already exists, skipping")
            user_map[email] = existing
            continue

        # Create user
        user = User(
            email=email,
            password_hash=get_password_hash(user_data["password"]),
            name=user_data["name"],
            role=user_data["role"],
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )

        # Add optional STUDENT fields
        if user_data["role"] == "STUDENT":
            user.first_name = user_data.get("first_name")
            user.last_name = user_data.get("last_name")
            user.nickname = user_data.get("nickname")
            user.phone = user_data.get("phone")
            user.specialization = user_data.get("specialization")
            user.onboarding_completed = user_data.get("onboarding_completed", False)

            # Date of birth
            if "date_of_birth" in user_data:
                user.date_of_birth = datetime.strptime(user_data["date_of_birth"], "%Y-%m-%d").date()

            # Address
            if "address" in user_data:
                addr = user_data["address"]
                user.street_address = addr.get("street")
                user.city = addr.get("city")
                user.postal_code = addr.get("postal_code")
                user.country = addr.get("country")

        db.add(user)
        db.flush()  # Get user.id

        # Create licenses for instructors
        if "licenses" in user_data:
            for lic_data in user_data["licenses"]:
                license = UserLicense(
                    user_id=user.id,
                    specialization_type=lic_data["specialization_type"],
                    current_level=lic_data["current_level"],
                    max_achieved_level=lic_data["current_level"],
                    is_active=lic_data.get("is_active", True),
                    started_at=datetime.now(timezone.utc)
                )
                db.add(license)

        # Create LFA Player license with onboarding data for students
        if user_data["role"] == "STUDENT" and user_data.get("specialization") == "LFA_FOOTBALL_PLAYER":
            # Calculate average skill level
            onboarding = user_data.get("onboarding_data", {})
            skills = onboarding.get("skills", {})

            if skills:
                skill_values = [
                    skills.get("heading", 5),
                    skills.get("shooting", 5),
                    skills.get("passing", 5),
                    skills.get("dribbling", 5),
                    skills.get("defending", 5),
                    skills.get("physical", 5)
                ]
                average_skill = sum(skill_values) / len(skill_values)
            else:
                average_skill = 5.0

            # Build motivation_scores JSON
            motivation_scores = None
            if onboarding:
                motivation_scores = {
                    "position": onboarding.get("position"),
                    "goals": onboarding.get("goals", ""),
                    "motivation": onboarding.get("motivation", ""),
                    "initial_self_assessment": skills,
                    "average_skill_level": round(average_skill, 1),
                    "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
                }

            # Create license
            student_license = UserLicense(
                user_id=user.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                current_level=1,
                max_achieved_level=1,
                is_active=True,
                started_at=datetime.now(timezone.utc),
                onboarding_completed=user_data.get("onboarding_completed", False),
                onboarding_completed_at=datetime.now(timezone.utc) if user_data.get("onboarding_completed") else None,
                motivation_scores=motivation_scores
            )
            db.add(student_license)

        user_map[email] = user
        print(f"   ✅ Created {user.role}: {email}")

    db.commit()
    print(f"✅ Users created: {len(user_map)}")
    return user_map


def seed_locations(db, locations_data: List[Dict]) -> Dict[str, tuple]:
    """Create locations and campuses, returns 'Location::Campus'->tuple map"""
    print(f"\n📍 Creating {len(locations_data)} locations...")
    location_campus_map = {}

    for loc_data in locations_data:
        loc_name = loc_data["name"]

        # Check if location exists
        existing_loc = db.query(Location).filter(Location.name == loc_name).first()
        if existing_loc:
            print(f"   ⚠️  Location '{loc_name}' already exists, skipping")
            location = existing_loc
        else:
            location = Location(
                name=loc_name,
                city=loc_data.get("city"),
                country=loc_data.get("country", "Hungary"),
                address=loc_data.get("address"),
                is_active=True
            )
            db.add(location)
            db.flush()
            print(f"   ✅ Created location: {loc_name}")

        # Create campuses
        for campus_data in loc_data.get("campuses", []):
            campus_name = campus_data["name"]

            # Check if campus exists
            existing_campus = db.query(Campus).filter(
                Campus.location_id == location.id,
                Campus.name == campus_name
            ).first()

            if existing_campus:
                print(f"      ⚠️  Campus '{campus_name}' already exists")
                campus = existing_campus
            else:
                campus = Campus(
                    location_id=location.id,
                    name=campus_name,
                    address=campus_data.get("address"),
                    is_active=True
                )
                db.add(campus)
                db.flush()
                print(f"      ✅ Created campus: {campus_name}")

            # Store mapping for FK resolution
            key = f"{loc_name}::{campus_name}"
            location_campus_map[key] = (location, campus)

    db.commit()
    print(f"✅ Locations created: {len(locations_data)}")
    return location_campus_map


def seed_semesters(db, semesters_data: List[Dict]) -> Dict[str, Semester]:
    """Create semesters, returns name->Semester map"""
    print(f"\n📅 Creating {len(semesters_data)} semesters...")
    semester_map = {}

    for sem_data in semesters_data:
        sem_name = sem_data["name"]

        # Check if semester exists
        existing = db.query(Semester).filter(Semester.name == sem_name).first()
        if existing:
            print(f"   ⚠️  Semester '{sem_name}' already exists, skipping")
            semester_map[sem_name] = existing
            continue

        semester = Semester(
            code=sem_data.get("code", sem_name.upper().replace(" ", "-")),
            name=sem_name,
            specialization_type=sem_data["specialization_type"],
            start_date=datetime.strptime(sem_data["start_date"], "%Y-%m-%d").date(),
            end_date=datetime.strptime(sem_data["end_date"], "%Y-%m-%d").date(),
            enrollment_cost=sem_data.get("enrollment_cost", 0),
            is_active=sem_data.get("is_active", True)
        )

        db.add(semester)
        db.flush()

        semester_map[sem_name] = semester
        print(f"   ✅ Created semester: {sem_name}")

    db.commit()
    print(f"✅ Semesters created: {len(semester_map)}")
    return semester_map


def seed_tournaments(db, tournaments_data: List[Dict], user_map: Dict[str, User], location_campus_map: Dict[str, tuple]) -> List[Semester]:
    """Create tournaments with FK resolution"""
    print(f"\n🏆 Creating {len(tournaments_data)} tournaments...")
    tournaments = []

    for tour_data in tournaments_data:
        tour_name = tour_data["name"]

        # Check if tournament exists
        existing = db.query(Semester).filter(Semester.name == tour_name).first()
        if existing:
            print(f"   ⚠️  Tournament '{tour_name}' already exists, skipping")
            tournaments.append(existing)
            continue

        # Resolve location + campus FK
        loc_name = tour_data["location"]
        campus_name = tour_data["campus"]
        key = f"{loc_name}::{campus_name}"

        if key not in location_campus_map:
            print(f"   ❌ ERROR: Location/Campus not found: {key}")
            continue

        location, campus = location_campus_map[key]

        # Resolve instructor FK (optional)
        master_instructor_id = None
        if tour_data.get("assigned_instructor_email"):
            instructor_email = tour_data["assigned_instructor_email"]
            if instructor_email in user_map:
                master_instructor_id = user_map[instructor_email].id
            else:
                print(f"   ⚠️  Instructor '{instructor_email}' not found")

        # Create tournament
        tournament = Semester(
            code=tour_data.get("code", tour_name.upper().replace(" ", "-")[:50]),
            name=tour_name,
            specialization_type="LFA_FOOTBALL_PLAYER",
            start_date=datetime.strptime(tour_data["start_date"], "%Y-%m-%d").date(),
            end_date=datetime.strptime(tour_data["end_date"], "%Y-%m-%d").date(),
            location_id=location.id,
            campus_id=campus.id,
            age_group=tour_data.get("age_group", "YOUTH"),
            max_players=tour_data.get("max_players", 10),
            enrollment_cost=tour_data.get("enrollment_cost", 0),
            # Optional workflow fields
            assignment_type=tour_data.get("assignment_type"),
            tournament_status=tour_data.get("status"),
            master_instructor_id=master_instructor_id,
            is_active=True
        )

        db.add(tournament)
        db.flush()

        tournaments.append(tournament)

        # Log creation
        assignment_info = f", {tour_data.get('assignment_type')}" if tour_data.get("assignment_type") else ""
        status_info = f", {tour_data.get('status')}" if tour_data.get("status") else ""
        print(f"   ✅ Created tournament: {tour_name} ({tour_data.get('age_group', 'YOUTH')}{assignment_info}{status_info})")

    db.commit()
    print(f"✅ Tournaments created: {len(tournaments)}")
    return tournaments


def seed_coupons(db, coupons_data: List[Dict], user_map: Dict[str, User]) -> List[Coupon]:
    """Create coupons with FK resolution"""
    print(f"\n🎟️  Creating {len(coupons_data)} coupons...")
    coupons = []

    for coupon_data in coupons_data:
        code = coupon_data["code"]

        # Check if coupon exists
        existing = db.query(Coupon).filter(Coupon.code == code).first()
        if existing:
            print(f"   ⚠️  Coupon '{code}' already exists, skipping")
            coupons.append(existing)
            continue

        # Resolve assigned_to FK
        assigned_to_user_id = None
        if "assigned_to_email" in coupon_data:
            email = coupon_data["assigned_to_email"]
            if email in user_map:
                assigned_to_user_id = user_map[email].id
            else:
                print(f"   ⚠️  User '{email}' not found, coupon will be unassigned")

        # Map type from JSON (CREDIT) to model (BONUS_CREDITS)
        coupon_type = coupon_data["type"]
        if coupon_type == "CREDIT":
            coupon_type = "BONUS_CREDITS"

        # Create coupon
        coupon = Coupon(
            code=code,
            type=coupon_type,
            discount_value=float(coupon_data["value"]),
            description=coupon_data.get("description", f"{coupon_data['value']} credits"),
            max_uses=coupon_data.get("max_uses", 1),
            current_uses=0,
            is_active=coupon_data.get("is_active", True),
            created_at=datetime.now(timezone.utc)
        )

        db.add(coupon)
        db.flush()

        coupons.append(coupon)
        print(f"   ✅ Created coupon: {code} ({coupon_type}, {coupon_data['value']} credits)")

    db.commit()
    print(f"✅ Coupons created: {len(coupons)}")
    return coupons


def main():
    """Main seeding workflow"""
    import argparse
    parser = argparse.ArgumentParser(description="Seed database from JSON fixture(s)")
    parser.add_argument("--fixture", help="Single JSON fixture name (without .json)")
    parser.add_argument("--modules", nargs="+", help="Modular JSON files to load (e.g., users locations tournaments_simple)")
    parser.add_argument("--skip-players", action="store_true", help="Skip seeding players (for E2E tests where Playwright creates users via UI)")
    args = parser.parse_args()

    # Validate arguments
    if not args.fixture and not args.modules:
        print("❌ ERROR: Must specify either --fixture or --modules")
        print("\nUsage:")
        print("  Single fixture: python scripts/seed_modular.py --fixture=seed_data_simple")
        print("  Modular:        python scripts/seed_modular.py --modules users locations tournaments_simple")
        print("  Skip players:   python scripts/seed_modular.py --modules seed_data --skip-players")
        sys.exit(1)

    print("=" * 80)
    print("🌱 MODULAR DATA-DRIVEN DATABASE SEEDER")
    print("=" * 80)

    if args.skip_players:
        print("\n⚠️  Player seeding disabled - players will be created by Playwright tests")

    # Load JSON (either single fixture or multiple modules)
    if args.modules:
        print(f"\n📖 Loading modular fixtures: {', '.join(args.modules)}...")
        data = load_modular_data(args.modules, skip_players=args.skip_players)
    else:
        print(f"\n📖 Loading {args.fixture}.json...")
        try:
            data = load_seed_data(args.fixture)
        except Exception as e:
            print(f"❌ Failed to load seed data: {e}")
            sys.exit(1)

    print(f"\n✅ Loaded seed data:")
    print(f"   - {len(data.get('users', []))} users")
    print(f"   - {len(data.get('locations', []))} locations")
    print(f"   - {len(data.get('tournaments', []))} tournaments")
    print(f"   - {len(data.get('coupons', []))} coupons")
    if data.get('semesters'):
        print(f"   - {len(data.get('semesters', []))} semesters (optional)")

    # Connect to DB
    print(f"\n🔌 Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Seed in dependency order
        user_map = seed_users(db, data.get("users", []))
        location_campus_map = seed_locations(db, data.get("locations", []))

        # Semesters (optional)
        semester_map = {}
        if data.get("semesters"):
            semester_map = seed_semesters(db, data.get("semesters", []))

        tournaments = seed_tournaments(db, data.get("tournaments", []), user_map, location_campus_map)
        coupons = seed_coupons(db, data.get("coupons", []), user_map)

        print("\n" + "=" * 80)
        print("🎉 DATABASE SEEDING COMPLETE!")
        print("=" * 80)
        print(f"\n✅ Summary:")
        print(f"   - Users: {len(user_map)}")
        print(f"   - Locations: {len(location_campus_map)}")
        if semester_map:
            print(f"   - Semesters: {len(semester_map)}")
        print(f"   - Tournaments: {len(tournaments)}")
        print(f"   - Coupons: {len(coupons)}")

        if args.modules:
            print(f"\n💡 Data loaded from modules: {', '.join(args.modules)}")
        else:
            print(f"\n💡 All data came from: tests/playwright/fixtures/{args.fixture}.json")

        print(f"\n💡 Usage examples:")
        print(f"   Single fixture:   python scripts/seed_modular.py --fixture=seed_data_simple")
        print(f"   Modular (simple): python scripts/seed_modular.py --modules users locations tournaments_simple")
        print(f"   Modular (full):   python scripts/seed_modular.py --modules users locations tournaments_full coupons")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
