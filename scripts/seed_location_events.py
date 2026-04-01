#!/usr/bin/env python3
"""
Seed: Location-Specific Event Audit & Seed  (LFA_FOOTBALL_PLAYER only)
=======================================================================

Event types per location:

  Budapest  (CENTER):
    TOURNAMENT  league      ✅ PLAYABLE-TOURN-H2H-LEAGUE-2026
    TOURNAMENT  score_based ✅ PLAYABLE-TOURN-SCORE-2026
    TOURNAMENT  time_based  ✅ PLAYABLE-TOURN-TIME-2026
    CAMP        summer      ✅ PLAYABLE-CAMP-SUMMER-2026-YOUTH
    CAMP        autumn      ✅ PLAYABLE-CAMP-AUTUMN-2026-YOUTH
    MINI_SEASON             ❌ → create  BDPST-MINI-FOOTBALL-YOUTH-2026
    ACADEMY_SEASON          ❌ → create  BDPST-ACADEMY-FOOTBALL-YOUTH-2026

  Debrecen  (PARTNER):
    TOURNAMENT  league      ✅ DEBR-TOURN-LFA_FOOTBALL_PLAYER-2026
    TOURNAMENT  score_based ❌ → create  DEBR-TOURN-SCORE-FOOTBALL-2026
    TOURNAMENT  time_based  ❌ → create  DEBR-TOURN-TIME-FOOTBALL-2026
    CAMP        summer      ❌ → create  DEBR-CAMP-SUMMER-FOOTBALL-2026
    CAMP        autumn      ❌ → create  DEBR-CAMP-AUTUMN-FOOTBALL-2026
    MINI_SEASON             ❌ → create  DEBR-MINI-FOOTBALL-YOUTH-2026
    ACADEMY_SEASON          — NOT ALLOWED (PARTNER type)

Spec: only LFA_FOOTBALL_PLAYER  (other specs not yet active)

ADDITIVE and IDEMPOTENT — safe to run multiple times.

Run:
    python scripts/seed_location_events.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.location import Location, LocationType
from app.models.campus import Campus
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_type import TournamentType
from app.models.game_configuration import GameConfiguration
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.game_preset import GamePreset

SPEC = "LFA_FOOTBALL_PLAYER"
AGE_GROUP = "YOUTH"

# ── Reward config ──────────────────────────────────────────────────────────────
# NOTE: skill keys must be lowercase snake_case (matching get_all_skill_keys())

_FOOTBALL_REWARD = {
    "template_name": "LFA Football Standard",
    "custom_config": False,
    "skill_mappings": [
        {"skill": "dribbling", "weight": 1.5, "category": "TECHNICAL", "enabled": True},
        {"skill": "finishing",  "weight": 1.3, "category": "TECHNICAL", "enabled": True},
        {"skill": "passing",    "weight": 1.0, "category": "TECHNICAL", "enabled": True},
    ],
    "first_place":   {"credits": 500, "xp_multiplier": 2.0, "badges": []},
    "second_place":  {"credits": 250, "xp_multiplier": 1.5, "badges": []},
    "third_place":   {"credits": 100, "xp_multiplier": 1.2, "badges": []},
    "participation": {"credits":  50, "xp_multiplier": 1.0, "badges": []},
}

# ── Location definitions ───────────────────────────────────────────────────────

_LOCATIONS = [
    {
        "city": "Budapest",
        "name": "LFA IK Education Center Budapest",
        "country": "Hungary",
        "country_code": "HU",
        "location_code": "BDPST-IK",
        "address": "Istvánmezei út 1-3, Budapest",
        "postal_code": "1146",
        "location_type": LocationType.CENTER,
        "campus_name": "IK Main Campus",
    },
    {
        "city": "Debrecen",
        "name": "LFA Debrecen Partner Center",
        "country": "Hungary",
        "country_code": "HU",
        "location_code": "DEBR-01",
        "address": "Nagyerdei körút 98, Debrecen",
        "postal_code": "4032",
        "location_type": LocationType.PARTNER,
        "campus_name": "Debrecen Main Campus",
    },
]

# ── Event definitions per location ────────────────────────────────────────────
# "allow_academy" is True only for CENTER locations.
# Each entry: code, category, and optional tournament fields.

_BUDAPEST_EVENTS = [
    # Already seeded by seed_minimum_playable.py — detected by code, skipped
    {"code": "PLAYABLE-TOURN-H2H-LEAGUE-2026",  "category": SemesterCategory.TOURNAMENT, "label": "League Tournament (H2H)",     "tt_code": "league",      "scoring_type": None,          "measurement_unit": None,      "ranking_direction": "DESC", "t_status": "ENROLLMENT_OPEN"},
    {"code": "PLAYABLE-TOURN-SCORE-2026",         "category": SemesterCategory.TOURNAMENT, "label": "Score Challenge",             "tt_code": "score_based", "scoring_type": "SCORE_BASED", "measurement_unit": "goals",   "ranking_direction": "DESC", "t_status": "ENROLLMENT_OPEN"},
    {"code": "PLAYABLE-TOURN-TIME-2026",          "category": SemesterCategory.TOURNAMENT, "label": "Time Trial Series",           "tt_code": "time_based",  "scoring_type": "TIME_BASED",  "measurement_unit": "seconds", "ranking_direction": "ASC",  "t_status": "ENROLLMENT_OPEN"},
    {"code": "PLAYABLE-CAMP-SUMMER-2026-YOUTH",   "category": SemesterCategory.CAMP,       "label": "Summer Camp (YOUTH)",         "enrollment_cost": 500},
    {"code": "PLAYABLE-CAMP-AUTUMN-2026-YOUTH",   "category": SemesterCategory.CAMP,       "label": "Autumn Camp (YOUTH)",         "enrollment_cost": 500},
    # Missing → will be created
    {"code": "BDPST-MINI-FOOTBALL-YOUTH-2026",    "category": SemesterCategory.MINI_SEASON,    "label": "Mini Season YOUTH 2026",  "enrollment_cost": 500,  "start_offset": 7,  "duration": 60},
    {"code": "BDPST-ACADEMY-FOOTBALL-YOUTH-2026", "category": SemesterCategory.ACADEMY_SEASON, "label": "Academy Season YOUTH 2026/27", "enrollment_cost": 1000, "start_offset": 14, "duration": 300},
]

_DEBRECEN_EVENTS = [
    # Already seeded in previous run
    {"code": "DEBR-TOURN-LFA_FOOTBALL_PLAYER-2026", "category": SemesterCategory.TOURNAMENT, "label": "League Tournament (H2H)",     "tt_code": "league",      "scoring_type": None,          "measurement_unit": None,      "ranking_direction": "DESC", "t_status": "ENROLLMENT_OPEN"},
    # Missing → will be created
    {"code": "DEBR-TOURN-SCORE-FOOTBALL-2026",      "category": SemesterCategory.TOURNAMENT, "label": "Score Challenge",             "tt_code": "score_based", "scoring_type": "SCORE_BASED", "measurement_unit": "goals",   "ranking_direction": "DESC", "t_status": "ENROLLMENT_OPEN"},
    {"code": "DEBR-TOURN-TIME-FOOTBALL-2026",       "category": SemesterCategory.TOURNAMENT, "label": "Time Trial Series",           "tt_code": "time_based",  "scoring_type": "TIME_BASED",  "measurement_unit": "seconds", "ranking_direction": "ASC",  "t_status": "ENROLLMENT_OPEN"},
    {"code": "DEBR-CAMP-SUMMER-FOOTBALL-2026",      "category": SemesterCategory.CAMP,       "label": "Summer Camp (YOUTH)",         "enrollment_cost": 500},
    {"code": "DEBR-CAMP-AUTUMN-FOOTBALL-2026",      "category": SemesterCategory.CAMP,       "label": "Autumn Camp (YOUTH)",         "enrollment_cost": 500},
    {"code": "DEBR-MINI-FOOTBALL-YOUTH-2026",       "category": SemesterCategory.MINI_SEASON,    "label": "Mini Season YOUTH 2026",  "enrollment_cost": 500,  "start_offset": 7,  "duration": 60},
    # No ACADEMY_SEASON — PARTNER location type does not allow it
]

_LOCATION_EVENTS = {
    "Budapest": _BUDAPEST_EVENTS,
    "Debrecen": _DEBRECEN_EVENTS,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_or_create_location(db, cfg: dict) -> Location:
    loc = db.query(Location).filter(Location.city == cfg["city"]).first()
    if loc:
        print(f"   ⏭️  Location: {loc.city} (id={loc.id}, type={loc.location_type.value})")
        return loc
    loc = Location(
        name=cfg["name"],
        city=cfg["city"],
        country=cfg["country"],
        country_code=cfg["country_code"],
        location_code=cfg["location_code"],
        address=cfg["address"],
        postal_code=cfg["postal_code"],
        location_type=cfg["location_type"],
        is_active=True,
    )
    db.add(loc)
    db.flush()
    print(f"   ✅ Created location: {loc.name} (id={loc.id})")
    return loc


def _get_or_create_campus(db, location: Location, campus_name: str) -> Campus:
    campus = (
        db.query(Campus)
        .filter(Campus.location_id == location.id, Campus.is_active == True)
        .first()
    )
    if campus:
        print(f"   ⏭️  Campus: {campus.name} (id={campus.id})")
        return campus
    campus = Campus(
        location_id=location.id,
        name=campus_name,
        venue=f"{campus_name} outdoor + gym",
        address=location.address or "",
        is_active=True,
    )
    db.add(campus)
    db.flush()
    print(f"   ✅ Created campus: {campus.name} (id={campus.id})")
    return campus


def _get_tt(db, code: str) -> TournamentType | None:
    return db.query(TournamentType).filter(TournamentType.code == code).first()


def _get_preset(db, code: str) -> GamePreset | None:
    return (
        db.query(GamePreset)
        .filter(GamePreset.code == code, GamePreset.is_active == True)
        .first()
    )


def _ensure_event(db, event_cfg: dict, location: Location, campus: Campus, today: date) -> bool:
    """Create the event if it doesn't exist. Returns True if created, False if already existed."""
    code = event_cfg["code"]
    existing = db.query(Semester).filter(Semester.code == code).first()
    if existing:
        return False  # already exists

    category: SemesterCategory = event_cfg["category"]
    label: str = event_cfg["label"]
    is_tournament = (category == SemesterCategory.TOURNAMENT)
    start_offset = event_cfg.get("start_offset", 14)
    duration = event_cfg.get("duration", 14)

    s = Semester(
        code=code,
        name=f"{label} — {location.city}",
        semester_category=category,
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status=event_cfg.get("t_status"),  # only set for TOURNAMENT
        age_group=AGE_GROUP,
        location_id=location.id,
        campus_id=campus.id,
        start_date=today + timedelta(days=start_offset),
        end_date=today + timedelta(days=start_offset + duration),
        enrollment_cost=event_cfg.get("enrollment_cost", 0),
        specialization_type=SPEC,
    )
    db.add(s)
    db.flush()

    if is_tournament:
        tt = _get_tt(db, event_cfg["tt_code"])
        db.add(TournamentConfiguration(
            semester_id=s.id,
            tournament_type_id=tt.id if tt else None,
            scoring_type=event_cfg.get("scoring_type"),
            measurement_unit=event_cfg.get("measurement_unit"),
            ranking_direction=event_cfg.get("ranking_direction", "DESC"),
            participant_type="INDIVIDUAL",
            is_multi_day=False,
            max_players=32,
            parallel_fields=1,
            sessions_generated=False,
        ))
        preset = _get_preset(db, "outfield_default")
        db.add(GameConfiguration(
            semester_id=s.id,
            game_preset_id=preset.id if preset else None,
            game_config={"metadata": {"min_players": 4, "game_category": "FOOTBALL"},
                         "match_rules": {"scoring": "goals", "overtime": False}},
        ))
        db.add(TournamentRewardConfig(
            semester_id=s.id,
            reward_policy_name=_FOOTBALL_REWARD["template_name"],
            reward_config=_FOOTBALL_REWARD,
        ))

    return True


