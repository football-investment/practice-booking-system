"""
Idempotent seed: create a permanent PROMO_VALIDATION_CLUB with teams, CSV players,
and a promotion tournament.  Safe to run multiple times — skips if already present.

Usage:
    PYTHONPATH=. python scripts/seed_validation_club.py

Leaves data permanently in the DB — never auto-deleted by test cleanup.
"""
import os
import sys
import uuid
from datetime import date

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
from sqlalchemy import text

CLUB_NAME = "PROMO_VALIDATION_CLUB"
CLUB_CODE = "PROMO-VALID"

# age_group_label → canonical Semester.age_group (mirrors _normalize_club_age_group)
_AGE_MAP = {
    "U12": "PRE",
    "U15": "YOUTH",
    "U18": "YOUTH",
    "ADULT": "AMATEUR",
}

TEAMS = [
    {"name": "Validation U12", "age_group": "U12", "players": [
        ("Val", "Alpha12", "val-alpha12@lfa-validation.com"),
        ("Val", "Beta12",  "val-beta12@lfa-validation.com"),
    ]},
    {"name": "Validation U15", "age_group": "U15", "players": [
        ("Val", "Alpha15", "val-alpha15@lfa-validation.com"),
        ("Val", "Beta15",  "val-beta15@lfa-validation.com"),
    ]},
    {"name": "Validation U18", "age_group": "U18", "players": [
        ("Val", "Alpha18", "val-alpha18@lfa-validation.com"),
        ("Val", "Beta18",  "val-beta18@lfa-validation.com"),
    ]},
]


def _get_or_create_user(db, email: str, first: str, last: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = User(
        name=f"{first} {last}",
        email=email,
        first_name=first,
        last_name=last,
        password_hash=get_password_hash("Validation#123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


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

            for first, last, email in tspec["players"]:
                user = _get_or_create_user(db, email, first, last)
                existing = db.query(TeamMember).filter(
                    TeamMember.team_id == team.id,
                    TeamMember.user_id == user.id,
                ).first()
                if not existing:
                    db.add(TeamMember(team_id=team.id, user_id=user.id, role="PLAYER"))
                    print(f"    Added player {email}")

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
            # Only create if there are teams for this age group
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
                age_group=canonical,      # U15 → YOUTH, U12 → PRE, U18 → YOUTH
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
