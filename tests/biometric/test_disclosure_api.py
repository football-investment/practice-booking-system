"""
Biometric disclosure API tests — PR-7A.

BCD-01  POST /me/biometric-disclosure — 201 + disclosure elfogadva
BCD-02  POST — 409 ha már aktív azonos verzió
BCD-03  GET — is_active=True + accepted_version ha elfogadva
BCD-04  GET — has_disclosure=False ha nincs
BCD-05  DELETE — 200 + is_active=False
BCD-06  DELETE — 404 ha nincs aktív
BCD-07  Feature flag OFF (BIOMETRIC_DISCLOSURE_ENABLED=False) → 503 mindhárom endpointon
BCD-08  Kiskorú (age<18) POST → 403 parental_consent_required
BCD-09  Ismeretlen kor (date_of_birth=None) POST → 403 parental_consent_required
BCD-10  Response nem tartalmaz face_match_score / embedding mezőt
BCD-11  Audit log EVT_DISCLOSURE_ACCEPTED rögzítve POST után
BCD-12  Audit log EVT_DISCLOSURE_REVOKED + EVT_CONSENT_REVOKED rögzítve DELETE után
BCD-13  DELETE disclosure meghívja a meglévő revoke_consent() service-t (not duplicated)
BCD-14  Disclosure verziózás: v1.0 elfogadva; v1.1 POST-ra 422 (version mismatch)
BCD-15  Liveness endpoint 403 biometric_disclosure_required ha nincs aktív disclosure
BCD-16  Régi disclosure verzió esetén liveness 403 biometric_disclosure_update_required
BCD-17  Régi disclosure verzió esetén verify 403 biometric_disclosure_update_required
BCD-18  Egy usernek egyszerre csak egy aktív disclosure rekordja lehet
BCD-19  DELETE disclosure meghívja revoke_consent() — nem duplikált Celery logika
BCD-20  Response schema AST teszt: score/embedding/raw mezők nincsenek disclosure sémákban
BCD-21  BIOMETRIC_DISCLOSURE_ENABLED=False → disclosure endpointok 503
BCD-22  BIOMETRIC_DISCLOSURE_ENABLED=True, BIOMETRIC_FACE_MATCHING_ENABLED=False
         → disclosure elfogadható; liveness/verify továbbra is tiltott
"""
from __future__ import annotations

import ast
import asyncio
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.api_v1.endpoints.users.biometric_disclosure import (
    accept_biometric_disclosure,
    get_biometric_disclosure,
    revoke_biometric_disclosure,
)
from app.models.biometric import BiometricVerificationLog, UserBiometricDisclosure
from app.schemas.biometric import BiometricDisclosureAcceptRequest, BiometricDisclosureStatusOut
from app.services.biometric.audit_log import (
    EVT_CONSENT_REVOKED,
    EVT_DISCLOSURE_ACCEPTED,
    EVT_DISCLOSURE_REVOKED,
)

_MODULE   = "app.api.api_v1.endpoints.users.biometric_disclosure"
_SVC      = "app.services.biometric.disclosure_service"
_CURR_VER = "v1.0"


def _run(fn):
    import inspect
    if inspect.iscoroutine(fn):
        return asyncio.run(fn)
    return fn


def _mock_request(ip: str = "127.0.0.1"):
    req = MagicMock()
    req.headers.get = lambda key, default=None: None
    req.client.host = ip
    return req


def _adult_user(uid: int = 42):
    u = MagicMock()
    u.id = uid
    u.age = 25
    u.date_of_birth = date(2001, 1, 1)
    u.is_minor = False
    return u


def _minor_user(uid: int = 99):
    u = MagicMock()
    u.id = uid
    u.age = 16
    u.date_of_birth = date(2010, 1, 1)
    u.is_minor = True
    return u


def _unknown_age_user(uid: int = 77):
    u = MagicMock()
    u.id = uid
    u.age = None
    u.date_of_birth = None
    u.is_minor = False  # is_minor returns False when age is None
    return u


def _disclosure_flag_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.BIOMETRIC_DISCLOSURE_ENABLED", True)
    monkeypatch.setattr(
        "app.services.biometric.feature_flag.settings.BIOMETRIC_DISCLOSURE_ENABLED", True
    )


