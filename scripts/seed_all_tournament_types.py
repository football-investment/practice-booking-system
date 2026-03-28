"""
Seed All Tournament Types
=========================
Creates 9 REWARDS_DISTRIBUTED tournaments covering every supported
format × participant_type combination.  Visible at /events/{id} and
in the admin tournament list.

Combinations:
  #1  H2H   INDIVIDUAL  league           (2 players)
  #2  H2H   INDIVIDUAL  knockout         (4 players)
  #3  H2H   INDIVIDUAL  group_knockout   (8 players)
  #4  IR    INDIVIDUAL  SCORE_BASED      (4 players)
  #5  H2H   TEAM        league           (3 teams × 2 members)
  #6  H2H   TEAM        knockout         (4 teams × 2 members)
  #7  H2H   TEAM        group_knockout   (8 teams × 2 members)
  #8  IR    TEAM        SCORE_BASED      (3 teams × 2 members)
  #9  H2H   TEAM        league 2-legs    (3 teams × 2 members)

Idempotent: skip already-existing tournaments (matched by code).
Set SATT_FORCE_REBUILD=1 to delete and rebuild from scratch.

Usage:
    PYTHONPATH=. python scripts/seed_all_tournament_types.py
"""
import os
import sys
import random
from datetime import date, datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system",
)

from sqlalchemy.orm import Session as DBSession

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import TournamentParticipation
from app.models.tournament_type import TournamentType
from app.models.game_preset import GamePreset
from app.models.game_configuration import GameConfiguration
from app.models.session import Session as SessionModel, EventCategory
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.core.security import get_password_hash
from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_tournament

# ── Config ────────────────────────────────────────────────────────────────────

FORCE_REBUILD = os.environ.get("SATT_FORCE_REBUILD", "").strip() in ("1", "true", "yes")
BASE_URL = os.environ.get("SATT_BASE_URL", "http://localhost:8000")
random.seed(2026)

REWARD_CONFIG = {
    "first_place":   {"xp": 500, "credits": 100},
    "second_place":  {"xp": 300, "credits": 50},
    "third_place":   {"xp": 200, "credits": 25},
    "participation": {"xp": 50,  "credits": 0},
    "skill_mappings": [],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_user(db: DBSession, email: str, name: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email,
            name=name,
            password_hash=get_password_hash("SATTtest#2026"),
            role=UserRole.STUDENT,
            is_active=True,
            onboarding_completed=True,
            credit_balance=5000,
        )
        db.add(u)
        db.flush()
    return u


def _ensure_license(db: DBSession, user: User) -> UserLicense:
    lic = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.is_active == True,
    ).first()
    if not lic:
        lic = UserLicense(
            user_id=user.id,
            specialization_type="LFA_FOOTBALL_PLAYER",
            started_at=datetime(2025, 1, 1),
            onboarding_completed=True,
            is_active=True,
            payment_verified=True,
        )
        db.add(lic)
        db.flush()
    return lic


def _ensure_players(db: DBSession, prefix: str, count: int) -> List[User]:
    players = []
    for i in range(1, count + 1):
        u = _get_or_create_user(db, f"satt.{prefix}.p{i:02d}@lfa-test.local", f"SATT {prefix} P{i:02d}")
        _ensure_license(db, u)
        players.append(u)
    return players


def _get_or_create_team(db: DBSession, code: str, name: str, members: int = 2) -> Team:
    team = db.query(Team).filter(Team.code == code).first()
    if not team:
        captain = _get_or_create_user(db, f"satt.team.{code.lower()}.cap@lfa-test.local", f"{name} Captain")
        _ensure_license(db, captain)
        team = Team(
            code=code, name=name,
            captain_user_id=captain.id, is_active=True,
        )
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.id, user_id=captain.id, role="CAPTAIN", is_active=True))
        for j in range(2, members + 1):
            pl = _get_or_create_user(
                db,
                f"satt.team.{code.lower()}.m{j}@lfa-test.local",
                f"{name} Member{j}",
            )
            _ensure_license(db, pl)
            db.add(TeamMember(team_id=team.id, user_id=pl.id, role="PLAYER", is_active=True))
        db.flush()
    return team


