"""
LFA Education Center - Login Page
REBUILT from unified_workflow_dashboard.py patterns
WITH SESSION PERSISTENCE
"""

import streamlit as st
import requests
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY, API_BASE_URL
from api_helpers import login_user, get_current_user
from session_manager import restore_session_from_url, save_session_to_url, clear_session

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# SIMPLIFIED SESSION PERSISTENCE: Restore from URL params
if SESSION_TOKEN_KEY not in st.session_state:
    restore_session_from_url()

# CRITICAL SECURITY: Hide sidebar if not authenticated
if SESSION_TOKEN_KEY not in st.session_state:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

# Check if already logged in - AUTO REDIRECT TO DASHBOARD
if SESSION_TOKEN_KEY in st.session_state and SESSION_USER_KEY in st.session_state:
    user = st.session_state[SESSION_USER_KEY]
    role = user.get('role', 'student')

    # Auto-redirect to appropriate dashboard
    if role == 'admin':
        st.switch_page("pages/Admin_Dashboard.py")
    elif role == 'instructor':
        st.switch_page("pages/Instructor_Dashboard.py")
    else:
        # Student redirect logic: check if they have unlocked any specializations
        user_licenses = user.get('licenses', [])
        has_unlocked_spec = any(lic.get('is_unlocked') for lic in user_licenses)

        if has_unlocked_spec:
            # Has at least one unlocked specialization -> go to Student Dashboard
            st.switch_page("pages/Student_Dashboard.py")
        else:
            # No unlocked specializations -> go to Specialization Hub to unlock one
            st.switch_page("pages/Specialization_Hub.py")

# Main page content - LOGIN OR REGISTER
st.title("⚽ LFA Education Center")

# Initialize show_register state
if 'show_register' not in st.session_state:
    st.session_state.show_register = False

# Toggle between Login and Register
if not st.session_state.show_register:
    # === LOGIN FORM ===
    st.markdown("### 🔐 Login")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        email = st.text_input("Email", value="", placeholder="admin@lfa.com", key="login_email")
        password = st.text_input("Password", type="password", value="", placeholder="Enter password", key="login_password")

        if st.button("🔐 Login", use_container_width=True, type="primary"):
            if email and password:
                with st.spinner("Authenticating..."):
                    success, error, response_data = login_user(email, password)

                    if success:
                        # Extract token
                        token = response_data.get("access_token")

                        # Get user data
                        user_success, user_error, user_data = get_current_user(token)

                        if user_success:
                            # Save to session state
                            st.session_state[SESSION_TOKEN_KEY] = token
                            st.session_state[SESSION_USER_KEY] = user_data
                            st.session_state[SESSION_ROLE_KEY] = user_data.get('role', 'student')

                            # PERSIST TO URL QUERY PARAMS (survives page refresh!)
                            save_session_to_url(token, user_data)

                            st.success(f"✅ Welcome back, {user_data.get('name', 'User')}!")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to fetch user data: {user_error}")
                    else:
                        st.error(f"❌ Login failed: {error}")
            else:
                st.warning("⚠️ Please enter both email and password")

        st.markdown("---")

        if st.button("📝 Register with Invitation Code", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()

else:
    # === REGISTER FORM ===
    st.markdown("### 📝 Register with Invitation Code")
    st.info("💡 **Kapott invitation code-dal tudsz regisztrálni!**")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        reg_name = st.text_input("Your Name *", value="", placeholder="Full Name", key="reg_name")
        reg_email = st.text_input("Your Email *", value="", placeholder="student@example.com", key="reg_email")
        reg_password = st.text_input("Choose Password *", type="password", value="", placeholder="Min 6 characters", key="reg_password")

        # ✅ NEW: Date of Birth
        from datetime import date, datetime
        reg_dob = st.date_input(
            "Date of Birth *",
            value=None,
            min_value=date(1930, 1, 1),
            max_value=date.today(),
            help="Required for age verification and category assignment",
            key="reg_dob"
        )

        # ✅ NEW: Nationality
        reg_nationality = st.text_input("Nationality *", value="", placeholder="e.g., Hungarian", key="reg_nationality")

        # ✅ NEW: Gender
        reg_gender = st.selectbox(
            "Gender *",
            options=["", "Male", "Female", "Other"],
            index=0,
            key="reg_gender"
        )

        reg_code = st.text_input("Invitation Code *", value="", placeholder="Enter the code you received", key="reg_code")

        st.caption("* Required fields")

        # Validation
        all_fields_filled = (
            reg_name and reg_email and reg_password and
            reg_dob is not None and reg_nationality and reg_gender and reg_code
        )

        if st.button("📝 Register Now", use_container_width=True, type="primary"):
            if not all_fields_filled:
                st.warning("⚠️ Please fill in all required fields (marked with *)")
            elif len(reg_password) < 6:
                st.warning("⚠️ Password must be at least 6 characters")
            else:
                with st.spinner("Registering..."):
                    # Call register API
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/api/v1/auth/register-with-invitation",
                            json={
                                "email": reg_email,
                                "password": reg_password,
                                "name": reg_name,
                                "date_of_birth": reg_dob.isoformat(),  # ✅ NEW: YYYY-MM-DD format
                                "nationality": reg_nationality,  # ✅ NEW
                                "gender": reg_gender,  # ✅ NEW
                                "invitation_code": reg_code
                            },
                            timeout=10
                        )

                        if response.status_code == 200:
                            st.success("✅ Registration successful! You can now login.")
                            st.session_state.show_register = False
                            st.rerun()
                        else:
                            error_detail = response.json().get("detail", "Registration failed")
                            st.error(f"❌ {error_detail}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        st.markdown("---")

        if st.button("🔙 Back to Login", use_container_width=True):
            st.session_state.show_register = False
            st.rerun()

st.markdown("---")
st.caption("LFA Education Center - Private Club")
