"""
User Modals Component
Edit, View, and Reset Password modals for users
"""

import streamlit as st
import secrets
import string
from typing import Dict, Any, Optional
from api_helpers import update_user
from api_helpers_general import reset_user_password


def render_edit_user_modal(user: Dict[str, Any], token: str) -> bool:
    """
    Render edit user modal with form

    Args:
        user: User data dictionary
        token: Authentication token

    Returns:
        True if user was updated, False otherwise
    """
    user_id = user.get('id')
    modal_key = f"edit_user_modal_{user_id}"

    # Check if modal should be shown
    if not st.session_state.get(modal_key, False):
        return False

    st.markdown("---")
    st.markdown(f"### ✏️ Edit User (ID: {user_id})")

    # Form fields
    with st.form(key=f"edit_user_form_{user_id}"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Name *",
                value=user.get('name', ''),
                max_chars=100
            )

            email = st.text_input(
                "Email *",
                value=user.get('email', ''),
                max_chars=100
            )

            role = st.selectbox(
                "Role *",
                options=["student", "instructor", "admin"],
                index=["student", "instructor", "admin"].index(user.get('role', 'student'))
            )

        with col2:
            credit_balance = st.number_input(
                "Credit Balance",
                min_value=0,
                max_value=10000,
                value=user.get('credit_balance', 0)
            )

            is_active = st.checkbox(
                "Active",
                value=user.get('is_active', True)
            )

        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submit = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if cancel:
            del st.session_state[modal_key]
            st.rerun()

        if submit:
            # Validation
            if not name.strip():
                st.error("Name is required!")
                return False

            if not email.strip() or '@' not in email:
                st.error("Valid email is required!")
                return False

            # Prepare update data
            update_data = {
                "name": name.strip(),
                "email": email.strip().lower(),
                "role": role,
                "credit_balance": credit_balance,
                "is_active": is_active
            }

            # Call API
            success, error, updated_user = update_user(token, user_id, update_data)

            if success:
                st.success(f"✅ User '{name}' updated successfully!")
                del st.session_state[modal_key]
                st.rerun()
                return True
            else:
                st.error(f"❌ Failed to update user: {error}")
                return False

    return False


def render_view_user_profile(user: Dict[str, Any]) -> None:
    """
    Render detailed view of a user profile

    Args:
        user: User data dictionary
    """
    user_id = user.get('id')
    modal_key = f"view_user_profile_{user_id}"

    # Check if modal should be shown
    if not st.session_state.get(modal_key, False):
        return

    st.markdown("---")
    st.markdown(f"### 👁️ User Profile (ID: {user_id})")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📋 Basic Information**")
        st.caption(f"**ID:** {user.get('id')}")
        st.caption(f"**Name:** {user.get('name', 'N/A')}")
        st.caption(f"**Email:** {user.get('email', 'N/A')}")
        st.caption(f"**Role:** {user.get('role', 'N/A').title()}")
        st.caption(f"**Status:** {'✅ Active' if user.get('is_active') else '❌ Inactive'}")

    with col2:
        st.markdown("**📜 Licenses**")
        licenses = user.get('licenses', [])
        if licenses:
            st.caption(f"**Total:** {len(licenses)}")
            # Group licenses by type
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
            st.caption("No licenses")

    with col3:
        st.markdown("**💰 Credits & Stats**")
        st.metric("Credit Balance", user.get('credit_balance', 0))
        # TODO: Add more stats (bookings, attendance, etc.)

    # Additional details
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📧 Contact Information**")
        st.caption(f"Email: {user.get('email', 'N/A')}")
        # TODO: Add phone, address if available

    with col2:
        st.markdown("**🎓 Specializations**")
        if licenses:
            specializations = set()
            for lic in licenses:
                spec = lic.get('specialization_type', '')
                if spec:
                    specializations.add(spec)
            for spec in sorted(specializations):
                st.caption(f"• {spec.replace('_', ' ').title()}")
        else:
            st.caption("No specializations")

    # Close button
    if st.button("❌ Close", key=f"close_profile_{user_id}"):
        del st.session_state[modal_key]
        st.rerun()


def generate_temp_password(length: int = 12) -> str:
    """
    Generate a secure temporary password

    Args:
        length: Password length (default 12)

    Returns:
        Generated password string
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def render_reset_password_dialog(user: Dict[str, Any], token: str) -> bool:
    """
    Render reset password dialog

    Args:
        user: User data dictionary
        token: Authentication token

    Returns:
        True if password was reset, False otherwise
    """
    user_id = user.get('id')
    modal_key = f"reset_password_{user_id}"

    # Check if modal should be shown
    if not st.session_state.get(modal_key, False):
        return False

    st.markdown("---")
    st.markdown(f"### 🔑 Reset Password")
    st.caption(f"User: **{user.get('name', 'Unknown')}** ({user.get('email', 'N/A')})")

    st.warning("⚠️ This will generate a new temporary password for the user.")

    # Generate password preview
    if f"temp_password_{user_id}" not in st.session_state:
        st.session_state[f"temp_password_{user_id}"] = generate_temp_password()

    temp_password = st.session_state[f"temp_password_{user_id}"]

    st.info(f"**New Temporary Password:** `{temp_password}`")
    st.caption("⚠️ Make sure to copy this password and send it to the user securely!")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("🔄 Generate New", key=f"regenerate_pw_{user_id}", use_container_width=True):
            st.session_state[f"temp_password_{user_id}"] = generate_temp_password()
            st.rerun()

    with col2:
        if st.button("✅ Confirm Reset", key=f"confirm_reset_{user_id}", type="primary", use_container_width=True):
            # Call actual password reset API
            success, error = reset_user_password(token, user_id, temp_password)

            if success:
                st.success(f"✅ Password reset successfully!")
                st.info(f"**New password:** `{temp_password}`")
                st.caption("⚠️ Make sure the user saves this password!")
            else:
                st.error(f"❌ Failed to reset password: {error}")

            # Clean up
            if f"temp_password_{user_id}" in st.session_state:
                del st.session_state[f"temp_password_{user_id}"]
            del st.session_state[modal_key]

            return success

    with col3:
        if st.button("❌ Cancel", key=f"cancel_reset_{user_id}", use_container_width=True):
            if f"temp_password_{user_id}" in st.session_state:
                del st.session_state[f"temp_password_{user_id}"]
            del st.session_state[modal_key]
            st.rerun()

    return False
