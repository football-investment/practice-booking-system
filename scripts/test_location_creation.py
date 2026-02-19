"""
Test Script: Location Creation with Country Codes

Tests the creation of locations with automatic name generation:
Format: 🇭🇺 HU - Budapest

Test cities:
- Hungary, Budapest
- Mexico, Mexico City
- Brazil, Sao Paulo
- Germany, Berlin
- England, London
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.location import Location, LocationType


# Test data: (country, city, country_code, location_code)
TEST_LOCATIONS = [
    ("Hungary", "Budapest", "HU", "BDPST"),
    ("Mexico", "Mexico City", "MX", "MXCTY"),
    ("Brazil", "Sao Paulo", "BR", "SAOPL"),
    ("Germany", "Berlin", "DE", "BERLN"),
    ("England", "London", "GB", "LONDN"),
]


def get_flag_emoji(country_code: str) -> str:
    """Generate flag emoji from country code"""
    if len(country_code) == 2:
        return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)
    return "🌍"


def test_location_creation(db: Session, dry_run: bool = True):
    """
    Test location creation with automatic name generation.

    Args:
        db: Database session
        dry_run: If True, rollback changes after testing
    """
    print("=" * 70)
    print("TEST: Location Creation with Country Codes")
    print("=" * 70)

    if dry_run:
        print("\n🔍 DRY RUN MODE - Changes will be rolled back")
    else:
        print("\n⚠️  LIVE MODE - Changes will be committed to database")

    print("\n" + "=" * 70)

    created_locations = []

    for country, city, country_code, location_code in TEST_LOCATIONS:
        print(f"\n📍 Processing location: {city}, {country}")
        print(f"   Country Code: {country_code}")
        print(f"   Location Code: {location_code}")

        # Check if location already exists by city or location_code
        existing = db.query(Location).filter(
            (Location.location_code == location_code) | (Location.city == city)
        ).first()

        if existing:
            print(f"   ℹ️  Location already exists (ID: {existing.id})")
            print(f"   Current Name: {existing.name}")

            # Update if missing country_code or location_code
            needs_update = False

            if not existing.country_code:
                print(f"   → Adding country_code: {country_code}")
                existing.country_code = country_code
                needs_update = True

            if not existing.location_code:
                print(f"   → Adding location_code: {location_code}")
                existing.location_code = location_code
                needs_update = True

            # Update display name to new format
            flag = get_flag_emoji(country_code)
            new_display_name = f"{flag} {country_code} - {city}"

            if existing.name != new_display_name:
                print(f"   → Updating name: {new_display_name}")
                existing.name = new_display_name
                needs_update = True

            if needs_update:
                db.flush()
                created_locations.append(existing)
                print(f"   ✅ Updated location ID: {existing.id}")
            else:
                print(f"   ✓ No updates needed")

            continue

        # Generate display name: 🇭🇺 HU - Budapest
        flag = get_flag_emoji(country_code)
        display_name = f"{flag} {country_code} - {city}"

        print(f"   Generated Name: {display_name}")

        # Create location (PARTNER type for international locations)
        # Only Budapest should be CENTER, rest are PARTNER
        location_type = LocationType.CENTER if city == "Budapest" else LocationType.PARTNER

        location = Location(
            name=display_name,
            city=city,
            country=country,
            country_code=country_code,
            location_code=location_code,
            location_type=location_type,
            is_active=True
        )

        print(f"   Location Type: {location_type.value}")

        db.add(location)
        db.flush()  # Get ID without committing

        created_locations.append(location)

        print(f"   ✅ Created location ID: {location.id}")
        print(f"   Display Name Property: {location.display_name}")
        print(f"   Flag Emoji: {location.get_country_flag()}")

    # Summary
    print("\n" + "=" * 70)
    print(f"✅ Successfully created {len(created_locations)} locations")
    print("=" * 70)

    # Show all created locations
    if created_locations:
        print("\n📋 Created Locations:")
        for loc in created_locations:
            print(f"   {loc.id}. {loc.name} (Code: {loc.location_code})")

    # Commit or rollback
    if dry_run:
        print("\n🔄 Rolling back changes (dry-run mode)")
        db.rollback()
    else:
        print("\n💾 Committing changes to database")
        db.commit()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


def verify_locations(db: Session):
    """Verify that locations exist and have correct format"""
    print("\n" + "=" * 70)
    print("VERIFICATION: Checking existing locations")
    print("=" * 70)

    for country, city, country_code, location_code in TEST_LOCATIONS:
        location = db.query(Location).filter(
            Location.location_code == location_code
        ).first()

        if location:
            print(f"\n✅ {location_code}: Found")
            print(f"   Name: {location.name}")
            print(f"   Display Name: {location.display_name}")
            print(f"   City: {location.city}")
            print(f"   Country: {location.country}")
            print(f"   Country Code: {location.country_code}")
            print(f"   Location Code: {location.location_code}")
        else:
            print(f"\n❌ {location_code}: Not found")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test location creation with country codes")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create locations (default is dry-run)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing locations instead of creating new ones"
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.verify:
            verify_locations(db)
        else:
            test_location_creation(db, dry_run=not args.execute)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