def _category_label(cat: SemesterCategory) -> str:
    return {
        SemesterCategory.TOURNAMENT:     "TOURNAMENT   ",
        SemesterCategory.CAMP:           "CAMP         ",
        SemesterCategory.MINI_SEASON:    "MINI_SEASON  ",
        SemesterCategory.ACADEMY_SEASON: "ACADEMY_SEASON",
    }.get(cat, str(cat))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    today = date.today()
    db = SessionLocal()

    try:
        print("\n" + "=" * 70)
        print("  Location Event Audit & Seed  —  LFA_FOOTBALL_PLAYER only")
        print("=" * 70)

        for loc_cfg in _LOCATIONS:
            city = loc_cfg["city"]
            ltype = loc_cfg["location_type"].value
            print(f"\n📍 {city}  ({ltype})")

            location = _get_or_create_location(db, loc_cfg)
            campus = _get_or_create_campus(db, location, loc_cfg["campus_name"])

            events = _LOCATION_EVENTS[city]
            print(f"\n   Events ({len(events)} defined):")
            created = 0
            for ev in events:
                code = ev["code"]
                cat_label = _category_label(ev["category"])
                was_created = _ensure_event(db, ev, location, campus, today)
                if was_created:
                    print(f"   ✅  {cat_label}  {ev['label']:<35}  [{code}]  CREATED")
                    created += 1
                else:
                    print(f"   ⏭️   {cat_label}  {ev['label']:<35}  [{code}]  already exists")

            if created:
                print(f"\n   → {created} new event(s) created for {city}")

        db.commit()

        # ── Final audit report ─────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("  Final Audit Report")
        print("=" * 70)

        all_ok = True
        for loc_cfg in _LOCATIONS:
            location = db.query(Location).filter(Location.city == loc_cfg["city"]).first()
            if not location:
                print(f"\n❌ {loc_cfg['city']}: NOT FOUND")
                all_ok = False
                continue

            ltype = location.location_type.value if location.location_type else "?"
            print(f"\n📍 {location.city}  (id={location.id}, type={ltype})")

            events = _LOCATION_EVENTS[location.city]
            for ev in events:
                sem = db.query(Semester).filter(Semester.code == ev["code"]).first()
                cat_label = _category_label(ev["category"])
                if sem:
                    print(f"   ✅  {cat_label}  {ev['label']:<35}  id={sem.id}  [{ev['code']}]")
                else:
                    print(f"   ❌  {cat_label}  {ev['label']:<35}  MISSING  [{ev['code']}]")
                    all_ok = False

        print()
        if all_ok:
            print("✅ All defined events are present in the database.")
        else:
            print("⚠️  Some events are still missing — check output above.")

    except Exception as exc:
        db.rollback()
        print(f"\n❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
