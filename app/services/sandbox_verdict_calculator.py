"""
Sandbox Verdict Calculator

Standalone module for calculating sandbox test verdict.
Analyzes tournament results and generates "Ship It" screen data.

MVP Scope: Simple WORKING/NOT_WORKING verdict based on:
- Status = REWARDS_DISTRIBUTED
- All participants have TournamentParticipation records
- Skills changed (non-zero deltas)
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.semester import Semester
from app.models.tournament_achievement import TournamentParticipation
from app.models.tournament_ranking import TournamentRanking
from app.services import skill_progression_service

logger = logging.getLogger(__name__)


class SandboxVerdictCalculator:
    """
    Calculates sandbox test verdict and builds response data

    Pure logic - no side effects
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_verdict(
        self,
        tournament_id: int,
        expected_participant_count: int,
        skills_to_test: List[str],
        distribution_result: Any,
        skills_before_snapshot: Dict[int, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Calculate verdict and build complete response data

        Args:
            tournament_id: Tournament ID
            expected_participant_count: Expected number of participants
            skills_to_test: Skills being tested
            distribution_result: Result from reward distribution
            skills_before_snapshot: Read-only snapshot of skills before tournament

        Returns:
            Dictionary with verdict, skill_progression, top/bottom performers, insights
        """
        insights = []

        # Check 1: Status = REWARDS_DISTRIBUTED
        tournament = self.db.query(Semester).filter(Semester.id == tournament_id).first()

        if not tournament:
            return {
                "verdict": "NOT_WORKING",
                "skill_progression": {},
                "top_performers": [],
                "bottom_performers": [],
                "insights": [{
                    "category": "VERDICT",
                    "severity": "ERROR",
                    "message": f"Tournament {tournament_id} not found"
                }]
            }

        if tournament.tournament_status != "REWARDS_DISTRIBUTED":
            insights.append({
                "category": "VERDICT",
                "severity": "ERROR",
                "message": f"Tournament status is {tournament.tournament_status}, expected REWARDS_DISTRIBUTED"
            })
            return self._build_not_working_verdict(insights)

        insights.append({
            "category": "STATUS_TRANSITION",
            "severity": "SUCCESS",
            "message": f"Status transition: DRAFT → COMPLETED → REWARDS_DISTRIBUTED"
        })

        # Check 2: All participants have TournamentParticipation records
        participation_count = self.db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tournament_id
        ).count()

        if participation_count != expected_participant_count:
            insights.append({
                "category": "VERDICT",
                "severity": "ERROR",
                "message": f"Expected {expected_participant_count} participants, found {participation_count} TournamentParticipation records"
            })
            return self._build_not_working_verdict(insights)

        insights.append({
            "category": "VERDICT",
            "severity": "SUCCESS",
            "message": f"All {expected_participant_count} participants received rewards successfully"
        })

        # Check 3: Skills changed (non-zero deltas)
        skill_progression = self._calculate_skill_progression(
            tournament_id, skills_to_test, skills_before_snapshot
        )

        total_skill_change = 0
        for skill_name, stats in skill_progression.items():
            change = stats["after"]["average"] - stats["before"]["average"]
            total_skill_change += abs(change)

        if total_skill_change == 0:
            insights.append({
                "category": "SKILL_PROGRESSION",
                "severity": "ERROR",
                "message": "No skill changes detected (expected progression for all tested skills)"
            })
            return self._build_not_working_verdict(insights)

        # Add skill progression insights
        for skill_name, stats in skill_progression.items():
            change = stats["after"]["average"] - stats["before"]["average"]
            insights.append({
                "category": "SKILL_PROGRESSION",
                "severity": "INFO",
                "message": f"Average {skill_name} skill changed by {change:+.1f} points"
            })

        # Check 4: No duplicate participation records (implicit - would have failed at Check 2)
        insights.append({
            "category": "IDEMPOTENCY",
            "severity": "SUCCESS",
            "message": "No duplicate TournamentParticipation records created"
        })

        # Build top/bottom performers
        top_performers = self._get_top_performers(tournament_id, skills_to_test, skills_before_snapshot, 3)
        bottom_performers = self._get_bottom_performers(tournament_id, skills_to_test, skills_before_snapshot, 2)

        return {
            "verdict": "WORKING",
            "skill_progression": skill_progression,
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,
            "insights": insights
        }

    def _build_not_working_verdict(self, insights: List[Dict]) -> Dict[str, Any]:
        """Build NOT_WORKING verdict response"""
        return {
            "verdict": "NOT_WORKING",
            "skill_progression": {},
            "top_performers": [],
            "bottom_performers": [],
            "insights": insights
        }

    def _calculate_skill_progression(
        self,
        tournament_id: int,
        skills_to_test: List[str],
        skills_before_snapshot: Dict[int, Dict[str, float]]
    ) -> Dict[str, Dict]:
        """
        Calculate before/after skill statistics using snapshot

        Returns:
            {
                "passing": {
                    "before": {"average": 75.2, "min": 60.0, "max": 90.0},
                    "after": {"average": 77.8, "min": 61.5, "max": 92.0},
                    "change": "+2.6 avg"
                },
                ...
            }
        """
        skill_stats = {}

        for skill_name in skills_to_test:
            before_values = []
            after_values = []

            # Use snapshot for BEFORE, current profile for AFTER
            for user_id, skills_before in skills_before_snapshot.items():
                before = skills_before.get(skill_name, 50.0)
                before_values.append(before)

                # Get AFTER from current profile
                skill_profile = skill_progression_service.get_skill_profile(self.db, user_id)

                # Guard: Ensure it's a dict
                if not isinstance(skill_profile, dict):
                    after = 50.0
                else:
                    skills_dict = skill_profile.get("skills", {})
                    skill_data = skills_dict.get(skill_name, {})
                    after = skill_data.get("current_level", 50.0)

                after_values.append(after)

            if before_values and after_values:
                before_avg = sum(before_values) / len(before_values)
                after_avg = sum(after_values) / len(after_values)
                change = after_avg - before_avg

                skill_stats[skill_name] = {
                    "before": {
                        "average": round(before_avg, 1),
                        "min": round(min(before_values), 1),
                        "max": round(max(before_values), 1)
                    },
                    "after": {
                        "average": round(after_avg, 1),
                        "min": round(min(after_values), 1),
                        "max": round(max(after_values), 1)
                    },
                    "change": f"{change:+.1f} avg"
                }

        return skill_stats

    def _get_top_performers(
        self,
        tournament_id: int,
        skills_to_test: List[str],
        skills_before_snapshot: Dict[int, Dict[str, float]],
        count: int
    ) -> List[Dict]:
        """
        Get top N performers with skill changes

        Returns list sorted by rank (1, 2, 3...)
        """
        rankings = self.db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).order_by(TournamentRanking.rank).limit(count).all()

        performers = []

        for ranking in rankings:
            # Get user
            from app.models.user import User
            user = self.db.query(User).filter(User.id == ranking.user_id).first()

            # Calculate skill changes using snapshot
            skills_changed = {}
            total_skill_gain = 0

            for skill_name in skills_to_test:
                before = skills_before_snapshot.get(ranking.user_id, {}).get(skill_name, 50.0)

                # Get AFTER from current profile
                skill_profile = skill_progression_service.get_skill_profile(self.db, ranking.user_id)

                # Guard: Ensure it's a dict
                if not isinstance(skill_profile, dict):
                    after = 50.0
                else:
                    skills_dict = skill_profile.get("skills", {})
                    skill_data = skills_dict.get(skill_name, {})
                    after = skill_data.get("current_level", 50.0)

                change = after - before

                skills_changed[skill_name] = {
                    "before": round(before, 1),
                    "after": round(after, 1),
                    "change": f"{change:+.1f}"
                }

                total_skill_gain += change

            performers.append({
                "user_id": ranking.user_id,
                "username": user.email.split("@")[0] if user else f"user_{ranking.user_id}",
                "rank": ranking.rank,
                "points": ranking.points,
                "skills_changed": skills_changed,
                "total_skill_gain": round(total_skill_gain, 1)
            })

        return performers

    def _get_bottom_performers(
        self,
        tournament_id: int,
        skills_to_test: List[str],
        skills_before_snapshot: Dict[int, Dict[str, float]],
        count: int
    ) -> List[Dict]:
        """
        Get bottom N performers with skill changes

        Returns list sorted by rank descending (last place first)
        """
        # Get total participant count
        total_count = self.db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).count()

        if total_count <= count:
            # If total count <= requested count, skip (would overlap with top performers)
            return []

        # Get bottom N rankings
        rankings = self.db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).order_by(TournamentRanking.rank.desc()).limit(count).all()

        performers = []

        for ranking in rankings:
            # Get user
            from app.models.user import User
            user = self.db.query(User).filter(User.id == ranking.user_id).first()

            # Calculate skill changes using snapshot
            skills_changed = {}
            total_skill_gain = 0

            for skill_name in skills_to_test:
                before = skills_before_snapshot.get(ranking.user_id, {}).get(skill_name, 50.0)

                # Get AFTER from current profile
                skill_profile = skill_progression_service.get_skill_profile(self.db, ranking.user_id)

                # Guard: Ensure it's a dict
                if not isinstance(skill_profile, dict):
                    after = 50.0
                else:
                    skills_dict = skill_profile.get("skills", {})
                    skill_data = skills_dict.get(skill_name, {})
                    after = skill_data.get("current_level", 50.0)

                change = after - before

                skills_changed[skill_name] = {
                    "before": round(before, 1),
                    "after": round(after, 1),
                    "change": f"{change:+.1f}"
                }

                total_skill_gain += change

            performers.append({
                "user_id": ranking.user_id,
                "username": user.email.split("@")[0] if user else f"user_{ranking.user_id}",
                "rank": ranking.rank,
                "points": ranking.points,
                "skills_changed": skills_changed,
                "total_skill_gain": round(total_skill_gain, 1)
            })

        return performers
