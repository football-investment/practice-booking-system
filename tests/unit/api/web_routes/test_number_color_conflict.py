"""Unit tests for Number-Color Conflict — Phase 2.3.

Route tests:
NCC-01   GET /virtual-training/number-color-conflict → 200 active game
NCC-02   GET /virtual-training/number-color-conflict → hub redirect when game inactive
NCC-03   GET /virtual-training/number-color-conflict → 303 non-student / non-onboarded
NCC-04   POST /virtual-training/number-color-conflict/submit → 200 valid data
NCC-05   POST submit → is_valid=False + 0 XP too_short
NCC-06   POST submit → is_valid=False + 0 XP bot_suspected
NCC-07   POST submit → 429 daily cap
NCC-08   POST submit → 404 inactive game
NCC-09   POST submit → 403 not onboarded
NCC-10   GET /virtual-training/number-color-conflict/result/{id} → 200 owner
NCC-11   GET result → hub redirect wrong user (attempt not found)
NCC-12   POST submit → idempotency key includes 'ncc'

Skill scorer tests (reuses existing scorers — no new scorer):
NCC-13   score_decisions(hit=1.0, wrong=0.0) → 1.0
NCC-14   score_decisions(hit=0.5, wrong=0.2) → 0.5 - 0.3 = 0.2
NCC-15   score_concentration(miss=0.0) → 1.0
NCC-16   score_composure(wrong=0.0) → 1.0
NCC-17   score_all() for NCC skill_targets covers all 4 skills

Performance delta tests:
NCC-18   Perfect NCC run → all four deltas positive
NCC-19   Wrong-heavy run → decisions and composure delta near zero or negative
NCC-20   Missed-heavy run → concentration delta near zero or negative

raw_metrics v3 tests:
NCC-21   Payload with v=3 hand_profile → protocol_difficulty_multiplier extracted
NCC-22   v3 late_summary.late_click_count → late_click_rate in signals
NCC-23   v1 payload (no hand_profile) → PDM defaults to 1.0

Template / link tests:
NCC-24   virtual_training_number_color_conflict.html exists in templates dir
NCC-25   virtual_training_number_color_conflict_result.html exists in templates dir
NCC-26   Result template references 'nccr-breakdown' (skill breakdown present)
NCC-27   Result template references 'decisions' formula note
NCC-28   Game template references 'ncc-protocol-card' (Today's Protocol card)

Seed:
NCC-SEED-01  number_color_conflict is_active=True in seed data
NCC-SEED-02  number_color_conflict config includes phases, numbers, colors, late_grace_ms
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import HTMLResponse, RedirectResponse

_ROUTES = "app.api.web_routes.virtual_training"
_METRICS = "app.services.virtual_training_metrics"
_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "app" / "templates"


def _run(coro):
    return asyncio.run(coro)


_NCC_SKILL_TARGETS = {
    "decisions":     0.40,
    "concentration": 0.30,
    "composure":     0.20,
    "reactions":     0.10,
}

_NCC_CONFIG = {
    "phases": [
        {"stimuli": 10, "window_ms": 2000, "isi_ms": 900,  "rule_switch": "alternating"},
        {"stimuli": 12, "window_ms": 1600, "isi_ms": 700,  "rule_switch": "random"},
        {"stimuli": 14, "window_ms": 1200, "isi_ms": 550,  "rule_switch": "random_high"},
    ],
    "numbers": [1, 2, 3, 4],
    "colors": {
        "RED":    "#ef4444",
        "GREEN":  "#22c55e",
        "BLUE":   "#3b82f6",
        "YELLOW": "#eab308",
    },
    "late_grace_ms": 350,
    "show_in_hub": True,
    "icon": "🔢",
    "football_benefit": "Filtering conflicting information.",
}


def _mock_ncc_game(*, is_active: bool = True) -> MagicMock:
    g = MagicMock()
    g.id                 = 5
    g.code               = "number_color_conflict"
    g.name               = "Number-Color Conflict"
    g.is_active          = is_active
    g.base_xp            = 12
    g.max_daily_attempts = 5
    g.skill_targets      = _NCC_SKILL_TARGETS
    g.config             = _NCC_CONFIG
    return g


def _mock_attempt(
    *,
    id: int = 55,
    user_id: int = 42,
    game_id: int = 5,
    is_valid: bool = True,
    xp_awarded: int = 12,
    score_normalized: float = 72.0,
    attempt_index_today: int = 1,
    invalid_reason: str | None = None,
    skill_deltas: dict | None = None,
    correct_count: int = 28,
    wrong_click_count: int = 4,
    error_count: int = 4,
    avg_reaction_ms: float = 620.0,
    stimuli_count: int = 36,
    duration_seconds: float = 55.0,
    raw_metrics: dict | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id                  = id
    a.user_id             = user_id
    a.game_id             = game_id
    a.is_valid            = is_valid
    a.xp_awarded          = xp_awarded
    a.score_normalized    = score_normalized
    a.attempt_index_today = attempt_index_today
    a.invalid_reason      = invalid_reason
    a.skill_deltas        = skill_deltas or {
        "decisions": 0.18, "concentration": 0.14,
        "composure": 0.09, "reactions": 0.04,
    }
    a.correct_count       = correct_count
    a.wrong_click_count   = wrong_click_count
    a.error_count         = error_count
    a.avg_reaction_ms     = avg_reaction_ms
    a.stimuli_count       = stimuli_count
    a.duration_seconds    = duration_seconds
    a.raw_metrics         = raw_metrics
    return a


def _mock_db(*, count: int = 0) -> MagicMock:
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value  = q
    q.count.return_value   = count
    q.first.return_value   = None
    q.all.return_value     = []
    db.query.return_value  = q
    return db


def _make_student(user_id: int = 42) -> MagicMock:
    from app.models.user import UserRole
    u = MagicMock()
    u.id = user_id
    u.role = UserRole.STUDENT
    u.onboarding_completed = True
    u.credit_balance = 0
    u.specialization = MagicMock()
    u.specialization.value = "LFA_FOOTBALL_PLAYER"
    return u


def _make_request(path: str = "/virtual-training/number-color-conflict") -> MagicMock:
    r = MagicMock()
    r.url.path = path
    r.cookies  = {}
    return r


def _valid_payload() -> dict:
    return {
        "started_at":        "2026-05-23T10:00:00.000Z",
        "duration_seconds":  56.0,
        "stimuli_count":     36,
        "correct_count":     28,
        "wrong_click_count": 4,
        "error_count":       4,
        "avg_reaction_ms":   620.0,
        "score_normalized":  72.0,
        "raw_metrics": {
            "v": 3,
            "per_phase": [],
            "per_stimulus": [],
            "late_summary": {"late_click_count": 2, "late_go_count": 0, "late_no_go_count": 0},
            "hand_profile": {
                "hand":   "right",
                "finger": "index",
                "label":  "Right Index",
                "protocol_difficulty_multiplier": 1.05,
                "assignment_source": "system",
            },
        },
    }


# ── NCC-01..03: GET game page ─────────────────────────────────────────────────

class TestNCCPage:

    def test_ncc01_active_game_returns_200(self):
        """NCC-01: GET /virtual-training/number-color-conflict → 200 for active game."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict

        user    = _make_student()
        request = _make_request()
        db      = _mock_db()
        game    = _mock_ncc_game()
        fake_protocol = MagicMock()
        fake_protocol.hand   = "free"
        fake_protocol.finger = "free"
        fake_protocol.protocol_difficulty_multiplier = 1.0
        fake_protocol.label  = ""
        fake_protocol.assignment_source = "system"

        fake_resp = MagicMock(spec=HTMLResponse)
        fake_resp.status_code = 200

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}._spec_ctx", return_value={}), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game), \
             patch(f"{_ROUTES}.VirtualTrainingService.assign_protocol", return_value=fake_protocol), \
             patch(f"{_ROUTES}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = fake_resp
            result = _run(virtual_training_number_color_conflict(request=request, db=db, user=user))

        assert result is fake_resp
        call_args = mock_tmpl.TemplateResponse.call_args
        assert call_args[0][0] == "virtual_training_number_color_conflict.html"
        ctx = call_args[0][1]
        assert ctx["game"] is game

    def test_ncc02_inactive_game_returns_hub(self):
        """NCC-02: GET → renders hub with error when game inactive."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict

        user    = _make_student()
        request = _make_request()
        db      = _mock_db()
        game    = _mock_ncc_game(is_active=False)

        fake_hub = MagicMock(spec=HTMLResponse)

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}._spec_ctx", return_value={}), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_hub_games", return_value=[]), \
             patch(f"{_ROUTES}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = fake_hub
            result = _run(virtual_training_number_color_conflict(request=request, db=db, user=user))

        assert result is fake_hub
        call_args = mock_tmpl.TemplateResponse.call_args
        assert call_args[0][0] == "virtual_training_hub.html"
        assert "error" in call_args[0][1]

    def test_ncc03_non_onboarded_redirected(self):
        """NCC-03: GET → guard redirect for non-onboarded user."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict

        user = _make_student()
        user.onboarding_completed = False
        request = _make_request()
        db = _mock_db()
        redirect = RedirectResponse(url="/dashboard", status_code=303)

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=redirect), \
             patch(f"{_ROUTES}.templates") as mock_tmpl:
            result = _run(virtual_training_number_color_conflict(request=request, db=db, user=user))

        assert isinstance(result, RedirectResponse)
        mock_tmpl.TemplateResponse.assert_not_called()


