"""
EMA V3 Validation — 10 Tournament Seed Script
==============================================
Creates 10 real tournaments in the DB with the existing star players,
using varied compositions, results, and skill mappings so the EMA V3
progression engine can be tested end-to-end via the frontend.

Design principles:
  - 4-5 players per tournament (always different groupings)
  - Varied placements: no player always wins, no player always loses
  - 3 tournament "themes" cycling through different dominant skill weights
  - Spread across ~3 months of calendar time (realistic timestamps)
  - Idempotent: checks for existing code before inserting

Run:
    cd <project_root>
    source venv/bin/activate
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        python scripts/seed_ema_validation_tournaments.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# ── project path ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.semester import Semester, SemesterStatus
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_achievement import (
    TournamentParticipation,
    TournamentSkillMapping,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system",
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# ── Player registry (DB ids confirmed from existing seed) ─────────────────────
PLAYERS = {
    "mbappe":      {"id": 3,  "name": "Kylian Mbappé",             "pos": "STRIKER"},
    "haaland":     {"id": 4,  "name": "Erling Haaland",             "pos": "STRIKER"},
    "messi":       {"id": 5,  "name": "Lionel Messi",               "pos": "MIDFIELDER"},
    "vinicius":    {"id": 6,  "name": "Vinícius Júnior",            "pos": "STRIKER"},
    "bellingham":  {"id": 7,  "name": "Jude Bellingham",            "pos": "MIDFIELDER"},
    "salah":       {"id": 8,  "name": "Mohamed Salah",              "pos": "STRIKER"},
    "foden":       {"id": 9,  "name": "Phil Foden",                 "pos": "MIDFIELDER"},
    "rodri":       {"id": 10, "name": "Rodrigo Hernández",          "pos": "MIDFIELDER"},
    "dias":        {"id": 11, "name": "Rúben Dias",                 "pos": "DEFENDER"},
    "saka":        {"id": 12, "name": "Bukayo Saka",                "pos": "STRIKER"},
}

# ── Skill weight themes ───────────────────────────────────────────────────────
# Each theme tests a different dominant skill so the fairness audit covers
# multiple weight profiles.
THEMES = {
    "ATTACK": {
        "skills": [
            ("finishing",    1.50),   # dominant
            ("dribbling",    0.80),   # supporting
            ("passing",      0.60),   # weak supporting
        ]
    },
    "SPEED": {
        "skills": [
            ("acceleration", 1.50),   # dominant
            ("sprint_speed", 1.20),   # strong supporting
            ("agility",      0.60),   # weak supporting
        ]
    },
    "VISION": {
        "skills": [
            ("vision",       1.50),   # dominant
            ("passing",      1.20),   # strong supporting
            ("tactical_awareness", 0.60),
        ]
    },
    "PHYSICAL": {
        "skills": [
            ("stamina",      1.50),
            ("strength",     1.00),
            ("balance",      0.70),
        ]
    },
    "DEFENSE": {
        "skills": [
            ("tackle",       1.50),
            ("marking",      1.20),
            ("positioning_def", 0.60),
        ]
    },
}

# ── Tournament definitions ────────────────────────────────────────────────────
# Each tournament: code_suffix, name, theme, participants [(key, placement)]
# Placements are carefully crafted:
#   - No player wins all 10
#   - No player loses all 10
#   - Mixed winner from each position type (striker, midfielder, defender)
#   - Some upset results (e.g. Dias/Rodri beating attackers)

BASE_DATE = datetime(2025, 11, 1, 10, 0, 0, tzinfo=timezone.utc)

TOURNAMENTS = [
    {
        "code":    "EMA-VAL-T01",
        "name":    "EMA Validation — T01: Attack Test",
        "theme":   "ATTACK",
        "date":    BASE_DATE + timedelta(weeks=0),
        "players": [
            ("mbappe",    1),
            ("salah",     2),
            ("vinicius",  3),
            ("foden",     4),
            ("bellingham",5),
        ],
    },
    {
        "code":    "EMA-VAL-T02",
        "name":    "EMA Validation — T02: Speed Circuit",
        "theme":   "SPEED",
        "date":    BASE_DATE + timedelta(weeks=2),
        "players": [
            ("vinicius",  1),   # speed specialist wins
            ("mbappe",    2),
            ("salah",     3),
            ("saka",      4),
        ],
    },
    {
        "code":    "EMA-VAL-T03",
        "name":    "EMA Validation — T03: Vision & Passing",
        "theme":   "VISION",
        "date":    BASE_DATE + timedelta(weeks=4),
        "players": [
            ("messi",     1),   # vision specialist wins
            ("bellingham",2),
            ("foden",     3),
            ("rodri",     4),
            ("haaland",   5),
        ],
    },
    {
        "code":    "EMA-VAL-T04",
        "name":    "EMA Validation — T04: Physical Challenge",
        "theme":   "PHYSICAL",
        "date":    BASE_DATE + timedelta(weeks=6),
        "players": [
            ("haaland",   1),   # physical powerhouse
            ("dias",      2),   # defender excels physically
            ("rodri",     3),
            ("mbappe",    4),
            ("messi",     5),
        ],
    },
    {
        "code":    "EMA-VAL-T05",
        "name":    "EMA Validation — T05: Defensive Duel",
        "theme":   "DEFENSE",
        "date":    BASE_DATE + timedelta(weeks=8),
        "players": [
            ("dias",      1),   # defender wins defensive tournament
            ("rodri",     2),
            ("bellingham",3),
            ("saka",      4),
        ],
    },
    {
        "code":    "EMA-VAL-T06",
        "name":    "EMA Validation — T06: All-Stars Attack",
        "theme":   "ATTACK",
        "date":    BASE_DATE + timedelta(weeks=10),
        "players": [
            ("salah",     1),   # different attacker wins
            ("mbappe",    2),
            ("vinicius",  3),
            ("haaland",   4),
            ("saka",      5),
        ],
    },
    {
        "code":    "EMA-VAL-T07",
        "name":    "EMA Validation — T07: Midfield Maestros",
        "theme":   "VISION",
        "date":    BASE_DATE + timedelta(weeks=12),
        "players": [
            ("foden",     1),
            ("bellingham",2),
            ("messi",     3),
            ("rodri",     4),
        ],
    },
    {
        "code":    "EMA-VAL-T08",
        "name":    "EMA Validation — T08: Mixed Challenge",
        "theme":   "SPEED",
        "date":    BASE_DATE + timedelta(weeks=14),
        "players": [
            ("saka",      1),
            ("vinicius",  2),
            ("dias",      3),   # defender in speed test — lower performance
            ("messi",     4),
            ("foden",     5),
        ],
    },
    {
        "code":    "EMA-VAL-T09",
        "name":    "EMA Validation — T09: Consistency Cup",
        "theme":   "PHYSICAL",
        "date":    BASE_DATE + timedelta(weeks=16),
        "players": [
            ("rodri",     1),   # engine midfielder wins physical
            ("bellingham",2),
            ("haaland",   3),
            ("salah",     4),
            ("mbappe",    5),
        ],
    },
    {
        "code":    "EMA-VAL-T10",
        "name":    "EMA Validation — T10: Grand Finale",
        "theme":   "ATTACK",
        "date":    BASE_DATE + timedelta(weeks=18),
        "players": [
            ("messi",     1),   # Messi wins the finale
            ("mbappe",    2),
            ("salah",     3),
            ("vinicius",  4),
            ("haaland",   5),
        ],
    },
]


def get_or_find_tournament_type_id(db, code="league"):
    row = db.execute(
        text("SELECT id FROM tournament_types WHERE code = :c"),
        {"c": code}
    ).fetchone()
    if row:
        return row[0]
    # fallback to first available
    row = db.execute(text("SELECT id FROM tournament_types LIMIT 1")).fetchone()
    return row[0] if row else None


def seed():
    db = Session()
    try:
        tt_id = get_or_find_tournament_type_id(db, "league")
        print(f"Tournament type id (league): {tt_id}")

        created = 0
        skipped = 0

        for t in TOURNAMENTS:
            # Idempotency check
            existing = db.execute(
                text("SELECT id FROM semesters WHERE code = :c"),
                {"c": t["code"]}
            ).fetchone()

            if existing:
                print(f"  SKIP (already exists): {t['code']}")
                skipped += 1
                continue

            # ── 1. Semester ──────────────────────────────────────────────────
            semester = Semester(
                code=t["code"],
                name=t["name"],
                start_date=t["date"].date(),
                end_date=(t["date"] + timedelta(days=1)).date(),
                status=SemesterStatus.COMPLETED,
                is_active=False,
            )
            db.add(semester)
            db.flush()  # get semester.id

            # ── 2. TournamentConfiguration ──────────────────────────────────
            n_players = len(t["players"])
            config = TournamentConfiguration(
                semester_id=semester.id,
                tournament_type_id=tt_id,
                participant_type="INDIVIDUAL",
                max_players=n_players,
                scoring_type="PLACEMENT",
            )
            db.add(config)

            # ── 3. TournamentSkillMapping ────────────────────────────────────
            for skill_name, weight in THEMES[t["theme"]]["skills"]:
                mapping = TournamentSkillMapping(
                    semester_id=semester.id,
                    skill_name=skill_name,
                    weight=weight,
                )
                db.add(mapping)

            # ── 4. TournamentParticipation ───────────────────────────────────
            for player_key, placement in t["players"]:
                player = PLAYERS[player_key]
                participation = TournamentParticipation(
                    user_id=player["id"],
                    semester_id=semester.id,
                    placement=placement,
                    achieved_at=t["date"] + timedelta(hours=placement),  # stagger timestamps
                    xp_awarded=max(0, 200 - (placement - 1) * 40),
                    credits_awarded=max(0, 100 - (placement - 1) * 20),
                )
                db.add(participation)

            db.commit()
            theme_skills = ", ".join(
                f"{s}(w={w})" for s, w in THEMES[t["theme"]]["skills"]
            )
            print(
                f"  CREATED T{t['code'][-2:]}: {t['name'][:50]}  "
                f"players={n_players}  theme={t['theme']}  "
                f"date={t['date'].date()}"
            )
            print(f"    skills: {theme_skills}")
            results = ", ".join(
                f"{PLAYERS[k]['name'].split()[0]}#{p}"
                for k, p in t["players"]
            )
            print(f"    results: {results}")
            created += 1

        print(f"\n✅ Done — created={created}, skipped={skipped}")

        # ── Summary: participations per player ────────────────────────────────
        print("\n── Participation summary ───────────────────────────────────────")
        for key, p in PLAYERS.items():
            wins = sum(
                1 for t in TOURNAMENTS
                for pk, pl in t["players"]
                if pk == key and pl == 1
            )
            total = sum(1 for t in TOURNAMENTS for pk, _ in t["players"] if pk == key)
            placements = [
                pl for t in TOURNAMENTS
                for pk, pl in t["players"]
                if pk == key
            ]
            avg_pl = sum(placements) / len(placements) if placements else 0
            print(
                f"  {p['name']:30s}: {total} tournaments, "
                f"{wins} wins, avg_place={avg_pl:.1f}"
            )

    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 65)
    print("EMA V3 VALIDATION TOURNAMENT SEED")
    print("=" * 65)
    seed()
