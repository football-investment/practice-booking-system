"""
Student specialization state service.

Single source of truth for the SpecState lifecycle:
    LOCKED    → no UserLicense exists for this spec
    PENDING   → license present but no activation signal → redirect to onboarding
    ACTIVE    → any activation signal present → "ENTER" CTA
    SUSPENDED → license is_active=False

Usage (enforcement points):
    from app.services.student_state_service import SpecState, resolve_spec_state

    # Pre-fetch enrolled_license_ids ONCE per request (N+1 prevention):
    enrolled_license_ids = {
        row[0]
        for row in db.query(SemesterEnrollment.user_license_id)
        .filter(
            SemesterEnrollment.user_id == user.id,
            SemesterEnrollment.user_license_id.isnot(None),
        )
        .all()
    }

    state = resolve_spec_state(license, enrolled_license_ids)
    if state != SpecState.ACTIVE:
        raise HTTPException(400, "Complete onboarding first.")
"""
from enum import Enum
from typing import Optional, FrozenSet, Set


class SpecState(str, Enum):
    LOCKED    = "LOCKED"     # no UserLicense
    PENDING   = "PENDING"    # license + no activation signal → "Continue Setup"
    ACTIVE    = "ACTIVE"     # any activation signal → "ENTER"
    SUSPENDED = "SUSPENDED"  # license.is_active = False


def resolve_spec_state(
    license,  # Optional[UserLicense] — avoid circular import with string annotation
    enrolled_license_ids: Set[int] = frozenset(),
) -> SpecState:
    """Canonical spec state resolver.

    Activation signals (any one is sufficient):
      1. license.onboarding_completed is True  — explicit flag from onboarding form
      2. license.football_skills is not None   — LFA baseline data present
      3. license.id in enrolled_license_ids    — legacy compat: enrolled before guard existed;
                                                  NOT circular because enrollment requires
                                                  onboarding for new users

    Args:
        license: UserLicense ORM object or None.
        enrolled_license_ids: Pre-fetched set of license IDs that have at least one
            SemesterEnrollment. Must be populated by the caller to avoid N+1 queries.

    Returns:
        SpecState enum value.
    """
    if license is None:
        return SpecState.LOCKED

    if not license.is_active:
        return SpecState.SUSPENDED

    effective = (
        license.onboarding_completed
        or (license.football_skills is not None)
        or (license.id in enrolled_license_ids)
    )
    return SpecState.ACTIVE if effective else SpecState.PENDING
