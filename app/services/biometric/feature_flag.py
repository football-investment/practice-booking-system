"""
Biometric feature flag guards.

Two separate flags with distinct scopes:

  BIOMETRIC_DISCLOSURE_ENABLED      — PR-7A disclosure/modal endpoints
    503 when False. Allows disclosure UI roll-out before full face matching.

  BIOMETRIC_FACE_MATCHING_ENABLED   — liveness, embedding, verify endpoints
    503 when False. Requires DPIA + legal sign-off before setting True.

Design: the two flags are independent. A user can accept the disclosure
(DISCLOSURE_ENABLED=True) before face matching is activated, so the UI
can present the tájékoztató modal ahead of the feature launch.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.config import settings


def is_biometric_enabled() -> bool:
    """Return True when the face matching feature flag is on."""
    return settings.BIOMETRIC_FACE_MATCHING_ENABLED


def is_disclosure_enabled() -> bool:
    """Return True when the disclosure/modal feature flag is on."""
    return settings.BIOMETRIC_DISCLOSURE_ENABLED


async def require_biometric_enabled() -> None:
    """
    FastAPI dependency — raises 503 when face matching feature is disabled.
    Used by: consent, liveness, verify endpoints.
    """
    if not is_biometric_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Biometric face matching is not enabled on this server. "
                "Set BIOMETRIC_FACE_MATCHING_ENABLED=true after completing "
                "DPIA and obtaining legal approval."
            ),
        )


async def require_disclosure_enabled() -> None:
    """
    FastAPI dependency — raises 503 when disclosure feature is disabled.
    Used by: GET/POST/DELETE /me/biometric-disclosure endpoints.

    Separate from require_biometric_enabled: disclosure can be enabled
    independently to allow the tájékoztató modal to be shown before the
    full face matching pipeline is activated.
    """
    if not is_disclosure_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Biometric disclosure is not enabled on this server. "
                "Set BIOMETRIC_DISCLOSURE_ENABLED=true to activate the "
                "disclosure/consent modal endpoints."
            ),
        )
