"""
Virtual Training Service — Phase 1

Provides pure-function helpers and DB-backed queries for the Virtual Training
mini-game system. No active user routes in Phase 1 — service exists purely
for data model validation and future Phase 2 integration.

Anti-farming rules enforced here (not in the route):
  - Bot filter: avg_reaction_ms < 100 → is_valid=False, invalid_reason="bot_suspected"
  - Diminishing returns multiplier: attempt 1→1.0, 2→0.6, 3→0.3, 4+→0.0

Skill delta computation reuses compute_skill_deltas() from segment_reward_service
so the formula is identical to the tournament/session training pipeline.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.virtual_training import VirtualTrainingAttempt, VirtualTrainingGame

_XP_MULTIPLIER_TABLE: dict[int, float] = {1: 1.0, 2: 0.6, 3: 0.3}
_BOT_REACTION_THRESHOLD_MS = 100.0


class VirtualTrainingService:

    # ── Read helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def get_games(db: Session) -> list[VirtualTrainingGame]:
        """Return all active game presets ordered by id."""
        return (
            db.query(VirtualTrainingGame)
            .filter(VirtualTrainingGame.is_active == True)  # noqa: E712
            .order_by(VirtualTrainingGame.id)
            .all()
        )

    @staticmethod
    def get_game(db: Session, code: str) -> Optional[VirtualTrainingGame]:
        """Fetch a game preset by its unique code (regardless of is_active)."""
        return (
            db.query(VirtualTrainingGame)
            .filter(VirtualTrainingGame.code == code)
            .first()
        )

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def validate_attempt(data: dict) -> tuple[bool, Optional[str]]:
        """
        Run anti-abuse checks on raw attempt data.

        Returns (is_valid, invalid_reason).
        Checks:
          - avg_reaction_ms < 100 → bot_suspected
        """
        avg_ms = data.get("avg_reaction_ms")
        if avg_ms is not None and float(avg_ms) < _BOT_REACTION_THRESHOLD_MS:
            return False, "bot_suspected"
        return True, None

    # ── Daily indexing ────────────────────────────────────────────────────────

    @staticmethod
    def calculate_daily_attempt_index(
        db: Session, user_id: int, game_id: int
    ) -> int:
        """
        Return the 1-based attempt index for today.

        Counts only valid attempts for the (user, game) pair that started
        on the current UTC calendar day. Returns 1 when no prior attempts.
        """
        today_start = datetime.combine(date.today(), datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        count = (
            db.query(VirtualTrainingAttempt)
            .filter(
                VirtualTrainingAttempt.user_id == user_id,
                VirtualTrainingAttempt.game_id == game_id,
                VirtualTrainingAttempt.started_at >= today_start,
                VirtualTrainingAttempt.is_valid == True,  # noqa: E712
            )
            .count()
        )
        return count + 1

    # ── XP calculation ────────────────────────────────────────────────────────

    @staticmethod
    def calculate_xp_multiplier(attempt_index: int) -> float:
        """
        Diminishing returns multiplier by daily attempt index.

        Index 1 → 1.0 (full XP)
        Index 2 → 0.6
        Index 3 → 0.3
        Index 4+ → 0.0 (no XP, but attempt still recorded)
        """
        return _XP_MULTIPLIER_TABLE.get(attempt_index, 0.0)

    @staticmethod
    def calculate_xp_awarded(game: VirtualTrainingGame, multiplier: float) -> int:
        """Compute floor(base_xp * multiplier). Returns 0 when multiplier is 0."""
        return int(game.base_xp * multiplier)

    # ── Skill deltas ──────────────────────────────────────────────────────────

    @staticmethod
    def calculate_skill_deltas(
        game: VirtualTrainingGame,
        xp_awarded: int,
        conversion_rates: dict[str, int],
    ) -> dict[str, float]:
        """
        Translate game skill_targets + XP into per-skill additive deltas.

        Delegates to segment_reward_service.compute_skill_deltas() so the
        formula is identical to the session training pipeline.
        """
        from app.services.segment_reward_service import compute_skill_deltas

        return compute_skill_deltas(
            skill_targets=game.skill_targets or {},
            xp_awarded=xp_awarded,
            conversion_rates=conversion_rates,
        )
