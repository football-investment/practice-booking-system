#!/usr/bin/env python3
"""
Interactive Workflow Testing Dashboard
Step-by-step testing with Student/Instructor action buttons
"""

import streamlit as st
import requests
from typing import Tuple, Optional
from datetime import datetime
import psycopg2
import bcrypt

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"
DB_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Admin credentials reference (for documentation)
ADMIN_EMAIL = "admin@lfa.com"

# Workflow step states
STEP_STATES = {
    "pending": "⏸️",
    "active": "🔵",
    "done": "✅",
    "error": "❌"
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "admin_token" not in st.session_state:
    st.session_state.admin_token = None
if "admin_email" not in st.session_state:
    st.session_state.admin_email = None
if "admin_role" not in st.session_state:
    st.session_state.admin_role = None

# Workflow state
if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = {
        "step1_create_user": "pending",
        "step2_student_login": "pending"
    }

# Data storage
if "created_user_email" not in st.session_state:
    st.session_state.created_user_email = None
if "created_user_password" not in st.session_state:
    st.session_state.created_user_password = None
if "student_token" not in st.session_state:
    st.session_state.student_token = None

# Logs
if "workflow_logs" not in st.session_state:
    st.session_state.workflow_logs = []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_log(message: str, level: str = "info"):
    """Add log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = {
        "info": "ℹ️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️"
    }.get(level, "ℹ️")

    log_entry = f"[{timestamp}] {icon} {message}"
    st.session_state.workflow_logs.append(log_entry)

def admin_login(email: str, password: str) -> Tuple[bool, str, str, str]:
    """Admin login with role verification"""
    try:
        # Authenticate
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )

        if response.status_code != 200:
            return False, "", "", ""

        token = response.json()["access_token"]

        # Get user info and role
        user_resp = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if user_resp.status_code != 200:
            return False, "", "", ""

        user_data = user_resp.json()
        return True, token, user_data.get('email', ''), user_data.get('role', '')

    except Exception as e:
        return False, "", "", ""

def create_student_user(admin_token: str, email: str, password: str, name: str) -> Tuple[bool, str]:
    """Create new student user directly in database"""
    try:
        # Hash password using bcrypt directly (same as backend)
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=10)
        hashed = bcrypt.hashpw(password_bytes, salt)
        hashed_password = hashed.decode('utf-8')

        # Connect to database
        conn = psycopg2.connect(DB_CONN_STRING)
        cur = conn.cursor()

        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            add_log(f"User already exists: {email}", "error")
            return False, f"User {email} already exists!"

        # Insert new user with all required NOT NULL fields
        cur.execute("""
            INSERT INTO users (
                email, password_hash, name, role, is_active, date_of_birth,
                payment_verified, nda_accepted, parental_consent
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (email, hashed_password, name, "STUDENT", True, "2000-01-01", False, False, False))

        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        add_log(f"User created successfully: {email} (ID: {user_id})", "success")
        return True, f"User {email} created successfully!"

    except Exception as e:
        add_log(f"Exception creating user: {str(e)}", "error")
        return False, f"Exception: {str(e)}"

def student_login(email: str, password: str) -> Tuple[bool, str, str]:
    """Student login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )

        if response.status_code == 200:
            token = response.json()["access_token"]
            add_log(f"Student logged in successfully: {email}", "success")
            return True, token, "Login successful!"
        else:
            error_msg = response.json().get("detail", "Unknown error")
            add_log(f"Student login failed: {error_msg}", "error")
            return False, "", f"Error: {error_msg}"

    except Exception as e:
        add_log(f"Exception during student login: {str(e)}", "error")
        return False, "", f"Exception: {str(e)}"

def reset_workflow():
    """Reset workflow state"""
    st.session_state.workflow_state = {
        "step1_create_user": "pending",
        "step2_student_login": "pending"
    }
    st.session_state.created_user_email = None
    st.session_state.created_user_password = None
    st.session_state.student_token = None
    st.session_state.workflow_logs = []
    add_log("Workflow reset", "info")

# ============================================================================
# STREAMLIT UI
# ============================================================================

st.set_page_config(
    page_title="Interactive Workflow Testing",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 Interactive Workflow Testing Dashboard")
st.markdown("**Step-by-step testing with role-based action buttons**")

# ============================================================================
# SIDEBAR - ADMIN AUTHENTICATION
# ============================================================================

with st.sidebar:
    st.header("🔐 Admin Login")

    if not st.session_state.admin_token:
        st.warning("⚠️ ADMIN ONLY: This dashboard requires administrator credentials.")

        email = st.text_input("Email", value="", placeholder="admin@lfa.com", key="admin_email_input")
        password = st.text_input("Password", type="password", value="", placeholder="Enter password", key="admin_password_input")

        if st.button("🔐 Login", use_container_width=True):
            if email and password:
                with st.spinner("Authenticating..."):
                    success, token, user_email, user_role = admin_login(email, password)

                    if success:
                        # Verify admin role (case-insensitive)
                        if user_role.upper() != "ADMIN":
                            st.error("🚫 ACCESS DENIED: This dashboard is for administrators only.")
                            st.error(f"Your role: {user_role}")
                        else:
                            st.session_state.admin_token = token
                            st.session_state.admin_email = user_email
                            st.session_state.admin_role = user_role
                            add_log(f"Admin logged in: {user_email}", "success")
                            st.rerun()
                    else:
                        st.error("❌ Login failed. Please check credentials.")
            else:
                st.warning("Please enter both email and password")
    else:
        st.success(f"✅ Logged in as: **{st.session_state.admin_email}**")
        st.info(f"Role: **{st.session_state.admin_role}**")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.admin_token = None
            st.session_state.admin_email = None
            st.session_state.admin_role = None
            reset_workflow()
            st.rerun()

    st.divider()

    # Reset workflow button
    if st.session_state.admin_token:
        st.subheader("🔄 Workflow Control")
        if st.button("🔄 Reset Workflow", use_container_width=True):
            reset_workflow()
            st.success("Workflow reset!")
            st.rerun()

# ============================================================================
# MAIN CONTENT
# ============================================================================

if not st.session_state.admin_token:
    st.warning("⚠️ Please login from the sidebar to start testing")
    st.info("**ADMIN ACCESS ONLY** - This dashboard requires administrator credentials.")
    st.stop()

# Double-layer protection: Verify admin role
if st.session_state.admin_role.upper() != "ADMIN":
    st.error("🚫 ACCESS DENIED: This dashboard is for administrators only.")
    st.error(f"Your role: {st.session_state.admin_role}")
    st.session_state.admin_token = None
    st.session_state.admin_email = None
    st.session_state.admin_role = None
    st.stop()

# ============================================================================
# WORKFLOW STEPS
# ============================================================================

st.header("📋 Workflow: User Creation & First Login")
st.markdown("**Phase 1:** Admin creates new student user, then student logs in for the first time")

# Create two columns for steps
col1, col2 = st.columns(2)

# ============================================================================
# STEP 1: ADMIN CREATES NEW USER
# ============================================================================

with col1:
    step1_state = st.session_state.workflow_state["step1_create_user"]
    st.subheader(f"{STEP_STATES[step1_state]} Step 1: Admin Creates User")

    st.markdown("**Role:** ADMIN")
    st.markdown("**Action:** Create new student user")

    # Always show the form, but disable it if step is done
    with st.form("create_user_form", clear_on_submit=False):
        new_email = st.text_input(
            "Student Email",
            value="" if step1_state != "done" else st.session_state.created_user_email,
            placeholder="student@example.com",
            disabled=(step1_state == "done")
        )
        new_password = st.text_input(
            "Password",
            type="password",
            value="" if step1_state != "done" else st.session_state.created_user_password,
            placeholder="Enter password",
            disabled=(step1_state == "done")
        )
        new_name = st.text_input(
            "Full Name",
            value="" if step1_state != "done" else f"Test Student",
            placeholder="John Doe",
            disabled=(step1_state == "done")
        )

        submit_button = st.form_submit_button(
            "👤 Create Student User",
            disabled=(step1_state == "done"),
            use_container_width=True
        )

        if submit_button and step1_state != "done":
            if new_email and new_password and new_name:
                add_log(f"Admin creating user: {new_email}", "info")
                success, message = create_student_user(
                    st.session_state.admin_token,
                    new_email,
                    new_password,
                    new_name
                )

                if success:
                    st.session_state.workflow_state["step1_create_user"] = "done"
                    st.session_state.workflow_state["step2_student_login"] = "active"
                    st.session_state.created_user_email = new_email
                    st.session_state.created_user_password = new_password
                    st.success(message)
                    st.rerun()
                else:
                    st.session_state.workflow_state["step1_create_user"] = "error"
                    st.error(message)
            else:
                st.warning("Please fill in all fields")

    # Show status
    if step1_state == "done":
        st.success(f"✅ User created: **{st.session_state.created_user_email}**")
    elif step1_state == "error":
        st.error("❌ User creation failed. Check logs below.")
    elif step1_state == "pending":
        st.info("⏸️ Waiting for admin to create user...")

# ============================================================================
# STEP 2: STUDENT FIRST LOGIN
# ============================================================================

with col2:
    step2_state = st.session_state.workflow_state["step2_student_login"]
    st.subheader(f"{STEP_STATES[step2_state]} Step 2: Student First Login")

    st.markdown("**Role:** STUDENT")
    st.markdown("**Action:** Login with new credentials")

    # Check if Step 1 is complete
    step1_complete = st.session_state.workflow_state["step1_create_user"] == "done"

    if not step1_complete:
        st.warning("⏸️ Waiting for Step 1 to complete...")
        st.info("Admin must create user first before student can login.")
    else:
        with st.form("student_login_form", clear_on_submit=False):
            login_email = st.text_input(
                "Email",
                value=st.session_state.created_user_email or "",
                disabled=(step2_state == "done")
            )
            login_password = st.text_input(
                "Password",
                type="password",
                value=st.session_state.created_user_password or "",
                disabled=(step2_state == "done")
            )

            login_button = st.form_submit_button(
                "🔐 Student Login",
                disabled=(step2_state == "done" or not step1_complete),
                use_container_width=True
            )

            if login_button and step2_state != "done" and step1_complete:
                if login_email and login_password:
                    add_log(f"Student attempting login: {login_email}", "info")
                    success, token, message = student_login(login_email, login_password)

                    if success:
                        st.session_state.workflow_state["step2_student_login"] = "done"
                        st.session_state.student_token = token
                        st.success(message)
                        st.rerun()
                    else:
                        st.session_state.workflow_state["step2_student_login"] = "error"
                        st.error(message)
                else:
                    st.warning("Please enter email and password")

        # Show status
        if step2_state == "done":
            st.success(f"✅ Student logged in successfully!")
            st.info(f"Email: **{st.session_state.created_user_email}**")
        elif step2_state == "error":
            st.error("❌ Login failed. Check logs below.")
        elif step2_state == "active":
            st.info("🔵 Ready to login. Click button above.")

# ============================================================================
# WORKFLOW LOGS
# ============================================================================

st.divider()
st.header("📋 Workflow Logs")

if st.session_state.workflow_logs:
    log_container = st.container()
    with log_container:
        for log in st.session_state.workflow_logs:
            if "✅" in log:
                st.success(log)
            elif "❌" in log:
                st.error(log)
            elif "⚠️" in log:
                st.warning(log)
            else:
                st.info(log)
else:
    st.info("No logs yet. Start the workflow above.")

# ============================================================================
# WORKFLOW STATUS SUMMARY
# ============================================================================

st.divider()
st.header("📊 Workflow Status")

status_col1, status_col2 = st.columns(2)

with status_col1:
    st.metric("Step 1: Create User", STEP_STATES[st.session_state.workflow_state["step1_create_user"]])

with status_col2:
    st.metric("Step 2: Student Login", STEP_STATES[st.session_state.workflow_state["step2_student_login"]])

# Check if workflow complete
if (st.session_state.workflow_state["step1_create_user"] == "done" and
    st.session_state.workflow_state["step2_student_login"] == "done"):
    st.success("🎉 **Workflow Phase 1 Complete!** Ready to proceed to next steps.")
    st.info("💡 Click 'Reset Workflow' in sidebar to test again, or wait for next phase implementation.")
