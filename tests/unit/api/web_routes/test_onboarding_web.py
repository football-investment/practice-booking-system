"""
Unit tests for app/api/web_routes/onboarding.py

Covers unique routes (not duplicated in specialization.py):
  specialization_select_page — renders select template with user licenses
  specialization_select_submit — invalid spec renders error, insufficient credits → /dashboard,
                                  existing license → no credit deduction, lfa-player → lfa onboarding URL,
                                  other spec → motivation URL
  lfa_player_onboarding_page (onboarding.py version) — no license → /dashboard,
                                                        completed → /dashboard, valid → template
  lfa_player_onboarding_cancel (onboarding.py version) — no license → /dashboard, cancel → refund
  lfa_player_onboarding_submit — invalid position → 500, no license → 500, valid → success dict
  onboarding_start — renders onboarding_new.html, age=None skips spec lookup
  onboarding_set_birthdate — invalid format → 400, too young → 400, valid → /onboarding/start

Note: onboarding.py missing imports (SpecializationType, CreditTransaction, TransactionType,
      get_available_specializations) were fixed in Sprint 54 P0. create=True removed.
"""
import asyncio
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.api.web_routes.onboarding import (
    lfa_player_onboarding_cancel,
    lfa_player_onboarding_page,
    lfa_player_onboarding_submit,
    onboarding_set_birthdate,
    onboarding_start,
    specialization_select_page,
    specialization_select_submit,
)
from app.models.user import UserRole
from app.models.specialization import SpecializationType

_BASE = "app.api.web_routes.onboarding"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _req():
    return MagicMock()


def _user(uid=99, credit_balance=200, age=20):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.STUDENT
    u.email = "student@test.com"
    u.credit_balance = credit_balance
    u.age = age
    u.onboarding_completed = False
    return u


