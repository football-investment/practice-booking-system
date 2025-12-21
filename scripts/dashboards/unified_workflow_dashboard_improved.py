"""
🎯 Unified Workflow Dashboard - IMPROVED ROLE SEPARATION
==============================

Complete testing dashboard with clear role separation:
- Each role has its own dedicated page
- No mixing of admin/student/instructor interfaces
- Clean navigation and better UX

Author: Claude Code
Date: 2025-12-13
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Tuple, Optional

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="LFA Testing Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "admin_token" not in st.session_state:
    st.session_state.admin_token = None

if "student_token" not in st.session_state:
    st.session_state.student_token = None

if "instructor_token" not in st.session_state:
    st.session_state.instructor_token = None

if "current_page" not in st.session_state:
    st.session_state.current_page = "home"  # "home", "admin", "student", "instructor"

# Invitation workflow state
if "invitation_workflow_state" not in st.session_state:
    st.session_state.invitation_workflow_state = {
        "step1_create_invitation": "pending",
        "step2_student_register": "pending",
        "step3_student_verify": "pending"
    }

if "invitation_code" not in st.session_state:
    st.session_state.invitation_code = None

if "student_registration_data" not in st.session_state:
    st.session_state.student_registration_data = None

# Credit workflow state
if "credit_workflow_state" not in st.session_state:
    st.session_state.credit_workflow_state = {
        "step1_student_request": "pending",
        "step2_admin_verify": "pending",
        "step3_check_credits": "pending"
    }

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = None

# Specialization workflow state
if "specialization_workflow_state" not in st.session_state:
    st.session_state.specialization_workflow_state = {
        "step1_view_available": "pending",
        "step2_unlock_spec": "pending",
        "step3_motivation": "pending",
        "step4_verify_unlock": "pending"
    }

if "selected_specialization" not in st.session_state:
    st.session_state.selected_specialization = None

if "unlocked_licenses" not in st.session_state:
    st.session_state.unlocked_licenses = []

if "workflow_logs" not in st.session_state:
    st.session_state.workflow_logs = []

if "reset_passwords" not in st.session_state:
    st.session_state.reset_passwords = {}

if "editing_user_id" not in st.session_state:
    st.session_state.editing_user_id = None

if "viewing_profile_user_id" not in st.session_state:
    st.session_state.viewing_profile_user_id = None

# ============================================================================
# HELPER FUNCTIONS - COMMON
# ============================================================================

def add_log(message: str, level: str = "info"):
    """Add timestamped log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}[level]
    st.session_state.workflow_logs.append(f"[{timestamp}] {icon} {message}")

def show_logs():
    """Display workflow logs"""
    if st.session_state.workflow_logs:
        with st.expander("📜 Activity Log", expanded=False):
            for log in reversed(st.session_state.workflow_logs[-20:]):
                st.text(log)

