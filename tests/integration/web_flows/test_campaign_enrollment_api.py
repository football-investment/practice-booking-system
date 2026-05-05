"""
Integration tests — POST /api/v1/tournaments/{id}/bulk-enroll-campaign

  BULKENR-API-01  2 eligible entries → 200, enrollments created in DB
  BULKENR-API-02  idempotent: second POST → enrolled=0, skipped=2
  BULKENR-API-03  non-PROMOTION_EVENT → 400
  BULKENR-API-04  non-admin user → 403
"""
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.dependencies import get_current_user_web
from app.core.security import get_password_hash
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.semester_enrollment import SemesterEnrollment
from app.models.sponsor import Sponsor, SponsorCampaign, SponsorAudienceEntry
from app.models.club import CsvImportLog
from app.models.user import User, UserRole


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_admin(db: Session) -> User:
    u = User(
        email=f"api-admin+{uuid.uuid4().hex[:8]}@lfa.com",
        name="API Admin",
        password_hash=get_password_hash("Admin1234!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_student(db: Session) -> User:
    u = User(
        email=f"api-student+{uuid.uuid4().hex[:8]}@lfa.com",
        name="API Student",
        password_hash=get_password_hash("Student1234!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_sponsor(db: Session) -> Sponsor:
    s = Sponsor(
        name=f"API Sponsor {uuid.uuid4().hex[:6]}",
        code=f"APIS-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(s)
    db.flush()
    return s


def _make_campaign(db: Session, sponsor: Sponsor) -> SponsorCampaign:
    c = SponsorCampaign(
        sponsor_id=sponsor.id,
        name=f"API Campaign {uuid.uuid4().hex[:6]}",
        campaign_type="IMPORT",
        status="ACTIVE",
    )
    db.add(c)
    db.flush()
    return c


def _make_promo_tournament(db: Session, sponsor: Sponsor,
                            campaign: SponsorCampaign,
                            status: str = "DRAFT") -> Semester:
    sem = Semester(
        code=f"PROMO-API-{uuid.uuid4().hex[:6]}",
        name="API Promo Event",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 2),
        status=SemesterStatus.DRAFT,
        tournament_status=status,
        semester_category=SemesterCategory.PROMOTION_EVENT,
        age_groups=["PRE"],
        enrollment_cost=0,
        organizer_sponsor_id=sponsor.id,
        organizer_campaign_id=campaign.id,
    )
    db.add(sem)
    db.flush()
    return sem


def _make_user_with_license(db: Session) -> tuple[User, UserLicense]:
    u = User(
        email=f"lic-player+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Licensed Player",
        password_hash=get_password_hash("x"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.flush()
    lic = UserLicense(
        user_id=u.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
        started_at=datetime.now(timezone.utc),
    )
    db.add(lic)
    db.flush()
    return u, lic


def _make_audience_entry(db: Session, sponsor: Sponsor, campaign: SponsorCampaign,
                          user: User) -> SponsorAudienceEntry:
    log = CsvImportLog(sponsor_id=sponsor.id, campaign_id=campaign.id)
    db.add(log)
    db.flush()
    entry = SponsorAudienceEntry(
        sponsor_id=sponsor.id,
        campaign_id=campaign.id,
        import_log_id=log.id,
        first_name="API",
        last_name=f"Player {uuid.uuid4().hex[:4]}",
        email=f"api-entry+{uuid.uuid4().hex[:8]}@lfa.com",
        status="ACTIVE",
        consent_given=True,
        user_id=user.id,
    )
    db.add(entry)
    db.flush()
    return entry


def _client(db: Session, actor: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_web] = lambda: actor
    return TestClient(app, raise_server_exceptions=True)


# ── BULKENR-API-01 ────────────────────────────────────────────────────────────

class TestBulkEnrollApiSuccess:
    """BULKENR-API-01: 2 eligible entries → 200, 2 enrollments in DB."""

    def test_bulkenr_api_01(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db)
        campaign = _make_campaign(test_db, sponsor)
        t = _make_promo_tournament(test_db, sponsor, campaign)

        u1, _ = _make_user_with_license(test_db)
        u2, _ = _make_user_with_license(test_db)
        _make_audience_entry(test_db, sponsor, campaign, u1)
        _make_audience_entry(test_db, sponsor, campaign, u2)
        test_db.commit()

        client = _client(test_db, admin)
        try:
            resp = client.post(f"/api/v1/tournaments/{t.id}/bulk-enroll-campaign")
            assert resp.status_code == 200

            body = resp.json()
            assert body["enrolled_count"] == 2
            assert body["skipped_count"] == 0
            assert len(body["enrolled"]) == 2

            enrolled_in_db = test_db.query(SemesterEnrollment).filter(
                SemesterEnrollment.semester_id == t.id,
                SemesterEnrollment.is_active == True,
            ).count()
            assert enrolled_in_db == 2
        finally:
            app.dependency_overrides.clear()


# ── BULKENR-API-02 ────────────────────────────────────────────────────────────

class TestBulkEnrollApiIdempotent:
    """BULKENR-API-02: second POST → enrolled=0, skipped=N."""

    def test_bulkenr_api_02(self, test_db: Session):
        admin = _make_admin(test_db)
        sponsor = _make_sponsor(test_db)
        campaign = _make_campaign(test_db, sponsor)
        t = _make_promo_tournament(test_db, sponsor, campaign)

        u, _ = _make_user_with_license(test_db)
        _make_audience_entry(test_db, sponsor, campaign, u)
        test_db.commit()

        client = _client(test_db, admin)
        try:
            # First call
            r1 = client.post(f"/api/v1/tournaments/{t.id}/bulk-enroll-campaign")
            assert r1.status_code == 200
            assert r1.json()["enrolled_count"] == 1

            # Second call — idempotent
            r2 = client.post(f"/api/v1/tournaments/{t.id}/bulk-enroll-campaign")
            assert r2.status_code == 200
            body2 = r2.json()
            assert body2["enrolled_count"] == 0
            assert body2["skipped_count"] == 1
        finally:
            app.dependency_overrides.clear()


# ── BULKENR-API-03 ────────────────────────────────────────────────────────────

class TestBulkEnrollApiNonPromo:
    """BULKENR-API-03: non-PROMOTION_EVENT tournament → 400."""

    def test_bulkenr_api_03(self, test_db: Session):
        admin = _make_admin(test_db)
        non_promo = Semester(
            code=f"MINI-API-{uuid.uuid4().hex[:6]}",
            name="Mini Season API",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 2),
            status=SemesterStatus.DRAFT,
            tournament_status="DRAFT",
            semester_category=SemesterCategory.MINI_SEASON,
            age_group="AMATEUR",
            enrollment_cost=0,
        )
        test_db.add(non_promo)
        test_db.commit()

        client = _client(test_db, admin)
        try:
            resp = client.post(f"/api/v1/tournaments/{non_promo.id}/bulk-enroll-campaign")
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()


# ── BULKENR-API-04 ────────────────────────────────────────────────────────────

class TestBulkEnrollApiNonAdmin:
    """BULKENR-API-04: non-admin user → 403."""

    def test_bulkenr_api_04(self, test_db: Session):
        student = _make_student(test_db)
        sponsor = _make_sponsor(test_db)
        campaign = _make_campaign(test_db, sponsor)
        t = _make_promo_tournament(test_db, sponsor, campaign)
        test_db.commit()

        client = _client(test_db, student)
        try:
            resp = client.post(f"/api/v1/tournaments/{t.id}/bulk-enroll-campaign")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()
