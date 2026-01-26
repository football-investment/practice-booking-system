"""
End-to-End Test for Knockout Tournament Type

Tests the complete lifecycle of a knockout tournament:
1. Creation
2. Enrollment
3. Session Generation
4. Result Submission & Auto-Progression
5. Final Standings
6. Rewards Distribution
7. Skill Progression Validation

Usage:
    pytest tests/tournament_types/test_knockout_tournament.py -v
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.user import User
from app.models.license import UserLicense
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.session import Session as SessionModel
from app.services.tournament_session_generator import TournamentSessionGenerator
from app.services.tournament.knockout_progression_service import KnockoutProgressionService
from app.services.tournament.leaderboard_service import TournamentLeaderboardService
from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_tournament


class TestKnockoutTournamentLifecycle:
    """
    End-to-end test for knockout tournament with 8 players
    """

    @pytest.fixture(scope="class")
    def db(self):
        """Database session fixture"""
        db = SessionLocal()
        yield db
        db.close()

    @pytest.fixture(scope="class")
    def tournament_type(self, db: Session):
        """Get knockout tournament type"""
        tournament_type = db.query(TournamentType).filter(
            TournamentType.code == "knockout"
        ).first()
        assert tournament_type is not None, "Knockout tournament type not found in database"
        return tournament_type

    @pytest.fixture(scope="class")
    def test_users(self, db: Session):
        """Create or get 8 test users for the tournament"""
        users = []
        for i in range(1, 9):
            user = db.query(User).filter(User.email == f"test_knockout_{i}@test.com").first()
            if not user:
                user = User(
                    email=f"test_knockout_{i}@test.com",
                    name=f"Test Player {i}",
                    role="USER"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                # Create active license
                license = UserLicense(
                    user_id=user.id,
                    specialization_type="LFA_FOOTBALL_PLAYER",
                    is_active=True,
                    football_skills={
                        "ball_control": 50.0,
                        "agility": 50.0,
                        "stamina": 50.0
                    }
                )
                db.add(license)
                db.commit()

            users.append(user)

        return users

    def test_1_create_knockout_tournament(self, db: Session, tournament_type):
        """Step 1: Create a knockout tournament"""
        tournament = Semester(
            name="Test Knockout Tournament",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            enrollment_start=datetime.now(),
            enrollment_deadline=datetime.now() + timedelta(hours=1),
            location="Test Field",
            city="Test City",
            country="HU",
            specialization_type="LFA_FOOTBALL_PLAYER",
            format="HEAD_TO_HEAD",
            tournament_type_id=tournament_type.id,
            tournament_status="ENROLLMENT_OPEN",
            measurement_unit="goals"
        )
        db.add(tournament)
        db.commit()
        db.refresh(tournament)

        # Assertions
        assert tournament.id is not None
        assert tournament.format == "HEAD_TO_HEAD"
        assert tournament.tournament_type_id == tournament_type.id
        assert tournament.tournament_status == "ENROLLMENT_OPEN"

        # Store tournament_id for later tests
        self.tournament_id = tournament.id

    def test_2_enroll_8_players(self, db: Session, test_users):
        """Step 2: Enroll 8 players (valid power-of-2)"""
        for user in test_users:
            enrollment = SemesterEnrollment(
                semester_id=self.tournament_id,
                user_id=user.id,
                user_license_id=db.query(UserLicense).filter(
                    UserLicense.user_id == user.id,
                    UserLicense.is_active == True
                ).first().id,
                request_status=EnrollmentStatus.APPROVED,
                is_active=True
            )
            db.add(enrollment)

        db.commit()

        # Assertions
        enrolled_count = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == self.tournament_id,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).count()
        assert enrolled_count == 8, f"Expected 8 enrollments, got {enrolled_count}"

    def test_3_validate_power_of_two_requirement(self, db: Session, tournament_type):
        """Step 3: Validate power-of-2 requirement"""
        # Verify tournament type requires power-of-2
        assert tournament_type.requires_power_of_two == True

        # Verify 8 is valid
        is_valid, error = tournament_type.validate_player_count(8)
        assert is_valid == True

        # Verify 7 is invalid
        is_valid, error = tournament_type.validate_player_count(7)
        assert is_valid == False
        assert "power of 2" in error.lower()

    def test_4_move_to_in_progress(self, db: Session):
        """Step 4: Move tournament to IN_PROGRESS status"""
        tournament = db.query(Semester).filter(Semester.id == self.tournament_id).first()
        tournament.tournament_status = "IN_PROGRESS"
        db.commit()

        assert tournament.tournament_status == "IN_PROGRESS"

    def test_5_generate_knockout_sessions(self, db: Session):
        """Step 5: Generate knockout bracket (7 matches + 1 bronze = 8 total)"""
        generator = TournamentSessionGenerator(db)

        # Check if can generate
        can_generate, reason = generator.can_generate_sessions(self.tournament_id)
        assert can_generate == True, f"Cannot generate sessions: {reason}"

        # Generate sessions
        success, message, sessions = generator.generate_sessions(
            tournament_id=self.tournament_id,
            parallel_fields=1,
            session_duration_minutes=90,
            break_minutes=15
        )

        assert success == True, f"Session generation failed: {message}"
        assert len(sessions) == 8, f"Expected 8 sessions (7 knockout + 1 bronze), got {len(sessions)}"

        # Verify session structure
        db_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id
        ).all()

        # Verify round names
        round_names = [s.title for s in db_sessions]
        assert any("Quarter-finals" in name for name in round_names), "Missing Quarter-finals"
        assert any("Semi-finals" in name for name in round_names), "Missing Semi-finals"
        assert any("Final" in name for name in round_names), "Missing Final"
        assert any("Bronze" in name or "3rd Place" in name for name in round_names), "Missing Bronze Match"

        # Verify first round has all participants
        qf_sessions = [s for s in db_sessions if "Quarter-finals" in s.title]
        for qf in qf_sessions:
            assert qf.participant_user_ids is not None, f"QF {qf.title} has no participants"
            assert len(qf.participant_user_ids) == 2, f"QF {qf.title} should have 2 participants"

        # Verify later rounds have NULL participants
        sf_sessions = [s for s in db_sessions if "Semi-finals" in s.title]
        for sf in sf_sessions:
            assert sf.participant_user_ids is None or len(sf.participant_user_ids) == 0, \
                f"SF {sf.title} should have NULL participants initially"

    def test_6_submit_quarterfinal_results(self, db: Session):
        """Step 6: Submit all QF results"""
        qf_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%Quarter-finals%")
        ).all()

        assert len(qf_sessions) == 4, f"Expected 4 QF matches, got {len(qf_sessions)}"

        for i, qf in enumerate(qf_sessions):
            # Winner is first participant
            winner_id = qf.participant_user_ids[0]
            loser_id = qf.participant_user_ids[1]

            qf.game_results = {
                "raw_results": {
                    str(winner_id): 3,
                    str(loser_id): 1
                }
            }
            qf.result_submitted = True
            qf.result_submitted_at = datetime.now()

        db.commit()

        # Verify all QF complete
        complete_qf = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%Quarter-finals%"),
            SessionModel.result_submitted == True
        ).count()
        assert complete_qf == 4, f"Expected 4 complete QF, got {complete_qf}"

    def test_7_auto_progression_to_semifinals(self, db: Session):
        """Step 7: Verify auto-progression to semifinals"""
        progression_service = KnockoutProgressionService(db)

        # Get first QF match
        qf = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%Quarter-finals%")
        ).first()

        # Trigger progression
        progression_service.process_knockout_progression(qf.id)

        # Verify semifinals populated
        sf_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%Semi-finals%")
        ).all()

        for sf in sf_sessions:
            assert sf.participant_user_ids is not None, f"SF {sf.title} participants not populated"
            assert len(sf.participant_user_ids) == 2, f"SF {sf.title} should have 2 participants"

    def test_8_submit_semifinal_results(self, db: Session):
        """Step 8: Submit all SF results"""
        sf_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%Semi-finals%")
        ).all()

        assert len(sf_sessions) == 2, f"Expected 2 SF matches, got {len(sf_sessions)}"

        for sf in sf_sessions:
            winner_id = sf.participant_user_ids[0]
            loser_id = sf.participant_user_ids[1]

            sf.game_results = {
                "raw_results": {
                    str(winner_id): 2,
                    str(loser_id): 0
                }
            }
            sf.result_submitted = True
            sf.result_submitted_at = datetime.now()

        db.commit()

    def test_9_auto_progression_to_final_and_bronze(self, db: Session):
        """Step 9: Verify auto-progression to Final and Bronze"""
        progression_service = KnockoutProgressionService(db)

        # Get first SF match
        sf = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%Semi-finals%")
        ).first()

        # Trigger progression
        progression_service.process_knockout_progression(sf.id)

        # Verify Final populated
        final = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%final%"),
            ~SessionModel.title.ilike("%quarter-final%"),
            ~SessionModel.title.ilike("%semi-final%"),
            ~SessionModel.title.ilike("%bronze%"),
            ~SessionModel.title.ilike("%3rd%")
        ).first()

        assert final is not None, "Final match not found"
        assert final.participant_user_ids is not None, "Final participants not populated"
        assert len(final.participant_user_ids) == 2, "Final should have 2 participants"

        # Verify Bronze populated
        bronze = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%bronze%") | SessionModel.title.ilike("%3rd%")
        ).first()

        assert bronze is not None, "Bronze match not found"
        assert bronze.participant_user_ids is not None, "Bronze participants not populated"
        assert len(bronze.participant_user_ids) == 2, "Bronze should have 2 participants"

    def test_10_submit_final_and_bronze_results(self, db: Session):
        """Step 10: Submit Final and Bronze results"""
        # Final
        final = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%final%"),
            ~SessionModel.title.ilike("%quarter-final%"),
            ~SessionModel.title.ilike("%semi-final%"),
            ~SessionModel.title.ilike("%bronze%")
        ).first()

        final.game_results = {
            "raw_results": {
                str(final.participant_user_ids[0]): 1,
                str(final.participant_user_ids[1]): 0
            }
        }
        final.result_submitted = True
        final.result_submitted_at = datetime.now()

        # Bronze
        bronze = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%bronze%") | SessionModel.title.ilike("%3rd%")
        ).first()

        bronze.game_results = {
            "raw_results": {
                str(bronze.participant_user_ids[0]): 2,
                str(bronze.participant_user_ids[1]): 1
            }
        }
        bronze.result_submitted = True
        bronze.result_submitted_at = datetime.now()

        db.commit()

    def test_11_calculate_final_standings(self, db: Session):
        """Step 11: Calculate final standings"""
        # Move to COMPLETED
        tournament = db.query(Semester).filter(Semester.id == self.tournament_id).first()
        tournament.tournament_status = "COMPLETED"
        db.commit()

        # Get leaderboard
        leaderboard_service = TournamentLeaderboardService(db)
        leaderboard = leaderboard_service.calculate_leaderboard(self.tournament_id)

        # Assertions
        assert "final_standings" in leaderboard, "No final_standings in leaderboard"
        final_standings = leaderboard["final_standings"]

        assert len(final_standings) == 8, f"Expected 8 final standings, got {len(final_standings)}"

        # Verify podium
        champion = final_standings[0]
        runner_up = final_standings[1]
        third_place = final_standings[2]

        assert champion["rank"] == 1
        assert champion["title"] == "Champion"

        assert runner_up["rank"] == 2
        assert runner_up["title"] == "Runner-up"

        assert third_place["rank"] == 3
        assert third_place["title"] == "Third Place"

    def test_12_distribute_rewards(self, db: Session):
        """Step 12: Distribute rewards"""
        result = distribute_rewards_for_tournament(
            db=db,
            tournament_id=self.tournament_id,
            distributed_by=None,
            force_redistribution=False
        )

        # Assertions
        assert result.total_participants == 8, f"Expected 8 participants, got {result.total_participants}"
        assert len(result.rewards_distributed) == 8, f"Expected 8 rewards, got {len(result.rewards_distributed)}"

        # Verify rewards vary by placement
        rewards_by_placement = {r.participation.placement: r for r in result.rewards_distributed}

        champion_reward = rewards_by_placement[1]
        runner_up_reward = rewards_by_placement[2]

        assert champion_reward.participation.total_xp > runner_up_reward.participation.total_xp, \
            "Champion should get more XP than runner-up"

        assert champion_reward.participation.credits > runner_up_reward.participation.credits, \
            "Champion should get more credits than runner-up"

    def test_13_validate_skill_progression(self, db: Session):
        """Step 13: Validate skill progression (dynamic, capped at 99)"""
        from app.services.skill_progression_service import get_skill_profile

        # Get champion
        final = db.query(SessionModel).filter(
            SessionModel.semester_id == self.tournament_id,
            SessionModel.title.ilike("%final%"),
            ~SessionModel.title.ilike("%quarter-final%"),
            ~SessionModel.title.ilike("%semi-final%")
        ).first()

        champion_id = list(final.game_results["raw_results"].keys())[0] if final.game_results else None
        assert champion_id is not None, "Cannot determine champion"

        # Get skill profile
        profile = get_skill_profile(db, int(champion_id))

        # Assertions
        assert "skills" in profile
        assert "average_level" in profile

        # Check no skill exceeds 99.0
        for skill_key, skill_data in profile["skills"].items():
            assert skill_data["current_level"] <= 99.0, \
                f"Skill {skill_key} exceeds cap: {skill_data['current_level']}"

    def test_14_cleanup(self, db: Session):
        """Step 14: Optional cleanup (comment out to inspect database)"""
        # Uncomment to delete test tournament
        # tournament = db.query(Semester).filter(Semester.id == self.tournament_id).first()
        # db.delete(tournament)
        # db.commit()
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
