"""
Seed 6 INDIVIDUAL tournament series for PROMO_VALIDATION_CLUB players.

Each tournament is fully completed with REWARDS_DISTRIBUTED so that:
  - UserLicense.football_skills is updated via EMA delta
  - TournamentParticipation.skill_rating_delta is populated
  - TournamentBadge rows exist (Champion, RunnerUp, Participant, etc.)
  - Admin profile skill chart and public player card show real progression

Idempotent: safe to re-run; deletes and rebuilds participation/badge/ranking
rows each time (does NOT touch other semesters).

Usage:
    PYTHONPATH=. python scripts/seed_skill_progression_tournaments.py
"""
import sys
import os
from datetime import date, datetime

# Allow running from project root with PYTHONPATH=.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import TournamentParticipation, TournamentBadge
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User
from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_tournament


# ── Player emails (PROMO_VALIDATION_CLUB) ───────────────────────────────────
PLAYER_EMAILS = [
    "val-alpha12@lfa-validation.com",   # idx 0 — MIDFIELDER — Rising star
    "val-beta12@lfa-validation.com",    # idx 1 — STRIKER    — Gradual improver
    "val-alpha15@lfa-validation.com",   # idx 2 — DEFENDER   — Flash start, then decline
    "val-beta15@lfa-validation.com",    # idx 3 — GOALKEEPER — Dominant, then inconsistent
    "val-alpha18@lfa-validation.com",   # idx 4 — STRIKER    — Consistent lower mid
    "val-beta18@lfa-validation.com",    # idx 5 — MIDFIELDER — Baseline reference (always last)
]

# ── Tournament series definition ─────────────────────────────────────────────
# placements[i] = final rank of PLAYER_EMAILS[i] in this tournament (1 = best)
TOURNAMENTS = [
    {
        "code": "PROG-T1-2026",
        "name": "LFA Skill Series — Round 1",
        "start_date": date(2026, 1, 15),
        "end_date":   date(2026, 1, 15),
        "skills": [("passing", 2.0), ("ball_control", 1.5), ("vision", 1.0)],
        "placements": [3, 5, 1, 2, 4, 6],
    },
    {
        "code": "PROG-T2-2026",
        "name": "LFA Skill Series — Round 2",
        "start_date": date(2026, 1, 29),
        "end_date":   date(2026, 1, 29),
        "skills": [("dribbling", 2.0), ("agility", 1.5), ("sprint_speed", 1.0)],
        "placements": [2, 4, 3, 1, 5, 6],
    },
    {
        "code": "PROG-T3-2026",
        "name": "LFA Skill Series — Round 3",
        "start_date": date(2026, 2, 8),
        "end_date":   date(2026, 2, 8),
        "skills": [("finishing", 2.0), ("heading", 1.5), ("crossing", 1.0)],
        "placements": [2, 3, 4, 1, 5, 6],
    },
    {
        "code": "PROG-T4-2026",
        "name": "LFA Skill Series — Round 4",
        "start_date": date(2026, 2, 19),
        "end_date":   date(2026, 2, 19),
        "skills": [("positioning_def", 2.0), ("marking", 1.5), ("composure", 1.0)],
        "placements": [1, 3, 4, 2, 5, 6],
    },
    {
        "code": "PROG-T5-2026",
        "name": "LFA Skill Series — Round 5",
        "start_date": date(2026, 3, 5),
        "end_date":   date(2026, 3, 5),
        "skills": [("tactical_awareness", 2.0), ("reactions", 1.5), ("balance", 1.0)],
        "placements": [1, 2, 3, 4, 5, 6],
    },
    {
        "code": "PROG-T6-2026",
        "name": "LFA Skill Series — Grand Final",
        "start_date": date(2026, 3, 15),
        "end_date":   date(2026, 3, 15),
        "skills": [("stamina", 2.0), ("strength", 1.5), ("tackle", 1.0)],
        "placements": [1, 2, 4, 3, 5, 6],
    },
]

MAX_POINTS = 100
POINTS_STEP = 15   # 1st=100, 2nd=85, 3rd=70, 4th=55, 5th=40, 6th=25


