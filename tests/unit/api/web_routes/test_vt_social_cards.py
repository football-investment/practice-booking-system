"""
SC-01  preview: participant → 200 HTML
SC-02  preview: non-participant → 403
SC-03  preview: invalid platform → 422
SC-04  export: participant → PNG bytes (mock Playwright)
SC-05  export: non-participant → 403
SC-06  export: rate limit 6th request → 429
SC-07  Content-Disposition contains challenge id + platform
SC-08  context score_win → is_viewer_winner=True when winner_id==viewer.id
SC-09  context forfeit loser → my_score=None
SC-10  context skill deltas come from viewer's attempt
SC-11  context draw → is_draw=True, winner_name=None
SC-12  context pending → challenger_score=None, challenged_score=None
SC-13  CTA completed + viewer won → "Play again"
SC-14  post_16_9 template contains outcome_reason, my_score, opp_score
SC-15  story_9_16 template contains outcome_reason, my_skill_scores
SC-16  both templates contain LFA branding marker
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import HTMLResponse, Response

from app.models.vt_challenge import ChallengeStatus, VirtualTrainingChallenge
from app.models.virtual_training import VirtualTrainingAttempt

_BASE = "app.api.web_routes.vt_challenges"
_POST_TEMPLATE   = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../../../../app/templates/public/export/challenge/post_16_9.html",
))
_STORY_TEMPLATE  = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../../../../app/templates/public/export/challenge/story_9_16.html",
))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(uid=1):
    u = MagicMock()
    u.id       = uid
    u.email    = f"u{uid}@lfa.com"
    u.nickname = None
    return u


def _game():
    g = MagicMock()
    g.id   = 7
    g.code = "target_tracking"
    g.name = "Target Tracking"
    g.config = {}
    return g


def _challenge(
    *,
    cid=10,
    status=ChallengeStatus.COMPLETED,
    challenger_id=1,
    challenged_id=2,
    winner_id=None,
    is_draw=False,
    forfeit_user_id=None,
    forfeit_reason=None,
    challenger_attempt_id=None,
    challenged_attempt_id=None,
    challenge_mode="live",
):
    from datetime import datetime, timezone
    ch = MagicMock(spec=VirtualTrainingChallenge)
    ch.id                    = cid
    ch.status                = status
    ch.challenger_id         = challenger_id
    ch.challenged_id         = challenged_id
    ch.winner_id             = winner_id
    ch.is_draw               = is_draw
    ch.forfeit_user_id       = forfeit_user_id
    ch.forfeit_reason        = forfeit_reason
    ch.challenger_attempt_id = challenger_attempt_id
    ch.challenged_attempt_id = challenged_attempt_id
    ch.game_id               = 7
    ch.difficulty_level      = "hard"
    ch.message               = None
    ch.challenge_mode        = challenge_mode
    ch.completion_deadline   = None
    ch.completed_at          = datetime.now(timezone.utc) if status == ChallengeStatus.COMPLETED else None
    ch.created_at            = datetime.now(timezone.utc)
    ch.challenger            = _user(uid=challenger_id)
    ch.challenged            = _user(uid=challenged_id)
    ch.winner                = _user(uid=winner_id) if winner_id else None
    ch.forfeit_user          = _user(uid=forfeit_user_id) if forfeit_user_id else None
    ch.game                  = _game()
    return ch


def _attempt(aid=100, score=75.0, skill_deltas=None):
    a = MagicMock(spec=VirtualTrainingAttempt)
    a.id               = aid
    a.is_valid         = True
    a.score_normalized = score
    a.skill_deltas     = skill_deltas or {}
    return a


# ── Shared call helpers ────────────────────────────────────────────────────────

def _call_preview(*, ch, user_id=1, platform="challenge_post_16_9",
                  challenger_attempt=None, challenged_attempt=None):
    from app.api.web_routes.vt_challenges import challenge_card_preview

    user = _user(uid=user_id)
    db   = MagicMock()
    firsts = iter([ch, challenger_attempt, challenged_attempt])
    db.query.return_value.filter.return_value.first.side_effect = lambda: next(firsts, None)

    captured = {}

    def _capture(tmpl, ctx, **kw):
        captured["template"] = tmpl
        captured["context"]  = ctx
        return MagicMock(spec=HTMLResponse)

    with patch(f"{_BASE}.require_student_onboarding", return_value=None), \
         patch(f"{_BASE}.templates.TemplateResponse", side_effect=_capture):
        try:
            asyncio.run(challenge_card_preview(
                challenge_id=ch.id,
                request=MagicMock(),
                platform=platform,
                db=db,
                user=user,
            ))
        except Exception as exc:
            captured["exc"] = exc

    return captured


def _call_export(*, ch, user_id=1, platform="challenge_post_16_9",
                 challenger_attempt=None, challenged_attempt=None,
                 rate_ok=True, png_bytes=b"PNG"):
    from app.api.web_routes.vt_challenges import challenge_card_export

    user = _user(uid=user_id)
    db   = MagicMock()
    firsts = iter([ch, challenger_attempt, challenged_attempt])
    db.query.return_value.filter.return_value.first.side_effect = lambda: next(firsts, None)

    captured = {}

    async def _mock_to_thread(fn, *args, **kw):
        return png_bytes

    with patch(f"{_BASE}.require_student_onboarding", return_value=None), \
         patch(f"{_BASE}._export_svc.check_export_rate_limit", return_value=rate_ok), \
         patch(f"{_BASE}.asyncio.to_thread", side_effect=_mock_to_thread), \
         patch("app.config.settings") as mock_settings:
        mock_settings.APP_INTERNAL_PORT = 8000
        try:
            result = asyncio.run(challenge_card_export(
                challenge_id=ch.id,
                request=MagicMock(),
                platform=platform,
                db=db,
                user=user,
            ))
            captured["result"] = result
        except Exception as exc:
            captured["exc"] = exc

    return captured


# ══════════════════════════════════════════════════════════════════════════════
# SC-01..03  preview route
# ══════════════════════════════════════════════════════════════════════════════

class TestChallengeCardPreview:

    def test_sc01_participant_gets_200(self):
        ch = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_preview(ch=ch, user_id=1)
        assert "exc" not in cap, f"Unexpected exception: {cap.get('exc')}"
        assert "template" in cap

    def test_sc01_template_name_post_16_9(self):
        ch = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_preview(ch=ch, user_id=1, platform="challenge_post_16_9")
        assert cap["template"] == "public/export/challenge/post_16_9.html"

    def test_sc01_template_name_story_9_16(self):
        ch = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_preview(ch=ch, user_id=1, platform="challenge_story_9_16")
        assert cap["template"] == "public/export/challenge/story_9_16.html"

    def test_sc02_non_participant_raises_403(self):
        ch = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_preview(ch=ch, user_id=99)
        exc = cap.get("exc")
        assert exc is not None
        from fastapi import HTTPException
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 403

    def test_sc03_invalid_platform_raises_422(self):
        ch = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_preview(ch=ch, user_id=1, platform="instagram_portrait")
        exc = cap.get("exc")
        assert exc is not None
        from fastapi import HTTPException
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# SC-04..07  export route
# ══════════════════════════════════════════════════════════════════════════════

class TestChallengeCardExport:

    def test_sc04_participant_gets_png(self):
        ch  = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_export(ch=ch, user_id=1, png_bytes=b"FAKEPNG")
        assert "exc" not in cap, f"Unexpected exception: {cap.get('exc')}"
        result = cap["result"]
        assert isinstance(result, Response)
        assert result.media_type == "image/png"
        assert result.body == b"FAKEPNG"

    def test_sc05_non_participant_raises_403(self):
        ch  = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_export(ch=ch, user_id=99)
        exc = cap.get("exc")
        assert exc is not None
        from fastapi import HTTPException
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 403

    def test_sc06_rate_limit_raises_429(self):
        ch  = _challenge(challenger_id=1, challenged_id=2)
        cap = _call_export(ch=ch, user_id=1, rate_ok=False)
        exc = cap.get("exc")
        assert exc is not None
        from fastapi import HTTPException
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 429

    def test_sc07_content_disposition_contains_id_and_platform(self):
        ch  = _challenge(cid=42, challenger_id=1, challenged_id=2)
        cap = _call_export(ch=ch, user_id=1, platform="challenge_post_16_9", png_bytes=b"X")
        result = cap["result"]
        cd = result.headers.get("Content-Disposition", "")
        assert "42" in cd
        assert "challenge_post_16_9" in cd


# ══════════════════════════════════════════════════════════════════════════════
# SC-08..13  context builder
# ══════════════════════════════════════════════════════════════════════════════

class TestChallengeCardContext:

    def _ctx(self, ch, challenger_attempt=None, challenged_attempt=None, viewer_id=1):
        from app.api.web_routes.vt_challenges import _build_challenge_card_context
        viewer = _user(uid=viewer_id)
        return _build_challenge_card_context(ch, viewer, challenger_attempt, challenged_attempt)

    def test_sc08_score_win_viewer_is_winner(self):
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            winner_id=1, status=ChallengeStatus.COMPLETED,
        )
        ctx = self._ctx(ch, viewer_id=1)
        assert ctx["is_viewer_winner"] is True

    def test_sc08_score_win_loser_not_winner(self):
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            winner_id=1, status=ChallengeStatus.COMPLETED,
        )
        ctx = self._ctx(ch, viewer_id=2)
        assert ctx["is_viewer_winner"] is False

    def test_sc09_forfeit_loser_my_score_none(self):
        """Forfeit: challenged (uid=2) submitted nothing → my_score=None when viewer=2."""
        ch_attempt = _attempt(aid=10, score=80.0)
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            challenger_attempt_id=10, challenged_attempt_id=None,
            forfeit_user_id=2, winner_id=1,
        )
        ctx = self._ctx(ch, challenger_attempt=ch_attempt, challenged_attempt=None, viewer_id=2)
        assert ctx["my_score"] is None

    def test_sc10_skill_deltas_from_viewer_attempt(self):
        """my_skill_scores = viewer's attempt.skill_deltas."""
        deltas = {"reactions": 0.08, "decision_making": -0.03}
        ch_attempt = _attempt(aid=20, score=70.0, skill_deltas=deltas)
        ch = _challenge(challenger_id=1, challenged_id=2, challenger_attempt_id=20)
        ctx = self._ctx(ch, challenger_attempt=ch_attempt, challenged_attempt=None, viewer_id=1)
        assert ctx["my_skill_scores"].get("reactions") == pytest.approx(0.08)
        assert ctx["my_skill_scores"].get("decision_making") == pytest.approx(-0.03)

    def test_sc11_draw_context(self):
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            is_draw=True, winner_id=None,
        )
        ctx = self._ctx(ch, viewer_id=1)
        assert ctx["is_draw"] is True
        assert ctx["winner_name"] is None

    def test_sc12_pending_scores_are_none(self):
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            status=ChallengeStatus.PENDING,
            challenger_attempt_id=None,
            challenged_attempt_id=None,
        )
        ctx = self._ctx(ch, viewer_id=1)
        assert ctx["challenger_score"] is None
        assert ctx["challenged_score"] is None

    def test_sc13_cta_winner_play_again(self):
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            winner_id=1, status=ChallengeStatus.COMPLETED,
        )
        ctx = self._ctx(ch, viewer_id=1)
        assert ctx["cta_label"] == "Play again"

    def test_sc13_cta_pending_view_challenge(self):
        ch = _challenge(
            challenger_id=1, challenged_id=2,
            status=ChallengeStatus.PENDING,
        )
        ctx = self._ctx(ch, viewer_id=1)
        assert ctx["cta_label"] == "View challenge"


