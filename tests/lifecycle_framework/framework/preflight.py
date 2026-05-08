"""Preflight checker and hidden dependency registry.

HiddenDependencyRegistry documents invariants that are NOT enforced by the
public API (or enforced only at a late stage), so scenario authors know what
to set up before calling lifecycle transitions.

PreflightChecker runs auto-checkable entries against the live DB/API and
raises PreflightError with actionable messages on failure.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from ._http import PreflightError


class Severity(Enum):
    CRITICAL = "CRITICAL"   # will cause the scenario to fail mid-flight
    WARNING = "WARNING"     # may cause partial failure; scenario may still run
    INFO = "INFO"           # documentation only


class DetectionMode(Enum):
    AUTO = "AUTO"           # check_fn is available; PreflightChecker will run it
    MANUAL = "MANUAL"       # must be verified by the scenario author


@dataclass
class HiddenDependency:
    name: str
    description: str
    severity: Severity
    detection_mode: DetectionMode
    # Returns (ok: bool, detail: str). Only required when detection_mode=AUTO.
    check_fn: Optional[Callable[[], tuple[bool, str]]] = None
    remediation: str = ""

    def __post_init__(self) -> None:
        if self.detection_mode == DetectionMode.AUTO and self.check_fn is None:
            raise ValueError(
                f"HiddenDependency '{self.name}' has AUTO detection but no check_fn"
            )


class HiddenDependencyRegistry:
    """Catalogue of non-obvious preconditions for lifecycle scenarios."""

    def __init__(self) -> None:
        self._entries: list[HiddenDependency] = []

    def register(self, dep: HiddenDependency) -> None:
        self._entries.append(dep)

    def all_auto(self) -> list[HiddenDependency]:
        return [d for d in self._entries if d.detection_mode == DetectionMode.AUTO]

    def all_manual(self) -> list[HiddenDependency]:
        return [d for d in self._entries if d.detection_mode == DetectionMode.MANUAL]


# ── Required coach level per age group (mirrors instructor_eligibility_service.py) ──
_AGE_GROUP_REQUIRED_LEVEL: dict[str, int] = {
    "PRE": 1,
    "YOUTH": 3,
    "AMATEUR": 5,
    "PRO": 7,
}


def _check_instructor_lfa_coach(
    instructor_email: str,
) -> Callable[[], tuple[bool, str]]:
    def _check() -> tuple[bool, str]:
        from app.database import SessionLocal
        from app.models.user import User as UserModel
        from app.models.license import UserLicense

        db = SessionLocal()
        try:
            user = db.query(UserModel).filter(UserModel.email == instructor_email).first()
            if not user:
                return False, f"{instructor_email} not in DB"
            lic = (
                db.query(UserLicense)
                .filter(
                    UserLicense.user_id == user.id,
                    UserLicense.specialization_type == "LFA_COACH",
                    UserLicense.is_active == True,  # noqa: E712
                )
                .first()
            )
            if not lic:
                return False, f"{instructor_email} has no active LFA_COACH license"
            return True, f"LFA_COACH level={lic.current_level}"
        finally:
            db.close()

    return _check


def _check_instructor_level(
    instructor_email: str,
    age_group: str,
) -> Callable[[], tuple[bool, str]]:
    required = _AGE_GROUP_REQUIRED_LEVEL.get(age_group.upper(), 0)

    def _check() -> tuple[bool, str]:
        from app.database import SessionLocal
        from app.models.user import User as UserModel
        from app.models.license import UserLicense

        db = SessionLocal()
        try:
            user = db.query(UserModel).filter(UserModel.email == instructor_email).first()
            if not user:
                return False, f"{instructor_email} not in DB"
            lic = (
                db.query(UserLicense)
                .filter(
                    UserLicense.user_id == user.id,
                    UserLicense.specialization_type == "LFA_COACH",
                    UserLicense.is_active == True,  # noqa: E712
                )
                .first()
            )
            if not lic:
                return False, "no active LFA_COACH license"
            if lic.current_level >= required:
                return True, f"level={lic.current_level} ≥ required={required} for {age_group}"
            return (
                False,
                f"level={lic.current_level} < required={required} for {age_group}",
            )
        finally:
            db.close()

    return _check


def _check_active_campus() -> Callable[[], tuple[bool, str]]:
    def _check() -> tuple[bool, str]:
        from app.database import SessionLocal
        from app.models.campus import Campus

        db = SessionLocal()
        try:
            count = db.query(Campus).filter(Campus.is_active == True).count()  # noqa: E712
            if count > 0:
                return True, f"{count} active campus(es)"
            return False, "no active campuses — run bootstrap_clean.py"
        finally:
            db.close()

    return _check


def _check_active_pitch() -> Callable[[], tuple[bool, str]]:
    def _check() -> tuple[bool, str]:
        try:
            from app.database import SessionLocal
            from app.models.pitch import Pitch

            db = SessionLocal()
            try:
                count = db.query(Pitch).filter(Pitch.is_active == True).count()  # noqa: E712
                if count > 0:
                    return True, f"{count} active pitch(es)"
                return False, "no active pitches — run bootstrap_clean.py"
            finally:
                db.close()
        except ImportError:
            return True, "Pitch model not available — skipped"

    return _check


def _check_seed_players(
    email_pattern: str,
    required: int,
) -> Callable[[], tuple[bool, str]]:
    def _check() -> tuple[bool, str]:
        from app.database import SessionLocal
        from app.models.user import User as UserModel, UserRole

        db = SessionLocal()
        try:
            count = (
                db.query(UserModel)
                .filter(
                    UserModel.role == UserRole.STUDENT,
                    UserModel.email.like(email_pattern),
                    UserModel.is_active == True,  # noqa: E712
                )
                .count()
            )
            if count >= required:
                return True, f"{count} seed players match '{email_pattern}'"
            return (
                False,
                f"{count} seed players match '{email_pattern}', need ≥ {required} — "
                "run bootstrap_clean.py",
            )
        finally:
            db.close()

    return _check


class PreflightChecker:
    """Runs AUTO-detectable hidden dependency checks and raises PreflightError on failure."""

    def __init__(self, registry: HiddenDependencyRegistry) -> None:
        self._registry = registry

    def run(self, *, fail_fast: bool = True) -> list[str]:
        """Run all AUTO checks. Returns list of passed check names.

        Raises PreflightError on first CRITICAL failure (if fail_fast=True),
        or collects all failures and raises a combined error (if fail_fast=False).
        """
        failures: list[str] = []
        passed: list[str] = []

        for dep in self._registry.all_auto():
            assert dep.check_fn is not None
            try:
                ok, detail = dep.check_fn()
            except Exception as exc:
                ok, detail = False, f"check raised {type(exc).__name__}: {exc}"

            if ok:
                passed.append(f"{dep.name}: {detail}")
            else:
                msg = f"{detail}"
                if dep.remediation:
                    msg += f" — {dep.remediation}"
                if fail_fast and dep.severity == Severity.CRITICAL:
                    raise PreflightError(dep.name, msg)
                failures.append(f"[{dep.severity.value}] {dep.name}: {msg}")

        if failures:
            raise PreflightError(
                "preflight",
                "\n".join(failures),
            )
        return passed


def build_standard_registry(
    instructor_email: str,
    age_group: str,
    player_email_pattern: str = "lfa-adult-%@lfa.com",
    min_players: int = 4,
) -> HiddenDependencyRegistry:
    """Build a registry pre-loaded with the standard H2H knockout hidden deps."""
    reg = HiddenDependencyRegistry()

    reg.register(HiddenDependency(
        name="instructor_lfa_coach_license",
        description=(
            "Instructor must have an active LFA_COACH UserLicense. "
            "Direct-assign-instructor and accept both enforce this."
        ),
        severity=Severity.CRITICAL,
        detection_mode=DetectionMode.AUTO,
        check_fn=_check_instructor_lfa_coach(instructor_email),
        remediation="PYTHONPATH=. python scripts/bootstrap_clean.py",
    ))

    reg.register(HiddenDependency(
        name="instructor_coach_level",
        description=(
            f"Instructor LFA_COACH level must be ≥ {_AGE_GROUP_REQUIRED_LEVEL.get(age_group.upper(), '?')} "
            f"for age_group={age_group}."
        ),
        severity=Severity.CRITICAL,
        detection_mode=DetectionMode.AUTO,
        check_fn=_check_instructor_level(instructor_email, age_group),
        remediation="PYTHONPATH=. python scripts/bootstrap_clean.py",
    ))

    reg.register(HiddenDependency(
        name="active_campus",
        description="At least one active Campus must exist for tournament creation.",
        severity=Severity.CRITICAL,
        detection_mode=DetectionMode.AUTO,
        check_fn=_check_active_campus(),
        remediation="PYTHONPATH=. python scripts/bootstrap_clean.py",
    ))

    reg.register(HiddenDependency(
        name="active_pitch",
        description=(
            "At least one active Pitch must exist — session generator assigns "
            "pitch_id round-robin."
        ),
        severity=Severity.CRITICAL,
        detection_mode=DetectionMode.AUTO,
        check_fn=_check_active_pitch(),
        remediation="PYTHONPATH=. python scripts/bootstrap_clean.py",
    ))

    reg.register(HiddenDependency(
        name="seed_players",
        description=(
            f"≥{min_players} active seed players matching '{player_email_pattern}' "
            "must exist. Players list API rejects .test-TLD emails, so resolution "
            "uses direct DB query."
        ),
        severity=Severity.CRITICAL,
        detection_mode=DetectionMode.AUTO,
        check_fn=_check_seed_players(player_email_pattern, min_players),
        remediation="PYTHONPATH=. python scripts/bootstrap_clean.py",
    ))

    reg.register(HiddenDependency(
        name="session_check_in_instructor_id",
        description=(
            "Session check-in requires session.instructor_id == current_user.id. "
            "The session generator sets instructor_id = master_instructor_id as fallback. "
            "The accepting instructor will match."
        ),
        severity=Severity.INFO,
        detection_mode=DetectionMode.MANUAL,
        remediation="No action needed — session generator handles this automatically.",
    ))

    reg.register(HiddenDependency(
        name="distribute_rewards_auto_transition",
        description=(
            "POST /distribute-rewards-v2 sets tournament_status='REWARDS_DISTRIBUTED' "
            "directly inside the endpoint (rewards_v2.py:92). "
            "No separate lifecycle PATCH is needed afterward."
        ),
        severity=Severity.INFO,
        detection_mode=DetectionMode.MANUAL,
    ))

    return reg
