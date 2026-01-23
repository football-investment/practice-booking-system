"""
⚽ Football Skill Assessment Service - V2
Handles assessment creation and average calculation for LFA Player skills
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional
from datetime import datetime, timezone

from ..models.football_skill_assessment import FootballSkillAssessment
from ..models.license import UserLicense
from ..models.user import User

class FootballSkillService:
    """Service for managing football skill assessments"""

    # Valid skill names
    VALID_SKILLS = ['heading', 'shooting', 'crossing', 'passing', 'dribbling', 'ball_control']

    def __init__(self, db: Session):
        self.db = db

    def create_assessment(
        self,
        user_license_id: int,
        skill_name: str,
        points_earned: int,
        points_total: int,
        assessed_by: int,
        notes: Optional[str] = None
    ) -> FootballSkillAssessment:
        """
        Create a new skill assessment and update cached average

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill name (heading, shooting, etc.)
            points_earned: Points earned (e.g., 7)
            points_total: Total points (e.g., 10)
            assessed_by: Instructor user ID
            notes: Optional notes

        Returns:
            Created assessment
        """
        # Validate skill name
        if skill_name not in self.VALID_SKILLS:
            raise ValueError(f"Invalid skill name: {skill_name}. Must be one of {self.VALID_SKILLS}")

        # Validate points
        if points_earned < 0:
            raise ValueError("Points earned cannot be negative")
        if points_total <= 0:
            raise ValueError("Total points must be greater than 0")
        if points_earned > points_total:
            raise ValueError(f"Points earned ({points_earned}) cannot exceed total points ({points_total})")

        # Calculate percentage
        percentage = FootballSkillAssessment.calculate_percentage(points_earned, points_total)

        # Create assessment
        assessment = FootballSkillAssessment(
            user_license_id=user_license_id,
            skill_name=skill_name,
            points_earned=points_earned,
            points_total=points_total,
            percentage=percentage,
            assessed_by=assessed_by,
            assessed_at=datetime.now(timezone.utc),
            notes=notes
        )

        self.db.add(assessment)
        self.db.flush()  # Get ID without committing

        # Recalculate and update cached average
        self.recalculate_skill_average(user_license_id, skill_name)

        return assessment

    def recalculate_skill_average(self, user_license_id: int, skill_name: str) -> float:
        """
        Recalculate average for a specific skill and update cached value

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill to recalculate

        Returns:
            New average percentage
        """
        # Get all assessments for this skill
        assessments = self.db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == user_license_id,
            FootballSkillAssessment.skill_name == skill_name
        ).all()

        if not assessments:
            return 0.0

        # Calculate average
        average = sum(a.percentage for a in assessments) / len(assessments)
        average = round(average, 1)

        # Update cached value in user_licenses.football_skills JSON
        license = self.db.query(UserLicense).filter(UserLicense.id == user_license_id).first()
        if license:
            if not license.football_skills:
                license.football_skills = {}

            license.football_skills[skill_name] = average

            # Mark as modified (for JSON field)
            flag_modified(license, 'football_skills')

        return average

    def recalculate_all_skill_averages(self, user_license_id: int) -> Dict[str, float]:
        """
        Recalculate averages for ALL 6 skills

        Args:
            user_license_id: UserLicense ID

        Returns:
            Dict of skill_name -> average
        """
        averages = {}
        for skill in self.VALID_SKILLS:
            avg = self.recalculate_skill_average(user_license_id, skill)
            averages[skill] = avg

        return averages

    def get_assessment_history(
        self,
        user_license_id: int,
        skill_name: str,
        limit: Optional[int] = None
    ):
        """
        Get assessment history for a specific skill with averages

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill name to get history for
            limit: Optional limit results

        Returns:
            SkillAssessmentHistoryResponse with current average, count, and assessments
        """
        assessments = self.db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == user_license_id,
            FootballSkillAssessment.skill_name == skill_name
        ).order_by(FootballSkillAssessment.assessed_at.desc())

        if limit:
            assessments = assessments.limit(limit)

        assessments = assessments.all()

        # Calculate current average
        if assessments:
            current_average = sum(a.percentage for a in assessments) / len(assessments)
            current_average = round(current_average, 1)
        else:
            current_average = 0.0

        # Get total count
        total_count = self.db.query(func.count(FootballSkillAssessment.id)).filter(
            FootballSkillAssessment.user_license_id == user_license_id,
            FootballSkillAssessment.skill_name == skill_name
        ).scalar() or 0

        # Convert to response schema
        assessment_responses = []
        for assessment in assessments:
            # Get assessor name
            assessor = self.db.query(User).filter(User.id == assessment.assessed_by).first()
            assessor_name = assessor.name if assessor else "Unknown"

            assessment_responses.append(SkillAssessmentResponse(
                id=assessment.id,
                user_license_id=assessment.user_license_id,
                skill_name=assessment.skill_name,
                points_earned=assessment.points_earned,
                points_total=assessment.points_total,
                percentage=assessment.percentage,
                assessed_by=assessment.assessed_by,
                assessed_at=assessment.assessed_at,
                assessor_name=assessor_name,
                notes=assessment.notes
            ))

        return SkillAssessmentHistoryResponse(
            skill_name=skill_name,
            current_average=current_average,
            assessment_count=total_count,
            assessments=assessment_responses
        )

    def get_current_averages(self, user_license_id: int) -> Dict[str, float]:
        """
        Get current skill averages from cached values

        Args:
            user_license_id: UserLicense ID

        Returns:
            Dict of skill_name -> average (0.0 if not assessed yet)
        """
        license = self.db.query(UserLicense).filter(UserLicense.id == user_license_id).first()

        if not license or not license.football_skills:
            return {skill: 0.0 for skill in self.VALID_SKILLS}

        averages = {}
        for skill in self.VALID_SKILLS:
            averages[skill] = license.football_skills.get(skill, 0.0)

        return averages

    def get_assessment_counts(self, user_license_id: int) -> Dict[str, int]:
        """
        Get count of assessments per skill

        Args:
            user_license_id: UserLicense ID

        Returns:
            Dict of skill_name -> count
        """
        counts = {}
        for skill in self.VALID_SKILLS:
            count = self.db.query(func.count(FootballSkillAssessment.id)).filter(
                FootballSkillAssessment.user_license_id == user_license_id,
                FootballSkillAssessment.skill_name == skill
            ).scalar()
            counts[skill] = count or 0

        return counts

    def bulk_create_assessments(
        self,
        user_license_id: int,
        assessments: Dict[str, Dict],
        assessed_by: int
    ) -> Dict[str, FootballSkillAssessment]:
        """
        Create assessments for multiple skills at once

        Args:
            user_license_id: UserLicense ID
            assessments: Dict of skill_name -> {points_earned, points_total, notes}
            assessed_by: Instructor user ID

        Returns:
            Dict of skill_name -> created assessment

        Example:
            assessments = {
                'heading': {'points_earned': 7, 'points_total': 10, 'notes': 'Good'},
                'shooting': {'points_earned': 8, 'points_total': 10, 'notes': None},
                ...
            }
        """
        created = {}

        for skill_name, data in assessments.items():
            if skill_name not in self.VALID_SKILLS:
                continue

            assessment = self.create_assessment(
                user_license_id=user_license_id,
                skill_name=skill_name,
                points_earned=data['points_earned'],
                points_total=data['points_total'],
                assessed_by=assessed_by,
                notes=data.get('notes')
            )
            created[skill_name] = assessment

        # Commit all at once
        self.db.commit()

        return created
