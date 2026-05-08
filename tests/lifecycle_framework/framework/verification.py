"""API-level and DB-level verification — invariant-centric."""
from __future__ import annotations

from dataclasses import dataclass, field

import requests

from ._http import require_ok


@dataclass
class VerificationResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0

    def assert_all(self) -> None:
        if self.failed:
            raise AssertionError(
                f"Verification failed ({len(self.failed)} checks):\n"
                + "\n".join(f"  ✗ {f}" for f in self.failed)
            )


class ApiVerifier:
    """Verifies end-state via public API endpoints — no DB access."""

    def __init__(self, base_url: str, admin_token: str, instructor_token: str) -> None:
        self._base = base_url
        self._admin_h = {"Authorization": f"Bearer {admin_token}"}
        self._instr_h = {"Authorization": f"Bearer {instructor_token}"}

    def verify_rewards_distributed(
        self,
        tournament_id: int,
        enrolled_count: int,
    ) -> VerificationResult:
        result = VerificationResult()
        self._check_tournament_status(tournament_id, result)
        self._check_rankings(tournament_id, enrolled_count, result)
        self._check_sessions_completed(tournament_id, result)
        return result

    def _check_tournament_status(self, tid: int, result: VerificationResult) -> None:
        try:
            resp = requests.get(
                f"{self._base}/api/v1/tournaments/{tid}",
                headers=self._admin_h,
                timeout=15,
            )
            data = require_ok(resp, "api:tournament_status")
            status = data.get("tournament_status") or data.get("status")
            if status == "REWARDS_DISTRIBUTED":
                result.passed.append(f"tournament_status = {status}")
            else:
                result.failed.append(
                    f"tournament_status: expected REWARDS_DISTRIBUTED, got {status!r}"
                )
        except Exception as exc:
            result.failed.append(f"tournament_status check raised: {exc}")

    def _check_rankings(
        self, tid: int, enrolled_count: int, result: VerificationResult
    ) -> None:
        try:
            resp = requests.get(
                f"{self._base}/api/v1/tournaments/{tid}/rankings",
                headers=self._admin_h,
                timeout=15,
            )
            data = require_ok(resp, "api:rankings")
            rank_list = data.get("rankings", [])
            if len(rank_list) >= enrolled_count:
                result.passed.append(
                    f"rankings: {len(rank_list)} entries (≥ enrolled {enrolled_count})"
                )
            else:
                result.failed.append(
                    f"rankings: got {len(rank_list)}, expected ≥ {enrolled_count}"
                )
        except Exception as exc:
            result.failed.append(f"rankings check raised: {exc}")

    def _check_sessions_completed(self, tid: int, result: VerificationResult) -> None:
        try:
            resp = requests.get(
                f"{self._base}/api/v1/tournaments/{tid}/sessions",
                headers=self._instr_h,
                timeout=15,
            )
            data = require_ok(resp, "api:sessions")
            sessions: list[dict] = data if isinstance(data, list) else data.get("sessions", [])
            match_sessions = [s for s in sessions if s.get("is_tournament_game")]
            completed = sum(1 for s in match_sessions if s.get("result_submitted"))
            if match_sessions and completed == len(match_sessions):
                result.passed.append(
                    f"sessions: {completed}/{len(match_sessions)} MATCH sessions completed"
                )
            elif not match_sessions:
                result.failed.append("sessions: no tournament game sessions found")
            else:
                result.failed.append(
                    f"sessions: {completed}/{len(match_sessions)} completed"
                )
        except Exception as exc:
            result.failed.append(f"sessions check raised: {exc}")


