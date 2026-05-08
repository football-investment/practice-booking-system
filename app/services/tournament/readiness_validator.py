"""
Tournament Readiness Validator

Pre-transition content checks for CHECK_IN_OPEN and IN_PROGRESS.
These complement the status-graph and enrollment-count checks in
status_validator.py with content-level policy enforcement:
    - status_validator.py: valid transitions + instructor presence + enrollment count
    - readiness_validator.py (this file): schedule config + reward config presence

Called from lifecycle.py before the status flush so any 400 leaves
tournament_status unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.semester import Semester


@dataclass
class ReadinessResult:
    ok: bool
    blocking_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requirement_codes: list[str] = field(default_factory=list)


def check_pre_check_in_open(db: "Session", tournament: "Semester") -> ReadinessResult:
    """
    Validate content readiness before transitioning to CHECK_IN_OPEN.

    Policy:
    - match_duration_minutes, break_duration_minutes, parallel_fields must all
      be explicitly configured in TournamentConfiguration.  NULL values are NOT
      silently defaulted to 90 / 15 / 1 — the admin must make an explicit choice.
    - Valid ranges: match_duration > 0, break_duration >= 0, parallel_fields >= 1.
    """
    errors: list[str] = []
    codes: list[str] = []

    cfg = tournament.tournament_config_obj
    missing: list[str] = []

    if cfg is None or cfg.match_duration_minutes is None:
        missing.append("match_duration_minutes")
    if cfg is None or cfg.break_duration_minutes is None:
        missing.append("break_duration_minutes")
    if cfg is None or cfg.parallel_fields is None:
        missing.append("parallel_fields")

    if missing:
        errors.append(
            f"Schedule Configuration must be set before CHECK_IN_OPEN. "
            f"Missing: {', '.join(missing)}. "
            f"Configure via the Schedule Configuration section."
        )
        codes.append("SCHEDULE_CONFIG_MISSING")
    else:
        range_errs: list[str] = []
        if cfg.match_duration_minutes <= 0:
            range_errs.append("match_duration_minutes must be > 0")
        if cfg.break_duration_minutes < 0:
            range_errs.append("break_duration_minutes cannot be negative")
        if cfg.parallel_fields < 1:
            range_errs.append("parallel_fields must be >= 1")
        if range_errs:
            errors.extend(range_errs)
            codes.append("SCHEDULE_CONFIG_INVALID")

    return ReadinessResult(
        ok=not errors,
        blocking_errors=errors,
        warnings=[],
        requirement_codes=codes,
    )


def check_pre_in_progress(db: "Session", tournament: "Semester") -> ReadinessResult:
    """
    Validate content readiness before transitioning to IN_PROGRESS.

    Policy:
    - Reward configuration must be present (non-empty reward_config JSONB).
      A tournament entering IN_PROGRESS without reward config will never
      distribute XP or badges to participants.

    TODO (GAP-4 tech debt): Re-validate master instructor LFA_COACH eligibility.
    status_validator.py:168-186 checks instructor *presence* only; a license may
    expire between CHECK_IN_OPEN and IN_PROGRESS.  When addressed, call
    check_tournament_master_instructor_eligible(db, tournament.id) here and surface
    as a INSTRUCTOR_ELIGIBILITY_STALE blocking error with code "INSTRUCTOR_LICENSE_EXPIRED".
    """
    errors: list[str] = []
    codes: list[str] = []

    # tournament.reward_config property returns {} when reward_config_obj is None
    # or when reward_config_obj.reward_config is None/empty — both are falsy.
    if not tournament.reward_config:
        errors.append(
            "Reward Configuration is required before starting the tournament (IN_PROGRESS). "
            "Set a reward policy via the Reward Configuration section."
        )
        codes.append("REWARD_CONFIG_MISSING")

    return ReadinessResult(
        ok=not errors,
        blocking_errors=errors,
        warnings=[],
        requirement_codes=codes,
    )
