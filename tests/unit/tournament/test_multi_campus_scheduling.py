"""
Unit tests — Multi-campus parallel_fields scheduling
DB-free: GroupKnockoutGenerator.generate() is called directly with
mocked tournament/DB objects.

Test matrix:
  TC-01  2 campuses, different parallel_fields + match durations
         → Group A → Campus-1 (dur=60 min, 2 parallel fields)
         → Group B → Campus-2 (dur=45 min, 3 parallel fields)
         → Assert: correct per-campus durations, no slot collision,
                   no cross-campus slot reuse (locations are isolated)

  TC-02  campus_configs=None  (global fallback path)
         → Both groups share the global field pool (session_duration=90)
         → Assert: no AttributeError, all sessions use 90-min duration

  TC-03  campus_configs partially missing campus 202
         → Group A → per-campus 60 min
         → Group B → missing entry → global fallback 90 min
         → Assert: correct per-group duration, no crash

  TC-04  parallel_fields=2 within one campus → no field-slot overlap
         → Group A has 4 players HEAD_TO_HEAD → 6 matches
         → Campus-1 has 2 parallel fields
         → Assert: at most 2 matches start at the same time
"""

import pytest
from collections import defaultdict
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _campus(id_: int, name: str, venue: str = "Pálya"):
    return SimpleNamespace(id=id_, name=name, venue=venue, location=None, is_active=True)


def _enrollment(user_id: int):
    return SimpleNamespace(
        id=user_id * 100,
        user_id=user_id,
        semester_id=1,
        is_active=True,
        request_status="approved",
        tournament_checked_in_at=None,
    )


def _tournament(format_: str = "INDIVIDUAL_RANKING"):
    return SimpleNamespace(
        id=1,
        name="Multi-Campus Cup",
        start_date=datetime(2026, 3, 1, 9, 0),
        format=format_,
        scoring_type="SCORE_BASED",
        campus=None,
        location=None,
        campus_id=None,
    )


def _tournament_type(format_: str = "INDIVIDUAL_RANKING"):
    return SimpleNamespace(
        id=1,
        code="group_knockout",
        format=format_,
        config={
            "group_configuration": {},   # empty → dynamic GroupDistribution path
            "round_names": {},
        },
    )


def _campus_cfg(dur: int, brk: int, parallel: int) -> dict:
    return {
        "match_duration_minutes": dur,
        "break_duration_minutes": brk,
        "parallel_fields": parallel,
        "venue_label": None,
    }


def _build_db(player_ids: list, campuses: list) -> MagicMock:
    """
    Minimal mock DB that serves:
      db.query(SemesterEnrollment).filter(*).all()  → enrollment list
      db.query(Campus).filter(*).order_by(*).all()  → campus list
    """
    enrollments = [_enrollment(uid) for uid in player_ids]

    mock_db = MagicMock()

    def _query(model):
        name = getattr(model, "__name__", str(model))

        if "Enrollment" in name or "enrollment" in name.lower():
            q = MagicMock()
            inner = MagicMock()
            inner.filter.return_value = inner
            inner.all.return_value = enrollments
            inner.count.return_value = len(enrollments)
            q.filter.return_value = inner
            return q

        else:  # Campus
            q = MagicMock()
            inner = MagicMock()
            inner.filter.return_value = inner
            order_obj = MagicMock()
            order_obj.all.return_value = campuses
            inner.order_by.return_value = order_obj
            q.filter.return_value = inner
            return q

    mock_db.query.side_effect = _query
    return mock_db


def _run(
    campus_ids,
    campus_configs,
    campuses,
    player_ids=None,
    format_="INDIVIDUAL_RANKING",
    global_parallel=1,
    global_duration=90,
    global_break=15,
):
    """Instantiate generator and call generate() with given params."""
    from app.services.tournament.session_generation.formats.group_knockout_generator import (
        GroupKnockoutGenerator,
    )

    if player_ids is None:
        player_ids = list(range(1, 9))  # 8 players → 2 groups of 4

    db = _build_db(player_ids, campuses)
    gen = GroupKnockoutGenerator(db=db)

    return gen.generate(
        tournament=_tournament(format_),
        tournament_type=_tournament_type(format_),
        player_count=len(player_ids),
        parallel_fields=global_parallel,
        session_duration=global_duration,
        break_minutes=global_break,
        campus_ids=campus_ids,
        campus_configs=campus_configs,
    )


def _group_stage(sessions):
    return [s for s in sessions if s["tournament_phase"] == "GROUP_STAGE"]


def _by_group(sessions, label):
    return [s for s in sessions if s.get("group_identifier") == label]


def _duration_minutes(session):
    return (session["date_end"] - session["date_start"]).total_seconds() / 60