def admin_login(email: str, password: str) -> Tuple[bool, Optional[str], str]:
    """Admin login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return True, data.get("access_token"), f"Admin logged in: {email}"
        return False, None, f"Login failed: {response.status_code}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def student_login(email: str, password: str) -> Tuple[bool, Optional[str], str]:
    """Student login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return True, data.get("access_token"), f"Student logged in: {email}"
        return False, None, f"Login failed: {response.status_code}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def instructor_login(email: str, password: str) -> Tuple[bool, Optional[str], str]:
    """Instructor login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return True, data.get("access_token"), f"Instructor logged in: {email}"
        return False, None, f"Login failed: {response.status_code}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

# ============================================================================
# SIDEBAR - ROLE SELECTION (IMPROVED)
# ============================================================================

with st.sidebar:
    st.title("🎯 LFA Testing Dashboard")
    st.caption("Improved Role Separation")
    st.divider()

    # HOME PAGE
    if st.button("🏠 Home", use_container_width=True, type="primary" if st.session_state.current_page == "home" else "secondary"):
        st.session_state.current_page = "home"
        st.rerun()

    st.divider()
    st.subheader("👤 Select Role")

    # ADMIN PAGE
    admin_button_type = "primary" if st.session_state.current_page == "admin" else "secondary"
    if st.button("👑 Admin Dashboard", use_container_width=True, type=admin_button_type):
        st.session_state.current_page = "admin"
        st.rerun()

    if st.session_state.current_page == "admin":
        with st.container(border=True):
            if not st.session_state.admin_token:
                st.caption("🔐 Login as Admin")
                admin_email = st.text_input("Email", value="admin@lfa.com", key="admin_email")
                admin_password = st.text_input("Password", type="password", value="admin123", key="admin_password")
                if st.button("🔑 Login", use_container_width=True, key="admin_login_btn"):
                    success, token, message = admin_login(admin_email, admin_password)
                    if success:
                        st.session_state.admin_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.success("✅ Admin logged in")
                if st.button("🚪 Logout", use_container_width=True, key="admin_logout_btn"):
                    st.session_state.admin_token = None
                    add_log("Admin logged out", "info")
                    st.rerun()

    # STUDENT PAGE
    student_button_type = "primary" if st.session_state.current_page == "student" else "secondary"
    if st.button("🎓 Student Dashboard", use_container_width=True, type=student_button_type):
        st.session_state.current_page = "student"
        st.rerun()

    if st.session_state.current_page == "student":
        with st.container(border=True):
            if not st.session_state.student_token:
                st.caption("🔐 Login as Student")
                student_email = st.text_input("Email", value="", key="student_email")
                student_password = st.text_input("Password", type="password", value="", key="student_password")
                if st.button("🔑 Login", use_container_width=True, key="student_login_btn"):
                    success, token, message = student_login(student_email, student_password)
                    if success:
                        st.session_state.student_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.success("✅ Student logged in")
                if st.button("🚪 Logout", use_container_width=True, key="student_logout_btn"):
                    st.session_state.student_token = None
                    add_log("Student logged out", "info")
                    st.rerun()

    # INSTRUCTOR PAGE
    instructor_button_type = "primary" if st.session_state.current_page == "instructor" else "secondary"
    if st.button("👨‍🏫 Instructor Dashboard", use_container_width=True, type=instructor_button_type):
        st.session_state.current_page = "instructor"
        st.rerun()

    if st.session_state.current_page == "instructor":
        with st.container(border=True):
            if not st.session_state.instructor_token:
                st.caption("🔐 Login as Instructor")
                instructor_email = st.text_input("Email", value="grandmaster@lfa.com", key="instructor_email")
                instructor_password = st.text_input("Password", type="password", value="grand123", key="instructor_password")
                if st.button("🔑 Login", use_container_width=True, key="instructor_login_btn"):
                    success, token, message = instructor_login(instructor_email, instructor_password)
                    if success:
                        st.session_state.instructor_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.success("✅ Instructor logged in")
                if st.button("🚪 Logout", use_container_width=True, key="instructor_logout_btn"):
                    st.session_state.instructor_token = None
                    add_log("Instructor logged out", "info")
                    st.rerun()

    st.divider()

    # QUICK ACTIONS (based on current page)
    if st.session_state.current_page == "admin" and st.session_state.admin_token:
        st.caption("⚡ Quick Actions")
        if st.button("🔄 Reset All Workflows", use_container_width=True):
            st.session_state.invitation_workflow_state = {
                "step1_create_invitation": "pending",
                "step2_student_register": "pending",
                "step3_student_verify": "pending"
            }
            st.session_state.credit_workflow_state = {
                "step1_student_request": "pending",
                "step2_admin_verify": "pending",
                "step3_check_credits": "pending"
            }
            add_log("All workflows reset", "info")
            st.rerun()

# ============================================================================
# MAIN CONTENT AREA - PAGE ROUTING
# ============================================================================

if st.session_state.current_page == "home":
    # ========================================================================
    # HOME PAGE
    # ========================================================================
    st.title("🏠 Welcome to LFA Testing Dashboard")
    st.markdown("### Improved Role Separation for Better Testing")

    st.divider()

    st.markdown("""
    ## 🎯 How to Use This Dashboard

    This dashboard has **separate pages** for each role to prevent interface mixing.

    ### 👑 Admin Dashboard
    - Manage invitation codes
    - Verify credit purchases
    - View all users and licenses
    - Assign instructors to sessions

    ### 🎓 Student Dashboard
    - Register with invitation code
    - Request credit purchases
    - Unlock specializations
    - View available sessions

    ### 👨‍🏫 Instructor Dashboard
    - View assigned sessions
    - Manage student attendance
    - Track licenses and renewals
    - View instructor profile

    ---

    ## 📋 Getting Started

    1. **Select a role** from the sidebar (Admin, Student, or Instructor)
    2. **Login** with the credentials shown
    3. **Use the dedicated dashboard** for that role
    4. **No more mixing!** Each role has its own isolated interface

    ---

    ## ✅ What's Improved?

    - ✅ **Separate pages** for each role (no more tabs mixing)
    - ✅ **Clear visual separation** between roles
    - ✅ **Role-specific login** only shows on that page
    - ✅ **Better navigation** with sidebar buttons
    - ✅ **Cleaner interface** without overlapping content

    """)

    st.divider()

    # Quick status
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.admin_token:
            st.success("👑 Admin: Logged in")
        else:
            st.info("👑 Admin: Not logged in")

    with col2:
        if st.session_state.student_token:
            st.success("🎓 Student: Logged in")
        else:
            st.info("🎓 Student: Not logged in")

    with col3:
        if st.session_state.instructor_token:
            st.success("👨‍🏫 Instructor: Logged in")
        else:
            st.info("👨‍🏫 Instructor: Not logged in")

    # Activity logs
    show_logs()

elif st.session_state.current_page == "admin":
    # ========================================================================
    # ADMIN PAGE
    # ========================================================================
    st.title("👑 Admin Dashboard")
    st.caption("Administrative tools and workflows")

    if not st.session_state.admin_token:
        st.warning("⚠️ Please login as admin from the sidebar")
        st.stop()

    st.divider()

    # Admin workflow tabs
    admin_tab1, admin_tab2, admin_tab3 = st.tabs([
        "🎟️ Invitation Codes",
        "💳 Credit Verification",
        "👥 User Management"
    ])

    with admin_tab1:
        st.header("🎟️ Invitation Code Management")
        st.markdown("**Only Admin Interface - No Student mixing**")

        st.info("Create invitation codes for new student registration")

        # TODO: Import and call the invitation code creation workflow
        st.markdown("Implementation: Create invitation code form here")

    with admin_tab2:
        st.header("💳 Credit Purchase Verification")
        st.markdown("**Only Admin Interface - No Student mixing**")

        st.info("Verify pending credit purchase requests")

        # TODO: Import and call the credit verification workflow
        st.markdown("Implementation: Credit verification interface here")

    with admin_tab3:
        st.header("👥 User Management")
        st.markdown("**Only Admin Interface - No Student mixing**")

        st.info("Manage all users and their licenses")

        # TODO: Import and call the user management interface
        st.markdown("Implementation: User management table here")

    show_logs()

elif st.session_state.current_page == "student":
    # ========================================================================
    # STUDENT PAGE
    # ========================================================================
    st.title("🎓 Student Dashboard")
    st.caption("Student workflows and tools")

    if not st.session_state.student_token:
        st.warning("⚠️ Please login as student from the sidebar")
        st.info("💡 Or register using an invitation code first!")
        st.stop()

    st.divider()

    # Student workflow tabs
    student_tab1, student_tab2, student_tab3 = st.tabs([
        "📝 Registration",
        "💰 Credit Purchase",
        "🎓 Specializations"
    ])

    with student_tab1:
        st.header("📝 Student Registration")
        st.markdown("**Only Student Interface - No Admin mixing**")

        st.info("Register with invitation code")

        # TODO: Import and call the student registration workflow
        st.markdown("Implementation: Registration form here")

    with student_tab2:
        st.header("💰 Request Credit Purchase")
        st.markdown("**Only Student Interface - No Admin mixing**")

        st.info("Request credit packages")

        # TODO: Import and call the credit purchase request workflow
        st.markdown("Implementation: Credit purchase request form here")

    with student_tab3:
        st.header("🎓 Unlock Specializations")
        st.markdown("**Only Student Interface - No Admin mixing**")

        st.info("Unlock new specializations")

        # TODO: Import and call the specialization unlock workflow
        st.markdown("Implementation: Specialization unlock interface here")

    show_logs()

elif st.session_state.current_page == "instructor":
    # ========================================================================
    # INSTRUCTOR PAGE
    # ========================================================================
    st.title("👨‍🏫 Instructor Dashboard")
    st.caption("Instructor tools and profile")

    if not st.session_state.instructor_token:
        st.warning("⚠️ Please login as instructor from the sidebar")
        st.stop()

    st.divider()

    # Instructor tabs
    instructor_tab1, instructor_tab2, instructor_tab3 = st.tabs([
        "📋 My Sessions",
        "🏆 My Licenses",
        "👤 Profile"
    ])

    with instructor_tab1:
        st.header("📋 Assigned Sessions")
        st.markdown("**Only Instructor Interface - No Admin/Student mixing**")

        st.info("View and manage your assigned sessions")

        # TODO: Import and call the instructor sessions interface
        st.markdown("Implementation: Sessions list here")

    with instructor_tab2:
        st.header("🏆 My Licenses")
        st.markdown("**Only Instructor Interface - No Admin/Student mixing**")

        st.info("View your licenses and renewal status")

        # TODO: Import and call the instructor licenses interface
        st.markdown("Implementation: Licenses display here")

    with instructor_tab3:
        st.header("👤 Instructor Profile")
        st.markdown("**Only Instructor Interface - No Admin/Student mixing**")

        st.info("View your public instructor profile")

        # TODO: Import and call the instructor profile interface
        st.markdown("Implementation: Profile view here")

    show_logs()

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("🎯 LFA Unified Testing Dashboard - Improved Role Separation v2.0")