# ── NCC-04..09: POST submit ───────────────────────────────────────────────────

class TestNCCSubmit:

    def test_ncc04_valid_submit_returns_200(self):
        """NCC-04: POST submit with valid data returns attempt_id, xp_awarded."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user    = _make_student()
        request = _make_request(path="/virtual-training/number-color-conflict/submit")

        async def _fake_json():
            return _valid_payload()
        request.json = _fake_json

        db      = _mock_db(count=0)
        game    = _mock_ncc_game()
        attempt = _mock_attempt()

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game), \
             patch(f"{_ROUTES}.VirtualTrainingService.record_attempt", return_value=attempt):
            result = _run(virtual_training_number_color_conflict_submit(request=request, db=db, user=user))

        assert result.status_code == 200
        body = json.loads(result.body)
        assert body["attempt_id"] == attempt.id
        assert body["xp_awarded"] == attempt.xp_awarded
        assert body["is_valid"] is True

    def test_ncc05_too_short_returns_invalid(self):
        """NCC-05: POST submit → is_valid=False, xp=0, invalid_reason='too_short'."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user = _make_student()
        request = _make_request()
        payload = _valid_payload()
        payload["duration_seconds"] = 5.0

        async def _fake_json():
            return payload
        request.json = _fake_json

        db      = _mock_db(count=0)
        game    = _mock_ncc_game()
        attempt = _mock_attempt(is_valid=False, xp_awarded=0, invalid_reason="too_short")

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game), \
             patch(f"{_ROUTES}.VirtualTrainingService.record_attempt", return_value=attempt):
            result = _run(virtual_training_number_color_conflict_submit(request=request, db=db, user=user))

        body = json.loads(result.body)
        assert body["is_valid"] is False
        assert body["xp_awarded"] == 0
        assert body["invalid_reason"] == "too_short"

    def test_ncc06_bot_suspected_returns_invalid(self):
        """NCC-06: POST submit avg_reaction_ms < 80 → bot_suspected."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user = _make_student()
        request = _make_request()
        payload = _valid_payload()
        payload["avg_reaction_ms"] = 50.0

        async def _fake_json():
            return payload
        request.json = _fake_json

        db      = _mock_db(count=0)
        game    = _mock_ncc_game()
        attempt = _mock_attempt(is_valid=False, xp_awarded=0, invalid_reason="bot_suspected")

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game), \
             patch(f"{_ROUTES}.VirtualTrainingService.record_attempt", return_value=attempt):
            result = _run(virtual_training_number_color_conflict_submit(request=request, db=db, user=user))

        body = json.loads(result.body)
        assert body["is_valid"] is False
        assert body["invalid_reason"] == "bot_suspected"

    def test_ncc07_daily_cap_returns_429(self):
        """NCC-07: POST submit → 429 when valid_today >= max_daily_attempts."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user = _make_student()
        request = _make_request()

        async def _fake_json():
            return _valid_payload()
        request.json = _fake_json

        db   = _mock_db(count=5)
        game = _mock_ncc_game()
        game.max_daily_attempts = 5

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game):
            result = _run(virtual_training_number_color_conflict_submit(request=request, db=db, user=user))

        assert result.status_code == 429

    def test_ncc08_inactive_game_returns_404(self):
        """NCC-08: POST submit → 404 when game is inactive."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user = _make_student()
        request = _make_request()

        async def _fake_json():
            return _valid_payload()
        request.json = _fake_json

        db   = _mock_db()
        game = _mock_ncc_game(is_active=False)

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game):
            result = _run(virtual_training_number_color_conflict_submit(request=request, db=db, user=user))

        assert result.status_code == 404

    def test_ncc09_not_onboarded_returns_403(self):
        """NCC-09: POST submit → 403 when user not onboarded."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user = _make_student()
        user.onboarding_completed = False
        request = _make_request()

        async def _fake_json():
            return _valid_payload()
        request.json = _fake_json

        db = _mock_db()
        redirect = RedirectResponse(url="/onboarding", status_code=303)

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=redirect):
            result = _run(virtual_training_number_color_conflict_submit(request=request, db=_mock_db(), user=user))

        assert result.status_code == 403


