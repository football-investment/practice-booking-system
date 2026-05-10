"""
Regression tests: /register nationality select is never empty.

Root cause that was fixed: Jinja2 silently produces an empty for-loop when
`country_list` is missing from the template context (UndefinedError swallowed).
This means any render path that forgets to pass `country_list` → silent empty
<select> with no error, no 500 — just a blank dropdown.

These tests guard all render paths:
  - GET /register (clean browser state)
  - POST /register with validation error → re-render must still have options
  - POST /register with invalid nationality → re-render must still have options
"""

import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.invitation_code import InvitationCode


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ── Client fixture (CSRF bypass via Bearer header) ────────────────────────────

@pytest.fixture
def anon_client(test_db: Session):
    """Unauthenticated TestClient with CSRF bypass for register flow tests."""
    def _override_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"}) as c:
        yield c
    app.dependency_overrides.clear()


def _nationality_options(html: str) -> list[str]:
    """Return all 2-letter ISO code values found in nationality <select> options."""
    return re.findall(r'<option value="([A-Z]{2})"', html)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_get_register_has_nationality_options(anon_client: TestClient):
    """GET /register must return nationality select with all options — clean state."""
    r = anon_client.get("/register")
    assert r.status_code == 200
    options = _nationality_options(r.text)
    assert len(options) >= 29, f"Expected ≥29 nationality options, got {len(options)}"
    assert "HU" in options, "HU not in nationality options"
    assert "🇭🇺 Hungary" in r.text or "Hungary" in r.text


def test_get_register_hu_option_value_is_iso_code(anon_client: TestClient):
    """Hungary option value must be 'HU' (ISO), not 'Hungarian' (legacy text)."""
    r = anon_client.get("/register")
    assert 'value="HU"' in r.text
    assert 'value="Hungarian"' not in r.text


def test_post_register_invalid_nationality_rerenders_with_options(
    anon_client: TestClient, test_db: Session
):
    """POST with invalid nationality → validation error re-render still has select options."""
    inv = InvitationCode(
        code=f"INV-NAT-{_uid()[:6].upper()}",
        invited_name="Test",
        bonus_credits=0,
        is_used=False,
    )
    test_db.add(inv)
    test_db.flush()

    r = anon_client.post(
        "/register",
        data={
            "first_name": "Test",
            "last_name": "User",
            "nickname": "tuser",
            "email": f"nat-{_uid()}@test.lfa",
            "password": "pass123",
            "phone": "+36201234567",
            "date_of_birth": "2000-01-01",
            "nationality": "INVALID_CODE",
            "gender": "Male",
            "street_address": "Street 1",
            "city": "City",
            "postal_code": "1111",
            "country": "Country",
            "invitation_code": inv.code,
        },
        follow_redirects=False,
    )
    assert r.status_code == 200, f"Expected 200 error re-render, got {r.status_code}"
    options = _nationality_options(r.text)
    assert len(options) >= 29, (
        f"Error re-render must preserve nationality options — got {len(options)}"
    )
    assert "HU" in options
    assert "valid nationality" in r.text.lower() or "nationality" in r.text.lower()


def test_post_register_short_name_rerenders_with_options(
    anon_client: TestClient, test_db: Session
):
    """POST with short first name (other validation error) → re-render still has options."""
    inv = InvitationCode(
        code=f"INV-NAT2-{_uid()[:5].upper()}",
        invited_name="Test",
        bonus_credits=0,
        is_used=False,
    )
    test_db.add(inv)
    test_db.flush()

    r = anon_client.post(
        "/register",
        data={
            "first_name": "X",  # too short → validation error
            "last_name": "User",
            "nickname": "tuser",
            "email": f"nat2-{_uid()}@test.lfa",
            "password": "pass123",
            "phone": "+36201234567",
            "date_of_birth": "2000-01-01",
            "nationality": "HU",
            "gender": "Male",
            "street_address": "Street 1",
            "city": "City",
            "postal_code": "1111",
            "country": "Country",
            "invitation_code": inv.code,
        },
        follow_redirects=False,
    )
    assert r.status_code == 200
    options = _nationality_options(r.text)
    assert len(options) >= 29, (
        f"Non-nationality validation error re-render must still preserve options — got {len(options)}"
    )


