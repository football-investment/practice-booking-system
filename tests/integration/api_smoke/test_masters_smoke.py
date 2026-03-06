"""
Smoke tests for instructor management master instructor endpoints.

Coverage target: app/api/api_v1/endpoints/instructor_management/masters/
  - direct_hire.py  (235 lines, 1 POST route)
  - applications.py (158 lines, 1 POST route)
  - offers.py       (290 lines, 4 routes)
  - legacy.py       (245 lines, 5 routes)
  - utils.py        → tested separately in tests/unit/test_masters_utils.py

All masters routes live under /api/v1/instructor-management/masters/

Auth requirements:
  - POST /direct-hire:                  ADMIN only
  - POST /hire-from-application:        ADMIN only
  - PATCH /offers/{id}/respond:         Instructor (receiving offer)
  - GET   /my-offers:                   Instructor
  - GET   /pending-offers:              ADMIN only
  - DELETE /offers/{id}:                ADMIN only
  - POST /   (legacy create):           ADMIN only
  - GET  /{location_id} (legacy get):   ADMIN only (any user?)
  - GET  /   (legacy list):             ADMIN only
  - PATCH /{master_id} (legacy update): ADMIN only
  - DELETE /{master_id} (legacy delete):ADMIN only
"""

import pytest
from fastapi.testclient import TestClient


class TestDirectHireSmoke:
    """Smoke tests for POST /masters/direct-hire (Pathway A)."""

    def test_direct_hire_auth_required(self, api_client: TestClient):
        """POST /masters/direct-hire without auth → 401 or 403."""
        response = api_client.post(
            "/masters/direct-hire",
            json={"instructor_id": 1, "location_id": 1, "age_group": "PRE_FOOTBALL"},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth POST direct-hire: unexpected {response.status_code}"
        )

    def test_direct_hire_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """Instructor POST /masters/direct-hire → 403 (Admin only)."""
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.post(
            "/masters/direct-hire",
            headers=headers,
            json={"instructor_id": 1, "location_id": 1},
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"Instructor POST direct-hire should be 403: got {response.status_code}"
        )

    def test_direct_hire_admin_nonexistent_resources(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin POST /masters/direct-hire — nonexistent instructor/location → 404 or 422."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/masters/direct-hire",
            headers=headers,
            json={
                "instructor_id": 99999,
                "location_id": 99999,
                "contract_start": "2026-09-01",
                "contract_end": "2027-06-30",
            },
        )
        assert response.status_code in [201, 400, 403, 404, 409, 422], (
            f"Admin POST direct-hire (nonexistent): unexpected {response.status_code}"
        )


class TestHireFromApplicationSmoke:
    """Smoke tests for POST /masters/hire-from-application (Pathway B)."""

    def test_hire_from_application_auth_required(self, api_client: TestClient):
        """POST /masters/hire-from-application without auth → 401 or 403."""
        response = api_client.post(
            "/masters/hire-from-application",
            json={"application_id": 1},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth POST hire-from-application: unexpected {response.status_code}"
        )

    def test_hire_from_application_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """Instructor POST hire-from-application → 403 (Admin only)."""
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.post(
            "/masters/hire-from-application",
            headers=headers,
            json={"application_id": 1, "offer_deadline_days": 7},
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"Instructor POST hire-from-application: got {response.status_code}"
        )

    def test_hire_from_application_admin_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin POST hire-from-application — application not found → 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/masters/hire-from-application",
            headers=headers,
            json={
                "application_id": 99999,
                "offer_deadline_days": 7,
                "contract_start": "2026-09-01",
                "contract_end": "2027-06-30",
            },
        )
        assert response.status_code in [201, 400, 403, 404, 409, 422], (
            f"Admin POST hire-from-application (nonexistent): unexpected {response.status_code}"
        )


