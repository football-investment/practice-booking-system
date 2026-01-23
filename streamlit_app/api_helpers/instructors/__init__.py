"""
Instructor Management API Helpers - Modular Package

This package provides a modular structure for instructor management API functions.
All functions are exported for backward compatibility with the original flat structure.

Modules:
- masters: Master instructor management, direct hire offers, legacy functions
- positions: Position posting, job board, status management
- applications: Job applications, application review and tracking
- assignments: Instructor assignments, matrix integration, co-instructors
- availability: Instructor availability windows and scheduling
- licenses: User license retrieval for badge display
"""

# Import from masters module
from .masters import (
    create_direct_hire_offer,
    respond_to_master_offer,
    get_my_master_offers,
    get_pending_master_offers,
    cancel_master_offer,
    hire_from_application,
    create_master_instructor,
    get_master_for_location,
    list_all_masters,
    update_master_instructor,
    terminate_master_instructor,
    get_available_instructors,
)

# Import from positions module
from .positions import (
    create_position,
    get_all_positions,
    get_position_by_id,
    get_job_board,
    update_position,
    delete_position,
    close_position,
)

# Import from applications module
from .applications import (
    apply_to_position,
    get_my_applications,
    get_applications_for_position,
    review_application,
    accept_application,
    decline_application,
    withdraw_application,
)

# Import from assignments module
from .assignments import (
    assign_instructor_to_session,
    get_instructor_assignments,
    get_session_instructors,
    update_instructor_assignment,
    remove_instructor_from_session,
    delete_assignment,
    get_location_instructors_summary,
    create_assignment_from_application,
)

# Import from availability module
from .availability import (
    set_instructor_availability,
    get_instructor_availability,
    update_availability,
    delete_availability,
)

# Import from licenses module
from .licenses import (
    get_user_licenses,
)

# Public API - all functions available for import
__all__ = [
    # Masters
    "create_direct_hire_offer",
    "respond_to_master_offer",
    "get_my_master_offers",
    "get_pending_master_offers",
    "cancel_master_offer",
    "hire_from_application",
    "create_master_instructor",
    "get_master_for_location",
    "list_all_masters",
    "update_master_instructor",
    "terminate_master_instructor",
    "get_available_instructors",
    # Positions
    "create_position",
    "get_all_positions",
    "get_position_by_id",
    "get_job_board",
    "update_position",
    "delete_position",
    "close_position",
    # Applications
    "apply_to_position",
    "get_my_applications",
    "get_applications_for_position",
    "review_application",
    "accept_application",
    "decline_application",
    "withdraw_application",
    # Assignments
    "assign_instructor_to_session",
    "get_instructor_assignments",
    "get_session_instructors",
    "update_instructor_assignment",
    "remove_instructor_from_session",
    "delete_assignment",
    "get_location_instructors_summary",
    "create_assignment_from_application",
    # Availability
    "set_instructor_availability",
    "get_instructor_availability",
    "update_availability",
    "delete_availability",
    # Licenses
    "get_user_licenses",
]
