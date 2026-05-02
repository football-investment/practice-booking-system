"""
Sponsor CRUD Web Flow Tests — SPON-01 through SPON-11

  SPON-01  GET /admin/sponsors → 200 (empty list)
  SPON-02  POST /admin/sponsors/new → sponsor created, redirects to detail
  SPON-03  POST /admin/sponsors/new duplicate code → 400 with error message
  SPON-04  POST /admin/sponsors/new with primary contact → contact created (is_primary=True)
  SPON-05  GET /admin/sponsors/{id} → 200, shows name, code
  SPON-06  POST /admin/sponsors/{id}/edit → fields updated
  SPON-07  POST /admin/sponsors/{id}/contacts/add → contact added
  SPON-08  POST /admin/sponsors/{id}/contacts/add (second primary) → redirect with error
  SPON-09  POST /admin/sponsors/{id}/contacts/{cid}/delete → contact removed
  SPON-10  GET /admin/sponsors/{id} non-existent → 404
  SPON-11  POST /admin/sponsors/new then GET /admin/sponsors → sponsor appears in list

DONE = pytest tests/integration/web_flows/test_sponsor_crud_web.py -v
"""
import uuid
import pytest
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.dependencies import get_current_user_web
from app.models.user import User, UserRole
from app.models.sponsor import Sponsor, SponsorContact
from app.core.security import get_password_hash


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_admin(db: Session) -> User:
    u = User(
        email=f"admin-spon+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Sponsor Admin",
        password_hash=get_password_hash("Admin1234!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_sponsor(db: Session, admin: User, suffix: str = "") -> Sponsor:
    s = Sponsor(
        name=f"Test Partner {suffix or uuid.uuid4().hex[:6]}",
        code=f"TP-{uuid.uuid4().hex[:6].upper()}",
        is_active=True,
        created_by=admin.id,
    )
    db.add(s)
    db.flush()
    return s


def _admin_client(test_db: Session, admin: User) -> TestClient:
    def override_db():
        yield test_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_web] = lambda: admin
    return TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"})


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSponsorList:
    """SPON-01, SPON-11"""

    def test_spon_01_list_empty(self, test_db: Session):
        admin = _make_admin(test_db)
        client = _admin_client(test_db, admin)
        try:
            resp = client.get("/admin/sponsors")
            assert resp.status_code == 200
            assert "Partners" in resp.text
        finally:
            app.dependency_overrides.clear()

    def test_spon_11_created_sponsor_appears_in_list(self, test_db: Session):
        admin = _make_admin(test_db)
        client = _admin_client(test_db, admin)
        code = f"LIST-{uuid.uuid4().hex[:4].upper()}"
        try:
            # Create via route so it's committed within the overridden session
            create_resp = client.post(
                "/admin/sponsors/new",
                data={"name": "List Check Sponsor", "code": code},
                follow_redirects=False,
            )
            assert create_resp.status_code == 303

            resp = client.get("/admin/sponsors")
            assert resp.status_code == 200
            assert "List Check Sponsor" in resp.text
        finally:
            app.dependency_overrides.clear()


class TestSponsorCreate:
    """SPON-02, SPON-03, SPON-04"""

    def test_spon_02_create_sponsor(self, test_db: Session):
        admin = _make_admin(test_db)
        client = _admin_client(test_db, admin)
        code = f"ADIDAS-{uuid.uuid4().hex[:4].upper()}"
        try:
            resp = client.post(
                "/admin/sponsors/new",
                data={
                    "name": "Adidas Hungary",
                    "code": code,
                    "brand_category": "Sportswear",
                    "city": "Budapest",
                    "country": "Hungary",
                },
                follow_redirects=False,
            )
            assert resp.status_code == 303
            location = resp.headers.get("location", "")
            assert "/admin/sponsors/" in location

            sponsor = test_db.query(Sponsor).filter(Sponsor.code == code).first()
            assert sponsor is not None
            assert sponsor.name == "Adidas Hungary"
            assert sponsor.brand_category == "Sportswear"
            assert sponsor.is_active is True
            assert sponsor.created_by == admin.id
        finally:
            app.dependency_overrides.clear()

    def test_spon_03_duplicate_code_returns_400(self, test_db: Session):
        admin = _make_admin(test_db)
        client = _admin_client(test_db, admin)
        code = f"DUP-{uuid.uuid4().hex[:4].upper()}"
        try:
            # First creation via route (so the session owns the committed record)
            first = client.post(
                "/admin/sponsors/new",
                data={"name": "First Sponsor", "code": code},
                follow_redirects=False,
            )
            assert first.status_code == 303

            # Second creation with same code → 400 with error message
            resp = client.post(
                "/admin/sponsors/new",
                data={"name": "Duplicate Partner", "code": code},
                follow_redirects=False,
            )
            assert resp.status_code == 400
            assert "already in use" in resp.text
        finally:
            app.dependency_overrides.clear()

    def test_spon_04_create_with_primary_contact(self, test_db: Session):
        admin = _make_admin(test_db)
        client = _admin_client(test_db, admin)
        code = f"NIKE-{uuid.uuid4().hex[:4].upper()}"
        try:
            resp = client.post(
                "/admin/sponsors/new",
                data={
                    "name": "Nike Hungary",
                    "code": code,
                    "contact_name": "Kovács János",
                    "contact_role": "Partnership Manager",
                    "contact_email_primary": "janos@nike.hu",
                },
                follow_redirects=False,
            )
            assert resp.status_code == 303

            sponsor = test_db.query(Sponsor).filter(Sponsor.code == code).first()
            assert sponsor is not None

            primary = (
                test_db.query(SponsorContact)
                .filter(SponsorContact.sponsor_id == sponsor.id, SponsorContact.is_primary == True)  # noqa: E712
                .first()
            )
            assert primary is not None
            assert primary.name == "Kovács János"
            assert primary.role == "Partnership Manager"
        finally:
            app.dependency_overrides.clear()


class TestSponsorDetail:
    """SPON-05, SPON-10"""

    def test_spon_05_detail_200(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db, admin, suffix="Detail")
        test_db.commit()
        client = _admin_client(test_db, admin)
        try:
            resp = client.get(f"/admin/sponsors/{sponsor.id}")
            assert resp.status_code == 200
            assert sponsor.name in resp.text
            assert sponsor.code in resp.text
        finally:
            app.dependency_overrides.clear()

    def test_spon_10_detail_404_unknown(self, test_db: Session):
        admin = _make_admin(test_db)
        client = _admin_client(test_db, admin)
        try:
            resp = client.get("/admin/sponsors/9999999")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestSponsorEdit:
    """SPON-06"""

    def test_spon_06_edit_sponsor(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db, admin, suffix="Edit")
        test_db.commit()
        client = _admin_client(test_db, admin)
        try:
            resp = client.post(
                f"/admin/sponsors/{sponsor.id}/edit",
                data={
                    "name": "Updated Partner Name",
                    "brand_category": "Insurance",
                    "city": "Debrecen",
                    "country": "Hungary",
                    "is_active": "on",
                },
                follow_redirects=False,
            )
            assert resp.status_code == 303

            test_db.expire_all()
            updated = test_db.query(Sponsor).filter(Sponsor.id == sponsor.id).first()
            assert updated.name == "Updated Partner Name"
            assert updated.brand_category == "Insurance"
            assert updated.city == "Debrecen"
            assert updated.is_active is True
        finally:
            app.dependency_overrides.clear()


class TestSponsorContacts:
    """SPON-07, SPON-08, SPON-09"""

    def test_spon_07_add_contact(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db, admin, suffix="Contacts")
        test_db.commit()
        client = _admin_client(test_db, admin)
        try:
            resp = client.post(
                f"/admin/sponsors/{sponsor.id}/contacts/add",
                data={
                    "contact_name": "Kiss Péter",
                    "contact_role": "Account Manager",
                    "contact_email": "peter@partner.com",
                },
                follow_redirects=False,
            )
            assert resp.status_code == 303

            contact = (
                test_db.query(SponsorContact)
                .filter(SponsorContact.sponsor_id == sponsor.id)
                .first()
            )
            assert contact is not None
            assert contact.name == "Kiss Péter"
            assert contact.role == "Account Manager"
            assert contact.is_primary is False
        finally:
            app.dependency_overrides.clear()

    def test_spon_08_second_primary_returns_error_redirect(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db, admin, suffix="DupPrimary")
        existing_primary = SponsorContact(
            sponsor_id=sponsor.id,
            name="First Primary",
            is_primary=True,
        )
        test_db.add(existing_primary)
        test_db.commit()
        client = _admin_client(test_db, admin)
        try:
            resp = client.post(
                f"/admin/sponsors/{sponsor.id}/contacts/add",
                data={
                    "contact_name": "Second Primary",
                    "is_primary": "on",
                },
                follow_redirects=False,
            )
            # Should redirect with error= in URL, NOT create a second primary
            assert resp.status_code == 303
            location = resp.headers.get("location", "")
            assert "error=" in location

            count = (
                test_db.query(SponsorContact)
                .filter(SponsorContact.sponsor_id == sponsor.id, SponsorContact.is_primary == True)  # noqa: E712
                .count()
            )
            assert count == 1
        finally:
            app.dependency_overrides.clear()

    def test_spon_09_delete_contact(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db, admin, suffix="DelContact")
        contact = SponsorContact(sponsor_id=sponsor.id, name="To Delete")
        test_db.add(contact)
        test_db.commit()
        contact_id = contact.id
        client = _admin_client(test_db, admin)
        try:
            resp = client.post(
                f"/admin/sponsors/{sponsor.id}/contacts/{contact_id}/delete",
                follow_redirects=False,
            )
            assert resp.status_code == 303

            deleted = test_db.query(SponsorContact).filter(SponsorContact.id == contact_id).first()
            assert deleted is None
        finally:
            app.dependency_overrides.clear()
