"""
Unit tests for P1 onboarding height/weight/preferred_foot fields.

Handler tests (web submit — cookie auth):
  OB-H1  missing height_cm → 422
  OB-H2  invalid height_cm (below range) → 422
  OB-H3  invalid height_cm (above range) → 422
  OB-W1  missing weight_kg → 422
  OB-W2  invalid weight_kg (below range) → 422
  OB-W3  invalid weight_kg (above range) → 422
  OB-F1  missing preferred_foot → 422
  OB-F2  invalid preferred_foot value → 422
  OB-V1  valid full payload → motivation_scores contains height_cm, weight_kg, preferred_foot
  OB-V2  valid full payload → onboarding_completed=True

Service gate tests (complete_lfa_player_onboarding):
  OB-SG1 motivation_scores missing height_cm → ValueError, onboarding_completed NOT set
  OB-SG2 motivation_scores missing weight_kg → ValueError, onboarding_completed NOT set
  OB-SG3 motivation_scores missing preferred_foot → ValueError, onboarding_completed NOT set
  OB-SG4 motivation_scores has all required fields → completes successfully
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.web_routes.onboarding import lfa_player_onboarding_web_submit
from app.services.onboarding_service import complete_lfa_player_onboarding
from app.models.user import UserRole

_PATCH_COMPLETE = "app.services.onboarding_service.complete_lfa_player_onboarding"
_PATCH_FLAG     = "sqlalchemy.orm.attributes.flag_modified"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


def _user(uid=99):
    u = MagicMock()
    u.id    = uid
    u.role  = UserRole.STUDENT
    u.email = "new.player@test.com"
    return u


def _mock_db(license_mock=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = (
        license_mock if license_mock is not None else MagicMock()
    )
    return db


def _valid_skills():
    from app.services.skill_progression._config import get_all_skill_keys
    return {k: 60 for k in get_all_skill_keys()}


def _valid_body(**overrides):
    body = {
        "position":      "MIDFIELDER",
        "goals":         "improve_skills",
        "motivation":    "",
        "skills":        _valid_skills(),
        "foot_dominance": 60,
        "height_cm":     175,
        "weight_kg":     72,
        "preferred_foot": "right",
    }
    body.update(overrides)
    return body


def _req(body: dict):
    r = MagicMock()
    r.json = AsyncMock(return_value=body)
    return r


# ---------------------------------------------------------------------------
# Handler tests (OB-H1 .. OB-V2)
# ---------------------------------------------------------------------------

class TestOnboardingHeightWeightValidation:

    # ── height_cm ──────────────────────────────────────────────────────────

    def test_ob_h1_missing_height_422(self):
        """OB-H1: height_cm absent from payload → 422."""
        body = _valid_body()
        del body["height_cm"]
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(body), db=db, user=_user()
        ))

        assert result.status_code == 422

    def test_ob_h2_height_below_range_422(self):
        """OB-H2: height_cm=119 (below 120) → 422."""
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(_valid_body(height_cm=119)), db=db, user=_user()
        ))

        assert result.status_code == 422

    def test_ob_h3_height_above_range_422(self):
        """OB-H3: height_cm=231 (above 230) → 422."""
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(_valid_body(height_cm=231)), db=db, user=_user()
        ))

        assert result.status_code == 422

    # ── weight_kg ──────────────────────────────────────────────────────────

    def test_ob_w1_missing_weight_422(self):
        """OB-W1: weight_kg absent from payload → 422."""
        body = _valid_body()
        del body["weight_kg"]
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(body), db=db, user=_user()
        ))

        assert result.status_code == 422

    def test_ob_w2_weight_below_range_422(self):
        """OB-W2: weight_kg=34 (below 35) → 422."""
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(_valid_body(weight_kg=34)), db=db, user=_user()
        ))

        assert result.status_code == 422

    def test_ob_w3_weight_above_range_422(self):
        """OB-W3: weight_kg=161 (above 160) → 422."""
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(_valid_body(weight_kg=161)), db=db, user=_user()
        ))

        assert result.status_code == 422

    # ── preferred_foot ─────────────────────────────────────────────────────

    def test_ob_f1_missing_preferred_foot_422(self):
        """OB-F1: preferred_foot absent from payload → 422."""
        body = _valid_body()
        del body["preferred_foot"]
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(body), db=db, user=_user()
        ))

        assert result.status_code == 422

    def test_ob_f2_invalid_preferred_foot_422(self):
        """OB-F2: preferred_foot='center' (invalid) → 422."""
        db = _mock_db()

        result = _run(lfa_player_onboarding_web_submit(
            request=_req(_valid_body(preferred_foot="center")), db=db, user=_user()
        ))

        assert result.status_code == 422

    # ── valid payload ──────────────────────────────────────────────────────

    def test_ob_v1_valid_payload_saves_height_weight_foot(self):
        """OB-V1: valid payload → motivation_scores contains height_cm, weight_kg, preferred_foot."""
        license_mock = MagicMock()
        db = _mock_db(license_mock)

        with patch(_PATCH_COMPLETE), patch(_PATCH_FLAG):
            result = _run(lfa_player_onboarding_web_submit(
                request=_req(_valid_body(height_cm=178, weight_kg=74, preferred_foot="both")),
                db=db,
                user=_user(),
            ))

        assert result.get("success") is True
        ms = license_mock.motivation_scores
        assert ms["height_cm"]      == 178
        assert ms["weight_kg"]      == 74
        assert ms["preferred_foot"] == "both"

    def test_ob_v2_valid_payload_calls_complete(self):
        """OB-V2: valid payload → complete_lfa_player_onboarding is called (onboarding_completed set)."""
        license_mock = MagicMock()
        db = _mock_db(license_mock)

        with patch(_PATCH_COMPLETE) as mock_complete, patch(_PATCH_FLAG):
            _run(lfa_player_onboarding_web_submit(
                request=_req(_valid_body()),
                db=db,
                user=_user(),
            ))

        mock_complete.assert_called_once()


# ---------------------------------------------------------------------------
# Service gate tests (OB-SG1 .. OB-SG4)
# ---------------------------------------------------------------------------

class TestOnboardingServiceCompletionGate:
    """Tests for complete_lfa_player_onboarding() completion guard."""

    def _make_license(self, motivation_scores=None):
        lic = MagicMock()
        lic.motivation_scores = motivation_scores or {}
        lic.onboarding_completed = False
        return lic

    def _make_user(self):
        u = MagicMock()
        u.onboarding_completed = False
        return u

    def _valid_skills(self):
        return {"skill_0": {"current_level": 60.0}}

    def test_ob_sg1_missing_height_cm_raises(self):
        """OB-SG1: motivation_scores missing height_cm → ValueError, not completed."""
        lic = self._make_license({"weight_kg": 72, "preferred_foot": "right"})
        u   = self._make_user()

        with pytest.raises(ValueError, match="height_cm"):
            complete_lfa_player_onboarding(MagicMock(), u, lic, self._valid_skills())

        assert lic.onboarding_completed is False
        assert u.onboarding_completed   is False

    def test_ob_sg2_missing_weight_kg_raises(self):
        """OB-SG2: motivation_scores missing weight_kg → ValueError, not completed."""
        lic = self._make_license({"height_cm": 175, "preferred_foot": "right"})
        u   = self._make_user()

        with pytest.raises(ValueError, match="weight_kg"):
            complete_lfa_player_onboarding(MagicMock(), u, lic, self._valid_skills())

        assert lic.onboarding_completed is False

    def test_ob_sg3_missing_preferred_foot_raises(self):
        """OB-SG3: motivation_scores missing preferred_foot → ValueError, not completed."""
        lic = self._make_license({"height_cm": 175, "weight_kg": 72})
        u   = self._make_user()

        with pytest.raises(ValueError, match="preferred_foot"):
            complete_lfa_player_onboarding(MagicMock(), u, lic, self._valid_skills())

        assert lic.onboarding_completed is False

    def test_ob_sg4_all_required_fields_completes(self):
        """OB-SG4: motivation_scores has all required fields → onboarding_completed=True."""
        lic = self._make_license({
            "height_cm": 175, "weight_kg": 72, "preferred_foot": "right"
        })
        u = self._make_user()
        skills = self._valid_skills()

        complete_lfa_player_onboarding(MagicMock(), u, lic, skills)

        assert lic.onboarding_completed is True
        assert u.onboarding_completed   is True
        assert lic.football_skills      is skills
