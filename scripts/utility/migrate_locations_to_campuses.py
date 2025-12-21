"""
Data Migration: Locations → Campuses
Converts existing flat location data to Location (city) → Campus (venue) hierarchy

BEFORE:
- locations: [
    {id: 1, name: "LFA EC - Budapest", city: "Budapest", venue: "Pest Campus"},
    {id: 2, name: "LFA EC - Budaörs", city: "Budaörs", venue: "Budaörs Campus"}
  ]

AFTER:
- locations: [
    {id: 1, city: "Budapest"},  # City-level
    {id: 2, city: "Budaörs"}    # City-level
  ]
- campuses: [
    {id: 1, location_id: 1, name: "Pest Campus", venue: "Pest Campus"},
    {id: 2, location_id: 2, name: "Budaörs Campus", venue: "Budaörs Campus"}
  ]
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def migrate_locations_to_campuses():
    """
    Migrate existing location data to Location → Campus hierarchy
    """
    db = SessionLocal()

    try:
        print("=" * 60)
        print("LOCATION → CAMPUS DATA MIGRATION")
        print("=" * 60)

        # Step 1: Get all existing locations
        print("\n📍 Step 1: Reading existing locations...")
        locations = db.execute(
            text("SELECT id, name, city, venue, address, notes, is_active FROM locations ORDER BY id")
        ).fetchall()

        print(f"Found {len(locations)} locations:")
        for loc in locations:
            print(f"  - ID {loc.id}: {loc.name} (City: {loc.city}, Venue: {loc.venue})")

        # Step 2: For each location, create a campus entry
        print("\n🏫 Step 2: Creating campus entries...")

        campuses_created = 0

        for loc in locations:
            location_id = loc.id
            campus_name = loc.venue if loc.venue else f"{loc.city} Main Campus"
            venue = loc.venue
            address = loc.address
            notes = loc.notes
            is_active = loc.is_active

            # Check if campus already exists
            existing = db.execute(
                text("SELECT id FROM campuses WHERE location_id = :loc_id AND name = :name"),
                {"loc_id": location_id, "name": campus_name}
            ).fetchone()

            if existing:
                print(f"  ⚠️  Campus '{campus_name}' already exists for location {location_id}")
                continue

            # Insert campus
            result = db.execute(
                text("""
                    INSERT INTO campuses (location_id, name, venue, address, notes, is_active, created_at, updated_at)
                    VALUES (:loc_id, :name, :venue, :address, :notes, :active, NOW(), NOW())
                    RETURNING id
                """),
                {
                    "loc_id": location_id,
                    "name": campus_name,
                    "venue": venue,
                    "address": address,
                    "notes": notes,
                    "active": is_active
                }
            )

            campus_id = result.fetchone()[0]
            campuses_created += 1

            print(f"  ✅ Created campus ID {campus_id}: '{campus_name}' for location {location_id} ({loc.city})")

        # Step 3: Commit transaction
        db.commit()

        print("\n✅ Migration completed successfully!")
        print(f"   - Total campuses created: {campuses_created}")

        # Step 4: Verify results
        print("\n📊 Step 4: Verification...")

        verification = db.execute(
            text("""
                SELECT
                    l.id as location_id,
                    l.city,
                    c.id as campus_id,
                    c.name as campus_name,
                    c.venue
                FROM locations l
                LEFT JOIN campuses c ON l.id = c.location_id
                ORDER BY l.id, c.id
            """)
        ).fetchall()

        print("\nFinal hierarchy:")
        current_location = None
        for row in verification:
            if row.location_id != current_location:
                print(f"\n📍 Location {row.location_id}: {row.city}")
                current_location = row.location_id
            if row.campus_id:
                print(f"   └─ 🏫 Campus {row.campus_id}: {row.campus_name} (Venue: {row.venue})")
            else:
                print(f"   └─ ⚠️  No campuses found!")

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    migrate_locations_to_campuses()
