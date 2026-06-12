"""
Biometric photo upload endpoint tests — PR-2.

BPH-01  POST /me/biometric-photo — JPEG, valid size → 201, photo_filename returned
BPH-02  PNG upload → 201, photo_filename returned
BPH-03  GIF upload → 422 biometric_photo_mime_rejected
BPH-04  File exceeds 5 MB → 422 biometric_photo_too_large
BPH-05  No active disclosure → 403 biometric_disclosure_required
BPH-06  No active consent → 403 biometric_consent_required
BPH-07  Unauthenticated (no current_user) → raises if dependency fails
BPH-08  Rate limit: 4th call within window → 429 rate_limited (in-memory store)
BPH-09  Response never contains face_match_score, embedding, or raw sensor data
BPH-10  photo_filename in response is a plain basename (no path separators)
BPH-11  photo_filename is server-generated UUID — client cannot influence it
BPH-12  Audit log EVT_REFERENCE_SUBMITTED written on success
"""
from __future__ import annotations

import asyncio
import io
from unittest.mock import MagicMock, patch

import pytest

from app.api.api_v1.endpoints.users.biometric_photo import upload_biometric_photo
from app.models.biometric import BiometricVerificationLog
from app.services.biometric.audit_log import EVT_REFERENCE_SUBMITTED

_ENDPOINT  = "app.api.api_v1.endpoints.users.biometric_photo"
_SVC       = "app.services.biometric.photo_upload_service"
# Patch target for save_biometric_photo inside the endpoint module
_SAVE_FN   = f"{_ENDPOINT}.save_biometric_photo"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _mock_request(ip: str = "127.0.0.1"):
    req = MagicMock()
    req.headers.get = lambda key, default=None: {
        "x-forwarded-for": None,
        "x-real-ip":       None,
    }.get(key, default)
    req.client.host = ip
    return req


def _make_upload_file(content: bytes, content_type: str, filename: str = "test.jpg"):
    """Return a FastAPI UploadFile-like mock."""
    import asyncio
    uf = MagicMock()
    uf.content_type = content_type
    uf.filename     = filename

    async def _read(n=-1):
        return content if n == -1 or n > len(content) else content[:n]

    uf.read = _read
    return uf


