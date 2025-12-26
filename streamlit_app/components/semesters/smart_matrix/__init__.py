"""
Smart Matrix Component
======================

Gap Detection & Quick Actions Module

Combines period generation + management in a single matrix view.
Allows admin to:
- See what periods/seasons are already generated
- Identify missing periods (gaps in coverage)
- Generate missing periods with one click
- Manage existing periods inline
"""

# Gap Detection Functions
from .gap_detection import (
    extract_existing_months,
    extract_existing_quarters,
    check_annual_exists,
    get_existing_semester_ids,
    calculate_coverage,
)

# Matrix Cell Rendering
from .matrix_cells import render_matrix_cell

# Quick Actions
from .quick_actions import (
    generate_missing_periods,
    edit_semester_action,
    delete_semester_action,
)

# Location Matrix
from .location_matrix import (
    render_location_matrix_header,
    render_age_group_label,
    render_matrix_row,
    render_coverage_matrix,
    render_legend,
)

# Instructor Integration
from .instructor_integration import (
    render_master_instructor_section,
    render_instructor_management_panel,
)

__all__ = [
    # Gap Detection
    "extract_existing_months",
    "extract_existing_quarters",
    "check_annual_exists",
    "get_existing_semester_ids",
    "calculate_coverage",
    # Matrix Cells
    "render_matrix_cell",
    # Quick Actions
    "generate_missing_periods",
    "edit_semester_action",
    "delete_semester_action",
    # Location Matrix
    "render_location_matrix_header",
    "render_age_group_label",
    "render_matrix_row",
    "render_coverage_matrix",
    "render_legend",
    # Instructor Integration
    "render_master_instructor_section",
    "render_instructor_management_panel",
]
