"""
Ferencvárosi TC — Large-Scale Realistic Club Seed
==================================================
Creates a full-size Hungarian football club with 160 players per age group
and 6 completed tournaments in different formats.

Structure:
  - 1 Club:   Ferencvárosi TC (FTC)
  - 4 Teams:  FTC U12 / U15 / U18 / Felnőtt  (160 players each = 640 total)
  - 3 GamePresets seeded if missing: outfield_default, passing_focus, shooting_focus
  - 6 Tournaments (REWARDS_DISTRIBUTED):
      T1: Swiss        — U12   — outfield_default   (64 enrolled)
      T2: Swiss        — U15   — passing_focus       (64 enrolled)
      T3: League       — U18   — outfield_default   (160 enrolled)
      T4: League       — ADULT — shooting_focus     (160 enrolled)
      T5: Group+KO     — U12   — passing_focus      (160 enrolled)
      T6: Group+KO     — ADULT — outfield_default   (160 enrolled)

Idempotent: safe to re-run; skips existing rows.
Set FTC_FORCE_REBUILD=1 to delete & rebuild FTC tournaments from scratch.

Usage:
    PYTHONPATH=. python scripts/seed_ftc_club.py
"""
import os
import sys
import random
from datetime import date, datetime, timedelta
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system",
)

from app.database import SessionLocal
from app.models.club import Club, CsvImportLog
from app.models.team import Team, TeamMember
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import TournamentParticipation, TournamentBadge
from app.models.tournament_type import TournamentType
from app.models.game_preset import GamePreset
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.core.security import get_password_hash
from app.skills_config import get_all_skill_keys
from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_tournament

# ── Constants ────────────────────────────────────────────────────────────────

CLUB_NAME = "Ferencvárosi TC"
CLUB_CODE = "FTC"
PLAYERS_PER_GROUP = 16
SEED_PASSWORD = "FTCtest#2026"
FORCE_REBUILD = os.environ.get("FTC_FORCE_REBUILD", "").strip() in ("1", "true", "yes")

random.seed(42)  # Reproducible placements

FIRST_NAMES = [
    "Ádám", "Bence", "Dávid", "Erik", "Gábor",
    "Hunor", "István", "János", "Kristóf", "László",
    "Márton", "Norbert", "Ödön", "Péter", "Richárd",
    "Sándor", "Tamás", "Viktor", "Zoltán", "Zsolt",
]
LAST_NAMES = [
    "Kovács", "Nagy", "Tóth", "Szabó", "Horváth",
    "Varga", "Kiss", "Molnár", "Fekete", "Papp",
    "Balogh", "Takács", "Juhász", "Farkas", "Lukács",
    "Simon", "Rácz", "Mészáros", "Oláh", "Bíró",
]
POSITIONS = ["STRIKER", "MIDFIELDER", "DEFENDER", "GOALKEEPER"]
GOALS = [
    "improve_skills", "play_higher_level", "become_professional",
    "team_football", "fitness_health", "enjoy_game",
]

# age_group_label → (Semester.age_group, dob_year_range, skill_base)
AGE_GROUP_DEFS = {
    "U12":   ("PRE",    (2012, 2014), 45.0),
    "U15":   ("YOUTH",  (2009, 2011), 53.0),
    "U18":   ("YOUTH",  (2006, 2008), 60.0),
    "ADULT": ("AMATEUR", (1995, 2003), 67.0),
}

TEAM_DEFS = [
    {"name": "FTC U12 Team",      "age_group": "U12"},
    {"name": "FTC U15 Team",      "age_group": "U15"},
    {"name": "FTC U18 Team",      "age_group": "U18"},
    {"name": "FTC Felnőtt Team",  "age_group": "ADULT"},
]

