"""
Specialization Service Factory

This module provides a factory pattern for instantiating the correct
specialization service based on the user's specialization type.

Usage:
    from app.services.specs import get_spec_service

    # Get service for a user
    service = get_spec_service(user.specialization)
    can_book, reason = service.can_book_session(user, session, db)

Supported Specializations:
    - LFA_PLAYER_* (PRE, YOUTH, AMATEUR, PRO) → LFAPlayerService
    - GANCUJU_PLAYER_* → GanCujuPlayerService
    - LFA_COACH_* → LFACoachService
    - LFA_INTERNSHIP → LFAInternshipService
"""

from typing import Optional
from app.services.specs.base_spec import BaseSpecializationService


# ============================================================================
# SERVICE REGISTRY
# ============================================================================

# Will be populated as services are implemented
_SERVICE_REGISTRY = {}


def register_service(spec_prefix: str, service_class):
    """
    Register a specialization service class.

    Args:
        spec_prefix: Prefix to match (e.g., "LFA_PLAYER", "LFA_COACH")
        service_class: Service class to instantiate
    """
    _SERVICE_REGISTRY[spec_prefix] = service_class


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_spec_service(spec_type: str) -> BaseSpecializationService:
    """
    Factory function to get appropriate service based on specialization type.

    This function implements a prefix-matching strategy to handle age-group
    variants (e.g., LFA_PLAYER_PRE, LFA_PLAYER_YOUTH) without needing
    separate service classes for each age group.

    Args:
        spec_type: Full specialization type from user record
                   (e.g., "LFA_PLAYER_PRE", "LFA_COACH", "GANCUJU_PLAYER_YOUTH")

    Returns:
        Instance of appropriate specialization service

    Raises:
        ValueError: If specialization type is unknown or not supported

    Examples:
        >>> service = get_spec_service("LFA_PLAYER_PRE")
        >>> isinstance(service, LFAPlayerService)
        True

        >>> service = get_spec_service("LFA_COACH")
        >>> isinstance(service, LFACoachService)
        True
    """
    if not spec_type:
        raise ValueError("Specialization type cannot be empty")

    # Try to find matching service by prefix
    for prefix, service_class in _SERVICE_REGISTRY.items():
        if spec_type.startswith(prefix):
            return service_class()

    # If no match found, raise error with helpful message
    available = ", ".join(_SERVICE_REGISTRY.keys())
    raise ValueError(
        f"Unknown specialization type: '{spec_type}'. "
        f"Available prefixes: {available}"
    )


# ============================================================================
# LAZY IMPORTS & REGISTRATION
# ============================================================================

def _register_all_services():
    """
    Import and register all available specialization services.

    This function is called on first use to avoid circular imports.
    Services are imported only when needed (lazy loading).
    """
    global _SERVICE_REGISTRY

    # Avoid re-registration
    if _SERVICE_REGISTRY:
        return

    # Import session-based services
    try:
        from app.services.specs.session_based.lfa_player_service import LFAPlayerService
        register_service("LFA_PLAYER", LFAPlayerService)
    except ImportError:
        pass  # Service not yet implemented

    # Import semester-based services
    try:
        from app.services.specs.semester_based.gancuju_player_service import GanCujuPlayerService
        register_service("GANCUJU_PLAYER", GanCujuPlayerService)
    except ImportError:
        pass  # Service not yet implemented

    try:
        from app.services.specs.semester_based.lfa_coach_service import LFACoachService
        register_service("LFA_COACH", LFACoachService)
    except ImportError:
        pass  # Service not yet implemented

    try:
        from app.services.specs.semester_based.lfa_internship_service import LFAInternshipService
        register_service("INTERNSHIP", LFAInternshipService)
    except ImportError:
        pass  # Service not yet implemented


# Ensure services are registered on first import
_register_all_services()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'BaseSpecializationService',
    'get_spec_service',
    'register_service',
]
