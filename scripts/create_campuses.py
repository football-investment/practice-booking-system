"""
Script: Create Campuses for Locations

Creates campuses (venues) for each location using district/area names.
Each location gets 3 campuses representing different districts/areas.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.location import Location
from app.models.campus import Campus


# Campus data: location_code -> [(campus_name, venue_description)]
CAMPUS_DATA = {
    "BDPST": [  # Budapest
        ("Buda Campus", "Buda District"),
        ("Pest Campus", "Pest District"),
        ("Óbuda Campus", "Óbuda District"),
    ],
    "MXCTY": [  # Mexico City
        ("Centro Campus", "Central District"),
        ("Norte Campus", "North District"),
        ("Sur Campus", "South District"),
    ],
    "SAOPL": [  # Sao Paulo
        ("Centro Campus", "Central District"),
        ("Zona Norte Campus", "North Zone"),
        ("Zona Sul Campus", "South Zone"),
    ],
    "BERLN": [  # Berlin
        ("Mitte Campus", "Mitte District"),
        ("Charlottenburg Campus", "Charlottenburg District"),
        ("Kreuzberg Campus", "Kreuzberg District"),
    ],
    "LONDN": [  # London
        ("Westminster Campus", "Westminster Borough"),
        ("Camden Campus", "Camden Borough"),
        ("Greenwich Campus", "Greenwich Borough"),
    ],
}


def create_campuses(db: Session, dry_run: bool = True):
    """
    Create campuses for all locations with district names.

    Args:
        db: Database session
        dry_run: If True, rollback changes after creating
    """
    print("=" * 70)
    print("CREATE CAMPUSES: District-based Campus Names")
    print("=" * 70)

    if dry_run:
        print("\n🔍 DRY RUN MODE - Changes will be rolled back")
    else:
        print("\n⚠️  LIVE MODE - Changes will be committed to database")

    print("\n" + "=" * 70)

    created_campuses = []
    skipped_campuses = 0

    for location_code, campus_list in CAMPUS_DATA.items():
        # Find location by code
        location = db.query(Location).filter(
            Location.location_code == location_code
        ).first()

        if not location:
            print(f"\n⚠️  Location '{location_code}' not found! Skipping...")
            continue

        print(f"\n📍 Location: {location.name} (ID: {location.id})")
        print(f"   Creating {len(campus_list)} campuses...")

        for campus_name, venue_desc in campus_list:
            # Check if campus already exists
            existing = db.query(Campus).filter(
                Campus.location_id == location.id,
                Campus.name == campus_name
            ).first()

            if existing:
                print(f"   ⏭️  '{campus_name}' already exists (ID: {existing.id})")
                skipped_campuses += 1
                continue

            # Create campus (without setting id, let database generate it)
            campus = Campus(
                location_id=location.id,
                name=campus_name,
                venue=venue_desc,
                is_active=True
            )

            db.add(campus)

            # Flush to get ID assigned by database
            try:
                db.flush()
                created_campuses.append(campus)
                print(f"   ✅ Created: {campus_name} (ID: {campus.id})")
            except Exception as e:
                print(f"   ❌ Error creating '{campus_name}': {e}")
                db.rollback()
                raise

    # Summary
    print("\n" + "=" * 70)
    print(f"✅ Successfully created {len(created_campuses)} campuses")
    if skipped_campuses > 0:
        print(f"⏭️  Skipped {skipped_campuses} existing campuses")
    print("=" * 70)

    # Show all created campuses grouped by location
    if created_campuses:
        print("\n📋 Created Campuses by Location:")

        # Group by location
        campuses_by_location = {}
        for campus in created_campuses:
            location_id = campus.location_id
            if location_id not in campuses_by_location:
                location = db.query(Location).filter(Location.id == location_id).first()
                campuses_by_location[location_id] = {
                    "location": location,
                    "campuses": []
                }
            campuses_by_location[location_id]["campuses"].append(campus)

        for data in campuses_by_location.values():
            location = data["location"]
            campuses = data["campuses"]
            print(f"\n   {location.name}:")
            for campus in campuses:
                print(f"      • {campus.name} - {campus.venue}")

    # Commit or rollback
    if dry_run:
        print("\n🔄 Rolling back changes (dry-run mode)")
        db.rollback()
    else:
        print("\n💾 Committing changes to database")
        db.commit()

    print("\n" + "=" * 70)
    print("CAMPUS CREATION COMPLETE")
    print("=" * 70)


def verify_campuses(db: Session):
    """Verify that campuses exist for all locations"""
    print("\n" + "=" * 70)
    print("VERIFICATION: Checking campuses for each location")
    print("=" * 70)

    for location_code in CAMPUS_DATA.keys():
        location = db.query(Location).filter(
            Location.location_code == location_code
        ).first()

        if not location:
            print(f"\n❌ {location_code}: Location not found")
            continue

        campuses = db.query(Campus).filter(
            Campus.location_id == location.id
        ).all()

        print(f"\n✅ {location.name} (ID: {location.id})")
        print(f"   Total Campuses: {len(campuses)}")

        if campuses:
            for campus in campuses:
                status = "✅" if campus.is_active else "❌"
                print(f"   {status} {campus.name} (ID: {campus.id})")
                if campus.venue:
                    print(f"      Venue: {campus.venue}")
        else:
            print("   ⚠️  No campuses found")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create campuses with district names")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create campuses (default is dry-run)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing campuses instead of creating new ones"
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.verify:
            verify_campuses(db)
        else:
            create_campuses(db, dry_run=not args.execute)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