def _has_field_collision(sessions):
    """
    Returns True if two sessions on the SAME physical field at the same
    location overlap in time.

    Sessions on DIFFERENT fields at the same campus CAN run simultaneously
    — that is the whole point of parallel_fields.  We use structure_config
    ['field_number'] to distinguish fields within one campus.
    """
    # key = (location, field_number) — two sessions share a field only if both match
    by_field: dict = defaultdict(list)
    for s in sessions:
        field_num = (s.get("structure_config") or {}).get("field_number", 1)
        key = (s.get("location", ""), field_num)
        by_field[key].append(s)

    for field_sessions in by_field.values():
        sorted_s = sorted(field_sessions, key=lambda x: x["date_start"])
        for i in range(len(sorted_s) - 1):
            e1 = sorted_s[i]["date_end"]
            s2 = sorted_s[i + 1]["date_start"]
            if e1 > s2:
                return True
    return False


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestMultiCampusScheduling:
    """TC-01 … TC-04: per-campus parallel_fields scheduling."""

    # ── TC-01 ─────────────────────────────────────────────────────────────────
    def test_two_campuses_different_durations(self):
        """
        2 campuses with different durations:
          Campus 101 → 60 min, 2 fields
          Campus 202 → 45 min, 3 fields
        Group A sessions must be 60 min; Group B sessions must be 45 min.
        No time-slot collision within each group.
        Location strings must match the correct campus.
        """
        c1 = _campus(101, "Campus Buda", "Kelenföldi Pálya")
        c2 = _campus(202, "Campus Pest", "Kőbányai Pálya")

        configs = {
            101: _campus_cfg(dur=60, brk=10, parallel=2),
            202: _campus_cfg(dur=45, brk=5,  parallel=3),
        }

        sessions = _run(
            campus_ids=[101, 202],
            campus_configs=configs,
            campuses=[c1, c2],
        )

        gs = _group_stage(sessions)
        ga = _by_group(gs, "A")
        gb = _by_group(gs, "B")

        assert len(ga) > 0, "Group A must have group-stage sessions"
        assert len(gb) > 0, "Group B must have group-stage sessions"

        # ── Duration per campus ──
        for s in ga:
            assert _duration_minutes(s) == 60, (
                f"Group A session should be 60 min, got {_duration_minutes(s)}"
            )
        for s in gb:
            assert _duration_minutes(s) == 45, (
                f"Group B session should be 45 min, got {_duration_minutes(s)}"
            )

        # ── Location isolation ──
        for s in ga:
            assert "Kelenföldi" in s["location"] or "Campus Buda" in s["location"], (
                f"Group A must use Campus Buda, got: {s['location']}"
            )
        for s in gb:
            assert "Kőbányai" in s["location"] or "Campus Pest" in s["location"], (
                f"Group B must use Campus Pest, got: {s['location']}"
            )

        # ── No sequential collision within the same campus ──
        assert not _has_field_collision(ga), "Group A: session time-slots must not overlap"
        assert not _has_field_collision(gb), "Group B: session time-slots must not overlap"

    # ── TC-02 ─────────────────────────────────────────────────────────────────
    def test_no_crash_when_campus_configs_is_none(self):
        """
        campus_configs=None → global fallback (session_duration=90 min).
        No AttributeError; all group-stage sessions are 90 min.
        """
        c1 = _campus(101, "Campus Buda")
        c2 = _campus(202, "Campus Pest")

        sessions = _run(
            campus_ids=[101, 202],
            campus_configs=None,        # ← global fallback
            campuses=[c1, c2],
            global_duration=90,
        )

        gs = _group_stage(sessions)
        assert len(gs) > 0, "Must still generate group-stage sessions"

        for s in gs:
            assert _duration_minutes(s) == 90, (
                f"Fallback duration must be 90 min, got {_duration_minutes(s)}"
            )

    # ── TC-03 ─────────────────────────────────────────────────────────────────
    def test_partial_campus_configs_falls_back_gracefully(self):
        """
        campus_configs contains only campus 101.
        Group A → 60 min (campus-level config).
        Group B → campus 202 missing from configs → global fallback → 90 min.
        No crash.
        """
        c1 = _campus(101, "Campus Buda")
        c2 = _campus(202, "Campus Pest")

        configs = {
            101: _campus_cfg(dur=60, brk=10, parallel=2),
            # 202 intentionally missing
        }

        sessions = _run(
            campus_ids=[101, 202],
            campus_configs=configs,
            campuses=[c1, c2],
            global_duration=90,
        )

        gs = _group_stage(sessions)
        ga = _by_group(gs, "A")
        gb = _by_group(gs, "B")

        assert len(ga) > 0 and len(gb) > 0, "Both groups must have sessions"

        for s in ga:
            assert _duration_minutes(s) == 60, (
                f"Group A must use campus-level config (60 min), got {_duration_minutes(s)}"
            )
        for s in gb:
            assert _duration_minutes(s) == 90, (
                f"Group B must fall back to global (90 min), got {_duration_minutes(s)}"
            )

    # ── TC-04 ─────────────────────────────────────────────────────────────────
    def test_parallel_fields_limits_concurrent_head_to_head_matches(self):
        """
        HEAD_TO_HEAD format, 8 players, 2 groups of 4.
        Campus 101: parallel_fields=2.
        → At most 2 Group-A matches may start at the exact same timestamp.
        """
        c1 = _campus(101, "Campus Buda", "Buda Field")
        c2 = _campus(202, "Campus Pest", "Pest Field")

        configs = {
            101: _campus_cfg(dur=60, brk=10, parallel=2),
            202: _campus_cfg(dur=60, brk=10, parallel=2),
        }

        sessions = _run(
            campus_ids=[101, 202],
            campus_configs=configs,
            campuses=[c1, c2],
            format_="HEAD_TO_HEAD",
        )

        gs = _group_stage(sessions)
        ga = _by_group(gs, "A")
        gb = _by_group(gs, "B")

        assert len(ga) >= 6, (
            "4 HEAD_TO_HEAD players generate 6 matches (round-robin)"
        )

        # Count concurrent starts per campus — must not exceed parallel_fields
        for grp_sessions, label, max_concurrent in [
            (ga, "A", 2),
            (gb, "B", 2),
        ]:
            by_start: dict = defaultdict(int)
            for s in grp_sessions:
                by_start[s["date_start"]] += 1

            for ts, count in by_start.items():
                assert count <= max_concurrent, (
                    f"Group {label}: {count} matches start at {ts}, "
                    f"but campus only has {max_concurrent} parallel fields"
                )

        # ── No collision: each field's sessions are sequential ──
        assert not _has_field_collision(ga), "Group A field slots must not collide"
        assert not _has_field_collision(gb), "Group B field slots must not collide"