# Tournament definitions (tournament_type looked up by code at runtime)
TOURNAMENT_DEFS = [
    {
        "code": "FTC-SWISS-01-2026",
        "name": "FTC Swiss Cup 2026 — U12",
        "tt_code": "swiss",
        "age_group_label": "U12",
        "max_enroll": 16,
        "preset_code": "outfield_default",
        "start_date": date(2026, 1, 10),
    },
    {
        "code": "FTC-SWISS-02-2026",
        "name": "FTC Swiss Cup 2026 — U15",
        "tt_code": "swiss",
        "age_group_label": "U15",
        "max_enroll": 16,
        "preset_code": "passing_focus",
        "start_date": date(2026, 1, 24),
    },
    {
        "code": "FTC-LEAGUE-01-2026",
        "name": "FTC League Championship 2026 — U18",
        "tt_code": "league",
        "age_group_label": "U18",
        "max_enroll": 16,
        "preset_code": "outfield_default",
        "start_date": date(2026, 2, 7),
    },
    {
        "code": "FTC-LEAGUE-02-2026",
        "name": "FTC League Championship 2026 — Felnőtt",
        "tt_code": "league",
        "age_group_label": "ADULT",
        "max_enroll": 16,
        "preset_code": "shooting_focus",
        "start_date": date(2026, 2, 21),
    },
    {
        "code": "FTC-GK-01-2026",
        "name": "FTC Group+Knockout Cup 2026 — U12",
        "tt_code": "group_knockout",
        "age_group_label": "U12",
        "max_enroll": 16,
        "preset_code": "passing_focus",
        "start_date": date(2026, 3, 7),
    },
    {
        "code": "FTC-GK-02-2026",
        "name": "FTC Group+Knockout Cup 2026 — Felnőtt",
        "tt_code": "group_knockout",
        "age_group_label": "ADULT",
        "max_enroll": 16,
        "preset_code": "outfield_default",
        "start_date": date(2026, 3, 21),
    },
]

