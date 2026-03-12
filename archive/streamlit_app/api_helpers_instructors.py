"""
REDIRECT: This file has been refactored into modular structure

All functions are now available via:
    from api_helpers.instructors import *

This redirect file maintains backward compatibility with existing imports:
    from api_helpers_instructors import *

See streamlit_app/api_helpers/instructors/ for modular implementation.
"""

from api_helpers.instructors import (
    # Masters
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
    # Positions
    create_position,
    get_all_positions,
    get_position_by_id,
    get_job_board,
    update_position,
    delete_position,
    close_position,
    # Applications
    apply_to_position,
    get_my_applications,
    get_applications_for_position,
    review_application,
    accept_application,
    decline_application,
    withdraw_application,
    # Assignments
    assign_instructor_to_session,
    get_instructor_assignments,
    get_session_instructors,
    update_instructor_assignment,
    remove_instructor_from_session,
    delete_assignment,
    get_location_instructors_summary,
    create_assignment_from_application,
    # Availability
    set_instructor_availability,
    get_instructor_availability,
    update_availability,
    delete_availability,
    # Licenses
    get_user_licenses,
)

__all__ = [
    # Masters (11 functions)
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
    # Positions (7 functions)
    "create_position",
    "get_all_positions",
    "get_position_by_id",
    "get_job_board",
    "update_position",
    "delete_position",
    "close_position",
    # Applications (7 functions)
    "apply_to_position",
    "get_my_applications",
    "get_applications_for_position",
    "review_application",
    "accept_application",
    "decline_application",
    "withdraw_application",
    # Assignments (8 functions)
    "assign_instructor_to_session",
    "get_instructor_assignments",
    "get_session_instructors",
    "update_instructor_assignment",
    "remove_instructor_from_session",
    "delete_assignment",
    "get_location_instructors_summary",
    "create_assignment_from_application",
    # Availability (4 functions)
    "set_instructor_availability",
    "get_instructor_availability",
    "update_availability",
    "delete_availability",
    # Licenses (1 function)
    "get_user_licenses",
    "get_master_instructor_by_location",  # Alias for backward compatibility
    "get_pending_offers",  # Alias for backward compatibility
    "cancel_offer",  # Alias for backward compatibility
    "get_positions_by_location",  # Alias for backward compatibility
    "get_my_positions",  # Alias for backward compatibility
    "create_assignment",  # Alias for backward compatibility
    "get_matrix_cell_instructors",  # Alias for backward compatibility
    "deactivate_assignment",  # Alias for backward compatibility
]

# Backward compatibility alias
get_master_instructor_by_location = get_master_for_location
get_pending_offers = get_pending_master_offers
cancel_offer = cancel_master_offer
get_positions_by_location = get_all_positions
get_my_positions = get_all_positions
create_assignment = assign_instructor_to_session
get_matrix_cell_instructors = get_session_instructors
deactivate_assignment = remove_instructor_from_session
