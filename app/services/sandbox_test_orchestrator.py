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

# Legacy fallback pool (used only when no @lfa-seed.hu users are found in DB)
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
        ranking_distribution: str = "NORMAL",
        game_preset_id: Optional[int] = None,
        game_config_overrides: Optional[Dict] = None,
        selected_users: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete sandbox test

        Args:
            tournament_type_code: Tournament type code (league, knockout, hybrid)
            skills_to_test: List of skill names to test
            player_count: Number of synthetic players (4-16)
            performance_variation: LOW, MEDIUM, HIGH
            ranking_distribution: NORMAL, TOP_HEAVY, BOTTOM_HEAVY
            game_preset_id: Optional game preset ID (P3)
            game_config_overrides: Optional game config overrides (P3)

        Returns:
            Complete test results including verdict, skill progression, top/bottom performers
        """
        self.start_time = datetime.now()
        self.test_run_id = f"sandbox-{self.start_time.strftime('%Y-%m-%d-%H-%M-%S')}-{random.randint(1000, 9999)}"

        logger.info(f"🧪 Starting sandbox test: {self.test_run_id} (preset={game_preset_id})")

        try:
            # Step 1: Create tournament
            self._create_tournament(
                tournament_type_code,
                skills_to_test,
                player_count,
                game_preset_id,
                game_config_overrides
            )

            # Step 2: Enroll participants
            enrolled_users = self._enroll_participants(player_count, selected_users)

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

            # Step 7: Cleanup sandbox data (maintain isolation for next run)
            self._cleanup_sandbox_data()

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
        player_count: int,
        game_preset_id: Optional[int] = None,
        game_config_overrides: Optional[Dict] = None
    ) -> None:
        """Create temporary tournament with P1+P2+P3 separated configurations"""
        logger.info(f"📋 Creating tournament: type={tournament_type_code}, players={player_count}, preset={game_preset_id}")

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

        # Create tournament (P2: without configuration fields, will be added as separate entity)
        # 🆓 CRITICAL FIX: Set enrollment_cost=0 for sandbox tournaments
        # Prevents credit deductions during testing and ensures clean audit trail
        # See: CRITICAL_FINDING_SANDBOX_CREDIT_LEAK.md for details
        # Get Grand Master instructor for sandbox tournaments (id=3, grandmaster@lfa.com)
        from app.models.user import User, UserRole
        grandmaster = self.db.query(User).filter(
            User.role == UserRole.INSTRUCTOR,
            User.email == "grandmaster@lfa.com"
        ).first()

        tournament = Semester(
            code=f"SANDBOX-{self.test_run_id}",
            name=f"SANDBOX-TEST-{tournament_type_code.upper()}-{self.start_time.strftime('%Y-%m-%d')}",
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date(),
            is_active=True,
            tournament_status="IN_PROGRESS",  # Start in IN_PROGRESS for sandbox (skip instructor assignment)
            master_instructor_id=grandmaster.id if grandmaster else None,  # Assign Grand Master
            enrollment_cost=0  # 🆓 FREE for testing - no credit deductions!
        )

        self.db.add(tournament)
        self.db.commit()
        self.db.refresh(tournament)

        self.tournament_id = tournament.id

        # 🏆 P2: Create separate TournamentConfiguration
        from app.models.tournament_configuration import TournamentConfiguration

        # Extract INDIVIDUAL scoring config from game_config_overrides if present
        # ✅ FIX: Use "HEAD_TO_HEAD" as scoring_type for HEAD_TO_HEAD tournaments
        # (scoring_type column has NOT NULL constraint, cannot use NULL)
        scoring_type = "HEAD_TO_HEAD"  # default for HEAD_TO_HEAD tournaments
        number_of_rounds = 1  # default
        measurement_unit = None
        ranking_direction = None
        is_individual_ranking = False

        if (game_config_overrides and
            "individual_config" in game_config_overrides and
            game_config_overrides["individual_config"] is not None):
            individual_config = game_config_overrides["individual_config"]
            scoring_type = individual_config.get("scoring_type", "PLACEMENT")
            number_of_rounds = individual_config.get("number_of_rounds", 1)
            measurement_unit = individual_config.get("measurement_unit")
            ranking_direction = individual_config.get("ranking_direction")
            is_individual_ranking = True
            logger.info(f"🎯 Applying INDIVIDUAL config: scoring_type={scoring_type}, rounds={number_of_rounds}, unit={measurement_unit}, direction={ranking_direction}")

        # 🎯 CRITICAL FIX: INDIVIDUAL_RANKING tournaments MUST NOT have tournament_type_id
        # The Semester.format property has a fallback chain:
        # 1. tournament_type.format (if tournament_type_id is set)
        # 2. game_preset.format_config (if game_preset_id is set)
        # 3. Default: "INDIVIDUAL_RANKING"
        # For INDIVIDUAL tournaments, we use the default fallback (tournament_type_id=NULL)
        # For HEAD_TO_HEAD tournaments, we use the requested tournament type (league, knockout, etc.)
        if is_individual_ranking:
            tournament_type_id_value = None  # NULL for INDIVIDUAL_RANKING
            logger.info(f"🔄 Setting tournament_type_id=NULL for INDIVIDUAL_RANKING tournament (format will use default fallback)")
        else:
            tournament_type_id_value = tournament_type.id  # Set for HEAD_TO_HEAD tournaments

        tournament_config_obj = TournamentConfiguration(
            semester_id=tournament.id,
            tournament_type_id=tournament_type_id_value,
            participant_type="INDIVIDUAL",
            is_multi_day=False,
            max_players=player_count,
            parallel_fields=1,
            scoring_type=scoring_type,
            number_of_rounds=number_of_rounds,
            measurement_unit=measurement_unit,
            ranking_direction=ranking_direction,
            assignment_type="OPEN_ASSIGNMENT",
            sessions_generated=False
        )
        self.db.add(tournament_config_obj)
        self.db.commit()

        # 🎁 P1: Create separate TournamentRewardConfig
        from app.models.tournament_reward_config import TournamentRewardConfig
        reward_config_obj = TournamentRewardConfig(
            semester_id=tournament.id,
            reward_policy_name="sandbox_test",
            reward_config=reward_config_data
        )
        self.db.add(reward_config_obj)
        self.db.commit()

        # 🎮 P3: Create separate GameConfiguration
        from app.models.game_configuration import GameConfiguration
        from app.models.game_preset import GamePreset

        # If game preset is provided, use it as template
        final_game_config = None
        if game_preset_id:
            preset = self.db.query(GamePreset).filter(GamePreset.id == game_preset_id).first()
            if preset:
                logger.info(f"🎮 Using game preset: {preset.name} (ID: {game_preset_id})")

                # Start with preset config
                final_game_config = preset.game_config.copy()

                # Apply overrides if provided
                if game_config_overrides:
                    logger.info(f"🔧 Applying game config overrides: {list(game_config_overrides.keys())}")

                    # Override skill config
                    if "skill_config" in game_config_overrides:
                        final_game_config.setdefault("skill_config", {}).update(
                            game_config_overrides["skill_config"]
                        )

                    # Override simulation config (match probabilities, etc.)
                    if "simulation_config" in game_config_overrides:
                        final_game_config.setdefault("simulation_config", {}).update(
                            game_config_overrides["simulation_config"]
                        )

                # 🎯 CRITICAL FIX: Override format_config for INDIVIDUAL_RANKING tournaments
                # If INDIVIDUAL scoring mode, replace format_config key with INDIVIDUAL_RANKING
                if is_individual_ranking and "format_config" in final_game_config:
                    # Extract existing format_config value (rules, etc.)
                    existing_format_configs = final_game_config["format_config"]
                    # Get the first format's config (HEAD_TO_HEAD or INDIVIDUAL_RANKING)
                    format_rules = list(existing_format_configs.values())[0] if existing_format_configs else {}

                    # Replace with INDIVIDUAL_RANKING key
                    final_game_config["format_config"] = {
                        "INDIVIDUAL_RANKING": format_rules
                    }
                    logger.info(f"🔄 Overrode format_config to use INDIVIDUAL_RANKING key (was {list(existing_format_configs.keys())})")
            else:
                logger.warning(f"⚠️ Game preset {game_preset_id} not found, using basic config")

        # If no preset or preset not found, build basic game config
        if not final_game_config:
            # 🎯 CRITICAL FIX: Use correct format key based on scoring mode
            # If INDIVIDUAL scoring mode → INDIVIDUAL_RANKING format
            # If HEAD_TO_HEAD scoring mode → use tournament_type.format (league/knockout/hybrid)
            format_key = "INDIVIDUAL_RANKING" if is_individual_ranking else tournament_type.format

            final_game_config = {
                "version": "1.0",
                "skill_config": {
                    "skills_tested": skills_to_test,
                    "skill_weights": {skill: 1.0 / len(skills_to_test) for skill in skills_to_test},
                    "skill_impact_on_matches": True
                },
                "format_config": {
                    format_key: {
                        "ranking_rules": {
                            "primary": "points",
                            "tiebreakers": ["goal_difference", "goals_for", "user_id"]
                        }
                    }
                },
                "simulation_config": {
                    "player_selection": "auto",
                    "ranking_distribution": "NORMAL",
                    "performance_variation": "MEDIUM"
                },
                "metadata": {
                    "game_category": "sandbox_test",
                    "difficulty_level": "intermediate"
                }
            }

        # 🎯 CRITICAL FIX: INDIVIDUAL_RANKING tournaments should NOT have game_preset_id
        # because game presets contain format_config that might override the format property
        # to HEAD_TO_HEAD instead of INDIVIDUAL_RANKING
        if is_individual_ranking:
            logger.info(f"🔄 Setting game_preset_id=NULL for INDIVIDUAL_RANKING tournament (to avoid format override)")
            game_preset_id_value = None
        else:
            game_preset_id_value = game_preset_id

        game_config_obj = GameConfiguration(
            semester_id=tournament.id,
            game_preset_id=game_preset_id_value,
            game_config=final_game_config,
            game_config_overrides=game_config_overrides
        )
        self.db.add(game_config_obj)
        self.db.commit()

        self.execution_steps.append(f"Tournament created (ID: {self.tournament_id}, Status: IN_PROGRESS)")
        logger.info(f"✅ Tournament created: ID={self.tournament_id}, Config: P2+P3, Reward: P1")

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

    def _enroll_participants(self, player_count: int, selected_users: Optional[List[int]] = None) -> List[int]:
        """Enroll synthetic participants

        Args:
            player_count: Number of participants to enroll
            selected_users: Optional list of specific user IDs to enroll (from UI selection)
                           If None, queries all active @lfa-seed.hu users with active licenses
                           (ordered by ID, first N selected deterministically).
                           Falls back to TEST_USER_POOL if no seed users found.
        """
        logger.info(f"👥 Enrolling {player_count} participants")

        # Use provided selected_users if available (UI selection), otherwise use deterministic pool
        if selected_users:
            logger.info(f"✅ Using UI-selected participants: {selected_users}")
            # Validate count matches
            if len(selected_users) != player_count:
                logger.warning(
                    f"⚠️  Participant count mismatch: UI selected {len(selected_users)}, "
                    f"expected {player_count}. Using UI selection."
                )
                player_count = len(selected_users)  # Use actual UI selection count
        else:
            # ✅ DETERMINISTIC: Query all active @lfa-seed.hu users with active licenses
            from app.models.user import User, UserRole

            seed_rows = (
                self.db.query(User.id)
                .join(UserLicense, UserLicense.user_id == User.id)
                .filter(
                    User.email.like("%@lfa-seed.hu"),
                    User.is_active == True,
                    UserLicense.is_active == True,
                )
                .order_by(User.id)
                .all()
            )
            seed_user_ids = [row.id for row in seed_rows]

            if seed_user_ids:
                logger.info(
                    f"🌱 Seed pool: {len(seed_user_ids)} @lfa-seed.hu users with active licenses"
                )
                pool = seed_user_ids
            else:
                # Fallback: legacy hardcoded pool
                logger.warning(
                    "⚠️  No @lfa-seed.hu users found — falling back to TEST_USER_POOL"
                )
                pool = sorted(TEST_USER_POOL)

            if player_count > len(pool):
                raise ValueError(
                    f"Cannot select {player_count} users from pool of {len(pool)}. "
                    f"Increase @lfa-seed.hu user count or reduce player_count."
                )

            # ✅ DETERMINISTIC: Take first N players from ordered pool
            selected_users = pool[:player_count]
            logger.info(f"🔒 DETERMINISTIC selection: first {player_count} from pool of {len(pool)}")

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
            from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus

            enrollment = SemesterEnrollment(
                user_id=user_id,
                semester_id=self.tournament_id,
                user_license_id=active_license.id,
                is_active=True,
                payment_verified=True,
                request_status=EnrollmentStatus.APPROVED  # Sandbox: auto-approve enrollments
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
        """Generate synthetic tournament rankings (DETERMINISTIC - no randomness)"""
        logger.info(f"🏆 Generating DETERMINISTIC rankings: distribution={ranking_distribution}")

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

        # ✅ DETERMINISTIC: NO random noise applied
        # performance_variation is IGNORED to ensure reproducibility
        logger.info(f"🔒 DETERMINISTIC mode: NO random variation applied (ignoring performance_variation={performance_variation})")
        final_points = base_points  # Use exact base points without noise

        # Sort by points descending and assign ranks
        ranked_data = sorted(zip(user_ids, final_points), key=lambda x: x[1], reverse=True)

        # Create tournament rankings (needed for reward distribution and verdict calculation)
        for rank, (user_id, points) in enumerate(ranked_data, start=1):
            ranking = TournamentRanking(
                tournament_id=self.tournament_id,
                user_id=user_id,
                participant_type="INDIVIDUAL",
                rank=rank,
                points=int(points),
                wins=0,  # Sandbox: simplified ranking
                losses=0,
                draws=0,
                goals_for=0,
                goals_against=0
            )
            self.db.add(ranking)

        self.db.commit()

        self.execution_steps.append(f"Rankings created ({len(ranked_data)} participants)")
        logger.info(f"✅ Rankings persisted for {len(ranked_data)} players")

    def _transition_to_completed(self) -> None:
        """
        Transition tournament status to COMPLETED

        For sandbox tests, we complete the tournament directly to enable verdict calculation.
        """
        logger.info("🎯 Transitioning tournament to COMPLETED")

        tournament = self.db.query(Semester).filter(Semester.id == self.tournament_id).first()
        if not tournament:
            raise ValueError(f"Tournament {self.tournament_id} not found")

        tournament.tournament_status = "COMPLETED"
        self.db.commit()

        self.execution_steps.append(f"Tournament transitioned to COMPLETED")
        logger.info(f"✅ Tournament {self.tournament_id} status: IN_PROGRESS → COMPLETED")

    def _distribute_rewards(self) -> Any:
        """
        Distribute rewards using orchestrator

        🧪 SANDBOX MODE: Skills are calculated in-memory only, NOT persisted to DB.
        This ensures full state isolation and reproducibility across test runs.
        """
        logger.info("🎁 Distributing tournament rewards (SANDBOX MODE: no skill persistence)")

        result = tournament_reward_orchestrator.distribute_rewards_for_tournament(
            db=self.db,
            tournament_id=self.tournament_id,
            distributed_by=None,
            force_redistribution=False,
            is_sandbox_mode=True  # 🧪 CRITICAL: Prevents skill changes from persisting to DB
        )

        tournament = self.db.query(Semester).filter(Semester.id == self.tournament_id).first()
        tournament.tournament_status = "REWARDS_DISTRIBUTED"
        self.db.commit()

        self.execution_steps.append(f"Rewards distributed ({result.total_participants} participants, SANDBOX MODE)")
        logger.info(f"✅ Rewards distributed: {result.total_participants} participants (skills not persisted)")

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

    def _cleanup_sandbox_data(self) -> None:
        """
        🧹 CLEANUP: Delete sandbox tournament data to maintain isolation

        This ensures that each sandbox run starts from a clean state.
        Deletes:
        - TournamentParticipation records (skill points, XP, credits)
        - TournamentRanking records
        - TournamentBadge records
        - XPTransaction records (tournament-related)
        - CreditTransaction records (tournament-related)
        - SemesterEnrollment records
        - GameConfiguration
        - Semester (tournament) itself

        🔒 CRITICAL: This prevents skill deltas from accumulating across runs.
        """
        if not self.tournament_id:
            logger.warning("No tournament_id set, skipping cleanup")
            return

        logger.info(f"🧹 Cleaning up sandbox data for tournament {self.tournament_id}")

        try:
            from app.models.tournament_achievement import TournamentParticipation, TournamentBadge
            from app.models.tournament_ranking import TournamentRanking
            from app.models.xp_transaction import XPTransaction
            from app.models.credit_transaction import CreditTransaction
            from app.models.semester_enrollment import SemesterEnrollment
            from app.models.game_configuration import GameConfiguration

            # Delete in reverse dependency order

            # 1. Delete tournament participations
            participation_count = self.db.query(TournamentParticipation).filter(
                TournamentParticipation.semester_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {participation_count} TournamentParticipation records")

            # 2. Delete tournament badges
            badge_count = self.db.query(TournamentBadge).filter(
                TournamentBadge.semester_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {badge_count} TournamentBadge records")

            # 3. Delete tournament rankings
            ranking_count = self.db.query(TournamentRanking).filter(
                TournamentRanking.tournament_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {ranking_count} TournamentRanking records")

            # 4. Delete XP transactions (tournament-related)
            xp_count = self.db.query(XPTransaction).filter(
                XPTransaction.semester_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {xp_count} XPTransaction records")

            # 5. Delete credit transactions (tournament-related)
            credit_count = self.db.query(CreditTransaction).filter(
                CreditTransaction.semester_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {credit_count} CreditTransaction records")

            # 6. Delete semester enrollments
            enrollment_count = self.db.query(SemesterEnrollment).filter(
                SemesterEnrollment.semester_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {enrollment_count} SemesterEnrollment records")

            # 7. Delete game configuration
            game_config_count = self.db.query(GameConfiguration).filter(
                GameConfiguration.semester_id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {game_config_count} GameConfiguration records")

            # 8. Delete tournament itself
            tournament_count = self.db.query(Semester).filter(
                Semester.id == self.tournament_id
            ).delete()
            logger.info(f"   Deleted {tournament_count} Semester (tournament) records")

            self.db.commit()

            self.execution_steps.append(f"Sandbox data cleaned up (tournament {self.tournament_id} deleted)")
            logger.info(f"✅ Sandbox cleanup complete for tournament {self.tournament_id}")

        except Exception as e:
            logger.error(f"❌ Cleanup failed for tournament {self.tournament_id}: {e}", exc_info=True)
            self.db.rollback()
            # Don't fail the entire test on cleanup error
            # Cleanup failure just means next run might see stale data
