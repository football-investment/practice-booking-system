"""
My Profile - Student Central Profile Display
Shows the 3-column READ-ONLY profile widget
"""

import streamlit as st
from datetime import datetime, date
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SPECIALIZATIONS

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - My Profile",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Authentication check
if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("Not authenticated. Please login first.")
    st.stop()

# Get token
token = st.session_state[SESSION_TOKEN_KEY]

# ✅ CRITICAL FIX: Fetch fresh data ONLY if not in middle of form submission
# Avoid refreshing during form edit which would lose form state
from api_helpers_general import get_current_user

# Only fetch fresh data if modal is NOT open (to preserve form state during editing)
if not st.session_state.get('show_edit_profile_modal', False):
    success, error, user = get_current_user(token)
    if not success:
        st.error(f"Failed to load profile: {error}")
        st.session_state.clear()
        st.switch_page("🏠_Home.py")
        st.stop()

    # Update session state with fresh data
    st.session_state[SESSION_USER_KEY] = user
else:
    # Modal is open - use cached session state to preserve form
    user = st.session_state[SESSION_USER_KEY]

# Check student role
if user.get('role') != 'student':
    st.error("Access denied. Student role required.")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Student')}!")
    st.caption(f"Role: **Student**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    # Credits display
    st.markdown("**💰 My Credits**")
    st.metric("Credit Balance", user.get('credit_balance', 0))

    st.markdown("---")

    # Logout and Refresh buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True, help="Reload profile data"):
            st.rerun()
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("🏠_Home.py")

# Header
st.title("👤 My Profile")
st.caption("Your personal information and unlocked specializations")

st.divider()

# ============================================================================
# CENTRAL PROFILE WIDGET (3-COLUMN LAYOUT - READ-ONLY)
# ============================================================================

# Calculate age from date of birth
age = None
dob = user.get('date_of_birth')
birth_date = None
if dob:
    try:
        if isinstance(dob, str):
            birth_date = datetime.fromisoformat(dob.replace('Z', '+00:00')).date()
        else:
            birth_date = dob
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    except:
        age = None
        birth_date = None

# Get credit balance
credit_balance = user.get('credit_balance', 0)

# Get user licenses
user_licenses = user.get('licenses', [])
unlocked_licenses = [lic for lic in user_licenses if lic.get('is_unlocked')]
locked_licenses = [lic for lic in user_licenses if not lic.get('is_unlocked')]

# 3-COLUMN PROFILE WIDGET
col1, col2, col3 = st.columns([2, 2, 2])

# ============================================================================
# COLUMN 1: BASIC INFORMATION
# ============================================================================
with col1:
    st.markdown("**📋 Basic Information**")
    st.caption(f"**Name:** {user.get('name', 'N/A')}")
    st.caption(f"**Email:** {user.get('email', 'N/A')}")

    if birth_date:
        st.caption(f"**Birth Date:** {birth_date.strftime('%Y-%m-%d')}")
    else:
        st.caption("**Birth Date:** Not set")

    if age is not None:
        st.caption(f"**Age:** {age} years old")
    else:
        st.caption("**Age:** N/A")

# ============================================================================
# COLUMN 2: UNLOCKED LICENSES/SPECIALIZATIONS
# ============================================================================
with col2:
    st.markdown("**🎓 Specializations**")

    if unlocked_licenses:
        st.caption("**✅ Unlocked:**")
        for lic in unlocked_licenses:
            spec_type = lic.get('specialization_type', 'Unknown')
            spec_name = SPECIALIZATIONS.get(spec_type, spec_type)
            st.caption(f"• {spec_name}")
    else:
        st.caption("**No specializations unlocked yet**")

    if locked_licenses:
        st.caption(f"**🔒 Locked:** {len(locked_licenses)} specializations")

# ============================================================================
# COLUMN 3: CREDITS & ACTIONS
# ============================================================================
with col3:
    st.markdown("**💰 Credits & Actions**")

    st.metric("Credit Balance", f"{credit_balance} credits")

    st.markdown("---")

    # Action buttons
    if st.button("✏️ Edit Profile", use_container_width=True, key="edit_profile_btn"):
        st.warning("🔍 DEBUG: Edit Profile button clicked! Opening modal...")
        st.session_state['show_edit_profile_modal'] = True
        st.rerun()

    if st.button("💳 Purchase Credits", use_container_width=True, key="purchase_credits_btn"):
        st.switch_page("pages/My_Credits.py")

st.divider()

# ============================================================================
# EDIT PROFILE MODAL (INLINE)
# ============================================================================
if st.session_state.get('show_edit_profile_modal', False):
    st.markdown("---")
    st.markdown("### ✏️ Edit My Profile")
    st.caption("Update your personal information")

    # ✅ DATE PICKER OUTSIDE FORM (fixes calendar picker bug)
    # This pattern ensures calendar clicks properly register
    # (Pattern proven in: player_tournament_generator.py)
    dob_value = None
    if user.get('date_of_birth'):
        try:
            if isinstance(user.get('date_of_birth'), str):
                dob_value = datetime.fromisoformat(user.get('date_of_birth').replace('Z', '+00:00')).date()
            else:
                dob_value = user.get('date_of_birth')
        except:
            pass

    date_of_birth = st.date_input(
        "Date of Birth",
        value=dob_value,
        min_value=date(1930, 1, 1),
        max_value=date.today(),
        key="profile_edit_dob",
        format="YYYY-MM-DD"
    )

    # NOW open form with other fields
    with st.form("edit_profile_form"):
        name = st.text_input(
            "Full Name *",
            value=user.get('name', ''),
            help="Your full legal name"
        )

        email = st.text_input(
            "Email *",
            value=user.get('email', ''),
            help="Your email address",
            disabled=True  # Email cannot be changed
        )

        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submit = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if cancel:
            st.session_state['show_edit_profile_modal'] = False
            st.rerun()

        if submit:
            # Validation
            if not name.strip():
                st.error("Name is required!")
            else:
                # ✅ Validate minimum age (5 years old)
                if date_of_birth:
                    from datetime import date as date_type
                    today = date_type.today()
                    age = today.year - date_of_birth.year - (
                        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
                    )

                    if age < 5:
                        st.error(f"❌ Minimum age requirement is 5 years. Current age: {age} years.")
                        st.stop()

                # Import update function
                from api_helpers_general import update_user

                # Prepare update data (✅ Convert date to datetime string with time component)
                update_data = {
                    "name": name.strip(),
                    "date_of_birth": f"{date_of_birth.isoformat()}T00:00:00" if date_of_birth else None
                }

                # Call API
                success, error, updated_user = update_user(token, user.get('id'), update_data)

                if success:
                    st.success(f"✅ Profile updated successfully!")
                    # Update session state with new user data
                    st.session_state[SESSION_USER_KEY] = updated_user
                    st.session_state['show_edit_profile_modal'] = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to update profile: {error}")

    st.divider()

# ============================================================================
# FOOTER NAVIGATION
# ============================================================================
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    if st.button("🏠 Back to Hub", use_container_width=True):
        # Navigate to appropriate dashboard based on specialization
        specialization = user.get('specialization')
        if specialization == 'LFA_FOOTBALL_PLAYER':
            st.switch_page("pages/LFA_Player_Dashboard.py")
        elif specialization in ['LFA_COACH', 'LFA_INTERNSHIP']:
            st.switch_page("pages/Specialization_Hub.py")
        else:
            # Fallback to generic hub
            st.switch_page("pages/Specialization_Hub.py")

with footer_col2:
    if st.button("👤 Profile", disabled=True, use_container_width=True):
        pass  # Already on profile page

with footer_col3:
    if st.button("💳 Credits", use_container_width=True):
        st.switch_page("pages/My_Credits.py")
