"""
Seed tournament_types table with pre-defined tournament configurations

Run ONCE after running the migration:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" python scripts/seed_tournament_types.py
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.tournament_type import TournamentType


def load_tournament_config(filename: str) -> dict:
    """Load tournament configuration from JSON file"""
    config_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'app',
        'tournament_types',
        filename
    )
    with open(config_path, 'r') as f:
        return json.load(f)


def seed_tournament_types():
    """Seed tournament_types table with pre-defined configurations"""
    db: Session = SessionLocal()

    try:
        print("🚀 Starting tournament types seed...")
        print("="*80)

        # Check if already seeded
        existing_count = db.query(TournamentType).count()
        if existing_count > 0:
            print(f"⚠️  WARNING: {existing_count} tournament types already exist in database")
            response = input("Do you want to re-seed? This will DELETE all existing tournament types. (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Seed cancelled")
                return

            # Delete existing
            db.query(TournamentType).delete()
            db.commit()
            print(f"🗑️  Deleted {existing_count} existing tournament types")

        # Load configurations
        tournament_configs = [
            'league.json',
            'knockout.json',
            'group_knockout.json',
            'swiss.json'
        ]

        created_count = 0

        for config_file in tournament_configs:
            try:
                config = load_tournament_config(config_file)

                tournament_type = TournamentType(
                    code=config['code'],
                    display_name=config['display_name'],
                    description=config['description'],
                    min_players=config['min_players'],
                    max_players=config.get('max_players'),
                    requires_power_of_two=config['requires_power_of_two'],
                    session_duration_minutes=config['session_duration_minutes'],
                    break_between_sessions_minutes=config['break_between_sessions_minutes'],
                    config=config
                )

                db.add(tournament_type)
                created_count += 1
                print(f"✅ Created: {tournament_type.display_name} ({tournament_type.code})")

            except FileNotFoundError:
                print(f"❌ ERROR: Config file not found: {config_file}")
            except json.JSONDecodeError as e:
                print(f"❌ ERROR: Invalid JSON in {config_file}: {e}")
            except Exception as e:
                print(f"❌ ERROR: Failed to create tournament type from {config_file}: {e}")

        # Commit all changes
        db.commit()

        # Summary
        print("\n" + "="*80)
        print("📊 SEED SUMMARY")
        print("="*80)
        print(f"✅ Successfully created: {created_count} tournament types")
        print(f"📝 Total in database: {db.query(TournamentType).count()}")
        print("="*80)

        # Display details
        print("\n🏆 TOURNAMENT TYPES IN DATABASE:")
        print("-"*80)
        for tt in db.query(TournamentType).all():
            print(f"  - {tt.display_name} ({tt.code})")
            print(f"    Players: {tt.min_players}-{tt.max_players if tt.max_players else 'unlimited'}")
            print(f"    Power of 2 required: {tt.requires_power_of_two}")
            print(f"    Session duration: {tt.session_duration_minutes} minutes")
            print()

        print("✅ Tournament types seed complete!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ SEED FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_tournament_types()
