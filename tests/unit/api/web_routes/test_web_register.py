"""
Integration tests for POST /register — invite code registration flow.

Covers (REG-01 … REG-09):
  REG-01  valid open code + valid form            → 303 /dashboard + user created
  REG-02  email-restricted code + correct email   → 303 /dashboard
  REG-03  email-restricted code + wrong email     → 200, specific error
  REG-04  already-used code                       → 200, "already been used"
  REG-05  expired code                            → 200, "expired"
  REG-06  completely invalid code                 → 200, "Invalid invitation code"
  REG-07  duplicate email                         → 200, "already exists"
  REG-08  post-commit session failure (zombie)    → 303 /login?registered=1
  REG-09  ORM user delete after invite bonus      → no IntegrityError

Tests use the real DB session so they verify actual SQL/constraint behaviour.
Every test cleans up after itself.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.database import SessionLocal
from app.models.credit_transaction import CreditTransaction, TransactionType
from app.models.invitation_code import InvitationCode
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.api.web_routes.auth import register_submit

_BASE = "app.api.web_routes.auth"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _mock_request():
    req = MagicMock()
    req.cookies = {}
    return req


def _settings():
    m = MagicMock()
    m.ACCESS_TOKEN_EXPIRE_MINUTES = 60
    m.COOKIE_HTTPONLY = True
    m.COOKIE_MAX_AGE = 3600
    m.COOKIE_SECURE = False
    m.COOKIE_SAMESITE = "lax"
    return m


VALID_FORM = dict(
    first_name="Test",
    last_name="Tester",
    nickname="reg_test_nick",
    email="reg_test@example.com",
    password="pass123",
    phone="+36201234567",
    date_of_birth="1990-06-15",
    nationality="HU",
    secondary_nationality="",
    gender="Male",
    street_address="Test St 1",
    city="Budapest",
    postal_code="1052",
    country="Hungary",
)


def _call_register(db, form_overrides=None):
    """Call register_submit with mock request + real DB, return response."""
    form = {**VALID_FORM, **(form_overrides or {})}
    with patch(f"{_BASE}.templates") as mock_tmpl, \
         patch(f"{_BASE}.settings", _settings()), \
         patch(f"{_BASE}.create_access_token", return_value="fake.jwt.token"):

        mock_tmpl.TemplateResponse.return_value = MagicMock(status_code=200)

        return _run(register_submit(
            request=_mock_request(),
            first_name=form["first_name"],
            last_name=form["last_name"],
            nickname=form["nickname"],
            email=form["email"],
            password=form["password"],
            phone=form["phone"],
            date_of_birth=form["date_of_birth"],
            nationality=form["nationality"],
            secondary_nationality=form["secondary_nationality"],
            gender=form["gender"],
            street_address=form["street_address"],
            city=form["city"],
            postal_code=form["postal_code"],
            country=form["country"],
            invitation_code=form.get("invitation_code", ""),
            db=db,
        )), mock_tmpl


def _make_open_code(db, bonus=50, suffix="") -> InvitationCode:
    """Insert a fresh unused open invite code, return it.
    Code is always stored uppercase to match handler's .upper() normalisation.
    """
    from app.models.invitation_code import InvitationCode as IC
    code = IC(
        code=f"INV-TEST-REG{suffix}".upper(),
        invited_name="Test",
        invited_email=None,
        bonus_credits=bonus,
        is_used=False,
    )
    db.add(code)
    db.flush()
    return code


def _make_restricted_code(db, email: str, bonus=50, suffix="") -> InvitationCode:
    from app.models.invitation_code import InvitationCode as IC
    code = IC(
        code=f"INV-TEST-RST{suffix}".upper(),
        invited_name="Test",
        invited_email=email,
        bonus_credits=bonus,
        is_used=False,
    )
    db.add(code)
    db.flush()
    return code


def _make_used_code(db, suffix="") -> InvitationCode:
    from app.models.invitation_code import InvitationCode as IC
    code = IC(
        code=f"INV-TEST-USD{suffix}".upper(),
        invited_name="Test",
        invited_email=None,
        bonus_credits=10,
        is_used=True,
        used_at=datetime.now(timezone.utc),
    )
    db.add(code)
    db.flush()
    return code


def _make_expired_code(db, suffix="") -> InvitationCode:
    from app.models.invitation_code import InvitationCode as IC
    code = IC(
        code=f"INV-TEST-EXP{suffix}".upper(),
        invited_name="Test",
        invited_email=None,
        bonus_credits=10,
        is_used=False,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(code)
    db.flush()
    return code


def _cleanup(db, email: str, code_prefix: str = None):
    u = db.query(User).filter(User.email == email).first()
    if u:
        db.execute(text(f"DELETE FROM credit_transactions WHERE user_id = {u.id}"))
        db.execute(text(f"DELETE FROM users WHERE id = {u.id}"))
    if code_prefix:
        prefix = code_prefix.upper()
        db.execute(text(f"DELETE FROM invitation_codes WHERE code LIKE '{prefix}%'"))
    db.commit()
    db.close()


def _get_template_call_kwarg(mock_tmpl, key: str):
    """Extract a context variable from the last TemplateResponse call."""
    call = mock_tmpl.TemplateResponse.call_args
    if call is None:
        return None
    ctx = call.args[1] if len(call.args) > 1 else call.kwargs.get("context", {})
    return ctx.get(key)


# ─────────────────────────────────────────────────────────────────────────────
# REG-01: valid open code → 303 /dashboard, user + tx created
# ─────────────────────────────────────────────────────────────────────────────

class TestReg01ValidOpenCode:

    def test_redirects_to_dashboard(self):
        db = SessionLocal()
        try:
            code = _make_open_code(db, bonus=75, suffix="01")
            db.commit()

            resp, _ = _call_register(db, {
                "email": "reg01@example.com",
                "nickname": "reg01nick",
                "invitation_code": code.code,
            })

            assert isinstance(resp, RedirectResponse)
            assert resp.status_code == 303
            assert "/dashboard" in resp.headers["location"]
        finally:
            _cleanup(db, "reg01@example.com", "INV-TEST-REG01")

    def test_user_created_with_correct_credits(self):
        db = SessionLocal()
        try:
            code = _make_open_code(db, bonus=75, suffix="01b")
            db.commit()

            _call_register(db, {
                "email": "reg01b@example.com",
                "nickname": "reg01bnick",
                "invitation_code": code.code,
            })

            u = db.query(User).filter(User.email == "reg01b@example.com").first()
            assert u is not None
            assert u.credit_balance == 75
            assert u.role == UserRole.STUDENT
        finally:
            _cleanup(db, "reg01b@example.com", "INV-TEST-REG01b")

    def test_credit_transaction_created(self):
        db = SessionLocal()
        try:
            code = _make_open_code(db, bonus=50, suffix="01c")
            db.commit()

            _call_register(db, {
                "email": "reg01c@example.com",
                "nickname": "reg01cnick",
                "invitation_code": code.code,
            })

            u = db.query(User).filter(User.email == "reg01c@example.com").first()
            tx = db.query(CreditTransaction).filter(CreditTransaction.user_id == u.id).first()
            assert tx is not None
            assert tx.transaction_type == TransactionType.INVITATION_BONUS.value
            assert tx.amount == 50
            assert tx.user_license_id is None
        finally:
            _cleanup(db, "reg01c@example.com", "INV-TEST-REG01c")

    def test_invite_code_marked_used(self):
        db = SessionLocal()
        try:
            code = _make_open_code(db, suffix="01d")
            db.commit()

            _call_register(db, {
                "email": "reg01d@example.com",
                "nickname": "reg01dnick",
                "invitation_code": code.code,
            })

            db.expire(code)
            assert code.is_used is True
            assert code.used_by_user_id is not None
        finally:
            _cleanup(db, "reg01d@example.com", "INV-TEST-REG01d")


# ─────────────────────────────────────────────────────────────────────────────
# REG-02: email-restricted code + correct email → 303 /dashboard
# ─────────────────────────────────────────────────────────────────────────────

class TestReg02RestrictedCorrectEmail:

    def test_succeeds_with_matching_email(self):
        db = SessionLocal()
        restricted_email = "restricted02@example.com"
        try:
            code = _make_restricted_code(db, email=restricted_email, suffix="02")
            db.commit()

            resp, _ = _call_register(db, {
                "email": restricted_email,
                "nickname": "reg02nick",
                "invitation_code": code.code,
            })

            assert isinstance(resp, RedirectResponse)
            assert resp.status_code == 303
        finally:
            _cleanup(db, restricted_email, "INV-TEST-RST02")


# ─────────────────────────────────────────────────────────────────────────────
# REG-03: email-restricted code + wrong email → 200, specific error
# ─────────────────────────────────────────────────────────────────────────────

class TestReg03RestrictedWrongEmail:

    def test_shows_specific_error_message(self):
        db = SessionLocal()
        try:
            code = _make_restricted_code(db, email="correct@example.com", suffix="03")
            db.commit()

            resp, mock_tmpl = _call_register(db, {
                "email": "wrong03@example.com",
                "nickname": "reg03nick",
                "invitation_code": code.code,
            })

            assert not isinstance(resp, RedirectResponse)
            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert error_msg is not None
            assert "specific email address" in error_msg
            assert "invitation on" in error_msg
        finally:
            _cleanup(db, "wrong03@example.com", "INV-TEST-RST03")

    def test_user_not_created(self):
        db = SessionLocal()
        try:
            code = _make_restricted_code(db, email="correct@example.com", suffix="03b")
            db.commit()

            _call_register(db, {
                "email": "wrong03b@example.com",
                "nickname": "reg03bnick",
                "invitation_code": code.code,
            })

            u = db.query(User).filter(User.email == "wrong03b@example.com").first()
            assert u is None
        finally:
            _cleanup(db, "wrong03b@example.com", "INV-TEST-RST03b")


# ─────────────────────────────────────────────────────────────────────────────
# REG-04: already-used code → 200, "already been used"
# ─────────────────────────────────────────────────────────────────────────────

class TestReg04UsedCode:

    def test_shows_already_used_message(self):
        db = SessionLocal()
        try:
            code = _make_used_code(db, suffix="04")
            db.commit()

            resp, mock_tmpl = _call_register(db, {
                "email": "reg04@example.com",
                "nickname": "reg04nick",
                "invitation_code": code.code,
            })

            assert not isinstance(resp, RedirectResponse)
            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert "already been used" in error_msg
        finally:
            _cleanup(db, "reg04@example.com", "INV-TEST-USD04")

    def test_does_not_mention_expired(self):
        db = SessionLocal()
        try:
            code = _make_used_code(db, suffix="04b")
            db.commit()

            _, mock_tmpl = _call_register(db, {
                "email": "reg04b@example.com",
                "nickname": "reg04bnick",
                "invitation_code": code.code,
            })

            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert "expired" not in error_msg
        finally:
            _cleanup(db, "reg04b@example.com", "INV-TEST-USD04b")


# ─────────────────────────────────────────────────────────────────────────────
# REG-05: expired code → 200, "expired" message, no "used" mention
# ─────────────────────────────────────────────────────────────────────────────

class TestReg05ExpiredCode:

    def test_shows_expired_message(self):
        db = SessionLocal()
        try:
            code = _make_expired_code(db, suffix="05")
            db.commit()

            resp, mock_tmpl = _call_register(db, {
                "email": "reg05@example.com",
                "nickname": "reg05nick",
                "invitation_code": code.code,
            })

            assert not isinstance(resp, RedirectResponse)
            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert "expired" in error_msg
            assert "administrator" in error_msg
        finally:
            _cleanup(db, "reg05@example.com", "INV-TEST-EXP05")

    def test_does_not_say_already_used(self):
        db = SessionLocal()
        try:
            code = _make_expired_code(db, suffix="05b")
            db.commit()

            _, mock_tmpl = _call_register(db, {
                "email": "reg05b@example.com",
                "nickname": "reg05bnick",
                "invitation_code": code.code,
            })

            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert "already been used" not in error_msg
        finally:
            _cleanup(db, "reg05b@example.com", "INV-TEST-EXP05b")


# ─────────────────────────────────────────────────────────────────────────────
# REG-06: invalid code → 200, "Invalid invitation code"
# ─────────────────────────────────────────────────────────────────────────────

class TestReg06InvalidCode:

    def test_shows_invalid_code_message(self):
        db = SessionLocal()
        try:
            resp, mock_tmpl = _call_register(db, {
                "email": "reg06@example.com",
                "nickname": "reg06nick",
                "invitation_code": "INV-TOTALLY-FAKE",
            })

            assert not isinstance(resp, RedirectResponse)
            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert "Invalid invitation code" in error_msg
            assert "typos" in error_msg
        finally:
            _cleanup(db, "reg06@example.com")


# ─────────────────────────────────────────────────────────────────────────────
# REG-07: duplicate email → 200, "already exists"
# ─────────────────────────────────────────────────────────────────────────────

class TestReg07DuplicateEmail:

    def test_shows_email_exists_message(self):
        db = SessionLocal()
        try:
            # First registration
            code1 = _make_open_code(db, suffix="07a")
            db.commit()
            _call_register(db, {
                "email": "reg07@example.com",
                "nickname": "reg07nick",
                "invitation_code": code1.code,
            })

            # Second registration with same email + different valid code
            code2 = _make_open_code(db, suffix="07b")
            db.commit()
            resp, mock_tmpl = _call_register(db, {
                "email": "reg07@example.com",
                "nickname": "reg07nick2",
                "invitation_code": code2.code,
            })

            assert not isinstance(resp, RedirectResponse)
            error_msg = _get_template_call_kwarg(mock_tmpl, "error")
            assert "already exists" in error_msg
        finally:
            _cleanup(db, "reg07@example.com", "INV-TEST-REG07")


# ─────────────────────────────────────────────────────────────────────────────
# REG-08: post-commit session failure (zombie) → redirect /login?registered=1
# ─────────────────────────────────────────────────────────────────────────────

class TestReg08ZombieAccountPrevention:

    def test_redirects_to_login_when_token_creation_fails(self):
        db = SessionLocal()
        try:
            code = _make_open_code(db, suffix="08")
            db.commit()

            form = {**VALID_FORM, "email": "reg08@example.com",
                    "nickname": "reg08nick", "invitation_code": code.code}

            with patch(f"{_BASE}.templates"), \
                 patch(f"{_BASE}.settings", _settings()), \
                 patch(f"{_BASE}.create_access_token", side_effect=Exception("JWT key missing")):
                resp = _run(register_submit(
                    request=_mock_request(),
                    first_name=form["first_name"], last_name=form["last_name"],
                    nickname=form["nickname"], email=form["email"],
                    password=form["password"], phone=form["phone"],
                    date_of_birth=form["date_of_birth"], nationality=form["nationality"],
                    secondary_nationality=form["secondary_nationality"],
                    gender=form["gender"], street_address=form["street_address"],
                    city=form["city"], postal_code=form["postal_code"],
                    country=form["country"], invitation_code=form["invitation_code"],
                    db=db,
                ))

            assert isinstance(resp, RedirectResponse)
            assert resp.status_code == 303
            location = resp.headers["location"]
            assert "/login" in location
            assert "registered=1" in location
        finally:
            _cleanup(db, "reg08@example.com", "INV-TEST-REG08")

    def test_user_exists_in_db_after_zombie_redirect(self):
        """After a post-commit failure the user record must still be persisted."""
        db = SessionLocal()
        try:
            code = _make_open_code(db, suffix="08b")
            db.commit()

            form = {**VALID_FORM, "email": "reg08b@example.com",
                    "nickname": "reg08bnick", "invitation_code": code.code}

            with patch(f"{_BASE}.templates"), \
                 patch(f"{_BASE}.settings", _settings()), \
                 patch(f"{_BASE}.create_access_token", side_effect=Exception("JWT key missing")):
                _run(register_submit(
                    request=_mock_request(),
                    first_name=form["first_name"], last_name=form["last_name"],
                    nickname=form["nickname"], email=form["email"],
                    password=form["password"], phone=form["phone"],
                    date_of_birth=form["date_of_birth"], nationality=form["nationality"],
                    secondary_nationality=form["secondary_nationality"],
                    gender=form["gender"], street_address=form["street_address"],
                    city=form["city"], postal_code=form["postal_code"],
                    country=form["country"], invitation_code=form["invitation_code"],
                    db=db,
                ))

            u = db.query(User).filter(User.email == "reg08b@example.com").first()
            assert u is not None, "User must be persisted even when session creation fails"
        finally:
            _cleanup(db, "reg08b@example.com", "INV-TEST-REG08b")


# ─────────────────────────────────────────────────────────────────────────────
# REG-09: ORM user delete after invite bonus → no IntegrityError
# ─────────────────────────────────────────────────────────────────────────────

class TestReg09OrmDeleteAfterInviteBonus:

    def test_delete_user_with_invitation_bonus_tx_succeeds(self):
        db = SessionLocal()
        try:
            u = User(
                name="Del09 Test", first_name="Del09", last_name="Test",
                nickname="del09nick", email="del09@example.com",
                password_hash=get_password_hash("x"),
                role=UserRole.STUDENT, is_active=True, credit_balance=30,
            )
            db.add(u)
            db.flush()
            tx = CreditTransaction(
                user_id=u.id, amount=30,
                transaction_type=TransactionType.INVITATION_BONUS.value,
                description="reg09 test",
                balance_after=30,
                idempotency_key=f"test_reg09:{u.id}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(tx)
            db.commit()

            # This was failing with IntegrityError before passive_deletes fix
            db.delete(u)
            db.commit()

            assert db.query(User).filter(User.email == "del09@example.com").first() is None
        except Exception as e:
            db.rollback()
            pytest.fail(f"ORM delete raised unexpected exception: {e}")
        finally:
            _cleanup(db, "del09@example.com")

    def test_credit_transactions_cascade_deleted(self):
        db = SessionLocal()
        tx_id = None
        try:
            u = User(
                name="Del09b Test", first_name="Del09b", last_name="Test",
                nickname="del09bnick", email="del09b@example.com",
                password_hash=get_password_hash("x"),
                role=UserRole.STUDENT, is_active=True, credit_balance=30,
            )
            db.add(u)
            db.flush()
            tx = CreditTransaction(
                user_id=u.id, amount=30,
                transaction_type=TransactionType.INVITATION_BONUS.value,
                description="reg09b test",
                balance_after=30,
                idempotency_key=f"test_reg09b:{u.id}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(tx)
            db.commit()
            tx_id = tx.id

            db.delete(u)
            db.commit()

            remaining = db.query(CreditTransaction).filter(
                CreditTransaction.id == tx_id
            ).first()
            assert remaining is None, "CreditTransaction must be cascade-deleted with user"
        except Exception as e:
            db.rollback()
            pytest.fail(f"Unexpected exception: {e}")
        finally:
            _cleanup(db, "del09b@example.com")
