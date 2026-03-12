"""
Instructor Management UI Components

Provides UI components for the two-tier instructor management system:
- Master instructor management (Admin)
- Position posting and job board (Master + All instructors)
- Application workflow (Instructors → Master)
- Instructor assignments (Matrix integration)
"""

from .master_section import render_master_section
from .instructor_panel import render_instructor_panel
from .cell_instructor_modal import show_cell_instructors_modal
from .position_posting_modal import show_position_posting_modal
from .application_review import render_application_review
from .reassignment_dialog import show_reassignment_dialog

__all__ = [
    "render_master_section",
    "render_instructor_panel",
    "show_cell_instructors_modal",
    "show_position_posting_modal",
    "render_application_review",
    "show_reassignment_dialog",
]