# ── NCC-10..12: GET result + idempotency ─────────────────────────────────────

class TestNCCResult:

    def test_ncc10_result_page_returns_200(self):
        """NCC-10: GET /result/{id} → 200 for attempt owner."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_result

        user    = _make_student()
        request = _make_request(path="/virtual-training/number-color-conflict/result/55")
        db      = _mock_db()
        attempt = _mock_attempt()
        game    = _mock_ncc_game()

        # db.query().filter().first() returns attempt then game
        q = MagicMock()
        q.filter.return_value = q
        q.first.side_effect   = [attempt, game]
        db.query.return_value = q

        fake_resp = MagicMock(spec=HTMLResponse)
        fake_resp.status_code = 200

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}._spec_ctx", return_value={}), \
             patch(f"{_ROUTES}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = fake_resp
            result = _run(virtual_training_number_color_conflict_result(
                attempt_id=55, request=request, db=db, user=user
            ))

        assert result is fake_resp
        call_args = mock_tmpl.TemplateResponse.call_args
        assert call_args[0][0] == "virtual_training_number_color_conflict_result.html"

    def test_ncc11_result_not_found_returns_hub(self):
        """NCC-11: GET /result/{id} → hub when attempt not found."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_result

        user    = _make_student()
        request = _make_request()
        db      = _mock_db()  # q.first() returns None

        fake_hub = MagicMock(spec=HTMLResponse)

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}._spec_ctx", return_value={}), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_hub_games", return_value=[]), \
             patch(f"{_ROUTES}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = fake_hub
            result = _run(virtual_training_number_color_conflict_result(
                attempt_id=9999, request=request, db=db, user=user
            ))

        call_args = mock_tmpl.TemplateResponse.call_args
        assert call_args[0][0] == "virtual_training_hub.html"
        assert "error" in call_args[0][1]

    def test_ncc12_idempotency_key_contains_ncc(self):
        """NCC-12: Idempotency key uses 'vt_ncc_u{id}_{started_at}' prefix."""
        from app.api.web_routes.virtual_training import virtual_training_number_color_conflict_submit

        user = _make_student()
        user.id = 42
        request = _make_request()

        payload = _valid_payload()
        payload["started_at"] = "2026-05-23T10:00:00.000Z"

        async def _fake_json():
            return payload
        request.json = _fake_json

        db   = _mock_db(count=0)
        game = _mock_ncc_game()
        attempt = _mock_attempt()

        captured = {}

        def capture_record(**kwargs):
            captured["idem_key"] = kwargs.get("idempotency_key", "")
            return attempt

        with patch(f"{_ROUTES}.require_student_onboarding", return_value=None), \
             patch(f"{_ROUTES}.VirtualTrainingService.get_game", return_value=game), \
             patch(f"{_ROUTES}.VirtualTrainingService.record_attempt", side_effect=lambda **kw: capture_record(**kw)):
            _run(virtual_training_number_color_conflict_submit(request=request, db=db, user=user))

        assert "ncc" in captured.get("idem_key", ""), (
            f"Expected 'ncc' in idempotency key, got: {captured.get('idem_key')}"
        )


# ── NCC-13..17: Skill scorers ─────────────────────────────────────────────────

class TestNCCScorerReuse:

    def _signals(self, **kwargs):
        from app.services.virtual_training_metrics import VTSignals
        defaults = dict(
            hit_rate=1.0, wrong_rate=0.0, miss_rate=0.0,
            speed_score=1.0, completion_rate=1.0,
            avg_reaction_ms=400.0, per_phase=None,
            late_click_rate=0.0, late_go_rate=0.0, late_nogo_rate=0.0,
            protocol_difficulty_multiplier=1.0,
        )
        defaults.update(kwargs)
        return VTSignals(**defaults)

    def test_ncc13_decisions_perfect(self):
        """NCC-13: score_decisions at hit=1.0, wrong=0.0 → 1.0."""
        from app.services.virtual_training_metrics import VTSkillScorer
        sig = self._signals(hit_rate=1.0, wrong_rate=0.0)
        assert VTSkillScorer.score_decisions(sig) == 1.0

    def test_ncc14_decisions_with_wrong(self):
        """NCC-14: score_decisions(hit=0.5, wrong=0.2) → 0.5 - 0.3 = 0.2."""
        from app.services.virtual_training_metrics import VTSkillScorer
        sig = self._signals(hit_rate=0.5, wrong_rate=0.2)
        score = VTSkillScorer.score_decisions(sig)
        assert abs(score - 0.2) < 1e-9

    def test_ncc15_concentration_perfect(self):
        """NCC-15: score_concentration at miss=0.0 → 1.0."""
        from app.services.virtual_training_metrics import VTSkillScorer
        sig = self._signals(miss_rate=0.0)
        assert VTSkillScorer.score_concentration(sig) == 1.0

    def test_ncc16_composure_perfect(self):
        """NCC-16: score_composure(wrong=0.0) → 1.0 (no false alarms in NCC context)."""
        from app.services.virtual_training_metrics import VTSkillScorer
        sig = self._signals(wrong_rate=0.0)
        assert VTSkillScorer.score_composure(sig) == 1.0

    def test_ncc17_score_all_covers_ncc_skills(self):
        """NCC-17: score_all() with NCC skill_targets returns all 4 skills."""
        from app.services.virtual_training_metrics import VTSkillScorer
        sig = self._signals()
        scores = VTSkillScorer.score_all(sig, _NCC_SKILL_TARGETS)
        assert set(scores.keys()) == {"decisions", "concentration", "composure", "reactions"}


# ── NCC-18..20: Performance delta direction ───────────────────────────────────

class TestNCCDeltaDirection:

    def _signals_from_data(self, data: dict):
        from app.services.virtual_training_metrics import VTSignalExtractor
        return VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])

    def test_ncc18_perfect_run_all_positive(self):
        """NCC-18: Perfect NCC run → all four skill deltas positive."""
        from app.services.virtual_training_metrics import VTSkillScorer, VTDeltaComputer
        data = {
            "stimuli_count": 36, "correct_count": 36,
            "wrong_click_count": 0, "error_count": 0,
            "avg_reaction_ms": 400.0,
        }
        from app.services.virtual_training_metrics import VTSignalExtractor
        signals = VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])
        scores  = VTSkillScorer.score_all(signals, _NCC_SKILL_TARGETS)
        deltas  = VTDeltaComputer.compute(scores, _NCC_SKILL_TARGETS, 12, 1.0)
        assert all(v > 0 for v in deltas.values()), f"Expected all positive, got: {deltas}"

    def test_ncc19_wrong_heavy_reduces_decisions_composure(self):
        """NCC-19: High wrong rate → decisions and composure scores low."""
        from app.services.virtual_training_metrics import VTSkillScorer, VTSignalExtractor
        data = {
            "stimuli_count": 36, "correct_count": 10,
            "wrong_click_count": 25, "error_count": 1,
            "avg_reaction_ms": 600.0,
        }
        signals = VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])
        scores  = VTSkillScorer.score_all(signals, _NCC_SKILL_TARGETS)
        assert scores["decisions"]  < 0.45, f"decisions={scores['decisions']}"
        assert scores["composure"]  < 0.45, f"composure={scores['composure']}"

    def test_ncc20_missed_heavy_reduces_concentration(self):
        """NCC-20: High miss rate → concentration score low."""
        from app.services.virtual_training_metrics import VTSkillScorer, VTSignalExtractor
        data = {
            "stimuli_count": 36, "correct_count": 8,
            "wrong_click_count": 0, "error_count": 28,
            "avg_reaction_ms": 900.0,
        }
        signals = VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])
        scores  = VTSkillScorer.score_all(signals, _NCC_SKILL_TARGETS)
        assert scores["concentration"] < 0.45, f"concentration={scores['concentration']}"


