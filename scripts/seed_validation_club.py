"""
Idempotent seed: create a permanent PROMO_VALIDATION_CLUB with teams, CSV players,
and a promotion tournament.  Safe to run multiple times — skips if already present,
updates profile fields if user already exists.

Usage:
    PYTHONPATH=. python scripts/seed_validation_club.py

Leaves data permanently in the DB — never auto-deleted by test cleanup.

Mirrors the real registration + onboarding data flow:
  - Registration: first_name, last_name, nickname, email, date_of_birth,
                  nationality, gender, phone  (all required in POST /register)
  - Onboarding:   football_skills (29 skills, flat 50.0 baseline),
                  motivation_scores["position"] + ["goals"]
                  (stored by lfa-player/onboarding-web handler)
"""
import os
import sys
import uuid
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")

from app.database import SessionLocal
from app.models.club import Club, CsvImportLog
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.core.security import get_password_hash
from app.skills_config import get_all_skill_keys
from sqlalchemy import text

# Uniform onboarding baseline — tournaments drive skill differences, not age group
# Mirrors DEFAULT_BASELINE = 50.0 in skill_progression_service.py
_SKILL_BASE = 50.0

CLUB_NAME = "PROMO_VALIDATION_CLUB"
CLUB_CODE = "PROMO-VALID"

# age_group_label → canonical Semester.age_group (mirrors _normalize_club_age_group)
_AGE_MAP = {
    "U12": "PRE",
    "U15": "YOUTH",
    "U18": "YOUTH",
    "ADULT": "AMATEUR",
}

# Players spec tuple:
# (first, last, email, dob_str, nationality, gender, phone, nickname, position, goals)
#
# position values: STRIKER | MIDFIELDER | DEFENDER | GOALKEEPER
#   → stored in UserLicense.motivation_scores["position"] (same as onboarding handler)
# goals values: improve_skills | play_higher_level | become_professional |
#               team_football | fitness_health | enjoy_game
#   → stored in UserLicense.motivation_scores["goals"]
# dob_str: YYYY-MM-DD — same validation as POST /register (age 5-120)
TEAMS = [
    {"name": "Validation U12", "age_group": "U12", "players": [
        ("Val", "Alpha12", "val-alpha12@lfa-validation.com",
         "2012-05-15", "Hungarian", "Male",   "+36301234501", "Valpha12",  "MIDFIELDER",  "improve_skills"),
        ("Val", "Beta12",  "val-beta12@lfa-validation.com",
         "2013-02-28", "Hungarian", "Female", "+36301234502", "Vbeta12",   "STRIKER",     "team_football"),
    ]},
    {"name": "Validation U15", "age_group": "U15", "players": [
        ("Val", "Alpha15", "val-alpha15@lfa-validation.com",
         "2009-08-22", "Hungarian", "Male",   "+36301234503", "Valpha15",  "DEFENDER",    "play_higher_level"),
        ("Val", "Beta15",  "val-beta15@lfa-validation.com",
         "2010-11-07", "Hungarian", "Female", "+36301234504", "Vbeta15",   "GOALKEEPER",  "fitness_health"),
    ]},
    {"name": "Validation U18", "age_group": "U18", "players": [
        ("Val", "Alpha18", "val-alpha18@lfa-validation.com",
         "2006-03-10", "Hungarian", "Male",   "+36301234505", "Valpha18",  "STRIKER",     "become_professional"),
        ("Val", "Beta18",  "val-beta18@lfa-validation.com",
         "2007-09-19", "Hungarian", "Female", "+36301234506", "Vbeta18",   "MIDFIELDER",  "improve_skills"),
    ]},
]


