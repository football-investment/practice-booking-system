"""PSP-01..PSP-14 — Public Player Profile page + cancel / next= social actions.

PSP-01  Anonymous user gets 200, friendship_panel state=anonymous
PSP-02  Logged-in user views own profile → state=own_profile
PSP-03  No friendship → state=none, can_add=True in context
PSP-04  Accepted friendship → state=accepted, can_remove=True
PSP-05  Pending sent → state=pending_sent, can_cancel=True
PSP-06  Pending received → state=pending_received, can_accept+can_decline=True
PSP-07  Profile user not found → 404 HTMLResponse
PSP-08  No active LFA license → 404 HTMLResponse
PSP-09  POST /friends/cancel/{id} — requester cancels pending → 303 success redirect
PSP-10  POST /friends/cancel/{id} — non-requester blocked → error redirect
PSP-11  POST /friends/cancel/{id} — non-PENDING row → error redirect
PSP-12  next= param — /players/ prefix accepted in cancel
PSP-13  next= param — /friends prefix accepted in accept
PSP-14  next= param — external URL falls back to default /friends
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import HTMLResponse, RedirectResponse

from app.models.friendship import FriendshipStatus, get_friendship_panel_ctx

_BASE_PP  = "app.api.web_routes.public_player"
_BASE_FR  = "app.api.web_routes.friends"
_SKILL_SVC = "app.services.skill_progression_service"
_FRIEND_MOD = "app.models.friendship"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _req():
    m = MagicMock()
    m.client = MagicMock()
    m.client.host = "127.0.0.1"
    return m


def _user(uid=1, name="Alice Smith", email="alice@lfa.com"):
    u = MagicMock()
    u.id           = uid
    u.name         = name
    u.email        = email
    u.nickname     = None
    u.nationality  = "HUN"
    u.is_active    = True
    u.date_of_birth = None
    return u


def _license(user_id=1, completed=True):
    lic = MagicMock()
    lic.user_id                = user_id
    lic.specialization_type    = "LFA_FOOTBALL_PLAYER"
    lic.is_active              = True
    lic.onboarding_completed   = completed
    lic.player_card_photo_url  = None
    lic.motivation_scores      = {"position": "STRIKER"}
    return lic


def _friendship_row(fid=10, requester_id=1, addressee_id=2,
                    status=FriendshipStatus.PENDING):
    f = MagicMock()
    f.id           = fid
    f.requester_id = requester_id
    f.addressee_id = addressee_id
    f.status       = status
    return f


def _profile_db(user=None, license=None):
    """DB mock for the public_player_profile route.

    Query order:
      1. db.query(User).filter(...).first()      → user
      2. db.query(UserLicense).filter(...).first() → license
      3. db.query(TournamentParticipation, Semester).join(...).filter(...).order_by(...).limit(...).all()
         → [] (no events)
    """
    db = MagicMock()
    # Queries 1 + 2: .filter().first()
    db.query.return_value.filter.return_value.first.side_effect = [user, license]
    # Query 3: participations chain uses .join().filter().order_by().limit().all()
    db.query.return_value.join.return_value.filter.return_value \
        .order_by.return_value.limit.return_value.all.return_value = []
    return db


_PANEL_ANONYMOUS  = {"state": "anonymous",        "friendship_id": None, "can_add": False, "can_cancel": False, "can_accept": False, "can_decline": False, "can_remove": False}
_PANEL_OWN        = {"state": "own_profile",       "friendship_id": None, "can_add": False, "can_cancel": False, "can_accept": False, "can_decline": False, "can_remove": False}
_PANEL_NONE       = {"state": "none",              "friendship_id": None, "can_add": True,  "can_cancel": False, "can_accept": False, "can_decline": False, "can_remove": False}
_PANEL_ACCEPTED   = {"state": "accepted",          "friendship_id": 10,   "can_add": False, "can_cancel": False, "can_accept": False, "can_decline": False, "can_remove": True}
_PANEL_SENT       = {"state": "pending_sent",      "friendship_id": 10,   "can_add": False, "can_cancel": True,  "can_accept": False, "can_decline": False, "can_remove": False}
_PANEL_RECEIVED   = {"state": "pending_received",  "friendship_id": 10,   "can_add": False, "can_cancel": False, "can_accept": True,  "can_decline": True,  "can_remove": False}


# ── PSP-01..PSP-08: public_player_profile route ───────────────────────────────

class TestPublicPlayerProfile:

    def _call(self, user=None, license=None, current_user=None, panel=None):
        from app.api.web_routes.public_player import public_player_profile
        profile_user = user or _user(uid=2)
        lic          = license or _license(user_id=2)
        db           = _profile_db(user=profile_user, license=lic)
        _panel       = panel if panel is not None else _PANEL_NONE
        with patch(f"{_BASE_PP}.templates") as mock_tmpl, \
             patch(f"{_SKILL_SVC}.get_skill_profile", return_value={"average_level": 65.0, "skills": {}, "total_tournaments": 3}), \
             patch(f"{_FRIEND_MOD}.get_friendship_panel_ctx", return_value=_panel):
            result = _run(public_player_profile(
                request=_req(), user_id=profile_user.id, db=db, current_user=current_user,
            ))
            ctx = mock_tmpl.TemplateResponse.call_args
        return result, ctx

    # PSP-01 — anonymous user: friendship_panel state=anonymous in context
    def test_psp01_anonymous_user_gets_anonymous_panel(self):
        _, ctx = self._call(current_user=None, panel=_PANEL_ANONYMOUS)
        context = ctx[0][2] if ctx else ctx.args[2]
        assert context["friendship_panel"]["state"] == "anonymous"
        assert context["current_user"] is None

    # PSP-02 — own profile: state=own_profile in context
    def test_psp02_own_profile_state(self):
        viewer = _user(uid=2)
        _, ctx = self._call(current_user=viewer, panel=_PANEL_OWN)
        context = ctx[0][2] if ctx else ctx.args[2]
        assert context["friendship_panel"]["state"] == "own_profile"

    # PSP-03 — no friendship: state=none, can_add=True
    def test_psp03_no_friendship_can_add(self):
        viewer = _user(uid=9)
        _, ctx = self._call(current_user=viewer, panel=_PANEL_NONE)
        context = ctx[0][2] if ctx else ctx.args[2]
        assert context["friendship_panel"]["state"] == "none"
        assert context["friendship_panel"]["can_add"] is True

    # PSP-04 — accepted: can_remove=True
    def test_psp04_accepted_friend_can_remove(self):
        viewer = _user(uid=9)
        _, ctx = self._call(current_user=viewer, panel=_PANEL_ACCEPTED)
        context = ctx[0][2] if ctx else ctx.args[2]
        assert context["friendship_panel"]["state"] == "accepted"
        assert context["friendship_panel"]["can_remove"] is True

    # PSP-05 — pending sent: can_cancel=True
    def test_psp05_pending_sent_can_cancel(self):
        viewer = _user(uid=9)
        _, ctx = self._call(current_user=viewer, panel=_PANEL_SENT)
        context = ctx[0][2] if ctx else ctx.args[2]
        assert context["friendship_panel"]["state"] == "pending_sent"
        assert context["friendship_panel"]["can_cancel"] is True

    # PSP-06 — pending received: can_accept + can_decline
    def test_psp06_pending_received_accept_decline(self):
        viewer = _user(uid=9)
        _, ctx = self._call(current_user=viewer, panel=_PANEL_RECEIVED)
        context = ctx[0][2] if ctx else ctx.args[2]
        assert context["friendship_panel"]["state"] == "pending_received"
        assert context["friendship_panel"]["can_accept"] is True
        assert context["friendship_panel"]["can_decline"] is True

    # PSP-07 — user not found → 404
    def test_psp07_user_not_found_returns_404(self):
        from app.api.web_routes.public_player import public_player_profile
        db = _profile_db(user=None, license=None)
        result = _run(public_player_profile(
            request=_req(), user_id=999, db=db, current_user=None,
        ))
        assert isinstance(result, HTMLResponse)
        assert result.status_code == 404

    # PSP-08 — no license → 404
    def test_psp08_no_license_returns_404(self):
        from app.api.web_routes.public_player import public_player_profile
        db = _profile_db(user=_user(uid=2), license=None)
        # first().side_effect has user at [0], None at [1] → license missing
        result = _run(public_player_profile(
            request=_req(), user_id=2, db=db, current_user=None,
        ))
        assert isinstance(result, HTMLResponse)
        assert result.status_code == 404


# ── PSP-09..PSP-11: POST /friends/cancel/{friendship_id} ─────────────────────

class TestCancelFriendRequest:

    def _db_with_row(self, row):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = row
        return db

    # PSP-09 — requester cancels PENDING → success redirect
    def test_psp09_requester_can_cancel_pending(self):
        from app.api.web_routes.friends import cancel_friend_request
        user = _user(uid=1)
        row  = _friendship_row(fid=10, requester_id=1, addressee_id=2,
                               status=FriendshipStatus.PENDING)
        db   = self._db_with_row(row)
        result = _run(cancel_friend_request(friendship_id=10, next=None, db=db, user=user))
        assert isinstance(result, RedirectResponse)
        assert "success=request_cancelled" in result.headers["location"]
        db.delete.assert_called_once_with(row)
        db.commit.assert_called_once()

    # PSP-10 — non-requester blocked → error redirect
    def test_psp10_non_requester_blocked(self):
        from app.api.web_routes.friends import cancel_friend_request
        user = _user(uid=3)   # addressee, not requester
        row  = _friendship_row(fid=10, requester_id=1, addressee_id=2,
                               status=FriendshipStatus.PENDING)
        db   = self._db_with_row(row)
        result = _run(cancel_friend_request(friendship_id=10, next=None, db=db, user=user))
        assert isinstance(result, RedirectResponse)
        assert "error=not_found" in result.headers["location"]
        db.delete.assert_not_called()

    # PSP-11 — non-PENDING row → error redirect
    def test_psp11_non_pending_blocked(self):
        from app.api.web_routes.friends import cancel_friend_request
        user = _user(uid=1)
        row  = _friendship_row(fid=10, requester_id=1, addressee_id=2,
                               status=FriendshipStatus.ACCEPTED)
        db   = self._db_with_row(row)
        result = _run(cancel_friend_request(friendship_id=10, next=None, db=db, user=user))
        assert isinstance(result, RedirectResponse)
        assert "error=not_pending" in result.headers["location"]
        db.delete.assert_not_called()


# ── PSP-12..PSP-14: _safe_next whitelist ─────────────────────────────────────

class TestSafeNext:
    """_safe_next whitelist validation via cancel + accept routes."""

    def _db_cancel(self, row):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = row
        return db

    # PSP-12 — /players/ prefix is accepted
    def test_psp12_players_prefix_accepted(self):
        from app.api.web_routes.friends import cancel_friend_request
        user = _user(uid=1)
        row  = _friendship_row(fid=10, requester_id=1, addressee_id=2,
                               status=FriendshipStatus.PENDING)
        db   = self._db_cancel(row)
        result = _run(cancel_friend_request(
            friendship_id=10, next="/players/2", db=db, user=user,
        ))
        assert result.headers["location"] == "/players/2"

    # PSP-13 — /friends prefix is accepted
    def test_psp13_friends_prefix_accepted(self):
        from app.api.web_routes.friends import accept_friend_request
        user = _user(uid=2)
        row  = _friendship_row(fid=10, requester_id=1, addressee_id=2,
                               status=FriendshipStatus.PENDING)
        db   = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = row
        with patch(f"{_BASE_FR}.notification_service"):
            result = _run(accept_friend_request(
                friendship_id=10, next="/friends/requests", db=db, user=user,
            ))
        assert result.headers["location"] == "/friends/requests"

    # PSP-14 — external URL falls back to default
    def test_psp14_external_url_rejected(self):
        from app.api.web_routes.friends import cancel_friend_request
        user = _user(uid=1)
        row  = _friendship_row(fid=10, requester_id=1, addressee_id=2,
                               status=FriendshipStatus.PENDING)
        db   = self._db_cancel(row)
        result = _run(cancel_friend_request(
            friendship_id=10, next="https://evil.com/steal", db=db, user=user,
        ))
        # External URL rejected — falls back to /friends?success=request_cancelled
        loc = result.headers["location"]
        assert "evil.com" not in loc
        assert loc.startswith("/friends")


# ── PSP model: get_friendship_panel_ctx helper ────────────────────────────────

class TestGetFriendshipPanelCtx:
    """Verify all states returned by get_friendship_panel_ctx()."""

    def _db_row(self, row=None):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = row
        return db

    def test_anonymous_state(self):
        ctx = get_friendship_panel_ctx(MagicMock(), None, 2)
        assert ctx["state"] == "anonymous"
        assert ctx["can_add"] is False

    def test_own_profile_state(self):
        ctx = get_friendship_panel_ctx(MagicMock(), 1, 1)
        assert ctx["state"] == "own_profile"

    def test_no_friendship_row(self):
        db = self._db_row(None)
        ctx = get_friendship_panel_ctx(db, 1, 2)
        assert ctx["state"] == "none"
        assert ctx["can_add"] is True

    def test_accepted_state(self):
        row = _friendship_row(fid=5, requester_id=1, addressee_id=2,
                              status=FriendshipStatus.ACCEPTED)
        db = self._db_row(row)
        ctx = get_friendship_panel_ctx(db, 1, 2)
        assert ctx["state"] == "accepted"
        assert ctx["can_remove"] is True
        assert ctx["friendship_id"] == 5

    def test_pending_sent_state(self):
        row = _friendship_row(fid=7, requester_id=1, addressee_id=2,
                              status=FriendshipStatus.PENDING)
        db = self._db_row(row)
        ctx = get_friendship_panel_ctx(db, 1, 2)
        assert ctx["state"] == "pending_sent"
        assert ctx["can_cancel"] is True
        assert ctx["can_accept"] is False

    def test_pending_received_state(self):
        row = _friendship_row(fid=7, requester_id=2, addressee_id=1,
                              status=FriendshipStatus.PENDING)
        db = self._db_row(row)
        ctx = get_friendship_panel_ctx(db, 1, 2)
        assert ctx["state"] == "pending_received"
        assert ctx["can_accept"] is True
        assert ctx["can_decline"] is True

    def test_declined_allows_re_add(self):
        row = _friendship_row(fid=3, requester_id=2, addressee_id=1,
                              status=FriendshipStatus.DECLINED)
        db = self._db_row(row)
        ctx = get_friendship_panel_ctx(db, 1, 2)
        assert ctx["state"] == "declined"
        assert ctx["can_add"] is True

    def test_blocked_no_actions(self):
        row = _friendship_row(fid=3, requester_id=2, addressee_id=1,
                              status=FriendshipStatus.BLOCKED)
        db = self._db_row(row)
        ctx = get_friendship_panel_ctx(db, 1, 2)
        assert ctx["state"] == "blocked"
        assert ctx["can_add"] is False
        assert ctx["can_cancel"] is False
        assert ctx["can_remove"] is False
