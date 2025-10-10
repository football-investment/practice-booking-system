#!/usr/bin/env python3
"""
Database Verification Script for Integration Hooks
Directly queries database to verify Hook 1, Hook 2, Hook 3 effects
"""
import os
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# Database connection
DATABASE_URL = "postgresql://lfa_user:lfa2024@localhost/practice_booking_system"
engine = create_engine(DATABASE_URL)

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_section(title):
    print(f"\n{BLUE}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def verify_hook_1_quiz_competency():
    """Verify Hook 1: Quiz → Competency Assessment"""
    print_section("HOOK 1 VERIFICATION: Quiz → Competency Assessment")

    with engine.connect() as conn:
        # Check recent quiz attempts
        print_info("Checking recent quiz attempts...")
        result = conn.execute(text("""
            SELECT
                qa.id,
                qa.user_id,
                u.name as user_name,
                q.title as quiz_title,
                qa.score,
                qa.completed_at,
                qa.started_at
            FROM quiz_attempts qa
            JOIN users u ON u.id = qa.user_id
            JOIN quizzes q ON q.id = qa.quiz_id
            WHERE qa.completed_at IS NOT NULL
            ORDER BY qa.completed_at DESC
            LIMIT 5
        """))

        attempts = result.fetchall()
        if attempts:
            print_success(f"Found {len(attempts)} recent quiz attempts:")
            for attempt in attempts:
                print(f"\n  Quiz Attempt ID: {attempt.id}")
                print(f"    User: {attempt.user_name} (ID: {attempt.user_id})")
                print(f"    Quiz: {attempt.quiz_title}")
                print(f"    Score: {attempt.score}%")
                print(f"    Completed: {attempt.completed_at}")

                # Check if competency assessments were created
                assess_result = conn.execute(text("""
                    SELECT
                        ca.id,
                        cc.name as category_name,
                        cs.name as skill_name,
                        ca.score,
                        ca.assessed_at
                    FROM competency_assessments ca
                    JOIN competency_skills cs ON cs.id = ca.skill_id
                    JOIN competency_categories cc ON cc.id = cs.category_id
                    WHERE ca.source_type = 'quiz'
                    AND ca.source_id = :quiz_attempt_id
                    ORDER BY ca.assessed_at DESC
                """), {"quiz_attempt_id": attempt.id})

                assessments = assess_result.fetchall()
                if assessments:
                    print_success(f"    ✅ Hook 1 triggered: {len(assessments)} competency assessments created:")
                    for assess in assessments:
                        print(f"      - {assess.category_name} > {assess.skill_name}: {assess.score}%")
                else:
                    print_error(f"    ❌ No competency assessments found for this quiz")

                # Check if learning profile was updated
                profile_result = conn.execute(text("""
                    SELECT
                        learning_pace,
                        quiz_average_score,
                        lessons_completed,
                        last_activity_at,
                        updated_at
                    FROM user_learning_profiles
                    WHERE user_id = :user_id
                """), {"user_id": attempt.user_id})

                profile = profile_result.fetchone()
                if profile:
                    print_success(f"    ✅ Learning profile updated:")
                    print(f"      - Pace: {profile.learning_pace}")
                    print(f"      - Quiz avg: {profile.quiz_average_score}%")
                    print(f"      - Lessons completed: {profile.lessons_completed}")
                    print(f"      - Updated: {profile.updated_at}")
                else:
                    print_error(f"    ❌ No learning profile found")

                # Check if recommendations were generated (for low scores)
                if attempt.score < 70:
                    rec_result = conn.execute(text("""
                        SELECT
                            recommendation_type,
                            title,
                            description,
                            priority,
                            created_at
                        FROM adaptive_recommendations
                        WHERE user_id = :user_id
                        AND is_active = true
                        ORDER BY created_at DESC
                        LIMIT 3
                    """), {"user_id": attempt.user_id})

                    recommendations = rec_result.fetchall()
                    if recommendations:
                        print_success(f"    ✅ Recommendations generated (low score <70%):")
                        for rec in recommendations:
                            print(f"      - {rec.recommendation_type}: {rec.title} (Priority: {rec.priority})")
                    else:
                        print_error(f"    ❌ No recommendations found (expected for score < 70%)")

        else:
            print_error("No quiz attempts found")

def verify_hook_2_exercise_competency():
    """Verify Hook 2: Exercise Grading → Competency Assessment"""
    print_section("HOOK 2 VERIFICATION: Exercise → Competency Assessment")

    with engine.connect() as conn:
        # Check recent graded exercise submissions
        print_info("Checking recent graded exercise submissions...")
        result = conn.execute(text("""
            SELECT
                es.id,
                es.user_id,
                u.name as user_name,
                e.title as exercise_title,
                es.score,
                es.passed,
                es.xp_awarded,
                es.reviewed_at,
                es.reviewed_by,
                ui.name as grader_name
            FROM user_exercise_submissions es
            JOIN users u ON u.id = es.user_id
            JOIN exercises e ON e.id = es.exercise_id
            LEFT JOIN users ui ON ui.id = es.reviewed_by
            WHERE es.reviewed_at IS NOT NULL
            ORDER BY es.reviewed_at DESC
            LIMIT 5
        """))

        submissions = result.fetchall()
        if submissions:
            print_success(f"Found {len(submissions)} graded exercise submissions:")
            for sub in submissions:
                print(f"\n  Exercise Submission ID: {sub.id}")
                print(f"    Student: {sub.user_name} (ID: {sub.user_id})")
                print(f"    Exercise: {sub.exercise_title}")
                print(f"    Score: {sub.score}% - {'PASSED' if sub.passed else 'FAILED'}")
                print(f"    XP Awarded: {sub.xp_awarded}")
                print(f"    Graded by: {sub.grader_name or 'N/A'}")
                print(f"    Graded at: {sub.reviewed_at}")

                # Check if competency assessments were created
                assess_result = conn.execute(text("""
                    SELECT
                        ca.id,
                        cc.name as category_name,
                        cs.name as skill_name,
                        ca.score,
                        ca.assessed_at
                    FROM competency_assessments ca
                    JOIN competency_skills cs ON cs.id = ca.skill_id
                    JOIN competency_categories cc ON cc.id = cs.category_id
                    WHERE ca.source_type = 'exercise'
                    AND ca.source_id = :submission_id
                    ORDER BY ca.assessed_at DESC
                """), {"submission_id": sub.id})

                assessments = assess_result.fetchall()
                if assessments:
                    print_success(f"    ✅ Hook 2 triggered: {len(assessments)} competency assessments created:")
                    for assess in assessments:
                        print(f"      - {assess.category_name} > {assess.skill_name}: {assess.score}%")
                else:
                    print_error(f"    ❌ No competency assessments found for this exercise")

        else:
            print_error("No graded exercise submissions found")

def verify_hook_3_daily_snapshots():
    """Verify Hook 3: Daily Snapshot Scheduler"""
    print_section("HOOK 3 VERIFICATION: Daily Snapshot Scheduler")

    with engine.connect() as conn:
        # Check recent performance snapshots
        print_info("Checking recent performance snapshots...")
        result = conn.execute(text("""
            SELECT
                ps.id,
                ps.user_id,
                u.name as user_name,
                ps.snapshot_date,
                ps.quiz_average,
                ps.quiz_count,
                ps.lessons_completed,
                ps.modules_completed,
                ps.total_minutes_studied,
                ps.total_xp,
                ps.current_level,
                ps.created_at
            FROM performance_snapshots ps
            JOIN users u ON u.id = ps.user_id
            ORDER BY ps.created_at DESC
            LIMIT 10
        """))

        snapshots = result.fetchall()
        if snapshots:
            print_success(f"Found {len(snapshots)} performance snapshots:")

            # Group by user
            users_with_snapshots = {}
            for snap in snapshots:
                if snap.user_id not in users_with_snapshots:
                    users_with_snapshots[snap.user_id] = {
                        "name": snap.user_name,
                        "snapshots": []
                    }
                users_with_snapshots[snap.user_id]["snapshots"].append(snap)

            for user_id, data in users_with_snapshots.items():
                print(f"\n  User: {data['name']} (ID: {user_id})")
                print(f"  Total snapshots: {len(data['snapshots'])}")
                for snap in data["snapshots"][:3]:  # Show last 3
                    print(f"    - Date: {snap.snapshot_date}")
                    print(f"      Quiz avg: {snap.quiz_average}% ({snap.quiz_count} quizzes), "
                          f"Lessons: {snap.lessons_completed}, Modules: {snap.modules_completed}, "
                          f"Study time: {snap.total_minutes_studied}m, XP: {snap.total_xp}, Level: {snap.current_level}")

            # Check if any snapshots were created today
            today_result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM performance_snapshots
                WHERE snapshot_date = CURRENT_DATE
            """))
            today_count = today_result.fetchone().count
            if today_count > 0:
                print_success(f"\n  ✅ {today_count} snapshot(s) created today")
            else:
                print_info(f"\n  ℹ️  No snapshots created today (scheduler runs at 00:00)")

        else:
            print_error("No performance snapshots found")

        # Check scheduler job status (from APScheduler)
        print_info("\nChecking APScheduler job status...")
        print_info("Note: Scheduler runs as background process - check application logs for:")
        print_info("  - 'Daily snapshots: Every day at 00:00'")
        print_info("  - 'Weekly recommendations: Every Monday at 06:00'")

def verify_competency_scores():
    """Verify competency scores are being updated"""
    print_section("COMPETENCY SCORES VERIFICATION")

    with engine.connect() as conn:
        # Check user competency scores
        print_info("Checking user competency scores...")
        result = conn.execute(text("""
            SELECT
                ucs.user_id,
                u.name as user_name,
                cc.name as category_name,
                ucs.current_score,
                ucs.percentage,
                ucs.competency_level,
                ucs.assessment_count,
                ucs.last_assessed
            FROM user_competency_scores ucs
            JOIN users u ON u.id = ucs.user_id
            JOIN competency_categories cc ON cc.id = ucs.competency_category_id
            WHERE ucs.assessment_count > 0
            ORDER BY ucs.last_assessed DESC
            LIMIT 15
        """))

        scores = result.fetchall()
        if scores:
            print_success(f"Found {len(scores)} user competency scores:")

            # Group by user
            users_competencies = {}
            for score in scores:
                if score.user_id not in users_competencies:
                    users_competencies[score.user_id] = {
                        "name": score.user_name,
                        "competencies": []
                    }
                users_competencies[score.user_id]["competencies"].append(score)

            for user_id, data in users_competencies.items():
                print(f"\n  User: {data['name']} (ID: {user_id})")
                for comp in data["competencies"]:
                    print(f"    - {comp.category_name}: {comp.percentage}% (Level {comp.competency_level}) "
                          f"- {comp.assessment_count} assessments")
        else:
            print_error("No competency scores found")

def run_all_verifications():
    """Run all database verifications"""
    print(f"{BLUE}")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "DATABASE HOOK VERIFICATION" + " "*27 + "║")
    print("║" + " "*10 + "Direct database queries for Hook 1, 2, 3" + " "*18 + "║")
    print("╚" + "="*68 + "╝")
    print(f"{RESET}\n")

    try:
        # Test database connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print_success(f"Database connected: {version.split(',')[0]}\n")

        # Run verifications
        verify_hook_1_quiz_competency()
        verify_hook_2_exercise_competency()
        verify_hook_3_daily_snapshots()
        verify_competency_scores()

        print_section("VERIFICATION COMPLETE")
        print_info("Check the results above to verify all hooks are working correctly")

    except Exception as e:
        print_error(f"Database error: {e}")
        exit(1)

if __name__ == "__main__":
    run_all_verifications()
