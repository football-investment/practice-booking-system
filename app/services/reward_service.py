"""
Reward Service — session completion rewards (EventRewardLog).

Provides ``award_session_completion()`` which creates (or updates) an
EventRewardLog row when a user completes a session.

Design principles:
  - Idempotent: any number of calls for the same (user, session) is safe.
    ``INSERT … ON CONFLICT DO UPDATE`` + a unique constraint on
    (user_id, session_id) makes the upsert atomic under concurrent load.
  - Explicit transaction boundary: the execute+commit block is wrapped in
    try/except/rollback so DB errors leave no partial state.
  - Multiplier chain: base_xp from session_reward_config → multiplier_applied.
  - Decoupled from LicenseProgression (structural level changes stay separate).
  - Structured logging via ``app.core.structured_log`` for aggregation.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.metrics import metrics
from app.core.structured_log import log_debug, log_error, log_info
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

    Uses PostgreSQL ``INSERT … ON CONFLICT DO UPDATE`` so the upsert is
    atomic and safe under concurrent calls for the same (user_id, session_id).

    Transaction boundary: the execute + commit block is wrapped in
    try/except/rollback — any DB error rolls the transaction back cleanly
    before the exception propagates to the caller.

    XP priority:
      1. session.session_reward_config["base_xp"]        (per-session override)
      2. _DEFAULT_XP_BY_CATEGORY[session.event_category] (category default)
      3. session.base_xp                                  (legacy fallback)

    Returns the upserted EventRewardLog row (committed, freshly fetched).
    """
    base_xp = _resolve_base_xp(session)
    xp_earned = int(base_xp * multiplier)

    log_debug(
        _logger, "reward_computing",
        user_id=user_id, session_id=session.id,
        base_xp=base_xp, multiplier=multiplier, xp=xp_earned,
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

    try:
        db.execute(stmt)
        db.commit()
    except Exception as exc:
        db.rollback()
        metrics.increment("rewards_failed")
        log_error(
            _logger, "reward_failed",
            user_id=user_id, session_id=session.id,
            xp=xp_earned, error=repr(exc),
        )
        raise

    log = db.query(EventRewardLog).filter(
        EventRewardLog.user_id == user_id,
        EventRewardLog.session_id == session.id,
    ).one()

    metrics.increment("rewards_generated")
    log_info(
        _logger, "reward_awarded",
        user_id=user_id, session_id=session.id,
        xp=log.xp_earned, multiplier=multiplier, skill_areas=skill_areas,
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
