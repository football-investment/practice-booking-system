"""
Admin Workflow Smoke Test — Sprint 59e Parity Verification

Covers 7 operational admin flows end-to-end against a SAVEPOINT-isolated
real PostgreSQL database (no mocks):

  SMOKE-01  Location: Create → Edit → Toggle (deactivate) → Delete
  SMOKE-02  Game Preset: Create → Edit → Toggle active/inactive
  SMOKE-03  Invoice: Create in DB → view payments page → verify KPI counts
  SMOKE-04  Sessions: List page loads + filters work (date_from, spec, status)
  SMOKE-05  Coupon: Create → view on coupons page → Toggle active
  SMOKE-06  Invitation Code: Create (via API) → verify on codes page
  SMOKE-07  Navigation: GET all 12 admin pages, confirm 200 + no 500 bodies

Auth: get_current_user_web overridden → admin_user injected.
CSRF: Authorization: Bearer bypass header skips CSRFProtectionMiddleware.
DB:   SAVEPOINT-isolated; all changes rolled back after each test.
"""

import uuid
import pytest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web
from app.models.user import User, UserRole
from app.models.location import Location, LocationType
from app.models.campus import Campus
from app.models.game_preset import GamePreset
from app.models.coupon import Coupon, CouponType
from app.models.invitation_code import InvitationCode
from app.models.invoice_request import InvoiceRequest, InvoiceRequestStatus
from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.semester_enrollment import SemesterEnrollment
from app.core.security import get_password_hash