# ── NCC-21..23: raw_metrics v3 / hand_profile ────────────────────────────────

class TestNCCRawMetricsV3:

    def test_ncc21_v3_hand_profile_extracts_pdm(self):
        """NCC-21: v3 payload with hand_profile → PDM extracted correctly."""
        from app.services.virtual_training_metrics import VTSignalExtractor
        data = {
            "stimuli_count": 36, "correct_count": 28,
            "wrong_click_count": 4, "error_count": 4,
            "avg_reaction_ms": 620.0,
            "raw_metrics": {
                "v": 3,
                "hand_profile": {
                    "protocol_difficulty_multiplier": 1.10,
                },
            },
        }
        signals = VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])
        assert abs(signals.protocol_difficulty_multiplier - 1.10) < 1e-9

    def test_ncc22_v3_late_summary_sets_late_click_rate(self):
        """NCC-22: v3 late_summary.late_click_count → late_click_rate in signals."""
        from app.services.virtual_training_metrics import VTSignalExtractor
        data = {
            "stimuli_count": 36, "correct_count": 30,
            "wrong_click_count": 2, "error_count": 0,
            "avg_reaction_ms": 550.0,
            "raw_metrics": {
                "v": 3,
                "late_summary": {
                    "late_click_count": 4,
                    "late_go_count": 0,
                    "late_no_go_count": 0,
                },
                "hand_profile": {"protocol_difficulty_multiplier": 1.0},
            },
        }
        signals = VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])
        expected = 4 / 36
        assert abs(signals.late_click_rate - expected) < 1e-6

    def test_ncc23_v1_payload_pdm_defaults_to_1(self):
        """NCC-23: v1 payload (no hand_profile) → PDM defaults to 1.0."""
        from app.services.virtual_training_metrics import VTSignalExtractor
        data = {
            "stimuli_count": 36, "correct_count": 28,
            "wrong_click_count": 4, "error_count": 4,
            "avg_reaction_ms": 620.0,
            "raw_metrics": {"v": 1, "per_stimulus": [], "per_phase": []},
        }
        signals = VTSignalExtractor.extract(data, _NCC_CONFIG["phases"])
        assert signals.protocol_difficulty_multiplier == 1.0


