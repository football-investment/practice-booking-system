"""Scenario orchestration primitives.

ScenarioStrategy — Protocol for format-specific logic (setup, enroll, complete).
ScenarioRunner — Orchestration-only: drives the 12-step lifecycle, delegates
                  format-specific work to the strategy.
ScenarioResult  — Outcome of a scenario run.
ScenarioFailure — Raised when the scenario fails (wraps the original exception).
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..framework._http import LifecycleError, PreflightError
from ..framework.auth import AuthContext, login
from ..framework.fixtures import (
    InstructorFixture,
    CampusFixture,
    PlayerFixture,
    resolve_campus,
    resolve_instructor,
    resolve_players_db,
)
from ..framework.logging import ColoredConsoleLogger, ScenarioLogger, TransitionEvent, TimedStep
from ..framework.preflight import HiddenDependencyRegistry, PreflightChecker
from ..framework.sessions import SessionCompletionStrategy, complete_all_sessions
from ..framework.transitions import (
    create_tournament,
    transition_status,
    direct_assign_instructor,
    accept_instructor_assignment,
    enroll_players,
    set_schedule_config,
    set_reward_config,
    calculate_rankings,
    distribute_rewards,
)
from ..framework.verification import ApiVerifier, DbVerifier, VerificationResult


@dataclass
class ScenarioConfig:
    base_url: str
    admin_email: str
    admin_password: str
    instructor_email: str
    instructor_password: str
    player_password: str = "Bootstrap#123"
    player_email_pattern: str = "lfa-adult-%@lfa.com"
    player_count: int = 4
    age_group: str = "AMATEUR"
    tournament_format: str = "HEAD_TO_HEAD"
    tournament_type_code: str = "knockout"
    max_players: int = 16
    enrollment_cost: int = 0
    match_duration_minutes: int = 90
    break_duration_minutes: int = 15
    parallel_fields: int = 1


@dataclass
class ScenarioResult:
    tournament_id: int
    sessions_completed: int
    players_enrolled: int
    api_verification: VerificationResult
    db_verification: VerificationResult
    events: list[TransitionEvent] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.api_verification.ok and self.db_verification.ok


class ScenarioFailure(Exception):
    """Raised when a scenario step fails. Wraps the original exception."""

    def __init__(self, step: str, cause: Exception) -> None:
        self.step = step
        self.cause = cause
        super().__init__(f"Scenario failed at [{step}]: {cause}")


@runtime_checkable
class ScenarioStrategy(Protocol):
    """Format-specific hooks called by ScenarioRunner at the right lifecycle moment."""

    def setup_instructor(
        self,
        cfg: ScenarioConfig,
        auth: AuthContext,
        tournament_id: int,
    ) -> None:
        """Assign and confirm the instructor for the tournament."""
        ...

    def enroll_participants(
        self,
        cfg: ScenarioConfig,
        auth: AuthContext,
        tournament_id: int,
    ) -> None:
        """Enroll players after ENROLLMENT_OPEN."""
        ...

    def extra_pre_checkin_steps(
        self,
        cfg: ScenarioConfig,
        auth: AuthContext,
        tournament_id: int,
    ) -> None:
        """Optional extra steps between ENROLLMENT_CLOSED and CHECK_IN_OPEN."""
        ...

    def extra_pre_in_progress_steps(
        self,
        cfg: ScenarioConfig,
        auth: AuthContext,
        tournament_id: int,
    ) -> None:
        """Optional extra steps between CHECK_IN_OPEN and IN_PROGRESS."""
        ...

    def complete_sessions(
        self,
        cfg: ScenarioConfig,
        auth: AuthContext,
        tournament_id: int,
    ) -> int:
        """Complete all pending sessions. Returns the number of sessions completed."""
        ...

    def session_completion_strategy(self) -> SessionCompletionStrategy:
        """Return the format-specific session completion strategy."""
        ...


class ScenarioRunner:
    """Orchestration engine — drives the full 12-step REWARDS_DISTRIBUTED lifecycle.

    Does NOT contain any format-specific logic. All format-specific work is
    delegated to the ScenarioStrategy.
    """

    def __init__(
        self,
        config: ScenarioConfig,
        strategy: ScenarioStrategy,
        registry: HiddenDependencyRegistry,
        logger: ScenarioLogger | None = None,
    ) -> None:
        self._cfg = config
        self._strategy = strategy
        self._registry = registry
        self._logger = logger or ColoredConsoleLogger()
        self._events: list[TransitionEvent] = []

    def run(self) -> ScenarioResult:
        cfg = self._cfg
        try:
            self._step_preflight()
            auth = self._step_auth()
            campus = self._step_resolve_fixtures(auth)
            tournament_id = self._step_create_tournament(auth, campus)
            self._step_instructor(auth, tournament_id)
            self._step_enrollment_open(auth, tournament_id)
            self._step_enroll_participants(auth, tournament_id)
            self._step_enrollment_close(auth, tournament_id)
            self._step_extra_pre_checkin(auth, tournament_id)
            self._step_schedule_config(auth, tournament_id)
            self._step_checkin_open(auth, tournament_id)
            self._step_extra_pre_in_progress(auth, tournament_id)
            self._step_reward_config(auth, tournament_id)
            self._step_in_progress(auth, tournament_id)
            sessions_completed = self._step_complete_sessions(auth, tournament_id)
            self._step_calculate_rankings(auth, tournament_id)
            self._step_completed(auth, tournament_id)
            self._step_distribute_rewards(auth, tournament_id)
            api_result, db_result = self._step_verify(
                auth, tournament_id, cfg.player_count
            )
        except (PreflightError, LifecycleError, ScenarioFailure):
            self._logger.summary(self._events)
            raise
        except Exception as exc:
            self._logger.summary(self._events)
            raise ScenarioFailure("unknown", exc) from exc

        result = ScenarioResult(
            tournament_id=tournament_id,
            sessions_completed=sessions_completed,
            players_enrolled=cfg.player_count,
            api_verification=api_result,
            db_verification=db_result,
            events=list(self._events),
        )
        self._logger.summary(self._events)
        return result

    # ── Step implementations ─────────────────────────────────────────────────

    def _step_preflight(self) -> None:
        import time
        t0 = time.perf_counter()
        checker = PreflightChecker(self._registry)
        passed = checker.run(fail_fast=True)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("preflight", elapsed, f"{len(passed)} checks passed")

    def _step_auth(self) -> AuthContext:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        admin_token = login(cfg.base_url, cfg.admin_email, cfg.admin_password)
        instructor_token = login(cfg.base_url, cfg.instructor_email, cfg.instructor_password)
        instructor = resolve_instructor(cfg.base_url, admin_token, cfg.instructor_email)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("auth", elapsed, f"admin + instructor (id={instructor.id})")
        return AuthContext(
            admin_token=admin_token,
            instructor_token=instructor_token,
            instructor_id=instructor.id,
        )

    def _step_resolve_fixtures(self, auth: AuthContext) -> CampusFixture:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg

        campus = resolve_campus(cfg.base_url, auth.admin_token)
        players = resolve_players_db(
            email_pattern=cfg.player_email_pattern,
            password=cfg.player_password,
            count=cfg.player_count,
            base_url=cfg.base_url,
        )
        # Populate auth with player tokens
        for p in players:
            tok = login(cfg.base_url, p.email, cfg.player_password)
            auth.player_tokens[p.email] = tok
            auth.player_ids[p.email] = p.id

        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok(
            "resolve_fixtures",
            elapsed,
            f"campus_id={campus.id}, {len(players)} players",
        )
        return campus

    def _step_create_tournament(
        self, auth: AuthContext, campus: CampusFixture
    ) -> int:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        data = create_tournament(
            cfg.base_url,
            auth.admin_token,
            tournament_format=cfg.tournament_format,
            tournament_type_code=cfg.tournament_type_code,
            age_group=cfg.age_group,
            max_players=cfg.max_players,
            enrollment_cost=cfg.enrollment_cost,
            campus_ids=[campus.id],
        )
        tid = data["tournament_id"]
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("create_tournament", elapsed, f"id={tid} → SEEKING_INSTRUCTOR")
        return tid

    def _step_instructor(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        self._strategy.setup_instructor(self._cfg, auth, tid)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("setup_instructor", elapsed, "→ INSTRUCTOR_CONFIRMED")

    def _step_enrollment_open(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        # campus_ids already passed to create_tournament; no separate assignment needed
        transition_status(cfg.base_url, auth.admin_token, tid, "ENROLLMENT_OPEN")
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("enrollment_open", elapsed, "INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN")

    def _step_enroll_participants(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        self._strategy.enroll_participants(self._cfg, auth, tid)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("enroll_participants", elapsed, f"{self._cfg.player_count} players enrolled")

    def _step_enrollment_close(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        transition_status(cfg.base_url, auth.admin_token, tid, "ENROLLMENT_CLOSED")
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("enrollment_close", elapsed, "ENROLLMENT_OPEN → ENROLLMENT_CLOSED")

    def _step_extra_pre_checkin(self, auth: AuthContext, tid: int) -> None:
        self._strategy.extra_pre_checkin_steps(self._cfg, auth, tid)

    def _step_schedule_config(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        set_schedule_config(
            cfg.base_url,
            auth.admin_token,
            tid,
            match_duration_minutes=cfg.match_duration_minutes,
            break_duration_minutes=cfg.break_duration_minutes,
            parallel_fields=cfg.parallel_fields,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("schedule_config", elapsed, "SCHEDULE_CONFIG_MISSING guard cleared")

    def _step_checkin_open(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        transition_status(cfg.base_url, auth.admin_token, tid, "CHECK_IN_OPEN")
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("checkin_open", elapsed, "ENROLLMENT_CLOSED → CHECK_IN_OPEN")

    def _step_extra_pre_in_progress(self, auth: AuthContext, tid: int) -> None:
        self._strategy.extra_pre_in_progress_steps(self._cfg, auth, tid)

    def _step_reward_config(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        set_reward_config(cfg.base_url, auth.admin_token, tid)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("reward_config", elapsed, "REWARD_CONFIG_MISSING guard cleared")

    def _step_in_progress(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        transition_status(cfg.base_url, auth.admin_token, tid, "IN_PROGRESS")
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("in_progress", elapsed, "CHECK_IN_OPEN → IN_PROGRESS (sessions auto-generated)")

    def _step_complete_sessions(self, auth: AuthContext, tid: int) -> int:
        import time
        t0 = time.perf_counter()
        count = self._strategy.complete_sessions(self._cfg, auth, tid)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("complete_sessions", elapsed, f"{count} session(s) completed")
        return count

    def _step_calculate_rankings(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        calculate_rankings(cfg.base_url, auth.admin_token, tid)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("calculate_rankings", elapsed, "rankings calculated")

    def _step_completed(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        transition_status(cfg.base_url, auth.admin_token, tid, "COMPLETED")
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok("completed", elapsed, "IN_PROGRESS → COMPLETED")

    def _step_distribute_rewards(self, auth: AuthContext, tid: int) -> None:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg
        distribute_rewards(cfg.base_url, auth.admin_token, tid)
        elapsed = (time.perf_counter() - t0) * 1000
        self._log_ok(
            "distribute_rewards",
            elapsed,
            "COMPLETED → REWARDS_DISTRIBUTED (auto-transition in rewards_v2.py:92)",
        )

    def _step_verify(
        self,
        auth: AuthContext,
        tid: int,
        enrolled_count: int,
    ) -> tuple[VerificationResult, VerificationResult]:
        import time
        t0 = time.perf_counter()
        cfg = self._cfg

        api = ApiVerifier(cfg.base_url, auth.admin_token, auth.instructor_token)
        api_result = api.verify_rewards_distributed(tid, enrolled_count)

        db = DbVerifier()
        db_result = db.verify_rewards_distributed(tid, enrolled_count)

        elapsed = (time.perf_counter() - t0) * 1000
        api_ok = len(api_result.passed)
        db_ok = len(db_result.passed)
        all_ok = api_result.ok and db_result.ok
        self._log_ok(
            "verify",
            elapsed,
            f"API {api_ok} passed, DB {db_ok} passed — {'PASS' if all_ok else 'FAIL'}",
        )
        return api_result, db_result

    # ── Logging helpers ──────────────────────────────────────────────────────

    def _log_ok(self, step: str, elapsed_ms: float, detail: str = "") -> None:
        from ..framework.logging import TransitionEvent
        event = TransitionEvent(step, "ok", elapsed_ms, detail)
        self._events.append(event)
        self._logger.log(event)