def _seed_tournament(db, t_def: dict, players: list[User]) -> dict:
    code = t_def["code"]
    print(f"\n  [{code}] {t_def['name']} …", end=" ", flush=True)

    # 1. Semester — upsert ────────────────────────────────────────────────────
    sem = db.query(Semester).filter(Semester.code == code).first()
    if not sem:
        sem = Semester(
            code=code,
            name=t_def["name"],
            start_date=t_def["start_date"],
            end_date=t_def["end_date"],
            status=SemesterStatus.COMPLETED,
            tournament_status="COMPLETED",
            semester_category=SemesterCategory.TOURNAMENT,
            specialization_type="LFA_FOOTBALL_PLAYER",
            age_group="AMATEUR",
            enrollment_cost=0,
        )
        db.add(sem)
        db.flush()
    else:
        # Ensure status is correct for re-runs
        sem.status = SemesterStatus.COMPLETED
        sem.tournament_status = "COMPLETED"
        db.flush()

    # 2. TournamentConfiguration — upsert ─────────────────────────────────────
    cfg = db.query(TournamentConfiguration).filter_by(semester_id=sem.id).first()
    if not cfg:
        db.add(TournamentConfiguration(
            semester_id=sem.id,
            participant_type="INDIVIDUAL",
            number_of_rounds=1,
        ))
        db.flush()

    # 3. TournamentRewardConfig — upsert ──────────────────────────────────────
    skill_mappings = [
        {"skill": s, "weight": w, "enabled": True}
        for s, w in t_def["skills"]
    ]
    reward_config = {
        "first_place":   {"xp": 500,  "credits": 100},
        "second_place":  {"xp": 300,  "credits": 50},
        "third_place":   {"xp": 200,  "credits": 25},
        "participation": {"xp": 50,   "credits": 0},
        "skill_mappings": skill_mappings,
    }
    rcfg = db.query(TournamentRewardConfig).filter_by(semester_id=sem.id).first()
    if not rcfg:
        db.add(TournamentRewardConfig(
            semester_id=sem.id,
            reward_policy_name="Custom",
            reward_config=reward_config,
        ))
    else:
        rcfg.reward_config = reward_config
    db.flush()

    # 4. Clean up previous run data (idempotency) ─────────────────────────────
    db.query(TournamentParticipation).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentBadge).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == sem.id).delete(synchronize_session="fetch")
    db.flush()

    # 5. TournamentRanking rows ────────────────────────────────────────────────
    for player, placement in zip(players, t_def["placements"]):
        pts = max(0, MAX_POINTS - (placement - 1) * POINTS_STEP)
        db.add(TournamentRanking(
            tournament_id=sem.id,
            user_id=player.id,
            participant_type="INDIVIDUAL",
            rank=placement,
            points=pts,
        ))
    db.flush()

    # 6. Session row (for admin UI visibility) ─────────────────────────────────
    existing_session = db.query(SessionModel).filter_by(semester_id=sem.id).first()
    if not existing_session:
        d = t_def["start_date"]
        db.add(SessionModel(
            title=f"{t_def['name']} — Match Day",
            date_start=datetime(d.year, d.month, d.day, 10, 0),
            date_end=datetime(d.year, d.month, d.day, 12, 0),
            semester_id=sem.id,
            event_category=EventCategory.MATCH,
        ))
    db.commit()

    # 7. distribute_rewards — computes EMA skill delta ─────────────────────────
    result = distribute_rewards_for_tournament(
        db=db,
        tournament_id=sem.id,
        force_redistribution=True,
    )
    # The orchestrator does NOT update tournament_status — do it here
    sem.tournament_status = "REWARDS_DISTRIBUTED"
    db.commit()

    n = len(result.rewards_distributed) if result.rewards_distributed else 0
    print(f"✅  ({n} rewards distributed)")
    return {"code": code, "sem_id": sem.id, "rewards": n}


def main():
    print("🏆 Seeding LFA Skill Series — 6 tournament progression series")
    print("=" * 65)

    db = SessionLocal()
    try:
        # Load players
        players = []
        missing = []
        for email in PLAYER_EMAILS:
            user = db.query(User).filter(User.email == email).first()
            if user:
                players.append(user)
            else:
                missing.append(email)

        if missing:
            print(f"\n❌ Players not found (run seed_validation_club.py first):")
            for e in missing:
                print(f"   • {e}")
            return

        print(f"✅ Found {len(players)} players:")
        for p in players:
            print(f"   • {p.email}  (id={p.id})")

        # Seed each tournament
        results = []
        for t_def in TOURNAMENTS:
            r = _seed_tournament(db, t_def, players)
            results.append(r)

        print("\n" + "=" * 65)
        print("✅ All 6 tournaments seeded successfully!\n")
        print(f"{'Code':<16}  {'Semester ID':>12}  {'Rewards':>8}")
        print("-" * 45)
        for r in results:
            print(f"{r['code']:<16}  {r['sem_id']:>12}  {r['rewards']:>8}")
        print()
        print("Verify with:")
        print("  psql $DATABASE_URL -c \"SELECT code, tournament_status, start_date")
        print("    FROM semesters WHERE code LIKE 'PROG-T%' ORDER BY start_date;\"")
        print()
        print("Admin UI:")
        player_id = players[0].id
        print(f"  http://localhost:8000/admin/users/{player_id}/profile")
        print(f"  http://localhost:8000/players/{player_id}/card")

    except Exception as exc:
        db.rollback()
        print(f"\n❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