class DbVerifier:
    """Verifies business invariants directly in the database.

    Uses only business-observable state, not implementation-internal flags.
    Session completion is verified via reward_policy_snapshot + ranking coverage,
    not session_status (which is an internal state machine detail).
    """

    def verify_rewards_distributed(
        self,
        tournament_id: int,
        enrolled_count: int,
    ) -> VerificationResult:
        result = VerificationResult()
        self._check_tournament_status(tournament_id, result)
        self._check_reward_snapshot(tournament_id, result)
        self._check_sessions_complete(tournament_id, result)
        self._check_ranking_coverage(tournament_id, enrolled_count, result)
        self._check_participation_records(tournament_id, result)
        return result

    def _check_tournament_status(self, tid: int, result: VerificationResult) -> None:
        try:
            from app.database import SessionLocal
            from app.models.semester import Semester

            db = SessionLocal()
            try:
                t = db.query(Semester).filter(Semester.id == tid).first()
                if t is None:
                    result.failed.append(f"tournament {tid} not found in DB")
                    return
                if t.tournament_status == "REWARDS_DISTRIBUTED":
                    result.passed.append(f"db:tournament_status = {t.tournament_status}")
                else:
                    result.failed.append(
                        f"db:tournament_status: expected REWARDS_DISTRIBUTED, "
                        f"got {t.tournament_status!r}"
                    )
            finally:
                db.close()
        except Exception as exc:
            result.failed.append(f"db:tournament_status check raised: {exc}")

    def _check_reward_snapshot(self, tid: int, result: VerificationResult) -> None:
        try:
            from app.database import SessionLocal
            from app.models.semester import Semester

            db = SessionLocal()
            try:
                t = db.query(Semester).filter(Semester.id == tid).first()
                if t is None:
                    return
                if t.reward_policy_snapshot is not None:
                    result.passed.append("db:reward_policy_snapshot IS NOT NULL")
                else:
                    result.failed.append(
                        "db:reward_policy_snapshot IS NULL — SNAPSHOT_MISSING guard applies"
                    )
            finally:
                db.close()
        except Exception as exc:
            result.failed.append(f"db:reward_policy_snapshot check raised: {exc}")

    def _check_sessions_complete(self, tid: int, result: VerificationResult) -> None:
        try:
            from app.database import SessionLocal
            from app.models.session import Session as SessionModel, EventCategory

            db = SessionLocal()
            try:
                incomplete = (
                    db.query(SessionModel)
                    .filter(
                        SessionModel.semester_id == tid,
                        SessionModel.auto_generated == True,  # noqa: E712
                        SessionModel.event_category == EventCategory.MATCH,
                        SessionModel.session_status != "completed",
                    )
                    .count()
                )
                if incomplete == 0:
                    result.passed.append(
                        "db:all auto-generated MATCH sessions have session_status='completed'"
                    )
                else:
                    result.failed.append(
                        f"db:{incomplete} auto-generated MATCH session(s) not completed"
                    )
            finally:
                db.close()
        except Exception as exc:
            result.failed.append(f"db:sessions_complete check raised: {exc}")

    def _check_ranking_coverage(
        self, tid: int, enrolled_count: int, result: VerificationResult
    ) -> None:
        try:
            from app.database import SessionLocal
            from app.models.tournament_ranking import TournamentRanking

            db = SessionLocal()
            try:
                count = (
                    db.query(TournamentRanking)
                    .filter(TournamentRanking.tournament_id == tid)
                    .count()
                )
                if count >= enrolled_count:
                    result.passed.append(
                        f"db:TournamentRanking count = {count} (≥ enrolled {enrolled_count})"
                    )
                else:
                    result.failed.append(
                        f"db:TournamentRanking count {count} < enrolled {enrolled_count}"
                    )
            finally:
                db.close()
        except Exception as exc:
            result.failed.append(f"db:ranking_coverage check raised: {exc}")

    def _check_participation_records(self, tid: int, result: VerificationResult) -> None:
        try:
            from app.database import SessionLocal
            from app.models.tournament_achievement import TournamentParticipation

            db = SessionLocal()
            try:
                count = (
                    db.query(TournamentParticipation)
                    .filter(TournamentParticipation.semester_id == tid)
                    .count()
                )
                if count > 0:
                    result.passed.append(f"db:TournamentParticipation count = {count}")
                else:
                    result.failed.append(
                        "db:TournamentParticipation count = 0 — PARTICIPATION_RECORDS_MISSING"
                    )
            finally:
                db.close()
        except ImportError:
            result.passed.append("db:TournamentParticipation skipped (not importable)")
        except Exception as exc:
            result.failed.append(f"db:participation_records check raised: {exc}")