def _small_jpeg() -> bytes:
    """Return minimal valid JPEG bytes (8×8 pixel solid colour)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _small_png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 100, 50)).save(buf, format="PNG")
    return buf.getvalue()


def _large_bytes() -> bytes:
    """Return 5 MB + 1 byte of zeros (exceeds limit)."""
    return b"\x00" * (5 * 1024 * 1024 + 1)


def _grant_consent(db, user):
    from app.services.biometric.consent_service import grant_consent
    grant_consent(db=db, user=user, consent_version="v1.0")


def _grant_disclosure(db, user):
    from app.services.biometric.disclosure_service import accept_disclosure
    accept_disclosure(db=db, user=user, disclosure_version="v1.0")


def _setup_user_with_consent(db, user):
    _grant_disclosure(db, user)
    _grant_consent(db, user)


# ── BPH-01: JPEG success ───────────────────────────────────────────────────────

class TestBiometricPhotoUploadSuccess:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_jpeg_201(self, db, student_user):
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(_small_jpeg(), "image/jpeg")
        result = _run(upload_biometric_photo(
            request=_mock_request(),
            photo=photo,
            db=db,
            current_user=student_user,
        ))
        assert hasattr(result, "photo_filename")
        assert result.photo_filename  # non-empty

    # BPH-02
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_png_201(self, db, student_user):
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(_small_png(), "image/png", "test.png")
        result = _run(upload_biometric_photo(
            request=_mock_request(),
            photo=photo,
            db=db,
            current_user=student_user,
        ))
        assert result.photo_filename.endswith(".png")

    # BPH-09: No forbidden fields in response
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_response_no_forbidden_fields(self, db, student_user):
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(_small_jpeg(), "image/jpeg")
        result = _run(upload_biometric_photo(
            request=_mock_request(),
            photo=photo,
            db=db,
            current_user=student_user,
        ))
        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
        forbidden = {"face_match_score", "embedding", "embedding_ciphertext",
                     "yaw", "roll", "pitch", "landmarks"}
        assert forbidden.isdisjoint(result_dict.keys())

    # BPH-10: photo_filename is a plain basename
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_photo_filename_is_basename(self, db, student_user):
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(_small_jpeg(), "image/jpeg")
        import os
        result = _run(upload_biometric_photo(
            request=_mock_request(),
            photo=photo,
            db=db,
            current_user=student_user,
        ))
        assert os.path.basename(result.photo_filename) == result.photo_filename

    # BPH-11: client cannot influence filename (UUID-based)
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_filename_server_generated(self, db, student_user):
        _setup_user_with_consent(db, student_user)
        # Upload twice with same content — filenames must differ (UUID)
        results = []
        for _ in range(2):
            photo = _make_upload_file(_small_jpeg(), "image/jpeg", "attacker.jpg")
            r = _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))
            results.append(r.photo_filename)
        assert results[0] != results[1]
        # Neither should contain "attacker"
        for fn in results:
            assert "attacker" not in fn


# ── BPH-03: MIME rejected ─────────────────────────────────────────────────────

class TestBiometricPhotoMimeRejected:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_gif_422(self, db, student_user):
        from fastapi import HTTPException
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(b"GIF89a...", "image/gif", "test.gif")
        with pytest.raises(HTTPException) as exc_info:
            _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))
        assert exc_info.value.status_code == 422
        assert "mime_rejected" in exc_info.value.detail

    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_webp_422(self, db, student_user):
        from fastapi import HTTPException
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(b"RIFF...", "image/webp", "test.webp")
        with pytest.raises(HTTPException) as exc_info:
            _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))
        assert exc_info.value.status_code == 422


# ── BPH-04: File too large ────────────────────────────────────────────────────

class TestBiometricPhotoTooLarge:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_over_5mb_422(self, db, student_user):
        from fastapi import HTTPException
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(_large_bytes(), "image/jpeg")
        with pytest.raises(HTTPException) as exc_info:
            _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))
        assert exc_info.value.status_code == 422
        assert "too_large" in exc_info.value.detail


# ── BPH-05: No disclosure ─────────────────────────────────────────────────────

class TestBiometricPhotoDisclosureGate:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_no_disclosure_403(self, db, student_user):
        from fastapi import HTTPException
        # Only consent, no disclosure
        _grant_consent(db, student_user)
        photo = _make_upload_file(_small_jpeg(), "image/jpeg")
        with pytest.raises(HTTPException) as exc_info:
            _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))
        assert exc_info.value.status_code == 403
        assert "disclosure" in exc_info.value.detail


# ── BPH-06: No consent ────────────────────────────────────────────────────────

class TestBiometricPhotoConsentGate:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_no_consent_403(self, db, student_user):
        from fastapi import HTTPException
        # Only disclosure, no consent
        _grant_disclosure(db, student_user)
        photo = _make_upload_file(_small_jpeg(), "image/jpeg")
        with pytest.raises(HTTPException) as exc_info:
            _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "biometric_consent_required"


# ── BPH-08: Rate limiting ─────────────────────────────────────────────────────

class TestBiometricPhotoRateLimit:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_rate_limit_429(self, db, student_user):
        from fastapi import HTTPException
        _setup_user_with_consent(db, student_user)

        call_count = 0

        def _limited_save(**kwargs):
            nonlocal call_count
            call_count += 1
            return f"biometric_{student_user.id}_test{call_count:03d}.jpg"

        with patch(_SAVE_FN, side_effect=_limited_save):
            # First 3 calls should succeed (LIVENESS_SUBMIT limit = 3/600s)
            for i in range(3):
                photo = _make_upload_file(_small_jpeg(), "image/jpeg")
                _run(upload_biometric_photo(
                    request=_mock_request(),
                    photo=photo,
                    db=db,
                    current_user=student_user,
                ))

            # 4th call should be rate-limited
            photo = _make_upload_file(_small_jpeg(), "image/jpeg")
            with pytest.raises(HTTPException) as exc_info:
                _run(upload_biometric_photo(
                    request=_mock_request(),
                    photo=photo,
                    db=db,
                    current_user=student_user,
                ))
            assert exc_info.value.status_code == 429


# ── BPH-12: Audit log ────────────────────────────────────────────────────────

class TestBiometricPhotoAuditLog:
    @pytest.mark.usefixtures("biometric_feature_enabled")
    def test_audit_log_written(self, db, student_user):
        _setup_user_with_consent(db, student_user)
        photo = _make_upload_file(_small_jpeg(), "image/jpeg")

        with patch(_SAVE_FN, return_value="biometric_1_abc.jpg"):
            _run(upload_biometric_photo(
                request=_mock_request(),
                photo=photo,
                db=db,
                current_user=student_user,
            ))

        logs = (
            db.query(BiometricVerificationLog)
            .filter_by(user_id=student_user.id, event_type=EVT_REFERENCE_SUBMITTED)
            .all()
        )
        assert len(logs) >= 1
        assert logs[-1].photo_filename == "biometric_1_abc.jpg"
        # Verify face_match_score is not stored (audit log column is separate)
        assert logs[-1].face_match_score is None


# ── photo_upload_service unit tests ──────────────────────────────────────────

class TestPhotoUploadService:
    def test_save_biometric_photo_jpeg(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        data = _small_jpeg()
        fn = svc.save_biometric_photo(user_id=42, file_bytes=data, content_type="image/jpeg")
        assert fn.startswith("biometric_42_")
        assert fn.endswith(".jpg")
        assert (tmp_path / "42" / fn).exists()

    def test_save_biometric_photo_png(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        fn = svc.save_biometric_photo(user_id=7, file_bytes=_small_png(), content_type="image/png")
        assert fn.endswith(".png")

    def test_mime_rejected(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        from app.services.biometric.photo_upload_service import BiometricPhotoMimeRejected
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        with pytest.raises(BiometricPhotoMimeRejected):
            svc.save_biometric_photo(user_id=1, file_bytes=b"...", content_type="image/gif")

    def test_too_large(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        from app.services.biometric.photo_upload_service import BiometricPhotoTooLarge
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        with pytest.raises(BiometricPhotoTooLarge):
            svc.save_biometric_photo(user_id=1, file_bytes=big, content_type="image/jpeg")

    def test_delete_biometric_photos(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        # Create two files
        svc.save_biometric_photo(user_id=5, file_bytes=_small_jpeg(), content_type="image/jpeg")
        svc.save_biometric_photo(user_id=5, file_bytes=_small_jpeg(), content_type="image/jpeg")
        deleted = svc.delete_biometric_photos_for_user(user_id=5)
        assert deleted == 2
        assert not (tmp_path / "5").exists()

    def test_get_photo_path_path_traversal_guard(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        result = svc.get_biometric_photo_path(user_id=1, filename="../etc/passwd")
        assert result is None

    def test_get_photo_path_not_found(self, tmp_path, monkeypatch):
        from app.services.biometric import photo_upload_service as svc
        monkeypatch.setattr(svc, "_BIOMETRIC_UPLOAD_ROOT", tmp_path)
        result = svc.get_biometric_photo_path(user_id=1, filename="nonexistent.jpg")
        assert result is None
