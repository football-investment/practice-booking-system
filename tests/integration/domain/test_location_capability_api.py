"""
API-level integration tests — CENTER vs PARTNER location capability enforcement
================================================================================

Uses SAVEPOINT-isolated ``test_db`` + shared-session ``client`` from
``tests/integration/conftest.py``.  All data is rolled back at teardown.

The ``client`` fixture overrides ``get_db`` so the API endpoint shares the same
transactional session as the test itself: builders only need ``flush()`` before
the API call, and endpoints see the data immediately.

Tests
-----
  LOC-API-01  POST /api/v1/semesters/generate-academy-season — PARTNER location → 400
  LOC-API-02  POST /api/v1/semesters/generate-academy-season — CENTER location → 201 (or 409 dupe code)
  LOC-API-03  POST /api/v1/semesters/generate-academy-season — location not found → 404
  LOC-API-04  POST /api/v1/semesters/generate-academy-season — non-ACADEMY type → 400
  LOC-API-05  POST /api/v1/semesters/ — PARTNER + ACADEMY specialization_type + location_id → 400
  LOC-API-06  POST /api/v1/semesters/ — CENTER + ACADEMY specialization_type + location_id → 201
  LOC-API-07  POST /api/v1/semesters/ — PARTNER + Mini Season specialization_type + location_id → 201
  LOC-API-08  POST /api/v1/semesters/ — ACADEMY + no location_id → 400 (K1 resolved: location required)

Boundary / auth
  LOC-API-09  POST /api/v1/semesters/generate-academy-season — unauthenticated → 401
  LOC-API-10  POST /api/v1/semesters/generate-academy-season — student token → 403

Decision stances encoded in this file
--------------------------------------
  K1 (API permissiveness without location_id):
      RESOLVED 2026-03-16 — LOC-API-08 now expects 400.
      ACADEMY types require location_id in POST /api/v1/semesters/ (K1 closed).

  K3 (session-level differentiation by location type):
      Session generation is NOT tested here — it is location-agnostic by design.
      See docs/architecture/domain-model.md §8.4 for the documented decision.
"""
import uuid
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.location import Location, LocationType
from app.models.campus import Campus
from app.models.semester import Semester, SemesterStatus


# ── Helpers ────────────────────────────────────────────────────────────────────

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_error_message(resp) -> str:
    """Extract a plain-string error message from any error envelope shape.

    The app's custom exception handler produces:
        {"error": {"code": ..., "message": <str or dict>, ...}}
    When the endpoint raises ``HTTPException(detail=some_dict)``, the handler
    places that dict as the "message" value — one extra nesting level.
    """
    body = resp.json()
    error = body.get("error")
    if isinstance(error, dict):
        msg = error.get("message", "")
        # message may itself be a dict when HTTPException.detail was a dict
        if isinstance(msg, dict):
            return msg.get("message", "") or str(msg)
        return str(msg) if msg else str(body)
    # FastAPI default: {"detail": str|dict}
    detail = body.get("detail")
    if isinstance(detail, dict):
        return detail.get("message", "") or str(detail)
    return str(detail) if detail else str(body)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def partner_location(test_db: Session) -> Location:
    loc = Location(
        name=f"LOC-API-Partner-{uuid.uuid4().hex[:6]}",
        city=f"PartnerCity-{uuid.uuid4().hex[:8]}",
        country="Hungary",
        country_code="HU",
        location_type=LocationType.PARTNER,
        is_active=True,
    )
    test_db.add(loc)
    test_db.flush()
    return loc


@pytest.fixture
def center_location(test_db: Session) -> Location:
    loc = Location(
        name=f"LOC-API-Center-{uuid.uuid4().hex[:6]}",
        city=f"CenterCity-{uuid.uuid4().hex[:8]}",
        country="Hungary",
        country_code="HU",
        location_type=LocationType.CENTER,
        is_active=True,
    )
    test_db.add(loc)
    test_db.flush()
    return loc


