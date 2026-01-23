#!/usr/bin/env python3
"""
Seed Star Players - Isolated Test Data

Creates 4 professional players with complete onboarding:
- Kylian Mbappé
- Lamine Jamal
- Cole Palmer
- Martin Ødegaard

✅ Does NOT modify existing seed data
✅ Complete onboarding (skills, motivation, credits, XP)
✅ Tournament-ready state
✅ Isolated seeding step

Usage:
    DATABASE_URL="postgresql://..." python scripts/seed_star_players.py
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, date
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base
from app.models.user import User
from app.models.license import UserLicense
from app.models.xp_transaction import XPTransaction  # Required for User model relationship
from app.core.security import get_password_hash


# Star Players Data with COMPLETE onboarding (skills + motivation)
STAR_PLAYERS = [
    {
        "email": "kylian.mbappe@f1rstteam.hu",
        "password": "Mbappe2026!",
        "name": "Kylian Mbappé",
        "first_name": "Kylian",
        "last_name": "Mbappé",
        "nickname": "Kyky",
        "date_of_birth": "1998-12-20",
        "phone": "+33612345678",
        "address": {
            "street": "Parc des Princes, Avenue du Parc des Princes",
            "city": "Paris",
            "postal_code": "75016",
            "country": "France"
        },
        "credits": 5000,
        "onboarding_data": {
            "position": "STRIKER",
            "skills": {
                "heading": 8,
                "shooting": 10,
                "passing": 8,
                "dribbling": 10,
                "defending": 4,
                "physical": 9
            },
            "goals": "play_higher_level",
            "motivation": "I want to become the best striker in the world. Speed and precision are my weapons."
        }
    },
    {
        "email": "lamine.jamal@f1rstteam.hu",
        "password": "Lamine2026!",
        "name": "Lamine Yamal",
        "first_name": "Lamine",
        "last_name": "Yamal",
        "nickname": "Lamino",
        "date_of_birth": "2007-07-13",
        "phone": "+34612345678",
        "address": {
            "street": "Camp Nou, Carrer d'Aristides Maillol",
            "city": "Barcelona",
            "postal_code": "08028",
            "country": "Spain"
        },
        "credits": 3000,
        "onboarding_data": {
            "position": "WINGER",
            "skills": {
                "heading": 6,
                "shooting": 8,
                "passing": 9,
                "dribbling": 10,
                "defending": 3,
                "physical": 7
            },
            "goals": "become_professional",
            "motivation": "I dream of playing for Barcelona and making history as the youngest player to shine at the highest level."
        }
    },
    {
        "email": "cole.palmer@f1rstteam.hu",
        "password": "Palmer2026!",
        "name": "Cole Palmer",
        "first_name": "Cole",
        "last_name": "Palmer",
        "nickname": "Cold Palmer",
        "date_of_birth": "2002-05-06",
        "phone": "+44712345678",
        "address": {
            "street": "Stamford Bridge, Fulham Road",
            "city": "London",
            "postal_code": "SW6 1HS",
            "country": "United Kingdom"
        },
        "credits": 4500,
        "onboarding_data": {
            "position": "MIDFIELDER",
            "skills": {
                "heading": 7,
                "shooting": 9,
                "passing": 9,
                "dribbling": 8,
                "defending": 6,
                "physical": 7
            },
            "goals": "play_higher_level",
            "motivation": "Cold under pressure. I thrive in the most crucial moments and want to lead my team to victory."
        }
    },
    {
        "email": "martin.odegaard@f1rstteam.hu",
        "password": "Odegaard2026!",
        "name": "Martin Ødegaard",
        "first_name": "Martin",
        "last_name": "Ødegaard",
        "nickname": "Ødegod",
        "date_of_birth": "1998-12-17",
        "phone": "+47412345678",
        "address": {
            "street": "Emirates Stadium, Hornsey Road",
            "city": "London",
            "postal_code": "N7 7AJ",
            "country": "United Kingdom"
        },
        "credits": 4800,
        "onboarding_data": {
            "position": "MIDFIELDER",
            "skills": {
                "heading": 7,
                "shooting": 8,
                "passing": 10,
                "dribbling": 9,
                "defending": 6,
                "physical": 8
            },
            "goals": "improve_skills",
            "motivation": "As a captain, I want to inspire my teammates and perfect my vision and passing to control every game."
        }
    }
]


def create_star_players():
    """Create star players with complete onboarding"""

    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("🌟 ═══════════════════════════════════════════════════════")
        print("🌟 STAR PLAYERS SEED - Isolated Test Data")
        print("🌟 ═══════════════════════════════════════════════════════\n")

        created_count = 0
        skipped_count = 0

        for player_data in STAR_PLAYERS:
            email = player_data["email"]
            name = player_data["name"]

            # Check if player already exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"⚠️  {name} ({email}) already exists - SKIPPED")
                skipped_count += 1
                continue

            # Create user (basic info only)
            user = User(
                email=email,
                password_hash=get_password_hash(player_data["password"]),
                name=name,
                first_name=player_data["first_name"],
                last_name=player_data["last_name"],
                nickname=player_data["nickname"],
                role="STUDENT",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                date_of_birth=datetime.strptime(player_data["date_of_birth"], "%Y-%m-%d").date(),
                phone=player_data["phone"],
                street_address=player_data["address"]["street"],
                city=player_data["address"]["city"],
                postal_code=player_data["address"]["postal_code"],
                country=player_data["address"]["country"],
                # ✅ Specialization and onboarding status
                specialization="LFA_FOOTBALL_PLAYER",
                onboarding_completed=True,
                # Credits only (NO XP!)
                credit_balance=player_data["credits"]
            )

            db.add(user)
            db.flush()  # Get user.id

            # ✅ COMPLETE ONBOARDING: Skills + Motivation stored in UserLicense
            onboarding = player_data["onboarding_data"]

            # Calculate average skill level (0-100 scale, each skill 0-10 -> multiply by 10)
            skills = onboarding["skills"]
            avg_skill = sum(skills.values()) / len(skills) * 10  # Average of 6 skills * 10

            # Build motivation_scores JSON structure
            motivation_data = {
                "position": onboarding["position"],
                "goals": onboarding["goals"],
                "motivation": onboarding["motivation"],
                "initial_self_assessment": skills,  # The 6 skill ratings
                "average_skill_level": round(avg_skill, 1),
                "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
            }

            # Create active license with skills + motivation
            license = UserLicense(
                user_id=user.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                current_level=1,  # Starting level
                max_achieved_level=1,
                is_active=True,
                onboarding_completed=True,
                onboarding_completed_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                # ✅ SKILLS + MOTIVATION stored here!
                motivation_scores=motivation_data
            )
            db.add(license)

            db.commit()

            onboarding = player_data["onboarding_data"]
            print(f"✅ {name}")
            print(f"   📧 Email: {email}")
            print(f"   🔑 Password: {player_data['password']}")
            print(f"   ⚽ Position: {onboarding['position']}")
            print(f"   🎯 Skills: Shooting={onboarding['skills']['shooting']}, Dribbling={onboarding['skills']['dribbling']}, Passing={onboarding['skills']['passing']}")
            print(f"   💰 Credits: {player_data['credits']}")
            print(f"   💬 Motivation: {onboarding['motivation'][:60]}...")
            print()

            created_count += 1

        print("🌟 ═══════════════════════════════════════════════════════")
        print(f"✅ Created: {created_count} players")
        print(f"⚠️  Skipped: {skipped_count} players (already exist)")
        print("🌟 ═══════════════════════════════════════════════════════")
        print("\n🎮 All players are TOURNAMENT-READY:")
        print("   ✅ Onboarding completed with skills + motivation")
        print("   ✅ Credits loaded (NO XP)")
        print("   ✅ Active LFA_FOOTBALL_PLAYER license")
        print("   ✅ Position + goals assigned")
        print("   ✅ 6 skill categories rated (heading, shooting, passing, dribbling, defending, physical)")
        print("\n🔐 Login Credentials:")
        for player in STAR_PLAYERS:
            print(f"   {player['name']}: {player['email']} / {player['password']}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_star_players()
