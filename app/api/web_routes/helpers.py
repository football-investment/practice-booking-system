"""
Helper functions for web routes
"""
from sqlalchemy.orm import Session
from datetime import date


def update_specialization_xp(
    db: Session,
    student_id: int,
    specialization_id: str,
    xp_earned: int,
    session_id: int,
    is_update: bool = False
):
    """
    Update or create specialization_progress record with XP

    Args:
        db: Database session
        student_id: Student user ID
        specialization_id: Specialization type (e.g., 'INTERNSHIP')
        xp_earned: XP amount to award
        session_id: Session ID for tracking
        is_update: If True, recalculate XP (don't add); if False, add new XP
    """
    from ...models.user_progress import SpecializationProgress
    from datetime import datetime, timezone
    from sqlalchemy.exc import IntegrityError

    try:
        # Get or create specialization progress
        progress = db.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == student_id,
            SpecializationProgress.specialization_id == specialization_id
        ).first()

        if not progress:
            # Create new progress record
            progress = SpecializationProgress(
                student_id=student_id,
                specialization_id=specialization_id,
                total_xp=xp_earned,
                completed_sessions=1,
                current_level=1,
                last_activity=datetime.now(timezone.utc)
            )
            db.add(progress)
            db.flush()  # Flush immediately to catch integrity errors
            print(f"( Created new SpecializationProgress for student {student_id} | Specialization: {specialization_id} | Initial XP: {xp_earned}")
        else:
            if is_update:
                # For updates, we need to recalculate total XP from all reviews
                # This is a simplified approach - you might want to track XP per session
                # For now, just update the XP to the new value (assumes single session)
                # TODO: Implement proper XP tracking per session
                progress.total_xp = xp_earned
                print(f"= Updated SpecializationProgress XP for student {student_id} | New XP: {xp_earned}")
            else:
                # Add new XP
                progress.total_xp = (progress.total_xp or 0) + xp_earned
                progress.completed_sessions = (progress.completed_sessions or 0) + 1
                print(f" Added XP to SpecializationProgress for student {student_id} | Added: {xp_earned} | Total: {progress.total_xp}")

            progress.last_activity = datetime.now(timezone.utc)

        # Calculate level based on XP (1000 XP per level)
        progress.current_level = max(1, (progress.total_xp or 0) // 1000)

        db.flush()

    except IntegrityError as e:
        # Rollback just the XP operation, not the entire transaction
        print(f" IntegrityError caught - rolling back XP update only...")
        print(f"   Error details: {str(e)}")

        # Query for existing record without transaction
        try:
            progress = db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == student_id,
                SpecializationProgress.specialization_id == specialization_id
            ).first()

            if progress:
                # Record exists, update it
                if is_update:
                    progress.total_xp = xp_earned
                    print(f"= [Retry] Updated SpecializationProgress XP for student {student_id} | New XP: {xp_earned}")
                else:
                    progress.total_xp = (progress.total_xp or 0) + xp_earned
                    progress.completed_sessions = (progress.completed_sessions or 0) + 1
                    print(f" [Retry] Added XP to SpecializationProgress for student {student_id} | Added: {xp_earned} | Total: {progress.total_xp}")

                progress.last_activity = datetime.now(timezone.utc)
                progress.current_level = max(1, (progress.total_xp or 0) // 1000)
            else:
                # Record doesn't exist - log but don't crash
                print(f" Warning: Could not update XP for student {student_id}, spec {specialization_id}")
                print(f"   XP tracking will be retried on next evaluation update")
        except Exception as retry_error:
            print(f"L Error during XP retry: {str(retry_error)}")
            print(f"   Performance review will still be saved, XP tracking skipped")


def get_lfa_age_category(date_of_birth):
    """
    Determine LFA Player age category based on date of birth.

    Returns tuple: (category_code, category_name, age_range, description)

    Categories:
    - PRE (5-13 years): Foundation Years - Monthly semesters
    - YOUTH (14-18 years): Technical Development - Quarterly semesters
    - AMATEUR (14+ years): Competitive Play - Bi-annual semesters (instructor assigned)
    - PRO (14+ years): Professional Track - Annual semesters (instructor assigned)
    """
    if not date_of_birth:
        return None, None, None, "Date of birth not set"

    today = date.today()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

    if 5 <= age <= 13:
        return "PRE", "PRE (Foundation Years)", "5-13 years", f"Age {age} - Monthly training blocks"
    elif 14 <= age <= 18:
        return "YOUTH", "YOUTH (Technical Development)", "14-18 years", f"Age {age} - Quarterly programs"
    elif age > 18:
        # For 18+ students, category must be assigned by instructor (AMATEUR or PRO)
        return None, None, None, f"Age {age} - Category assigned by instructor (AMATEUR or PRO)"
    else:
        return None, None, None, f"Age {age} - Below minimum age requirement (5 years)"