# ══════════════════════════════════════════════════════════════════════════════
# SC-14..16  template content
# ══════════════════════════════════════════════════════════════════════════════

class TestChallengeCardTemplates:

    def _post(self):
        with open(_POST_TEMPLATE, encoding="utf-8") as fh:
            return fh.read()

    def _story(self):
        with open(_STORY_TEMPLATE, encoding="utf-8") as fh:
            return fh.read()

    def test_sc14_post_template_has_outcome_reason(self):
        assert "outcome_reason" in self._post()

    def test_sc14_post_template_has_challenger_score(self):
        assert "challenger_score" in self._post()

    def test_sc14_post_template_has_challenged_score(self):
        assert "challenged_score" in self._post()

    def test_sc15_story_template_has_outcome_reason(self):
        assert "outcome_reason" in self._story()

    def test_sc15_story_template_has_my_skill_scores(self):
        assert "my_skill_scores" in self._story()

    def test_sc15_story_skill_delta_no_delta_message(self):
        assert "No skill delta recorded" in self._story()

    def test_sc16_post_has_lfa_branding(self):
        html = self._post()
        assert "LFA" in html

    def test_sc16_story_has_lfa_branding(self):
        html = self._story()
        assert "LFA" in html

    def test_sc16_both_templates_are_standalone_html(self):
        for html in (self._post(), self._story()):
            assert "<!DOCTYPE html>" in html
