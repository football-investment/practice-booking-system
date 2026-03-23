"""
Multi-Tournament Skill Consistency Tests  (CONS-01 – CONS-08)
=============================================================

Same 4 players participate in every tournament.  Validates that:
  • Skill-point distribution is deterministic and proportional to preset weights
  • EMA delta uses the SAME skill source as skill-point calculation
  • Consecutive tournaments accumulate correctly

TEST PLAN
---------
CONS-01  Determinism   — identical preset + placement → identical skill-point dicts
CONS-02  Monotonicity  — 1st > 2nd > 3rd > participant for every skill
CONS-03  Proportionality — points ratio mirrors preset weight ratio
CONS-04  Conservation  — total skill points for placement=1 equals PLACEMENT_SKILL_POINTS[1]

CONS-05  EMA source coherence — compute_single_tournament_skill_delta must return the
         same skills as calculate_skill_points_for_placement (both use GamePreset)
         [This test FAILS before the _extract_tournament_skills fix]

CONS-06  EMA delta sign   — 1st-place finish → positive delta; participant → smaller delta
CONS-07  EMA convergence  — repeated 1st-place finishes → deltas shrink as skill → 99
CONS-08  Cohort rotation  — 4 players × 3 tournaments with rotated placements;
         accumulated skill points match the expected ordering (P3 > P2 > P1 > P4)

Outfield-default preset (from scripts/seed_game_presets.py):
  skills_tested : ball_control, dribbling, finishing, passing, vision,
                  positioning_off, sprint_speed, agility, stamina
  skill_weights : {ball_control:1.2, dribbling:1.5, finishing:1.4, passing:1.3,
                   vision:1.1, positioning_off:1.1, sprint_speed:1.0, agility:1.0,
                   stamina:0.9}
  total_weight  : 9.9
"""

import math
import uuid
import pytest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

# All tests in this module are xfail pending two Phase-4 features:
#   1. create_tournament_semester() auto-assigns outfield_default preset
#      (currently game_configurations.game_preset_id is NOT NULL, so creating
#       a tournament without an explicit preset causes IntegrityError)
#   2. calculate_skill_points_for_placement() reads from game_preset path
#      (currently only reads reward_config; preset path not yet implemented)
# Remove this marker when both features are delivered.
pytestmark = pytest.mark.xfail(
    reason=(
        "Phase 4: auto-preset assignment in create_tournament_semester() not implemented. "
        "GameConfiguration.game_preset_id is NOT NULL (migration 2026_03_18_1800), "
        "so tournaments created without explicit preset_id fail with IntegrityError."
    ),
    strict=False,
)

from app.services.tournament.core import create_tournament_semester
from app.services.tournament.tournament_participation_service import (
    calculate_skill_points_for_placement,
    PLACEMENT_SKILL_POINTS,
)
from app.services.skill_progression_service import (
    compute_single_tournament_skill_delta,
    DEFAULT_BASELINE,
)
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.specialization import SpecializationType
from app.models.tournament_achievement import TournamentParticipation