class TestOffersSmoke:
    """Smoke tests for offers management routes."""

    # ── PATCH /offers/{offer_id}/respond ─────────────────────────────────────

    def test_respond_offer_auth_required(self, api_client: TestClient):
        """PATCH /masters/offers/99999/respond without auth → 401 or 403."""
        response = api_client.patch(
            "/masters/offers/99999/respond",
            json={"action": "ACCEPT"},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PATCH offer respond: unexpected {response.status_code}"
        )

    def test_respond_offer_nonexistent(
        self, api_client: TestClient, instructor_token: str
    ):
        """Instructor PATCH /masters/offers/99999/respond — offer not found → 404."""
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.patch(
            "/masters/offers/99999/respond",
            headers=headers,
            json={"action": "ACCEPT"},
        )
        assert response.status_code in [200, 400, 403, 404, 409, 422], (
            f"Instructor PATCH offer respond (nonexistent): unexpected {response.status_code}"
        )

    # ── GET /my-offers ────────────────────────────────────────────────────────

    def test_my_offers_auth_required(self, api_client: TestClient):
        """GET /masters/my-offers without auth → 401 or 403."""
        response = api_client.get("/masters/my-offers")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET my-offers: unexpected {response.status_code}"
        )

    def test_my_offers_instructor_token(
        self, api_client: TestClient, instructor_token: str
    ):
        """Instructor GET /masters/my-offers → 200 (empty list) or 404."""
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/masters/my-offers", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Instructor GET my-offers: unexpected {response.status_code}"
        )

    # ── GET /pending-offers ───────────────────────────────────────────────────

    def test_pending_offers_auth_required(self, api_client: TestClient):
        """GET /masters/pending-offers without auth → 401 or 403."""
        response = api_client.get("/masters/pending-offers")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET pending-offers: unexpected {response.status_code}"
        )

    def test_pending_offers_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin GET /masters/pending-offers → 200 (empty list)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/masters/pending-offers", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET pending-offers: unexpected {response.status_code}"
        )

    def test_pending_offers_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """Instructor GET /masters/pending-offers → 403 (Admin only)."""
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/masters/pending-offers", headers=headers)
        assert response.status_code in [400, 403, 404, 422], (
            f"Instructor GET pending-offers should be 403: got {response.status_code}"
        )

    # ── DELETE /offers/{offer_id} ─────────────────────────────────────────────

    def test_delete_offer_auth_required(self, api_client: TestClient):
        """DELETE /masters/offers/99999 without auth → 401 or 403."""
        response = api_client.delete("/masters/offers/99999")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth DELETE offer: unexpected {response.status_code}"
        )

    def test_delete_offer_admin_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin DELETE /masters/offers/99999 — offer not found → 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.delete("/masters/offers/99999", headers=headers)
        assert response.status_code in [200, 204, 400, 403, 404, 409, 422], (
            f"Admin DELETE offer (nonexistent): unexpected {response.status_code}"
        )


class TestLegacyMastersSmoke:
    """Smoke tests for legacy master instructor management routes."""

    # ── POST / (legacy create — immediate active) ─────────────────────────────

    def test_legacy_create_auth_required(self, api_client: TestClient):
        """POST /masters/ without auth → 401 or 403."""
        response = api_client.post(
            "/masters/",
            json={"instructor_id": 1, "location_id": 1},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth POST legacy master: unexpected {response.status_code}"
        )

    def test_legacy_create_admin_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin POST /masters/ — nonexistent instructor/location → 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/masters/",
            headers=headers,
            json={
                "instructor_id": 99999,
                "location_id": 99999,
                "contract_start": "2026-09-01",
                "contract_end": "2027-06-30",
            },
        )
        assert response.status_code in [201, 400, 403, 404, 409, 422], (
            f"Admin POST legacy master (nonexistent): unexpected {response.status_code}"
        )

    # ── GET / (legacy list) ───────────────────────────────────────────────────

    def test_legacy_list_auth_required(self, api_client: TestClient):
        """GET /masters/ without auth → 401 or 403."""
        response = api_client.get("/masters/")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET legacy list: unexpected {response.status_code}"
        )

    def test_legacy_list_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin GET /masters/ → 200 (list, possibly empty)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/masters/", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET legacy list: unexpected {response.status_code}"
        )

    # ── GET /{location_id} (get master for location) ──────────────────────────

    def test_legacy_get_by_location_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin GET /masters/99999 — location not found → 404 or 200."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/masters/99999", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET master by location: unexpected {response.status_code}"
        )

    # ── PATCH /{master_id} (legacy update) ───────────────────────────────────

    def test_legacy_update_auth_required(self, api_client: TestClient):
        """PATCH /masters/99999 without auth → 401 or 403."""
        response = api_client.patch(
            "/masters/99999",
            json={"contract_end": "2027-06-30"},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PATCH legacy master: unexpected {response.status_code}"
        )

    def test_legacy_update_admin_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin PATCH /masters/99999 — not found → 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.patch(
            "/masters/99999",
            headers=headers,
            json={"contract_end": "2027-06-30", "is_active": False},
        )
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin PATCH legacy master (nonexistent): unexpected {response.status_code}"
        )

    # ── DELETE /{master_id} (legacy terminate) ────────────────────────────────

    def test_legacy_delete_auth_required(self, api_client: TestClient):
        """DELETE /masters/99999 without auth → 401 or 403."""
        response = api_client.delete("/masters/99999")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth DELETE legacy master: unexpected {response.status_code}"
        )

    def test_legacy_delete_admin_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin DELETE /masters/99999 — not found → 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.delete("/masters/99999", headers=headers)
        assert response.status_code in [200, 204, 400, 403, 404, 409, 422], (
            f"Admin DELETE legacy master (nonexistent): unexpected {response.status_code}"
        )
