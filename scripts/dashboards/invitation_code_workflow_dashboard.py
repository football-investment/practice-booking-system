#!/usr/bin/env python3
"""
Invitation Code Workflow Dashboard
Production-ready user registration flow with invitation codes

HELYES LOGIKA:
1. Admin létrehoz invitation code-ot (csak kód + credits + lejárat)
2. Student megkapja a kódot, ő adja meg: név, email, jelszó
3. Kód újrafelhasználható ha félbeszakad, de csak 1 sikeres regisztráció
"""

import streamlit as st
import requests
from typing import Tuple, Optional
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"

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
        "step1_create_invitation": "pending",
        "step2_student_register": "pending",
        "step3_student_verify": "pending"
    }

# Data storage
if "invitation_code" not in st.session_state:
    st.session_state.invitation_code = None
if "invitation_credits" not in st.session_state:
    st.session_state.invitation_credits = None
if "invitation_expires" not in st.session_state:
    st.session_state.invitation_expires = None
if "student_email" not in st.session_state:
    st.session_state.student_email = None
if "student_password" not in st.session_state:
    st.session_state.student_password = None
if "student_token" not in st.session_state:
    st.session_state.student_token = None
if "student_name" not in st.session_state:
    st.session_state.student_name = None

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
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )

        if response.status_code != 200:
            return False, "", "", ""

        token = response.json()["access_token"]

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

