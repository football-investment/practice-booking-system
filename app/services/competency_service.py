"""
Competency Service
Automatic competency assessment and skill tracking
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CompetencyService:
    """Service for competency assessment and tracking"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # AUTOMATIC ASSESSMENT FROM QUIZZES AND EXERCISES
    # ============================================================================

    def assess_from_quiz(self, user_id: int, quiz_id: int, quiz_attempt_id: int, score: float):
        """
        Automatically assess competencies based on quiz performance

        Args:
            user_id: Student ID
            quiz_id: Quiz ID
            quiz_attempt_id: Quiz attempt ID
            score: Quiz score (0-100)
        """
        logger.info(f"Assessing competencies from quiz {quiz_id} for user {user_id}, score={score}")

        # Get quiz metadata
        quiz_data = self.db.execute(text("""
            SELECT specialization_id, lesson_id, category
            FROM quizzes
            WHERE id = :quiz_id
        """), {"quiz_id": quiz_id}).fetchone()

        if not quiz_data or not quiz_data.specialization_id:
            logger.warning(f"Quiz {quiz_id} has no specialization, skipping competency assessment")
            return

        specialization_id = quiz_data.specialization_id
        lesson_id = quiz_data.lesson_id
        category = quiz_data.category

        # Get lesson metadata if available
        lesson_tags = []
        if lesson_id:
            lesson_data = self.db.execute(text("""
                SELECT skill_focus_tags
                FROM lessons
                WHERE id = :lesson_id
            """), {"lesson_id": lesson_id}).fetchone()

            if lesson_data and lesson_data.skill_focus_tags:
                import json
                try:
                    lesson_tags = json.loads(lesson_data.skill_focus_tags)
                except:
                    lesson_tags = []

        # Map quiz category to competency categories
        category_mapping = {
            'MARKETING': 'Professional Skills',
            'ECONOMICS': 'Professional Skills',
            'INFORMATICS': 'Digital Competency',
            'SPORTS_PHYSIOLOGY': 'Physical Fitness',
            'NUTRITION': 'Physical Fitness'
        }

        target_category = category_mapping.get(category, None)

        # Get relevant competency categories
        categories = self.db.execute(text("""
            SELECT id, name
            FROM competency_categories
            WHERE specialization_id = :spec_id
            AND (:target_cat IS NULL OR name = :target_cat)
        """), {"spec_id": specialization_id, "target_cat": target_category}).fetchall()

        if not categories:
            logger.warning(f"No competency categories found for {specialization_id}")
            return

        # For each category, get skills and assess
        for category_row in categories:
            category_id = category_row.id
            category_name = category_row.name

            # Get skills for this category
            skills = self.db.execute(text("""
                SELECT id, name
                FROM competency_skills
                WHERE competency_category_id = :cat_id
            """), {"cat_id": category_id}).fetchall()

            if not skills:
                continue

            # Assess each skill
            for skill in skills:
                skill_id = skill.id
                skill_name = skill.name

                # Calculate skill score based on quiz score
                # Apply tag matching bonus if lesson has relevant tags
                skill_score = score  # Base score

                if lesson_tags and any(tag.lower() in skill_name.lower() for tag in lesson_tags):
                    skill_score = min(score + 5, 100)  # Bonus for relevant skills

                # Update skill score
                self._update_skill_score(user_id, skill_id, skill_score, quiz_attempt_id, 'QUIZ')

            # Update overall category competency
            self._update_competency_score(user_id, category_id, score, quiz_attempt_id, 'QUIZ')

        # Check for milestone achievements
        self._check_milestones(user_id, specialization_id)

        logger.info(f"Competency assessment complete for user {user_id}")

    def assess_from_exercise(self, user_id: int, exercise_submission_id: int, score: float):
        """
        Automatically assess competencies based on exercise submission

        Args:
            user_id: Student ID
            exercise_submission_id: Exercise submission ID
            score: Exercise score (0-100)
        """
        logger.info(f"Assessing competencies from exercise submission {exercise_submission_id} for user {user_id}, score={score}")

        # Get exercise metadata
        exercise_data = self.db.execute(text("""
            SELECT e.lesson_id, e.type, l.specialization_id
            FROM exercise_submissions es
            JOIN exercises e ON e.id = es.exercise_id
            JOIN lessons l ON l.id = e.lesson_id
            WHERE es.id = :submission_id
        """), {"submission_id": exercise_submission_id}).fetchone()

        if not exercise_data:
            logger.warning(f"Exercise submission {exercise_submission_id} not found")
            return

        specialization_id = exercise_data.specialization_id
        exercise_type = exercise_data.type

        # Map exercise type to competency categories
        type_mapping = {
            'CODING': 'Digital Competency',
            'PRACTICAL': 'Technical Skills',
            'VIDEO': 'Professional Skills',
            'PRESENTATION': 'Communication'
        }

        target_category = type_mapping.get(exercise_type, None)

        # Get relevant competency categories
        categories = self.db.execute(text("""
            SELECT id, name
            FROM competency_categories
            WHERE specialization_id = :spec_id
            AND (:target_cat IS NULL OR name = :target_cat)
        """), {"spec_id": specialization_id, "target_cat": target_category}).fetchall()

        if not categories:
            logger.warning(f"No competency categories found for {specialization_id}")
            return

        # Assess categories
        for category_row in categories:
            category_id = category_row.id

            # Get skills
            skills = self.db.execute(text("""
                SELECT id
                FROM competency_skills
                WHERE competency_category_id = :cat_id
            """), {"cat_id": category_id}).fetchall()

            # Update skills
            for skill in skills:
                self._update_skill_score(user_id, skill.id, score, exercise_submission_id, 'EXERCISE')

            # Update category
            self._update_competency_score(user_id, category_id, score, exercise_submission_id, 'EXERCISE')

        # Check milestones
        self._check_milestones(user_id, specialization_id)

        logger.info(f"Competency assessment complete for user {user_id}")

    def _update_skill_score(self, user_id: int, skill_id: int, score: float, source_id: int, source_type: str):
        """
        Update user's skill score using weighted average

        More recent assessments have higher weight:
        - Last 5 assessments: 0.4, 0.25, 0.2, 0.1, 0.05
        """
        # Insert assessment record
        self.db.execute(text("""
            INSERT INTO competency_assessments (
                user_id, competency_skill_id, score, assessment_type, source_id, assessed_at
            )
            VALUES (
                :user_id, :skill_id, :score, :assessment_type, :source_id, NOW()
            )
        """), {
            "user_id": user_id,
            "skill_id": skill_id,
            "score": score,
            "assessment_type": source_type,
            "source_id": source_id
        })

        # Get last 5 assessments for this skill
        assessments = self.db.execute(text("""
            SELECT score
            FROM competency_assessments
            WHERE user_id = :user_id AND competency_skill_id = :skill_id
            ORDER BY assessed_at DESC
            LIMIT 5
        """), {"user_id": user_id, "skill_id": skill_id}).fetchall()

        # Calculate weighted average
        scores = [float(a.score) for a in assessments]
        weights = [0.4, 0.25, 0.2, 0.1, 0.05][:len(scores)]
        weighted_avg = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

        # Determine level based on score
        level = self._score_to_level(weighted_avg)

        # Upsert user_skill_scores
        self.db.execute(text("""
            INSERT INTO user_skill_scores (
                user_id, competency_skill_id, current_score, percentage, last_assessed
            )
            VALUES (
                :user_id, :skill_id, :score, :score, NOW()
            )
            ON CONFLICT (user_id, competency_skill_id) DO UPDATE
            SET
                current_score = :score,
                percentage = :score,
                last_assessed = NOW(),
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "skill_id": skill_id,
            "score": weighted_avg
        })

        self.db.commit()

    def _update_competency_score(self, user_id: int, category_id: int, score: float, source_id: int, source_type: str):
        """
        Update user's overall competency score for a category
        Uses weighted average of recent assessments
        """
        # Insert assessment record
        self.db.execute(text("""
            INSERT INTO competency_assessments (
                user_id, competency_category_id, score, assessment_type, source_id, assessed_at
            )
            VALUES (
                :user_id, :category_id, :score, :assessment_type, :source_id, NOW()
            )
        """), {
            "user_id": user_id,
            "category_id": category_id,
            "score": score,
            "assessment_type": source_type,
            "source_id": source_id
        })

        # Get last 5 assessments
        assessments = self.db.execute(text("""
            SELECT score
            FROM competency_assessments
            WHERE user_id = :user_id AND competency_category_id = :category_id
            ORDER BY assessed_at DESC
            LIMIT 5
        """), {"user_id": user_id, "category_id": category_id}).fetchall()

        # Weighted average
        scores = [float(a.score) for a in assessments]
        weights = [0.4, 0.25, 0.2, 0.1, 0.05][:len(scores)]
        weighted_avg = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

        # Level
        level = self._score_to_level(weighted_avg)

        # Upsert user_competency_scores
        self.db.execute(text("""
            INSERT INTO user_competency_scores (
                user_id, competency_category_id, current_score, percentage, competency_level, last_assessed
            )
            VALUES (
                :user_id, :category_id, :score, :score, :level, NOW()
            )
            ON CONFLICT (user_id, competency_category_id) DO UPDATE
            SET
                current_score = :score,
                percentage = :score,
                competency_level = :level,
                last_assessed = NOW(),
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "category_id": category_id,
            "score": weighted_avg,
            "level": level
        })

        self.db.commit()

    def _score_to_level(self, score: float) -> int:
        """Convert numeric score to competency level (1-5)"""
        if score >= 90:
            return 5  # Expert
        elif score >= 75:
            return 4  # Proficient
        elif score >= 60:
            return 3  # Competent
        elif score >= 40:
            return 2  # Developing
        else:
            return 1  # Beginner

    def _check_milestones(self, user_id: int, specialization_id: str):
        """Check and award milestone achievements"""
        # Get all milestones for this specialization
        milestones = self.db.execute(text("""
            SELECT id, required_score, required_level, xp_reward
            FROM competency_milestones
            WHERE specialization_id = :spec_id
        """), {"spec_id": specialization_id}).fetchall()

        for milestone in milestones:
            milestone_id = milestone.id
            required_score = float(milestone.required_score)
            required_level = milestone.required_level
            xp_reward = milestone.xp_reward

            # Check if already achieved
            existing = self.db.execute(text("""
                SELECT id FROM user_competency_milestones
                WHERE user_id = :user_id AND milestone_id = :milestone_id
            """), {"user_id": user_id, "milestone_id": milestone_id}).fetchone()

            if existing:
                continue

            # Check if user meets requirements
            # Get user's current competencies
            competencies = self.db.execute(text("""
                SELECT current_score, current_level
                FROM user_competency_scores ucs
                JOIN competency_categories cc ON cc.id = ucs.category_id
                WHERE ucs.user_id = :user_id AND cc.specialization_id = :spec_id
            """), {"user_id": user_id, "spec_id": specialization_id}).fetchall()

            if not competencies:
                continue

            # Check if all competencies meet threshold
            avg_score = sum(float(c.current_score) for c in competencies) / len(competencies)

            if avg_score >= required_score:
                # Award milestone
                self.db.execute(text("""
                    INSERT INTO user_competency_milestones (
                        user_id, milestone_id, achieved_at
                    )
                    VALUES (:user_id, :milestone_id, NOW())
                """), {"user_id": user_id, "milestone_id": milestone_id})

                # Award XP if applicable
                if xp_reward and xp_reward > 0:
                    self.db.execute(text("""
                        UPDATE users
                        SET total_xp = total_xp + :xp
                        WHERE id = :user_id
                    """), {"user_id": user_id, "xp": xp_reward})

                logger.info(f"Milestone {milestone_id} achieved by user {user_id}, awarded {xp_reward} XP")

        self.db.commit()

    # ============================================================================
    # COMPETENCY RETRIEVAL
    # ============================================================================

    def get_user_competencies(self, user_id: int, specialization_id: Optional[str] = None) -> List[Dict]:
        """Get user's competency scores"""
        query = """
            SELECT
                ucs.id,
                ucs.user_id,
                ucs.category_id,
                cc.name as category_name,
                cc.icon as category_icon,
                cc.specialization_id,
                ucs.current_score,
                ucs.current_level,
                ucs.total_assessments,
                ucs.last_assessed_at
            FROM user_competency_scores ucs
            JOIN competency_categories cc ON cc.id = ucs.category_id
            WHERE ucs.user_id = :user_id
        """

        params = {"user_id": user_id}

        if specialization_id:
            query += " AND cc.specialization_id = :spec_id"
            params["spec_id"] = specialization_id

        query += " ORDER BY cc.display_order"

        results = self.db.execute(text(query), params).fetchall()

        return [{
            "id": r.id,
            "user_id": r.user_id,
            "category_id": r.category_id,
            "category_name": r.category_name,
            "category_icon": r.category_icon,
            "specialization_id": r.specialization_id,
            "current_score": float(r.current_score),
            "current_level": r.current_level,
            "total_assessments": r.total_assessments,
            "last_assessed_at": r.last_assessed_at
        } for r in results]

    def get_competency_breakdown(self, user_id: int, category_id: int) -> Dict:
        """Get detailed breakdown of skills within a competency category"""
        # Get category info
        category = self.db.execute(text("""
            SELECT * FROM competency_categories WHERE id = :cat_id
        """), {"cat_id": category_id}).fetchone()

        if not category:
            return None

        # Get user's category score
        category_score = self.db.execute(text("""
            SELECT * FROM user_competency_scores
            WHERE user_id = :user_id AND competency_category_id = :cat_id
        """), {"user_id": user_id, "cat_id": category_id}).fetchone()

        # Get skills
        skills = self.db.execute(text("""
            SELECT
                cs.id,
                cs.name,
                cs.description,
                uss.current_score,
                uss.current_level,
                uss.total_assessments,
                uss.last_assessed_at
            FROM competency_skills cs
            LEFT JOIN user_skill_scores uss ON uss.skill_id = cs.id AND uss.user_id = :user_id
            WHERE cs.competency_category_id = :cat_id
            ORDER BY cs.display_order
        """), {"user_id": user_id, "cat_id": category_id}).fetchall()

        return {
            "category": {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "icon": category.icon,
                "current_score": float(category_score.current_score) if category_score else 0.0,
                "current_level": category_score.current_level if category_score else "Beginner",
                "total_assessments": category_score.total_assessments if category_score else 0
            },
            "skills": [{
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "current_score": float(s.current_score) if s.current_score else 0.0,
                "current_level": s.current_level if s.current_level else "Beginner",
                "total_assessments": s.total_assessments if s.total_assessments else 0,
                "last_assessed_at": s.last_assessed_at
            } for s in skills]
        }

    def get_assessment_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get recent assessment history"""
        results = self.db.execute(text("""
            SELECT
                ca.id,
                ca.user_id,
                ca.category_id,
                ca.skill_id,
                cc.name as category_name,
                cs.name as skill_name,
                ca.score,
                ca.source_type,
                ca.source_id,
                ca.assessed_at
            FROM competency_assessments ca
            LEFT JOIN competency_categories cc ON cc.id = ca.category_id
            LEFT JOIN competency_skills cs ON cs.id = ca.skill_id
            WHERE ca.user_id = :user_id
            ORDER BY ca.assessed_at DESC
            LIMIT :limit
        """), {"user_id": user_id, "limit": limit}).fetchall()

        return [{
            "id": r.id,
            "category_name": r.category_name,
            "skill_name": r.skill_name,
            "score": float(r.score),
            "source_type": r.source_type,
            "source_id": r.source_id,
            "assessed_at": r.assessed_at
        } for r in results]

    def get_user_milestones(self, user_id: int, specialization_id: Optional[str] = None) -> List[Dict]:
        """Get user's achieved milestones"""
        query = """
            SELECT
                ucm.id,
                ucm.user_id,
                ucm.milestone_id,
                cm.name as milestone_name,
                cm.description,
                cm.icon,
                cm.xp_reward,
                cm.specialization_id,
                ucm.achieved_at
            FROM user_competency_milestones ucm
            JOIN competency_milestones cm ON cm.id = ucm.milestone_id
            WHERE ucm.user_id = :user_id
        """

        params = {"user_id": user_id}

        if specialization_id:
            query += " AND cm.specialization_id = :spec_id"
            params["spec_id"] = specialization_id

        query += " ORDER BY ucm.achieved_at DESC"

        results = self.db.execute(text(query), params).fetchall()

        return [{
            "id": r.id,
            "milestone_id": r.milestone_id,
            "milestone_name": r.milestone_name,
            "description": r.description,
            "icon": r.icon,
            "xp_reward": r.xp_reward,
            "specialization_id": r.specialization_id,
            "achieved_at": r.achieved_at
        } for r in results]
