"""
Period Labeling System - Intelligent Season vs Semester

This module provides dynamic labeling based on specialization type:
- Session-based (LFA_PLAYER) -> "Season" 
- Semester-based (INTERNSHIP, COACH, GANCUJU) -> "Semester"

Usage:
    from period_labels import get_period_label, get_period_labels
    
    label = get_period_label("LFA_PLAYER")  # Returns "Season"
    labels = get_period_labels("INTERNSHIP")  # Returns {"singular": "Semester", "plural": "Semesters", ...}
"""

from typing import Dict


# ============================================================================
# SPECIALIZATION TYPE MAPPING
# ============================================================================

SESSION_BASED_SPECS = [
    'LFA_PLAYER',       # Football Player - Season-based (age groups, no semester commitment)
]

SEMESTER_BASED_SPECS = [
    'INTERNSHIP',       # LFA Internship - Semester-based (formal education structure)
    'COACH',            # LFA Coach - Semester-based (teaching credentials)
    'GANCUJU',          # GānCuju Player - Semester-based (belt progression, traditional structure)
]


# ============================================================================
# LABEL GENERATION FUNCTIONS
# ============================================================================

def is_session_based(specialization_type: str) -> bool:
    """
    Check if a specialization is session-based (uses "Season" terminology)
    
    Args:
        specialization_type: e.g., "LFA_PLAYER", "LFA_PLAYER_PRE", "INTERNSHIP"
        
    Returns:
        True if session-based (Season), False if semester-based (Semester)
    """
    if not specialization_type:
        return False
    
    # Check if any session-based spec is in the type
    return any(spec in specialization_type.upper() for spec in SESSION_BASED_SPECS)


def get_period_label(specialization_type: str, plural: bool = False, capitalize: bool = True) -> str:
    """
    Get the appropriate period label (Season/Semester) for a specialization
    
    Args:
        specialization_type: e.g., "LFA_PLAYER", "INTERNSHIP"
        plural: Return plural form if True
        capitalize: Capitalize first letter if True
        
    Returns:
        "Season" or "Semester" (or plural/lowercase variants)
        
    Examples:
        >>> get_period_label("LFA_PLAYER")
        'Season'
        >>> get_period_label("LFA_PLAYER", plural=True)
        'Seasons'
        >>> get_period_label("INTERNSHIP")
        'Semester'
        >>> get_period_label("INTERNSHIP", plural=True, capitalize=False)
        'semesters'
    """
    if is_session_based(specialization_type):
        base = "season"
    else:
        base = "semester"
    
    if plural:
        base = base + "s"
    
    if capitalize:
        base = base.capitalize()
    
    return base


def get_period_labels(specialization_type: str) -> Dict[str, str]:
    """
    Get all period label variants for a specialization
    
    Args:
        specialization_type: e.g., "LFA_PLAYER", "INTERNSHIP"
        
    Returns:
        Dictionary with label variants:
        {
            "singular": "Season",
            "plural": "Seasons", 
            "singular_lower": "season",
            "plural_lower": "seasons",
            "emoji": "⚽" or "📚"
        }
        
    Example:
        >>> labels = get_period_labels("LFA_PLAYER")
        >>> print(f"Generate {labels['plural']}")  # "Generate Seasons"
    """
    is_season = is_session_based(specialization_type)
    
    return {
        "singular": "Season" if is_season else "Semester",
        "plural": "Seasons" if is_season else "Semesters",
        "singular_lower": "season" if is_season else "semester",
        "plural_lower": "seasons" if is_season else "semesters",
        "emoji": "⚽" if is_season else "📚",
        "cycle_type": "season-based" if is_season else "semester-based"
    }


def format_period_text(template: str, specialization_type: str, **kwargs) -> str:
    """
    Format text with automatic period label substitution
    
    Args:
        template: Text template with {period}, {periods}, {Period}, {Periods} placeholders
        specialization_type: Specialization type
        **kwargs: Additional format arguments
        
    Returns:
        Formatted text with period labels substituted
        
    Example:
        >>> format_period_text(
        ...     "Generate {Periods} for {spec}",
        ...     "LFA_PLAYER",
        ...     spec="LFA Player"
        ... )
        'Generate Seasons for LFA Player'
    """
    labels = get_period_labels(specialization_type)
    
    # Add period labels to kwargs
    format_args = {
        "period": labels["singular_lower"],
        "periods": labels["plural_lower"],
        "Period": labels["singular"],
        "Periods": labels["plural"],
        "period_emoji": labels["emoji"],
        **kwargs
    }
    
    return template.format(**format_args)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_generate_button_text(specialization_type: str) -> str:
    """Get the text for the generate button"""
    label = get_period_label(specialization_type, plural=True)
    return f"🚀 Generate {label}"


def get_count_text(count: int, specialization_type: str) -> str:
    """Get formatted count text (e.g., '3 seasons', '5 semesters')"""
    label = get_period_label(specialization_type, plural=(count != 1), capitalize=False)
    return f"{count} {label}"


def get_header_text(specialization_type: str) -> str:
    """Get header text for generation page"""
    label = get_period_label(specialization_type, plural=True)
    return f"🚀 Generate {label} for a Year"