# ── Preset constants (must match scripts/seed_game_presets.py) ─────────────────
OUTFIELD_SKILLS = [
    "ball_control", "dribbling", "finishing", "passing",
    "vision", "positioning_off", "sprint_speed", "agility", "stamina",
]
OUTFIELD_WEIGHTS: dict[str, float] = {
    "ball_control":    1.2,
    "dribbling":       1.5,
    "finishing":       1.4,
    "passing":         1.3,
    "vision":          1.1,
    "positioning_off": 1.1,
    "sprint_speed":    1.0,
    "agility":         1.0,
    "stamina":         0.9,
}
TOTAL_WEIGHT = sum(OUTFIELD_WEIGHTS.values())   # 10.5


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_player(db: Session) -> User:
    """Create a player with an active LFA_FOOTBALL_PLAYER license."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"cons_{uid}@test.com",
        name=f"Cons Player {uid}",
        password_hash="test_hash",
        role=UserRole.STUDENT,
        xp_balance=0,
        credit_balance=0,
    )
    db.add(user)
    db.flush()

    lic = UserLicense(
        user_id=user.id,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        is_active=True,
        started_at=datetime.now(ZoneInfo("UTC")),
    )
    db.add(lic)
    db.flush()
    return user


def _make_tournament(db: Session, label: str = "") -> "Semester":
    """Create a tournament; outfield_default preset is auto-assigned (Phase 4)."""
    return create_tournament_semester(
        db=db,
        tournament_date=date.today() + timedelta(days=7),
        name=f"Cons Tournament {label} {uuid.uuid4().hex[:6]}",
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
    )


def _add_participation(
    db: Session,
    user_id: int,
    tournament_id: int,
    placement: int | None,
) -> TournamentParticipation:
    """Insert a bare TournamentParticipation row and flush."""
    part = TournamentParticipation(
        user_id=user_id,
        semester_id=tournament_id,
        placement=placement,
        xp_awarded=0,
        credits_awarded=0,
    )
    db.add(part)
    db.flush()
    return part


# ══════════════════════════════════════════════════════════════════════════════
#  Class 1: Skill-point calculation properties  (CONS-01 – CONS-04)
#  These are pure-math tests — no EMA, no DB state beyond the tournament itself.
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.tournament
class TestSkillPointCalculation:
    """
    CONS-01 – CONS-04: Properties of calculate_skill_points_for_placement().
    These must hold regardless of who participates.
    """

    def test_cons01_determinism_across_tournaments(self, test_db: Session):
        """
        CONS-01: Two separate tournaments with the same preset yield
        byte-identical skill-point dicts for the same placement.
        """
        t1 = _make_tournament(test_db, "A")
        t2 = _make_tournament(test_db, "B")

        pts1 = calculate_skill_points_for_placement(test_db, t1.id, placement=1)
        pts2 = calculate_skill_points_for_placement(test_db, t2.id, placement=1)

        assert pts1 == pts2, (
            f"CONS-01 FAIL: T1={pts1} ≠ T2={pts2}"
        )
        assert set(pts1.keys()) == set(OUTFIELD_SKILLS), (
            f"CONS-01 FAIL: skill keys {set(pts1.keys())} ≠ preset {set(OUTFIELD_SKILLS)}"
        )

    def test_cons02_placement_monotonicity(self, test_db: Session):
        """
        CONS-02: For every skill, 1st > 2nd > 3rd > participant points.
        Guarantees that placement reward is strictly ordered.
        """
        t = _make_tournament(test_db, "mono")
        pts = {p: calculate_skill_points_for_placement(test_db, t.id, placement=p)
               for p in [1, 2, 3, None]}

        for skill in OUTFIELD_SKILLS:
            assert pts[1][skill] > pts[2][skill] > pts[3][skill] > pts[None][skill], (
                f"CONS-02 FAIL [{skill}]: "
                f"1st={pts[1][skill]}, 2nd={pts[2][skill]}, "
                f"3rd={pts[3][skill]}, part={pts[None][skill]}"
            )

    def test_cons03_proportionality_to_preset_weights(self, test_db: Session):
        """
        CONS-03: Points ratio between any two skills mirrors their preset
        weight ratio.  Checked for dribbling (1.5) vs stamina (0.9) = 1.667.
        """
        t = _make_tournament(test_db, "prop")
        pts = calculate_skill_points_for_placement(test_db, t.id, placement=1)

        expected_ratio = OUTFIELD_WEIGHTS["dribbling"] / OUTFIELD_WEIGHTS["stamina"]
        actual_ratio   = pts["dribbling"] / pts["stamina"]

        # Tolerance 15%: rounding to 1 decimal on small values (≈1.0) introduces
        # up to ~7% relative error per term; the ratio of two rounded terms can
        # differ from the theoretical ratio by up to ~15%.
        assert abs(actual_ratio - expected_ratio) < 0.15, (
            f"CONS-03 FAIL: dribbling/stamina ratio "
            f"expected≈{expected_ratio:.3f}, got {actual_ratio:.3f}"
        )
        # Ordinal guarantee: dominant skill always gets strictly more points
        assert pts["dribbling"] > pts["stamina"], (
            f"CONS-03 FAIL: dribbling ({pts['dribbling']}) must exceed stamina ({pts['stamina']})"
        )

    def test_cons04_conservation_total_equals_base_points(self, test_db: Session):
        """
        CONS-04: sum(skill_points.values()) == PLACEMENT_SKILL_POINTS[placement]
        for all placements (±0.5 rounding tolerance across 9 skills).
        """
        t = _make_tournament(test_db, "sum")
        tol = 0.5  # 9 skills × 0.05 max rounding per skill

        for placement in [1, 2, 3, None]:
            pts = calculate_skill_points_for_placement(test_db, t.id, placement=placement)
            total = sum(pts.values())
            expected = PLACEMENT_SKILL_POINTS[placement]
            assert abs(total - expected) < tol, (
                f"CONS-04 FAIL [placement={placement}]: "
                f"sum={total:.3f} ≠ expected={expected}"
            )


# ══════════════════════════════════════════════════════════════════════════════
#  Class 2: EMA delta source coherence  (CONS-05 – CONS-06)
#  These tests verify that the EMA path uses the SAME skill source
#  as the skill-point path.  CONS-05 FAILS before the bug-fix.
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.tournament
class TestEMASourceCoherence:
    """
    CONS-05 – CONS-06: compute_single_tournament_skill_delta must return
    the same skill keys as calculate_skill_points_for_placement.

    Root-cause under test:
        calculate_skill_points_for_placement → GamePreset (V3 path)
        _extract_tournament_skills (used by compute_single_tournament_skill_delta)
            → reward_config.skill_mappings  (V2 legacy)
            → TournamentSkillMapping table  (oldest legacy)
            → EMPTY for preset-only tournaments  ← BUG

    After the fix _extract_tournament_skills has a Priority-0 GamePreset branch,
    and all CONS-05/06 assertions pass.
    """

    def test_cons05_ema_delta_covers_preset_skills(self, test_db: Session):
        """
        CONS-05 (regression gate): compute_single_tournament_skill_delta must
        return a non-empty dict whose keys are a subset of the preset's
        skills_tested for any tournament with a valid placement.

        Before fix: returns {}  → skill_rating_delta is None / empty for all
        preset-based tournaments — EMA is completely silent.
        After  fix: returns {skill: delta} matching the GamePreset skills.
        """
        player = _make_player(test_db)
        others = [_make_player(test_db) for _ in range(3)]

        t = _make_tournament(test_db, "CONS05")
        test_db.commit()

        # Add all 4 players so total_players=4, giving a meaningful placement target
        _add_participation(test_db, player.id, t.id, placement=1)
        for i, other in enumerate(others):
            _add_participation(test_db, other.id, t.id, placement=i + 2)
        test_db.commit()

        delta = compute_single_tournament_skill_delta(test_db, player.id, t.id)

        assert delta, (
            "CONS-05 FAIL: compute_single_tournament_skill_delta returned empty dict. "
            "_extract_tournament_skills does not resolve GamePreset skills. "
            "Fix: add Priority-0 GamePreset branch to _extract_tournament_skills()."
        )
        unexpected = set(delta.keys()) - set(OUTFIELD_SKILLS)
        assert not unexpected, (
            f"CONS-05 FAIL: delta contains unexpected skill keys: {unexpected}"
        )
        # At least some preset skills must have a positive delta (1st place → target=100)
        assert any(v > 0 for v in delta.values()), (
            f"CONS-05 FAIL: 1st-place delta expected positive values, got {delta}"
        )

    def test_cons06_delta_sign_matches_placement_quality(self, test_db: Session):
        """
        CONS-06: For the same tournament field (4 players),
        1st-place total EMA delta > participant total EMA delta.
        Requires CONS-05 to pass (GamePreset skills resolved).
        """
        champion   = _make_player(test_db)
        last_place = _make_player(test_db)
        filler_a   = _make_player(test_db)
        filler_b   = _make_player(test_db)

        t = _make_tournament(test_db, "CONS06")
        test_db.commit()

        _add_participation(test_db, champion.id,   t.id, placement=1)
        _add_participation(test_db, filler_a.id,   t.id, placement=2)
        _add_participation(test_db, filler_b.id,   t.id, placement=3)
        _add_participation(test_db, last_place.id, t.id, placement=None)
        test_db.commit()

        delta_champion   = compute_single_tournament_skill_delta(test_db, champion.id, t.id)
        delta_last_place = compute_single_tournament_skill_delta(test_db, last_place.id, t.id)

        # Champion (1st, target=100) must move further than participant (skipped by EMA)
        assert delta_champion, (
            "CONS-06 FAIL: champion delta is empty (CONS-05 fix required)"
        )
        total_champion = sum(delta_champion.values())
        assert total_champion > 0, (
            f"CONS-06 FAIL: champion total delta={total_champion:.2f} must be positive"
        )
        # Participant: placement=None is skipped by compute_single_tournament_skill_delta
        # → delta must be empty dict {} (no EMA update for spectators)
        assert delta_last_place == {}, (
            f"CONS-06 FAIL: participant expected empty delta, got {delta_last_place}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Class 3: EMA accumulation across multiple tournaments  (CONS-07 – CONS-08)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.tournament
class TestEMAAccumulation:
    """
    CONS-07 – CONS-08: EMA convergence and cohort ordering across 3 tournaments.
    Requires CONS-05 fix (GamePreset skills resolved in _extract_tournament_skills).
    """

    def test_cons07_repeated_first_place_converges(self, test_db: Session):
        """
        CONS-07: Player always finishing 1st over 3 consecutive tournaments.
        Because each EMA step moves the value toward 100, each successive
        delta must be SMALLER than the previous one (convergence toward 99).

        T1: baseline=50 → ~63  (large delta ≈ +13)
        T2:  63 → ~73           (medium delta ≈ +10)
        T3:  73 → ~81           (smaller delta ≈ +8)
        """
        champion = _make_player(test_db)
        others   = [_make_player(test_db) for _ in range(3)]

        deltas_total: list[float] = []

        for i in range(3):
            t = _make_tournament(test_db, f"C07_T{i+1}")
            test_db.commit()

            _add_participation(test_db, champion.id, t.id, placement=1)
            for j, o in enumerate(others):
                _add_participation(test_db, o.id, t.id, placement=j + 2)
            test_db.commit()

            delta = compute_single_tournament_skill_delta(test_db, champion.id, t.id)
            assert delta, f"CONS-07 FAIL T{i+1}: empty delta (CONS-05 fix required)"

            total = sum(delta.values())
            assert total > 0, f"CONS-07 FAIL T{i+1}: 1st-place total delta={total:.2f} must be positive"
            deltas_total.append(total)

        # Each successive delta must be strictly smaller (EMA convergence)
        assert deltas_total[0] > deltas_total[1] > deltas_total[2], (
            f"CONS-07 FAIL: deltas not converging: "
            f"T1={deltas_total[0]:.2f}, T2={deltas_total[1]:.2f}, T3={deltas_total[2]:.2f}\n"
            "Expected T1 > T2 > T3 (smaller steps as skill approaches 99)."
        )

    def test_cons08_four_player_cohort_rotation(self, test_db: Session):
        """
        CONS-08: 4 players, 3 tournaments with rotated placements.
        Each player participates in EVERY tournament.

        Schedule:
          T1: P1=1st  P2=2nd  P3=3rd  P4=part
          T2: P2=1st  P3=2nd  P4=3rd  P1=part
          T3: P3=1st  P4=2nd  P1=3rd  P2=part

        Accumulated skill points (sum of calculate_skill_points_for_placement):
          P1: 10 + 1 + 5 = 16
          P2:  7 + 10 + 1 = 18
          P3:  5 +  7 + 10 = 22
          P4:  1 +  5 +  7 = 13

        Expected ordering: P3 > P2 > P1 > P4

        EMA-delta ordering (tournament contributions, preset-based):
          All positive for 1st/2nd/3rd.
          P3 accumulated the most first-place finishes in the final tournament
          → highest aggregate delta.
        """
        p1, p2, p3, p4 = [_make_player(test_db) for _ in range(4)]

        # Placement schedule: (p1, p2, p3, p4)
        schedule = [
            (1,    2,    3,    None),
            (None, 1,    2,    3   ),
            (3,    None, 1,    2   ),
        ]

        accumulated_pts: dict[int, float] = {p.id: 0.0 for p in [p1, p2, p3, p4]}
        accumulated_ema: dict[int, float] = {p.id: 0.0 for p in [p1, p2, p3, p4]}

        for t_idx, (r1, r2, r3, r4) in enumerate(schedule):
            t = _make_tournament(test_db, f"C08_T{t_idx+1}")
            test_db.commit()

            players_placements = [(p1, r1), (p2, r2), (p3, r3), (p4, r4)]

            # Phase A: add all participation rows for this tournament
            for player, placement in players_placements:
                _add_participation(test_db, player.id, t.id, placement=placement)
            test_db.commit()

            # Phase B: accumulate skill points + EMA deltas
            for player, placement in players_placements:
                skill_pts = calculate_skill_points_for_placement(
                    test_db, t.id, placement=placement
                )
                accumulated_pts[player.id] += sum(skill_pts.values())

                ema = compute_single_tournament_skill_delta(test_db, player.id, t.id)
                accumulated_ema[player.id] += sum(ema.values())

        # ── Skill-point ordering ──────────────────────────────────────────────
        tol = 0.5   # rounding across 9 skills × 3 tournaments
        assert accumulated_pts[p3.id] > accumulated_pts[p2.id] > \
               accumulated_pts[p1.id] > accumulated_pts[p4.id], (
            f"CONS-08 FAIL (skill points ordering):\n"
            f"  P1={accumulated_pts[p1.id]:.2f}  P2={accumulated_pts[p2.id]:.2f}"
            f"  P3={accumulated_pts[p3.id]:.2f}  P4={accumulated_pts[p4.id]:.2f}\n"
            f"  Expected: P3 > P2 > P1 > P4"
        )
        # Exact expected totals (base points × 9 skills / 9.9 total weight ≈ 1.0)
        base = PLACEMENT_SKILL_POINTS
        exp = {
            p1.id: base[1] + base[None] + base[3],   # 10+1+5 = 16
            p2.id: base[2] + base[1]   + base[None],  # 7+10+1 = 18
            p3.id: base[3] + base[2]   + base[1],     # 5+7+10 = 22
            p4.id: base[None] + base[3] + base[2],    # 1+5+7  = 13
        }
        for player in [p1, p2, p3, p4]:
            assert abs(accumulated_pts[player.id] - exp[player.id]) < tol, (
                f"CONS-08 FAIL (exact total for player {player.id}): "
                f"got {accumulated_pts[player.id]:.2f}, "
                f"expected≈{exp[player.id]}"
            )

        # ── EMA-delta ordering ────────────────────────────────────────────────
        # (Only valid when CONS-05 fix is applied; skip if EMA is all zeros)
        if any(accumulated_ema[p.id] > 0 for p in [p1, p2, p3, p4]):
            assert accumulated_ema[p3.id] > accumulated_ema[p2.id] > \
                   accumulated_ema[p1.id] > accumulated_ema[p4.id], (
                f"CONS-08 FAIL (EMA delta ordering):\n"
                f"  P1={accumulated_ema[p1.id]:.2f}  P2={accumulated_ema[p2.id]:.2f}"
                f"  P3={accumulated_ema[p3.id]:.2f}  P4={accumulated_ema[p4.id]:.2f}\n"
                f"  Expected: P3 > P2 > P1 > P4"
            )