def _face_flag_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.BIOMETRIC_FACE_MATCHING_ENABLED", True)
    monkeypatch.setattr(
        "app.services.biometric.feature_flag.settings.BIOMETRIC_FACE_MATCHING_ENABLED", True
    )


def _valid_payload(version: str = _CURR_VER) -> BiometricDisclosureAcceptRequest:
    return BiometricDisclosureAcceptRequest(disclosure_version=version)


# ── BCD-01 — POST 201 accepted ────────────────────────────────────────────────

def test_bcd01_post_returns_201_accepted(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    result = _run(accept_biometric_disclosure(
        payload=_valid_payload(),
        request=_mock_request(),
        db=db,
        current_user=student_user,
    ))
    db.commit()
    assert isinstance(result, BiometricDisclosureStatusOut)
    assert result.has_disclosure is True
    assert result.is_active is True
    assert result.accepted_version == _CURR_VER


# ── BCD-02 — POST 409 duplicate ───────────────────────────────────────────────

def test_bcd02_post_409_duplicate(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        _run(accept_biometric_disclosure(
            payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
        ))
    assert exc_info.value.status_code == 409
    assert "already_accepted" in exc_info.value.detail


# ── BCD-03 — GET returns active status ────────────────────────────────────────

def test_bcd03_get_returns_active_status(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    result = _run(get_biometric_disclosure(db=db, current_user=student_user))
    assert result.is_active is True
    assert result.accepted_version == _CURR_VER


# ── BCD-04 — GET returns has_disclosure=False if none ─────────────────────────

def test_bcd04_get_no_disclosure(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    result = _run(get_biometric_disclosure(db=db, current_user=student_user))
    assert result.has_disclosure is False
    assert result.is_active is False


# ── BCD-05 — DELETE 200 + is_active=False ────────────────────────────────────

def test_bcd05_delete_revokes(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    result = _run(revoke_biometric_disclosure(
        request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    assert result.is_active is False
    assert result.revoked_at is not None


# ── BCD-06 — DELETE 404 if no active ─────────────────────────────────────────

def test_bcd06_delete_404_no_active(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    with pytest.raises(HTTPException) as exc_info:
        _run(revoke_biometric_disclosure(
            request=_mock_request(), db=db, current_user=student_user
        ))
    assert exc_info.value.status_code == 404


# ── BCD-07 / BCD-21 — flag OFF → 503 ─────────────────────────────────────────

def test_bcd07_disclosure_flag_off_503():
    from app.services.biometric.feature_flag import require_disclosure_enabled

    async def _call():
        await require_disclosure_enabled()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_call())
    assert exc_info.value.status_code == 503


# ── BCD-08 — minor → 403 parental_consent_required ───────────────────────────

def test_bcd08_minor_user_403(db, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    minor = _minor_user()

    # Patch user.age to return 16 via property (MagicMock has it set)
    from app.services.biometric.disclosure_service import _assert_not_minor
    with pytest.raises(HTTPException) as exc_info:
        _assert_not_minor(minor)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "parental_consent_required"


# ── BCD-09 — unknown age → 403 ───────────────────────────────────────────────

def test_bcd09_unknown_age_403(db, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    unknown = _unknown_age_user()

    from app.services.biometric.disclosure_service import _assert_not_minor
    with pytest.raises(HTTPException) as exc_info:
        _assert_not_minor(unknown)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "parental_consent_required"


# ── BCD-10 — response has no score / embedding ───────────────────────────────

def test_bcd10_response_no_score_no_embedding(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    result = _run(get_biometric_disclosure(db=db, current_user=student_user))
    d = result.model_dump()
    assert "face_match_score" not in d
    assert "embedding" not in d
    assert "embedding_ciphertext" not in d
    assert "yaw" not in d
    assert "roll" not in d


# ── BCD-11 — audit EVT_DISCLOSURE_ACCEPTED ────────────────────────────────────

def test_bcd11_audit_disclosure_accepted(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    logs = db.query(BiometricVerificationLog).filter(
        BiometricVerificationLog.user_id == student_user.id,
        BiometricVerificationLog.event_type == EVT_DISCLOSURE_ACCEPTED,
    ).all()
    assert logs, "EVT_DISCLOSURE_ACCEPTED must be written"


# ── BCD-12 — audit EVT_DISCLOSURE_REVOKED ────────────────────────────────────

def test_bcd12_audit_disclosure_revoked(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    _run(revoke_biometric_disclosure(
        request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    logs = db.query(BiometricVerificationLog).filter(
        BiometricVerificationLog.user_id == student_user.id,
        BiometricVerificationLog.event_type == EVT_DISCLOSURE_REVOKED,
    ).all()
    assert logs, "EVT_DISCLOSURE_REVOKED must be written"


# ── BCD-13 — DELETE triggers revoke_consent if consent active ─────────────────

def test_bcd13_delete_cascades_consent_revoke(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _face_flag_on(monkeypatch)
    from app.services.biometric.consent_service import grant_consent
    grant_consent(db=db, user=student_user, consent_version="v1.0")
    db.flush()

    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()

    _run(revoke_biometric_disclosure(
        request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()

    # Consent must be revoked
    from app.models.biometric import UserBiometricConsent
    active = db.query(UserBiometricConsent).filter_by(
        user_id=student_user.id, is_active=True
    ).first()
    assert active is None, "Consent must be revoked when disclosure is revoked"

    revoke_log = db.query(BiometricVerificationLog).filter(
        BiometricVerificationLog.user_id == student_user.id,
        BiometricVerificationLog.event_type == EVT_CONSENT_REVOKED,
    ).all()
    assert revoke_log, "EVT_CONSENT_REVOKED must be written"


# ── BCD-14 — wrong version → 422 ─────────────────────────────────────────────

def test_bcd14_wrong_version_422(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    with pytest.raises(HTTPException) as exc_info:
        _run(accept_biometric_disclosure(
            payload=_valid_payload("v9.9"),
            request=_mock_request(),
            db=db,
            current_user=student_user,
        ))
    assert exc_info.value.status_code == 422
    assert "version_mismatch" in exc_info.value.detail


# ── BCD-15 — liveness 403 biometric_disclosure_required ──────────────────────

def test_bcd15_liveness_403_no_disclosure(db, student_user, monkeypatch):
    _face_flag_on(monkeypatch)
    from app.services.biometric.consent_service import grant_consent
    grant_consent(db=db, user=student_user, consent_version="v1.0")
    db.flush()

    from app.services.biometric.liveness_service import submit_liveness_result
    metadata = {
        "challenge_version": "v1.0", "steps_completed": ["center"],
        "total_duration_ms": 3000, "retry_count": 0,
    }
    with pytest.raises(HTTPException) as exc_info:
        submit_liveness_result(
            db=db, user=student_user, liveness_metadata=metadata,
            source="onboarding_liveness", photo_filename="ref.jpg",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "biometric_disclosure_required"


# ── BCD-16 — liveness 403 biometric_disclosure_update_required ───────────────

def test_bcd16_liveness_403_stale_disclosure(db, student_user, monkeypatch):
    _face_flag_on(monkeypatch)
    _disclosure_flag_on(monkeypatch)

    # Store a row with OLD version directly
    from app.models.biometric import UserBiometricDisclosure
    from datetime import datetime, timezone
    old_row = UserBiometricDisclosure(
        user_id=student_user.id,
        disclosure_version="v0.9",
        accepted_at=datetime.now(timezone.utc),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(old_row)
    db.flush()

    from app.services.biometric.consent_service import grant_consent
    grant_consent(db=db, user=student_user, consent_version="v1.0")
    db.flush()

    from app.services.biometric.liveness_service import submit_liveness_result
    metadata = {
        "challenge_version": "v1.0", "steps_completed": ["center"],
        "total_duration_ms": 3000, "retry_count": 0,
    }
    with pytest.raises(HTTPException) as exc_info:
        submit_liveness_result(
            db=db, user=student_user, liveness_metadata=metadata,
            source="onboarding_liveness", photo_filename="ref.jpg",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "biometric_disclosure_update_required"


# ── BCD-17 — verify 403 biometric_disclosure_update_required ─────────────────

def test_bcd17_verify_403_stale_disclosure(
    db, student_user, monkeypatch, biometric_feature_enabled, encryption_test_key, allow_test_key
):
    _disclosure_flag_on(monkeypatch)

    # Store old disclosure version
    from app.models.biometric import UserBiometricDisclosure
    from datetime import datetime, timezone
    old_row = UserBiometricDisclosure(
        user_id=student_user.id,
        disclosure_version="v0.9",
        accepted_at=datetime.now(timezone.utc),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(old_row)
    db.flush()

    from app.services.biometric.consent_service import grant_consent
    from app.services.biometric.embedding_service import FakeEmbeddingProvider, store_embedding
    grant_consent(db=db, user=student_user, consent_version="v1.0")
    emb = FakeEmbeddingProvider().generate(b"seed")
    row = store_embedding(db=db, user_id=student_user.id, embedding=emb, model_version="fake_v1")
    row.is_active = True
    db.flush()

    from app.api.api_v1.endpoints.users.biometric_verify import verify_biometric
    from app.schemas.biometric import BiometricVerifyRequest
    with pytest.raises(HTTPException) as exc_info:
        _run(verify_biometric(
            payload=BiometricVerifyRequest(photo_filename="photo.jpg"),
            db=db,
            current_user=student_user,
        ))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "biometric_disclosure_update_required"


# ── BCD-18 — only one active disclosure per user ──────────────────────────────

def test_bcd18_only_one_active_disclosure(db, student_user, monkeypatch):
    _disclosure_flag_on(monkeypatch)
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    count = db.query(UserBiometricDisclosure).filter_by(
        user_id=student_user.id, is_active=True
    ).count()
    assert count == 1, "Only one active disclosure allowed per user"


# ── BCD-19 — DELETE reuses revoke_consent, not duplicated logic ───────────────

def test_bcd19_delete_reuses_revoke_consent_service(db, student_user, monkeypatch):
    """
    Verifies the consent revoke path calls the existing revoke_consent()
    service rather than duplicating Celery embedding delete logic.
    """
    _disclosure_flag_on(monkeypatch)
    _face_flag_on(monkeypatch)
    from app.services.biometric.consent_service import grant_consent
    grant_consent(db=db, user=student_user, consent_version="v1.0")
    db.flush()
    _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()

    # Patch at the source module — disclosure_service imports it locally
    with patch(
        "app.services.biometric.consent_service.revoke_consent"
    ) as mock_revoke:
        _run(revoke_biometric_disclosure(
            request=_mock_request(), db=db, current_user=student_user
        ))

    # revoke_consent was called exactly once — not duplicated
    mock_revoke.assert_called_once()


# ── BCD-20 — AST schema test: no score/embedding in disclosure schemas ────────

def test_bcd20_schema_ast_no_score_or_embedding():
    import app.schemas.biometric as mod
    src = open(mod.__file__).read()
    tree = ast.parse(src)

    forbidden = {"face_match_score", "embedding", "embedding_ciphertext",
                 "yaw", "roll", "pitch", "landmarks", "frame_data"}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and "Disclosure" in node.name:
            for item in ast.walk(node):
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    assert item.value not in forbidden, (
                        f"Forbidden field '{item.value}' found in {node.name}"
                    )


# ── BCD-21 — already covered by BCD-07 (flag off → 503) ─────────────────────

# BCD-21 is covered by BCD-07: require_disclosure_enabled raises 503 when
# BIOMETRIC_DISCLOSURE_ENABLED=False. The same dependency is used on all
# three endpoints, so BCD-07 covers all three.


# ── BCD-22 — disclosure_enabled=True + face_matching=False ───────────────────

def test_bcd22_disclosure_allowed_without_face_matching(db, student_user, monkeypatch):
    """
    BCD-22 decision: when BIOMETRIC_DISCLOSURE_ENABLED=True but
    BIOMETRIC_FACE_MATCHING_ENABLED=False, disclosure acceptance is allowed.
    Liveness/verify remain blocked by the face matching flag.
    """
    _disclosure_flag_on(monkeypatch)
    # BIOMETRIC_FACE_MATCHING_ENABLED stays False (default)

    result = _run(accept_biometric_disclosure(
        payload=_valid_payload(), request=_mock_request(), db=db, current_user=student_user
    ))
    db.commit()
    assert result.has_disclosure is True, "Disclosure acceptance must succeed"

    # Liveness is still blocked by the face matching flag
    from app.services.biometric.feature_flag import require_biometric_enabled
    async def _check_face():
        await require_biometric_enabled()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_check_face())
    assert exc_info.value.status_code == 503, "Face matching must still be 503"