def _ensure_teams(db: DBSession, prefix: str, count: int, members_per_team: int = 2) -> List[Team]:
    teams = []
    for i in range(1, count + 1):
        code = f"SATT-{prefix}-T{i:02d}"
        name = f"SATT {prefix} Team {i}"
        teams.append(_get_or_create_team(db, code, name, members_per_team))
    return teams


def _get_or_create_preset(db: DBSession) -> GamePreset:
    gp = db.query(GamePreset).filter(GamePreset.code == "satt-default").first()
    if not gp:
        gp = GamePreset(
            code="satt-default",
            name="SATT Default",
            description="Auto-created for seed_all_tournament_types",
            is_active=True,
            game_config={"metadata": {"min_players": 0}, "skills_tested": [], "skill_weights": {}},
        )
        db.add(gp)
        db.flush()
    return gp


def _teardown_tournament(db: DBSession, sem: Semester) -> None:
    """Delete reward/ranking data so we can rebuild cleanly."""
    db.query(TournamentParticipation).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == sem.id).delete(synchronize_session="fetch")
    db.query(GameConfiguration).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentConfiguration).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentRewardConfig).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(SessionModel).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.flush()


def _create_tournament(
    db: DBSession,
    code: str,
    name: str,
    tt_id,            # int or None (None = INDIVIDUAL_RANKING)
    participant_type: str,
    preset: GamePreset,
    *,
    number_of_legs: int = 1,
    track_home_away: bool = False,
    ranking_direction: str = "DESC",
    scoring_type: str = "HEAD_TO_HEAD",
    max_players: int = 32,
    start_date: date = date(2026, 4, 1),
) -> Semester:
    sem = db.query(Semester).filter_by(code=code).first()
    if sem and FORCE_REBUILD:
        _teardown_tournament(db, sem)
    if sem is None:
        sem = Semester(
            code=code, name=name,
            start_date=start_date,
            end_date=start_date,
            status=SemesterStatus.COMPLETED,
            tournament_status="COMPLETED",
            semester_category=SemesterCategory.TOURNAMENT,
            specialization_type="LFA_FOOTBALL_PLAYER",
        )
        db.add(sem)
        db.flush()
    else:
        sem.tournament_status = "COMPLETED"
        db.flush()

    # TournamentConfiguration
    cfg = db.query(TournamentConfiguration).filter_by(semester_id=sem.id).first()
    if not cfg:
        cfg = TournamentConfiguration(
            semester_id=sem.id,
            tournament_type_id=tt_id,
            participant_type=participant_type,
            max_players=max_players,
            number_of_rounds=1,
            parallel_fields=1,
            ranking_direction=ranking_direction,
            scoring_type=scoring_type,
            number_of_legs=number_of_legs,
            track_home_away=track_home_away,
        )
        db.add(cfg)
        db.flush()

    # GameConfiguration
    gcfg = db.query(GameConfiguration).filter_by(semester_id=sem.id).first()
    if not gcfg:
        db.add(GameConfiguration(semester_id=sem.id, game_preset_id=preset.id))
        db.flush()

    # TournamentRewardConfig
    rcfg = db.query(TournamentRewardConfig).filter_by(semester_id=sem.id).first()
    if not rcfg:
        db.add(TournamentRewardConfig(
            semester_id=sem.id,
            reward_policy_name="SATT Default Policy",
            reward_config=REWARD_CONFIG,
        ))
    else:
        rcfg.reward_config = REWARD_CONFIG
    db.flush()

    # Dummy session for admin UI visibility
    if not db.query(SessionModel).filter_by(semester_id=sem.id).first():
        d = start_date
        db.add(SessionModel(
            title=f"{name} — Match Day",
            date_start=datetime(d.year, d.month, d.day, 10, 0),
            date_end=datetime(d.year, d.month, d.day, 18, 0),
            semester_id=sem.id,
            event_category=EventCategory.MATCH,
            is_tournament_game=True,
        ))
        db.flush()

    return sem


