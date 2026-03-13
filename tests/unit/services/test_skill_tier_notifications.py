"""
Unit tests for ENABLE_SKILL_TIER_NOTIFICATIONS feature (Sprint P5).

Covers the tier-crossing check injected into update_skill_assessments():

  TIER-U-01  flag=True, old=55 + delta=+6 → new=61, crosses 60 → Intermediate
  TIER-U-02  flag=False, same delta → no notification
  TIER-U-03  old=62, delta=+4 → new=66, stays in Intermediate → no notification
  TIER-U-04  old=72, delta=+5 → new=77, crosses 75 → Advanced
  TIER-U-05  old=88, delta=+4 → new=92, crosses 90 → Expert
  TIER-U-06  old=60, delta=-3 → new=57, regression → no notification
  TIER-U-07  old=58, delta=+35 → new=93, crosses 60 first (break) → Intermediate only
  TIER-U-08  old=99, delta=+1 → clamped to 99, no crossing → no notification

Mock strategy (mirrors PROP-U-* tests):
  - patch settings.ENABLE_TOURNAMENT_SKILL_PROPAGATION = True
  - patch settings.ENABLE_SKILL_TIER_NOTIFICATIONS = True / False
  - patch settings.SKILL_TIER_THRESHOLDS = {60: "Intermediate", 75: "Advanced", 90: "Expert"}
  - patch create_skill_tier_notification and assert call count / args
  - Use _db() helper matching the double .first() call pattern in update_skill_assessments()
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.tournament.tournament_participation_service import update_skill_assessments
from app.models.football_skill_assessment import FootballSkillAssessment


_BASE = "app.services.tournament.tournament_participation_service"

_USER_ID = 42
_LICENSE_ID = 7
_TOURNAMENT_ID = 99

_THRESHOLDS = {60: "Intermediate", 75: "Advanced", 90: "Expert"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _db(existing_pct: float):
    """
    Build a MagicMock db whose query chain returns predictable values for a
    single-skill scenario.

    Call sequence (same as PROP-U helper):
      Call 0  → license
      Call 1  → existing assessment (order_by path)
      Call 2  → idempotency guard → None
    """
    db = MagicMock()
    call_count = [0]

    lic = MagicMock()
    lic.id = _LICENSE_ID

    existing = MagicMock(spec=FootballSkillAssessment)
    existing.percentage = existing_pct
    existing.status = "ASSESSED"

    def query_side_effect(model):
        m = MagicMock()

        def filter_side_effect(*args, **kwargs):
            fm = MagicMock()

            def first_side_effect():
                idx = call_count[0]
                call_count[0] += 1
                if idx == 0:
                    return lic
                elif idx == 1:
                    return existing  # existing assessment
                else:
                    return None  # idempotency guard

            fm.first = first_side_effect

            def order_by_side_effect(*args):
                om = MagicMock()
                om.first = first_side_effect
                return om

            fm.order_by = order_by_side_effect
            return fm

        m.filter = filter_side_effect
        return m

    db.query.side_effect = query_side_effect
    return db


def _call_update(db, delta: float, flag: bool = True) -> MagicMock:
    """
    Call update_skill_assessments with a single-skill delta dict and return
    the mocked create_skill_tier_notification.
    """
    with patch(f"{_BASE}.settings") as mock_settings, \
         patch(f"{_BASE}.create_skill_tier_notification") as mock_notify:

        mock_settings.ENABLE_TOURNAMENT_SKILL_PROPAGATION = True
        mock_settings.ENABLE_SKILL_TIER_NOTIFICATIONS = flag
        mock_settings.SKILL_TIER_THRESHOLDS = _THRESHOLDS

        update_skill_assessments(
            db=db,
            user_id=_USER_ID,
            skill_points={},
            skill_rating_delta={"finishing": delta},
            tournament_id=_TOURNAMENT_ID,
        )
        return mock_notify


# ── TIER-U-01: crosses 60 → Intermediate ─────────────────────────────────────

def test_tier_u01_crosses_intermediate_notifies():
    # old=55.0 + delta=+6.0 → new=61.0; 55 < 60 <= 61 → Intermediate
    db = _db(existing_pct=55.0)
    mock_notify = _call_update(db, delta=6.0, flag=True)

    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert kwargs["tier_name"] == "Intermediate"
    assert kwargs["user_id"] == _USER_ID
    assert kwargs["skill_name"] == "finishing"
    assert kwargs["tournament_id"] == _TOURNAMENT_ID
    assert abs(kwargs["new_pct"] - 61.0) < 0.1


# ── TIER-U-02: flag=False → no notification ───────────────────────────────────

def test_tier_u02_flag_disabled_no_notification():
    # same scenario as TIER-U-01 but flag is off
    db = _db(existing_pct=55.0)
    mock_notify = _call_update(db, delta=6.0, flag=False)

    mock_notify.assert_not_called()


# ── TIER-U-03: stays in tier → no notification ────────────────────────────────

def test_tier_u03_stays_in_intermediate_no_notification():
    # old=62 + delta=+4 → new=66; no threshold crossed (all below 66 already passed)
    db = _db(existing_pct=62.0)
    mock_notify = _call_update(db, delta=4.0, flag=True)

    mock_notify.assert_not_called()


# ── TIER-U-04: crosses 75 → Advanced ─────────────────────────────────────────

def test_tier_u04_crosses_advanced_notifies():
    # old=72 + delta=+5 → new=77; 72 < 75 <= 77 → Advanced
    db = _db(existing_pct=72.0)
    mock_notify = _call_update(db, delta=5.0, flag=True)

    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert kwargs["tier_name"] == "Advanced"
    assert abs(kwargs["new_pct"] - 77.0) < 0.1


# ── TIER-U-05: crosses 90 → Expert ───────────────────────────────────────────

def test_tier_u05_crosses_expert_notifies():
    # old=88 + delta=+4 → new=92; 88 < 90 <= 92 → Expert
    db = _db(existing_pct=88.0)
    mock_notify = _call_update(db, delta=4.0, flag=True)

    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert kwargs["tier_name"] == "Expert"
    assert abs(kwargs["new_pct"] - 92.0) < 0.1


# ── TIER-U-06: regression → no notification ───────────────────────────────────

def test_tier_u06_regression_no_notification():
    # old=60 + delta=-3 → new=57; old_pct < threshold check: 60 < 60 is False
    db = _db(existing_pct=60.0)
    mock_notify = _call_update(db, delta=-3.0, flag=True)

    mock_notify.assert_not_called()


# ── TIER-U-07: skips multiple thresholds, only first notified ─────────────────

def test_tier_u07_skips_multiple_thresholds_first_only():
    # old=58 + delta=+35 → new=93; crosses 60, 75, 90 — break after 60
    db = _db(existing_pct=58.0)
    mock_notify = _call_update(db, delta=35.0, flag=True)

    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert kwargs["tier_name"] == "Intermediate", (
        "Should notify only the first (lowest) crossed threshold"
    )


# ── TIER-U-08: already capped at 99, clamping → no crossing ──────────────────

def test_tier_u08_clamped_at_99_no_crossing():
    # old=99 + delta=+1 → raw=100, clamped to 99; no threshold crossed
    db = _db(existing_pct=99.0)
    mock_notify = _call_update(db, delta=1.0, flag=True)

    mock_notify.assert_not_called()
