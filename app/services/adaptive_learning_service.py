"""
Adaptive Learning Service
Personalized learning recommendations based on user behavior and performance
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AdaptiveLearningService:
    """Service for adaptive learning recommendations and profile management"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # LEARNING PROFILE MANAGEMENT
    # ============================================================================

    def get_or_create_profile(self, user_id: int) -> Dict:
        """Get or create user learning profile"""
        result = self.db.execute(text("""
            SELECT * FROM user_learning_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        if not result:
            # Create new profile
            self.db.execute(text("""
                INSERT INTO user_learning_profiles (
                    user_id, learning_pace, pace_score, quiz_average_score,
                    lessons_completed_count, avg_time_per_lesson_minutes,
                    preferred_content_type, last_activity_at, created_at
                )
                VALUES (
                    :user_id, 'MEDIUM', 50.0, 0.0,
                    0, 0.0,
                    'TEXT', NOW(), NOW()
                )
            """), {"user_id": user_id})
            self.db.commit()

            result = self.db.execute(text("""
                SELECT * FROM user_learning_profiles
                WHERE user_id = :user_id
            """), {"user_id": user_id}).fetchone()

        return {
            "id": result.id,
            "user_id": result.user_id,
            "learning_pace": result.learning_pace,
            "pace_score": float(result.pace_score) if result.pace_score else 0.0,
            "quiz_average_score": float(result.quiz_average_score) if result.quiz_average_score else 0.0,
            "lessons_completed_count": result.lessons_completed_count or 0,
            "avg_time_per_lesson_minutes": float(result.avg_time_per_lesson_minutes) if result.avg_time_per_lesson_minutes else 0.0,
            "preferred_content_type": result.preferred_content_type or "TEXT",
            "last_activity_at": result.last_activity_at,
            "created_at": result.created_at,
            "updated_at": result.updated_at
        }

    def update_profile_metrics(self, user_id: int) -> Dict:
        """Recalculate all learning profile metrics"""
        logger.info(f"Updating profile metrics for user {user_id}")

        # 1. Calculate quiz average (last 10 attempts, weighted)
        quiz_avg = self._calculate_quiz_average(user_id)

        # 2. Calculate learning pace
        pace_score = self._calculate_pace_score(user_id)
        pace_category = self._categorize_pace(pace_score)

        # 3. Calculate lessons completed
        lessons_completed = self._count_lessons_completed(user_id)

        # 4. Calculate average time per lesson
        avg_time = self._calculate_avg_lesson_time(user_id)

        # 5. Detect preferred content type
        preferred_content = self._detect_content_preference(user_id)

        # 6. Update profile
        self.db.execute(text("""
            UPDATE user_learning_profiles
            SET
                quiz_average_score = :quiz_avg,
                pace_score = :pace_score,
                learning_pace = :pace_category,
                lessons_completed_count = :lessons_completed,
                avg_time_per_lesson_minutes = :avg_time,
                preferred_content_type = :preferred_content,
                last_activity_at = NOW(),
                updated_at = NOW()
            WHERE user_id = :user_id
        """), {
            "user_id": user_id,
            "quiz_avg": quiz_avg,
            "pace_score": pace_score,
            "pace_category": pace_category,
            "lessons_completed": lessons_completed,
            "avg_time": avg_time,
            "preferred_content": preferred_content
        })
        # NOTE: Don't commit here - let caller handle transaction commit
        # This allows proper transaction isolation when called from hooks

        logger.info(f"Profile updated: pace={pace_category}, quiz_avg={quiz_avg:.1f}%, lessons={lessons_completed}")

        return self.get_or_create_profile(user_id)

    def _calculate_quiz_average(self, user_id: int) -> float:
        """Calculate weighted average of last 10 quiz attempts"""
        result = self.db.execute(text("""
            SELECT score
            FROM quiz_attempts
            WHERE user_id = :user_id AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT 10
        """), {"user_id": user_id}).fetchall()

        if not result:
            return 0.0

        scores = [float(r.score) for r in result]

        # Weighted average: more recent = more weight
        weights = [0.4, 0.25, 0.2, 0.1, 0.05, 0.04, 0.03, 0.02, 0.01, 0.01][:len(scores)]
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        weight_sum = sum(weights)

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    def _calculate_pace_score(self, user_id: int) -> float:
        """
        Calculate learning pace score (0-100)
        Higher = faster learner
        Based on: lessons completed, time spent, quiz performance
        """
        # Get last 30 days activity
        result = self.db.execute(text("""
            SELECT
                COUNT(DISTINCT ulp.lesson_id) as lessons_completed,
                COALESCE(AVG(qa.score), 0) as avg_quiz_score,
                COUNT(DISTINCT DATE(ulp.completed_at)) as active_days
            FROM user_lesson_progress ulp
            LEFT JOIN quiz_attempts qa ON qa.user_id = ulp.user_id
                AND qa.completed_at >= NOW() - INTERVAL '30 days'
            WHERE ulp.user_id = :user_id
                AND ulp.completed_at >= NOW() - INTERVAL '30 days'
                AND ulp.completed_at IS NOT NULL
        """), {"user_id": user_id}).fetchone()

        if not result or result.lessons_completed == 0:
            return 50.0  # Default medium pace

        lessons_completed = result.lessons_completed or 0
        avg_quiz_score = float(result.avg_quiz_score) if result.avg_quiz_score else 0.0
        active_days = result.active_days or 1

        # Calculate pace components
        lesson_velocity = min(lessons_completed / 30.0 * 100, 100)  # lessons per month normalized
        consistency = min(active_days / 20.0 * 100, 100)  # active days normalized
        performance = avg_quiz_score  # already 0-100

        # Weighted combination
        pace_score = (
            lesson_velocity * 0.4 +
            consistency * 0.3 +
            performance * 0.3
        )

        return min(max(pace_score, 0), 100)

    def _categorize_pace(self, pace_score: float) -> str:
        """Categorize pace score into labels"""
        if pace_score >= 80:
            return "ACCELERATED"
        elif pace_score >= 60:
            return "FAST"
        elif pace_score >= 40:
            return "MEDIUM"
        else:
            return "SLOW"

    def _count_lessons_completed(self, user_id: int) -> int:
        """Count total completed lessons"""
        result = self.db.execute(text("""
            SELECT COUNT(*) as count
            FROM user_lesson_progress
            WHERE user_id = :user_id AND completed_at IS NOT NULL
        """), {"user_id": user_id}).fetchone()

        return result.count if result else 0

    def _calculate_avg_lesson_time(self, user_id: int) -> float:
        """Calculate average time spent per lesson (minutes)"""
        result = self.db.execute(text("""
            SELECT AVG(time_spent_minutes) as avg_time
            FROM user_lesson_progress
            WHERE user_id = :user_id
                AND completed_at IS NOT NULL
                AND time_spent_minutes IS NOT NULL
                AND time_spent_minutes > 0
        """), {"user_id": user_id}).fetchone()

        return float(result.avg_time) if result and result.avg_time else 0.0

    def _detect_content_preference(self, user_id: int) -> str:
        """Detect user's preferred content type based on engagement"""
        # Simple heuristic: if average time < 10 min = VIDEO preference
        # if 10-20 min = TEXT preference
        # if > 20 min = PRACTICE preference

        avg_time = self._calculate_avg_lesson_time(user_id)

        if avg_time < 10:
            return "VIDEO"
        elif avg_time < 20:
            return "TEXT"
        else:
            return "PRACTICE"

    # ============================================================================
    # RECOMMENDATION ENGINE
    # ============================================================================

    def generate_recommendations(self, user_id: int, refresh: bool = False) -> List[Dict]:
        """
        Generate AI-powered recommendations for user
        Returns list of recommendations sorted by priority
        """
        logger.info(f"Generating recommendations for user {user_id} (refresh={refresh})")

        # If not refresh, check for existing active recommendations
        if not refresh:
            existing = self.db.execute(text("""
                SELECT * FROM adaptive_recommendations
                WHERE user_id = :user_id
                    AND is_active = true
                    AND created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY priority DESC
                LIMIT 5
            """), {"user_id": user_id}).fetchall()

            if existing:
                return [self._format_recommendation(r) for r in existing]

        # Generate fresh recommendations
        recommendations = []

        # 1. Check for burnout
        burnout_rec = self._detect_burnout(user_id)
        if burnout_rec:
            recommendations.append(burnout_rec)

        # 2. Find weak areas (low quiz scores)
        weak_lessons = self._find_weak_lessons(user_id)
        if weak_lessons:
            recommendations.append({
                "type": "REVIEW_LESSON",
                "title": "Review Weak Topics",
                "message": f"You scored below 70% on {len(weak_lessons)} lesson(s). Review recommended.",
                "priority": 85,
                "metadata": {"lesson_ids": weak_lessons}
            })

        # 3. Suggest next lesson
        next_lesson = self._suggest_next_lesson(user_id)
        if next_lesson:
            recommendations.append(next_lesson)

        # 4. Check for inactive users
        inactivity_rec = self._check_inactivity(user_id)
        if inactivity_rec:
            recommendations.append(inactivity_rec)

        # 5. Suggest practice if theory-heavy
        practice_rec = self._suggest_practice(user_id)
        if practice_rec:
            recommendations.append(practice_rec)

        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"], reverse=True)

        # Save to database
        self._save_recommendations(user_id, recommendations[:5])

        return recommendations[:5]

    def _detect_burnout(self, user_id: int) -> Optional[Dict]:
        """Detect if user is at risk of burnout (too much study time)"""
        result = self.db.execute(text("""
            SELECT
                SUM(time_spent_minutes) as total_time,
                COUNT(*) as lesson_count
            FROM user_lesson_progress
            WHERE user_id = :user_id
                AND started_at >= NOW() - INTERVAL '3 days'
        """), {"user_id": user_id}).fetchone()

        if not result:
            return None

        total_time = float(result.total_time) if result.total_time else 0

        # Burnout threshold: 10+ hours in 3 days
        if total_time >= 600:
            return {
                "type": "TAKE_BREAK",
                "title": "🧘 Take a Break",
                "message": f"You've studied {total_time:.0f} minutes in 3 days. Consider taking a short break.",
                "priority": 95,
                "metadata": {"total_minutes": total_time}
            }

        return None

    def _find_weak_lessons(self, user_id: int) -> List[int]:
        """Find lessons where user scored below 70%"""
        result = self.db.execute(text("""
            SELECT DISTINCT q.lesson_id
            FROM quiz_attempts qa
            JOIN quizzes q ON q.id = qa.quiz_id
            WHERE qa.user_id = :user_id
                AND q.lesson_id IS NOT NULL
                AND qa.score < 70
                AND qa.completed_at >= NOW() - INTERVAL '30 days'
            LIMIT 3
        """), {"user_id": user_id}).fetchall()

        return [r.lesson_id for r in result] if result else []

    def _suggest_next_lesson(self, user_id: int) -> Optional[Dict]:
        """Suggest next lesson in curriculum"""
        # Find current specialization and level
        result = self.db.execute(text("""
            SELECT u.current_specialization, u.current_level
            FROM users u
            WHERE u.id = :user_id
        """), {"user_id": user_id}).fetchone()

        if not result or not result.current_specialization:
            return None

        specialization = result.current_specialization
        level = result.current_level or 1

        # Find next incomplete lesson
        next_lesson = self.db.execute(text("""
            SELECT l.id, l.title, l.display_order
            FROM lessons l
            LEFT JOIN user_lesson_progress ulp ON ulp.lesson_id = l.id AND ulp.user_id = :user_id
            WHERE l.specialization_id = :spec
                AND l.level_id = :level
                AND l.is_published = true
                AND ulp.completed_at IS NULL
            ORDER BY l.display_order ASC
            LIMIT 1
        """), {"user_id": user_id, "spec": specialization, "level": level}).fetchone()

        if next_lesson:
            return {
                "type": "CONTINUE_LEARNING",
                "title": "Continue Your Journey",
                "message": f"Next lesson: {next_lesson.title}",
                "priority": 70,
                "metadata": {"lesson_id": next_lesson.id, "lesson_title": next_lesson.title}
            }

        return None

    def _check_inactivity(self, user_id: int) -> Optional[Dict]:
        """Check if user has been inactive for 7+ days"""
        result = self.db.execute(text("""
            SELECT MAX(started_at) as last_activity
            FROM user_lesson_progress
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        if not result or not result.last_activity:
            return {
                "type": "START_LEARNING",
                "title": "Start Your Learning Journey",
                "message": "Begin your first lesson today!",
                "priority": 80,
                "metadata": {}
            }

        last_activity = result.last_activity
        days_inactive = (datetime.now() - last_activity).days

        if days_inactive >= 7:
            return {
                "type": "RESUME_LEARNING",
                "title": "Welcome Back!",
                "message": f"It's been {days_inactive} days. Let's pick up where you left off.",
                "priority": 90,
                "metadata": {"days_inactive": days_inactive}
            }

        return None

    def _suggest_practice(self, user_id: int) -> Optional[Dict]:
        """Suggest practice if user has done mostly theory"""
        result = self.db.execute(text("""
            SELECT
                COUNT(DISTINCT ulp.lesson_id) as lessons_done,
                COUNT(DISTINCT es.id) as exercises_done
            FROM user_lesson_progress ulp
            LEFT JOIN exercise_submissions es ON es.user_id = ulp.user_id
                AND es.created_at >= NOW() - INTERVAL '14 days'
            WHERE ulp.user_id = :user_id
                AND ulp.completed_at >= NOW() - INTERVAL '14 days'
        """), {"user_id": user_id}).fetchone()

        if not result:
            return None

        lessons_done = result.lessons_done or 0
        exercises_done = result.exercises_done or 0

        # If done 5+ lessons but less than 2 exercises
        if lessons_done >= 5 and exercises_done < 2:
            return {
                "type": "PRACTICE_MORE",
                "title": "Practice Makes Perfect",
                "message": "Try some practical exercises to reinforce your learning.",
                "priority": 75,
                "metadata": {"lessons_done": lessons_done, "exercises_done": exercises_done}
            }

        return None

    def _save_recommendations(self, user_id: int, recommendations: List[Dict]):
        """Save recommendations to database"""
        # Deactivate old recommendations
        self.db.execute(text("""
            UPDATE adaptive_recommendations
            SET is_active = false
            WHERE user_id = :user_id AND is_active = true
        """), {"user_id": user_id})

        # Insert new recommendations
        for rec in recommendations:
            self.db.execute(text("""
                INSERT INTO adaptive_recommendations (
                    user_id, recommendation_type, title, message,
                    priority, metadata, is_active, created_at
                )
                VALUES (
                    :user_id, :type, :title, :message,
                    :priority, :metadata::jsonb, true, NOW()
                )
            """), {
                "user_id": user_id,
                "type": rec["type"],
                "title": rec["title"],
                "message": rec["message"],
                "priority": rec["priority"],
                "metadata": str(rec["metadata"])
            })

        # NOTE: Don't commit here - let caller handle transaction commit
        # This allows proper transaction isolation when called from hooks

    def _format_recommendation(self, row) -> Dict:
        """Format database row to recommendation dict"""
        return {
            "id": row.id,
            "type": row.recommendation_type,
            "title": row.title,
            "message": row.message,
            "priority": row.priority,
            "metadata": row.metadata,
            "is_active": row.is_active,
            "created_at": row.created_at
        }

    def dismiss_recommendation(self, user_id: int, recommendation_id: int):
        """Mark recommendation as dismissed"""
        self.db.execute(text("""
            UPDATE adaptive_recommendations
            SET is_active = false, dismissed_at = NOW()
            WHERE id = :rec_id AND user_id = :user_id
        """), {"rec_id": recommendation_id, "user_id": user_id})
        self.db.commit()

    # ============================================================================
    # PERFORMANCE TRACKING
    # ============================================================================

    def create_daily_snapshot(self, user_id: int):
        """Create daily performance snapshot"""
        logger.info(f"Creating daily snapshot for user {user_id}")

        profile = self.get_or_create_profile(user_id)

        # Get today's activity
        today_lessons = self.db.execute(text("""
            SELECT COUNT(*) as count
            FROM user_lesson_progress
            WHERE user_id = :user_id
                AND completed_at IS NOT NULL
                AND completed_at >= CURRENT_DATE
        """), {"user_id": user_id}).fetchone().count or 0

        today_time = self.db.execute(text("""
            SELECT COALESCE(SUM(time_spent_minutes), 0) as total
            FROM user_lesson_progress
            WHERE user_id = :user_id
                AND started_at >= CURRENT_DATE
        """), {"user_id": user_id}).fetchone().total or 0

        # Insert snapshot
        self.db.execute(text("""
            INSERT INTO performance_snapshots (
                user_id, snapshot_date, pace_score, quiz_average,
                lessons_completed_count, time_spent_minutes_today, created_at
            )
            VALUES (
                :user_id, CURRENT_DATE, :pace_score, :quiz_avg,
                :lessons_count, :time_today, NOW()
            )
            ON CONFLICT (user_id, snapshot_date) DO UPDATE
            SET
                pace_score = EXCLUDED.pace_score,
                quiz_average = EXCLUDED.quiz_average,
                lessons_completed_count = EXCLUDED.lessons_completed_count,
                time_spent_minutes_today = EXCLUDED.time_spent_minutes_today
        """), {
            "user_id": user_id,
            "pace_score": profile["pace_score"],
            "quiz_avg": profile["quiz_average_score"],
            "lessons_count": today_lessons,
            "time_today": float(today_time)
        })
        self.db.commit()

        logger.info(f"Snapshot created: {today_lessons} lessons, {today_time:.0f} minutes")

    def get_performance_history(self, user_id: int, days: int = 30) -> List[Dict]:
        """Get performance history for last N days"""
        result = self.db.execute(text("""
            SELECT *
            FROM performance_snapshots
            WHERE user_id = :user_id
                AND snapshot_date >= CURRENT_DATE - INTERVAL ':days days'
            ORDER BY snapshot_date DESC
        """), {"user_id": user_id, "days": days}).fetchall()

        return [{
            "date": r.snapshot_date,
            "pace_score": float(r.pace_score) if r.pace_score else 0,
            "quiz_average": float(r.quiz_average) if r.quiz_average else 0,
            "lessons_completed": r.lessons_completed_count or 0,
            "time_spent": float(r.time_spent_minutes_today) if r.time_spent_minutes_today else 0
        } for r in result]
