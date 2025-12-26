"""
DEPRECATED: This module has been refactored into app.services.specialization

This file remains for backward compatibility only.
All imports are redirected to the new modular structure.

For new code, use:
    from app.services.specialization import SpecializationService
    # or
    from app.services.specialization import enroll_lfa_player, get_lfa_player_progress

Old imports still work:
    from app.services.specialization_service import SpecializationService
"""

# Re-export everything from the new location
from app.services.specialization import (
    # Main class
    SpecializationService,

    # Validation & Common
    specialization_id_to_enum,
    handle_legacy_specialization,
    validate_specialization_exists,
    get_all_specializations,
    DEPRECATED_MAPPINGS,
    DEPRECATION_DEADLINE,
    DEPRECATION_WARNING,

    # Common functions
    get_level_requirements,
    get_student_progress,
    can_level_up,
    update_progress,
    get_all_levels,
    enroll_user,

    # LFA_PLAYER
    enroll_lfa_player,
    get_lfa_player_level_requirements,
    get_lfa_player_progress,
    update_lfa_player_progress,
    get_all_lfa_player_levels,

    # LFA_COACH
    enroll_lfa_coach,
    get_lfa_coach_level_requirements,
    get_lfa_coach_progress,
    update_lfa_coach_progress,
    get_all_lfa_coach_levels,

    # GANCUJU_PLAYER
    enroll_gancuju_player,
    get_gancuju_player_level_requirements,
    get_gancuju_player_progress,
    update_gancuju_player_progress,
    get_all_gancuju_player_levels,

    # INTERNSHIP
    enroll_internship,
    get_internship_level_requirements,
    get_internship_progress,
    update_internship_progress,
    get_all_internship_levels,
)

__all__ = [
    # Main class
    'SpecializationService',

    # Validation
    'specialization_id_to_enum',
    'handle_legacy_specialization',
    'validate_specialization_exists',
    'get_all_specializations',
    'DEPRECATED_MAPPINGS',
    'DEPRECATION_DEADLINE',
    'DEPRECATION_WARNING',

    # Common
    'get_level_requirements',
    'get_student_progress',
    'can_level_up',
    'update_progress',
    'get_all_levels',
    'enroll_user',

    # LFA_PLAYER
    'enroll_lfa_player',
    'get_lfa_player_level_requirements',
    'get_lfa_player_progress',
    'update_lfa_player_progress',
    'get_all_lfa_player_levels',

    # LFA_COACH
    'enroll_lfa_coach',
    'get_lfa_coach_level_requirements',
    'get_lfa_coach_progress',
    'update_lfa_coach_progress',
    'get_all_lfa_coach_levels',

    # GANCUJU_PLAYER
    'enroll_gancuju_player',
    'get_gancuju_player_level_requirements',
    'get_gancuju_player_progress',
    'update_gancuju_player_progress',
    'get_all_gancuju_player_levels',

    # INTERNSHIP
    'enroll_internship',
    'get_internship_level_requirements',
    'get_internship_progress',
    'update_internship_progress',
    'get_all_internship_levels',
]
