"""
Unified Onboarding Service
==========================

Single authoritative point for marking a license as onboarding-complete.

Per-spec completion definition
-------------------------------
LFA_FOOTBALL_PLAYER:
    Completed by POST /specialization/lfa-player/onboarding-web (cookie auth)
    or POST /specialization/lfa-player/onboarding-submit (Bearer auth).
    Requires: position, goals, motivation, all 29 skill values (0–100).
    Effect: populates license.football_skills in rich format,
            sets license.onboarding_completed + onboarding_completed_at,
            sets user.onboarding_completed.

All other specializations:
    Completed by POST /specialization/motivation-submit (cookie auth).
    Requires: form submission of the motivation questionnaire.
    Effect: sets license.onboarding_completed + onboarding_completed_at,
            sets user.onboarding_completed.

Caller contract
---------------
Both functions do NOT call db.commit().  The caller owns the transaction.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from ..models.license import UserLicense
from ..models.user import User


def complete_lfa_player_onboarding(
    db: Session,
    user: User,
    license: UserLicense,
    football_skills: Dict[str, Any],
) -> None:
    """
    Mark LFA Football Player onboarding as complete.

    Only called from:
    - POST /specialization/lfa-player/onboarding-web  (cookie auth)
    - POST /specialization/lfa-player/onboarding-submit  (Bearer auth)

    The football_skills dict must already be in rich format
    (keys = all 29 skill keys, values = dicts with baseline/current_level/…).
    """
    now = datetime.now(timezone.utc)
    license.football_skills = football_skills
    license.onboarding_completed = True
    license.onboarding_completed_at = now
    user.onboarding_completed = True


def complete_motivation_onboarding(
    db: Session,
    user: User,
    license: UserLicense,
) -> None:
    """
    Mark motivation-questionnaire onboarding as complete (non-LFA specializations).

    Only called from:
    - POST /specialization/motivation-submit  (cookie auth)
    """
    now = datetime.now(timezone.utc)
    license.onboarding_completed = True
    license.onboarding_completed_at = now
    user.onboarding_completed = True
