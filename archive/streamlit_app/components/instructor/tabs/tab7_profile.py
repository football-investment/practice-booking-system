"""
Instructor Dashboard — Tab 7: My Profile
==========================================

Phase 3 extraction Step 3.1 (lowest risk — fully self-contained).
Displays instructor licenses, teaching permissions, and license details.

Public API:
    render_profile_tab(token, user)
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

import streamlit as st

from config import SPECIALIZATIONS
from api_helpers_instructors import get_user_licenses


def render_profile_tab(token: str, user: Dict[str, Any]) -> None:
    """Render the 'My Profile' tab content.

    Args:
        token: Bearer JWT for the authenticated instructor.
        user:  Session user dict (from st.session_state[SESSION_USER_KEY]).
    """
    st.markdown("### 👤 My Profile")
    st.caption("Your licenses, teaching permissions, and instructor status")

    # Fetch instructor's teaching licenses
    instructor_licenses = get_user_licenses(token, user.get('id'))

    # Display instructor profile in 3-column layout (similar to student profile)
    profile_col1, profile_col2, profile_col3 = st.columns([2, 2, 2])

    # ============================================================================
    # COLUMN 1: BASIC INFORMATION
    # ============================================================================
    with profile_col1:
        st.markdown("**📋 Basic Information**")
        st.caption(f"**Name:** {user.get('name', 'N/A')}")
        st.caption(f"**Email:** {user.get('email', 'N/A')}")
        st.caption(f"**Role:** Instructor")

        # Check if user is a Master Instructor
        is_master = user.get('is_master_instructor', False)
        if is_master:
            st.caption("**Status:** ⭐ Master Instructor")
        else:
            st.caption("**Status:** Regular Instructor")

    # ============================================================================
    # COLUMN 2: TEACHING LICENSES
    # ============================================================================
    with profile_col2:
        st.markdown("**📜 Teaching Licenses**")

        if instructor_licenses:
            # Deduplicate by specialization_type, keep highest level
            grouped_licenses = {}
            for lic in instructor_licenses:
                spec_type = lic.get('specialization_type')
                current_level = lic.get('current_level', 1)

                if spec_type not in grouped_licenses:
                    grouped_licenses[spec_type] = lic
                else:
                    if current_level > grouped_licenses[spec_type].get('current_level', 0):
                        grouped_licenses[spec_type] = lic

            active_licenses = [lic for lic in grouped_licenses.values() if lic.get('is_active', True)]

            if active_licenses:
                st.caption("**✅ Active Licenses:**")
                for lic in active_licenses:
                    spec_type = lic.get('specialization_type', 'Unknown')
                    current_level = lic.get('current_level', 1)
                    display_name = _spec_display_name(spec_type)
                    st.caption(f"• {display_name} (Level {current_level})")
            else:
                st.caption("**No active teaching licenses**")
                st.caption("_Contact admin to get licensed_")
        else:
            active_licenses = []
            st.caption("**No teaching licenses found**")
            st.caption("_You need licenses to accept teaching assignments_")

    # ============================================================================
    # COLUMN 3: TEACHING PERMISSIONS
    # ============================================================================
    with profile_col3:
        st.markdown("**🎯 Teaching Permissions**")

        if instructor_licenses:
            teaching_permissions = []

            for lic in active_licenses:
                spec_type = lic.get('specialization_type', 'Unknown')
                current_level = lic.get('current_level', 1)

                if spec_type == 'LFA_COACH':
                    # ALL levels (1-8) authorized
                    teaching_permissions.append("LFA Football Player programs")
                    teaching_permissions.append("LFA Coach programs")

                elif spec_type == 'INTERNSHIP':
                    # ONLY Level 5 (Principal) can teach
                    if current_level == 5:
                        teaching_permissions.append("LFA Internship mentoring")

                elif spec_type == 'GANCUJU_PLAYER':
                    # ONLY Level 5-8 can teach
                    if current_level >= 5:
                        teaching_permissions.append("GānCuju player training")

            permission_count = len(teaching_permissions)
            st.metric("Can Teach", f"{permission_count} program type{'s' if permission_count != 1 else ''}")

            st.markdown("---")

            if permission_count > 0:
                st.caption("**You are qualified to teach:**")
                for permission in teaching_permissions:
                    st.caption(f"• {permission}")
            else:
                st.caption("**No instructor authorization**")
                st.caption("_Reach higher levels to gain teaching permissions!_")
        else:
            st.info("⚠️ No teaching licenses - cannot accept assignments")

    st.divider()

    # Show detailed license information
    if instructor_licenses:
        with st.expander("📊 Detailed License Information"):
            for lic in active_licenses:
                spec_type = lic.get('specialization_type', 'Unknown')
                current_level = lic.get('current_level', 1)
                display_name = _spec_display_name(spec_type)
                is_active = lic.get('is_active', True)
                status_badge = "✅ Active" if is_active else "❌ Inactive"

                st.markdown(f"**{display_name} (Level {current_level})** - {status_badge}")

                col_a, col_b = st.columns(2)
                with col_a:
                    issued_at = lic.get('issued_at')
                    if issued_at:
                        try:
                            if isinstance(issued_at, str):
                                issued_date = datetime.fromisoformat(issued_at.replace('Z', '+00:00'))
                            else:
                                issued_date = issued_at
                            st.caption(f"Issued: {issued_date.strftime('%Y-%m-%d')}")
                        except Exception:
                            st.caption("Issued: Unknown")
                    else:
                        started_at = lic.get('started_at')
                        if started_at:
                            try:
                                if isinstance(started_at, str):
                                    start_date = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                                else:
                                    start_date = started_at
                                st.caption(f"Started: {start_date.strftime('%Y-%m-%d')}")
                            except Exception:
                                st.caption("Issued: Unknown")
                        else:
                            st.caption("Issued: Unknown")

                with col_b:
                    expires_at = lic.get('expires_at')
                    if expires_at:
                        try:
                            if isinstance(expires_at, str):
                                expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            else:
                                expiry_date = expires_at

                            st.caption(f"Valid until: {expiry_date.strftime('%Y-%m-%d')}")

                            days_remaining = (expiry_date - datetime.now()).days
                            if days_remaining < 0:
                                st.error(f"⚠️ EXPIRED {abs(days_remaining)} days ago!")
                            elif days_remaining <= 30:
                                st.warning(f"⚠️ Expires in {days_remaining} days")
                        except Exception:
                            st.caption("Valid until: Unknown")
                    else:
                        st.caption("Valid until: Perpetual")

                st.markdown("---")


# ── Private helpers ───────────────────────────────────────────────────────────

def _spec_display_name(spec_type: str) -> str:
    """Map specialization_type to a human-readable display name."""
    _NAMES = {
        'GANCUJU_PLAYER':     'GānCuju Player',
        'LFA_COACH':          'LFA Coach',
        'INTERNSHIP':         'Internship',
        'LFA_FOOTBALL_PLAYER': 'LFA Football Player',
    }
    return _NAMES.get(spec_type) or SPECIALIZATIONS.get(spec_type, spec_type)
