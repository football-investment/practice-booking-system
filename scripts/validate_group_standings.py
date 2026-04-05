#!/usr/bin/env python3
"""
validate_group_standings.py
============================
Hard-fail validation for group_knockout standings correctness.

Per tournament, per group — three checks:

  GS-01  NOT-ZERO      At least one participant has Pts>0 or GF>0.
                        Fails when game_results parsing is broken (all zeros = data not read).

  GS-02  DETERMINISM   calculate_group_standings() invoked twice with shuffled session
                        input order → identical participant order in each group.
                        Catches non-stable sort or insertion-order dependence.

  GS-03  QUALIFICATION  Participant IDs in R1 knockout sessions
                        == standings[:top_n] from each group.
                        Catches sorting/qualification divergence.

Exit codes:
  0 = all checks pass
  1 = one or more failures (details printed above summary)

Usage (local):
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY=dev-secret-key PYTHONPATH=. \\
        python scripts/validate_group_standings.py

Usage (CI):
    Called after seed_rewards_distributed_showcase.py has run.
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from sqlalchemy import text as _sql

from app.database import SessionLocal
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_type import TournamentType
from app.services.tournament.results.calculators.standings_calculator import StandingsCalculator

# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ok(msg):   print(f"  ✅  {msg}")
def _fail(msg): print(f"  ❌  FAIL: {msg}")
def _info(msg): print(f"       {msg}")
def _sep():     print(f"  {'─'*65}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _id_key(entries: list[dict]) -> str:
    return "team_id" if (entries and "team_id" in entries[0]) else "user_id"


def _ordered_ids(standings: dict[str, list[dict]]) -> dict[str, list[int]]:
    """Extract ordered participant IDs per group from a standings dict."""
    return {
        grp: [e[_id_key(entries)] for e in entries]
        for grp, entries in standings.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

db = SessionLocal()
failures: list[str] = []
checked = 0


def _record_fail(msg: str) -> None:
    _fail(msg)
    failures.append(msg)


try:
    # ── Find all group_knockout tournaments ───────────────────────────────────
    tournaments = (
        db.query(Semester)
        .join(TournamentConfiguration, TournamentConfiguration.semester_id == Semester.id)
        .join(TournamentType, TournamentType.id == TournamentConfiguration.tournament_type_id)
        .filter(TournamentType.code == "group_knockout")
        .order_by(Semester.id)
        .all()
    )

    if not tournaments:
        print("⚠️  No group_knockout tournaments found — nothing to validate")
        sys.exit(0)

    print(f"\nFound {len(tournaments)} group_knockout tournament(s)\n")

    for t in tournaments:
        checked += 1
        print(f"\n{'='*68}")
        print(f"  Tournament  id={t.id}  '{t.name}'")
        print(f"  Status: {t.tournament_status}")
        print(f"{'='*68}")

        # ── Fetch sessions ────────────────────────────────────────────────────
        group_sessions = (
            db.query(SessionModel)
            .filter(
                SessionModel.semester_id == t.id,
                SessionModel.tournament_phase == "GROUP_STAGE",
            )
            .order_by(SessionModel.id)
            .all()
        )

        ko_r1_sessions = (
            db.query(SessionModel)
            .filter(
                SessionModel.semester_id == t.id,
                SessionModel.tournament_phase == "KNOCKOUT",
                SessionModel.tournament_round == 1,
            )
            .all()
        )

        if not group_sessions:
            _record_fail(f"[id={t.id}] No GROUP_STAGE sessions found")
            continue

        if not ko_r1_sessions:
            _record_fail(f"[id={t.id}] No R1 KNOCKOUT sessions found — cannot validate qualification")
            continue

        _info(f"GROUP_STAGE sessions : {len(group_sessions)}")
        _info(f"KNOCKOUT R1 sessions : {len(ko_r1_sessions)}")

        # ── Calculate standings (run 1 — DB order) ────────────────────────────
        calc = StandingsCalculator(db)
        standings_1 = calc.calculate_group_standings(list(group_sessions))

        # ── Calculate standings (run 2 — reversed order) ──────────────────────
        shuffled = list(group_sessions)
        shuffled.reverse()
        standings_2 = calc.calculate_group_standings(shuffled)

        # ── GS-01: Not-zero check ─────────────────────────────────────────────
        print()
        all_groups_nonzero = True
        for grp, entries in sorted(standings_1.items()):
            has_data = any(
                e.get("points", 0) > 0
                or e.get("goals_for", 0) > 0
                or e.get("goal_difference", 0) != 0
                for e in entries
            )
            if not has_data:
                _record_fail(f"[id={t.id}] GS-01 Group {grp}: ALL standings are zero — results not parsed")
                all_groups_nonzero = False
            else:
                _ok(f"GS-01  Group {grp}: non-zero standings confirmed")

        # ── GS-02: Determinism check ──────────────────────────────────────────
        order_1 = _ordered_ids(standings_1)
        order_2 = _ordered_ids(standings_2)
        deterministic = True
        for grp in sorted(order_1.keys()):
            if order_1.get(grp) != order_2.get(grp):
                _record_fail(
                    f"[id={t.id}] GS-02 Group {grp}: NON-DETERMINISTIC — "
                    f"fwd={order_1[grp]}  rev={order_2[grp]}"
                )
                deterministic = False
            else:
                _ok(f"GS-02  Group {grp}: deterministic  {order_1[grp]}")

        # ── GS-03: Qualification check ────────────────────────────────────────
        # Build actual qualified set from R1 knockout sessions
        actual_qualified: set[int] = set()
        for sess in ko_r1_sessions:
            for pid in (sess.participant_team_ids or []):
                actual_qualified.add(pid)
            for pid in (sess.participant_user_ids or []):
                actual_qualified.add(pid)

        # Infer top_n from bracket size
        num_groups = len(standings_1)
        total_r1_slots = len(ko_r1_sessions) * 2
        top_n = total_r1_slots // max(num_groups, 1)

        # Expected qualified = top_n from each group, in standings order
        expected_qualified: set[int] = set()
        for grp, entries in standings_1.items():
            idk = _id_key(entries)
            for e in entries[:top_n]:
                expected_qualified.add(e[idk])

        # Print standings table with Q marker
        print()
        _info(f"top_n per group = {top_n}  (inferred from {len(ko_r1_sessions)} R1 sessions × 2 / {num_groups} groups)")
        print()
        for grp, entries in sorted(standings_1.items()):
            idk = _id_key(entries)
            id_label = "team_id" if idk == "team_id" else "user_id"
            print(f"  ┌─ Group {grp} ──────────────────────────────────────────┐")
            print(f"  │  {'#':>2}  {id_label:<9}  {'Name':<22}  {'Pts':>3}  {'W':>2}  {'D':>2}  {'L':>2}  {'GD':>5}  {'GF':>3}  Q")
            print(f"  │  {'─'*72}")
            for i, e in enumerate(entries, 1):
                pid = e[idk]
                in_actual = pid in actual_qualified
                in_expected = pid in expected_qualified
                q_char = "Q" if in_actual else " "
                consistent = "✓" if in_actual == in_expected else "✗ MISMATCH"
                print(
                    f"  │  {i:>2}  {pid:<9}  {e.get('name','?'):<22}  "
                    f"{e.get('points',0):>3}  {e.get('wins',0):>2}  {e.get('draws',0):>2}  "
                    f"{e.get('losses',0):>2}  {e.get('goal_difference',0):>+5}  "
                    f"{e.get('goals_for',0):>3}  {q_char} {consistent}"
                )
            print(f"  └{'─'*75}┘")

        print()
        _info(f"Expected qualified : {sorted(expected_qualified)}")
        _info(f"Actual qualified   : {sorted(actual_qualified)}")

        if actual_qualified != expected_qualified:
            _record_fail(
                f"[id={t.id}] GS-03 QUALIFICATION MISMATCH — "
                f"expected={sorted(expected_qualified)}  actual={sorted(actual_qualified)}"
            )
        else:
            _ok(f"GS-03  Qualification matches top-{top_n} standings for all {num_groups} groups")

finally:
    db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────

print(f"\n{'='*68}")
print(f"  GROUP STANDINGS VALIDATION — SUMMARY")
print(f"{'='*68}")
print(f"  Tournaments checked : {checked}")
print(f"  Checks per event    : GS-01 (not-zero) · GS-02 (determinism) · GS-03 (qualification)")

if failures:
    print(f"  ❌  {len(failures)} failure(s):\n")
    for f in failures:
        print(f"       • {f}")
    print()
    sys.exit(1)
else:
    print(f"  ✅  All checks passed")
    print()
    sys.exit(0)
