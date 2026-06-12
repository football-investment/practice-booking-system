"""
Biometric reference photo upload endpoint — PR-2.

POST /me/biometric-photo
  Accepts a multipart/form-data JPEG or PNG (max 5 MB).
  Stores the image in app/uploads/biometric/<user_id>/ (not web-accessible).
  Returns the server-generated filename for use in submitLiveness(photo_filename=…).

Gates (all must pass):
  - Bearer auth (get_current_user)
  - BIOMETRIC_FACE_MATCHING_ENABLED = true
  - Active biometric disclosure (assert_disclosure_current)
  - Active biometric consent (UserBiometricConsent.is_active = true)
  - MIME whitelist: image/jpeg, image/png
  - Max 5 MB
  - Rate limit: shared with LIVENESS_SUBMIT group (3 / 600 s)

Not KYC. Not production-ready. DPIA / DPO approval pending.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.api_v1.endpoints.users.biometric_consent import _extract_ip
from app.database import get_db
from app.dependencies import get_current_user
from app.models.biometric import UserBiometricConsent
from app.models.user import User
from app.services.biometric.audit_log import BiometricAuditLogger, EVT_REFERENCE_SUBMITTED
from app.services.biometric.disclosure_service import assert_disclosure_current
from app.services.biometric.feature_flag import require_biometric_enabled
from app.services.biometric.photo_upload_service import (
    BiometricPhotoMimeRejected,
    BiometricPhotoTooLarge,
    save_biometric_photo,
)

router = APIRouter()

_MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB


class BiometricPhotoUploadResponse(BaseModel):
    """Response for POST /me/biometric-photo."""
    photo_filename: str


@router.post(
    "/me/biometric-photo",
    status_code=status.HTTP_201_CREATED,
    response_model=BiometricPhotoUploadResponse,
    dependencies=[Depends(require_biometric_enabled)],
    summary="Upload biometric liveness reference photo",
)
async def upload_biometric_photo(
    request:      Request,
    photo:        UploadFile = File(..., description="JPEG or PNG, max 5 MB"),
    db:           Session    = Depends(get_db),
    current_user: User       = Depends(get_current_user),
) -> Any:
    """
    Upload the reference photo captured at the end of the liveness challenge.

    - MIME must be image/jpeg or image/png (422 otherwise).
    - File must not exceed 5 MB (422 otherwise).
    - Requires active biometric disclosure and consent (403 otherwise).
    - Returns photo_filename (server-generated basename) for use in
      POST /me/biometric-liveness { photo_filename: "..." }.
    - face_match_score is never read, written, or returned here.
    - Image bytes are written to disk only; not stored in DB.
    """
    from app.services.biometric.rate_limiter import enforce_rate_limit, LIVENESS_SUBMIT

    _ip = _extract_ip(request)

    # ── Rate limit (shared with liveness submit) ───────────────────────────────
    enforce_rate_limit(
        endpoint_group=LIVENESS_SUBMIT,
        user_id=current_user.id,
        ip=_ip,
        db=db,
        audit_user_id=current_user.id,
    )

    # ── Disclosure check ───────────────────────────────────────────────────────
    assert_disclosure_current(db=db, user_id=current_user.id)

    # ── Consent check ──────────────────────────────────────────────────────────
    active_consent = (
        db.query(UserBiometricConsent)
        .filter(
            UserBiometricConsent.user_id == current_user.id,
            UserBiometricConsent.is_active.is_(True),
        )
        .first()
    )
    if not active_consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="biometric_consent_required",
        )

    # ── Read file bytes (enforce size limit before disk write) ─────────────────
    try:
        file_bytes = await photo.read(_MAX_CONTENT_LENGTH + 1)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="biometric_photo_read_error",
        ) from exc

    # ── Delegate to service (MIME + size validation + disk write) ─────────────
    try:
        filename = save_biometric_photo(
            user_id=current_user.id,
            file_bytes=file_bytes,
            content_type=photo.content_type or "",
        )
    except BiometricPhotoMimeRejected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="biometric_photo_mime_rejected",
        )
    except BiometricPhotoTooLarge:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="biometric_photo_too_large",
        )
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="biometric_photo_storage_error",
        ) from exc

    # ── Audit log ──────────────────────────────────────────────────────────────
    BiometricAuditLogger(db).log(
        user_id=current_user.id,
        event_type=EVT_REFERENCE_SUBMITTED,
        event_result="uploaded",
        photo_filename=filename,
        actor_ip_address=_ip,
    )
    db.commit()

    return BiometricPhotoUploadResponse(photo_filename=filename)
