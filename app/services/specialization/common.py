"""
Common functions shared across all specialization types
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from app.models.specialization import SpecializationType
from app.services.specialization_config_loader import get_config_loader
from .validation import specialization_id_to_enum, validate_specialization_exists

    from app.models.user_progress import SpecializationProgress

    # STEP 1: Validate specialization exists in DB (HYBRID check)

    # STEP 1: Validate specialization exists in DB (HYBRID check)
    from app.services.gamification import GamificationService
            from app.services.progress_license_sync_service import ProgressLicenseSyncService
    from app.models.user import User
    from app.services.specialization_validation import SpecializationValidator

    # STEP 1: Validate specialization exists in DB
logger = logging.getLogger(__name__)


def get_level_requirements(
    db: Session,
    specialization_id: str,
    level: int
) -> Optional[Dict[str, Any]]:
    """
    Get requirements for a specific level in a specialization.
    HYBRID: Validates DB existence, then loads from JSON config.

    Args:
        db: Database session
        specialization_id: GANCUJU_PLAYER, LFA_FOOTBALL_PLAYER, LFA_COACH, or INTERNSHIP
                          (also supports legacy: PLAYER, COACH)
        level: Level number (1-8 for most, 1-3 for INTERNSHIP)

    Returns:
        Dict with level info or None if not found
    """
    config_loader = get_config_loader()

    # STEP 1: Validate specialization exists in DB (HYBRID check)
    if not validate_specialization_exists(db, specialization_id):
        logger.warning(f"Specialization {specialization_id} not found or inactive in DB")
        return None

    # Convert to enum
    spec_enum = specialization_id_to_enum(specialization_id)
    if not spec_enum:
        return None

    # STEP 2: Load from JSON config (Source of Truth)
    try:
        level_config = config_loader.get_level_config(spec_enum, level)
        if not level_config:
            return None

        # Format response to match legacy API contract
        requirements = level_config.get('requirements', {})

        response = {
            'level': level,
            'name': level_config.get('name'),
            'required_xp': level_config.get('xp_required', 0),
            'xp_max': level_config.get('xp_max', 999999),
            'required_sessions': level_config.get('required_sessions', 0),
            'required_projects': level_config.get('required_projects', 0),
            'description': level_config.get('description', ''),
        }

        # Add specialization-specific fields
        if 'theory_hours' in requirements:
            response['theory_hours'] = requirements['theory_hours']
        if 'practice_hours' in requirements:
            response['practice_hours'] = requirements['practice_hours']
        if 'skills' in requirements:
            response['skills'] = requirements['skills']

        # Add display fields if available
        if 'belt_color' in level_config:
            response['color'] = level_config['belt_color']
            response['belt_color'] = level_config['belt_color']
        if 'belt_name' in level_config:
            response['belt_name'] = level_config['belt_name']
        if 'name_en' in level_config:
            response['name_en'] = level_config['name_en']

        # Legacy: license_title (construct from level name)
        response['license_title'] = level_config.get('name', f'Level {level}')

        return response

    except Exception as e:
        logger.error(f"Error loading level config for {specialization_id} level {level}: {e}")
        return None


def get_student_progress(
    db: Session,
    student_id: int,
    specialization_id: str
) -> Dict[str, Any]:
    """
    Get student's progress for a specialization.
    HYBRID: Validates DB existence, then creates/retrieves progress.

    Args:
        db: Database session
        student_id: User ID
        specialization_id: GANCUJU_PLAYER, LFA_FOOTBALL_PLAYER, LFA_COACH, or INTERNSHIP
                          (also supports legacy: PLAYER, COACH)

    Returns:
        Dict with complete progress information

    Raises:
        ValueError: If specialization doesn't exist or is inactive
    """
    if not validate_specialization_exists(db, specialization_id):
        raise ValueError(f"Specialization '{specialization_id}' does not exist or is not active")

    # STEP 2: Progress lekérése vagy létrehozása
    progress = db.query(SpecializationProgress).filter(
        and_(
            SpecializationProgress.student_id == student_id,
            SpecializationProgress.specialization_id == specialization_id
        )
    ).first()

    if not progress:
        # Automatikus létrehozás
        progress = SpecializationProgress(
            student_id=student_id,
            specialization_id=specialization_id,
            current_level=1,
            total_xp=0,
            completed_sessions=0,
            completed_projects=0
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)

    # Jelenlegi szint követelmények
    current_level_req = get_level_requirements(db, specialization_id, progress.current_level)

    # Következő szint követelmények
    next_level_req = get_level_requirements(db, specialization_id, progress.current_level + 1)

    # Progress percentage kalkuláció
    progress_percentage = 0
    if next_level_req:
        progress_percentage = min(100, int((progress.total_xp / next_level_req['required_xp']) * 100))

    # XP needed for next level
    xp_needed = 0
    if next_level_req:
        xp_needed = max(0, next_level_req['required_xp'] - progress.total_xp)

    # Sessions needed for next level
    sessions_needed = 0
    if next_level_req:
        sessions_needed = max(0, next_level_req['required_sessions'] - progress.completed_sessions)

    # Format response to match frontend expectations
    response = {
        'student_id': student_id,
        'specialization_id': specialization_id,
        'current_level': current_level_req,  # Frontend expects full level object
        'next_level': next_level_req,  # Frontend expects 'next_level', not 'next_level_info'
        'total_xp': progress.total_xp,
        'xp_needed': xp_needed,
        'completed_sessions': progress.completed_sessions,
        'sessions_needed': sessions_needed,
        'completed_projects': progress.completed_projects,
        'progress_percentage': progress_percentage,
        'can_level_up': can_level_up(db, progress),
        'last_activity': progress.last_activity,
        'is_max_level': next_level_req is None
    }

    # Add COACH-specific hours tracking
    if specialization_id == 'COACH':
        response['theory_hours_completed'] = progress.theory_hours_completed
        response['practice_hours_completed'] = progress.practice_hours_completed

        # Calculate hours needed for next level
        if next_level_req:
            response['theory_hours_needed'] = max(0,
                next_level_req['theory_hours'] - progress.theory_hours_completed)
            response['practice_hours_needed'] = max(0,
                next_level_req['practice_hours'] - progress.practice_hours_completed)

    return response


def can_level_up(db: Session, progress) -> bool:
    """
    Check if student can level up.

    Args:
        db: Database session
        progress: SpecializationProgress instance

    Returns:
        bool: True if requirements met
    """
    next_level_req = get_level_requirements(
        db,
        progress.specialization_id,
        progress.current_level + 1
    )

    if not next_level_req:
        return False  # Nincs több szint

    # Basic requirements (all specializations)
    can_level = (
        progress.total_xp >= next_level_req['required_xp'] and
        progress.completed_sessions >= next_level_req['required_sessions']
    )

    # COACH specialization: also check theory/practice hours
    if progress.specialization_id == 'COACH':
        can_level = can_level and (
            progress.theory_hours_completed >= next_level_req.get('theory_hours', 0) and
            progress.practice_hours_completed >= next_level_req.get('practice_hours', 0)
        )

    return can_level


def update_progress(
    db: Session,
    student_id: int,
    specialization_id: str,
    xp_gained: int = 0,
    sessions_completed: int = 0,
    projects_completed: int = 0
) -> Dict[str, Any]:
    """
    Update student progress and check for level up.
    HYBRID: Validates DB existence before update.

    Args:
        db: Database session
        student_id: User ID
        specialization_id: GANCUJU_PLAYER, LFA_FOOTBALL_PLAYER, LFA_COACH, or INTERNSHIP
                          (also supports legacy: PLAYER, COACH)
        xp_gained: XP to add
        sessions_completed: Number of sessions completed
        projects_completed: Number of projects completed

    Returns:
        Dict with update result

    Raises:
        ValueError: If specialization doesn't exist or is inactive
    """
    if not validate_specialization_exists(db, specialization_id):
        raise ValueError(f"Specialization '{specialization_id}' does not exist or is not active")

    # STEP 2: Get or create progress
    progress = db.query(SpecializationProgress).filter(
        and_(
            SpecializationProgress.student_id == student_id,
            SpecializationProgress.specialization_id == specialization_id
        )
    ).first()

    if not progress:
        progress = SpecializationProgress(
            student_id=student_id,
            specialization_id=specialization_id,
            current_level=1,
            total_xp=0,
            completed_sessions=0,
            completed_projects=0
        )
        db.add(progress)

    # Progress frissítése
    old_level = progress.current_level
    progress.total_xp += xp_gained
    progress.completed_sessions += sessions_completed
    progress.completed_projects += projects_completed
    progress.last_activity = datetime.utcnow()

    # Level up ellenőrzés (akár többszöri level up is)
    leveled_up = False
    levels_gained = 0
    while can_level_up(db, progress):
        progress.current_level += 1
        levels_gained += 1
        leveled_up = True

    db.commit()
    db.refresh(progress)

    # Get new level info if leveled up
    new_level_info = None
    if leveled_up:
        new_level_info = get_level_requirements(db, specialization_id, progress.current_level)

    # CHECK AND AWARD SPECIALIZATION ACHIEVEMENTS
    gamification = GamificationService(db)
    new_achievements = gamification.check_and_award_specialization_achievements(
        user_id=student_id,
        specialization_id=specialization_id
    )

    # P1: AUTO-SYNC Progress → License after level change
    sync_result = None
    if leveled_up:
        try:
            sync_service = ProgressLicenseSyncService(db)
            sync_result = sync_service.sync_progress_to_license(
                user_id=student_id,
                specialization=specialization_id,
                synced_by=None  # Auto-sync (not manual admin)
            )
            if not sync_result.get('success'):
                # Log warning but don't fail the update
                logger.warning(
                    f"Auto-sync failed for user {student_id}, {specialization_id}: {sync_result.get('message')}"
                )
        except Exception as e:
            # Log error but don't fail the progress update
            logger.error(f"Auto-sync exception for user {student_id}: {str(e)}")

    return {
        'success': True,
        'new_xp': progress.total_xp,
        'old_level': old_level,
        'new_level': progress.current_level,
        'leveled_up': leveled_up,
        'levels_gained': levels_gained,
        'new_level_info': new_level_info,
        'sync_result': sync_result,  # Include sync result for transparency
        'achievements_earned': [
            {
                'title': ach.title,
                'description': ach.description,
                'icon': ach.icon
            }
            for ach in new_achievements
        ]
    }


def get_all_levels(db: Session, specialization_id: str) -> list[Dict[str, Any]]:
    """
    Get all levels for a specialization.
    HYBRID: Validates DB existence, then loads from JSON config files.

    Args:
        db: Database session
        specialization_id: GANCUJU_PLAYER, LFA_FOOTBALL_PLAYER, LFA_COACH, or INTERNSHIP
                          (also supports legacy: PLAYER, COACH)

    Returns:
        List of level dicts
    """
    config_loader = get_config_loader()

    # STEP 1: Validate specialization exists in DB (HYBRID check)
    if not validate_specialization_exists(db, specialization_id):
        logger.warning(f"Specialization {specialization_id} not found or inactive in DB")
        return []

    # Convert to enum
    spec_enum = specialization_id_to_enum(specialization_id)
    if not spec_enum:
        return []

    # STEP 2: Load from JSON config (Source of Truth)
    try:
        max_level = config_loader.get_max_level(spec_enum)
        levels = []

        for level in range(1, max_level + 1):
            level_info = get_level_requirements(db, specialization_id, level)
            if level_info:
                levels.append(level_info)

        return levels

    except Exception as e:
        logger.error(f"Error loading levels for {specialization_id}: {e}")
        return []


def enroll_user(db: Session, user_id: int, specialization_id: str) -> Dict[str, Any]:
    """
    Enroll user in specialization (HYBRID: DB validation + JSON config + Age/Consent validation).

    Process:
    1. Check DB (FK + is_active)
    2. Load JSON config for age requirements
    3. Validate age, parental consent
    4. Create progress record (DB)

    Args:
        db: Database session
        user_id: User ID to enroll
        specialization_id: Specialization to enroll in

    Returns:
        Dict with enrollment result

    Raises:
        ValueError: If validation fails
    """
    if not validate_specialization_exists(db, specialization_id):
        raise ValueError(f"Specialization '{specialization_id}' does not exist or is not active")

    # STEP 2: Get user
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # STEP 3: Validate age and consent requirements (JSON + User data)
    spec_enum = specialization_id_to_enum(specialization_id)
    validator = SpecializationValidator(db)
    validation_result = validator.validate_user_for_specialization(user, spec_enum, raise_exception=True)

    # STEP 4: Create progress record (DB)
    existing_progress = db.query(SpecializationProgress).filter_by(
        student_id=user_id,
        specialization_id=specialization_id
    ).first()

    if existing_progress:
        return {
            'success': False,
            'message': 'User already enrolled in this specialization',
            'progress': existing_progress
        }

    progress = SpecializationProgress(
        student_id=user_id,
        specialization_id=specialization_id,
        current_level=1,
        total_xp=0,
        completed_sessions=0,
        completed_projects=0
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)

    return {
        'success': True,
        'message': f'User enrolled in {specialization_id}',
        'progress': progress
    }
