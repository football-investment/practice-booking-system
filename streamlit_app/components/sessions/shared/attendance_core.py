"""
Core attendance functionality shared between regular and tournament sessions.

This module provides reusable components for attendance tracking that work
for both regular sessions (4 statuses) and tournaments (2 statuses).
"""

import streamlit as st
from typing import Dict, List, Tuple


def calculate_attendance_summary(
    bookings: List[Dict],
    attendance_map: Dict[int, str]
) -> Tuple[int, int, int, int, int]:
    """
    Calculate attendance summary statistics.

    Args:
        bookings: List of booking objects
        attendance_map: Dict mapping user_id -> attendance status

    Returns:
        Tuple of (present_count, absent_count, late_count, excused_count, pending_count)

    Example:
        >>> bookings = [{"user": {"id": 1}}, {"user": {"id": 2}}]
        >>> attendance_map = {1: "present", 2: "absent"}
        >>> calculate_attendance_summary(bookings, attendance_map)
        (1, 1, 0, 0, 0)
    """
    present_count = sum(1 for s in attendance_map.values() if s == 'present')
    absent_count = sum(1 for s in attendance_map.values() if s == 'absent')
    late_count = sum(1 for s in attendance_map.values() if s == 'late')
    excused_count = sum(1 for s in attendance_map.values() if s == 'excused')
    pending_count = len(bookings) - len(attendance_map)

    return present_count, absent_count, late_count, excused_count, pending_count


def render_attendance_status_badge(
    user_name: str,
    user_email: str,
    current_status: str
) -> None:
    """
    Render visual badge for student with current attendance status.

    Args:
        user_name: Student name
        user_email: Student email
        current_status: Current attendance status (present, absent, late, excused, or None)

    Renders:
        Streamlit success/error/warning/info box with student name and email
    """
    if current_status == 'present':
        st.success(f"✅ **{user_name}**")
        st.caption(user_email)
    elif current_status == 'absent':
        st.error(f"❌ **{user_name}**")
        st.caption(user_email)
    elif current_status == 'late':
        st.warning(f"⏰ **{user_name}**")
        st.caption(user_email)
    elif current_status == 'excused':
        st.info(f"🎫 **{user_name}**")
        st.caption(user_email)
    else:
        st.info(f"⏳ **{user_name}**")
        st.caption(user_email)