def _get_or_create_user(db, email: str, first: str, last: str,
                        dob_str: str, nationality: str, gender: str,
                        phone: str, nickname: str) -> User:
    """Create or upsert user with all registration-required fields.

    Mirrors POST /register which requires: first_name, last_name, nickname,
    email, phone, date_of_birth, nationality, gender.
    Re-runs always update profile fields (idempotent).
    """
    dob = datetime.strptime(dob_str, "%Y-%m-%d")
    u = db.query(User).filter(User.email == email).first()
    if u:
        # Upsert — re-runs keep data fresh
        u.date_of_birth = dob
        u.nationality = nationality
        u.gender = gender
        u.phone = phone
        u.nickname = nickname
        return u
    u = User(
        name=f"{first} {last}",
        email=email,
        first_name=first,
        last_name=last,
        nickname=nickname,
        password_hash=get_password_hash("Validation#123"),
        role=UserRole.STUDENT,
        is_active=True,
        date_of_birth=dob,
        nationality=nationality,
        gender=gender,
        phone=phone,
    )
    db.add(u)
    db.flush()
    return u


def _ensure_lfa_license(db, user: User, position: str, goals: str) -> UserLicense:
    """Create or update an active, onboarding-completed LFA_FOOTBALL_PLAYER license.

    Mirrors the data written by the lfa-player onboarding-web handler:
    - football_skills: flat {key: 50.0} for all 29 skills (get_baseline_skills handles this)
    - motivation_scores: same JSONB structure as onboarding.py ~line 275
    - No CreditTransaction rows needed — direct credit_balance set is correct seed pattern
    """
    lic = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
    ).first()

    all_keys = get_all_skill_keys()
    football_skills = {k: _SKILL_BASE for k in all_keys}
    motivation_scores = {
        "position": position,
        "goals": goals,
        "motivation": "",
        "average_skill_level": _SKILL_BASE,
        "onboarding_completed_at": datetime.now().isoformat(),
    }

    now = datetime.now()
    if lic:
        lic.is_active = True
        lic.onboarding_completed = True
        lic.onboarding_completed_at = now
        lic.payment_verified = True
        lic.football_skills = football_skills
        lic.motivation_scores = motivation_scores
        lic.average_motivation_score = _SKILL_BASE
    else:
        lic = UserLicense(
            user_id=user.id,
            specialization_type="LFA_FOOTBALL_PLAYER",
            current_level=1,
            max_achieved_level=1,
            started_at=now,
            payment_verified=True,
            payment_verified_at=now,
            onboarding_completed=True,
            onboarding_completed_at=now,
            is_active=True,
            football_skills=football_skills,
            motivation_scores=motivation_scores,
            average_motivation_score=_SKILL_BASE,
        )
        db.add(lic)
    return lic