def _add_individual_rankings(db: DBSession, sem: Semester, players: List[User]) -> None:
    """Insert TournamentRanking rows for INDIVIDUAL participants."""
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == sem.id).delete(synchronize_session="fetch")
    shuffled = random.sample(players, len(players))
    n = len(shuffled)
    for rank, p in enumerate(shuffled, 1):
        pts = max(10, 1000 - (rank - 1) * (990 // n))
        db.add(TournamentRanking(
            tournament_id=sem.id,
            user_id=p.id,
            participant_type="INDIVIDUAL",
            rank=rank, points=pts,
            wins=max(0, n - rank), losses=rank - 1, draws=0,
        ))
    db.flush()


def _add_team_rankings(db: DBSession, sem: Semester, teams: List[Team]) -> None:
    """Insert TournamentRanking rows for TEAM participants."""
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == sem.id).delete(synchronize_session="fetch")
    shuffled = random.sample(teams, len(teams))
    n = len(shuffled)
    for rank, t in enumerate(shuffled, 1):
        pts = max(10, 1000 - (rank - 1) * (990 // n))
        db.add(TournamentRanking(
            tournament_id=sem.id,
            team_id=t.id,
            user_id=None,
            participant_type="TEAM",
            rank=rank, points=pts,
            wins=max(0, n - rank), losses=rank - 1, draws=0,
        ))
    db.flush()


def _finalize(db: DBSession, sem: Semester) -> int:
    """Distribute rewards and set REWARDS_DISTRIBUTED. Returns reward count."""
    result = distribute_rewards_for_tournament(db=db, tournament_id=sem.id, force_redistribution=True)
    sem.tournament_status = "REWARDS_DISTRIBUTED"
    db.commit()
    return len(result.rewards_distributed) if result.rewards_distributed else 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("⚽  Seed All Tournament Types")
    print("=" * 60)
    if FORCE_REBUILD:
        print("⚠️  SATT_FORCE_REBUILD=1 — rebuilding existing tournaments\n")

    db = SessionLocal()
    try:
        preset = _get_or_create_preset(db)
        db.commit()

        # Look up TournamentTypes by code
        tt: Dict[str, int] = {}
        for code in ("league", "knockout", "group_knockout"):
            obj = db.query(TournamentType).filter_by(code=code).first()
            if not obj:
                raise RuntimeError(
                    f"TournamentType '{code}' not found. Run seed_tournament_types.py first."
                )
            tt[code] = obj.id
        print(f"TournamentTypes: { {k: v for k, v in tt.items()} }\n")

        # Shared players (INDIVIDUAL tournaments)
        ind_players_4 = _ensure_players(db, "ind", 4)
        ind_players_8 = _ensure_players(db, "ind", 8)
        db.commit()

        # Shared teams (TEAM tournaments)
        teams_3 = _ensure_teams(db, "tm3", 3, members_per_team=2)
        teams_4 = _ensure_teams(db, "tm4", 4, members_per_team=2)
        teams_8 = _ensure_teams(db, "tm8", 8, members_per_team=2)
        db.commit()

        results = []

        # ── #1  H2H INDIVIDUAL league ─────────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-01-IND-LEAGUE", "SATT #1 — Individual League",
            tt["league"], "INDIVIDUAL", preset,
            start_date=date(2026, 4, 1),
        )
        _add_individual_rankings(db, sem, ind_players_4[:2])
        rewarded = _finalize(db, sem)
        results.append((1, "H2H / INDIVIDUAL / league", sem.id, rewarded))

        # ── #2  H2H INDIVIDUAL knockout ───────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-02-IND-KNOCKOUT", "SATT #2 — Individual Knockout",
            tt["knockout"], "INDIVIDUAL", preset,
            start_date=date(2026, 4, 3),
        )
        _add_individual_rankings(db, sem, ind_players_4)
        rewarded = _finalize(db, sem)
        results.append((2, "H2H / INDIVIDUAL / knockout", sem.id, rewarded))

        # ── #3  H2H INDIVIDUAL group_knockout ─────────────────────────────────
        sem = _create_tournament(
            db, "SATT-03-IND-GK", "SATT #3 — Individual Group+Knockout",
            tt["group_knockout"], "INDIVIDUAL", preset,
            start_date=date(2026, 4, 5),
        )
        _add_individual_rankings(db, sem, ind_players_8)
        rewarded = _finalize(db, sem)
        results.append((3, "H2H / INDIVIDUAL / group_knockout", sem.id, rewarded))

        # ── #4  IR INDIVIDUAL SCORE_BASED ─────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-04-IND-IR", "SATT #4 — Individual Ranking (Score)",
            None, "INDIVIDUAL", preset,        # tt_id=None → INDIVIDUAL_RANKING
            ranking_direction="DESC",
            scoring_type="SCORE_BASED",
            start_date=date(2026, 4, 7),
        )
        _add_individual_rankings(db, sem, ind_players_4)
        rewarded = _finalize(db, sem)
        results.append((4, "IR / INDIVIDUAL / SCORE_BASED", sem.id, rewarded))

        # ── #5  H2H TEAM league ────────────────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-05-TEAM-LEAGUE", "SATT #5 — Team League",
            tt["league"], "TEAM", preset,
            start_date=date(2026, 4, 9),
        )
        _add_team_rankings(db, sem, teams_3)
        rewarded = _finalize(db, sem)
        results.append((5, "H2H / TEAM / league", sem.id, rewarded))

        # ── #6  H2H TEAM knockout ─────────────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-06-TEAM-KNOCKOUT", "SATT #6 — Team Knockout",
            tt["knockout"], "TEAM", preset,
            start_date=date(2026, 4, 11),
        )
        _add_team_rankings(db, sem, teams_4)
        rewarded = _finalize(db, sem)
        results.append((6, "H2H / TEAM / knockout", sem.id, rewarded))

        # ── #7  H2H TEAM group_knockout ───────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-07-TEAM-GK", "SATT #7 — Team Group+Knockout",
            tt["group_knockout"], "TEAM", preset,
            start_date=date(2026, 4, 13),
        )
        _add_team_rankings(db, sem, teams_8)
        rewarded = _finalize(db, sem)
        results.append((7, "H2H / TEAM / group_knockout", sem.id, rewarded))

        # ── #8  IR TEAM SCORE_BASED ───────────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-08-TEAM-IR", "SATT #8 — Team Ranking (Score)",
            None, "TEAM", preset,             # tt_id=None → INDIVIDUAL_RANKING
            ranking_direction="DESC",
            scoring_type="SCORE_BASED",
            start_date=date(2026, 4, 15),
        )
        _add_team_rankings(db, sem, teams_3)
        rewarded = _finalize(db, sem)
        results.append((8, "IR / TEAM / SCORE_BASED", sem.id, rewarded))

        # ── #9  H2H TEAM league 2-legs ────────────────────────────────────────
        sem = _create_tournament(
            db, "SATT-09-TEAM-LEAGUE-2L", "SATT #9 — Team League 2-Legs",
            tt["league"], "TEAM", preset,
            number_of_legs=2,
            track_home_away=True,
            start_date=date(2026, 4, 17),
        )
        _add_team_rankings(db, sem, teams_3)
        rewarded = _finalize(db, sem)
        results.append((9, "H2H / TEAM / league (2 legs)", sem.id, rewarded))

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"\n✅  Created {len(results)} tournaments (REWARDS_DISTRIBUTED):\n")
        for num, label, sem_id, rewarded in results:
            print(f"  [{num}] {label:<40}  id={sem_id}  rewards={rewarded}")
            print(f"       {BASE_URL}/events/{sem_id}")

        print()

    except Exception as exc:
        db.rollback()
        print(f"\n❌  Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
