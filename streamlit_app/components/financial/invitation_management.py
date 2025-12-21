"""
Invitation Code Management Component
Handles invitation code generation, display, and deletion
"""

import streamlit as st
from datetime import datetime, timedelta
from api_helpers_invitations import get_invitation_codes, create_invitation_code, delete_invitation_code


def render_invitation_management(token: str):
    """Render the invitation code management interface"""
    st.markdown("### 🎟️ Invitation Code Management")
    st.caption("Generate and manage invitation codes for new user registrations")

    # Refresh and Create buttons
    col_refresh, col_create = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄", key="refresh_invitations"):
            st.rerun()

    with col_create:
        if st.button("➕ Generate Invitation Code", key="create_invitation_btn", use_container_width=True):
            st.session_state.show_create_invitation_modal = True
            st.rerun()

    st.divider()

    # Get invitation codes
    success, codes = get_invitation_codes(token)

    if success and codes:
        # Statistics
        total = len(codes)
        used = len([c for c in codes if c.get('is_used')])
        valid = len([c for c in codes if c.get('is_valid')])
        expired = len([c for c in codes if not c.get('is_valid') and not c.get('is_used')])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Codes", total)
        with col2:
            st.metric("✅ Used", used)
        with col3:
            st.metric("⏰ Valid", valid)
        with col4:
            st.metric("🚫 Expired", expired)

        st.divider()

        # Table header
        h1, h2, h3, h4, h5, h6 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
        with h1:
            st.markdown("**🎟️ Code**")
        with h2:
            st.markdown("**💰 Credits**")
        with h3:
            st.markdown("**📊 Status**")
        with h4:
            st.markdown("**👤 Used By**")
        with h5:
            st.markdown("**⏰ Expires**")
        with h6:
            st.markdown("**⚙️ Actions**")

        st.divider()

        # Display codes
        for code in codes:
            code_id = code.get('id')
            code_str = code.get('code')
            is_used = code.get('is_used', False)
            is_valid = code.get('is_valid', True)
            used_by_name = code.get('used_by_name')
            expires_at = code.get('expires_at')
            bonus_credits = code.get('bonus_credits', 0)

            c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])

            with c1:
                st.code(code_str, language=None)
                desc = code.get('invited_name', '')
                if desc:
                    st.caption(desc)

            with c2:
                st.markdown(f"**+{bonus_credits}**")

            with c3:
                if is_used:
                    st.success("✅ Used")
                elif not is_valid:
                    st.error("🚫 Expired")
                else:
                    st.info("⏰ Valid")

            with c4:
                if used_by_name:
                    st.markdown(f"**{used_by_name}**")
                    used_at = code.get('used_at')
                    if used_at:
                        try:
                            dt = datetime.fromisoformat(used_at.replace('Z', '+00:00'))
                            st.caption(dt.strftime('%m-%d %H:%M'))
                        except:
                            pass
                else:
                    st.caption("-")

            with c5:
                if expires_at:
                    try:
                        dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%m-%d')
                        time_str = dt.strftime('%H:%M')
                        st.markdown(f"**{date_str}**")
                        st.caption(time_str)
                    except:
                        st.caption(expires_at)
                else:
                    st.caption("Never")

            with c6:
                # Can only delete if not used
                if not is_used:
                    if st.button("🗑️ Delete", key=f"del_inv_{code_id}", use_container_width=True):
                        s, e = delete_invitation_code(token, code_id)
                        if s:
                            st.success("✅ Deleted!")
                            st.rerun()
                        else:
                            st.error(f"❌ {e}")
                else:
                    st.caption("(Used)")

            st.divider()

    elif success:
        st.info("ℹ️ No invitation codes yet. Generate one to allow new user registrations!")
    else:
        st.error("❌ Failed to load invitation codes")

    # CREATE MODAL
    if st.session_state.get('show_create_invitation_modal'):
        _render_create_invitation_modal(token)


def _render_create_invitation_modal(token: str):
    """Render the create invitation code modal (internal function)"""
    @st.dialog("Generate Invitation Code")
    def create_invitation_modal():
        with st.form("create_invitation_f", clear_on_submit=False):
            description = st.text_input(
                "Internal Description",
                value="",
                placeholder="e.g., December promo, Partner ABC code"
            )

            bonus_credits = st.number_input(
                "Bonus Credits",
                min_value=1,
                max_value=100,
                value=10,
                step=10
            )

            expires_hours = st.number_input(
                "Lejárat (óra)",
                min_value=0,
                max_value=168,
                value=24,
                step=24,
                help="0 = nincs lejárat"
            )

            notes = st.text_area(
                "Admin Notes",
                value="",
                placeholder="Internal notes"
            )

            # BUTTONS AT BOTTOM
            sub = st.form_submit_button("🎟️ Generate Code", use_container_width=True, type="primary")
            can = st.form_submit_button("Cancel", use_container_width=True)

            if can:
                st.session_state.show_create_invitation_modal = False
                st.rerun()

            if sub:
                # Create invitation code (description can be empty)
                final_description = description if description.strip() else "Generated invitation code"

                s, e, generated_code = create_invitation_code(
                    token,
                    final_description,
                    bonus_credits,
                    expires_hours if expires_hours > 0 else None,
                    notes if notes.strip() else None
                )

                if s:
                    st.success(f"✅ Invitation code generated!")
                    st.code(generated_code, language=None)
                    st.info(f"💰 {bonus_credits} bonus credits")
                    if expires_hours > 0:
                        st.warning(f"⏰ Lejár {expires_hours} óra múlva")
                    else:
                        st.info("⏰ Nincs lejárat")
                    st.session_state.show_create_invitation_modal = False
                    # Don't rerun immediately - show the code
                else:
                    st.error(f"❌ Failed: {e}")

    create_invitation_modal()