# Inline preset definitions (same as seed_game_presets.py — seeded if missing)
_PRESET_DEFS = [
    {
        "code": "outfield_default",
        "name": "Outfield Football (Default)",
        "is_recommended": True,
        "is_locked": False,
        "game_config": {
            "version": "1.0",
            "metadata": {"game_category": "FOOTBALL", "difficulty_level": "intermediate", "min_players": 4},
            "skill_config": {
                "skills_tested": ["ball_control", "dribbling", "finishing", "passing",
                                  "vision", "positioning_off", "sprint_speed", "agility", "stamina"],
                "skill_weights": {
                    "ball_control": 1.2, "dribbling": 1.5, "finishing": 1.4,
                    "passing": 1.3, "vision": 1.1, "positioning_off": 1.1,
                    "sprint_speed": 1.0, "agility": 1.0, "stamina": 0.9,
                },
            },
            "format_config": {}, "simulation_config": {},
        },
    },
    {
        "code": "passing_focus",
        "name": "Passing & Vision Focus",
        "is_recommended": False,
        "is_locked": False,
        "game_config": {
            "version": "1.0",
            "metadata": {"game_category": "FOOTBALL", "difficulty_level": "intermediate", "min_players": 4},
            "skill_config": {
                "skills_tested": ["passing", "vision", "ball_control", "positioning_off", "agility", "stamina"],
                "skill_weights": {
                    "passing": 1.8, "vision": 1.6, "ball_control": 1.4,
                    "positioning_off": 1.3, "agility": 1.0, "stamina": 0.8,
                },
            },
            "format_config": {}, "simulation_config": {},
        },
    },
    {
        "code": "shooting_focus",
        "name": "Finishing & Shooting Focus",
        "is_recommended": False,
        "is_locked": False,
        "game_config": {
            "version": "1.0",
            "metadata": {"game_category": "FOOTBALL", "difficulty_level": "intermediate", "min_players": 4},
            "skill_config": {
                "skills_tested": ["finishing", "sprint_speed", "dribbling", "ball_control", "agility", "positioning_off"],
                "skill_weights": {
                    "finishing": 2.0, "sprint_speed": 1.6, "dribbling": 1.5,
                    "ball_control": 1.2, "agility": 1.1, "positioning_off": 0.9,
                },
            },
            "format_config": {}, "simulation_config": {},
        },
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_presets(db) -> Dict[str, GamePreset]:
    """Ensure outfield_default/passing_focus/shooting_focus exist; return dict."""
    result = {}
    for p in _PRESET_DEFS:
        gp = db.query(GamePreset).filter_by(code=p["code"]).first()
        if not gp:
            gp = GamePreset(
                code=p["code"],
                name=p["name"],
                game_config=p["game_config"],
                is_recommended=p["is_recommended"],
                is_locked=p["is_locked"],
                is_active=True,
            )
            db.add(gp)
            print(f"  Created GamePreset: {p['code']}")
        result[p["code"]] = gp
    db.flush()
    return result


def _get_or_create_user(db, email: str, first: str, last: str,
                        dob: date, phone: str, nickname: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = User(
        name=f"{first} {last}",
        email=email,
        first_name=first,
        last_name=last,
        nickname=nickname,
        password_hash=get_password_hash(SEED_PASSWORD),
        role=UserRole.STUDENT,
        is_active=True,
        date_of_birth=dob,
        nationality="Hungarian",
        gender="Male",
        phone=phone,
        onboarding_completed=True,
        credit_balance=2000,
    )
    db.add(u)
    db.flush()
    return u


def _ensure_lfa_license(db, user: User, skill_base: float, position: str, goals: str) -> UserLicense:
    lic = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
    ).first()
    all_keys = get_all_skill_keys()
    football_skills = {k: skill_base for k in all_keys}
    now = datetime.now()
    motivation_scores = {
        "position": position, "goals": goals, "motivation": "",
        "average_skill_level": skill_base,
        "onboarding_completed_at": now.isoformat(),
    }
    if lic:
        lic.is_active = True
        lic.onboarding_completed = True
        lic.onboarding_completed_at = now
        lic.payment_verified = True
        lic.football_skills = football_skills
        lic.motivation_scores = motivation_scores
        lic.average_motivation_score = skill_base
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
            average_motivation_score=skill_base,
        )
        db.add(lic)
    return lic


def _seed_players(db, team: Team, age_group: str, skill_base: float,
                  dob_years: tuple, count: int = PLAYERS_PER_GROUP) -> List[User]:
    """Create `count` players and add them to `team`. Returns User list."""
    players = []
    ag_key = age_group.lower()
    dob_start = date(dob_years[0], 1, 1)
    dob_range_days = (date(dob_years[1], 12, 31) - dob_start).days

    for i in range(1, count + 1):
        fn = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
        ln = LAST_NAMES[(i - 1) % len(LAST_NAMES)]
        email = f"ftc.{ag_key}.p{i:03d}@ftc-football.test"
        nickname = f"ftc_{ag_key}_{i:03d}"
        phone = f"+363{i:07d}"
        dob = dob_start + timedelta(days=(i * 97) % dob_range_days)
        position = POSITIONS[(i - 1) % len(POSITIONS)]
        goals = GOALS[(i - 1) % len(GOALS)]

        user = _get_or_create_user(db, email, fn, ln, dob, phone, nickname)
        user.onboarding_completed = True
        user.credit_balance = max(user.credit_balance or 0, 2000)
        _ensure_lfa_license(db, user, skill_base, position, goals)

        if not db.query(TeamMember).filter_by(team_id=team.id, user_id=user.id).first():
            role = "CAPTAIN" if i == 1 else "PLAYER"
            db.add(TeamMember(team_id=team.id, user_id=user.id, role=role))

        players.append(user)

    db.flush()
    return players


def _seed_tournament(db, t_def: dict, players: List[User],
                     tt_map: Dict[str, int], presets: Dict[str, GamePreset]) -> dict:
    code = t_def["code"]
    print(f"\n  [{code}] {t_def['name']} …", end=" ", flush=True)

    # Force rebuild: delete existing participation/badge/ranking rows
    sem = db.query(Semester).filter_by(code=code).first()
    if sem and FORCE_REBUILD:
        db.query(TournamentParticipation).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
        db.query(TournamentBadge).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
        db.query(TournamentRanking).filter(TournamentRanking.tournament_id == sem.id).delete(synchronize_session="fetch")
        db.flush()

    # 1. Semester upsert
    if not sem:
        age_label = t_def["age_group_label"]
        sem_age_group = AGE_GROUP_DEFS[age_label][0]
        sem = Semester(
            code=code,
            name=t_def["name"],
            start_date=t_def["start_date"],
            end_date=t_def["start_date"],
            status=SemesterStatus.COMPLETED,
            tournament_status="COMPLETED",
            semester_category=SemesterCategory.TOURNAMENT,
            specialization_type="LFA_FOOTBALL_PLAYER",
            age_group=sem_age_group,
            enrollment_cost=0,
        )
        db.add(sem)
        db.flush()
    else:
        sem.status = SemesterStatus.COMPLETED
        sem.tournament_status = "COMPLETED"
        db.flush()

    # 2. TournamentConfiguration (HEAD_TO_HEAD via tournament_type_id)
    cfg = db.query(TournamentConfiguration).filter_by(semester_id=sem.id).first()
    if not cfg:
        tt_id = tt_map[t_def["tt_code"]]
        db.add(TournamentConfiguration(
            semester_id=sem.id,
            tournament_type_id=tt_id,
            participant_type="INDIVIDUAL",
            max_players=t_def["max_enroll"],
            number_of_rounds=1,
        ))
        db.flush()

    # 3. TournamentRewardConfig — skill_weights from GamePreset
    preset = presets[t_def["preset_code"]]
    skill_weights = preset.game_config["skill_config"]["skill_weights"]
    skill_mappings = [
        {"skill": sk, "weight": w, "enabled": True}
        for sk, w in skill_weights.items()
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
            reward_policy_name=preset.name,
            reward_config=reward_config,
        ))
    else:
        rcfg.reward_config = reward_config
    db.flush()

    # 4. Clean old ranking rows + insert new (idempotent)
    db.query(TournamentParticipation).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentBadge).filter_by(semester_id=sem.id).delete(synchronize_session="fetch")
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == sem.id).delete(synchronize_session="fetch")
    db.flush()

    enrolled = players[: t_def["max_enroll"]]
    shuffled = random.sample(enrolled, len(enrolled))
    n = len(shuffled)
    for rank, player in enumerate(shuffled, 1):
        pts = max(10, 1000 - (rank - 1) * (990 // n))
        db.add(TournamentRanking(
            tournament_id=sem.id,
            user_id=player.id,
            participant_type="INDIVIDUAL",
            rank=rank,
            points=pts,
        ))
    db.flush()

    # 5. Session row for admin UI visibility
    if not db.query(SessionModel).filter_by(semester_id=sem.id).first():
        d = t_def["start_date"]
        db.add(SessionModel(
            title=f"{t_def['name']} — Match Day",
            date_start=datetime(d.year, d.month, d.day, 10, 0),
            date_end=datetime(d.year, d.month, d.day, 18, 0),
            semester_id=sem.id,
            event_category=EventCategory.MATCH,
        ))
    db.commit()

    # 6. Distribute rewards (EMA computation)
    result = distribute_rewards_for_tournament(
        db=db,
        tournament_id=sem.id,
        force_redistribution=True,
    )
    sem.tournament_status = "REWARDS_DISTRIBUTED"
    db.commit()

    rewarded = len(result.rewards_distributed) if result.rewards_distributed else 0
    print(f"✅  ({rewarded} rewards distributed)")
    return {"code": code, "sem_id": sem.id, "rewarded": rewarded, "enrolled": n}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("⚽  Ferencvárosi TC — Large-Scale Club Seed")
    print("=" * 60)
    if FORCE_REBUILD:
        print("⚠️  FTC_FORCE_REBUILD=1 — existing FTC tournament data will be wiped\n")

    db = SessionLocal()
    try:
        # ── Force rebuild: remove excess FTC team members (keep users, just detach) ─
        if FORCE_REBUILD:
            print("0. Resetting FTC team memberships …")
            from sqlalchemy import text as _text
            # Remove all team_members for FTC teams — re-seeded with 16 below
            deleted = db.execute(_text(
                "DELETE FROM team_members WHERE team_id IN "
                "(SELECT t.id FROM teams t JOIN clubs c ON t.club_id = c.id WHERE c.code = 'FTC')"
            )).rowcount
            db.commit()
            print(f"   Removed {deleted} old team memberships (users remain in DB)")

        # ── Game Presets ──────────────────────────────────────────────────────
        print("1. Seeding game presets …")
        presets = _seed_presets(db)
        db.commit()
        print(f"   Presets ready: {list(presets.keys())}")

        # ── TournamentType lookup ─────────────────────────────────────────────
        tt_map: Dict[str, int] = {}
        for code in ("swiss", "league", "group_knockout"):
            tt = db.query(TournamentType).filter_by(code=code).first()
            if not tt:
                raise RuntimeError(
                    f"TournamentType '{code}' not found in DB. "
                    "Run seed_tournament_types.py first."
                )
            tt_map[code] = tt.id
        print(f"   TournamentTypes: { {k: v for k, v in tt_map.items()} }")

        # ── Club ──────────────────────────────────────────────────────────────
        print("\n2. Creating club …")
        club = db.query(Club).filter_by(code=CLUB_CODE).first()
        if not club:
            club = Club(
                name=CLUB_NAME,
                code=CLUB_CODE,
                city="Budapest",
                country="HU",
                contact_email="info@ftc-football.test",
                is_active=True,
            )
            db.add(club)
            db.flush()
            print(f"   Created: {CLUB_NAME} (id={club.id})")
        else:
            print(f"   Exists: {CLUB_NAME} (id={club.id})")
        db.commit()

        # ── Teams + Players ───────────────────────────────────────────────────
        print(f"\n3. Creating teams & players ({PLAYERS_PER_GROUP} per group) …")
        group_players: Dict[str, List[User]] = {}

        for tdef in TEAM_DEFS:
            ag_key = tdef["age_group"]
            sem_age_group, dob_years, skill_base = AGE_GROUP_DEFS[ag_key]

            team = db.query(Team).filter(
                Team.club_id == club.id,
                Team.name == tdef["name"],
            ).first()
            if not team:
                team = Team(
                    name=tdef["name"],
                    club_id=club.id,
                    age_group_label=ag_key,
                    is_active=True,
                )
                db.add(team)
                db.flush()
                print(f"   Created team: {tdef['name']} (id={team.id})", end=" … ")
            else:
                print(f"   Exists: {tdef['name']} (id={team.id})", end=" … ")

            players = _seed_players(db, team, ag_key, skill_base, dob_years)
            group_players[ag_key] = players
            db.commit()
            print(f"{len(players)} players")

        # ── CsvImportLog (cosmetic — shows in club detail page) ───────────────
        if not db.query(CsvImportLog).filter_by(club_id=club.id).first():
            total = sum(len(v) for v in group_players.values())
            db.add(CsvImportLog(
                club_id=club.id,
                filename="ftc_seed.csv",
                total_rows=total,
                rows_created=total,
                rows_updated=0,
                rows_skipped=0,
                rows_failed=0,
                status="DONE",
            ))
            db.commit()

        # ── Tournaments ───────────────────────────────────────────────────────
        print("\n4. Seeding 6 tournaments …")
        results = []
        for t_def in TOURNAMENT_DEFS:
            ag_key = t_def["age_group_label"]
            players = group_players[ag_key]
            r = _seed_tournament(db, t_def, players, tt_map, presets)
            results.append(r)

        # ── Summary ───────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("✅  FTC Club Seed Complete!\n")
        total_players = sum(len(v) for v in group_players.values())
        print(f"  Club:    {CLUB_NAME} (id={club.id})")
        print(f"  Players: {total_players} total  ({PLAYERS_PER_GROUP} per age group)")
        print()
        print(f"  {'Code':<24}  {'Enrolled':>8}  {'Rewarded':>8}")
        print("  " + "-" * 45)
        for r in results:
            print(f"  {r['code']:<24}  {r['enrolled']:>8}  {r['rewarded']:>8}")
        print()

        # Pick one player per age group for verification links
        print("  Verify (sample profile links):")
        for ag_key, players in group_players.items():
            uid = players[0].id
            print(f"    {ag_key:6s}: http://localhost:8000/admin/users/{uid}/profile")
        print()
        print(f"  Club detail:  http://localhost:8000/admin/clubs/{club.id}")
        print(f"  Tournaments:  http://localhost:8000/admin/tournaments")

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