def _mock_db(first_return=None, all_return=None, user_return=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = first_return
    db.query.return_value.filter.return_value.all.return_value = all_return or []
    db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = first_return
    # SELECT FOR UPDATE chain (user re-query in specialization_select_submit)
    _ur = user_return if user_return is not None else first_return
    db.query.return_value.with_for_update.return_value.filter.return_value.first.return_value = _ur
    return db


# ──────────────────────────────────────────────────────────────────────────────
# specialization_select_page (GET /specialization/select)
# ──────────────────────────────────────────────────────────────────────────────

class TestSpecializationSelectPage:

    def test_renders_select_template(self):
        user = _user()
        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(specialization_select_page(request=_req(), db=_mock_db(), user=user))
        tmpl, _ = mock_tmpl.TemplateResponse.call_args.args
        assert tmpl == "specialization_select.html"

    def test_context_includes_user_license_types(self):
        license_mock = MagicMock()
        license_mock.specialization_type = "LFA_FOOTBALL_PLAYER"
        user = _user()
        db = _mock_db(all_return=[license_mock])
        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(specialization_select_page(request=_req(), db=db, user=user))
        _, ctx = mock_tmpl.TemplateResponse.call_args.args
        assert "LFA_FOOTBALL_PLAYER" in ctx["user_specialization_types"]

    def test_context_includes_active_specializations_dict(self):
        user = _user()
        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(specialization_select_page(request=_req(), db=_mock_db(), user=user))
        _, ctx = mock_tmpl.TemplateResponse.call_args.args
        assert "active_specializations" in ctx
        assert "LFA_FOOTBALL_PLAYER" in ctx["active_specializations"]


# ──────────────────────────────────────────────────────────────────────────────
# specialization_select_submit (POST /specialization/select)
# ──────────────────────────────────────────────────────────────────────────────

class TestSpecializationSelectSubmit:

    def _run_submit(self, user, spec, db=None):
        if db is None:
            db = _mock_db()
        with patch(f"{_BASE}.SpecializationType", SpecializationType), \
             patch(f"{_BASE}.CreditTransaction", MagicMock()), \
             patch(f"{_BASE}.TransactionType", MagicMock()), \
             patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            result = _run(specialization_select_submit(
                request=_req(), specialization=spec, db=db, user=user
            ))
        return result, mock_tmpl

    def test_invalid_spec_renders_error_template(self):
        user = _user()
        result, mock_tmpl = self._run_submit(user, "TOTALLY_INVALID")
        tmpl, ctx = mock_tmpl.TemplateResponse.call_args.args
        assert tmpl == "specialization_select.html"
        assert "error" in ctx

    def test_insufficient_credits_redirects_to_dashboard(self):
        user = _user(credit_balance=50)
        # user_return=user: SELECT FOR UPDATE re-query returns the real user mock (50 credits < 100)
        db = _mock_db(first_return=None, user_return=user)
        result, _ = self._run_submit(user, "LFA_FOOTBALL_PLAYER", db=db)
        assert isinstance(result, RedirectResponse)
        assert "/dashboard" in result.headers["location"]

    def test_existing_license_skips_credit_deduction(self):
        license_mock = MagicMock()
        user = _user(credit_balance=200)
        # user_return=user: SELECT FOR UPDATE returns user; first_return=license_mock: license check returns existing
        db = _mock_db(first_return=license_mock, user_return=user)
        result, _ = self._run_submit(user, "LFA_FOOTBALL_PLAYER", db=db)
        assert isinstance(result, RedirectResponse)
        assert user.credit_balance == 200  # Credits NOT deducted (license already exists)
        # Guard: existing license path still redirects to the correct onboarding URL
        assert "lfa-player/onboarding" in result.headers["location"]

    def test_lfa_player_redirects_to_lfa_onboarding(self):
        user = _user(credit_balance=200)
        # user_return=user: SELECT FOR UPDATE re-query returns the same user (with 200 credits)
        # first_return=None: license check returns None → new unlock path
        db = _mock_db(first_return=None, user_return=user)
        result, _ = self._run_submit(user, "LFA_FOOTBALL_PLAYER", db=db)
        assert isinstance(result, RedirectResponse)
        assert "lfa-player/onboarding" in result.headers["location"]

    def test_non_lfa_spec_redirects_to_motivation(self):
        user = _user(credit_balance=200)
        db = _mock_db(first_return=None, user_return=user)
        result, _ = self._run_submit(user, "GANCUJU_PLAYER", db=db)
        assert isinstance(result, RedirectResponse)
        assert "motivation" in result.headers["location"]

    def test_credit_boundary_99_is_rejected(self):
        """credit_balance=99 < 100 → insufficient credits → /dashboard redirect."""
        user = _user(credit_balance=99)
        db = _mock_db(first_return=None, user_return=user)
        result, _ = self._run_submit(user, "LFA_FOOTBALL_PLAYER", db=db)
        assert isinstance(result, RedirectResponse)
        assert "/dashboard" in result.headers["location"]

    def test_credit_boundary_100_is_accepted(self):
        """credit_balance=100 == 100 → exactly enough → proceed to lfa onboarding redirect."""
        user = _user(credit_balance=100)
        db = _mock_db(first_return=None, user_return=user)
        result, _ = self._run_submit(user, "LFA_FOOTBALL_PLAYER", db=db)
        assert isinstance(result, RedirectResponse)
        assert "lfa-player/onboarding" in result.headers["location"]

    def test_integrity_error_during_license_creation_redirects_to_dashboard(self):
        """IntegrityError during DB commit (race condition duplicate) → 303 /dashboard."""
        from sqlalchemy.exc import IntegrityError
        user = _user(credit_balance=200)
        db = _mock_db(first_return=None, user_return=user)
        db.flush.side_effect = IntegrityError("duplicate", {}, Exception())

        result, _ = self._run_submit(user, "LFA_FOOTBALL_PLAYER", db=db)

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 303
        assert result.headers["location"] == "/dashboard"


# ──────────────────────────────────────────────────────────────────────────────
# lfa_player_onboarding_page (onboarding.py version — same logic as specialization.py)
# ──────────────────────────────────────────────────────────────────────────────

class TestOnboardingLfaPlayerPage:

    def test_no_license_redirects_to_dashboard(self):
        user = _user()
        result = _run(lfa_player_onboarding_page(
            request=_req(), db=_mock_db(first_return=None), user=user
        ))
        assert isinstance(result, RedirectResponse)
        assert "/dashboard" in result.headers["location"]

    def test_completed_onboarding_redirects_to_dashboard(self):
        license_mock = MagicMock()
        license_mock.onboarding_completed = True
        user = _user()
        result = _run(lfa_player_onboarding_page(
            request=_req(), db=_mock_db(first_return=license_mock), user=user
        ))
        assert isinstance(result, RedirectResponse)

    def test_incomplete_license_renders_template(self):
        license_mock = MagicMock()
        license_mock.onboarding_completed = False
        user = _user()
        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(lfa_player_onboarding_page(
                request=_req(), db=_mock_db(first_return=license_mock), user=user
            ))
        tmpl, _ = mock_tmpl.TemplateResponse.call_args.args
        assert tmpl == "lfa_player_onboarding.html"


# ──────────────────────────────────────────────────────────────────────────────
# lfa_player_onboarding_cancel (onboarding.py version)
# ──────────────────────────────────────────────────────────────────────────────

class TestOnboardingLfaPlayerCancel:

    def test_no_license_redirects_to_dashboard(self):
        user = _user()
        result = _run(lfa_player_onboarding_cancel(
            request=_req(), db=_mock_db(first_return=None), user=user
        ))
        assert isinstance(result, RedirectResponse)
        assert "/dashboard" in result.headers["location"]

    def test_incomplete_license_refunds_and_redirects(self):
        license_mock = MagicMock()
        license_mock.id = 1
        user = _user(credit_balance=0)
        db = _mock_db(first_return=license_mock)
        with patch(f"{_BASE}.CreditTransaction", MagicMock()), \
             patch(f"{_BASE}.TransactionType", MagicMock()):
            result = _run(lfa_player_onboarding_cancel(
                request=_req(), db=db, user=user
            ))
        assert isinstance(result, RedirectResponse)
        assert user.credit_balance == 100
        db.delete.assert_called_once_with(license_mock)


# ──────────────────────────────────────────────────────────────────────────────
# lfa_player_onboarding_submit (POST /specialization/lfa-player/onboarding-submit)
# ──────────────────────────────────────────────────────────────────────────────

class TestLfaPlayerOnboardingSubmit:

    def _make_req(self, body: dict):
        r = MagicMock()
        r.json = AsyncMock(return_value=body)
        return r

    def _valid_body(self):
        return {
            "position": "STRIKER",
            "goals": "Win",
            "motivation": "Love football",
            "skills": {f"skill_{i}": 50 for i in range(36)},
        }

    def test_invalid_position_raises_500(self):
        body = self._valid_body()
        body["position"] = "INVALID_POS"
        user = _user()
        db = _mock_db(first_return=MagicMock())
        with patch("app.skills_config.get_all_skill_keys", return_value=list(body["skills"].keys())):
            with pytest.raises(HTTPException) as exc_info:
                _run(lfa_player_onboarding_submit(
                    request=self._make_req(body), db=db, user=user
                ))
        assert exc_info.value.status_code == 500

    def test_no_license_raises_500(self):
        body = self._valid_body()
        user = _user()
        db = _mock_db(first_return=None)
        with patch("app.skills_config.get_all_skill_keys", return_value=list(body["skills"].keys())):
            with pytest.raises(HTTPException) as exc_info:
                _run(lfa_player_onboarding_submit(
                    request=self._make_req(body), db=db, user=user
                ))
        assert exc_info.value.status_code == 500

    def test_valid_submit_returns_success(self):
        body = self._valid_body()
        license_mock = MagicMock()
        user = _user()
        db = _mock_db(first_return=license_mock)
        with patch("app.skills_config.get_all_skill_keys", return_value=list(body["skills"].keys())):
            result = _run(lfa_player_onboarding_submit(
                request=self._make_req(body), db=db, user=user
            ))
        assert result["success"] is True
        assert license_mock.onboarding_completed is True
        db.commit.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# onboarding_start (GET /onboarding/start)
# ──────────────────────────────────────────────────────────────────────────────

class TestOnboardingStart:

    def test_renders_onboarding_template(self):
        user = _user(age=None)  # No age → skip spec lookup
        with patch(f"{_BASE}.get_available_specializations", MagicMock(return_value=[])), \
             patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(onboarding_start(request=_req(), db=_mock_db(), user=user))
        tmpl, _ = mock_tmpl.TemplateResponse.call_args.args
        assert tmpl == "student/onboarding_new.html"

    def test_user_with_age_calls_get_available_specializations(self):
        user = _user(age=18)
        mock_specs = [{"name": "LFA_FOOTBALL_PLAYER"}]
        mock_get = MagicMock(return_value=mock_specs)
        with patch(f"{_BASE}.get_available_specializations", mock_get), \
             patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(onboarding_start(request=_req(), db=_mock_db(), user=user))
        mock_get.assert_called_once_with(18)
        _, ctx = mock_tmpl.TemplateResponse.call_args.args
        assert ctx["available_specs"] == mock_specs


# ──────────────────────────────────────────────────────────────────────────────
# onboarding_set_birthdate (POST /onboarding/set-birthdate)
# ──────────────────────────────────────────────────────────────────────────────

class TestOnboardingSetBirthdate:

    def test_invalid_date_format_raises_400(self):
        user = _user()
        with pytest.raises(HTTPException) as exc_info:
            _run(onboarding_set_birthdate(
                request=_req(), date_of_birth="not-a-date", db=_mock_db(), user=user
            ))
        assert exc_info.value.status_code == 400

    def test_too_young_raises_400(self):
        user = _user()
        dob = f"{date.today().year - 2}-01-01"
        with pytest.raises(HTTPException) as exc_info:
            _run(onboarding_set_birthdate(
                request=_req(), date_of_birth=dob, db=_mock_db(), user=user
            ))
        assert exc_info.value.status_code == 400
        assert "5" in exc_info.value.detail

    def test_valid_dob_saves_and_redirects(self):
        user = _user()
        db = _mock_db()
        result = _run(onboarding_set_birthdate(
            request=_req(), date_of_birth="2000-06-15", db=db, user=user
        ))
        assert isinstance(result, RedirectResponse)
        assert "/onboarding/start" in result.headers["location"]
        db.commit.assert_called_once()

    def test_valid_dob_sets_user_date_of_birth(self):
        user = _user()
        db = _mock_db()
        _run(onboarding_set_birthdate(
            request=_req(), date_of_birth="1998-03-20", db=db, user=user
        ))
        assert user.date_of_birth == date(1998, 3, 20)
