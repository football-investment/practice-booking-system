"""
Reward Service — session completion rewards (EventRewardLog).

Provides `award_session_completion()` which creates (or updates) an
EventRewardLog row when a user completes a session.

Design principles:
  - Idempotent: calling any number of times for the same (user, session) is safe.
    The unique constraint on (user_id, session_id) plus PostgreSQL's
    INSERT … ON CONFLICT DO UPDATE makes the upsert atomic — concurrent calls
    cannot produce duplicate rows.
  - Multiplier chain: base_xp from session_reward_config → multiplier_applied.
  - Decoupled from LicenseProgression (structural level changes stay separate).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.event_reward_log import EventRewardLog
from app.models.session import Session as SessionModel, EventCategory

_logger = logging.getLogger(__name__)

_DEFAULT_XP_BY_CATEGORY: dict[str, int] = {
    EventCategory.MATCH.value: 100,
    EventCategory.TRAINING.value: 50,
}


def award_session_completion(
    db: Session,
    user_id: int,
    session: SessionModel,
    multiplier: float = 1.0,
    skill_areas: Optional[list[str]] = None,
) -> EventRewardLog:
    """
    Create or update an EventRewardLog for a user completing a session.

    Uses PostgreSQL INSERT … ON CONFLICT DO UPDATE so the operation is atomic
    and safe under concurrent calls for the same (user_id, session_id) pair.

    XP priority:
      1. session.session_reward_config["base_xp"]   (explicit per-session config)
      2. _DEFAULT_XP_BY_CATEGORY[session.event_category]  (category default)
      3. session.base_xp                              (legacy xp field fallback)

    Returns the upserted EventRewardLog row (committed).
    """
    base_xp = _resolve_base_xp(session)
    xp_earned = int(base_xp * multiplier)

    _logger.debug(
        "award_session_completion user=%d session=%d base_xp=%d multiplier=%.2f xp=%d",
        user_id, session.id, base_xp, multiplier, xp_earned,
    )

    stmt = (
        pg_insert(EventRewardLog)
        .values(
            user_id=user_id,
            session_id=session.id,
            xp_earned=xp_earned,
            points_earned=xp_earned,      # 1:1 default; override in caller if needed
            skill_areas_affected=skill_areas,
            multiplier_applied=multiplier,
        )
        .on_conflict_do_update(
            constraint="uq_event_reward_log_user_session",
            set_=dict(
                xp_earned=xp_earned,
                points_earned=xp_earned,
                skill_areas_affected=skill_areas,
                multiplier_applied=multiplier,
            ),
        )
    )
    db.execute(stmt)
    db.commit()

    log = db.query(EventRewardLog).filter(
        EventRewardLog.user_id == user_id,
        EventRewardLog.session_id == session.id,
    ).one()

    _logger.info(
        "reward_awarded user=%d session=%d xp=%d multiplier=%.2f skill_areas=%r",
        user_id, session.id, log.xp_earned, multiplier, skill_areas,
    )
    return log


def _resolve_base_xp(session: SessionModel) -> int:
    """Determine base XP for a session using priority order."""
    # Priority 1: explicit per-session config
    if session.session_reward_config and isinstance(session.session_reward_config, dict):
        cfg_xp = session.session_reward_config.get("base_xp")
        if cfg_xp is not None:
            return int(cfg_xp)

    # Priority 2: category default
    if session.event_category is not None:
        cat_xp = _DEFAULT_XP_BY_CATEGORY.get(session.event_category.value)
        if cat_xp is not None:
            return cat_xp

    # Priority 3: legacy field
    if session.base_xp is not None:
        return int(session.base_xp)

    return 50  # ultimate fallback