def run():
    db = SessionLocal()
    try:
        # ── Club ──────────────────────────────────────────────────────────────
        club = db.query(Club).filter(Club.name == CLUB_NAME).first()
        if club:
            print(f"Club already exists: id={club.id}  code={club.code}")
        else:
            club = Club(
                name=CLUB_NAME,
                code=CLUB_CODE,
                city="Budapest",
                country="HU",
                contact_email="validation@lfa.com",
                is_active=True,
            )
            db.add(club)
            db.flush()
            print(f"Created club: id={club.id}  code={club.code}")

        # ── Teams + players ───────────────────────────────────────────────────
        for tspec in TEAMS:
            team = db.query(Team).filter(
                Team.club_id == club.id,
                Team.name == tspec["name"],
            ).first()
            if team:
                print(f"  Team exists: {team.name} (id={team.id})")
            else:
                team = Team(
                    name=tspec["name"],
                    club_id=club.id,
                    age_group_label=tspec["age_group"],
                    is_active=True,
                )
                db.add(team)
                db.flush()
                print(f"  Created team: {team.name} (id={team.id})")

            for (first, last, email,
                 dob_str, nationality, gender, phone, nickname,
                 position, goals) in tspec["players"]:

                user = _get_or_create_user(
                    db, email, first, last,
                    dob_str, nationality, gender, phone, nickname,
                )

                # Tournament-ready LFA license with onboarding data
                _ensure_lfa_license(db, user, position, goals)

                # User-level tournament prerequisites
                user.onboarding_completed = True
                user.credit_balance = max(user.credit_balance or 0, 1000)

                existing = db.query(TeamMember).filter(
                    TeamMember.team_id == team.id,
                    TeamMember.user_id == user.id,
                ).first()
                if not existing:
                    db.add(TeamMember(team_id=team.id, user_id=user.id, role="PLAYER"))
                    print(f"    Added player {email}  pos={position}")
                else:
                    print(f"    Player exists: {email}  pos={position}")

        db.flush()

        # ── CSV import log (simulated) ─────────────────────────────────────────
        log = db.query(CsvImportLog).filter(CsvImportLog.club_id == club.id).first()
        if not log:
            log = CsvImportLog(
                club_id=club.id,
                filename="validation_seed.csv",
                total_rows=6,
                rows_created=6,
                rows_updated=0,
                rows_skipped=0,
                rows_failed=0,
                status="DONE",
            )
            db.add(log)
            db.flush()
            print(f"  Created CSV import log: id={log.id}")

        # ── Promotion tournaments (one per age_group) ─────────────────────────
        for age_label, canonical in _AGE_MAP.items():
            teams_for_ag = [
                t for tspec in TEAMS
                if tspec["age_group"] == age_label
                for t in db.query(Team).filter(
                    Team.club_id == club.id,
                    Team.age_group_label == age_label,
                ).all()
            ]
            if not teams_for_ag:
                continue

            tourn_name = f"{CLUB_NAME} Cup 2026 ({age_label})"
            existing_t = db.query(Semester).filter(Semester.name == tourn_name).first()
            if existing_t:
                print(f"  Tournament exists: {tourn_name} (id={existing_t.id}, age_group={existing_t.age_group})")
                continue

            code = f"PROMO-VALID-{age_label}-{uuid.uuid4().hex[:6].upper()}"
            sem = Semester(
                code=code,
                name=tourn_name,
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 3),
                status=SemesterStatus.DRAFT,
                tournament_status="DRAFT",
                semester_category=SemesterCategory.TOURNAMENT,
                specialization_type="LFA_FOOTBALL_PLAYER",
                age_group=canonical,
                enrollment_cost=0,
            )
            db.add(sem)
            db.flush()

            db.add(TournamentConfiguration(
                semester_id=sem.id,
                participant_type="TEAM",
                number_of_rounds=1,
            ))

            for team in teams_for_ag:
                db.add(TournamentTeamEnrollment(
                    semester_id=sem.id,
                    team_id=team.id,
                    is_active=True,
                    payment_verified=True,
                ))
            db.flush()
            print(f"  Created tournament: {tourn_name}  Semester.age_group={canonical}  id={sem.id}")

        db.commit()

        # ── Final DB report ───────────────────────────────────────────────────
        print("\n── DB state ─────────────────────────────────────────────────")
        club = db.query(Club).filter(Club.name == CLUB_NAME).first()
        print(f"Club  id={club.id}  name={club.name}  code={club.code}  active={club.is_active}")

        teams = db.query(Team).filter(Team.club_id == club.id).all()
        for t in teams:
            count = db.query(TeamMember).filter(TeamMember.team_id == t.id).count()
            print(f"  Team id={t.id}  name={t.name}  age_group_label={t.age_group_label}  members={count}")

        sems = db.query(Semester).filter(Semester.name.like(f"{CLUB_NAME}%")).all()
        for s in sems:
            enr_count = db.query(TournamentTeamEnrollment).filter(
                TournamentTeamEnrollment.semester_id == s.id
            ).count()
            print(f"  Tournament id={s.id}  name={s.name}  age_group={s.age_group}  enrollments={enr_count}")

        # Profile field sanity check
        print("\n── Profile field check ──────────────────────────────────────")
        for tspec in TEAMS:
            for row in tspec["players"]:
                email, position = row[2], row[8]
                u = db.query(User).filter(User.email == email).first()
                ul = db.query(UserLicense).filter(
                    UserLicense.user_id == u.id,
                    UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
                ).first()
                ms_pos = (ul.motivation_scores or {}).get("position", "MISSING") if ul else "NO LICENSE"
                print(f"  {email}  dob={u.date_of_birth and u.date_of_birth.strftime('%Y-%m-%d')}  "
                      f"nationality={u.nationality}  gender={u.gender}  "
                      f"motivation_scores.position={ms_pos}")

        print("\n✅ PROMO_VALIDATION_CLUB seeded and permanent in DB.")

    except Exception:
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()
