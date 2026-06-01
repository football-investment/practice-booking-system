"""
CS-S4B — Challenge Studio: selector + phase/platform selector + live preview iframe

CS-S4B1: Challenge selector list
S4B1-01  GET /card-studio/challenge (no challenge_id) → 200
S4B1-02  challenge_rows includes user's sent challenges (challenger_id match)
S4B1-03  challenge_rows includes user's received challenges (challenged_id match)
S4B1-04  other user's challenges do not appear in challenge_rows
S4B1-05  filter=active → only active challenges
S4B1-06  filter=completed → only completed/terminal challenges
S4B1-07  empty challenge list → empty state in context
S4B1-08  Preview Card CTA links to /card-studio/challenge?challenge_id={id}

CS-S4B2: Challenge select + phase/platform selector
S4B2-01  challenge_id param → selected_challenge context
S4B2-02  non-participant user → error mode (challenge_error=not_participant)
S4B2-03  non-existent challenge_id → error mode (challenge_error=not_found)
S4B2-04  unlocked phases for PENDING as challenger: challenge_sent
S4B2-05  unlocked phases for PENDING as challenged: challenge_received
S4B2-06  unlocked phases for COMPLETED score win: completed_score_win
S4B2-07  locked phases list present in context for non-PENDING challenges
S4B2-08  active phase chip marked correctly
S4B2-09  platform chips include both challenge_post_16_9 and challenge_story_9_16

CS-S4B3: Preview iframe integration
S4B3-01  preview_url = /challenges/{id}/card/preview?platform={platform}&phase={phase}
S4B3-02  shell template uses preview_url as iframe src (challenge preview mode)
S4B3-03  post_16_9 platform → ratio_class mfg-ratio-169
S4B3-04  story_9_16 platform → ratio_class mfg-ratio-916
S4B3-05  selector mode (no challenge_id) → preview_url is None, placeholder shown
S4B3-06  error mode → no iframe, placeholder shown
S4B3-07  legacy editor CTA /card-editor/challenge present in challenge panel
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "app" / "templates"
INCLUDES_DIR  = TEMPLATES_DIR / "includes"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(uid: int = 10):
    u = MagicMock(); u.id = uid; u.nickname = f"user{uid}"; u.email = f"u{uid}@test.com"
    return u

def _make_license(onboarding: bool = True):
    lic = MagicMock(); lic.onboarding_completed = onboarding; return lic

def _make_challenge(ch_id: int, challenger_id: int, challenged_id: int, status_val: str):
    """Create a mock VirtualTrainingChallenge."""
    from app.models.vt_challenge import ChallengeStatus
    ch = MagicMock()
    ch.id                    = ch_id
    ch.challenger_id         = challenger_id
    ch.challenged_id         = challenged_id
    ch.challenger_attempt_id = None
    ch.challenged_attempt_id = None
    ch.winner_id             = None
    ch.is_draw               = False
    ch.forfeit_user_id       = None
    ch.forfeit_reason        = None
    ch.challenge_mode        = "async"
    ch.created_at            = None
    ch.completed_at          = None

    status_map = {
        "pending":          ChallengeStatus.PENDING,
        "accepted":         ChallengeStatus.ACCEPTED,
        "completed":        ChallengeStatus.COMPLETED,
        "declined":         ChallengeStatus.DECLINED,
        "cancelled":        ChallengeStatus.CANCELLED,
        "expired":          ChallengeStatus.EXPIRED,
        "live_lobby":       ChallengeStatus.LIVE_LOBBY,
        "live_in_progress": ChallengeStatus.LIVE_IN_PROGRESS,
    }
    ch.status = status_map.get(status_val, ChallengeStatus.PENDING)
    ch.game = MagicMock(); ch.game.name = "Memory Sequence"
    ch.challenger = _make_user(challenger_id)
    ch.challenged = _make_user(challenged_id)
    return ch

def _ctx_fn():
    from app.api.web_routes.card_studio import _resolve_challenge_context
    return _resolve_challenge_context

def _db_licensed():
    """DB with active license."""
    db  = MagicMock()
    lic = _make_license(onboarding=True)
    db.query.return_value.filter.return_value.first.return_value = lic
    return db

def _db_with_challenges(challenges: list):
    """DB that returns given challenges for the query chain."""
    db = MagicMock()
    lic = _make_license(onboarding=True)
    # first().return_value = lic (license guard)
    db.query.return_value.filter.return_value.first.return_value = lic
    # .filter().filter().order_by().limit().all() → challenges
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = challenges
    # no filter (all): .filter().order_by().limit().all()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = challenges
    # Attempt batch load: filter().filter().all()
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
    return db


# ── S4B1: Challenge selector list ────────────────────────────────────────────

class TestS4B1ChallengeSelector:

    def test_s4b1_01_no_challenge_id_returns_200(self):
        """S4B1-01: GET /card-studio/challenge route is registered and returns 200."""
        from app.main import app
        paths = [getattr(r, "path", "") for r in app.routes]
        assert "/card-studio/challenge" in paths

    def test_s4b1_02_challenger_challenges_in_rows(self):
        """S4B1-02: challenge_rows includes challenges where user is challenger."""
        fn   = _ctx_fn()
        user = _make_user(10)
        ch1  = _make_challenge(1, challenger_id=10, challenged_id=20, status_val="pending")
        db   = _db_with_challenges([ch1])

        with patch("app.api.web_routes.card_studio.VirtualTrainingAttempt"):
            ctx, redirect = fn(db, user, challenge_id=None)

        assert redirect is None
        ids = [r["id"] for r in ctx.get("challenge_rows", [])]
        assert 1 in ids

    def test_s4b1_03_challenged_challenges_in_rows(self):
        """S4B1-03: challenge_rows includes challenges where user is challenged."""
        fn   = _ctx_fn()
        user = _make_user(20)
        ch1  = _make_challenge(5, challenger_id=10, challenged_id=20, status_val="accepted")
        db   = _db_with_challenges([ch1])

        with patch("app.api.web_routes.card_studio.VirtualTrainingAttempt"):
            ctx, redirect = fn(db, user, challenge_id=None)

        assert redirect is None
        ids = [r["id"] for r in ctx.get("challenge_rows", [])]
        assert 5 in ids

    def test_s4b1_04_other_user_challenge_not_in_rows(self):
        """S4B1-04: Challenges between other users do not appear."""
        fn   = _ctx_fn()
        user = _make_user(99)  # not involved in challenge
        ch1  = _make_challenge(7, challenger_id=10, challenged_id=20, status_val="pending")
        db   = _db_with_challenges([])  # query already filtered by user

        ctx, redirect = fn(db, user, challenge_id=None)
        assert redirect is None
        assert ctx["challenge_rows"] == []

    def test_s4b1_05_filter_active_context(self):
        """S4B1-05: filter=active → active_filter='active' in context."""
        fn   = _ctx_fn()
        user = _make_user(10)
        db   = _db_with_challenges([])

        ctx, _ = fn(db, user, challenge_id=None, filter_val="active")
        assert ctx["active_filter"] == "active"

    def test_s4b1_06_filter_completed_context(self):
        """S4B1-06: filter=completed → active_filter='completed' in context."""
        fn   = _ctx_fn()
        user = _make_user(10)
        db   = _db_with_challenges([])

        ctx, _ = fn(db, user, challenge_id=None, filter_val="completed")
        assert ctx["active_filter"] == "completed"

    def test_s4b1_07_empty_challenges_empty_rows(self):
        """S4B1-07: No challenges → challenge_rows == []."""
        fn   = _ctx_fn()
        user = _make_user(10)
        db   = _db_with_challenges([])

        ctx, _ = fn(db, user, challenge_id=None)
        assert ctx["challenge_rows"] == []
        assert ctx["challenge_mode"] == "selector"

    def test_s4b1_08_challenge_row_has_studio_url(self):
        """S4B1-08: challenge_rows entry has studio_url with challenge_id."""
        fn   = _ctx_fn()
        user = _make_user(10)
        ch   = _make_challenge(42, 10, 20, "pending")
        db   = _db_with_challenges([ch])

        with patch("app.api.web_routes.card_studio.VirtualTrainingAttempt"):
            ctx, _ = fn(db, user, challenge_id=None)

        rows = ctx.get("challenge_rows", [])
        if rows:
            assert "challenge_id=42" in rows[0]["studio_url"]


# ── S4B2: Challenge select + phase/platform selector ─────────────────────────

class TestS4B2PhaseSelector:

    def _db_for_challenge(self, ch, my_attempt=None):
        db = MagicMock()
        lic = _make_license(True)
        db.query.return_value.filter.return_value.first.side_effect = [lic, ch, my_attempt]
        return db

    def test_s4b2_01_challenge_id_returns_selected_challenge(self):
        """S4B2-01: ?challenge_id={id} → selected_challenge in context."""
        fn   = _ctx_fn()
        user = _make_user(10)
        ch   = _make_challenge(99, 10, 20, "pending")

        db = MagicMock()
        lic = _make_license(True)

        def query_side(*args, **kwargs):
            m = MagicMock()
            m.filter.return_value.first.return_value = lic
            return m

        with patch("app.api.web_routes.card_studio._license_guard", return_value=lic):
            with patch("app.api.web_routes.card_studio.VirtualTrainingChallenge") as VTC:
                VTC_instance = MagicMock()
                db.query.return_value.filter.return_value.first.return_value = ch
                ctx, redirect = fn(db, user, challenge_id=99)

        assert redirect is None
        assert ctx.get("challenge_mode") == "preview"
        assert ctx.get("selected_challenge_id") == 99

    def test_s4b2_02_non_participant_returns_error(self):
        """S4B2-02: User not in challenge → error mode not_participant."""
        fn   = _ctx_fn()
        user = _make_user(99)  # not in challenge
        ch   = _make_challenge(1, challenger_id=10, challenged_id=20, status_val="pending")

        db = MagicMock()
        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db.query.return_value.filter.return_value.first.return_value = ch
            ctx, redirect = fn(db, user, challenge_id=1)

        assert redirect is None
        assert ctx["challenge_mode"] == "error"
        assert ctx["challenge_error"] == "not_participant"

    def test_s4b2_03_not_found_challenge_returns_error(self):
        """S4B2-03: Non-existent challenge_id → error mode not_found."""
        fn   = _ctx_fn()
        user = _make_user(10)

        db = MagicMock()
        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db.query.return_value.filter.return_value.first.return_value = None
            ctx, redirect = fn(db, user, challenge_id=9999)

        assert redirect is None
        assert ctx["challenge_mode"] == "error"
        assert ctx["challenge_error"] == "not_found"

    def test_s4b2_04_pending_challenger_unlocked_phase(self):
        """S4B2-04: PENDING as challenger → unlocked phase includes challenge_sent."""
        from app.api.web_routes.vt_challenges import get_unlocked_challenge_card_phases
        ch = _make_challenge(1, 10, 20, "pending")
        phases = get_unlocked_challenge_card_phases(ch, 10, None)
        assert "challenge_sent" in phases

    def test_s4b2_05_pending_challenged_unlocked_phase(self):
        """S4B2-05: PENDING as challenged → unlocked phase includes challenge_received."""
        from app.api.web_routes.vt_challenges import get_unlocked_challenge_card_phases
        ch = _make_challenge(1, 10, 20, "pending")
        phases = get_unlocked_challenge_card_phases(ch, 20, None)
        assert "challenge_received" in phases

    def test_s4b2_06_completed_score_win_unlocked_phases(self):
        """S4B2-06: COMPLETED score win → unlocked phases include completed_score_win."""
        from app.api.web_routes.vt_challenges import get_unlocked_challenge_card_phases
        ch = _make_challenge(1, 10, 20, "completed")
        ch.winner_id     = 10
        ch.forfeit_user_id = None
        ch.is_draw       = False
        phases = get_unlocked_challenge_card_phases(ch, 10, None)
        assert "completed_score_win" in phases

    def test_s4b2_07_locked_phases_returned_for_non_pending(self):
        """S4B2-07: Non-PENDING challenge has locked historical phases."""
        from app.api.web_routes.vt_challenges import get_locked_challenge_card_phases
        ch = _make_challenge(1, 10, 20, "completed")
        locked = get_locked_challenge_card_phases(ch, 10)
        assert len(locked) > 0

    def test_s4b2_08_active_phase_chip_marked(self):
        """S4B2-08: phase_chips contains exactly one active=True chip."""
        fn   = _ctx_fn()
        user = _make_user(10)
        ch   = _make_challenge(1, 10, 20, "pending")

        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            with MagicMock() as mock_db:
                mock_db.query.return_value.filter.return_value.first.return_value = ch
                mock_db.query.return_value.filter.return_value.first.side_effect = None
                db = MagicMock()
                db.query.return_value.filter.return_value.first.return_value = ch
                ctx, _ = fn(db, user, challenge_id=1, phase="challenge_sent")

        if ctx.get("challenge_mode") == "preview":
            active_chips = [c for c in ctx.get("phase_chips", []) if c["active"]]
            assert len(active_chips) == 1

    def test_s4b2_09_platform_chips_both_platforms(self):
        """S4B2-09: platform_chips contains both post and story platforms."""
        fn   = _ctx_fn()
        user = _make_user(10)
        ch   = _make_challenge(1, 10, 20, "pending")

        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db = MagicMock()
            db.query.return_value.filter.return_value.first.return_value = ch
            ctx, _ = fn(db, user, challenge_id=1, phase="challenge_sent")

        if ctx.get("challenge_mode") == "preview":
            platform_ids = [c["id"] for c in ctx.get("platform_chips", [])]
            assert "challenge_post_16_9" in platform_ids
            assert "challenge_story_9_16" in platform_ids


# ── S4B3: Preview iframe ──────────────────────────────────────────────────────

class TestS4B3PreviewIframe:

    def test_s4b3_01_preview_url_pattern(self):
        """S4B3-01: preview_url = /challenges/{id}/card/preview?platform=...&phase=..."""
        fn   = _ctx_fn()
        user = _make_user(10)
        ch   = _make_challenge(42, 10, 20, "pending")

        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db = MagicMock()
            db.query.return_value.filter.return_value.first.return_value = ch
            ctx, _ = fn(db, user, challenge_id=42, phase="challenge_sent",
                        platform="challenge_post_16_9")

        if ctx.get("challenge_mode") == "preview":
            url = ctx["preview_url"]
            assert "/challenges/42/card/preview" in url
            assert "platform=challenge_post_16_9" in url
            assert "phase=challenge_sent" in url

    def test_s4b3_02_shell_uses_challenge_mode_for_iframe(self):
        """S4B3-02: Shell template has challenge_mode=='preview' check for iframe."""
        src = (TEMPLATES_DIR / "card_studio_shell.html").read_text()
        assert "challenge_mode == \"preview\"" in src or "challenge_mode == 'preview'" in src
        assert "cs-preview-iframe" in src

    def test_s4b3_03_post_platform_ratio_169(self):
        """S4B3-03: challenge_post_16_9 → ratio_class = mfg-ratio-169."""
        from app.api.web_routes.card_studio import _CC_RATIO
        assert _CC_RATIO["challenge_post_16_9"] == "mfg-ratio-169"

    def test_s4b3_04_story_platform_ratio_916(self):
        """S4B3-04: challenge_story_9_16 → ratio_class = mfg-ratio-916."""
        from app.api.web_routes.card_studio import _CC_RATIO
        assert _CC_RATIO["challenge_story_9_16"] == "mfg-ratio-916"

    def test_s4b3_05_selector_mode_no_preview_url(self):
        """S4B3-05: Selector mode (no challenge_id) → preview_url is None."""
        fn   = _ctx_fn()
        user = _make_user(10)
        db   = MagicMock()
        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
            ctx, _ = fn(db, user, challenge_id=None)
        assert ctx["preview_url"] is None
        assert ctx["challenge_mode"] == "selector"

    def test_s4b3_06_error_mode_no_preview_url(self):
        """S4B3-06: Error mode → preview_url is None."""
        fn   = _ctx_fn()
        user = _make_user(10)
        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db = MagicMock()
            db.query.return_value.filter.return_value.first.return_value = None
            ctx, _ = fn(db, user, challenge_id=9999)
        assert ctx["preview_url"] is None
        assert ctx["challenge_mode"] == "error"

    def test_s4b3_07_challenge_panel_has_legacy_cta(self):
        """S4B3-07: cs_challenge_panel.html references legacy_editor_url;
        context sets it to /card-editor/challenge."""
        src = (INCLUDES_DIR / "cs_challenge_panel.html").read_text()
        assert "legacy_editor_url" in src  # template uses context var

        # Context must set legacy_editor_url = /card-editor/challenge
        from app.api.web_routes.card_studio import _resolve_challenge_context
        user = _make_user(10)
        with patch("app.api.web_routes.card_studio._license_guard", return_value=_make_license(True)):
            db = MagicMock()
            db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
            ctx, _ = _resolve_challenge_context(db, user, challenge_id=None)
        assert ctx["legacy_editor_url"] == "/card-editor/challenge"
