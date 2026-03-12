"""
Intelligent Semester/Season Overview Wrapper

This provides helper functions that automatically adapt labels based on
the specialization type being displayed.
"""

from components.period_labels import get_period_label, get_count_text


def get_semester_count_label(count: int, specialization_type: str = None) -> str:
    """
    Get the right label for semester/season count
    
    If specialization_type is provided, uses intelligent labeling.
    Otherwise, uses generic "periods"
    
    Examples:
        >>> get_semester_count_label(3, "LFA_PLAYER")
        '3 seasons'
        >>> get_semester_count_label(5, "INTERNSHIP")  
        '5 semesters'
        >>> get_semester_count_label(2)  # No spec provided
        '2 periods'
    """
    if specialization_type:
        return get_count_text(count, specialization_type)
    else:
        return f"{count} period{'s' if count != 1 else ''}"


def get_expander_label_for_spec(spec: str, count: int) -> str:
    """
    Get expander label with intelligent labeling
    
    Examples:
        >>> get_expander_label_for_spec("LFA_PLAYER", 3)
        '⚽ **LFA_PLAYER** (3 seasons)'
        >>> get_expander_label_for_spec("INTERNSHIP", 5)
        '⚽ **INTERNSHIP** (5 semesters)'
    """
    count_text = get_semester_count_label(count, spec)
    return f"⚽ **{spec}** ({count_text})"


def get_no_periods_message(specialization_type: str = None) -> str:
    """
    Get the "no periods" message with intelligent labeling
    
    Examples:
        >>> get_no_periods_message("LFA_PLAYER")
        '📭 No seasons in this group'
        >>> get_no_periods_message("INTERNSHIP")
        '📭 No semesters in this group'
    """
    if specialization_type:
        label = get_period_label(specialization_type, plural=True, capitalize=False)
    else:
        label = "periods"
    
    return f"📭 No {label} in this group"