def test_post_register_valid_nationality_accepted(
    anon_client: TestClient, test_db: Session
):
    """POST with valid ISO nationality (HU) must succeed and redirect."""
    inv = InvitationCode(
        code=f"INV-HU-{_uid()[:6].upper()}",
        invited_name="Test",
        bonus_credits=0,
        is_used=False,
    )
    test_db.add(inv)
    test_db.flush()

    r = anon_client.post(
        "/register",
        data={
            "first_name": "Teszt",
            "last_name": "Felhasznalo",
            "nickname": "tfelh",
            "email": f"hu-nat-{_uid()}@test.lfa",
            "password": "pass123",
            "phone": "+36201234567",
            "date_of_birth": "2000-01-01",
            "nationality": "HU",
            "gender": "Male",
            "street_address": "Street 1",
            "city": "Budapest",
            "postal_code": "1055",
            "country": "Hungary",
            "invitation_code": inv.code,
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, (
        f"Valid HU nationality must produce 303 redirect, got {r.status_code}. "
        f"Body: {r.text[:400]}"
    )


# ── Secondary nationality tests ───────────────────────────────────────────────

def _base_data(inv_code: str, uid: str, **overrides) -> dict:
    data = {
        "first_name": "Teszt",
        "last_name": "Felhasznalo",
        "nickname": f"tfelh{uid[:4]}",
        "email": f"sec-{uid}@test.lfa",
        "password": "pass123",
        "phone": "+36201234567",
        "date_of_birth": "2000-01-01",
        "nationality": "HU",
        "gender": "Male",
        "street_address": "Street 1",
        "city": "Budapest",
        "postal_code": "1055",
        "country": "Hungary",
        "invitation_code": inv_code,
    }
    data.update(overrides)
    return data


def _fresh_inv(test_db: Session) -> InvitationCode:
    inv = InvitationCode(
        code=f"INV-S-{_uid()[:6].upper()}",
        invited_name="Test",
        bonus_credits=0,
        is_used=False,
    )
    test_db.add(inv)
    test_db.flush()
    return inv


def test_get_register_has_secondary_nationality_select(anon_client: TestClient):
    """GET /register must contain the secondary_nationality select element."""
    r = anon_client.get("/register")
    assert r.status_code == 200
    assert 'name="secondary_nationality"' in r.text
    assert "No secondary nationality" in r.text
    # Both selects should have HU option
    assert r.text.count('value="HU"') >= 2


def test_post_register_valid_primary_and_secondary(
    anon_client: TestClient, test_db: Session
):
    """POST with valid primary HU + secondary BR → 303 redirect."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, secondary_nationality="BR"),
        follow_redirects=False,
    )
    assert r.status_code == 303, f"Expected 303, got {r.status_code}. Body: {r.text[:400]}"


def test_post_register_same_primary_secondary_rejected(
    anon_client: TestClient, test_db: Session
):
    """POST with primary == secondary (HU == HU) → validation error, selects not empty."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, secondary_nationality="HU"),
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "different" in r.text.lower() or "secondary" in r.text.lower()
    # Both selects must still have options
    assert _nationality_options(r.text).__len__() >= 29


def test_post_register_invalid_secondary_rejected(
    anon_client: TestClient, test_db: Session
):
    """POST with invalid secondary code → validation error, selects preserved."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, secondary_nationality="INVALID"),
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "secondary" in r.text.lower() or "valid" in r.text.lower()
    assert _nationality_options(r.text).__len__() >= 29


def test_post_register_no_secondary_accepted(
    anon_client: TestClient, test_db: Session
):
    """POST with no secondary_nationality → accepted (it is optional)."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid),  # no secondary_nationality key
        follow_redirects=False,
    )
    assert r.status_code == 303, f"No secondary must be accepted, got {r.status_code}. Body: {r.text[:400]}"


def test_post_register_empty_secondary_accepted(
    anon_client: TestClient, test_db: Session
):
    """POST with empty string secondary_nationality → treated as None, accepted."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, secondary_nationality=""),
        follow_redirects=False,
    )
    assert r.status_code == 303, f"Empty secondary must be accepted, got {r.status_code}. Body: {r.text[:400]}"


# ── Duplicate-guard explicit proof ───────────────────────────────────────────
#
# Backend validation order (auth.py:318-324):
#   1. nationality not in COUNTRY_CODES  → "valid nationality" error
#   2. secondary not in COUNTRY_CODES    → "valid secondary nationality" error
#   3. secondary == nationality           → "must be different" error
# COUNTRY_CODES is a frozenset of UPPERCASE 2-letter codes — no normalisation.
# Therefore lowercase / freetext inputs are caught by check 1 or 2 before
# reaching check 3, so they can never bypass the duplicate guard.

def test_post_register_ca_ca_same_rejected(
    anon_client: TestClient, test_db: Session
):
    """CA primary + CA secondary (both valid ISO) → rejected as duplicate."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, nationality="CA", secondary_nationality="CA"),
        follow_redirects=False,
    )
    assert r.status_code == 200, f"Expected 200 error, got {r.status_code}"
    assert "different" in r.text.lower() or "secondary" in r.text.lower()
    assert _nationality_options(r.text).__len__() >= 29, "Selects must be preserved on error"


def test_post_register_lowercase_primary_rejected(
    anon_client: TestClient, test_db: Session
):
    """Lowercase 'ca' primary → rejected as invalid (not in COUNTRY_CODES) before dup check."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, nationality="ca", secondary_nationality="CA"),
        follow_redirects=False,
    )
    assert r.status_code == 200, f"Expected 200 error, got {r.status_code}"
    # Backend rejects before DB write — both selects preserved
    assert _nationality_options(r.text).__len__() >= 29, "Selects must be preserved on error"


def test_post_register_freetext_primary_rejected(
    anon_client: TestClient, test_db: Session
):
    """Freetext 'Canada' primary → rejected as invalid (not in COUNTRY_CODES)."""
    inv = _fresh_inv(test_db)
    uid = _uid()
    r = anon_client.post(
        "/register",
        data=_base_data(inv.code, uid, nationality="Canada", secondary_nationality="CA"),
        follow_redirects=False,
    )
    assert r.status_code == 200, f"Expected 200 error, got {r.status_code}"
    assert "nationality" in r.text.lower()
    assert _nationality_options(r.text).__len__() >= 29, "Selects must be preserved on error"
