"""
Seed Achievement Definitions

Creates initial achievement definitions for the gamification system.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.achievement import Achievement, AchievementCategory


def seed_achievements():
    """Seed initial achievement definitions"""
    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(Achievement).count()
        if existing > 0:
            print(f"⚠️  Achievements already seeded ({existing} found). Skipping.")
            return

        achievements = [
            # Onboarding Achievements (3)
            {
                "code": "FIRST_LOGIN",
                "name": "Welcome to GānCuju!",
                "description": "Complete your first login",
                "icon": "👋",
                "xp_reward": 10,
                "category": AchievementCategory.ONBOARDING,
                "requirements": {"action": "login", "count": 1}
            },
            {
                "code": "SPECIALIZATION_SELECTED",
                "name": "Choose Your Path",
                "description": "Select your specialization",
                "icon": "🎯",
                "xp_reward": 25,
                "category": AchievementCategory.ONBOARDING,
                "requirements": {"action": "select_specialization", "count": 1}
            },
            {
                "code": "PROFILE_COMPLETE",
                "name": "Profile Complete",
                "description": "Complete your profile information",
                "icon": "✅",
                "xp_reward": 50,
                "category": AchievementCategory.ONBOARDING,
                "requirements": {"action": "complete_profile", "count": 1}
            },

            # Learning Achievements (4)
            {
                "code": "FIRST_QUIZ",
                "name": "Quiz Master Beginner",
                "description": "Complete your first quiz",
                "icon": "📝",
                "xp_reward": 20,
                "category": AchievementCategory.LEARNING,
                "requirements": {"action": "complete_quiz", "count": 1}
            },
            {
                "code": "QUIZ_STREAK_5",
                "name": "5 Quiz Streak",
                "description": "Complete 5 quizzes in a row",
                "icon": "🔥",
                "xp_reward": 100,
                "category": AchievementCategory.LEARNING,
                "requirements": {"action": "complete_quiz", "count": 5}
            },
            {
                "code": "QUIZ_MASTER_10",
                "name": "Quiz Master",
                "description": "Complete 10 quizzes",
                "icon": "🎓",
                "xp_reward": 200,
                "category": AchievementCategory.LEARNING,
                "requirements": {"action": "complete_quiz", "count": 10}
            },
            {
                "code": "PERFECT_QUIZ",
                "name": "Perfect Score",
                "description": "Score 100% on a quiz",
                "icon": "💯",
                "xp_reward": 75,
                "category": AchievementCategory.LEARNING,
                "requirements": {"action": "quiz_perfect_score", "count": 1}
            },

            # Progression Achievements (3)
            {
                "code": "FIRST_LICENSE",
                "name": "Licensed Player",
                "description": "Earn your first license",
                "icon": "🏆",
                "xp_reward": 100,
                "category": AchievementCategory.PROGRESSION,
                "requirements": {"action": "license_earned", "count": 1}
            },
            {
                "code": "LEVEL_UP_2",
                "name": "Rising Star",
                "description": "Reach Level 2 in any specialization",
                "icon": "⭐",
                "xp_reward": 150,
                "category": AchievementCategory.PROGRESSION,
                "requirements": {"action": "reach_level", "level": 2}
            },
            {
                "code": "LEVEL_UP_5",
                "name": "Expert Practitioner",
                "description": "Reach Level 5 in any specialization",
                "icon": "🌟",
                "xp_reward": 500,
                "category": AchievementCategory.PROGRESSION,
                "requirements": {"action": "reach_level", "level": 5}
            },

            # Project Achievements (2)
            {
                "code": "PROJECT_ENROLLED",
                "name": "Project Pioneer",
                "description": "Enroll in your first project",
                "icon": "🚀",
                "xp_reward": 50,
                "category": AchievementCategory.LEARNING,
                "requirements": {"action": "project_enroll", "count": 1}
            },
            {
                "code": "PROJECT_COMPLETE",
                "name": "Project Completer",
                "description": "Complete your first project",
                "icon": "🎉",
                "xp_reward": 200,
                "category": AchievementCategory.LEARNING,
                "requirements": {"action": "project_complete", "count": 1}
            },

            # Mastery Achievements (2)
            {
                "code": "MASTER_LEVEL_8",
                "name": "Dragon Wisdom",
                "description": "Reach Level 8 (Sárkány Bölcsesség)",
                "icon": "🐉",
                "xp_reward": 1000,
                "category": AchievementCategory.MASTERY,
                "requirements": {"action": "reach_level", "level": 8}
            },
            {
                "code": "MULTI_SPECIALIST",
                "name": "Multi-Specialist",
                "description": "Have licenses in 2+ specializations",
                "icon": "🎭",
                "xp_reward": 300,
                "category": AchievementCategory.MASTERY,
                "requirements": {"action": "multiple_specializations", "count": 2}
            }
        ]

        # Insert achievements
        for ach_data in achievements:
            achievement = Achievement(**ach_data)
            db.add(achievement)

        db.commit()

        print(f"✅ Seeded {len(achievements)} achievements successfully!")

        # Print summary by category
        print("\n📊 Achievements by category:")
        for category in [AchievementCategory.ONBOARDING, AchievementCategory.LEARNING,
                        AchievementCategory.PROGRESSION, AchievementCategory.MASTERY]:
            count = len([a for a in achievements if a["category"] == category])
            print(f"   {category}: {count} achievements")

        print(f"\n💰 Total XP available: {sum(a['xp_reward'] for a in achievements)} XP")

    except Exception as e:
        print(f"❌ Error seeding achievements: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_achievements()
