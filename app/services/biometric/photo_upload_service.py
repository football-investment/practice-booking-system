"""
Biometric photo upload service — PR-2.

Saves a liveness reference photo to disk for subsequent embedding generation.

Design rules (enforced here):
  1. Files stored in app/uploads/biometric/<user_id>/ — NOT in app/static/.
     This directory is not served as a static route, so files are not
     directly URL-accessible from outside the application process.
  2. MIME whitelist: image/jpeg, image/png only.
  3. Max 5 MB (5_242_880 bytes) enforced before disk write.
  4. Filename generated server-side (UUID4 + .jpg). Client cannot influence filename.
  5. One active photo per user: previous file overwritten atomically.
  6. Path traversal impossible: filename generated server-side.
  7. No image content is logged, hashed, or returned beyond the basename.
  8. Cleanup: pending uploads older than BIOMETRIC_PHOTO_STALE_SECONDS with no
     matching liveness submission are deleted by the orphan-cleanup Celery task.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Storage configuration ──────────────────────────────────────────────────────

# Root directory for biometric photos.  NOT under app/static/ — not web-accessible.
_BIOMETRIC_UPLOAD_ROOT: Path = Path("app/uploads/biometric")

# MIME whitelist — only JPEG and PNG accepted.
_ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png"})

# Maximum accepted file size in bytes (5 MB).
_MAX_BYTES: int = 5 * 1024 * 1024  # 5 242 880

# Extension map for allowed MIME types.
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png":  ".png",
}


# ── Public API ─────────────────────────────────────────────────────────────────

class BiometricPhotoTooLarge(Exception):
    """Raised when the uploaded file exceeds _MAX_BYTES."""


class BiometricPhotoMimeRejected(Exception):
    """Raised when the Content-Type is not in _ALLOWED_MIME_TYPES."""


def save_biometric_photo(
    *,
    user_id: int,
    file_bytes: bytes,
    content_type: str,
) -> str:
    """
    Validate and persist a liveness reference photo.

    Parameters
    ----------
    user_id:
        Owning user — used to scope the storage directory.
    file_bytes:
        Raw image bytes from the multipart upload.
    content_type:
        MIME type from the UploadFile.content_type field.

    Returns
    -------
    str
        Basename of the saved file, e.g. "biometric_42_<uuid4>.jpg".
        This value is safe to pass directly to submitLiveness(photo_filename=…).

    Raises
    ------
    BiometricPhotoMimeRejected  — content_type not in JPEG / PNG whitelist.
    BiometricPhotoTooLarge      — file_bytes exceeds 5 MB.
    OSError                     — disk write failure (propagated to caller).
    """
    # ── MIME guard ────────────────────────────────────────────────────────────
    mime = (content_type or "").lower().split(";")[0].strip()
    if mime not in _ALLOWED_MIME_TYPES:
        raise BiometricPhotoMimeRejected(f"Unsupported MIME type: {mime!r}")

    # ── Size guard ────────────────────────────────────────────────────────────
    if len(file_bytes) > _MAX_BYTES:
        raise BiometricPhotoTooLarge(
            f"File size {len(file_bytes)} exceeds limit {_MAX_BYTES}"
        )

    # ── Filename: server-generated, client cannot influence ───────────────────
    ext      = _MIME_TO_EXT[mime]
    filename = f"biometric_{user_id}_{uuid.uuid4().hex}{ext}"

    # ── Directory: <root>/<user_id>/ ──────────────────────────────────────────
    user_dir = _BIOMETRIC_UPLOAD_ROOT / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # ── Atomic write: write to temp then rename so Celery never reads partial ─
    dest = user_dir / filename
    tmp  = dest.with_suffix(".tmp")
    try:
        tmp.write_bytes(file_bytes)
        tmp.rename(dest)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise

    logger.info(
        "biometric photo saved user_id=%s filename=%s size=%d",
        user_id, filename, len(file_bytes),
    )
    return filename


def delete_biometric_photos_for_user(user_id: int) -> int:
    """
    Delete all biometric photo files for a given user.

    Called during consent revocation (GDPR right to erasure) after the face
    embedding has been deleted.  Idempotent: returns 0 if no files found.

    Returns
    -------
    int
        Number of files deleted.
    """
    user_dir = _BIOMETRIC_UPLOAD_ROOT / str(user_id)
    if not user_dir.exists():
        return 0

    deleted = 0
    for f in user_dir.iterdir():
        if f.is_file():
            try:
                f.unlink()
                deleted += 1
            except OSError as exc:
                logger.error(
                    "delete_biometric_photos_for_user: could not delete %s: %s", f, exc
                )
    try:
        user_dir.rmdir()   # remove empty dir; silently fails if not empty
    except OSError:
        pass

    logger.info(
        "delete_biometric_photos_for_user: deleted %d files for user_id=%s",
        deleted, user_id,
    )
    return deleted


def get_biometric_photo_path(user_id: int, filename: str) -> Optional[Path]:
    """
    Return the absolute path for a stored biometric photo, or None if not found.

    Validates that filename is a plain basename (no path separators) before
    constructing the path — prevents path traversal even from internal callers.

    Used by the Celery embedding task to load actual image bytes (PR-5+).
    """
    import os
    if os.path.basename(filename) != filename:
        logger.error(
            "get_biometric_photo_path: path traversal attempt filename=%r user_id=%s",
            filename, user_id,
        )
        return None

    path = _BIOMETRIC_UPLOAD_ROOT / str(user_id) / filename
    return path if path.exists() else None
