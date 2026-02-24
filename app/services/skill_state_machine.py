"""
🎯 Skill Assessment Lifecycle State Machine

Production-grade state machine for skill assessment lifecycle with:
- Explicit state definition and validation
- Invalid transition matrix
- Idempotent state transitions
- State transition audit trail

State Machine (Phase 1):
  NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED
                     ↓           ↓
                 ARCHIVED    ARCHIVED (when new assessment created)
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITIONS
# ============================================================================

class SkillAssessmentState:
    """Skill assessment lifecycle states"""
    NOT_ASSESSED = "NOT_ASSESSED"
    ASSESSED = "ASSESSED"
    VALIDATED = "VALIDATED"
    ARCHIVED = "ARCHIVED"
    # Phase 2: DISPUTED = "DISPUTED"

    @classmethod
    def all_states(cls) -> List[str]:
        """Get all valid states"""
        return [cls.NOT_ASSESSED, cls.ASSESSED, cls.VALIDATED, cls.ARCHIVED]

    @classmethod
    def active_states(cls) -> List[str]:
        """Get active (non-archived) states"""
        return [cls.ASSESSED, cls.VALIDATED]

    @classmethod
    def terminal_states(cls) -> List[str]:
        """Get terminal states (no transitions allowed)"""
        return [cls.ARCHIVED]


# ============================================================================
# TRANSITION MATRIX
# ============================================================================

# Valid state transitions (from_state -> [to_states])
VALID_TRANSITIONS: Dict[str, List[str]] = {
    SkillAssessmentState.NOT_ASSESSED: [
        SkillAssessmentState.NOT_ASSESSED,  # Idempotent (no-op)
        SkillAssessmentState.ASSESSED,      # Create assessment
    ],
    SkillAssessmentState.ASSESSED: [
        SkillAssessmentState.ASSESSED,      # Idempotent (no-op)
        SkillAssessmentState.VALIDATED,     # Admin validates
        SkillAssessmentState.ARCHIVED,      # New assessment replaces old
    ],
    SkillAssessmentState.VALIDATED: [
        SkillAssessmentState.VALIDATED,     # Idempotent (no-op)
        SkillAssessmentState.ARCHIVED,      # New assessment replaces old
    ],
    SkillAssessmentState.ARCHIVED: [
        SkillAssessmentState.ARCHIVED,      # Idempotent (no-op)
    ],
}

# Invalid transitions (explicitly documented for clarity)
INVALID_TRANSITIONS: Dict[str, List[str]] = {
    SkillAssessmentState.NOT_ASSESSED: [
        SkillAssessmentState.VALIDATED,     # Must create assessment first
        SkillAssessmentState.ARCHIVED,      # Must create assessment first
    ],
    SkillAssessmentState.ASSESSED: [
        SkillAssessmentState.NOT_ASSESSED,  # Cannot un-create assessment
    ],
    SkillAssessmentState.VALIDATED: [
        SkillAssessmentState.NOT_ASSESSED,  # Cannot un-create assessment
        SkillAssessmentState.ASSESSED,      # Cannot un-validate
    ],
    SkillAssessmentState.ARCHIVED: [
        SkillAssessmentState.NOT_ASSESSED,  # Terminal state
        SkillAssessmentState.ASSESSED,      # Terminal state
        SkillAssessmentState.VALIDATED,     # Terminal state
    ],
}


# ============================================================================
# STATE TRANSITION VALIDATION
# ============================================================================

def validate_state_transition(
    from_state: str,
    to_state: str,
    allow_idempotent: bool = True
) -> Tuple[bool, str]:
    """
    Validate state transition according to state machine rules.

    Args:
        from_state: Current state
        to_state: Target state
        allow_idempotent: Allow idempotent transitions (same state)

    Returns:
        (is_valid, error_message)
        - is_valid=True: Transition allowed
        - is_valid=False: Transition invalid (with reason)

    Examples:
        >>> validate_state_transition('ASSESSED', 'VALIDATED')
        (True, '')

        >>> validate_state_transition('VALIDATED', 'ASSESSED')
        (False, 'Invalid state transition: VALIDATED → ASSESSED. Cannot un-validate assessment.')

        >>> validate_state_transition('ASSESSED', 'ASSESSED', allow_idempotent=True)
        (True, '')

        >>> validate_state_transition('ASSESSED', 'ASSESSED', allow_idempotent=False)
        (False, 'Idempotent transition not allowed: ASSESSED → ASSESSED')
    """
    # Validate state values
    all_states = SkillAssessmentState.all_states()
    if from_state not in all_states:
        return False, f"Invalid from_state: {from_state}. Must be one of {all_states}"
    if to_state not in all_states:
        return False, f"Invalid to_state: {to_state}. Must be one of {all_states}"

    # Idempotent transition (same state)
    if from_state == to_state:
        if allow_idempotent:
            return True, ""  # Idempotent allowed
        else:
            return False, f"Idempotent transition not allowed: {from_state} → {to_state}"

    # Check valid transitions
    valid_targets = VALID_TRANSITIONS.get(from_state, [])
    if to_state in valid_targets:
        return True, ""

    # Invalid transition
    error_messages = {
        (SkillAssessmentState.NOT_ASSESSED, SkillAssessmentState.VALIDATED): (
            "Cannot validate non-existent assessment. Create assessment first (ASSESSED)."
        ),
        (SkillAssessmentState.NOT_ASSESSED, SkillAssessmentState.ARCHIVED): (
            "Cannot archive non-existent assessment. Create assessment first (ASSESSED)."
        ),
        (SkillAssessmentState.ASSESSED, SkillAssessmentState.NOT_ASSESSED): (
            "Cannot un-create assessment. Assessment already exists."
        ),
        (SkillAssessmentState.VALIDATED, SkillAssessmentState.NOT_ASSESSED): (
            "Cannot un-create validated assessment. Assessment already validated."
        ),
        (SkillAssessmentState.VALIDATED, SkillAssessmentState.ASSESSED): (
            "Cannot un-validate assessment. Validation is permanent."
        ),
        (SkillAssessmentState.ARCHIVED, SkillAssessmentState.NOT_ASSESSED): (
            "Cannot restore archived assessment. Archived state is terminal."
        ),
        (SkillAssessmentState.ARCHIVED, SkillAssessmentState.ASSESSED): (
            "Cannot restore archived assessment. Archived state is terminal."
        ),
        (SkillAssessmentState.ARCHIVED, SkillAssessmentState.VALIDATED): (
            "Cannot restore archived assessment. Archived state is terminal."
        ),
    }

    error_msg = error_messages.get(
        (from_state, to_state),
        f"Invalid state transition: {from_state} → {to_state}. Transition not allowed."
    )

    return False, error_msg


def is_terminal_state(state: str) -> bool:
    """
    Check if state is terminal (no transitions allowed except idempotent).

    Args:
        state: State to check

    Returns:
        True if terminal state, False otherwise

    Example:
        >>> is_terminal_state('ARCHIVED')
        True

        >>> is_terminal_state('ASSESSED')
        False
    """
    return state in SkillAssessmentState.terminal_states()


def get_valid_transitions(from_state: str) -> List[str]:
    """
    Get list of valid target states from current state.

    Args:
        from_state: Current state

    Returns:
        List of valid target states (excluding idempotent)

    Example:
        >>> get_valid_transitions('ASSESSED')
        ['VALIDATED', 'ARCHIVED']

        >>> get_valid_transitions('ARCHIVED')
        []
    """
    valid_targets = VALID_TRANSITIONS.get(from_state, [])
    # Exclude idempotent transition (same state)
    return [state for state in valid_targets if state != from_state]


# ============================================================================
# BUSINESS RULES
# ============================================================================

def determine_validation_requirement(
    license_level: int,
    instructor_tenure_days: int,
    skill_category: str
) -> bool:
    """
    Determine if assessment requires admin validation.

    Business Rules (Phase 1):
    1. High-stakes assessments (license level 5+) require validation
    2. New instructors (< 6 months tenure) require validation
    3. Critical skill categories require validation (mental, set_pieces)
    4. Default: auto-accepted (no validation required)

    Args:
        license_level: Current license level (1-8)
        instructor_tenure_days: Instructor tenure in days
        skill_category: Skill category ('outfield', 'set_pieces', 'mental', 'physical')

    Returns:
        True if validation required, False if auto-accepted

    Examples:
        >>> determine_validation_requirement(5, 200, 'outfield')
        True  # High-stakes (level 5+)

        >>> determine_validation_requirement(3, 100, 'outfield')
        True  # New instructor (< 180 days)

        >>> determine_validation_requirement(3, 200, 'mental')
        True  # Critical skill category

        >>> determine_validation_requirement(3, 200, 'physical')
        False  # Auto-accepted (no validation)
    """
    # Rule 1: High-stakes assessments (license level 5+)
    if license_level >= 5:
        logger.info(
            f"Validation required: High-stakes (license_level={license_level} >= 5)"
        )
        return True

    # Rule 2: New instructors (< 6 months = 180 days)
    INSTRUCTOR_PROBATION_DAYS = 180
    if instructor_tenure_days < INSTRUCTOR_PROBATION_DAYS:
        logger.info(
            f"Validation required: New instructor (tenure={instructor_tenure_days} < {INSTRUCTOR_PROBATION_DAYS} days)"
        )
        return True

    # Rule 3: Critical skill categories
    CRITICAL_SKILL_CATEGORIES = ['mental', 'set_pieces']
    if skill_category in CRITICAL_SKILL_CATEGORIES:
        logger.info(
            f"Validation required: Critical skill category (category={skill_category})"
        )
        return True

    # Rule 4: Default - auto-accepted
    logger.info(
        f"Validation NOT required: Auto-accepted (level={license_level}, "
        f"tenure={instructor_tenure_days}, category={skill_category})"
    )
    return False


def get_skill_category(skill_name: str) -> str:
    """
    Get skill category for a given skill name.

    Uses skills_config.py to determine category.

    Args:
        skill_name: Skill name (e.g., 'ball_control', 'free_kicks')

    Returns:
        Category key ('outfield', 'set_pieces', 'mental', 'physical')
        Returns 'unknown' if skill not found

    Examples:
        >>> get_skill_category('ball_control')
        'outfield'

        >>> get_skill_category('free_kicks')
        'set_pieces'

        >>> get_skill_category('composure')
        'mental'
    """
    from ..skills_config import SKILL_CATEGORIES

    for category in SKILL_CATEGORIES:
        for skill in category['skills']:
            if skill['key'] == skill_name:
                return category['key']

    logger.warning(f"Skill category not found for skill_name={skill_name}, returning 'unknown'")
    return 'unknown'


# ============================================================================
# STATE TRANSITION HELPERS
# ============================================================================

def create_state_transition_audit(
    previous_status: str,
    new_status: str,
    changed_by: int,
    reason: Optional[str] = None
) -> Dict[str, any]:
    """
    Create state transition audit data.

    Args:
        previous_status: Previous state
        new_status: New state
        changed_by: User ID who triggered transition
        reason: Optional reason for transition

    Returns:
        Dictionary with audit fields for database update

    Example:
        >>> create_state_transition_audit('ASSESSED', 'VALIDATED', 123, 'Admin validated')
        {
            'previous_status': 'ASSESSED',
            'status': 'VALIDATED',
            'status_changed_at': datetime(...),
            'status_changed_by': 123,
            'status_change_reason': 'Admin validated'
        }
    """
    return {
        'previous_status': previous_status,
        'status': new_status,
        'status_changed_at': datetime.now(timezone.utc),
        'status_changed_by': changed_by,
        # Note: status_change_reason not in schema yet (Phase 2)
    }


def log_state_transition(
    assessment_id: int,
    from_state: str,
    to_state: str,
    changed_by: int,
    reason: Optional[str] = None
) -> None:
    """
    Log state transition for audit trail.

    Args:
        assessment_id: Assessment ID
        from_state: Previous state
        to_state: New state
        changed_by: User ID who triggered transition
        reason: Optional reason for transition
    """
    if from_state == to_state:
        logger.info(
            f"🔒 IDEMPOTENT: Assessment {assessment_id} already in state {to_state} "
            f"(no change, user={changed_by})"
        )
    else:
        logger.info(
            f"✅ STATE TRANSITION: Assessment {assessment_id}: {from_state} → {to_state} "
            f"(user={changed_by}, reason={reason or 'N/A'})"
        )
