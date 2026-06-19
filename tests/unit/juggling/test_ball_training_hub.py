"""
Global Ball Training Hub tests — BTH-01..BTH-15.

Coverage:
  BTH-01  Queue returns assignment_id only — no video_id, frame_ms, storage_path
  BTH-02  assignment_id is a valid UUID
  BTH-03  Cross-user assignment access → 404 (no info-leak)
  BTH-04  Expired assignment submit → 410
  BTH-05  Consumed assignment (second submit) → 409
  BTH-06  Non-existent assignment UUID → 404
  BTH-07  Valid confirm submit → 201, feedback row created, assignment consumed
  BTH-08  Valid no_ball submit → 201, correct decision persisted
  BTH-09  corrected decision → 422 (deferred to PR-1B)
  BTH-10  Queue excludes frames without training_consent (consent gate)
  BTH-11  Queue excludes user's own video frames
  BTH-12  Idempotent queue — two requests return same assignment for same frame
  BTH-13  Frame capacity: 4 sequential submits, 4 different users → 3 succeed, 1 gets 409
  BTH-14  Consent revoke after assignment issued → submit returns 403
  BTH-15  Consensus task skipped when training_consent revoked (BTH-CC-01)

FastAPI TestClient + PostgreSQL savepoint for full DB isolation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, select
from sqlalchemy.orm import sessionmaker

from app.core.auth import create_access_token
from app.database import engine, get_db
from app.main import app
from app.models.juggling import (
    BallTrainingAssignment,
    JugglingBallFeedback,
    JugglingBallTrajectory,
    JugglingConsent,
    JugglingFrameGroundTruth,
    JugglingVideo,
    JugglingVideoStatus,
)
from app.models.user import User, UserRole
from app.services.juggling import feature_flag as ff_module
import app.api.api_v1.endpoints.users.juggling_ball_training as hub_module
from app.tasks.juggling_feedback_task import run_compute_frame_consensus


# ── DB fixture (savepoint pattern) ───────────────────────────────────────────

@pytest.fixture()
def db():
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSession()
    connection.begin_nested()

    @sa_event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, txn):
        if txn.nested and not txn._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(db, suffix: str = "", role: UserRole = UserRole.STUDENT) -> User:
    u = User(
        email=f"bth_{suffix}_{uuid.uuid4().hex[:6]}@test.com",
        name="BTH User",
        password_hash="x",
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_video(db, owner: User, status: str = "analyzed") -> JugglingVideo:
    v = JugglingVideo(
        user_id=owner.id,
        source_type="in_app_capture",
        upload_source="camera",
        status=status,
        storage_path=f"/tmp/v_{uuid.uuid4().hex}.mp4",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _make_consent(db, user: User, training: bool = True) -> JugglingConsent:
    c = JugglingConsent(
        user_id=user.id,
        service_consent=True,
        training_consent=training,
        admin_review_consent=False,
        consented_at=datetime.now(timezone.utc),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_trajectory(
    db,
    video: JugglingVideo,
    frame_ms: int = 1000,
    confidence: float = 0.5,
    tracking_state: str = "detected",
) -> JugglingBallTrajectory:
    t = JugglingBallTrajectory(
        video_id=video.id,
        frame_ms=frame_ms,
        ball_x=0.5,
        ball_y=0.4,
        confidence=confidence,
        tracking_state=tracking_state,
        image_width_px=1920,
        image_height_px=1080,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_assignment(
    db,
    user: User,
    video: JugglingVideo,
    frame_ms: int = 1000,
    expires_delta: timedelta = timedelta(hours=1),
    consumed_at: datetime | None = None,
) -> BallTrainingAssignment:
    now = datetime.now(timezone.utc)
    a = BallTrainingAssignment(
        user_id=user.id,
        video_id=video.id,
        frame_ms=frame_ms,
        expires_at=now + expires_delta,
        consumed_at=consumed_at,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _auth(user: User) -> dict:
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _flags_on(monkeypatch):
    monkeypatch.setattr(ff_module, "is_juggling_enabled", lambda: True)
    monkeypatch.setattr(hub_module.settings, "BALL_FEEDBACK_ENABLED", True)


# ── BTH-01: Queue response contains no privacy-sensitive fields ───────────────

def test_bth_01_queue_response_no_private_fields(db, client, monkeypatch):
    _flags_on(monkeypatch)
    reviewer = _make_user(db, "reviewer", UserRole.ADMIN)
    owner = _make_user(db, "owner")
    video = _make_video(db, owner)
    _make_consent(db, owner, training=True)
    _make_trajectory(db, video, frame_ms=1000, confidence=0.4)

    resp = client.get(
        "/api/v1/users/me/ball-training/queue",
        headers=_auth(reviewer),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "tasks" in data

    for task in data["tasks"]:
        assert "video_id" not in task
        assert "frame_ms" not in task
        assert "storage_path" not in task
        assert "assignment_id" in task


# ── BTH-02: assignment_id is a valid UUID ─────────────────────────────────────

def test_bth_02_assignment_id_is_uuid(db, client, monkeypatch):
    _flags_on(monkeypatch)
    reviewer = _make_user(db, "rev2", UserRole.ADMIN)
    owner = _make_user(db, "ow2")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=2000)

    resp = client.get("/api/v1/users/me/ball-training/queue", headers=_auth(reviewer))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    for task in data["tasks"]:
        aid = task["assignment_id"]
        parsed = uuid.UUID(aid)
        assert parsed.version == 4


# ── BTH-03: Cross-user assignment → 404 (no info-leak) ───────────────────────

def test_bth_03_cross_user_assignment_404(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user_a = _make_user(db, "a3", UserRole.ADMIN)
    user_b = _make_user(db, "b3", UserRole.ADMIN)
    owner = _make_user(db, "ow3")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=3000)

    # Create assignment belonging to user_a
    assignment = _make_assignment(db, user_a, video, frame_ms=3000)

    # user_b tries to submit with user_a's assignment_id
    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(assignment.id), "decision": "confirm"},
        headers=_auth(user_b),
    )
    assert resp.status_code == 404
    # Response must not reveal ownership info
    assert "user" not in resp.text.lower() or "not found" in resp.text.lower()


# ── BTH-04: Expired assignment → 410 ─────────────────────────────────────────

def test_bth_04_expired_assignment_410(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u4", UserRole.ADMIN)
    owner = _make_user(db, "ow4")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=4000)

    assignment = _make_assignment(
        db, user, video, frame_ms=4000,
        expires_delta=timedelta(seconds=-1),  # already expired
    )

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(assignment.id), "decision": "confirm"},
        headers=_auth(user),
    )
    assert resp.status_code == 410


# ── BTH-05: Second submit on same assignment → 409 ───────────────────────────

def test_bth_05_consumed_assignment_409(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u5", UserRole.ADMIN)
    owner = _make_user(db, "ow5")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=5000)

    assignment = _make_assignment(
        db, user, video, frame_ms=5000,
        consumed_at=datetime.now(timezone.utc),  # already consumed
    )

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(assignment.id), "decision": "no_ball"},
        headers=_auth(user),
    )
    assert resp.status_code == 409


# ── BTH-06: Non-existent assignment_id → 404 ─────────────────────────────────

def test_bth_06_nonexistent_assignment_404(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u6", UserRole.ADMIN)

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(uuid.uuid4()), "decision": "confirm"},
        headers=_auth(user),
    )
    assert resp.status_code == 404


# ── BTH-07: Valid confirm submit → 201, feedback persisted, assignment consumed

def test_bth_07_valid_confirm_submit(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u7", UserRole.ADMIN)
    owner = _make_user(db, "ow7")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=7000)

    assignment = _make_assignment(db, user, video, frame_ms=7000)

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(assignment.id), "decision": "confirm"},
        headers=_auth(user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["decision"] == "confirm"
    assert str(data["assignment_id"]) == str(assignment.id)

    # Verify feedback row created
    fb = db.execute(
        select(JugglingBallFeedback).where(
            JugglingBallFeedback.video_id == video.id,
            JugglingBallFeedback.frame_ms == 7000,
            JugglingBallFeedback.user_id == user.id,
        )
    ).scalar_one_or_none()
    assert fb is not None
    assert fb.decision == "confirm"

    # Verify assignment consumed
    db.refresh(assignment)
    assert assignment.consumed_at is not None


# ── BTH-08: Valid no_ball submit → 201, correct decision ─────────────────────

def test_bth_08_valid_no_ball_submit(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u8", UserRole.ADMIN)
    owner = _make_user(db, "ow8")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=8000)

    assignment = _make_assignment(db, user, video, frame_ms=8000)

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(assignment.id), "decision": "no_ball"},
        headers=_auth(user),
    )
    assert resp.status_code == 201
    assert resp.json()["decision"] == "no_ball"


# ── BTH-09: corrected decision → 422 (deferred to PR-1B) ────────────────────

def test_bth_09_corrected_decision_422(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u9", UserRole.ADMIN)
    owner = _make_user(db, "ow9")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=9000)
    assignment = _make_assignment(db, user, video, frame_ms=9000)

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={
            "assignment_id": str(assignment.id),
            "decision": "corrected",
            "corrected_x": 0.5,
            "corrected_y": 0.4,
        },
        headers=_auth(user),
    )
    assert resp.status_code == 422


# ── BTH-10: Queue excludes frames without training_consent ───────────────────

def test_bth_10_queue_excludes_no_consent(db, client, monkeypatch):
    _flags_on(monkeypatch)
    reviewer = _make_user(db, "rev10", UserRole.ADMIN)
    owner_no = _make_user(db, "ow10_no")
    owner_yes = _make_user(db, "ow10_yes")

    video_no = _make_video(db, owner_no)
    video_yes = _make_video(db, owner_yes)

    _make_consent(db, owner_no, training=False)
    _make_consent(db, owner_yes, training=True)

    _make_trajectory(db, video_no, frame_ms=10001, confidence=0.1)  # high priority
    _make_trajectory(db, video_yes, frame_ms=10002, confidence=0.9)  # lower priority

    resp = client.get("/api/v1/users/me/ball-training/queue", headers=_auth(reviewer))
    assert resp.status_code == 200, resp.text

    # Verify: no assignment was created for video_no's frame (non-consented).
    # We check the DB directly — the client-visible response never contains video_id.
    bad_assignment = db.execute(
        select(BallTrainingAssignment).where(
            BallTrainingAssignment.user_id == reviewer.id,
            BallTrainingAssignment.video_id == video_no.id,
            BallTrainingAssignment.consumed_at.is_(None),
        )
    ).scalar_one_or_none()
    assert bad_assignment is None, (
        "Queue created an assignment for a non-consented video"
    )


# ── BTH-11: Queue excludes user's own video frames ───────────────────────────

def test_bth_11_queue_excludes_own_videos(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u11", UserRole.ADMIN)
    other = _make_user(db, "ow11")

    own_video = _make_video(db, user)
    other_video = _make_video(db, other)

    _make_consent(db, user, training=True)
    _make_consent(db, other, training=True)

    _make_trajectory(db, own_video, frame_ms=11001, confidence=0.1)
    _make_trajectory(db, other_video, frame_ms=11002, confidence=0.9)

    resp = client.get("/api/v1/users/me/ball-training/queue", headers=_auth(user))
    assert resp.status_code == 200, resp.text

    # Verify: no assignment was created for the user's own video's frame.
    bad = db.execute(
        select(BallTrainingAssignment).where(
            BallTrainingAssignment.user_id == user.id,
            BallTrainingAssignment.video_id == own_video.id,
            BallTrainingAssignment.consumed_at.is_(None),
        )
    ).scalar_one_or_none()
    assert bad is None, "Queue created an assignment for the user's own video"


# ── BTH-12: Idempotent assignment creation — same UUID returned on repeat call ─

def test_bth_12_idempotent_assignment_creation(db):
    """Two calls to _get_or_create_assignment for the same (user, video, frame)
    return the identical assignment_id. Exactly one active row exists in the DB.

    Tests the advisory-lock + check-before-create mechanism directly at the
    service level, independent of queue priority ordering.
    """
    from app.services.juggling.ball_training_service import _get_or_create_assignment

    reviewer = _make_user(db, "rev12")
    owner = _make_user(db, "ow12")
    video = _make_video(db, owner)

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)

    a1 = _get_or_create_assignment(db, reviewer.id, video.id, 12000, expires, now)
    db.flush()

    a2 = _get_or_create_assignment(db, reviewer.id, video.id, 12000, expires, now)

    assert a1.id == a2.id, (
        f"Idempotency violation: same frame returned different IDs: {a1.id} != {a2.id}"
    )

    active = db.execute(
        select(BallTrainingAssignment).where(
            BallTrainingAssignment.user_id == reviewer.id,
            BallTrainingAssignment.video_id == video.id,
            BallTrainingAssignment.frame_ms == 12000,
            BallTrainingAssignment.consumed_at.is_(None),
        )
    ).scalars().all()
    assert len(active) == 1, f"Expected 1 active assignment, found {len(active)}"


# ── BTH-13: Frame capacity — 4 sequential submits, 4 users → 3 succeed ───────

def test_bth_13_frame_capacity_three_max(db, client, monkeypatch):
    _flags_on(monkeypatch)
    owner = _make_user(db, "ow13")
    video = _make_video(db, owner)
    _make_consent(db, owner)
    _make_trajectory(db, video, frame_ms=13000)

    users = [_make_user(db, f"u13_{i}", UserRole.ADMIN) for i in range(4)]
    assignments = [_make_assignment(db, u, video, frame_ms=13000) for u in users]

    results = []
    for user, assignment in zip(users, assignments):
        resp = client.post(
            "/api/v1/users/me/ball-training/feedback",
            json={"assignment_id": str(assignment.id), "decision": "confirm"},
            headers=_auth(user),
        )
        results.append(resp.status_code)

    success_count = results.count(201)
    conflict_count = results.count(409)

    assert success_count == 3, f"Expected 3 successes, got {results}"
    assert conflict_count == 1, f"Expected 1 conflict (409), got {results}"

    # Verify exactly 3 feedback rows in DB
    total_fb = db.execute(
        select(JugglingBallFeedback).where(
            JugglingBallFeedback.video_id == video.id,
            JugglingBallFeedback.frame_ms == 13000,
        )
    ).scalars().all()
    assert len(total_fb) == 3, f"Expected 3 feedback rows, found {len(total_fb)}"


# ── BTH-14: Consent revoke after assignment issued → 403 ─────────────────────

def test_bth_14_consent_revoke_blocks_submit(db, client, monkeypatch):
    _flags_on(monkeypatch)
    user = _make_user(db, "u14", UserRole.ADMIN)
    owner = _make_user(db, "ow14")
    video = _make_video(db, owner)
    consent = _make_consent(db, owner, training=True)
    _make_trajectory(db, video, frame_ms=14000)

    assignment = _make_assignment(db, user, video, frame_ms=14000)

    # Revoke consent after assignment was issued
    consent.training_consent = False
    db.commit()

    resp = client.post(
        "/api/v1/users/me/ball-training/feedback",
        json={"assignment_id": str(assignment.id), "decision": "confirm"},
        headers=_auth(user),
    )
    assert resp.status_code == 403

    # Assignment must NOT be consumed (so user can retry if consent is re-granted)
    db.refresh(assignment)
    assert assignment.consumed_at is None


# ── BTH-15: Consensus skipped when training_consent revoked ──────────────────

def test_bth_15_consensus_skipped_on_revoke(db):
    owner = _make_user(db, "ow15")
    video = _make_video(db, owner)
    consent = _make_consent(db, owner, training=True)
    _make_trajectory(db, video, frame_ms=15000)

    # Insert a feedback row directly (simulating prior submission)
    fb = JugglingBallFeedback(
        video_id=video.id,
        frame_ms=15000,
        user_id=owner.id,
        decision="confirm",
        approval_state="pending",
        spam_flags=[],
    )
    db.add(fb)
    db.commit()

    # Revoke consent before running consensus
    consent.training_consent = False
    db.commit()

    # run_compute_frame_consensus should bail out without creating a GT row
    run_compute_frame_consensus(db, str(video.id), 15000)

    gt = db.execute(
        select(JugglingFrameGroundTruth).where(
            JugglingFrameGroundTruth.video_id == video.id,
            JugglingFrameGroundTruth.frame_ms == 15000,
        )
    ).scalar_one_or_none()
    assert gt is None, "GT row must not be created when training_consent is revoked"


# ── BTH-16: Feature flag off → 503 ───────────────────────────────────────────

def test_bth_16_flag_off_503(db, client, monkeypatch):
    monkeypatch.setattr(ff_module, "is_juggling_enabled", lambda: True)
    monkeypatch.setattr(hub_module.settings, "BALL_FEEDBACK_ENABLED", False)

    user = _make_user(db, "u16", UserRole.ADMIN)
    resp = client.get("/api/v1/users/me/ball-training/queue", headers=_auth(user))
    assert resp.status_code == 503


# ── BTH-17: Non-allowlisted student → 403 ────────────────────────────────────

def test_bth_17_non_allowlisted_student_403(db, client, monkeypatch):
    _flags_on(monkeypatch)
    monkeypatch.setattr(hub_module.settings, "BALL_TRAINING_ALLOWED_USER_IDS", "")

    student = _make_user(db, "stu17", UserRole.STUDENT)
    resp = client.get("/api/v1/users/me/ball-training/queue", headers=_auth(student))
    assert resp.status_code == 403


# ── BTH-18: Allowlisted student → 200 ────────────────────────────────────────

def test_bth_18_allowlisted_student_200(db, client, monkeypatch):
    _flags_on(monkeypatch)
    owner = _make_user(db, "ow18")
    student = _make_user(db, "stu18", UserRole.STUDENT)
    _make_consent(db, owner)
    video = _make_video(db, owner)
    _make_trajectory(db, video, frame_ms=18000)

    monkeypatch.setattr(
        hub_module.settings,
        "BALL_TRAINING_ALLOWED_USER_IDS",
        str(student.id),
    )

    resp = client.get("/api/v1/users/me/ball-training/queue", headers=_auth(student))
    assert resp.status_code == 200
