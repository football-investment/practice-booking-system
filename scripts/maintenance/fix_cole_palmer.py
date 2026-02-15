"""Fix Cole Palmer license 33 - apply tournament deltas"""
import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.skill_progression_service import SkillProgressionService
from app.models.license import UserLicense

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

db = Session()
try:
    license = db.query(UserLicense).filter(UserLicense.id == 33).first()
    skill_service = SkillProgressionService(db)

    # Migrate to new format first
    license.football_skills = skill_service._ensure_new_format(license.football_skills or {})

    # Tournament 18: speed: 0.6, agility: 0.4
    license.football_skills = skill_service._apply_skill_delta(license.football_skills, "speed", 0.07, "tournament")
    license.football_skills = skill_service._apply_skill_delta(license.football_skills, "agility", 0.05, "tournament")

    # Tournament 19: stamina: 7.0
    license.football_skills = skill_service._apply_skill_delta(license.football_skills, "stamina", 0.88, "tournament")

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(license, 'football_skills')
    db.commit()

    print(f"✅ License 33 updated: {license.football_skills}")
finally:
    db.close()