@pytest.fixture
def center_campus(test_db: Session, center_location: Location) -> Campus:
    campus = Campus(
        location_id=center_location.id,
        name=f"LOC-API-Campus-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    test_db.add(campus)
    test_db.flush()
    return campus


@pytest.fixture
def partner_campus(test_db: Session, partner_location: Location) -> Campus:
    campus = Campus(
        location_id=partner_location.id,
        name=f"LOC-API-PartnerCampus-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    test_db.add(campus)
    test_db.flush()
    return campus


# ── LOC-API-01 to LOC-API-04: generate-academy-season endpoint ─────────────────

class TestAcademySeasonGeneratorLocationRules:
    """
    LOC-API-01 to LOC-API-04

    Validates that POST /api/v1/semesters/generate-academy-season enforces
    the CENTER-only rule for all four ACADEMY specialization types.

    The endpoint requires:
      - specialization_type ∈ {LFA_PLAYER_*_ACADEMY}
      - location_id pointing to a CENTER location
      - campus_id within that location
      - year >= current year
    """

    _CURRENT_YEAR = date.today().year

    def _payload(self, spec_type: str, location_id: int, campus_id: int) -> dict:
        return {
            "specialization_type": spec_type,
            "location_id": location_id,
            "campus_id": campus_id,
            "year": self._CURRENT_YEAR,
        }

    def test_loc_api_01_partner_location_blocks_academy(
        self, client: TestClient, admin_token: str,
        partner_location: Location, partner_campus: Campus,
    ):
        """LOC-API-01: PARTNER location + ACADEMY type → 400."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._payload(
                "LFA_PLAYER_PRE_ACADEMY",
                partner_location.id,
                partner_campus.id,
            ),
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400, (
            f"Expected 400 for PARTNER + ACADEMY, got {resp.status_code}. "
            f"Body: {resp.text[:300]}"
        )
        msg = _get_error_message(resp)
        assert msg, "Expected non-empty error message in response"
        # Message should mention CENTER or location restriction
        assert any(kw in msg for kw in ("CENTER", "PARTNER", "helyszín", "csak")), (
            f"Error message does not describe location restriction: {msg!r}"
        )

    @pytest.mark.parametrize("spec_type", [
        "LFA_PLAYER_PRE_ACADEMY",
        "LFA_PLAYER_YOUTH_ACADEMY",
        "LFA_PLAYER_AMATEUR_ACADEMY",
        "LFA_PLAYER_PRO_ACADEMY",
    ])
    def test_loc_api_01_all_academy_types_blocked_at_partner(
        self, client: TestClient, admin_token: str,
        partner_location: Location, partner_campus: Campus,
        spec_type: str,
    ):
        """LOC-API-01 (parametrised): every ACADEMY type is blocked at PARTNER."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._payload(spec_type, partner_location.id, partner_campus.id),
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400, (
            f"Expected 400 for {spec_type} at PARTNER, got {resp.status_code}"
        )

    def test_loc_api_02_center_location_allows_academy(
        self, client: TestClient, admin_token: str,
        center_location: Location, center_campus: Campus,
    ):
        """LOC-API-02: CENTER location + ACADEMY type → success (201) or duplicate-code (409)."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._payload(
                "LFA_PLAYER_YOUTH_ACADEMY",
                center_location.id,
                center_campus.id,
            ),
            headers=_auth(admin_token),
        )
        # 201 = created; 409 = duplicate code (semester for this year/type already exists)
        # Both indicate the location check passed
        assert resp.status_code in (200, 201, 409), (
            f"Expected 201 (success) or 409 (duplicate code) for CENTER + ACADEMY, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )

    def test_loc_api_03_location_not_found(
        self, client: TestClient, admin_token: str,
        center_campus: Campus,
    ):
        """LOC-API-03: Non-existent location_id → 404."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._payload("LFA_PLAYER_PRE_ACADEMY", 999_999, center_campus.id),
            headers=_auth(admin_token),
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown location_id, got {resp.status_code}"
        )

    def test_loc_api_04_non_academy_type_rejected(
        self, client: TestClient, admin_token: str,
        center_location: Location, center_campus: Campus,
    ):
        """LOC-API-04: Mini Season type sent to academy generator → 400 (type whitelist)."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._payload(
                "LFA_PLAYER_PRE",  # mini season — not an academy type
                center_location.id,
                center_campus.id,
            ),
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400, (
            f"Expected 400 for non-ACADEMY type at academy endpoint, got {resp.status_code}"
        )


# ── LOC-API-05 to LOC-API-08: generic semester create endpoint ─────────────────

class TestGenericSemesterCreateLocationRules:
    """
    LOC-API-05 to LOC-API-08

    Validates that POST /api/v1/semesters/ enforces (or explicitly does not enforce)
    the CENTER vs PARTNER rule depending on whether location_id is provided.

    NOTE: The SemesterCreate schema does NOT include location_id — the endpoint
    reads it from extra/custom handling in _semesters_main.py.  The field is
    passed as part of the JSON body but is not declared in the Pydantic model.
    The endpoint handler extracts it separately if present.
    """

    def _base_payload(self, code_prefix: str, spec_type: str) -> dict:
        code = f"{code_prefix}-{uuid.uuid4().hex[:6].upper()}"
        return {
            "code": code,
            "name": f"LOC-API {code}",
            "start_date": (date.today() + timedelta(days=1)).isoformat(),
            "end_date": (date.today() + timedelta(days=90)).isoformat(),
            "enrollment_cost": 500,
            "specialization_type": spec_type,
        }

    def test_loc_api_05_partner_plus_academy_type_blocked(
        self, client: TestClient, admin_token: str,
        partner_location: Location,
    ):
        """LOC-API-05: PARTNER location_id + ACADEMY specialization_type → 400."""
        payload = self._base_payload("LOC05", "LFA_PLAYER_PRE_ACADEMY")
        payload["location_id"] = partner_location.id
        resp = client.post(
            "/api/v1/semesters/",
            json=payload,
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400, (
            f"Expected 400 for PARTNER + ACADEMY via /semesters/, got {resp.status_code}. "
            f"Body: {resp.text[:300]}"
        )
        msg = _get_error_message(resp)
        assert msg, "Expected a non-empty error message"

    def test_loc_api_06_center_plus_academy_type_allowed(
        self, client: TestClient, admin_token: str,
        center_location: Location,
    ):
        """LOC-API-06: CENTER location_id + ACADEMY specialization_type → 201."""
        payload = self._base_payload("LOC06", "LFA_PLAYER_AMATEUR_ACADEMY")
        payload["location_id"] = center_location.id
        resp = client.post(
            "/api/v1/semesters/",
            json=payload,
            headers=_auth(admin_token),
        )
        assert resp.status_code in (200, 201), (
            f"Expected 201 for CENTER + ACADEMY, got {resp.status_code}. "
            f"Body: {resp.text[:300]}"
        )

    def test_loc_api_07_partner_plus_mini_season_allowed(
        self, client: TestClient, admin_token: str,
        partner_location: Location,
    ):
        """LOC-API-07: PARTNER location_id + Mini Season type → 201 (PARTNER allows Mini Season)."""
        payload = self._base_payload("LOC07", "LFA_PLAYER_PRE")
        payload["location_id"] = partner_location.id
        resp = client.post(
            "/api/v1/semesters/",
            json=payload,
            headers=_auth(admin_token),
        )
        assert resp.status_code in (200, 201), (
            f"Expected 201 for PARTNER + Mini Season, got {resp.status_code}. "
            f"Body: {resp.text[:300]}"
        )

    def test_loc_api_08_academy_type_without_location_id_blocked(
        self, client: TestClient, admin_token: str,
    ):
        """
        LOC-API-08: ACADEMY specialization_type with NO location_id → 400.

        Decision K1 is RESOLVED as "require location_id":
        The REST API now enforces that Academy Season types must declare a location_id
        so the CENTER / PARTNER rule can be evaluated.  Without a location the guard
        cannot determine whether the request is legal.

        See: docs/architecture/domain-model.md §8.5 (K1 decision)
        """
        payload = self._base_payload("LOC08", "LFA_PLAYER_PRO_ACADEMY")
        # Intentionally omit location_id — must be rejected
        resp = client.post(
            "/api/v1/semesters/",
            json=payload,
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400, (
            f"LOC-API-08 (K1 resolved): expected 400 for ACADEMY type without location_id, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )
        msg = _get_error_message(resp)
        assert msg, "Expected non-empty error message"
        assert any(kw in msg.lower() for kw in ("location", "helyszín", "academy")), (
            f"Error message should mention location/academy requirement: {msg!r}"
        )


# ── LOC-API-09 to LOC-API-10: auth boundary tests ──────────────────────────────

class TestAcademySeasonGeneratorAuthBoundary:
    """
    LOC-API-09 to LOC-API-10

    Auth boundary tests run in parallel with location validation tests.
    These guard against auth regressions introduced when location validation
    middleware or dependency overrides are changed.
    """

    def _minimal_payload(self, location_id: int, campus_id: int) -> dict:
        return {
            "specialization_type": "LFA_PLAYER_PRE_ACADEMY",
            "location_id": location_id,
            "campus_id": campus_id,
            "year": date.today().year,
        }

    def test_loc_api_09_unauthenticated_returns_401(
        self, client: TestClient, center_location: Location, center_campus: Campus,
    ):
        """LOC-API-09: No Bearer token → 401 Unauthorized."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._minimal_payload(center_location.id, center_campus.id),
            # No Authorization header
        )
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated request, got {resp.status_code}"
        )

    def test_loc_api_10_student_token_returns_403(
        self, client: TestClient, student_token: str,
        center_location: Location, center_campus: Campus,
    ):
        """LOC-API-10: Student Bearer token → 403 Forbidden (admin-only endpoint)."""
        resp = client.post(
            "/api/v1/semesters/generate-academy-season",
            json=self._minimal_payload(center_location.id, center_campus.id),
            headers=_auth(student_token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for student token on admin endpoint, got {resp.status_code}"
        )


# ── LOC-API-11 to LOC-API-14: K1 + K2 enforcement tests ───────────────────────

class TestK1LocationRequiredForAcademy:
    """
    LOC-API-11 to LOC-API-12

    K1 RESOLVED 2026-03-16: POST /api/v1/semesters/ must reject ACADEMY types
    when location_id is absent.  Any location_id (even a PARTNER location) triggers
    the location-validation path; the K1 guard fires BEFORE that check when
    location_id is completely omitted.

    LOC-API-11  ACADEMY type + no location_id → 400 (K1 guard)
    LOC-API-12  Non-ACADEMY type + no location_id → 201 (K1 guard does not fire)
    """

    def _payload(self, code_prefix: str, spec_type: str) -> dict:
        code = f"{code_prefix}-{uuid.uuid4().hex[:6].upper()}"
        return {
            "code": code,
            "name": f"LOC-API {code}",
            "start_date": (date.today() + timedelta(days=1)).isoformat(),
            "end_date": (date.today() + timedelta(days=90)).isoformat(),
            "enrollment_cost": 500,
            "specialization_type": spec_type,
            # Intentionally NO location_id
        }

    @pytest.mark.parametrize("spec_type", [
        "LFA_PLAYER_PRE_ACADEMY",
        "LFA_PLAYER_YOUTH_ACADEMY",
        "LFA_PLAYER_AMATEUR_ACADEMY",
        "LFA_PLAYER_PRO_ACADEMY",
    ])
    def test_loc_api_11_all_academy_types_blocked_without_location(
        self, client: TestClient, admin_token: str, spec_type: str,
    ):
        """LOC-API-11: Every ACADEMY type without location_id → 400 (K1 guard)."""
        resp = client.post(
            "/api/v1/semesters/",
            json=self._payload("LOC11", spec_type),
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400, (
            f"LOC-API-11 ({spec_type}): expected 400 when location_id absent, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )
        msg = _get_error_message(resp)
        assert any(kw in msg.lower() for kw in ("location", "helyszín", "academy")), (
            f"Error message should reference location/academy requirement: {msg!r}"
        )

    def test_loc_api_12_mini_season_without_location_allowed(
        self, client: TestClient, admin_token: str,
    ):
        """LOC-API-12: Non-ACADEMY type without location_id → 201 (K1 guard skips)."""
        resp = client.post(
            "/api/v1/semesters/",
            json=self._payload("LOC12", "LFA_PLAYER_PRE"),
            headers=_auth(admin_token),
        )
        assert resp.status_code in (200, 201), (
            f"LOC-API-12: expected 201 for Mini Season without location_id, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )


class TestK2LocationTypeDowngradeBlocked:
    """
    LOC-API-13 to LOC-API-15

    K2 IMPLEMENTED 2026-03-16: PUT /api/v1/locations/{id} blocks CENTER→PARTNER
    type change when the location hosts an ACTIVE Academy Season.

    LOC-API-13  CENTER location + active Academy semester → PUT to PARTNER → 409
    LOC-API-14  CENTER location + completed/draft Academy semester → PUT to PARTNER → 200
    LOC-API-15  PARTNER→CENTER upgrade always allowed → 200
    """

    def _make_semester(
        self,
        test_db: Session,
        location: Location,
        spec_type: str,
        sem_status: SemesterStatus,
    ) -> Semester:
        code = f"K2-{spec_type[:8]}-{uuid.uuid4().hex[:6].upper()}"
        sem = Semester(
            code=code,
            name=f"K2 test {code}",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status=sem_status,
            specialization_type=spec_type,
            location_id=location.id,
            enrollment_cost=500,
        )
        test_db.add(sem)
        test_db.flush()
        return sem

    def test_loc_api_13_center_to_partner_blocked_by_active_academy(
        self,
        client: TestClient,
        admin_token: str,
        center_location: Location,
        test_db: Session,
    ):
        """LOC-API-13: CENTER→PARTNER rejected when READY_FOR_ENROLLMENT Academy semester exists."""
        self._make_semester(
            test_db, center_location,
            "LFA_PLAYER_YOUTH_ACADEMY",
            SemesterStatus.READY_FOR_ENROLLMENT,
        )
        resp = client.put(
            f"/api/v1/admin/locations/{center_location.id}",
            json={
                "name": center_location.name,
                "city": center_location.city,
                "country": center_location.country,
                "location_type": "PARTNER",
            },
            headers=_auth(admin_token),
        )
        assert resp.status_code == 409, (
            f"LOC-API-13: expected 409 for CENTER→PARTNER with active Academy, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )
        msg = _get_error_message(resp)
        assert msg, "Expected non-empty 409 error message"
        # Location type must not have changed
        test_db.refresh(center_location)
        assert center_location.location_type == LocationType.CENTER, (
            "Location type was changed despite active Academy semester conflict"
        )

    def test_loc_api_14_center_to_partner_allowed_when_no_active_academy(
        self,
        client: TestClient,
        admin_token: str,
        center_location: Location,
        test_db: Session,
    ):
        """LOC-API-14: CENTER→PARTNER allowed when Academy semesters are only DRAFT."""
        self._make_semester(
            test_db, center_location,
            "LFA_PLAYER_PRE_ACADEMY",
            SemesterStatus.DRAFT,  # not active → no conflict
        )
        resp = client.put(
            f"/api/v1/admin/locations/{center_location.id}",
            json={
                "name": center_location.name,
                "city": center_location.city,
                "country": center_location.country,
                "location_type": "PARTNER",
            },
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, (
            f"LOC-API-14: expected 200 for CENTER→PARTNER with only DRAFT Academy, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )

    def test_loc_api_15_partner_to_center_always_allowed(
        self,
        client: TestClient,
        admin_token: str,
        partner_location: Location,
    ):
        """LOC-API-15: PARTNER→CENTER upgrade is unconditionally allowed."""
        resp = client.put(
            f"/api/v1/admin/locations/{partner_location.id}",
            json={
                "name": partner_location.name,
                "city": partner_location.city,
                "country": partner_location.country,
                "location_type": "CENTER",
            },
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, (
            f"LOC-API-15: expected 200 for PARTNER→CENTER upgrade, "
            f"got {resp.status_code}. Body: {resp.text[:300]}"
        )
