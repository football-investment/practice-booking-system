"""
Multicamera Capture Cycle Tests — PR-MC1.

CC-01..08   create_cycle (happy path, idempotency, bad session status, no devices)
SC-01..06   schedule_cycle (happy, not-ready devices, bad status, revision)
CS-01..07   confirm_device_start (happy, all-start→recording, bad status, revision)
DS-01..06   confirm_device_stop (happy, completion logic, bad status)
RF-01..04   report_device_failure (happy, completion, terminal guard)
AC-01..04   abort_cycle (all active states, terminal guard)
FS-01..05   finalize_session (happy, non-terminal cycles, bad status, revision)
LC-01..03   list_cycles / GET
CM-01..04   cycle completion logic (partial, all-fail, mixed)
TR-01..03   transition guards (SESSION_TRANSITIONS include ACTIVE)
"""
import threading
import uuid as _uuid
from datetime import datetime, timezone, timedelta

import pytest

from app.database import SessionLocal
from app.models.managed_device import ManagedDevice
from app.models.multicamera_session import (
    CaptureCycle,
    CaptureCycleDevice,
    CycleDeviceRecordingStatus,
    CycleStatus,
    MultiCameraSession,
    SessionDevice,
    SessionParticipant,
    SessionStatus,
)
from app.models.user import User, UserRole
from app.services.multicamera.cycle_service import CycleService
from app.services.multicamera.exceptions import (
    CycleConflictError,
    CycleNotFoundError,
    DeviceNotFoundError,
    DeviceNotReadyError,
    InvalidTransitionError,
    NoCycleDevicesError,
    RevisionConflictError,
    SessionNotFoundError,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def users(db):
    tag = _uuid.uuid4().hex[:8]
    instructor = User(
        name="Instructor",
        email=f"cc-inst-{tag}@test.com",
        password_hash="x",
        role=UserRole.INSTRUCTOR,
        is_active=True,
    )
    player = User(
        name="Player",
        email=f"cc-play-{tag}@test.com",
        password_hash="x",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add_all([instructor, player])
    db.flush()
    return instructor, player


@pytest.fixture()
def active_session(db, users):
    """An ACTIVE session with instructor participant and two ready devices."""
    instructor, player = users
    tag = _uuid.uuid4().hex[:8]

    s = MultiCameraSession(
        created_by_user_id=instructor.id,
        status=SessionStatus.ACTIVE.value,
        max_participants=4,
        max_devices=4,
    )
    db.add(s)
    db.flush()

    p_inst = SessionParticipant(session_id=s.id, user_id=instructor.id, role="instructor")
    db.add(p_inst)
    db.flush()

    md1 = ManagedDevice(owner_user_id=instructor.id, device_type="ipad", device_name=f"iPad-{tag}")
    md2 = ManagedDevice(owner_user_id=player.id, device_type="iphone", device_name=f"iPhone-{tag}")
    db.add_all([md1, md2])
    db.flush()

    sd1 = SessionDevice(
        session_id=s.id, device_id=md1.id, participant_id=p_inst.id,
        device_role="instructor_primary", status="ready",
    )
    sd2 = SessionDevice(
        session_id=s.id, device_id=md2.id, participant_id=p_inst.id,
        device_role="player_primary", status="ready",
    )
    db.add_all([sd1, sd2])
    db.flush()

    return s, p_inst, sd1, sd2


@pytest.fixture()
def cycle_with_two_devices(db, active_session):
    """A PREPARING cycle with two required devices."""
    s, p_inst, sd1, sd2 = active_session
    svc = CycleService(db)
    cycle = svc.create_cycle(s.session_uuid, "idem-key-001", p_inst.id)
    return cycle, sd1, sd2, p_inst, s


# ── CC — create_cycle ─────────────────────────────────────────────────────────

class TestCreateCycle:
    def test_cc_01_happy_path(self, db, active_session):
        """CC-01: create_cycle on ACTIVE session creates cycle + device snapshot."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        cycle = svc.create_cycle(s.session_uuid, "key-cc01", p_inst.id)

        assert cycle.id is not None
        assert cycle.cycle_index == 0
        assert CycleStatus(cycle.status) == CycleStatus.PREPARING
        assert cycle.idempotency_key == "key-cc01"
        assert cycle.created_by_participant_id == p_inst.id
        assert len(cycle.cycle_devices) == 2

    def test_cc_02_device_snapshot_required_flags(self, db, active_session):
        """CC-02: auxiliary_camera device gets required=False, others True."""
        s, p_inst, sd1, sd2 = active_session
        tag = _uuid.uuid4().hex[:8]
        md3 = ManagedDevice(owner_user_id=p_inst.user_id, device_type="gopro", device_name=f"GoPro-{tag}")
        db.add(md3)
        db.flush()
        sd3 = SessionDevice(
            session_id=s.id, device_id=md3.id,
            managed_by_device_id=sd1.id,
            device_role="auxiliary_camera", status="ready",
        )
        db.add(sd3)
        db.flush()

        svc = CycleService(db)
        cycle = svc.create_cycle(s.session_uuid, "key-cc02", p_inst.id)

        required_map = {ccd.session_device_id: ccd.required for ccd in cycle.cycle_devices}
        assert required_map[sd1.id] is True
        assert required_map[sd2.id] is True
        assert required_map[sd3.id] is False

    def test_cc_03_idempotent_duplicate_key_returns_existing(self, db, active_session):
        """CC-03: duplicate idempotency_key returns existing cycle, no new row."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        c1 = svc.create_cycle(s.session_uuid, "key-cc03", p_inst.id)
        c2 = svc.create_cycle(s.session_uuid, "key-cc03", p_inst.id)
        assert c1.id == c2.id
        assert c1.cycle_index == c2.cycle_index

    def test_cc_04_different_keys_get_different_indices(self, db, active_session):
        """CC-04: two distinct keys → cycle_index 0 and 1."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        c1 = svc.create_cycle(s.session_uuid, "key-cc04a", p_inst.id)
        c2 = svc.create_cycle(s.session_uuid, "key-cc04b", p_inst.id)
        assert c1.cycle_index == 0
        assert c2.cycle_index == 1

    def test_cc_05_session_not_active_raises(self, db, users):
        """CC-05: session in LOBBY raises InvalidTransitionError."""
        instructor, _ = users
        s = MultiCameraSession(created_by_user_id=instructor.id, status=SessionStatus.LOBBY.value)
        db.add(s)
        db.flush()
        p = SessionParticipant(session_id=s.id, user_id=instructor.id, role="instructor")
        db.add(p)
        db.flush()

        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.create_cycle(s.session_uuid, "key-cc05", p.id)

    def test_cc_06_session_not_found_raises(self, db):
        """CC-06: non-existent session_uuid raises SessionNotFoundError."""
        svc = CycleService(db)
        with pytest.raises(SessionNotFoundError):
            svc.create_cycle(_uuid.uuid4(), "key-cc06", 1)

    def test_cc_07_no_active_devices_raises(self, db, users):
        """CC-07: ACTIVE session with no devices raises NoCycleDevicesError."""
        instructor, _ = users
        s = MultiCameraSession(created_by_user_id=instructor.id, status=SessionStatus.ACTIVE.value)
        db.add(s)
        db.flush()
        p = SessionParticipant(session_id=s.id, user_id=instructor.id, role="instructor")
        db.add(p)
        db.flush()

        svc = CycleService(db)
        with pytest.raises(NoCycleDevicesError):
            svc.create_cycle(s.session_uuid, "key-cc07", p.id)

    def test_cc_08_removed_devices_excluded_from_snapshot(self, db, active_session):
        """CC-08: removed session device is not included in cycle snapshot."""
        s, p_inst, sd1, sd2 = active_session
        from datetime import datetime, timezone
        sd2.removed_at = datetime.now(timezone.utc)
        db.flush()

        svc = CycleService(db)
        cycle = svc.create_cycle(s.session_uuid, "key-cc08", p_inst.id)
        device_ids = {ccd.session_device_id for ccd in cycle.cycle_devices}
        assert sd1.id in device_ids
        assert sd2.id not in device_ids


# ── SC — schedule_cycle ───────────────────────────────────────────────────────

class TestScheduleCycle:
    def test_sc_01_happy_path(self, db, cycle_with_two_devices):
        """SC-01: PREPARING → RECORDING_PENDING, scheduled_start_at set."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        result = svc.schedule_cycle(cycle.id, cycle.revision)

        assert CycleStatus(result.status) == CycleStatus.RECORDING_PENDING
        assert result.scheduled_start_at is not None
        expected_lead = timedelta(seconds=8)
        diff = abs((result.scheduled_start_at - datetime.now(timezone.utc)) - expected_lead)
        assert diff.total_seconds() < 2

    def test_sc_02_not_ready_device_raises(self, db, active_session):
        """SC-02: required device not ready → DeviceNotReadyError."""
        s, p_inst, sd1, sd2 = active_session
        sd2.status = "registered"
        db.flush()

        svc = CycleService(db)
        cycle = svc.create_cycle(s.session_uuid, "key-sc02", p_inst.id)
        with pytest.raises(DeviceNotReadyError):
            svc.schedule_cycle(cycle.id, cycle.revision)

    def test_sc_03_wrong_status_raises(self, db, cycle_with_two_devices):
        """SC-03: cycle already in RECORDING_PENDING → InvalidTransitionError on second call."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        with pytest.raises(InvalidTransitionError):
            svc.schedule_cycle(cycle.id, cycle.revision)

    def test_sc_04_revision_conflict_raises(self, db, cycle_with_two_devices):
        """SC-04: wrong revision raises RevisionConflictError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        with pytest.raises(RevisionConflictError):
            svc.schedule_cycle(cycle.id, cycle.revision + 99)

    def test_sc_05_cycle_not_found_raises(self, db):
        """SC-05: non-existent cycle_id raises CycleNotFoundError."""
        svc = CycleService(db)
        with pytest.raises(CycleNotFoundError):
            svc.schedule_cycle(99999, 1)

    def test_sc_06_auxiliary_device_not_blocking(self, db, active_session):
        """SC-06: auxiliary (non-required) device not-ready does not block schedule."""
        s, p_inst, sd1, sd2 = active_session
        tag = _uuid.uuid4().hex[:8]
        md3 = ManagedDevice(owner_user_id=p_inst.user_id, device_type="gopro", device_name=f"G-{tag}")
        db.add(md3)
        db.flush()
        sd3 = SessionDevice(
            session_id=s.id, device_id=md3.id,
            managed_by_device_id=sd1.id,
            device_role="auxiliary_camera", status="registered",
        )
        db.add(sd3)
        db.flush()

        svc = CycleService(db)
        cycle = svc.create_cycle(s.session_uuid, "key-sc06", p_inst.id)
        result = svc.schedule_cycle(cycle.id, cycle.revision)
        assert CycleStatus(result.status) == CycleStatus.RECORDING_PENDING


# ── CS — confirm_device_start ─────────────────────────────────────────────────

class TestConfirmDeviceStart:
    def _schedule(self, svc, cycle):
        return svc.schedule_cycle(cycle.id, cycle.revision)

    def test_cs_01_first_device_start_stays_recording_pending(self, db, cycle_with_two_devices):
        """CS-01: First device confirms start; cycle stays RECORDING_PENDING."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = self._schedule(svc, cycle)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        now = datetime.now(timezone.utc)
        result = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        assert CycleStatus(result.status) == CycleStatus.RECORDING_PENDING

    def test_cs_02_all_devices_start_transitions_to_recording(self, db, cycle_with_two_devices):
        """CS-02: Both required devices confirm start → RECORDING, recording_started_at set."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = self._schedule(svc, cycle)
        now = datetime.now(timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        # Reload ccd2 revision
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        result = svc.confirm_device_start(cycle.id, sd2.id, now, ccd2.revision)
        assert CycleStatus(result.status) == CycleStatus.RECORDING
        assert result.recording_started_at is not None

    def test_cs_03_wrong_cycle_status_raises(self, db, cycle_with_two_devices):
        """CS-03: cycle in PREPARING (not scheduled) → InvalidTransitionError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.confirm_device_start(cycle.id, sd1.id, datetime.now(timezone.utc), 1)

    def test_cs_04_revision_conflict_raises(self, db, cycle_with_two_devices):
        """CS-04: wrong cycle_device revision raises RevisionConflictError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = self._schedule(svc, cycle)
        with pytest.raises(RevisionConflictError):
            svc.confirm_device_start(cycle.id, sd1.id, datetime.now(timezone.utc), 999)

    def test_cs_05_unknown_device_raises(self, db, cycle_with_two_devices):
        """CS-05: session_device_id not in cycle → DeviceNotFoundError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = self._schedule(svc, cycle)
        with pytest.raises(DeviceNotFoundError):
            svc.confirm_device_start(cycle.id, 99999, datetime.now(timezone.utc), 1)

    def test_cs_06_double_confirm_start_raises(self, db, cycle_with_two_devices):
        """CS-06: confirming start twice raises InvalidTransitionError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = self._schedule(svc, cycle)
        now = datetime.now(timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        cycle = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        with pytest.raises(InvalidTransitionError):
            svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)

    def test_cs_07_started_at_stored(self, db, cycle_with_two_devices):
        """CS-07: started_at is persisted on the CycleDevice row."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = self._schedule(svc, cycle)
        t = datetime(2026, 6, 24, 10, 0, 0, tzinfo=timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        svc.confirm_device_start(cycle.id, sd1.id, t, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        assert ccd1.started_at == t


# ── ST — stop_cycle ───────────────────────────────────────────────────────────

class TestStopCycle:
    def _get_to_recording(self, db, cycle_with_two_devices):
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        now = datetime.now(timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd2.id, now, ccd2.revision)
        return cycle, sd1, sd2, svc

    def test_ds_01_stop_from_recording(self, db, cycle_with_two_devices):
        """DS-01: RECORDING → STOPPING, stop_requested_at set."""
        cycle, sd1, sd2, svc = self._get_to_recording(db, cycle_with_two_devices)
        result = svc.stop_cycle(cycle.id, cycle.revision)
        assert CycleStatus(result.status) == CycleStatus.STOPPING
        assert result.stop_requested_at is not None

    def test_ds_02_stop_from_wrong_status_raises(self, db, cycle_with_two_devices):
        """DS-02: stopping from PREPARING raises InvalidTransitionError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.stop_cycle(cycle.id, cycle.revision)


# ── DS — confirm_device_stop ──────────────────────────────────────────────────

class TestConfirmDeviceStop:
    def _get_to_stopping(self, db, cycle_with_two_devices):
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        now = datetime.now(timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        ccd2_init = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd2.id, now, ccd2.revision)
        cycle = svc.stop_cycle(cycle.id, cycle.revision)
        return cycle, sd1, sd2, svc

    def test_ds_stop_01_first_device_stop_stays_stopping(self, db, cycle_with_two_devices):
        """DS-STOP-01: one device stops, cycle stays STOPPING."""
        cycle, sd1, sd2, svc = self._get_to_stopping(db, cycle_with_two_devices)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        now = datetime.now(timezone.utc)
        result = svc.confirm_device_stop(cycle.id, sd1.id, now, ccd1.revision)
        assert CycleStatus(result.status) == CycleStatus.STOPPING

    def test_ds_stop_02_both_devices_stop_completes(self, db, cycle_with_two_devices):
        """DS-STOP-02: both devices confirm stop → COMPLETED, result=success."""
        cycle, sd1, sd2, svc = self._get_to_stopping(db, cycle_with_two_devices)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        now = datetime.now(timezone.utc)
        cycle = svc.confirm_device_stop(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        result = svc.confirm_device_stop(cycle.id, sd2.id, now, ccd2.revision)
        assert CycleStatus(result.status) == CycleStatus.COMPLETED
        assert result.result == "success"
        assert result.recording_stopped_at is not None
        assert result.completed_at is not None

    def test_ds_stop_03_wrong_device_status_raises(self, db, cycle_with_two_devices):
        """DS-STOP-03: device still pending → InvalidTransitionError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        now = datetime.now(timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        cycle = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        # sd2 still pending — try to confirm stop without start
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        # Must be in confirmed_start to call confirm_device_stop
        with pytest.raises(InvalidTransitionError):
            svc.confirm_device_stop(cycle.id, sd2.id, now, ccd2.revision)


# ── RF — report_device_failure ────────────────────────────────────────────────

class TestReportDeviceFailure:
    def test_rf_01_failure_from_pending(self, db, cycle_with_two_devices):
        """RF-01: device fails while pending → failure_reason stored."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        result = svc.report_device_failure(cycle.id, sd1.id, "camera crash", ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        assert CycleDeviceRecordingStatus(ccd1.recording_status) == CycleDeviceRecordingStatus.FAILED
        assert ccd1.failure_reason == "camera crash"

    def test_rf_02_all_fail_marks_cycle_failed(self, db, cycle_with_two_devices):
        """RF-02: all required devices fail → cycle transitions to FAILED."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.report_device_failure(cycle.id, sd1.id, "err1", ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        result = svc.report_device_failure(cycle.id, sd2.id, "err2", ccd2.revision)
        assert CycleStatus(result.status) == CycleStatus.FAILED
        assert result.result == "failed"

    def test_rf_03_terminal_cycle_raises(self, db, cycle_with_two_devices):
        """RF-03: reporting failure on ABORTED cycle raises InvalidTransitionError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.abort_cycle(cycle.id, cycle.revision, "manual abort")
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        with pytest.raises(InvalidTransitionError):
            svc.report_device_failure(cycle.id, sd1.id, "err", ccd1.revision)

    def test_rf_04_revision_conflict_raises(self, db, cycle_with_two_devices):
        """RF-04: wrong cycle_device revision raises RevisionConflictError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        with pytest.raises(RevisionConflictError):
            svc.report_device_failure(cycle.id, sd1.id, "err", 999)


# ── AC — abort_cycle ──────────────────────────────────────────────────────────

class TestAbortCycle:
    def test_ac_01_abort_from_preparing(self, db, cycle_with_two_devices):
        """AC-01: PREPARING → ABORTED."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        result = svc.abort_cycle(cycle.id, cycle.revision)
        assert CycleStatus(result.status) == CycleStatus.ABORTED

    def test_ac_02_abort_stores_reason(self, db, cycle_with_two_devices):
        """AC-02: abort with reason stores it on cycle."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        result = svc.abort_cycle(cycle.id, cycle.revision, "test abort reason")
        assert result.failure_reason == "test abort reason"

    def test_ac_03_abort_from_recording_pending(self, db, cycle_with_two_devices):
        """AC-03: RECORDING_PENDING → ABORTED."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        result = svc.abort_cycle(cycle.id, cycle.revision)
        assert CycleStatus(result.status) == CycleStatus.ABORTED

    def test_ac_04_abort_from_terminal_raises(self, db, cycle_with_two_devices):
        """AC-04: aborting already ABORTED cycle raises InvalidTransitionError."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.abort_cycle(cycle.id, cycle.revision)
        with pytest.raises(InvalidTransitionError):
            svc.abort_cycle(cycle.id, cycle.revision)


# ── FS — finalize_session ─────────────────────────────────────────────────────

class TestFinalizeSession:
    def test_fs_01_happy_path_no_cycles(self, db, active_session):
        """FS-01: ACTIVE session with no cycles → COMPLETED."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        result = svc.finalize_session(s.session_uuid, s.revision)
        assert SessionStatus(result.status) == SessionStatus.COMPLETED
        assert result.finalized_at is not None

    def test_fs_02_happy_path_with_completed_cycle(self, db, cycle_with_two_devices):
        """FS-02: ACTIVE session with ABORTED cycle → COMPLETED."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        svc.abort_cycle(cycle.id, cycle.revision)
        db.expire_all()
        s = svc._require_session(s.session_uuid)
        result = svc.finalize_session(s.session_uuid, s.revision)
        assert SessionStatus(result.status) == SessionStatus.COMPLETED

    def test_fs_03_non_terminal_cycle_blocks_finalize(self, db, cycle_with_two_devices):
        """FS-03: PREPARING cycle prevents finalization."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.finalize_session(s.session_uuid, s.revision)

    def test_fs_04_revision_conflict_raises(self, db, active_session):
        """FS-04: wrong session revision raises RevisionConflictError."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        with pytest.raises(RevisionConflictError):
            svc.finalize_session(s.session_uuid, s.revision + 99)

    def test_fs_05_non_active_session_raises(self, db, users):
        """FS-05: finalizing a LOBBY session raises InvalidTransitionError."""
        instructor, _ = users
        s = MultiCameraSession(created_by_user_id=instructor.id, status=SessionStatus.LOBBY.value)
        db.add(s)
        db.flush()
        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.finalize_session(s.session_uuid, s.revision)


# ── LC — list_cycles ──────────────────────────────────────────────────────────

class TestListCycles:
    def test_lc_01_empty_returns_empty_list(self, db, active_session):
        """LC-01: no cycles → empty list."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        result = svc.list_cycles(s.session_uuid)
        assert result == []

    def test_lc_02_returns_in_cycle_index_order(self, db, active_session):
        """LC-02: cycles returned ordered by cycle_index."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        c1 = svc.create_cycle(s.session_uuid, "lc-key-a", p_inst.id)
        c2 = svc.create_cycle(s.session_uuid, "lc-key-b", p_inst.id)
        result = svc.list_cycles(s.session_uuid)
        assert len(result) == 2
        assert result[0].cycle_index < result[1].cycle_index

    def test_lc_03_session_not_found_raises(self, db):
        """LC-03: non-existent session raises SessionNotFoundError."""
        svc = CycleService(db)
        with pytest.raises(SessionNotFoundError):
            svc.list_cycles(_uuid.uuid4())


# ── CM — completion logic ─────────────────────────────────────────────────────

class TestCycleCompletionLogic:
    def _make_recording_cycle(self, db, cycle_with_two_devices):
        """Helper: advance cycle all the way to RECORDING."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        now = datetime.now(timezone.utc)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.confirm_device_start(cycle.id, sd2.id, now, ccd2.revision)
        return cycle, sd1, sd2, svc

    def test_cm_01_partial_result_when_one_failed(self, db, cycle_with_two_devices):
        """CM-01: one device fails, one stops → result=partial."""
        cycle, sd1, sd2, svc = self._make_recording_cycle(db, cycle_with_two_devices)
        cycle = svc.stop_cycle(cycle.id, cycle.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        cycle = svc.report_device_failure(cycle.id, sd1.id, "crash", ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        now = datetime.now(timezone.utc)
        result = svc.confirm_device_stop(cycle.id, sd2.id, now, ccd2.revision)
        assert CycleStatus(result.status) == CycleStatus.COMPLETED
        assert result.result == "partial"

    def test_cm_02_success_when_all_stop(self, db, cycle_with_two_devices):
        """CM-02: both devices stop → result=success (covered by DS-STOP-02, verified here)."""
        cycle, sd1, sd2, svc = self._make_recording_cycle(db, cycle_with_two_devices)
        cycle = svc.stop_cycle(cycle.id, cycle.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        now = datetime.now(timezone.utc)
        cycle = svc.confirm_device_stop(cycle.id, sd1.id, now, ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        result = svc.confirm_device_stop(cycle.id, sd2.id, now, ccd2.revision)
        assert result.result == "success"

    def test_cm_03_failed_result_when_all_fail(self, db, cycle_with_two_devices):
        """CM-03: all devices fail → result=failed, status=FAILED."""
        cycle, sd1, sd2, p_inst, s = cycle_with_two_devices
        svc = CycleService(db)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd1 = next(d for d in cycle.cycle_devices if d.session_device_id == sd1.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        cycle = svc.report_device_failure(cycle.id, sd1.id, "err1", ccd1.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        ccd2 = next(d for d in cycle.cycle_devices if d.session_device_id == sd2.id)
        result = svc.report_device_failure(cycle.id, sd2.id, "err2", ccd2.revision)
        assert CycleStatus(result.status) == CycleStatus.FAILED
        assert result.result == "failed"

    def test_cm_04_auxiliary_device_not_counted_in_completion(self, db, active_session):
        """CM-04: auxiliary (non-required) failure does not trigger cycle completion."""
        s, p_inst, sd1, sd2 = active_session
        tag = _uuid.uuid4().hex[:8]
        md3 = ManagedDevice(owner_user_id=p_inst.user_id, device_type="gopro", device_name=f"G-{tag}")
        db.add(md3)
        db.flush()
        sd3 = SessionDevice(
            session_id=s.id, device_id=md3.id,
            managed_by_device_id=sd1.id,
            device_role="auxiliary_camera", status="ready",
        )
        db.add(sd3)
        db.flush()

        svc = CycleService(db)
        cycle = svc.create_cycle(s.session_uuid, "key-cm04", p_inst.id)
        cycle = svc.schedule_cycle(cycle.id, cycle.revision)
        db.expire_all()
        cycle = svc.get_cycle(cycle.id)
        # Fail the auxiliary camera — should not complete cycle
        ccd3 = next(d for d in cycle.cycle_devices if d.session_device_id == sd3.id)
        result = svc.report_device_failure(cycle.id, sd3.id, "aux fail", ccd3.revision)
        assert CycleStatus(result.status) == CycleStatus.RECORDING_PENDING


# ── TR — transition guards ────────────────────────────────────────────────────

class TestTransitionGuards:
    def test_tr_01_session_lobby_can_activate(self, db, users):
        """TR-01: SessionStatus LOBBY → ACTIVE via activate_session."""
        instructor, _ = users
        s = MultiCameraSession(
            created_by_user_id=instructor.id,
            status=SessionStatus.LOBBY.value,
        )
        db.add(s)
        db.flush()
        p = SessionParticipant(session_id=s.id, user_id=instructor.id, role="instructor")
        db.add(p)
        db.flush()

        svc = CycleService(db)
        result = svc.activate_session(s.session_uuid, s.revision)
        assert SessionStatus(result.status) == SessionStatus.ACTIVE

    def test_tr_02_activate_from_active_raises(self, db, active_session):
        """TR-02: already ACTIVE session → InvalidTransitionError on second activate."""
        s, p_inst, sd1, sd2 = active_session
        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.activate_session(s.session_uuid, s.revision)

    def test_tr_03_activate_from_completed_raises(self, db, users):
        """TR-03: COMPLETED session → InvalidTransitionError."""
        instructor, _ = users
        s = MultiCameraSession(created_by_user_id=instructor.id, status=SessionStatus.COMPLETED.value)
        db.add(s)
        db.flush()
        svc = CycleService(db)
        with pytest.raises(InvalidTransitionError):
            svc.activate_session(s.session_uuid, s.revision)


# ── Concurrent idempotency ────────────────────────────────────────────────────

class TestConcurrentIdempotency:
    def test_idem_concurrent_same_key(self):
        """IDEM-01: two concurrent create_cycle calls with same key → exactly one cycle created."""
        from app.database import SessionLocal
        import uuid as _u

        # Commit setup so worker threads can see it
        setup_db = SessionLocal()
        tag = _u.uuid4().hex[:8]
        try:
            instructor = User(
                name=f"ConcInst-{tag}",
                email=f"conc-inst-{tag}@test.com",
                password_hash="x",
                role=UserRole.INSTRUCTOR,
                is_active=True,
            )
            setup_db.add(instructor)
            setup_db.flush()

            s = MultiCameraSession(
                created_by_user_id=instructor.id,
                status=SessionStatus.ACTIVE.value,
            )
            setup_db.add(s)
            setup_db.flush()

            p = SessionParticipant(session_id=s.id, user_id=instructor.id, role="instructor")
            setup_db.add(p)
            setup_db.flush()

            md = ManagedDevice(owner_user_id=instructor.id, device_type="ipad", device_name=f"iPad-{tag}")
            setup_db.add(md)
            setup_db.flush()

            sd = SessionDevice(
                session_id=s.id, device_id=md.id, participant_id=p.id,
                device_role="instructor_primary", status="ready",
            )
            setup_db.add(sd)
            setup_db.flush()

            session_uuid = s.session_uuid
            participant_id = p.id
            session_id = s.id
            setup_db.commit()
        except Exception:
            setup_db.rollback()
            setup_db.close()
            raise

        setup_db.close()

        results = []
        errors = []

        def _create():
            worker_db = SessionLocal()
            try:
                svc = CycleService(worker_db)
                cycle = svc.create_cycle(session_uuid, "idem-concurrent-key", participant_id)
                results.append(cycle.id)
            except Exception as e:
                errors.append(e)
            finally:
                worker_db.close()

        t1 = threading.Thread(target=_create)
        t2 = threading.Thread(target=_create)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Cleanup
        cleanup_db = SessionLocal()
        try:
            from app.models.multicamera_session import CaptureCycleDevice as CCD, CaptureCycle as CC
            cleanup_db.query(CCD).filter(CCD.capture_cycle_id.in_(
                cleanup_db.query(CC.id).filter(CC.session_id == session_id)
            )).delete(synchronize_session=False)
            cleanup_db.query(CC).filter(CC.session_id == session_id).delete()
            cleanup_db.query(SessionDevice).filter(SessionDevice.session_id == session_id).delete()
            cleanup_db.query(SessionParticipant).filter(SessionParticipant.session_id == session_id).delete()
            cleanup_db.query(MultiCameraSession).filter(MultiCameraSession.id == session_id).delete()
            cleanup_db.commit()
        finally:
            cleanup_db.close()

        # Both calls should succeed (idempotency, not errors)
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 2
        # Both results should have a valid ID
        assert all(r is not None for r in results)
