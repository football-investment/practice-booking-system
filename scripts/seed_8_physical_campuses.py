"""
Seed 8 Physical Campuses for Multi-Venue Tournaments

Creates 8 distinct physical campuses in Budapest to support
distributed tournament logistics (e.g., 64-player Group+Knockout with
2 groups per campus).

Usage:
    python scripts/seed_8_physical_campuses.py

Campuses created:
    1. Óbuda Sports Complex (North)
    2. Pest Central Arena (East)
    3. Buda Athletic Center (West)
    4. Újpest Stadium (Northeast)
    5. Ferencváros Field (South)
    6. Zugló Sports Park (Southeast)
    7. Kispest Training Ground (Southwest)
    8. Angyalföld Community Pitch (Northwest)

All campuses are active and linked to Budapest location.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.campus import Campus
from app.models.location import Location


def seed_8_campuses(db: Session) -> None:
    """Seed 8 physical campuses for multi-venue tournaments."""

    # Get Budapest location (id=1)
    budapest = db.query(Location).filter(Location.city == "Budapest").first()
    if not budapest:
        print("❌ Budapest location not found. Creating...")
        budapest = Location(
            name="Budapest",
            city="Budapest",
            country="Hungary",
            is_active=True,
        )
        db.add(budapest)
        db.commit()
        db.refresh(budapest)

    budapest_id = budapest.id
    print(f"✅ Budapest location found: id={budapest_id}")

    # Define 8 physical campuses (geographically distributed)
    campuses_to_create = [
        {
            "name": "Óbuda Sports Complex",
            "venue": "Field A",
            "address": "Óbuda, District III, Budapest",
            "notes": "North sector - 2 full-size pitches, floodlights",
        },
        {
            "name": "Pest Central Arena",
            "venue": "Arena 1",
            "address": "Pest, District V, Budapest",
            "notes": "East sector - indoor arena, all-weather",
        },
        {
            "name": "Buda Athletic Center",
            "venue": "Training Ground B",
            "address": "Buda, District II, Budapest",
            "notes": "West sector - 3 training pitches, clubhouse",
        },
        {
            "name": "Újpest Stadium",
            "venue": "Main Pitch",
            "address": "Újpest, District IV, Budapest",
            "notes": "Northeast sector - stadium seating, professional grade",
        },
        {
            "name": "Ferencváros Field",
            "venue": "South Pitch",
            "address": "Ferencváros, District IX, Budapest",
            "notes": "South sector - community field, youth facilities",
        },
        {
            "name": "Zugló Sports Park",
            "venue": "Park Field 1",
            "address": "Zugló, District XIV, Budapest",
            "notes": "Southeast sector - 4 parallel pitches, parking",
        },
        {
            "name": "Kispest Training Ground",
            "venue": "Training Pitch A",
            "address": "Kispest, District XIX, Budapest",
            "notes": "Southwest sector - professional training facility",
        },
        {
            "name": "Angyalföld Community Pitch",
            "venue": "Community Field",
            "address": "Angyalföld, District XIII, Budapest",
            "notes": "Northwest sector - public access, artificial turf",
        },
    ]

    created_count = 0
    skipped_count = 0

    for campus_data in campuses_to_create:
        # Check if campus already exists
        existing = db.query(Campus).filter(Campus.name == campus_data["name"]).first()
        if existing:
            print(f"⏭️  Campus '{campus_data['name']}' already exists (id={existing.id})")
            skipped_count += 1
            continue

        # Create new campus
        campus = Campus(
            location_id=budapest_id,
            name=campus_data["name"],
            venue=campus_data["venue"],
            address=campus_data["address"],
            notes=campus_data["notes"],
            is_active=True,
        )
        db.add(campus)
        created_count += 1
        print(f"✅ Created: {campus_data['name']} ({campus_data['venue']})")

    db.commit()

    print("\n" + "="*60)
    print(f"✅ Seeding complete: {created_count} created, {skipped_count} skipped")
    print("="*60)

    # List all active campuses
    all_campuses = db.query(Campus).filter(Campus.is_active == True).order_by(Campus.id).all()
    print(f"\n📍 Total active campuses: {len(all_campuses)}")
    for c in all_campuses:
        print(f"   {c.id:2d}. {c.name:30s} → {c.venue or 'N/A':20s} ({c.address or 'N/A'})")


def main():
    """Main entry point."""
    print("🏟️  Seeding 8 Physical Campuses for Multi-Venue Tournaments")
    print("="*60)

    db = SessionLocal()
    try:
        seed_8_campuses(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    print("\n✅ All done! You now have 8+ physical campuses for distributed tournaments.")


if __name__ == "__main__":
    main()