def create_invitation_code(admin_token: str, description: str, credits: int, expires_hours: Optional[int], notes: str) -> Tuple[bool, str, str, Optional[str]]:
    """Create invitation code via API

    Args:
        description: Internal note/description (stored in invited_name field)
        expires_hours: Hours until expiration (None = no expiration)
    """
    try:
        # Calculate expiration if specified
        expires_at = None
        if expires_hours and expires_hours > 0:
            expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()

        payload = {
            "invited_name": description,  # Using as internal description
            "invited_email": None,  # No email restriction - anyone can use!
            "bonus_credits": credits,
            "expires_at": expires_at,
            "notes": notes
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/invitation-codes",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            code = data.get("code", "")
            expires_str = f"expires in {expires_hours}h" if expires_hours else "no expiration"
            add_log(f"Invitation code created: {code} ({credits} credits, {expires_str})", "success")
            return True, code, f"Code created: {code}", expires_at
        else:
            error = response.json().get("detail", "Unknown error")
            add_log(f"Failed to create invitation code: {error}", "error")
            return False, "", f"Error: {error}", None

    except Exception as e:
        add_log(f"Exception creating invitation code: {str(e)}", "error")
        return False, "", f"Exception: {str(e)}", None

def student_register(email: str, password: str, name: str, invitation_code: str) -> Tuple[bool, str, str]:
    """Student registration with invitation code"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/register-with-invitation",
            json={
                "email": email,
                "password": password,
                "name": name,
                "invitation_code": invitation_code
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token", "")
            add_log(f"Student registered successfully: {email}", "success")
            return True, token, "Registration successful!"
        else:
            error_data = response.json()
            if "error" in error_data:
                error_msg = error_data["error"].get("message", "Unknown error")
            else:
                error_msg = error_data.get("detail", "Unknown error")
            add_log(f"Student registration failed: {error_msg}", "error")
            return False, "", f"Error: {error_msg}"

    except Exception as e:
        add_log(f"Exception during student registration: {str(e)}", "error")
        return False, "", f"Exception: {str(e)}"

def get_student_info(token: str) -> Tuple[bool, dict]:
    """Get student info using token"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {}

    except Exception as e:
        return False, {}

def get_recent_registered_users(admin_token: str, limit: int = 10) -> Tuple[bool, list]:
    """Get recently registered users via invitation codes"""
    try:
        # Get recent users ordered by creation date
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/?limit={limit}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            # Response is a UserList object with 'users' field
            users = data.get('users', []) if isinstance(data, dict) else data
            return True, users
        else:
            return False, []
    except Exception as e:
        return False, []

def reset_workflow():
    """Reset workflow state"""
    st.session_state.workflow_state = {
        "step1_create_invitation": "pending",
        "step2_student_register": "pending",
        "step3_student_verify": "pending"
    }
    st.session_state.invitation_code = None
    st.session_state.invitation_credits = None
    st.session_state.invitation_expires = None
    st.session_state.student_email = None
    st.session_state.student_password = None
    st.session_state.student_token = None
    st.session_state.student_name = None
    st.session_state.workflow_logs = []
    add_log("Workflow reset", "info")

# ============================================================================
# STREAMLIT UI
# ============================================================================

st.set_page_config(
    page_title="Invitation Code Workflow",
    page_icon="🎟️",
    layout="wide"
)

st.title("🎟️ Invitation Code Workflow Dashboard")
st.markdown("**Production-ready:** Admin creates code → Student registers → Verification")
st.info("💡 **Logika:** Admin csak kódot hoz létre. Student adja meg saját adatait (név, email, jelszó)!")

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

st.header("📋 Workflow: Invitation Code Registration")

# Create three columns for steps
col1, col2, col3 = st.columns(3)

# ============================================================================
# STEP 1: ADMIN CREATES INVITATION CODE
# ============================================================================

with col1:
    step1_state = st.session_state.workflow_state["step1_create_invitation"]
    st.subheader(f"{STEP_STATES[step1_state]} Step 1: Create Code")

    st.markdown("**Role:** ADMIN")
    st.markdown("**Action:** Generate invitation code")
    st.info("💡 Admin **CSAK** kódot hoz létre. Student adja meg később a nevét/emailjét!")

    with st.form("create_invitation_form", clear_on_submit=False):
        inv_description = st.text_input(
            "Internal Description",
            value="" if step1_state != "done" else "Promo code",
            placeholder="e.g., December promo, Partner ABC code",
            disabled=(step1_state == "done"),
            help="Csak admin látja - nem megy ki a studentnek"
        )
        inv_credits = st.number_input(
            "Bonus Credits",
            min_value=1,
            max_value=100,
            value=10 if step1_state != "done" else st.session_state.invitation_credits or 10,
            disabled=(step1_state == "done")
        )
        inv_expiry_hours = st.number_input(
            "Lejárat (óra)",
            min_value=0,
            max_value=168,
            value=24,
            disabled=(step1_state == "done"),
            help="0 = nincs lejárat"
        )
        inv_notes = st.text_area(
            "Admin Notes",
            value="",
            placeholder="Internal notes",
            disabled=(step1_state == "done")
        )

        submit_button = st.form_submit_button(
            "🎟️ Create Invitation Code",
            disabled=(step1_state == "done"),
            use_container_width=True
        )

        if submit_button and step1_state != "done":
            if inv_description and inv_credits:
                add_log(f"Admin creating invitation code: {inv_description}", "info")
                success, code, message, expires = create_invitation_code(
                    st.session_state.admin_token,
                    inv_description,
                    inv_credits,
                    inv_expiry_hours if inv_expiry_hours > 0 else None,
                    inv_notes
                )

                if success:
                    st.session_state.workflow_state["step1_create_invitation"] = "done"
                    st.session_state.workflow_state["step2_student_register"] = "active"
                    st.session_state.invitation_code = code
                    st.session_state.invitation_credits = inv_credits
                    st.session_state.invitation_expires = expires
                    st.success(message)
                    st.rerun()
                else:
                    st.session_state.workflow_state["step1_create_invitation"] = "error"
                    st.error(message)
            else:
                st.warning("Please fill in description and credits")

    if step1_state == "done":
        st.success(f"✅ Code created:")
        st.code(st.session_state.invitation_code, language=None)
        st.info(f"💰 {st.session_state.invitation_credits} bonus credits")
        if st.session_state.invitation_expires:
            st.warning(f"⏰ Lejár: {st.session_state.invitation_expires[:19]}")
        else:
            st.info("⏰ Nincs lejárat")
    elif step1_state == "error":
        st.error("❌ Code creation failed. Check logs below.")
    elif step1_state == "pending":
        st.info("⏸️ Waiting for admin to create invitation code...")

# ============================================================================
# STEP 2: STUDENT REGISTRATION
# ============================================================================

with col2:
    step2_state = st.session_state.workflow_state["step2_student_register"]
    st.subheader(f"{STEP_STATES[step2_state]} Step 2: Student Register")

    st.markdown("**Role:** STUDENT")
    st.markdown("**Action:** Register with code")
    st.info("💡 Student adja meg: **saját név, email, jelszó** + invitation code")

    step1_complete = st.session_state.workflow_state["step1_create_invitation"] == "done"

    if not step1_complete:
        st.warning("⏸️ Waiting for Step 1 to complete...")
        st.info("Admin must create invitation code first.")
    else:
        with st.form("student_register_form", clear_on_submit=False):
            st.success(f"**Kapott kód:** `{st.session_state.invitation_code}`")

            reg_name = st.text_input(
                "Saját Neved (Student)",
                value="" if step2_state != "done" else st.session_state.student_name,
                placeholder="Teljes név",
                disabled=(step2_state == "done"),
                help="Student maga adja meg!"
            )
            reg_email = st.text_input(
                "Saját Email címed (Student)",
                value="" if step2_state != "done" else st.session_state.student_email,
                placeholder="student@example.com",
                disabled=(step2_state == "done"),
                help="Student maga adja meg!"
            )
            reg_password = st.text_input(
                "Válassz Jelszót (Student)",
                type="password",
                value="" if step2_state != "done" else st.session_state.student_password,
                placeholder="Min 6 karakter",
                disabled=(step2_state == "done"),
                help="Student maga választja!"
            )
            reg_code = st.text_input(
                "Invitation Code",
                value=st.session_state.invitation_code or "",
                disabled=(step2_state == "done"),
                help="Az adminról kapott kód"
            )

            register_button = st.form_submit_button(
                "📝 Register Now",
                disabled=(step2_state == "done" or not step1_complete),
                use_container_width=True
            )

            if register_button and step2_state != "done" and step1_complete:
                if reg_email and reg_name and reg_password and reg_code:
                    if len(reg_password) < 6:
                        st.warning("Password must be at least 6 characters")
                    else:
                        add_log(f"Student registering: {reg_name} ({reg_email})", "info")
                        success, token, message = student_register(
                            reg_email, reg_password, reg_name, reg_code
                        )

                        if success:
                            st.session_state.workflow_state["step2_student_register"] = "done"
                            st.session_state.workflow_state["step3_student_verify"] = "active"
                            st.session_state.student_token = token
                            st.session_state.student_email = reg_email
                            st.session_state.student_password = reg_password
                            st.session_state.student_name = reg_name
                            st.success(message)
                            st.rerun()
                        else:
                            st.session_state.workflow_state["step2_student_register"] = "error"
                            st.error(message)
                else:
                    st.warning("Please fill in all fields")

        if step2_state == "done":
            st.success(f"✅ Student registered!")
            st.info(f"👤 Név: **{st.session_state.student_name}**")
            st.info(f"📧 Email: **{st.session_state.student_email}**")
        elif step2_state == "error":
            st.error("❌ Registration failed. Check logs below.")
            st.warning("💡 Kód újrafelhasználható! Próbáld újra vagy használj másik emailt.")
        elif step2_state == "active":
            st.info("🔵 Ready! Fill form above.")

# ============================================================================
# STEP 3: VERIFICATION
# ============================================================================

with col3:
    step3_state = st.session_state.workflow_state["step3_student_verify"]
    st.subheader(f"{STEP_STATES[step3_state]} Step 3: Verify")

    st.markdown("**Role:** SYSTEM")
    st.markdown("**Action:** Verify registration")

    step2_complete = st.session_state.workflow_state["step2_student_register"] == "done"

    if not step2_complete:
        st.warning("⏸️ Waiting for Step 2...")
        st.info("Student must register first.")
    else:
        if st.button("🔍 Verify Registration", disabled=(step3_state == "done"), use_container_width=True):
            if st.session_state.student_token:
                success, student_data = get_student_info(st.session_state.student_token)

                if success:
                    st.session_state.workflow_state["step3_student_verify"] = "done"
                    add_log("Registration verified successfully", "success")
                    st.success("✅ Verification successful!")

                    with st.expander("📊 Student Account Details", expanded=True):
                        st.json({
                            "email": student_data.get("email"),
                            "name": student_data.get("name"),
                            "role": student_data.get("role"),
                            "credit_balance": student_data.get("credit_balance"),
                            "is_active": student_data.get("is_active")
                        })
                    st.rerun()
                else:
                    st.session_state.workflow_state["step3_student_verify"] = "error"
                    st.error("❌ Verification failed")
                    add_log("Failed to verify student info", "error")

        if step3_state == "done":
            st.success("✅ Registration verified!")
            st.info("Student account active")
        elif step3_state == "error":
            st.error("❌ Verification failed")
        elif step3_state == "active":
            st.info("🔵 Click button to verify")

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

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.metric("Step 1: Create Code", STEP_STATES[st.session_state.workflow_state["step1_create_invitation"]])

with status_col2:
    st.metric("Step 2: Student Register", STEP_STATES[st.session_state.workflow_state["step2_student_register"]])

with status_col3:
    st.metric("Step 3: Verification", STEP_STATES[st.session_state.workflow_state["step3_student_verify"]])

# Check if workflow complete
if (st.session_state.workflow_state["step1_create_invitation"] == "done" and
    st.session_state.workflow_state["step2_student_register"] == "done" and
    st.session_state.workflow_state["step3_student_verify"] == "done"):
    st.success("🎉 **Complete Invitation Code Workflow Successful!**")
    st.balloons()
    st.info("💡 Click 'Reset Workflow' in sidebar to test again.")

# ============================================================================
# KEY FEATURES
# ============================================================================

st.divider()
st.header("✨ Key Features")

feat_col1, feat_col2, feat_col3 = st.columns(3)

with feat_col1:
    st.success("**✅ Kód újrafelhasználható**")
    st.caption("Ha regisztráció félbeszakad, ugyanaz a kód újra használható")

with feat_col2:
    st.info("**⏰ Időkorlát**")
    st.caption("Admin beállíthatja a lejárati időt (órában)")

with feat_col3:
    st.warning("**🔒 Egy sikeres reg**")
    st.caption("Sikeres regisztráció után a kód már nem használható")

# ============================================================================
# 📋 RECENTLY REGISTERED USERS LIST
# ============================================================================

st.divider()
st.subheader("📋 Recently Registered Users")

# Only show if admin is logged in
if st.session_state.admin_token:
    col_refresh, col_limit = st.columns([3, 1])

    with col_limit:
        user_limit = st.selectbox("Limit", [5, 10, 20, 50], index=1, key="user_limit")

    with col_refresh:
        if st.button("🔄 Refresh User List", use_container_width=True):
            st.session_state.force_refresh = True

    # Fetch recent users
    success, users = get_recent_registered_users(st.session_state.admin_token, limit=user_limit)

    if success and users:
        st.success(f"✅ Found {len(users)} users")

        # Create a table-like display
        for user in users:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

                with col1:
                    # User name and email
                    st.markdown(f"**👤 {user.get('name', 'N/A')}**")
                    st.caption(f"📧 {user.get('email', 'N/A')}")

                with col2:
                    # Role and status
                    role = user.get('role', 'N/A')
                    role_emoji = "🎓" if role == "STUDENT" else "👨‍🏫" if role == "INSTRUCTOR" else "👑"
                    st.markdown(f"{role_emoji} **{role}**")

                    is_active = user.get('is_active', False)
                    status_color = "🟢" if is_active else "🔴"
                    status_text = "Active" if is_active else "Inactive"
                    st.caption(f"{status_color} {status_text}")

                with col3:
                    # Credit balance
                    credit_balance = user.get('credit_balance', 0)
                    st.metric("💰 Credits", credit_balance)

                with col4:
                    # User ID and created date
                    st.caption(f"ID: {user.get('id', 'N/A')}")
                    created_at = user.get('created_at', 'N/A')
                    if created_at != 'N/A':
                        try:
                            # Parse and format date
                            from datetime import datetime
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            st.caption(f"📅 {dt.strftime('%Y-%m-%d %H:%M')}")
                        except:
                            st.caption(f"📅 {created_at[:10]}")
                    else:
                        st.caption("📅 N/A")

                st.divider()

        # Show detailed JSON in expander
        with st.expander("🔍 View Raw User Data (JSON)"):
            st.json(users)

    elif success and not users:
        st.info("ℹ️ No users found")
    else:
        st.error("❌ Failed to fetch users. Please check your admin token or backend connection.")
else:
    st.warning("⚠️ Please log in as admin to view registered users")
