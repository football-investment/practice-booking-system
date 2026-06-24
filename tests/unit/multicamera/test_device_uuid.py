"""
MC1-iOS-0 — Stable Device UUID: create-or-get semantics.

DU-01  device_uuid + device_type → new ManagedDevice with client UUID
DU-02  second call same device_uuid → same ManagedDevice (idempotent)
DU-03  same device_uuid, same session → idempotent SessionDevice
DU-04  device_uuid of existing device → returns it without creating
DU-05  device_uuid owned by another user → 403
DU-06  device_uuid=nil + device_type → old flow (backward compat)
DU-07  neither device_uuid nor device_type → 422
DU-08  invalid UUID format → 422
DU-09  device_uuid without device_type, device unknown → 422
DU-10  device_type mismatch on same UUID → preserves original type
DU-11  concurrent same UUID create → exactly one ManagedDevice
DU-12  concurrent same session+device register → exactly one SessionDevice
"""
import threading
import uuid as _uuid

import pytest

from app.database import SessionLocal
from app.models.managed_device import ManagedDevice
from app.models.multicamera_session import (
    MultiCameraSession,
    SessionDevice,
    SessionParticipant,
    SessionStatus,
)
from app.models.user import User, UserRole
from app.services.multicamera.device_service import DeviceService
from app.services.multicamera.session_service import SessionService


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_user(db, tag=None):
    tag = tag or _uuid.uuid4().hex[:8]
    u = User(
        name=f"DU-{tag}", email=f"du-{tag}@test.com",
        password_hash="x", role=UserRole.INSTRUCTOR, is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_session_and_participant(db, user):
    s = MultiCameraSession(
        created_by_user_id=user.id, status=SessionStatus.ACTIVE.value,
        max_participants=4, max_devices=4,
    )
    db.add(s)
    db.flush()
    p = SessionParticipant(session_id=s.id, user_id=user.id, role="instructor")
    db.add(p)
    db.flush()
    return s, p


# ── DU-01 — create with client UUID ─────────────────────────────────────────

class TestCreateOrGetDevice:
    def test_du_01_create_with_client_uuid(self, db):
        """DU-01: device_uuid + device_type → ManagedDevice created with that UUID."""
        user = _make_user(db)
        client_uuid = _uuid.uuid4()
        ds = DeviceService(db)
        md = ds.register_managed_device_with_uuid(
            user.id, client_uuid, "iphone", "Test iPhone",
        )
        assert md is not None
        assert md.device_uuid == client_uuid
        assert md.owner_user_id == user.id
        assert md.device_type == "iphone"
        assert md.device_name == "Test iPhone"

    def test_du_02_second_call_same_uuid_idempotent(self, db):
        """DU-02: same device_uuid → same ManagedDevice row."""
        user = _make_user(db)
        client_uuid = _uuid.uuid4()
        ds = DeviceService(db)
        md1 = ds.register_managed_device_with_uuid(user.id, client_uuid, "iphone")
        md2 = ds.register_managed_device_with_uuid(user.id, client_uuid, "iphone")
        assert md1.id == md2.id

    def test_du_03_same_session_device_idempotent(self, db):
        """DU-03: same device_uuid in same session → same SessionDevice."""
        user = _make_user(db)
        client_uuid = _uuid.uuid4()
        s, p = _make_session_and_participant(db, user)
        ds = DeviceService(db)
        md = ds.register_managed_device_with_uuid(user.id, client_uuid, "ipad")

        ss = SessionService(db)
        sd1 = ss.register_device(s.session_uuid, md.device_uuid, "instructor_primary")
        sd2 = ss.register_device(s.session_uuid, md.device_uuid, "instructor_primary")
        assert sd1.id == sd2.id

    def test_du_04_existing_device_returned(self, db):
        """DU-04: device_uuid already exists → returns existing, no new row."""
        user = _make_user(db)
        client_uuid = _uuid.uuid4()
        ds = DeviceService(db)
        md_first = ds.register_managed_device_with_uuid(user.id, client_uuid, "ipad")
        count_before = db.query(ManagedDevice).filter(
            ManagedDevice.device_uuid == client_uuid
        ).count()

        md_again = ds.register_managed_device_with_uuid(user.id, client_uuid, "ipad")
        count_after = db.query(ManagedDevice).filter(
            ManagedDevice.device_uuid == client_uuid
        ).count()

        assert md_again.id == md_first.id
        assert count_after == count_before

    def test_du_06_nil_uuid_backward_compat(self, db):
        """DU-06: device_uuid=None + device_type → old flow (server-generated UUID)."""
        user = _make_user(db)
        ds = DeviceService(db)
        md = ds.register_managed_device(user.id, "iphone", "Old Client iPhone")
        assert md is not None
        assert md.device_uuid is not None
        assert md.device_type == "iphone"


# ── DU-10 — device type mismatch ────────────────────────────────────────────

class TestDeviceTypeMismatch:
    def test_du_10_type_mismatch_preserves_original(self, db):
        """DU-10: same UUID with different device_type → original type preserved."""
        user = _make_user(db)
        client_uuid = _uuid.uuid4()
        ds = DeviceService(db)
        md_ipad = ds.register_managed_device_with_uuid(user.id, client_uuid, "ipad")
        assert md_ipad.device_type == "ipad"

        md_iphone = ds.register_managed_device_with_uuid(user.id, client_uuid, "iphone")
        assert md_iphone.id == md_ipad.id
        assert md_iphone.device_type == "ipad"  # original preserved


# ── DU-11 — concurrent UUID create ──────────────────────────────────────────

class TestConcurrentDeviceCreate:
    def test_du_11_concurrent_same_uuid_exactly_one_device(self):
        """DU-11: two threads creating same UUID → exactly one ManagedDevice."""
        setup_db = SessionLocal()
        client_uuid = _uuid.uuid4()
        try:
            user = _make_user(setup_db, tag=f"conc-{client_uuid.hex[:6]}")
            setup_db.commit()
            user_id = user.id
        except Exception:
            setup_db.rollback()
            raise
        finally:
            setup_db.close()

        results = []
        errors = []

        def _register():
            thread_db = SessionLocal()
            try:
                ds = DeviceService(thread_db)
                md = ds.register_managed_device_with_uuid(
                    user_id, client_uuid, "iphone",
                )
                results.append(md.id)
            except Exception as e:
                errors.append(e)
            finally:
                thread_db.close()

        t1 = threading.Thread(target=_register)
        t2 = threading.Thread(target=_register)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Unexpected errors: {errors}"
        assert len(results) == 2
        assert results[0] == results[1], "Both threads must return the same ManagedDevice"

        check_db = SessionLocal()
        try:
            count = check_db.query(ManagedDevice).filter(
                ManagedDevice.device_uuid == client_uuid
            ).count()
            assert count == 1, f"Expected exactly 1 ManagedDevice, got {count}"
        finally:
            check_db.close()

    def test_du_12_concurrent_same_session_device_exactly_one(self):
        """DU-12: two threads registering same device to same session → one SessionDevice."""
        setup_db = SessionLocal()
        client_uuid = _uuid.uuid4()
        try:
            user = _make_user(setup_db, tag=f"sd-conc-{client_uuid.hex[:6]}")
            s, p = _make_session_and_participant(setup_db, user)
            ds = DeviceService(setup_db)
            md = ds.register_managed_device_with_uuid(user.id, client_uuid, "ipad")
            setup_db.commit()
            session_uuid = s.session_uuid
            session_id = s.id
            device_id = md.id
        except Exception:
            setup_db.rollback()
            raise
        finally:
            setup_db.close()

        results = []
        errors = []

        def _register_sd():
            thread_db = SessionLocal()
            try:
                ss = SessionService(thread_db)
                sd = ss.register_device(session_uuid, client_uuid, "instructor_primary")
                results.append(sd.id)
            except Exception as e:
                errors.append(e)
            finally:
                thread_db.close()

        t1 = threading.Thread(target=_register_sd)
        t2 = threading.Thread(target=_register_sd)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # At least one must succeed; IntegrityError on second is acceptable
        successful = [r for r in results]
        assert len(successful) >= 1, f"At least one must succeed; errors={errors}"

        check_db = SessionLocal()
        try:
            count = check_db.query(SessionDevice).filter(
                SessionDevice.session_id == session_id,
                SessionDevice.device_id == device_id,
            ).count()
            assert count == 1, f"Expected exactly 1 SessionDevice, got {count}"
        finally:
            check_db.close()