# ── NCC-24..28: Template / link tests ────────────────────────────────────────

class TestNCCTemplates:

    def test_ncc24_game_template_exists(self):
        """NCC-24: virtual_training_number_color_conflict.html present in templates."""
        tmpl = _TEMPLATES_DIR / "virtual_training_number_color_conflict.html"
        assert tmpl.exists(), f"Missing: {tmpl}"

    def test_ncc25_result_template_exists(self):
        """NCC-25: virtual_training_number_color_conflict_result.html present."""
        tmpl = _TEMPLATES_DIR / "virtual_training_number_color_conflict_result.html"
        assert tmpl.exists(), f"Missing: {tmpl}"

    def test_ncc26_result_template_has_skill_breakdown(self):
        """NCC-26: Result template references 'nccr-breakdown' (skill breakdown)."""
        tmpl = _TEMPLATES_DIR / "virtual_training_number_color_conflict_result.html"
        content = tmpl.read_text()
        assert "nccr-breakdown" in content

    def test_ncc27_result_template_has_decisions_formula(self):
        """NCC-27: Result template shows decisions formula note for players."""
        tmpl = _TEMPLATES_DIR / "virtual_training_number_color_conflict_result.html"
        content = tmpl.read_text()
        assert "decisions" in content
        assert "wrong" in content.lower()

    def test_ncc28_game_template_has_protocol_card(self):
        """NCC-28: Game template has Today's Protocol card (ncc-protocol-card)."""
        tmpl = _TEMPLATES_DIR / "virtual_training_number_color_conflict.html"
        content = tmpl.read_text()
        assert "ncc-protocol-card" in content


