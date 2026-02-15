"""
Admin Dashboard - Users Tab Component
User management with filters and actions
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers import get_users
from components.user_filters import render_user_filters, apply_user_filters
from components.user_actions import render_user_action_buttons


def render_users_tab(token, user):
    """
    Render the Users tab with user management.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    # Main layout with sidebar filters
    filter_col, main_col = st.columns([1, 3])

    # Sidebar: Filters
    with filter_col:
        user_filters = render_user_filters()

    # Main area: User cards
    with main_col:
        st.markdown("### 👥 User Management")
        st.caption("View and manage all users in the system")

        with st.spinner("Loading users..."):
            success, users = get_users(token, limit=100)

        if success and users:
            # Apply filters
            filtered_users = apply_user_filters(users, user_filters)

            # Stats widgets
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

            students_count = len([u for u in filtered_users if u.get("role") == "student"])
            instructors_count = len([u for u in filtered_users if u.get("role") == "instructor"])
            admins_count = len([u for u in filtered_users if u.get("role") == "admin"])
            active_count = len([u for u in filtered_users if u.get("is_active")])

            with stats_col1:
                st.metric("👥 Total", len(filtered_users))
            with stats_col2:
                st.metric("🎓 Students", students_count)
            with stats_col3:
                st.metric("👨‍🏫 Instructors", instructors_count)
            with stats_col4:
                st.metric("✅ Active", active_count)

            st.divider()

            # User cards with action buttons (paginated rendering)
            if filtered_users:
                USERS_PER_PAGE = 100
                total_pages = max(1, (len(filtered_users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE)

                if "users_page" not in st.session_state:
                    st.session_state.users_page = 1

                # Reset to page 1 if filters changed the list size
                if st.session_state.users_page > total_pages:
                    st.session_state.users_page = 1

                current_page = st.session_state.users_page
                start_idx = (current_page - 1) * USERS_PER_PAGE
                end_idx = min(start_idx + USERS_PER_PAGE, len(filtered_users))
                page_users = filtered_users[start_idx:end_idx]

                st.caption(f"📋 Showing {start_idx + 1}–{end_idx} of {len(filtered_users)} user(s):")

                if total_pages > 1:
                    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                    with nav_col1:
                        if st.button("◀ Prev", disabled=(current_page == 1), key="users_prev"):
                            st.session_state.users_page -= 1
                            st.rerun()
                    with nav_col2:
                        st.caption(f"Page {current_page} / {total_pages}")
                    with nav_col3:
                        if st.button("Next ▶", disabled=(current_page == total_pages), key="users_next"):
                            st.session_state.users_page += 1
                            st.rerun()

                for user_item in page_users:
                    role = user_item.get("role", "").lower()
                    role_icon = {"student": "🎓", "instructor": "👨‍🏫", "admin": "👑"}.get(role, "👤")
                    status_icon = "✅" if user_item.get('is_active') else "❌"

                    with st.expander(
                        f"{role_icon} **{user_item.get('name', 'Unknown')}** ({user_item.get('email', 'N/A')}) {status_icon}",
                        expanded=False
                    ):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**📋 Basic Info**")
                            st.caption(f"ID: {user_item.get('id')}")
                            st.caption(f"Email: {user_item.get('email', 'N/A')}")
                            st.caption(f"Name: {user_item.get('name', 'N/A')}")

                        with col2:
                            st.markdown("**🔑 Role & Access**")
                            st.caption(f"Role: {role.title()}")
                            st.caption(f"Status: {'✅ Active' if user_item.get('is_active') else '❌ Inactive'}")

                            licenses = user_item.get('licenses', [])
                            if licenses:
                                st.caption(f"📜 Licenses: {len(licenses)}")
                                license_types = {}
                                for lic in licenses:
                                    spec_type = lic.get('specialization_type', 'Unknown')
                                    if spec_type.startswith('LFA_'):
                                        spec_type = spec_type.replace('LFA_', '')
                                    formatted = spec_type.replace('_', ' ').title()
                                    license_types[formatted] = license_types.get(formatted, 0) + 1

                                for spec_type, count in sorted(license_types.items()):
                                    if count > 1:
                                        st.caption(f"  • {spec_type} x{count}")
                                    else:
                                        st.caption(f"  • {spec_type}")
                            else:
                                st.caption("📜 Licenses: None")

                        with col3:
                            st.markdown("**💰 Credits & Stats**")
                            st.metric("Credit Balance", user_item.get('credit_balance', 0))

                        st.divider()
                        # Action buttons (from compact component)
                        render_user_action_buttons(user_item, token)
            else:
                st.info("No users match the selected filters")

        elif success and not users:
            st.info("No users found")
        else:
            st.error("❌ Failed to load users")