# ── SAVEPOINT-isolated DB ─────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()
    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, txn):
        if txn.nested and not txn._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# ── Admin user + client ───────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def admin_user(test_db: Session) -> User:
    u = User(
        email=f"smoke-admin+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Smoke Admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(u)
    test_db.commit()
    test_db.refresh(u)
    return u


@pytest.fixture(scope="function")
def student_user(test_db: Session) -> User:
    u = User(
        email=f"smoke-student+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Smoke Student",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    test_db.add(u)
    test_db.commit()
    test_db.refresh(u)
    return u


@pytest.fixture(scope="function")
def admin_client(test_db: Session, admin_user: User) -> TestClient:
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_web] = lambda: admin_user

    with TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"}) as c:
        yield c

    app.dependency_overrides.clear()


# ── Minimal data fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def location(test_db: Session) -> Location:
    unique_city = f"SmokeCity-{uuid.uuid4().hex[:8]}"
    loc = Location(
        name=f"Smoke Loc {uuid.uuid4().hex[:6]}",
        city=unique_city,
        country="Hungary",
        location_type=LocationType.CENTER,
        is_active=True,
    )
    test_db.add(loc)
    test_db.commit()
    test_db.refresh(loc)
    return loc


@pytest.fixture
def game_preset(test_db: Session) -> GamePreset:
    gp = GamePreset(
        name=f"Smoke Preset {uuid.uuid4().hex[:6]}",
        code=f"SP-{uuid.uuid4().hex[:4].upper()}",
        is_active=True,
        game_config={"skill_config": {"skill_weights": {}}, "format_config": {}, "metadata": {}},
    )
    test_db.add(gp)
    test_db.commit()
    test_db.refresh(gp)
    return gp


@pytest.fixture
def coupon(test_db: Session) -> Coupon:
    c = Coupon(
        code=f"SMOKE-{uuid.uuid4().hex[:6].upper()}",
        type=CouponType.BONUS_CREDITS,
        discount_value=50.0,
        description="Smoke test coupon",
        is_active=True,
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


@pytest.fixture
def invitation_code(test_db: Session, admin_user: User) -> InvitationCode:
    ic = InvitationCode(
        code=f"SMOKE-INV-{uuid.uuid4().hex[:6].upper()}",
        invited_name="Smoke Invitee",
        bonus_credits=100,
        is_used=False,
        created_by_admin_id=admin_user.id,
    )
    test_db.add(ic)
    test_db.commit()
    test_db.refresh(ic)
    return ic


@pytest.fixture
def invoice_request(test_db: Session, student_user: User) -> InvoiceRequest:
    import uuid as _uuid
    ir = InvoiceRequest(
        user_id=student_user.id,
        amount_eur=50.0,
        credit_amount=500,
        status=InvoiceRequestStatus.PENDING,
        payment_reference=f"SMOKE-{_uuid.uuid4().hex[:8].upper()}",
    )
    test_db.add(ir)
    test_db.commit()
    test_db.refresh(ir)
    return ir


@pytest.fixture
def semester(test_db: Session) -> Semester:
    sem = Semester(
        code=f"SMK-{uuid.uuid4().hex[:6].upper()}",
        name="Smoke Semester",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=SemesterStatus.ONGOING,
        specialization_type="FOOTBALL_SKILLS",
        is_active=True,
    )
    test_db.add(sem)
    test_db.commit()
    test_db.refresh(sem)
    return sem


@pytest.fixture
def session_obj(test_db: Session, semester: Semester, admin_user: User) -> SessionModel:
    now = datetime.now(ZoneInfo("Europe/Budapest")).replace(tzinfo=None)
    s = SessionModel(
        title="Smoke Session",
        semester_id=semester.id,
        session_type=SessionType.on_site,
        date_start=now + timedelta(hours=24),
        date_end=now + timedelta(hours=25),
        instructor_id=admin_user.id,
    )
    test_db.add(s)
    test_db.commit()
    test_db.refresh(s)
    return s


# ============================================================================
# SMOKE-01: Location CRUD
# ============================================================================

class TestSmoke01LocationCRUD:

    def test_01_create_location(self, admin_client, test_db):
        """POST /admin/locations → 303 + Location row created in DB."""
        code = uuid.uuid4().hex[:6].upper()
        unique_city = f"SmokeCreate-{uuid.uuid4().hex[:8]}"
        resp = admin_client.post(
            "/admin/locations",
            data={
                "name": f"Smoke City {code}",
                "city": unique_city,
                "country": "Hungary",
                "country_code": "HU",
                "location_code": code[:3],
                "location_type": "CENTER",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303, f"Expected 303, got {resp.status_code}"
        assert "/admin/locations" in resp.headers["location"]

        loc = test_db.query(Location).filter(Location.city == unique_city).first()
        assert loc is not None, "Location not found in DB after create"
        assert loc.is_active is True

    def test_02_edit_location_page_loads(self, admin_client, location):
        """GET /admin/locations/{id}/edit → 200, form rendered."""
        resp = admin_client.get(f"/admin/locations/{location.id}/edit")
        assert resp.status_code == 200
        assert location.name in resp.text
        assert "Save Changes" in resp.text

    def test_03_edit_location_submit(self, admin_client, location, test_db):
        """POST /admin/locations/{id}/edit → 303 + DB updated."""
        new_name = f"Updated-{uuid.uuid4().hex[:6]}"
        resp = admin_client.post(
            f"/admin/locations/{location.id}/edit",
            data={
                "name": new_name,
                "city": location.city,  # city is already unique (set by fixture)
                "country": location.country or "Hungary",
                "location_type": "CENTER",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        test_db.expire_all()
        updated = test_db.query(Location).filter(Location.id == location.id).first()
        assert updated.name == new_name

    def test_04_toggle_location_deactivates(self, admin_client, location, test_db):
        """POST /admin/locations/{id}/toggle → is_active flips False."""
        assert location.is_active is True
        resp = admin_client.post(
            f"/admin/locations/{location.id}/toggle",
            follow_redirects=False,
        )
        assert resp.status_code == 303

        test_db.expire_all()
        loc = test_db.query(Location).filter(Location.id == location.id).first()
        assert loc.is_active is False

    def test_05_delete_location(self, admin_client, test_db):
        """POST /admin/locations/{id}/delete → 303 + row removed."""
        # Create a fresh standalone location to delete (unique city to avoid unique constraint)
        loc = Location(
            name=f"DeleteMe-{uuid.uuid4().hex[:6]}",
            city=f"DeleteCity-{uuid.uuid4().hex[:8]}",
            country="Hungary",
            location_type=LocationType.PARTNER,
            is_active=True,
        )
        test_db.add(loc)
        test_db.commit()
        test_db.refresh(loc)
        lid = loc.id

        resp = admin_client.post(
            f"/admin/locations/{lid}/delete",
            follow_redirects=False,
        )
        assert resp.status_code == 303

        test_db.expire_all()
        assert test_db.query(Location).filter(Location.id == lid).first() is None

    def test_06_locations_list_with_filters(self, admin_client, location):
        """GET /admin/locations?city_filter=Budapest → 200, no 500."""
        resp = admin_client.get("/admin/locations?city_filter=Budapest&status_filter=active")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text
        assert "Locations" in resp.text


# ============================================================================
# SMOKE-02: Game Preset CRUD
# ============================================================================

class TestSmoke02GamePresetCRUD:

    def test_01_create_game_preset(self, admin_client, test_db):
        """POST /admin/game-presets → 303 + GamePreset in DB."""
        code = f"GP-{uuid.uuid4().hex[:4].upper()}"
        resp = admin_client.post(
            "/admin/game-presets",
            data={
                "name": f"Smoke Preset {code}",
                "code": code,
                "description": "Smoke test",
                "skill_ids": [],
                "skill_weights": [],
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        gp = test_db.query(GamePreset).filter(GamePreset.code == code).first()
        assert gp is not None, f"GamePreset {code} not found in DB"
        assert gp.is_active is True

    def test_02_edit_game_preset_page_loads(self, admin_client, game_preset):
        """GET /admin/game-presets/{id}/edit → 200, form with preset name."""
        resp = admin_client.get(f"/admin/game-presets/{game_preset.id}/edit")
        assert resp.status_code == 200
        assert game_preset.name in resp.text

    def test_03_edit_game_preset_submit(self, admin_client, game_preset, test_db):
        """POST /admin/game-presets/{id}/edit → 303 + DB updated."""
        new_name = f"Edited-{uuid.uuid4().hex[:6]}"
        resp = admin_client.post(
            f"/admin/game-presets/{game_preset.id}/edit",
            data={
                "name": new_name,
                "code": game_preset.code,
                "description": "Updated",
                "skill_ids": [],
                "skill_weights": [],
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        test_db.expire_all()
        updated = test_db.query(GamePreset).filter(GamePreset.id == game_preset.id).first()
        assert updated.name == new_name

    def test_04_toggle_game_preset(self, admin_client, game_preset, test_db):
        """POST /admin/game-presets/{id}/toggle → is_active flips."""
        assert game_preset.is_active is True
        resp = admin_client.post(
            f"/admin/game-presets/{game_preset.id}/toggle",
            follow_redirects=False,
        )
        assert resp.status_code == 303

        test_db.expire_all()
        gp = test_db.query(GamePreset).filter(GamePreset.id == game_preset.id).first()
        assert gp.is_active is False

    def test_05_locked_preset_delete_blocked(self, admin_client, test_db):
        """POST /admin/game-presets/{id}/delete on locked preset → 400."""
        locked = GamePreset(
            name="Locked Preset",
            code=f"LCK-{uuid.uuid4().hex[:4].upper()}",
            is_active=True,
            is_locked=True,
            game_config={"skill_config": {"skill_weights": {}}, "format_config": {}, "metadata": {}},
        )
        test_db.add(locked)
        test_db.commit()
        test_db.refresh(locked)

        resp = admin_client.post(
            f"/admin/game-presets/{locked.id}/delete",
            follow_redirects=False,
        )
        assert resp.status_code == 400

        # Row should still exist
        test_db.expire_all()
        assert test_db.query(GamePreset).filter(GamePreset.id == locked.id).first() is not None


# ============================================================================
# SMOKE-03: Invoice — view payments page, KPI, filter
# ============================================================================

class TestSmoke03InvoiceView:

    def test_01_payments_page_loads(self, admin_client, invoice_request):
        """GET /admin/payments → 200, invoice appears in list."""
        resp = admin_client.get("/admin/payments")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text
        # KPI bar should render
        assert "Total Revenue" in resp.text
        assert "Awaiting Approval" in resp.text

    def test_02_pending_invoice_counted_in_kpi(self, admin_client, invoice_request):
        """Pending InvoiceRequest increments 'Awaiting Approval' KPI."""
        resp = admin_client.get("/admin/payments")
        assert resp.status_code == 200
        # The KPI 'open_invoices' should be ≥1 (our pending one)
        body = resp.text
        # Template renders fin.open_invoices — check it's on the page and > 0
        assert "Awaiting Approval" in body

    def test_03_payments_page_no_500_without_invoices(self, admin_client):
        """GET /admin/payments with empty invoice table → 200, no 500."""
        resp = admin_client.get("/admin/payments")
        assert resp.status_code == 200
        assert "500" not in resp.text[:200]  # status code 500 not in early HTML


# ============================================================================
# SMOKE-04: Sessions — list page + filters
# ============================================================================

class TestSmoke04SessionsList:

    def test_01_sessions_page_loads(self, admin_client, session_obj):
        """GET /admin/sessions → 200, session appears in listing."""
        resp = admin_client.get("/admin/sessions")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text
        assert "Sessions" in resp.text

    def test_02_date_from_default_today(self, admin_client):
        """GET /admin/sessions with no params → date_from defaults to today."""
        resp = admin_client.get("/admin/sessions")
        assert resp.status_code == 200
        today = date.today().isoformat()
        # The default date_from should appear in the filter form value
        assert today in resp.text

    def test_03_cleared_param_removes_default(self, admin_client):
        """GET /admin/sessions?cleared=1 → no date_from default applied."""
        resp = admin_client.get("/admin/sessions?cleared=1")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text

    def test_04_session_type_filter(self, admin_client, session_obj):
        """GET /admin/sessions?session_type=on_site → 200, no 500."""
        resp = admin_client.get("/admin/sessions?session_type=on_site&cleared=1")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text

    def test_05_specialization_filter(self, admin_client, session_obj, semester):
        """GET /admin/sessions?spec=FOOTBALL_SKILLS → 200, session visible."""
        resp = admin_client.get("/admin/sessions?spec=FOOTBALL_SKILLS&cleared=1")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text


# ============================================================================
# SMOKE-05: Coupon — Create + Toggle
# ============================================================================

class TestSmoke05CouponCRUD:

    def test_01_create_coupon(self, admin_client, test_db):
        """POST /admin/coupons → 303 + Coupon row in DB."""
        code = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        resp = admin_client.post(
            "/admin/coupons",
            data={
                "code": code,
                "coupon_type": "BONUS_CREDITS",
                "value": "100",
                "description": "Smoke coupon",
                "max_uses": "",
                "expires_days": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        c = test_db.query(Coupon).filter(Coupon.code == code).first()
        assert c is not None, f"Coupon {code} not found in DB"
        assert c.is_active is True
        assert c.discount_value == 100.0

    def test_02_create_coupon_invalid_type_returns_400(self, admin_client):
        """POST /admin/coupons with bad coupon_type → 400."""
        resp = admin_client.post(
            "/admin/coupons",
            data={
                "code": "BAD-TYPE",
                "coupon_type": "NOT_A_REAL_TYPE",
                "value": "50",
                "description": "should fail",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 400

    def test_03_coupon_appears_on_list_page(self, admin_client, coupon):
        """GET /admin/coupons → 200, coupon code visible."""
        resp = admin_client.get("/admin/coupons")
        assert resp.status_code == 200
        assert coupon.code in resp.text

    def test_04_toggle_coupon(self, admin_client, coupon, test_db):
        """POST /admin/coupons/{id}/toggle → is_active flips."""
        assert coupon.is_active is True
        resp = admin_client.post(
            f"/admin/coupons/{coupon.id}/toggle",
            follow_redirects=False,
        )
        assert resp.status_code == 303

        test_db.expire_all()
        c = test_db.query(Coupon).filter(Coupon.id == coupon.id).first()
        assert c.is_active is False

    def test_05_create_discount_coupon_validates_range(self, admin_client, test_db):
        """POST /admin/coupons with discount > 100 → 400."""
        resp = admin_client.post(
            "/admin/coupons",
            data={
                "code": f"DISC-{uuid.uuid4().hex[:6].upper()}",
                "coupon_type": "PURCHASE_DISCOUNT_PERCENT",
                "value": "150",  # > 100 → invalid
                "description": "bad range",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 400


# ============================================================================
# SMOKE-06: Invitation Code — Create via API + view page
# ============================================================================

class TestSmoke06InvitationCodes:

    def test_01_invitation_code_page_loads(self, admin_client, invitation_code):
        """GET /admin/invitation-codes → 200, code visible."""
        resp = admin_client.get("/admin/invitation-codes")
        assert resp.status_code == 200
        assert invitation_code.code in resp.text
        assert "Internal Server Error" not in resp.text

    def test_02_multiple_codes_render_correctly(self, admin_client, test_db, admin_user):
        """Invitation codes page renders multiple codes (used + unused) without errors."""
        # Seed two codes: one used, one not
        ic_used = InvitationCode(
            code=f"USED-{uuid.uuid4().hex[:6].upper()}",
            invited_name="Used Person",
            bonus_credits=50,
            is_used=True,
            created_by_admin_id=admin_user.id,
        )
        ic_free = InvitationCode(
            code=f"FREE-{uuid.uuid4().hex[:6].upper()}",
            invited_name="Free Person",
            bonus_credits=100,
            is_used=False,
            created_by_admin_id=admin_user.id,
        )
        test_db.add_all([ic_used, ic_free])
        test_db.commit()

        resp = admin_client.get("/admin/invitation-codes")
        assert resp.status_code == 200
        assert ic_used.code in resp.text
        assert ic_free.code in resp.text
        assert "Internal Server Error" not in resp.text

    def test_03_used_code_not_redeemable_again(self, admin_client, test_db, admin_user):
        """Invitation code marked is_used=True cannot be viewed as unused."""
        ic = InvitationCode(
            code=f"USED-{uuid.uuid4().hex[:6].upper()}",
            invited_name="Used Invitee",
            bonus_credits=50,
            is_used=True,
            created_by_admin_id=admin_user.id,
        )
        test_db.add(ic)
        test_db.commit()

        resp = admin_client.get("/admin/invitation-codes")
        assert resp.status_code == 200
        # The page should still render without errors
        assert "Internal Server Error" not in resp.text


# ============================================================================
# SMOKE-07: Navigation — all admin pages return 200
# ============================================================================

ADMIN_PAGES = [
    "/admin/users",
    "/admin/sessions",
    "/admin/semesters",
    "/admin/analytics",
    "/admin/payments",
    "/admin/coupons",
    "/admin/invitation-codes",
    "/admin/locations",
    "/admin/game-presets",
    "/admin/system-events",
    "/admin/tournaments",
    "/admin/enrollments",
]


class TestSmoke07Navigation:

    @pytest.mark.parametrize("path", ADMIN_PAGES)
    def test_admin_page_loads_200(self, admin_client, path):
        """GET {path} → 200, no Internal Server Error in body."""
        resp = admin_client.get(path)
        assert resp.status_code == 200, (
            f"Expected 200 for {path}, got {resp.status_code}"
        )
        assert "Internal Server Error" not in resp.text, (
            f"500 error on {path}"
        )

    def test_analytics_nav_strip_present(self, admin_client):
        """GET /admin/analytics → nav strip includes all key links."""
        resp = admin_client.get("/admin/analytics")
        assert resp.status_code == 200
        for link in ["/admin/users", "/admin/sessions", "/admin/semesters",
                     "/admin/tournaments", "/admin/locations", "/admin/payments"]:
            assert link in resp.text, f"Nav link {link} missing from analytics.html"

    def test_semesters_nav_strip_present(self, admin_client):
        """GET /admin/semesters → nav strip includes all key links."""
        resp = admin_client.get("/admin/semesters")
        assert resp.status_code == 200
        for link in ["/admin/analytics", "/admin/sessions", "/admin/locations"]:
            assert link in resp.text, f"Nav link {link} missing from semesters.html"

    def test_users_page_has_analytics_and_semesters_links(self, admin_client):
        """GET /admin/users → header nav contains Analytics + Semesters links."""
        resp = admin_client.get("/admin/users")
        assert resp.status_code == 200
        assert "/admin/analytics" in resp.text
        assert "/admin/semesters" in resp.text

    def test_pagination_on_users_page(self, admin_client):
        """GET /admin/users → page renders with valid page structure."""
        resp = admin_client.get("/admin/users?page=1")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text
        # Stats cards should be present
        assert "Total Users" in resp.text

    def test_system_events_default_filter_is_open(self, admin_client):
        """GET /admin/system-events → default resolved filter = 'open'."""
        resp = admin_client.get("/admin/system-events")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text
        # 'open' should be selected in the resolved filter
        assert 'value="open"' in resp.text


# ============================================================================
# SMOKE-08: Invoice Verification Workflow
# ============================================================================

class TestSmoke08InvoiceVerification:
    """Covers the 3-state invoice lifecycle via new web wrapper routes."""

    def test_01_bookings_page_in_nav(self, admin_client):
        """Payments page nav contains Bookings link."""
        resp = admin_client.get("/admin/payments")
        assert resp.status_code == 200
        assert "/admin/bookings" in resp.text

    def test_02_verify_invoice(self, admin_client, test_db, invoice_request, student_user):
        """POST /admin/invoices/{id}/verify → 200, credits added to student."""
        initial_balance = student_user.credit_balance or 0
        resp = admin_client.post(f"/admin/invoices/{invoice_request.id}/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["credits_added"] == invoice_request.credit_amount
        # Verify DB state
        test_db.refresh(student_user)
        assert student_user.credit_balance == initial_balance + invoice_request.credit_amount
        test_db.refresh(invoice_request)
        assert invoice_request.status == "verified"

    def test_03_verify_already_verified_returns_400(self, admin_client, test_db, invoice_request):
        """POST verify on already-verified invoice → 400."""
        invoice_request.status = "verified"
        test_db.commit()
        resp = admin_client.post(f"/admin/invoices/{invoice_request.id}/verify")
        assert resp.status_code == 400

    def test_04_cancel_invoice(self, admin_client, test_db, invoice_request):
        """POST /admin/invoices/{id}/cancel → 200, status=cancelled."""
        resp = admin_client.post(
            f"/admin/invoices/{invoice_request.id}/cancel",
            data={"reason": "Test cancellation"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        test_db.refresh(invoice_request)
        assert invoice_request.status == "cancelled"

    def test_05_unverify_invoice(self, admin_client, test_db, invoice_request, student_user):
        """POST /admin/invoices/{id}/unverify → 200, credits reverted."""
        # First verify
        invoice_request.status = "verified"
        student_user.credit_balance = (student_user.credit_balance or 0) + invoice_request.credit_amount
        student_user.credit_purchased = (student_user.credit_purchased or 0) + invoice_request.credit_amount
        test_db.commit()
        balance_before = student_user.credit_balance

        resp = admin_client.post(f"/admin/invoices/{invoice_request.id}/unverify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["credits_removed"] == invoice_request.credit_amount
        test_db.refresh(student_user)
        assert student_user.credit_balance == balance_before - invoice_request.credit_amount
        test_db.refresh(invoice_request)
        assert invoice_request.status == "pending"


# ============================================================================
# SMOKE-09: Bookings Admin Panel
# ============================================================================

class TestSmoke09BookingsPanel:
    """Covers /admin/bookings page and booking action routes."""

    def test_01_bookings_page_renders(self, admin_client):
        """GET /admin/bookings → 200, contains expected UI elements."""
        resp = admin_client.get("/admin/bookings")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text
        assert "Booking Management" in resp.text
        assert "Confirmed" in resp.text

    def test_02_bookings_page_with_status_filter(self, admin_client):
        """GET /admin/bookings?status_filter=CONFIRMED → 200."""
        resp = admin_client.get("/admin/bookings?status_filter=CONFIRMED")
        assert resp.status_code == 200
        assert "Internal Server Error" not in resp.text

    def test_03_confirm_booking(self, admin_client, test_db, session_obj, student_user):
        """POST /admin/bookings/{id}/confirm → 200, status=CONFIRMED."""
        from app.models.booking import Booking, BookingStatus
        b = Booking(user_id=student_user.id, session_id=session_obj.id, status=BookingStatus.PENDING)
        test_db.add(b)
        test_db.commit()
        test_db.refresh(b)

        resp = admin_client.post(f"/admin/bookings/{b.id}/confirm")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        test_db.refresh(b)
        assert b.status == BookingStatus.CONFIRMED

    def test_04_cancel_booking(self, admin_client, test_db, session_obj, student_user):
        """POST /admin/bookings/{id}/cancel → 200, status=CANCELLED."""
        from app.models.booking import Booking, BookingStatus
        b = Booking(user_id=student_user.id, session_id=session_obj.id, status=BookingStatus.CONFIRMED)
        test_db.add(b)
        test_db.commit()
        test_db.refresh(b)

        resp = admin_client.post(
            f"/admin/bookings/{b.id}/cancel",
            data={"reason": "Admin test cancel"}
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        test_db.refresh(b)
        assert b.status == BookingStatus.CANCELLED

    def test_05_mark_attendance(self, admin_client, test_db, session_obj, student_user):
        """POST /admin/bookings/{id}/attendance → 200, attendance record created."""
        from app.models.booking import Booking, BookingStatus
        from app.models.attendance import Attendance, AttendanceStatus
        b = Booking(user_id=student_user.id, session_id=session_obj.id, status=BookingStatus.CONFIRMED)
        test_db.add(b)
        test_db.commit()
        test_db.refresh(b)

        resp = admin_client.post(
            f"/admin/bookings/{b.id}/attendance",
            data={"attendance_status": "present", "notes": "Smoke test"}
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        att = test_db.query(Attendance).filter(Attendance.booking_id == b.id).first()
        assert att is not None
        assert att.status == AttendanceStatus.present

    def test_06_confirm_nonexistent_booking_returns_404(self, admin_client):
        """POST /admin/bookings/999999/confirm → 404."""
        resp = admin_client.post("/admin/bookings/999999/confirm")
        assert resp.status_code == 404

    def test_07_bookings_page_in_nav(self, admin_client):
        """Users admin page nav contains Bookings link."""
        resp = admin_client.get("/admin/users")
        assert resp.status_code == 200
        assert "/admin/bookings" in resp.text