# ── NCC-SEED-01..02: Seed tests ───────────────────────────────────────────────

class TestNCCSeed:

    def _get_ncc_seed(self):
        from scripts.seed_virtual_training_games import _GAMES
        return next((g for g in _GAMES if g["code"] == "number_color_conflict"), None)

    def test_ncc_seed01_is_active_true(self):
        """NCC-SEED-01: number_color_conflict is_active=True in seed data."""
        entry = self._get_ncc_seed()
        assert entry is not None, "number_color_conflict not found in _GAMES"
        assert entry["is_active"] is True, "number_color_conflict must be active"

    def test_ncc_seed02_config_has_gameplay_keys(self):
        """NCC-SEED-02: seed config includes phases, numbers, colors, late_grace_ms."""
        entry = self._get_ncc_seed()
        assert entry is not None
        cfg = entry["config"]
        assert "phases" in cfg, "seed config missing 'phases'"
        assert "numbers" in cfg, "seed config missing 'numbers'"
        assert "colors" in cfg, "seed config missing 'colors'"
        assert "late_grace_ms" in cfg, "seed config missing 'late_grace_ms'"
        assert len(cfg["phases"]) == 3, f"expected 3 phases, got {len(cfg['phases'])}"
        total = sum(p["stimuli"] for p in cfg["phases"])
        assert total == 36, f"expected 36 total stimuli, got {total}"
