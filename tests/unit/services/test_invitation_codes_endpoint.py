"""
Unit tests for app/api/api_v1/endpoints/invitation_codes.py
Sprint 24 P2 — coverage: 34% stmt, 0% branch → ≥85%

6 endpoints + 1 hybrid auth helper:
1. get_admin_user_hybrid      dependency
2. get_all_invitation_codes   GET  /admin/invitation-codes
3. create_invitation_code     POST /admin/invitation-codes
4. delete_invitation_code     DELETE /admin/invitation-codes/{id}
5. validate_invitation_code   POST /invitation-codes/validate
6. redeem_invitation_code     POST /invitation-codes/redeem
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from datetime import datetime, timezone

from app.api.api_v1.endpoints.invitation_codes import (
    get_admin_user_hybrid,
    get_all_invitation_codes,
    create_invitation_code,
    delete_invitation_code,
    validate_invitation_code,
    redeem_invitation_code,
    InvitationCodeCreate,
    InvitationCodeRedeem,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.invitation_codes"
_VERIFY = "app.core.auth.verify_token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    u = MagicMock()
    u.id = 42
    u.name = "Admin User"
    u.email = "admin@lfa.com"
    u.role = UserRole.ADMIN
    u.is_active = True
    u.credit_balance = 0
    return u


def _student():
    u = MagicMock()
    u.id = 99
    u.name = "Student"
    u.email = "student@lfa.com"
    u.role = UserRole.STUDENT
    u.is_active = True
    u.credit_balance = 1000
    return u


def _icode(**kwargs):
    """Mock InvitationCode."""
    c = MagicMock()
    c.id = 1
    c.code = "INV-20260101-ABC123"
    c.invited_name = "Test Partner"
    c.invited_email = None
    c.bonus_credits = 500
    c.is_used = False
    c.used_by_user_id = None
    c.used_at = None
    c.created_by_admin_id = 42
    c.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.expires_at = None
    c.notes = None
    c.is_valid = MagicMock(return_value=True)
    c.can_be_used_by_email = MagicMock(return_value=True)
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def _q(first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    return q


def _db(first=None, all_=None):
    db = MagicMock()
    db.query.return_value = _q(first=first, all_=all_)
    return db


def _run(coro):
    return asyncio.run(coro)


# ===========================================================================
# get_admin_user_hybrid
# ===========================================================================

@pytest.mark.unit
class TestGetAdminUserHybrid:
    def _request(self, cookie=None):
        req = MagicMock()
        req.cookies.get.return_value = cookie
        return req

    def test_bearer_token_valid_admin_returns_user(self):
        admin = _admin()
        q = _q(first=admin)
        db = MagicMock(); db.query.return_value = q
        creds = MagicMock(); creds.credentials = "valid_bearer"
        with patch(_VERIFY, return_value="admin@lfa.com"):
            result = _run(get_admin_user_hybrid(
                request=self._request(),
                db=db,
                credentials=creds,
            ))
        assert result is admin

    def test_bearer_token_returns_non_admin_falls_to_cookie_then_403(self):
        non_admin = MagicMock(); non_admin.is_active = True; non_admin.role = UserRole.STUDENT
        q = _q(first=non_admin)
        db = MagicMock(); db.query.return_value = q
        creds = MagicMock(); creds.credentials = "student_token"
        # No cookie
        with patch(_VERIFY, return_value="student@lfa.com"):
            with pytest.raises(HTTPException) as exc:
                _run(get_admin_user_hybrid(
                    request=self._request(cookie=None),
                    db=db,
                    credentials=creds,
                ))
        assert exc.value.status_code == 403

    def test_no_credentials_cookie_valid_admin_returns_user(self):
        admin = _admin()
        q = _q(first=admin)
        db = MagicMock(); db.query.return_value = q
        with patch(_VERIFY, return_value="admin@lfa.com"):
            result = _run(get_admin_user_hybrid(
                request=self._request(cookie="Bearer valid_cookie"),
                db=db,
                credentials=None,
            ))
        assert result is admin

    def test_cookie_exception_falls_to_403(self):
        with patch(_VERIFY, side_effect=Exception("token error")):
            with pytest.raises(HTTPException) as exc:
                _run(get_admin_user_hybrid(
                    request=self._request(cookie="Bearer bad_token"),
                    db=_db(),
                    credentials=None,
                ))
        assert exc.value.status_code == 403

    def test_neither_method_works_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            _run(get_admin_user_hybrid(
                request=self._request(cookie=None),
                db=_db(),
                credentials=None,
            ))
        assert exc.value.status_code == 403


# ===========================================================================
# get_all_invitation_codes
# ===========================================================================

@pytest.mark.unit
class TestGetAllInvitationCodes:
    def test_empty_list_returns_empty(self):
        db = _db(all_=[])
        result = _run(get_all_invitation_codes(
            request=MagicMock(), db=db, current_user=_admin()
        ))
        assert result == []

    def test_code_without_user_ids_has_null_names(self):
        c = _icode(used_by_user_id=None, created_by_admin_id=None)
        db = _db(all_=[c])
        result = _run(get_all_invitation_codes(
            request=MagicMock(), db=db, current_user=_admin()
        ))
        assert len(result) == 1
        assert result[0]["used_by_name"] is None
        assert result[0]["created_by_name"] is None

    def test_code_with_used_by_user_id_fetches_name(self):
        # used_by_user_id=99, created_by_admin_id=None → 2 queries: all + user lookup
        c = _icode(used_by_user_id=99, created_by_admin_id=None)
        user = MagicMock(); user.name = "Student User"
        q_all = _q(all_=[c])
        q_user = _q(first=user)
        db = MagicMock()
        db.query.side_effect = [q_all, q_user]
        result = _run(get_all_invitation_codes(
            request=MagicMock(), db=db, current_user=_admin()
        ))
        assert result[0]["used_by_name"] == "Student User"

    def test_code_with_created_by_admin_id_fetches_name(self):
        # used_by_user_id=None, created_by_admin_id=42 → 2 queries: all + admin lookup
        c = _icode(used_by_user_id=None, created_by_admin_id=42)
        admin_user = MagicMock(); admin_user.name = "Admin User"
        q_all = _q(all_=[c])
        q_admin = _q(first=admin_user)
        db = MagicMock()
        db.query.side_effect = [q_all, q_admin]
        result = _run(get_all_invitation_codes(
            request=MagicMock(), db=db, current_user=_admin()
        ))
        assert result[0]["created_by_name"] == "Admin User"


# ===========================================================================
# create_invitation_code
# ===========================================================================

@pytest.mark.unit
class TestCreateInvitationCode:
    def _payload(self, credits=500):
        return InvitationCodeCreate(
            invited_name="Test Partner",
            bonus_credits=credits,
        )

    def test_nonpositive_credits_raises_400(self):
        db = _db()
        with pytest.raises(HTTPException) as exc:
            _run(create_invitation_code(
                request=MagicMock(),
                code_data=self._payload(credits=0),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400
        assert "positive" in exc.value.detail.lower()

    def test_too_many_duplicate_attempts_raises_500(self):
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = MagicMock()  # always finds duplicate → loop > 10
        db = MagicMock(); db.query.return_value = q
        with patch(f"{_BASE}.InvitationCode") as MockIC:
            MockIC.generate_code.return_value = "INV-ALWAYS-DUPLICATE"
            with pytest.raises(HTTPException) as exc:
                _run(create_invitation_code(
                    request=MagicMock(),
                    code_data=self._payload(),
                    db=db,
                    current_user=_admin(),
                ))
        assert exc.value.status_code == 500

    def test_success_returns_invitation_code_response(self):
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None   # no duplicate
        db = MagicMock(); db.query.return_value = q

        mock_ic = _icode()
        with patch(f"{_BASE}.InvitationCode") as MockIC:
            MockIC.generate_code.return_value = "INV-20260101-ABC123"
            MockIC.return_value = mock_ic
            result = _run(create_invitation_code(
                request=MagicMock(),
                code_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        assert result.code == "INV-20260101-ABC123"
        assert result.bonus_credits == 500
        db.add.assert_called_once_with(mock_ic)
        db.commit.assert_called_once()


# ===========================================================================
# delete_invitation_code
# ===========================================================================

@pytest.mark.unit
class TestDeleteInvitationCode:
    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(delete_invitation_code(
                request=MagicMock(), code_id=99, db=db, current_user=_admin()
            ))
        assert exc.value.status_code == 404

    def test_already_used_raises_400(self):
        c = _icode(is_used=True)
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(delete_invitation_code(
                request=MagicMock(), code_id=1, db=db, current_user=_admin()
            ))
        assert exc.value.status_code == 400
        assert "used" in exc.value.detail.lower()

    def test_success_deletes_and_returns_message(self):
        c = _icode(is_used=False)
        db = _db(first=c)
        result = _run(delete_invitation_code(
            request=MagicMock(), code_id=1, db=db, current_user=_admin()
        ))
        db.delete.assert_called_once_with(c)
        db.commit.assert_called_once()
        assert result["success"] is True


# ===========================================================================
# validate_invitation_code
# ===========================================================================

@pytest.mark.unit
class TestValidateInvitationCode:
    def _req(self, code="TESTCODE"):
        return InvitationCodeRedeem(code=code)

    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(validate_invitation_code(
                request=MagicMock(), redeem_data=self._req(), db=db
            ))
        assert exc.value.status_code == 404

    def test_already_used_raises_400(self):
        c = _icode(is_used=True)
        c.is_valid.return_value = False
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(validate_invitation_code(
                request=MagicMock(), redeem_data=self._req(), db=db
            ))
        assert exc.value.status_code == 400
        assert "already been used" in exc.value.detail

    def test_expired_raises_400(self):
        c = _icode(is_used=False)
        c.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)  # past
        c.is_valid.return_value = False
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(validate_invitation_code(
                request=MagicMock(), redeem_data=self._req(), db=db
            ))
        assert exc.value.status_code == 400
        assert "expired" in exc.value.detail

    def test_valid_code_returns_details(self):
        c = _icode()
        db = _db(first=c)
        result = _run(validate_invitation_code(
            request=MagicMock(), redeem_data=self._req(), db=db
        ))
        assert result["success"] is True
        assert result["valid"] is True
        assert result["bonus_credits"] == 500


# ===========================================================================
# redeem_invitation_code
# ===========================================================================

@pytest.mark.unit
class TestRedeemInvitationCode:
    _GCUW = f"{_BASE}.get_current_user_web"

    def _req(self, code="TESTCODE"):
        return InvitationCodeRedeem(code=code)

    def test_auth_exception_raises_401(self):
        db = _db()
        with patch(self._GCUW, side_effect=Exception("not logged in")):
            with pytest.raises(HTTPException) as exc:
                _run(redeem_invitation_code(
                    request=MagicMock(), redeem_data=self._req(), db=db
                ))
        assert exc.value.status_code == 401

    def test_code_not_found_raises_404(self):
        user = _student()
        db = _db(first=None)
        with patch(self._GCUW, new_callable=AsyncMock, return_value=user):
            with pytest.raises(HTTPException) as exc:
                _run(redeem_invitation_code(
                    request=MagicMock(), redeem_data=self._req(), db=db
                ))
        assert exc.value.status_code == 404

    def test_already_used_code_raises_400(self):
        user = _student()
        c = _icode(is_used=True)
        c.is_valid.return_value = False
        db = _db(first=c)
        with patch(self._GCUW, new_callable=AsyncMock, return_value=user):
            with pytest.raises(HTTPException) as exc:
                _run(redeem_invitation_code(
                    request=MagicMock(), redeem_data=self._req(), db=db
                ))
        assert exc.value.status_code == 400

    def test_expired_code_raises_400(self):
        user = _student()
        c = _icode(is_used=False)
        c.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        c.is_valid.return_value = False
        db = _db(first=c)
        with patch(self._GCUW, new_callable=AsyncMock, return_value=user):
            with pytest.raises(HTTPException) as exc:
                _run(redeem_invitation_code(
                    request=MagicMock(), redeem_data=self._req(), db=db
                ))
        assert exc.value.status_code == 400

    def test_email_restriction_raises_403(self):
        user = _student()
        c = _icode()
        c.can_be_used_by_email.return_value = False  # email doesn't match
        db = _db(first=c)
        with patch(self._GCUW, new_callable=AsyncMock, return_value=user):
            with pytest.raises(HTTPException) as exc:
                _run(redeem_invitation_code(
                    request=MagicMock(), redeem_data=self._req(), db=db
                ))
        assert exc.value.status_code == 403

    def test_already_redeemed_raises_400(self):
        user = _student()
        c = _icode()     # valid code
        prior = _icode() # user already redeemed another code
        q_code = _q(first=c)
        q_prior = _q(first=prior)
        db = MagicMock()
        db.query.side_effect = [q_code, q_prior]
        with patch(self._GCUW, new_callable=AsyncMock, return_value=user):
            with pytest.raises(HTTPException) as exc:
                _run(redeem_invitation_code(
                    request=MagicMock(), redeem_data=self._req(), db=db
                ))
        assert exc.value.status_code == 400
        assert "already redeemed" in exc.value.detail

    def test_success_adds_credits_and_marks_used(self):
        user = _student()
        user.credit_balance = 1000
        c = _icode(bonus_credits=500)
        q_code = _q(first=c)
        q_prior = _q(first=None)   # no prior redemption
        db = MagicMock()
        db.query.side_effect = [q_code, q_prior]
        with patch(self._GCUW, new_callable=AsyncMock, return_value=user):
            result = _run(redeem_invitation_code(
                request=MagicMock(), redeem_data=self._req(), db=db
            ))
        assert result["success"] is True
        assert result["bonus_credits"] == 500
        assert result["old_balance"] == 1000
        assert user.credit_balance == 1500  # 1000 + 500
        assert c.is_used is True
        db.commit.assert_called_once()
