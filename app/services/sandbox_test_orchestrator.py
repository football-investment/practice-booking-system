"""
Sandbox Test Orchestrator

Coordinates end-to-end sandbox tournament test execution:
1. Create temporary tournament
2. Enroll synthetic participants
3. Generate rankings
4. Complete tournament lifecycle
5. Distribute rewards
6. Calculate verdict

MVP Scope: Single test run, auto-generated data only
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random

from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.tournament_ranking import TournamentRanking
from app.models.license import UserLicense
from app.services.tournament import tournament_reward_orchestrator
from app.services import skill_progression_service

logger = logging.getLogger(__name__)

# Test user pool (valid existing user IDs) with known baseline skills
TEST_USER_POOL = [4, 5, 6, 7, 13, 14, 15, 16]


class SandboxTestOrchestrator:
    """
    Orchestrates sandbox tournament test execution

    Handles full lifecycle from tournament creation to reward distribution
    """

    def __init__(self, db: Session):
        self.db = db
        self.tournament_id: Optional[int] = None
        self.test_run_id: str = ""
        self.execution_steps: List[str] = []
        self.start_time: Optional[datetime] = None
        self.skills_before_snapshot: Dict[int, Dict[str, float]] = {}  # {user_id: {skill: value}}

    def execute_test(
        self,
        tournament_type_code: str,
        skills_to_test: List[str],
        player_count: int,
        performance_variation: str = "MEDIUM",
        ranking_distribution: str = "NORMAL"
    ) -> Dict[str, Any]:
        """
        Execute complete sandbox test

        Args:
            tournament_type_code: Tournament type code (league, knockout, hybrid)
            skills_to_test: List of skill names to test
            player_count: Number of synthetic players (4-16)
            performance_variation: LOW, MEDIUM, HIGH
            ranking_distribution: NORMAL, TOP_HEAVY, BOTTOM_HEAVY

        Returns:
            Complete test results including verdict, skill progression, top/bottom performers
        """
        self.start_time = datetime.now()
        self.test_run_id = f"sandbox-{self.start_time.strftime('%Y-%m-%d-%H-%M-%S')}-{random.randint(1000, 9999)}"

        logger.info(f"🧪 Starting sandbox test: {self.test_run_id}")

        try:
            # Step 1: Create tournament
            self._create_tournament(tournament_type_code, skills_to_test, player_count)

            # Step 2: Enroll participants
            enrolled_users = self._enroll_participants(player_count)

            # Step 2.5: Snapshot skills BEFORE tournament (read-only)
            self._snapshot_skills_before(enrolled_users, skills_to_test)

            # Step 3: Generate rankings
            self._generate_rankings(enrolled_users, performance_variation, ranking_distribution)

            # Step 4: Transition to COMPLETED
            self._transition_to_completed()

            # Step 5: Distribute rewards
            distribution_result = self._distribute_rewards()

            # Step 6: Calculate verdict (pass snapshot)
            verdict_data = self._calculate_verdict(
                enrolled_users, skills_to_test, distribution_result, self.skills_before_snapshot
            )

            duration_seconds = (datetime.now() - self.start_time).total_seconds()

            return {
                "verdict": verdict_data["verdict"],
                "test_run_id": self.test_run_id,
                "tournament": {
                    "id": self.tournament_id,
                    "name": f"SANDBOX-TEST-{tournament_type_code.upper()}-{self.start_time.strftime('%Y-%m-%d')}",
                    "type": tournament_type_code.upper(),
                    "status": "REWARDS_DISTRIBUTED",
                    "player_count": player_count,
                    "skills_tested": skills_to_test
                },
                "execution_summary": {
                    "duration_seconds": round(duration_seconds, 2),
                    "steps_completed": self.execution_steps
                },
                "skill_progression": verdict_data["skill_progression"],
                "top_performers": verdict_data["top_performers"],
                "bottom_performers": verdict_data["bottom_performers"],
                "insights": verdict_data["insights"],
                "export_data": {
                    "pdf_ready": True,
                    "export_url": f"/api/v1/sandbox/export-pdf/{self.test_run_id}"
                }
            }

        except Exception as e:
            logger.error(f"❌ Sandbox test failed: {e}", exc_info=True)

            duration_seconds = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0

            return {
                "verdict": "NOT_WORKING",
                "test_run_id": self.test_run_id if self.test_run_id else "unknown",
                "tournament": {
                    "id": self.tournament_id,
                    "name": f"SANDBOX-TEST-FAILED",
                    "type": tournament_type_code.upper() if tournament_type_code else "UNKNOWN",
                    "status": self._get_tournament_status() or "UNKNOWN",
                    "player_count": player_count,
                    "skills_tested": skills_to_test
                },
                "execution_summary": {
                    "duration_seconds": round(duration_seconds, 2),
                    "steps_completed": self.execution_steps
                },
                "skill_progression": {},
                "top_performers": [],
                "bottom_performers": [],
                "insights": [{
                    "category": "ERROR",
                    "severity": "ERROR",
                    "message": f"Test execution failed at stage: {self._get_current_stage()}"
                }, {
                    "category": "ERROR",
                    "severity": "ERROR",
                    "message": f"Error: {str(e)}"
                }],
                "export_data": {
                    "pdf_ready": False,
                    "export_url": None
                },
                "error": {
                    "stage": self._get_current_stage(),
                    "message": str(e),
                    "details": repr(e)
                }
            }

    def _create_tournament(
        self,
        tournament_type_code: str,
        skills_to_test: List[str],
        player_count: int
    ) -> None:
        """Create temporary tournament with reward config"""
        logger.info(f"📋 Creating tournament: type={tournament_type_code}, players={player_count}")

        # Get tournament type
        tournament_type = self.db.query(TournamentType).filter(
            TournamentType.code == tournament_type_code
        ).first()

        if not tournament_type:
            raise ValueError(f"Tournament type not found: {tournament_type_code}")

        # Validate player count
        is_valid, error_msg = tournament_type.validate_player_count(player_count)
        if not is_valid:
            raise ValueError(error_msg)

        # Build reward config
        reward_config_data = self._build_reward_config(skills_to_test)

        # Create tournament (P1: without reward_config, will be added as separate entity)
        tournament = Semester(
            code=f"SANDBOX-{self.test_run_id}",
            name=f"SANDBOX-TEST-{tournament_type_code.upper()}-{self.start_time.strftime('%Y-%m-%d')}",
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date(),
            is_active=True,
            tournament_type_id=tournament_type.id,
            tournament_status="DRAFT",
            max_players=player_count
        )

        self.db.add(tournament)
        self.db.commit()
        self.db.refresh(tournament)

        self.tournament_id = tournament.id

        # 🎁 P1: Create separate TournamentRewardConfig
        from app.models.tournament_reward_config import TournamentRewardConfig
        reward_config_obj = TournamentRewardConfig(
            semester_id=tournament.id,
            reward_policy_name="sandbox_test",
            reward_config=reward_config_data
        )
        self.db.add(reward_config_obj)
        self.db.commit()

        self.execution_steps.append(f"Tournament created (ID: {self.tournament_id}, Status: DRAFT)")
        logger.info(f"✅ Tournament created: ID={self.tournament_id}, Reward config: sandbox_test")

    def _build_reward_config(self, skills_to_test: List[str]) -> Dict:
        """Build reward config with skill mappings"""
        skill_mappings = []
        for skill in skills_to_test:
            skill_mappings.append({
                "skill": skill,
                "enabled": True,
                "weight": 1.0,
                "placement_bonuses": {
                    "1": 5.0,  # 1st place: +5.0
                    "2": 3.0,  # 2nd place: +3.0
                    "3": 2.0,  # 3rd place: +2.0
                    "default": 1.0  # Others: +1.0
                }
            })

        return {
            "template_name": "sandbox_test",
            "first_place": {
                "xp_multiplier": 1.0,
                "credits": 100
            },
            "second_place": {
                "xp_multiplier": 0.8,
                "credits": 50
            },
            "third_place": {
                "xp_multiplier": 0.6,
                "credits": 25
            },
            "participation": {
                "xp_multiplier": 0.2,
                "credits": 10
            },
            "skill_mappings": skill_mappings
        }

    def _enroll_participants(self, player_count: int) -> List[int]:
        """Enroll synthetic participants"""
        logger.info(f"👥 Enrolling {player_count} participants")

        # Select random users from test pool
        selected_users = random.sample(TEST_USER_POOL, player_count)

        # Get active licenses for each user
        from app.models.license import UserLicense

        for user_id in selected_users:
            # Get user's active license
            active_license = self.db.query(UserLicense).filter(
                UserLicense.user_id == user_id,
                UserLicense.is_active == True
            ).first()

            if not active_license:
                logger.warning(f"User {user_id} has no active license, skipping enrollment")
                continue

            # Create enrollment record with user_license_id
            from app.models.semester_enrollment import SemesterEnrollment

            enrollment = SemesterEnrollment(
                user_id=user_id,
                semester_id=self.tournament_id,
                user_license_id=active_license.id,
                is_active=True,
                payment_verified=True
            )
            self.db.add(enrollment)

        self.db.commit()

        self.execution_steps.append(f"Participants enrolled ({player_count} players)")
        logger.info(f"✅ Enrolled users: {selected_users}")

        return selected_users

    def _snapshot_skills_before(self, user_ids: List[int], skills_to_test: List[str]) -> None:
        """Snapshot current skill values BEFORE tournament (read-only, in-memory)"""
        logger.info(f"📸 Snapshotting skills for {len(user_ids)} users")

        for user_id in user_ids:
            try:
                # Get current skill profile (nested structure)
                skill_profile = skill_progression_service.get_skill_profile(self.db, user_id)

                # Guard: Ensure it's a dict
                if not isinstance(skill_profile, dict):
                    logger.warning(f"skill_profile returned non-dict type={type(skill_profile)}, using defaults")
                    self.skills_before_snapshot[user_id] = {skill: 50.0 for skill in skills_to_test}
                    continue

                skills_dict = skill_profile.get("skills", {})

                # Extract only tested skills (use current_level)
                user_skills = {}
                for skill in skills_to_test:
                    skill_data = skills_dict.get(skill, {})
                    user_skills[skill] = skill_data.get("current_level", 50.0)

                self.skills_before_snapshot[user_id] = user_skills

            except Exception as e:
                logger.error(f"Could not snapshot skills for user {user_id}: {e}", exc_info=True)
                # Set defaults
                self.skills_before_snapshot[user_id] = {skill: 50.0 for skill in skills_to_test}

        logger.info(f"✅ Skills snapshot complete: {len(self.skills_before_snapshot)} users")

    def _generate_rankings(
        self,
        user_ids: List[int],
        performance_variation: str,
        ranking_distribution: str
    ) -> None:
        """Generate synthetic tournament rankings"""
        logger.info(f"🏆 Generating rankings: variation={performance_variation}, distribution={ranking_distribution}")

        player_count = len(user_ids)

        # Generate base points based on distribution
        if ranking_distribution == "NORMAL":
            base_points = [100 - (i * (100 / player_count)) for i in range(player_count)]
        elif ranking_distribution == "TOP_HEAVY":
            # Top 3 get 70% of total points
            if player_count >= 3:
                base_points = [100, 90, 80] + [40 - (i * 5) for i in range(player_count - 3)]
            else:
                base_points = [100, 90, 80][:player_count]
        elif ranking_distribution == "BOTTOM_HEAVY":
            # Bottom half clustered
            base_points = [100] + [50 - (i * 5) for i in range(player_count - 1)]
        else:
            base_points = [100 - (i * (100 / player_count)) for i in range(player_count)]

        # Apply variation (noise)
        noise_range = {"LOW": 5, "MEDIUM": 10, "HIGH": 20}.get(performance_variation, 10)

        final_points = []
        for points in base_points:
            noise = random.uniform(-noise_range, noise_range)
            final_points.append(max(0, points + noise))

        # Sort by points descending and assign ranks
        ranked_data = sorted(zip(user_ids, final_points), key=lambda x: x[1], reverse=True)

        # Insert rankings
        for rank, (user_id, points) in enumerate(ranked_data, start=1):
            ranking = TournamentRanking(
                tournament_id=self.tournament_id,
                user_id=user_id,
                participant_type="PLAYER",
                rank=rank,
                points=int(points),
                wins=0,
                losses=0,
                draws=0,
                updated_at=datetime.now()
            )
            self.db.add(ranking)

        self.db.commit()

        self.execution_steps.append("Rankings generated")
        logger.info(f"✅ Rankings created for {len(ranked_data)} players")

    def _transition_to_completed(self) -> None:
        """Transition tournament status to COMPLETED"""
        logger.info("🎯 Transitioning to COMPLETED")

        tournament = self.db.query(Semester).filter(Semester.id == self.tournament_id).first()
        tournament.tournament_status = "COMPLETED"
        self.db.commit()

        self.execution_steps.append("Status transitioned to COMPLETED")
        logger.info("✅ Tournament status → COMPLETED")

    def _distribute_rewards(self) -> Any:
        """Distribute rewards using orchestrator"""
        logger.info("🎁 Distributing rewards")

        result = tournament_reward_orchestrator.distribute_rewards_for_tournament(
            db=self.db,
            tournament_id=self.tournament_id,
            distributed_by=None,
            force_redistribution=False
        )

        # Manually transition status to REWARDS_DISTRIBUTED
        # (The API endpoint does this, but direct orchestrator call doesn't)
        tournament = self.db.query(Semester).filter(Semester.id == self.tournament_id).first()
        tournament.tournament_status = "REWARDS_DISTRIBUTED"
        self.db.commit()

        self.execution_steps.append(f"Rewards distributed (Status: {tournament.tournament_status})")
        logger.info(f"✅ Rewards distributed, status: {tournament.tournament_status}")

        return result

    def _calculate_verdict(
        self,
        user_ids: List[int],
        skills_to_test: List[str],
        distribution_result: Any,
        skills_before_snapshot: Dict[int, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calculate verdict and build response data"""
        from app.services.sandbox_verdict_calculator import SandboxVerdictCalculator

        calculator = SandboxVerdictCalculator(self.db)

        return calculator.calculate_verdict(
            tournament_id=self.tournament_id,
            expected_participant_count=len(user_ids),
            skills_to_test=skills_to_test,
            distribution_result=distribution_result,
            skills_before_snapshot=skills_before_snapshot
        )

    def _get_current_stage(self) -> str:
        """Get current execution stage for error reporting"""
        if not self.execution_steps:
            return "INITIALIZATION"

        last_step = self.execution_steps[-1]

        if "created" in last_step.lower():
            return "TOURNAMENT_CREATION"
        elif "enrolled" in last_step.lower():
            return "ENROLLMENT"
        elif "rankings" in last_step.lower():
            return "RANKING_GENERATION"
        elif "completed" in last_step.lower():
            return "STATUS_TRANSITION"
        elif "rewards" in last_step.lower():
            return "REWARD_DISTRIBUTION"
        else:
            return "UNKNOWN"

    def _get_tournament_status(self) -> Optional[str]:
        """Get current tournament status"""
        if not self.tournament_id:
            return None

        tournament = self.db.query(Semester).filter(Semester.id == self.tournament_id).first()
        return tournament.tournament_status if tournament else None
