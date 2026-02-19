"""
🎯 Unified Workflow Dashboard
==============================

Complete testing dashboard for:
1. 🎟️ Invitation Code Registration Workflow
2. 💳 Credit Purchase Workflow

Author: Claude Code
Date: 2025-12-11
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Tuple, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

    from datetime import datetime

                                                        from datetime import datetime as dt
                                    import time
                    from collections import defaultdict
                            import secrets
                            import string
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

if "active_workflow" not in st.session_state:
    st.session_state.active_workflow = "invitation"  # "invitation", "credit", "specialization", "admin", or "instructor"

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

def admin_login(email: str, password: str) -> Tuple[bool, Optional[str], str]:
    """Admin login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            return True, token, f"Admin logged in: {email}"
        else:
            # Get detailed error message
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", f"HTTP {response.status_code}")
            except:
                error_detail = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No details'}"
            return False, None, f"Login failed: {error_detail}"

    except Exception as e:
        return False, None, f"Login error: {str(e)}"

def student_login(email: str, password: str) -> Tuple[bool, Optional[str], str]:
    """Student login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            return True, token, f"Student logged in: {email}"
        else:
            # Get detailed error message
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", f"HTTP {response.status_code}")
            except:
                error_detail = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No details'}"
            return False, None, f"Login failed: {error_detail}"

    except Exception as e:
        return False, None, f"Login error: {str(e)}"

def instructor_login(email: str, password: str) -> Tuple[bool, Optional[str], str]:
    """Instructor login"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            return True, token, f"Instructor logged in: {email}"
        else:
            # Get detailed error message
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", f"HTTP {response.status_code}")
            except:
                error_detail = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No details'}"
            return False, None, f"Login failed: {error_detail}"

    except Exception as e:
        return False, None, f"Login error: {str(e)}"

def get_user_info(token: str) -> Tuple[bool, dict]:
    """Get current user info"""
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
    """Get recently registered users"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/?limit={limit}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', []) if isinstance(data, dict) else data
            return True, users
        else:
            return False, []
    except Exception as e:
        return False, []

def reset_user_password(admin_token: str, user_id: int, new_password: str) -> Tuple[bool, str]:
    """Admin resets user password"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/users/{user_id}/reset-password",
            json={"new_password": new_password},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        if response.status_code == 200:
            return True, "Password reset successfully"
        else:
            # Get detailed error message
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", f"HTTP {response.status_code}")
            except:
                error_detail = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No details'}"
            return False, f"Failed: {error_detail}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_user_profile(admin_token: str, user_id: int, updates: dict) -> Tuple[bool, str]:
    """Admin updates user profile fields"""
    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/users/{user_id}",
            json=updates,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        if response.status_code == 200:
            return True, "User profile updated successfully"
        else:
            error_detail = response.json().get("detail", "Unknown error") if response.text else f"HTTP {response.status_code}"
            return False, f"Failed: {error_detail}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_credit_transactions(token: str, limit: int = 50, offset: int = 0) -> Tuple[bool, dict]:
    """Get current user's credit transaction history"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me/credit-transactions",
            params={"limit": limit, "offset": offset},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {}
    except Exception as e:
        return False, {}

def display_credit_transactions(token: str, credit_balance: int):
    """Display credit transaction history in an expander"""
    st.divider()

    with st.expander("💰 Credit Transaction History", expanded=False):
        st.markdown(f"**Current Balance:** {credit_balance} credits")

        # Fetch transactions
        success, data = get_credit_transactions(token, limit=20)

        if success and data.get('transactions'):
            transactions = data['transactions']
            total_count = data.get('total_count', 0)

            st.caption(f"Showing {len(transactions)} of {total_count} total transactions")

            # Transaction type emoji mapping
            type_emoji = {
                "PURCHASE": "🛒",
                "ENROLLMENT": "📝",
                "REFUND": "↩️",
                "ADMIN_ADJUSTMENT": "⚙️",
                "EXPIRATION": "⏰",
                "LICENSE_RENEWAL": "🔄"
            }

            # Display transactions
            for tx in transactions:
                tx_type = tx.get('transaction_type', 'UNKNOWN')
                amount = tx.get('amount', 0)
                balance_after = tx.get('balance_after', 0)
                description = tx.get('description', 'No description')
                created_at = tx.get('created_at', '')

                # Format date
                date_str = created_at[:10] if created_at else 'N/A'

                # Color based on amount
                amount_color = "🟢" if amount > 0 else "🔴"
                amount_str = f"+{amount}" if amount > 0 else str(amount)

                # Display transaction
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    emoji = type_emoji.get(tx_type, "📋")
                    st.markdown(f"{emoji} **{description}**")
                    st.caption(f"📅 {date_str}")
                with col2:
                    st.markdown(f"{amount_color} **{amount_str}** credits")
                with col3:
                    st.caption(f"Balance: {balance_after}")

                st.divider()
        else:
            st.info("No transactions found")

# ============================================================================
# HELPER FUNCTIONS - INVITATION WORKFLOW
# ============================================================================

def create_invitation_code(admin_token: str, description: str, credits: int, hours: int, notes: str) -> Tuple[bool, dict]:
    """Admin creates invitation code"""
    try:
        expires_at = None
        if hours > 0:
            expires_at = (datetime.now() + timedelta(hours=hours)).isoformat()

        payload = {
            "invited_name": description,
            "invited_email": None,
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
            return True, data
        else:
            return False, {}

    except Exception as e:
        return False, {}

def register_with_invitation(email: str, name: str, password: str, invitation_code: str,
                            date_of_birth: str, nationality: str, gender: str) -> Tuple[bool, dict]:
    """Student registers with invitation code"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/register-with-invitation",
            json={
                "email": email,
                "password": password,
                "name": name,
                "invitation_code": invitation_code,
                "date_of_birth": date_of_birth,
                "nationality": nationality,
                "gender": gender
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {}

    except Exception as e:
        return False, {}

# ============================================================================
# HELPER FUNCTIONS - CREDIT WORKFLOW
# ============================================================================

def request_credit_purchase(student_token: str, credit_amount: int, amount_eur: float) -> Tuple[bool, dict]:
    """Student requests credit purchase"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/request",
            json={
                "credit_amount": credit_amount,
                "amount_eur": amount_eur,
                "coupon_code": None
            },
            cookies={"access_token": student_token},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {}

    except Exception as e:
        return False, {}

def list_pending_invoices(admin_token: str) -> Tuple[bool, list]:
    """Admin lists pending invoices"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/invoices/list?status=pending",
            cookies={"access_token": admin_token},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, []

    except Exception as e:
        return False, []

def verify_invoice_payment(admin_token: str, invoice_id: int) -> Tuple[bool, dict]:
    """Admin verifies invoice payment"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/verify",
            cookies={"access_token": admin_token},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {}

    except Exception as e:
        return False, {}

# ============================================================================
# HELPER FUNCTIONS - SPECIALIZATION UNLOCK WORKFLOW
# ============================================================================

def get_available_specializations() -> list:
    """Get list of available specializations"""
    return [
        {"code": "GANCUJU_PLAYER", "name": "🥋 GānCuju™ Player", "cost": 100, "api_prefix": "/gancuju"},
        {"code": "LFA_PLAYER", "name": "⚽ LFA Football Player", "cost": 100, "api_prefix": "/lfa-player"},
        {"code": "LFA_COACH", "name": "👨‍🏫 LFA Coach", "cost": 100, "api_prefix": "/coach"},
        {"code": "INTERNSHIP", "name": "📚 Internship Program", "cost": 100, "api_prefix": "/internship"}
    ]

def get_user_licenses(student_token: str) -> Tuple[bool, list]:
    """Get student's unlocked licenses"""
    try:
        # Use Bearer token in Authorization header (API endpoints require this, not cookies)
        response = requests.get(
            f"{API_BASE_URL}/api/v1/licenses/my-licenses",
            headers={"Authorization": f"Bearer {student_token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, []

    except Exception as e:
        return False, []

def calculate_age_group_from_dob(date_of_birth: datetime) -> str:
    """Calculate age group based on date of birth

    Age-based categories (automatic):
    - PRE: 4-6 years (preschool)
    - YOUTH: 7-14 years (elementary school)
    - AMATEUR: 15-18+ years (high school, beginner adults)

    PRO category (15+ years) is NOT automatic - it's a professional qualification
    that requires manual selection and coaching/admin approval!
    """
    today = datetime.today()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

    if age < 7:
        return "PRE"  # 4-6 years: preschool
    elif age < 15:
        return "YOUTH"  # 7-14 years: elementary school
    else:
        return "AMATEUR"  # 15-18+ years: high school and beginner adults
        # NOTE: PRO is NOT assigned automatically - it's a professional qualification!

def unlock_specialization(student_token: str, specialization_code: str, user_dob: datetime = None) -> Tuple[bool, dict]:
    """Unlock a specialization (create UserLicense) - costs 100 credits

    For LFA_PLAYER, age_group is automatically calculated from user's date_of_birth:
    - PRE: under 12 years old
    - YOUTH: 12-17 years old
    - AMATEUR: 18-22 years old
    - PRO: 23+ years old
    """
    try:
        # Calculate age group for LFA_PLAYER if date_of_birth is provided
        age_group = "YOUTH"  # Default
        if specialization_code == "LFA_PLAYER" and user_dob:
            age_group = calculate_age_group_from_dob(user_dob)

        # Map specialization code to API endpoint and request body
        endpoint_map = {
            "GANCUJU_PLAYER": ("/api/v1/gancuju/licenses", {"initial_credits": 0}),
            "LFA_PLAYER": ("/api/v1/lfa-player/licenses", {"age_group": age_group, "initial_credits": 0}),
            "LFA_COACH": ("/api/v1/coach/licenses", {"initial_credits": 0}),
            "INTERNSHIP": ("/api/v1/internship/licenses", {"initial_credits": 0})
        }

        endpoint, body = endpoint_map.get(specialization_code, (None, None))
        if not endpoint:
            return False, {"error": "Invalid specialization"}

        # Use Bearer token in Authorization header (API endpoints require this, not cookies)
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            json=body,
            headers={"Authorization": f"Bearer {student_token}"},
            timeout=10
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return True, data
        else:
            # Extract detailed error message from backend response
            try:
                error_data = response.json()
                # Backend returns {"detail": "message"} for HTTPException
                if "detail" in error_data:
                    error_detail = error_data["detail"]
                # Some endpoints might use {"error": {"message": "..."}}
                elif "error" in error_data and isinstance(error_data["error"], dict):
                    error_detail = error_data["error"].get("message", str(error_data["error"]))
                # Fallback to entire error object
                else:
                    error_detail = str(error_data)
            except:
                # If JSON parsing fails, use raw response text
                error_detail = response.text[:200] if response.text else f"HTTP {response.status_code}"

            return False, {"error": error_detail}

    except Exception as e:
        return False, {"error": str(e)}


def submit_motivation_assessment(student_token: str, specialization_type: str, motivation_data: dict) -> Tuple[bool, str]:
    """Submit motivation assessment after specialization unlock

    Args:
        student_token: Student's JWT token
        specialization_type: Type of specialization (LFA_PLAYER, GANCUJU, COACH, INTERNSHIP)
        motivation_data: Motivation data specific to specialization

    Returns:
        Tuple of (success, message)
    """
    try:
        # Build request body based on specialization type
        if "LFA_PLAYER" in specialization_type or specialization_type == "LFA_FOOTBALL_PLAYER":
            request_body = {"lfa_player": motivation_data}
        elif specialization_type == "GANCUJU_PLAYER":
            request_body = {"gancuju": motivation_data}
        elif specialization_type == "LFA_COACH":
            request_body = {"coach": motivation_data}
        elif specialization_type == "INTERNSHIP":
            request_body = {"internship": motivation_data}
        else:
            return False, f"Unknown specialization type: {specialization_type}"

        response = requests.post(
            f"{API_BASE_URL}/api/v1/licenses/motivation-assessment",
            json=request_body,
            headers={"Authorization": f"Bearer {student_token}"},
            timeout=10
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return True, data.get("message", "Motivation assessment submitted successfully")
        else:
            try:
                error_data = response.json()
                # Extract detailed error for debugging
                if "error" in error_data:
                    error_detail = error_data["error"].get("message", f"HTTP {response.status_code}")
                    if "details" in error_data["error"]:
                        error_detail += f" - {error_data['error']['details']}"
                else:
                    error_detail = error_data.get("detail", f"HTTP {response.status_code}")
            except:
                error_detail = response.text[:500] if response.text else f"HTTP {response.status_code}"

            # Log full error for debugging
            print(f"❌ MOTIVATION ERROR DEBUG:")
            print(f"   Status: {response.status_code}")
            print(f"   Request body: {request_body}")
            print(f"   Response: {response.text[:500]}")

            return False, error_detail

    except Exception as e:
        return False, f"Error: {str(e)}"


# ============================================================================
# RESET FUNCTIONS
# ============================================================================

def reset_invitation_workflow():
    """Reset invitation workflow"""
    st.session_state.invitation_workflow_state = {
        "step1_create_invitation": "pending",
        "step2_student_register": "pending",
        "step3_student_verify": "pending"
    }
    st.session_state.invitation_code = None
    st.session_state.student_registration_data = None

def reset_credit_workflow():
    """Reset credit workflow"""
    st.session_state.credit_workflow_state = {
        "step1_student_request": "pending",
        "step2_admin_verify": "pending",
        "step3_check_credits": "pending"
    }
    st.session_state.invoice_data = None

def reset_specialization_workflow():
    """Reset specialization workflow"""
    st.session_state.specialization_workflow_state = {
        "step1_view_available": "pending",
        "step2_unlock_spec": "pending",
        "step3_motivation": "pending",
        "step4_verify_unlock": "pending"
    }
    st.session_state.selected_specialization = None
    st.session_state.unlocked_licenses = []

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="🎯 Unified Workflow Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("🎯 Workflows & Login")
    st.caption("Select workflow first, then login")

    # Workflow selector FIRST (moved up)
    workflow_choice = st.radio(
        "Choose workflow to test:",
        ["🎟️ Invitation Code Registration", "💳 Credit Purchase", "🎓 Specialization Unlock", "👑 Admin Management", "👨‍🏫 Instructor Dashboard", "🧪 Session Rules Testing"],
        key="workflow_selector"
    )

    if workflow_choice == "🎟️ Invitation Code Registration":
        st.session_state.active_workflow = "invitation"
    elif workflow_choice == "💳 Credit Purchase":
        st.session_state.active_workflow = "credit"
    elif workflow_choice == "🎓 Specialization Unlock":
        st.session_state.active_workflow = "specialization"
    elif workflow_choice == "👑 Admin Management":
        st.session_state.active_workflow = "admin"
    elif workflow_choice == "👨‍🏫 Instructor Dashboard":
        st.session_state.active_workflow = "instructor"
    else:
        st.session_state.active_workflow = "session_rules"

    st.divider()

    # Role-specific login BASED ON WORKFLOW (no tabs!)
    st.subheader("🔐 Login for this workflow")

    # Determine which roles are needed for current workflow
    if st.session_state.active_workflow == "invitation":
        # Needs both Admin and Student
        with st.expander("👑 Admin Login", expanded=not st.session_state.admin_token):
            if not st.session_state.admin_token:
                admin_email = st.text_input("Admin Email", value="admin@lfa.com", key="admin_email_input")
                admin_password = st.text_input("Admin Password", type="password", value="admin123", key="admin_password_input")
                if st.button("🔑 Login as Admin", use_container_width=True):
                    success, token, message = admin_login(admin_email, admin_password)
                    if success:
                        st.session_state.admin_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Admin logged in")
                if st.button("🚪 Logout Admin", use_container_width=True):
                    st.session_state.admin_token = None
                    add_log("Admin logged out", "info")
                    st.rerun()

        with st.expander("🎓 Student Login", expanded=not st.session_state.student_token):
            if not st.session_state.student_token:
                student_email = st.text_input("Student Email", value="", key="student_email_input")
                student_password = st.text_input("Student Password", type="password", value="", key="student_password_input")
                if st.button("🔑 Login as Student", use_container_width=True):
                    success, token, message = student_login(student_email, student_password)
                    if success:
                        st.session_state.student_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Student logged in")
                if st.button("🚪 Logout Student", use_container_width=True):
                    st.session_state.student_token = None
                    add_log("Student logged out", "info")
                    st.rerun()

    elif st.session_state.active_workflow == "credit":
        # Needs both Admin and Student
        with st.expander("🎓 Student Login", expanded=not st.session_state.student_token):
            if not st.session_state.student_token:
                student_email = st.text_input("Student Email", value="", key="student_email_input")
                student_password = st.text_input("Student Password", type="password", value="", key="student_password_input")
                if st.button("🔑 Login as Student", use_container_width=True):
                    success, token, message = student_login(student_email, student_password)
                    if success:
                        st.session_state.student_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Student logged in")
                if st.button("🚪 Logout Student", use_container_width=True):
                    st.session_state.student_token = None
                    add_log("Student logged out", "info")
                    st.rerun()

        with st.expander("👑 Admin Login", expanded=not st.session_state.admin_token):
            if not st.session_state.admin_token:
                admin_email = st.text_input("Admin Email", value="admin@lfa.com", key="admin_email_input")
                admin_password = st.text_input("Admin Password", type="password", value="admin123", key="admin_password_input")
                if st.button("🔑 Login as Admin", use_container_width=True):
                    success, token, message = admin_login(admin_email, admin_password)
                    if success:
                        st.session_state.admin_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Admin logged in")
                if st.button("🚪 Logout Admin", use_container_width=True):
                    st.session_state.admin_token = None
                    add_log("Admin logged out", "info")
                    st.rerun()

    elif st.session_state.active_workflow == "specialization":
        # Needs only Student
        with st.expander("🎓 Student Login", expanded=not st.session_state.student_token):
            if not st.session_state.student_token:
                student_email = st.text_input("Student Email", value="", key="student_email_input")
                student_password = st.text_input("Student Password", type="password", value="", key="student_password_input")
                if st.button("🔑 Login as Student", use_container_width=True):
                    success, token, message = student_login(student_email, student_password)
                    if success:
                        st.session_state.student_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Student logged in")
                if st.button("🚪 Logout Student", use_container_width=True):
                    st.session_state.student_token = None
                    add_log("Student logged out", "info")
                    st.rerun()

    elif st.session_state.active_workflow == "admin":
        # Needs only Admin
        with st.expander("👑 Admin Login", expanded=not st.session_state.admin_token):
            if not st.session_state.admin_token:
                admin_email = st.text_input("Admin Email", value="admin@lfa.com", key="admin_email_input")
                admin_password = st.text_input("Admin Password", type="password", value="admin123", key="admin_password_input")
                if st.button("🔑 Login as Admin", use_container_width=True):
                    success, token, message = admin_login(admin_email, admin_password)
                    if success:
                        st.session_state.admin_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Admin logged in")
                if st.button("🚪 Logout Admin", use_container_width=True):
                    st.session_state.admin_token = None
                    add_log("Admin logged out", "info")
                    st.rerun()

    elif st.session_state.active_workflow == "instructor":
        # Needs only Instructor
        with st.expander("👨‍🏫 Instructor Login", expanded=not st.session_state.instructor_token):
            if not st.session_state.instructor_token:
                instructor_email = st.text_input("Instructor Email", value="grandmaster@lfa.com", key="instructor_email_input")
                instructor_password = st.text_input("Instructor Password", type="password", value="grand123", key="instructor_password_input")
                if st.button("🔑 Login as Instructor", use_container_width=True):
                    success, token, message = instructor_login(instructor_email, instructor_password)
                    if success:
                        st.session_state.instructor_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Instructor logged in")
                if st.button("🚪 Logout Instructor", use_container_width=True):
                    st.session_state.instructor_token = None
                    add_log("Instructor logged out", "info")
                    st.rerun()

    else:  # session_rules
        # Needs both Instructor AND Student for session rules testing
        with st.expander("👨‍🏫 Instructor Login", expanded=not st.session_state.instructor_token):
            if not st.session_state.instructor_token:
                instructor_email = st.text_input("Instructor Email", key="sr_instructor_email")
                instructor_password = st.text_input("Instructor Password", type="password", key="sr_instructor_password")
                if st.button("🔑 Login as Instructor", use_container_width=True, key="sr_instructor_login_btn"):
                    success, token, message = instructor_login(instructor_email, instructor_password)
                    if success:
                        st.session_state.instructor_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Instructor logged in")
                if st.button("🚪 Logout Instructor", use_container_width=True, key="sr_instructor_logout_btn"):
                    st.session_state.instructor_token = None
                    add_log("Instructor logged out", "info")
                    st.rerun()

        with st.expander("👨‍🎓 Student Login", expanded=not st.session_state.student_token):
            if not st.session_state.student_token:
                student_email = st.text_input("Student Email", key="sr_student_email")
                student_password = st.text_input("Student Password", type="password", key="sr_student_password")
                if st.button("🔑 Login as Student", use_container_width=True, key="sr_student_login_btn"):
                    success, token, message = student_login(student_email, student_password)
                    if success:
                        st.session_state.student_token = token
                        add_log(message, "success")
                        st.rerun()
                    else:
                        add_log(message, "error")
                        st.error(message)
            else:
                st.success("✅ Student logged in")
                if st.button("🚪 Logout Student", use_container_width=True, key="sr_student_logout_btn"):
                    st.session_state.student_token = None
                    add_log("Student logged out", "info")
                    st.rerun()

    st.divider()

    # Workflow control
    st.header("🔄 Workflow Control")
    if st.session_state.active_workflow == "invitation":
        if st.button("🔄 Reset Invitation Workflow", use_container_width=True):
            reset_invitation_workflow()
            add_log("Invitation workflow reset", "info")
            st.rerun()
    elif st.session_state.active_workflow == "credit":
        if st.button("🔄 Reset Credit Workflow", use_container_width=True):
            reset_credit_workflow()
            add_log("Credit workflow reset", "info")
            st.rerun()
    else:
        if st.button("🔄 Reset Specialization Workflow", use_container_width=True):
            reset_specialization_workflow()
            add_log("Specialization workflow reset", "info")
            st.rerun()

# ============================================================================
# MAIN HEADER
# ============================================================================

st.title("🎯 Unified Workflow Testing Dashboard")
st.markdown("**Test both workflows:** Invitation Code Registration & Credit Purchase")
st.divider()

# ============================================================================
# WORKFLOW CONTENT
# ============================================================================

if st.session_state.active_workflow == "invitation":
    # ========================================================================
    # INVITATION CODE WORKFLOW
    # ========================================================================

    st.header("🎟️ Invitation Code Registration Workflow")
    st.caption("Admin creates code → Student registers → Verification")
    st.divider()

    col1, col2, col3 = st.columns(3)

    # Step 1: Admin creates invitation code
    with col1:
        step_status = st.session_state.invitation_workflow_state["step1_create_invitation"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 1: Create Code")
        st.caption("**Role:** ADMIN")

        if not st.session_state.admin_token:
            st.warning("⚠️ Please log in as admin")
        elif step_status == "done":
            st.success(f"✅ Code created!")
            if st.session_state.invitation_code:
                st.info(f"**Code:** `{st.session_state.invitation_code}`")
        else:
            description = st.text_input("Description", value="Test Student", key="inv_desc")
            credits = st.number_input("Bonus Credits", min_value=0, max_value=100, value=10, key="inv_credits")
            hours = st.number_input("Expires (hours, 0=never)", min_value=0, max_value=168, value=0, key="inv_hours")
            notes = st.text_area("Notes", value="Test invitation", key="inv_notes")

            if st.button("🎟️ Create Invitation Code", use_container_width=True, key="create_inv_btn"):
                success, data = create_invitation_code(st.session_state.admin_token, description, credits, hours, notes)
                if success:
                    st.session_state.invitation_code = data.get("code", "")
                    st.session_state.invitation_workflow_state["step1_create_invitation"] = "done"
                    st.session_state.invitation_workflow_state["step2_student_register"] = "active"
                    add_log(f"Invitation code created: {st.session_state.invitation_code}", "success")
                    st.rerun()
                else:
                    add_log("Failed to create invitation code", "error")
                    st.error("❌ Failed")

    # Step 2: Student registers
    with col2:
        step_status = st.session_state.invitation_workflow_state["step2_student_register"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 2: Register")
        st.caption("**Role:** STUDENT")

        if st.session_state.invitation_workflow_state["step1_create_invitation"] != "done":
            st.info("⏸️ Waiting for Step 1...")
        elif step_status == "done":
            st.success("✅ Student registered!")
        else:
            st.markdown("**💡 Student registers with own password**")

            email = st.text_input("Student Email", value="newstudent@test.com", key="reg_email")
            name = st.text_input("Student Name", value="New Student", key="reg_name")
            password = st.text_input("Choose Password", type="password", value="", key="reg_password")

            # Required fields for first login
            st.markdown("**📋 Required Information**")
            date_of_birth = st.date_input("Date of Birth", value=datetime(2000, 1, 1), key="reg_dob")

            # Nationality with flags
            nationality_options = [
                "🇭🇺 Hungarian", "🇷🇴 Romanian", "🇸🇰 Slovak", "🇦🇹 Austrian",
                "🇩🇪 German", "🇬🇧 British", "🇫🇷 French", "🇪🇸 Spanish",
                "🇮🇹 Italian", "🇵🇱 Polish", "🇨🇿 Czech", "🇺🇦 Ukrainian",
                "🇷🇸 Serbian", "🇭🇷 Croatian", "🇸🇮 Slovenian", "🇧🇬 Bulgarian",
                "🇺🇸 American", "🇨🇦 Canadian", "🇧🇷 Brazilian", "🇦🇷 Argentine",
                "🇲🇽 Mexican", "🇨🇱 Chilean", "🇨🇴 Colombian", "🇵🇪 Peruvian",
                "🇨🇳 Chinese", "🇯🇵 Japanese", "🇰🇷 Korean", "🇮🇳 Indian",
                "🇦🇺 Australian", "🇳🇿 New Zealand", "🇿🇦 South African", "Other"
            ]
            nationality = st.selectbox("Nationality", options=nationality_options, index=0, key="reg_nationality")

            gender = st.selectbox("Gender", options=["Male", "Female", "Other", "Prefer not to say"], key="reg_gender")

            st.info(f"**Invitation Code:** `{st.session_state.invitation_code}`")
            st.caption("Student chooses their own password")

            if st.button("📝 Register", use_container_width=True, key="register_btn"):
                if not password:
                    st.error("❌ Password is required!")
                elif not nationality:
                    st.error("❌ Nationality is required!")
                else:
                    # Format date_of_birth to ISO format with time
                    dob_str = date_of_birth.strftime("%Y-%m-%dT00:00:00")
                    # Extract nationality name without flag (remove emoji and space)
                    nationality_clean = nationality.split(" ", 1)[1] if " " in nationality else nationality
                    success, data = register_with_invitation(email, name, password, st.session_state.invitation_code,
                                                            dob_str, nationality_clean, gender)
                    if success:
                        st.session_state.student_registration_data = data
                        st.session_state.invitation_workflow_state["step2_student_register"] = "done"
                        st.session_state.invitation_workflow_state["step3_student_verify"] = "active"
                        add_log(f"Student registered: {email}", "success")
                        st.rerun()
                    else:
                        add_log("Registration failed", "error")
                        st.error("❌ Failed")

    # Step 3: Verify
    with col3:
        step_status = st.session_state.invitation_workflow_state["step3_student_verify"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 3: Verify")
        st.caption("**Role:** SYSTEM")

        if st.session_state.invitation_workflow_state["step2_student_register"] != "done":
            st.info("⏸️ Waiting for Step 2...")
        else:
            if st.button("🔍 Verify Registration", use_container_width=True, key="verify_reg_btn"):
                if st.session_state.student_registration_data:
                    token = st.session_state.student_registration_data.get("access_token")
                    success, user_info = get_user_info(token)
                    if success:
                        st.success("✅ Verified!")
                        st.json(user_info)
                        st.session_state.invitation_workflow_state["step3_student_verify"] = "done"

                        if all(s == "done" for s in st.session_state.invitation_workflow_state.values()):
                            st.balloons()
                    else:
                        st.error("❌ Failed")

elif st.session_state.active_workflow == "credit":
    # ========================================================================
    # CREDIT PURCHASE WORKFLOW
    # ========================================================================

    st.header("💳 Credit Purchase Workflow")
    st.caption("Student requests → Admin verifies → Credits added")
    st.divider()

    col1, col2, col3 = st.columns(3)

    # Step 1: Student requests
    with col1:
        step_status = st.session_state.credit_workflow_state["step1_student_request"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 1: Request")
        st.caption("**Role:** STUDENT")

        if not st.session_state.student_token:
            st.warning("⚠️ Please log in as student")
        elif step_status == "done":
            st.success("✅ Request sent!")
            if st.session_state.invoice_data:
                st.info(f"**Ref:** `{st.session_state.invoice_data['payment_reference']}`")
                st.caption(f"Credits: {st.session_state.invoice_data['credit_amount']}")
                st.caption(f"Amount: €{st.session_state.invoice_data['amount_eur']}")
        else:
            st.markdown("**💡 Choose credit package**")

            if st.session_state.student_token:
                success, user_info = get_user_info(st.session_state.student_token)
                if success:
                    st.caption(f"Current balance: **{user_info.get('credit_balance', 0)} credits**")

            # Predefined credit packages
            st.markdown("**📦 Credit Packages:**")

            package_choice = st.radio(
                "Select package:",
                [
                    "💎 Starter: 10 credits - €10",
                    "🚀 Basic: 25 credits - €22.50 (10% off)",
                    "⭐ Standard: 50 credits - €40 (20% off)",
                    "👑 Premium: 100 credits - €70 (30% off)",
                    "🎯 Custom amount"
                ],
                key="package_selector"
            )

            # Parse selected package
            if "Starter" in package_choice:
                credit_amount = 10
                amount_eur = 10.0
            elif "Basic" in package_choice:
                credit_amount = 25
                amount_eur = 22.5
            elif "Standard" in package_choice:
                credit_amount = 50
                amount_eur = 40.0
            elif "Premium" in package_choice:
                credit_amount = 100
                amount_eur = 70.0
            else:  # Custom
                credit_amount = st.number_input("Custom Credits", min_value=1, value=10, key="credit_amt")
                amount_eur = st.number_input("Custom Amount (EUR)", min_value=1.0, value=10.0, step=0.5, key="amount_eur")

            st.info(f"**Selected:** {credit_amount} credits for €{amount_eur}")

            if st.button("💳 Request Purchase", use_container_width=True, key="request_btn"):
                success, data = request_credit_purchase(st.session_state.student_token, credit_amount, amount_eur)
                if success:
                    st.session_state.invoice_data = data
                    st.session_state.credit_workflow_state["step1_student_request"] = "done"
                    st.session_state.credit_workflow_state["step2_admin_verify"] = "active"
                    add_log(f"Credit purchase requested: {credit_amount} credits for €{amount_eur}", "success")
                    st.rerun()
                else:
                    st.error("❌ Failed")

    # Step 2: Admin verifies
    with col2:
        step_status = st.session_state.credit_workflow_state["step2_admin_verify"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 2: Verify")
        st.caption("**Role:** ADMIN")

        if st.session_state.credit_workflow_state["step1_student_request"] != "done":
            st.info("⏸️ Waiting for Step 1...")
        elif not st.session_state.admin_token:
            st.warning("⚠️ Please log in as admin")
        elif step_status == "done":
            st.success("✅ Payment verified!")
        else:
            if st.session_state.invoice_data:
                st.info(f"**Ref:** `{st.session_state.invoice_data['payment_reference']}`")

            if st.button("🔄 Refresh", key="refresh_inv_btn"):
                st.rerun()

            success, invoices = list_pending_invoices(st.session_state.admin_token)
            if success and invoices:
                our_invoice = None
                if st.session_state.invoice_data:
                    ref = st.session_state.invoice_data['payment_reference']
                    our_invoice = next((inv for inv in invoices if inv['payment_reference'] == ref), None)

                if our_invoice:
                    if st.button("✅ Verify Payment", use_container_width=True, key="verify_pay_btn"):
                        success, data = verify_invoice_payment(st.session_state.admin_token, our_invoice['id'])
                        if success:
                            st.session_state.credit_workflow_state["step2_admin_verify"] = "done"
                            st.session_state.credit_workflow_state["step3_check_credits"] = "active"
                            add_log("Payment verified", "success")
                            st.rerun()
                        else:
                            st.error("❌ Failed")

    # Step 3: Check credits
    with col3:
        step_status = st.session_state.credit_workflow_state["step3_check_credits"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 3: Check")
        st.caption("**Role:** SYSTEM")

        if st.session_state.credit_workflow_state["step2_admin_verify"] != "done":
            st.info("⏸️ Waiting for Step 2...")
        else:
            if st.button("🔍 Check Credits", use_container_width=True, key="check_cred_btn"):
                success, user_info = get_user_info(st.session_state.student_token)
                if success:
                    st.success("✅ Verified!")
                    st.metric("💰 Balance", user_info.get('credit_balance', 0))
                    st.session_state.credit_workflow_state["step3_check_credits"] = "done"

                    if all(s == "done" for s in st.session_state.credit_workflow_state.values()):
                        st.balloons()
                else:
                    st.error("❌ Failed")

elif st.session_state.active_workflow == "specialization":
    # ========================================================================
    # SPECIALIZATION UNLOCK WORKFLOW
    # ========================================================================

    # Header with Reset button
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.header("🎓 Specialization Unlock Workflow")
        st.caption("View specializations → Student unlocks → Motivation assessment → Verify")
    with header_col2:
        st.write("")  # Spacer
        if st.button("🔄 Reset Workflow", use_container_width=True, key="reset_spec_workflow"):
            # Reset workflow state to beginning
            st.session_state.specialization_workflow_state = {
                "step1_view_available": "active",
                "step2_unlock_spec": "pending",
                "step3_motivation": "pending",
                "step4_verify_unlock": "pending"
            }
            st.session_state.selected_specialization = None
            add_log("Workflow reset to beginning", "info")
            st.rerun()

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    # Step 1: View available specializations
    with col1:
        step_status = st.session_state.specialization_workflow_state["step1_view_available"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 1: View Available")
        st.caption("**Role:** STUDENT")

        if not st.session_state.student_token:
            st.warning("⚠️ Please log in as student")
        elif step_status == "done":
            st.success("✅ Viewed specializations!")
        else:
            st.markdown("**📋 Available Specializations:**")

            # Show current credit balance
            if st.session_state.student_token:
                success, user_info = get_user_info(st.session_state.student_token)
                if success:
                    st.info(f"**💰 Your credits:** {user_info.get('credit_balance', 0)}")

            # Get user's active licenses
            active_licenses = []
            if st.session_state.student_token:
                success, licenses = get_user_licenses(st.session_state.student_token)
                if success and licenses:
                    active_licenses = [lic.get("specialization_type", "") for lic in licenses]

            specializations = get_available_specializations()

            # Show each specialization with unlocked status
            for spec in specializations:
                is_unlocked = spec['code'] in active_licenses
                if is_unlocked:
                    st.markdown(f"✅ **{spec['name']}** - UNLOCKED")
                else:
                    st.markdown(f"🔓 {spec['name']} - **{spec['cost']} credits**")

            if st.button("👀 View Specializations", use_container_width=True, key="view_specs_btn"):
                st.session_state.specialization_workflow_state["step1_view_available"] = "done"
                st.session_state.specialization_workflow_state["step2_unlock_spec"] = "active"
                add_log("Viewed available specializations", "success")
                st.rerun()

    # Step 2: Unlock specialization
    with col2:
        step_status = st.session_state.specialization_workflow_state["step2_unlock_spec"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 2: Unlock")
        st.caption("**Role:** STUDENT")

        if st.session_state.specialization_workflow_state["step1_view_available"] != "done":
            st.info("⏸️ Waiting for Step 1...")
        elif not st.session_state.student_token:
            st.warning("⚠️ Please log in as student")
        elif step_status == "done":
            st.success("✅ Specialization unlocked!")
            if st.session_state.selected_specialization:
                spec_name = st.session_state.selected_specialization.get("name", "Unknown")
                st.info(f"**Unlocked:** {spec_name}")
        else:
            st.markdown("**💡 Choose a specialization to unlock:**")

            # Show current credits
            success, user_info = get_user_info(st.session_state.student_token)
            if success:
                current_credits = user_info.get('credit_balance', 0)
                st.caption(f"Current balance: **{current_credits} credits**")

                if current_credits < 100:
                    st.warning(f"⚠️ Insufficient credits! You have {current_credits}, need 100.")

            # Get user's active licenses
            active_licenses = []
            success_lic, licenses = get_user_licenses(st.session_state.student_token)
            if success_lic and licenses:
                active_licenses = [lic.get("specialization_type", "") for lic in licenses]

            # Filter out already unlocked specializations
            all_specializations = get_available_specializations()
            specializations = [
                spec for spec in all_specializations
                if spec["code"] not in active_licenses
            ]

            # If no specializations available to unlock
            if not specializations:
                st.info("✅ You have already unlocked all available specializations!")
                st.stop()

            spec_choice = st.radio(
                "Select specialization:",
                [f"{s['name']} - {s['cost']} credits" for s in specializations],
                key="spec_selector"
            )

            # Extract selected specialization
            selected_spec = None
            for spec in specializations:
                if spec["name"] in spec_choice:
                    selected_spec = spec
                    break

            if selected_spec:
                st.info(f"**Selected:** {selected_spec['name']}")

                # Show age group info for LFA Player (auto-calculated from DOB)
                if selected_spec["code"] == "LFA_PLAYER" and user_info and user_info.get('date_of_birth'):
                    try:
                        dob_str = user_info.get('date_of_birth')
                        if isinstance(dob_str, str):
                            user_dob = datetime.fromisoformat(dob_str.replace('Z', '+00:00'))
                        else:
                            user_dob = dob_str
                        age_group = calculate_age_group_from_dob(user_dob)
                        st.caption(f"**Age Group:** {age_group} (automatically calculated from your birth date)")
                    except:
                        pass

                if st.button("🔓 Unlock Specialization", use_container_width=True, key="unlock_btn"):
                    # Get user DOB for age_group calculation
                    user_dob = None
                    if user_info and user_info.get('date_of_birth'):
                        try:
                            dob_str = user_info.get('date_of_birth')
                            if isinstance(dob_str, str):
                                user_dob = datetime.fromisoformat(dob_str.replace('Z', '+00:00'))
                            else:
                                user_dob = dob_str
                        except:
                            pass

                    success, data = unlock_specialization(st.session_state.student_token, selected_spec["code"], user_dob)
                    if success:
                        st.session_state.selected_specialization = selected_spec
                        st.session_state.specialization_workflow_state["step2_unlock_spec"] = "done"
                        st.session_state.specialization_workflow_state["step3_motivation"] = "active"
                        add_log(f"Unlocked specialization: {selected_spec['name']}", "success")
                        st.rerun()
                    else:
                        error_msg = data.get("error", "Unknown error")
                        add_log(f"Failed to unlock: {error_msg}", "error")
                        st.error(f"❌ Failed: {error_msg}")

    # Step 3: Motivation Assessment
    with col3:
        step_status = st.session_state.specialization_workflow_state["step3_motivation"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 3: Motivation")
        st.caption("**Role:** STUDENT")

        if st.session_state.specialization_workflow_state["step2_unlock_spec"] != "done":
            st.info("⏸️ Waiting for Step 2...")
        elif not st.session_state.student_token:
            st.warning("⚠️ Please log in as student")
        elif step_status == "done":
            st.success("✅ Assessment completed!")
        else:
            st.markdown("**📝 Complete your assessment:**")

            # Get specialization - either from session_state OR fetch from database
            spec_code = None
            if st.session_state.selected_specialization:
                spec_code = st.session_state.selected_specialization.get("code", "")
            else:
                # Fetch user's active license from database
                success, licenses = get_user_licenses(st.session_state.student_token)
                if success and licenses:
                    # Get the most recent license
                    latest_license = licenses[0]
                    spec_code = latest_license.get("specialization_type", "")
                    # Store in session for future use
                    st.session_state.selected_specialization = {
                        "code": spec_code,
                        "name": spec_code.replace("_", " ").title()
                    }

            if spec_code:

                # LFA PLAYER - Position + 7 Skill Self-Ratings
                if "LFA_PLAYER" in spec_code or spec_code == "LFA_FOOTBALL_PLAYER":
                    # Position selection
                    st.caption("**Select your preferred playing position:**")
                    position = st.selectbox(
                        "Position:",
                        ["Striker", "Midfielder", "Defender", "Goalkeeper"],
                        key="mot_position"
                    )

                    st.divider()

                    # Skill self-ratings
                    st.caption("**Rate your skills (1-10):**")
                    heading = st.slider("Heading", 1, 10, 5, key="mot_heading")
                    shooting = st.slider("Shooting", 1, 10, 5, key="mot_shooting")
                    crossing = st.slider("Crossing", 1, 10, 5, key="mot_crossing")
                    passing = st.slider("Passing", 1, 10, 5, key="mot_passing")
                    dribbling = st.slider("Dribbling", 1, 10, 5, key="mot_dribbling")
                    ball_control = st.slider("Ball Control", 1, 10, 5, key="mot_ball_control")
                    defending = st.slider("Defending", 1, 10, 5, key="mot_defending")

                    motivation_data = {
                        "preferred_position": position,
                        "heading_self_rating": heading,
                        "shooting_self_rating": shooting,
                        "crossing_self_rating": crossing,
                        "passing_self_rating": passing,
                        "dribbling_self_rating": dribbling,
                        "ball_control_self_rating": ball_control,
                        "defending_self_rating": defending
                    }

                # GANCUJU - Character Type
                elif spec_code == "GANCUJU_PLAYER":
                    character = st.radio(
                        "Choose your path:",
                        ["Warrior - Competition focused, winning mindset", "Teacher - Teaching others, knowledge transfer"],
                        key="mot_gancuju"
                    )
                    motivation_data = {
                        "character_type": "warrior" if "Warrior" in character else "teacher"
                    }

                # COACH - Preferences
                elif spec_code == "LFA_COACH":
                    age_group = st.selectbox("Preferred age group:", ["PRE", "YOUTH", "AMATEUR", "PRO", "ALL"], key="mot_coach_age")
                    role = st.selectbox("Preferred role:", [
                        "Technical Coach", "Fitness Coach", "Tactical Analyst",
                        "Goalkeeping Coach", "Head Coach", "Coaching Coordinator"
                    ], key="mot_coach_role")
                    specialization = st.selectbox("Specialization area:", [
                        "Attacking play", "Defensive play", "Goalkeeping", "Set pieces", "Mental coaching"
                    ], key="mot_coach_spec")

                    motivation_data = {
                        "age_group_preference": age_group,
                        "role_preference": role,
                        "specialization_area": specialization
                    }

                # INTERNSHIP - Position Selection (Max 7, Min 1)
                elif spec_code == "INTERNSHIP":
                    st.caption("🎯 Select your position preferences (minimum 1, maximum 7)")
                    st.info("✅ Choose the internship positions you're interested in. You can select between 1 and 7 positions.")

                    # All 45 available positions across 6 departments
                    positions = [
                        "LFA Sports Director", "LFA Digital Marketing Manager", "LFA Social Media Manager",
                        "LFA Advertising Specialist", "LFA Brand Manager", "LFA Event Organizer",
                        "LFA Facility Manager", "LFA Technical Manager", "LFA Maintenance Technician",
                        "LFA Energy Specialist", "LFA Groundskeeping Specialist", "LFA Security Director",
                        "LFA Retail Manager", "LFA Inventory Manager", "LFA Sales Representative",
                        "LFA Webshop Manager", "LFA Ticket Office Manager", "LFA Customer Service Agent",
                        "LFA VIP Relations Manager", "LFA Press Officer", "LFA Spokesperson",
                        "LFA Content Creator", "LFA Photographer", "LFA Videographer",
                        "LFA Talent Scout", "LFA Mental Coach", "LFA Social Worker",
                        "LFA Regional Director", "LFA Liaison Officer", "LFA Business Development Manager"
                    ]

                    # Initialize selected positions in session state
                    if "selected_internship_positions" not in st.session_state:
                        st.session_state.selected_internship_positions = []

                    # Display checkboxes for each position
                    st.write("**Select positions:**")
                    selected_positions = []

                    for position in positions:
                        # Disable checkbox if 7 already selected AND this position is NOT already selected
                        is_disabled = (len(st.session_state.selected_internship_positions) >= 7 and
                                     position not in st.session_state.selected_internship_positions)

                        is_checked = st.checkbox(
                            position,
                            value=position in st.session_state.selected_internship_positions,
                            key=f"mot_int_cb_{position}",
                            disabled=is_disabled
                        )

                        if is_checked:
                            selected_positions.append(position)

                    # Update session state
                    st.session_state.selected_internship_positions = selected_positions

                    # Show selection count
                    selection_count = len(selected_positions)
                    if selection_count == 0:
                        st.warning(f"⚠️ Please select at least 1 position (0/7 selected)")
                    elif selection_count > 7:
                        st.error(f"❌ Too many selections! Maximum is 7 positions ({selection_count}/7 selected)")
                    else:
                        st.success(f"✅ {selection_count}/7 positions selected")

                    # Send selected positions as a list
                    motivation_data = {
                        "selected_positions": selected_positions
                    }

                else:
                    st.warning(f"Unknown specialization: {spec_code}")
                    motivation_data = None

                # Validation for Internship - ensure at least 1 position selected
                can_submit = True
                if spec_code == "INTERNSHIP" and motivation_data:
                    if len(motivation_data.get("selected_positions", [])) < 1:
                        can_submit = False
                        st.error("❌ Please select at least 1 position before submitting")
                    elif len(motivation_data.get("selected_positions", [])) > 7:
                        can_submit = False
                        st.error("❌ Please select maximum 7 positions")

                if motivation_data and can_submit and st.button("✅ Submit Assessment", use_container_width=True, key="submit_motivation_btn"):
                    success, message = submit_motivation_assessment(st.session_state.student_token, spec_code, motivation_data)
                    if success:
                        st.session_state.specialization_workflow_state["step3_motivation"] = "done"
                        st.session_state.specialization_workflow_state["step4_verify_unlock"] = "active"
                        add_log(f"Motivation assessment completed", "success")
                        st.rerun()
                    else:
                        add_log(f"Failed to submit assessment: {message}", "error")
                        st.error(f"❌ Failed: {message}")
            else:
                st.warning("⚠️ No specialization found. Please unlock a specialization first in Step 2.")

    # Step 4: Verify unlock
    with col4:
        step_status = st.session_state.specialization_workflow_state["step4_verify_unlock"]
        status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

        st.markdown(f"### {status_icon} Step 4: Verify")
        st.caption("**Role:** STUDENT")

        if st.session_state.specialization_workflow_state["step3_motivation"] != "done":
            st.info("⏸️ Waiting for Step 3...")
        elif not st.session_state.student_token:
            st.warning("⚠️ Please log in as student")
        elif step_status == "done":
            st.success("✅ Verified!")
            if st.session_state.unlocked_licenses:
                st.info(f"**Total licenses:** {len(st.session_state.unlocked_licenses)}")
        else:
            st.markdown("**🔍 Verify your licenses**")

            if st.button("🔍 Check My Licenses", use_container_width=True, key="check_licenses_btn"):
                success, licenses = get_user_licenses(st.session_state.student_token)
                if success:
                    st.session_state.unlocked_licenses = licenses
                    st.session_state.specialization_workflow_state["step4_verify_unlock"] = "done"
                    add_log(f"Verified licenses: {len(licenses)} found", "success")
                    st.rerun()
                else:
                    add_log("Failed to fetch licenses", "error")
                    st.error("❌ Failed")

            # Show updated credit balance
            success, user_info = get_user_info(st.session_state.student_token)
            if success:
                st.caption(f"Credits after unlock: **{user_info.get('credit_balance', 0)}**")

    # Show unlocked licenses
    if st.session_state.unlocked_licenses:
        st.divider()
        st.subheader("🎓 Your Unlocked Licenses")

        for license in st.session_state.unlocked_licenses:
            with st.expander(f"📜 {license.get('specialization_type', 'Unknown')} License"):
                st.json(license)

elif st.session_state.active_workflow == "admin":
    # ========================================================================
    # ADMIN MANAGEMENT WORKFLOW
    # ========================================================================

    st.header("👑 Admin Management Dashboard")
    st.caption("Semester Generation • Location Assignment • Instructor Management")
    st.divider()

    if not st.session_state.admin_token:
        st.warning("⚠️ Please log in as admin to access management features")
    else:
        # ====================================================================
        # SEMESTER GENERATION & MANAGEMENT
        # ====================================================================

        st.subheader("📅 Semester Generation & Management")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Location Management", "🚀 Generate Semesters", "🎯 Manage Semesters", "👨‍🏫 Instructor Specs", "📅 Campus Calendar"])

        # TAB 1: Location Management (LFA Education Centers)
        with tab1:
            st.markdown("### 📍 LFA Education Center Locations")
            st.caption("Manage academy locations where semesters can be held")

            # Fetch all locations
            try:
                locations_response = requests.get(
                    f"{API_BASE_URL}/api/v1/admin/locations/",
                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                    params={"include_inactive": True},
                    timeout=10
                )

                if locations_response.status_code == 200:
                    all_locations = locations_response.json()

                    # Show existing locations
                    if all_locations:
                        st.markdown("#### 📋 Existing Locations")
                        for loc in all_locations:
                            status_icon = "✅" if loc['is_active'] else "❌"
                            with st.expander(f"{status_icon} {loc['name']} ({loc['city']}, {loc['country']})"):
                                st.markdown(f"**ID:** {loc['id']}")
                                st.markdown(f"**City:** {loc['city']}")
                                if loc.get('postal_code'):
                                    st.markdown(f"**Postal Code:** {loc['postal_code']}")
                                st.markdown(f"**Country:** {loc['country']}")
                                if loc.get('venue'):
                                    st.markdown(f"**Venue:** {loc['venue']}")
                                if loc.get('address'):
                                    st.markdown(f"**Address:** {loc['address']}")
                                if loc.get('notes'):
                                    st.markdown(f"**Notes:** {loc['notes']}")
                                st.markdown(f"**Active:** {'Yes' if loc['is_active'] else 'No'}")

                                # Toggle active status
                                new_status = not loc['is_active']
                                action_label = "Activate" if new_status else "Deactivate"

                                if st.button(f"🔄 {action_label}", key=f"toggle_{loc['id']}"):
                                    update_response = requests.put(
                                        f"{API_BASE_URL}/api/v1/admin/locations/{loc['id']}",
                                        headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                        json={"is_active": new_status},
                                        timeout=10
                                    )

                                    if update_response.status_code == 200:
                                        st.success(f"✅ Location {action_label.lower()}d successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to update location")
                    else:
                        st.info("📭 No locations created yet")

                    st.divider()

                    # Create new location form
                    st.markdown("#### ➕ Create New Location")

                    with st.form("create_location_form"):
                        new_name = st.text_input("Location Name *", placeholder="LFA Education Center - Budapest")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            new_city = st.text_input("City *", placeholder="Budapest")
                        with col2:
                            new_postal_code = st.text_input("Postal Code", placeholder="1011")
                        with col3:
                            new_country = st.text_input("Country *", placeholder="Hungary")

                        new_venue = st.text_input("Venue", placeholder="Buda Campus (optional)")
                        new_address = st.text_input("Address", placeholder="Fő utca 1. (optional)")
                        new_notes = st.text_area("Notes", placeholder="Additional information (optional)")
                        new_is_active = st.checkbox("Active", value=True)

                        create_btn = st.form_submit_button("➕ Create Location", use_container_width=True, type="primary")

                        if create_btn:
                            if not new_name or not new_city or not new_country:
                                st.error("❌ Please fill in all required fields (Name, City, Country)")
                            else:
                                create_response = requests.post(
                                    f"{API_BASE_URL}/api/v1/admin/locations/",
                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                    json={
                                        "name": new_name,
                                        "city": new_city,
                                        "postal_code": new_postal_code if new_postal_code else None,
                                        "country": new_country,
                                        "venue": new_venue if new_venue else None,
                                        "address": new_address if new_address else None,
                                        "notes": new_notes if new_notes else None,
                                        "is_active": new_is_active
                                    },
                                    timeout=10
                                )

                                if create_response.status_code == 201:
                                    created_location = create_response.json()
                                    st.success(f"✅ Location created: {created_location['name']}")
                                    add_log(f"Created location: {created_location['name']}", "success")
                                    st.rerun()
                                else:
                                    error_msg = create_response.json().get('detail', 'Unknown error')
                                    st.error(f"❌ Failed to create location: {error_msg}")
                                    add_log(f"Failed to create location: {error_msg}", "error")

                else:
                    st.error("❌ Failed to fetch locations")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

        # TAB 2: Generate Semesters
        with tab2:
            st.markdown("### 🚀 Generate Semesters for a Year")
            st.caption("⚠️ **Important:** You must select an active location before generating semesters!")

            # Fetch active locations first
            try:
                active_locs_response = requests.get(
                    f"{API_BASE_URL}/api/v1/admin/locations/active/list",
                    timeout=10
                )

                if active_locs_response.status_code == 200:
                    active_locations = active_locs_response.json()

                    if not active_locations:
                        st.error("❌ No active locations available! Please create a location first in the **📍 Location Management** tab.")
                        gen_location_id = None
                    else:
                        # Location selector
                        st.markdown("#### 📍 Select Location")
                        location_options = {f"{loc['name']} ({loc['city']}, {loc['country']})": loc['id'] for loc in active_locations}
                        selected_location_label = st.selectbox("Location", list(location_options.keys()), key="gen_location_select")
                        gen_location_id = location_options[selected_location_label]

                        # Find selected location details
                        selected_location = next((loc for loc in active_locations if loc['id'] == gen_location_id), None)
                        if selected_location:
                            st.caption(f"🏢 **City:** {selected_location['city']} | **Country:** {selected_location['country']}")
                            if selected_location.get('venue'):
                                st.caption(f"🏟️ **Venue:** {selected_location['venue']}")

                        st.divider()

                        # Fetch available templates from backend
                        templates_response = requests.get(
                            f"{API_BASE_URL}/api/v1/admin/semesters/available-templates",
                            headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                            timeout=10
                        )

                        if templates_response.status_code == 200:
                            available_templates = templates_response.json().get("available_templates", [])

                            # Extract unique specializations
                            available_specs = sorted(list(set(t["specialization"] for t in available_templates)))

                            st.markdown("#### 🎯 Semester Configuration")

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                gen_year = st.number_input("Year", min_value=2024, max_value=2030, value=2026, step=1)

                            with col2:
                                if available_specs:
                                    gen_spec = st.selectbox("Specialization", available_specs, key="gen_spec_select")
                                else:
                                    st.error("❌ No templates available")
                                    gen_spec = None

                            with col3:
                                # Filter age groups based on selected specialization
                                if gen_spec:
                                    available_age_groups = sorted([
                                        t["age_group"] for t in available_templates
                                        if t["specialization"] == gen_spec
                                    ])
                                    gen_age_group = st.selectbox("Age Group", available_age_groups, key="gen_age_select")
                                else:
                                    st.warning("⚠️ Select a specialization first")
                                    gen_age_group = None

                            # Show info about selected template
                            if gen_spec and gen_age_group:
                                selected_template = next(
                                    (t for t in available_templates
                                     if t["specialization"] == gen_spec and t["age_group"] == gen_age_group),
                                    None
                                )
                                if selected_template:
                                    st.caption(f"📊 **{selected_template['cycle_type'].title()}** cycle: {selected_template['semester_count']} semesters/year")
                                    st.caption(f"This will generate **{selected_template['semester_count']} semesters** for **{gen_year}/{gen_spec}/{gen_age_group}** at **{selected_location_label}**")
                        else:
                            st.error("❌ Failed to fetch available templates")
                            gen_spec = None
                            gen_age_group = None

                        if gen_location_id and gen_spec and gen_age_group and st.button("🚀 Generate Semesters", use_container_width=True, type="primary"):
                            response = requests.post(
                                f"{API_BASE_URL}/api/v1/admin/semesters/generate",
                                headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                json={
                                    "year": gen_year,
                                    "specialization": gen_spec,
                                    "age_group": gen_age_group,
                                    "location_id": gen_location_id
                                },
                                timeout=30
                            )

                            if response.status_code == 200:
                                result = response.json()
                                st.success(f"✅ {result['message']}")
                                st.info(f"📅 Generated {result['generated_count']} semesters at {selected_location_label}")

                                with st.expander("📋 View Generated Semesters"):
                                    for sem in result['semesters']:
                                        st.markdown(f"**{sem['code']}** - {sem['name']}")
                                        st.caption(f"📍 {sem['start_date']} to {sem['end_date']}")
                                        st.caption(f"🎯 Theme: {sem['theme']}")
                                        st.divider()

                                add_log(f"Generated {result['generated_count']} semesters for {gen_year}/{gen_spec}/{gen_age_group} at {selected_location_label}", "success")
                            else:
                                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                                st.error(f"❌ Failed: {error_msg}")
                                add_log(f"Failed to generate semesters: {error_msg}", "error")

                else:
                    st.error("❌ Failed to fetch active locations")
                    gen_location_id = None

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                gen_location_id = None

        # TAB 3: Manage Semesters (View & Delete)
        with tab3:
            st.markdown("### 🎯 Manage Existing Semesters")
            st.caption("View all semesters and delete unused ones")

            # Refresh button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Refresh", key="refresh_semesters", use_container_width=True):
                    st.rerun()

            try:
                # Fetch all semesters
                response = requests.get(
                    f"{API_BASE_URL}/api/v1/semesters/",
                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    semesters = data.get("semesters", [])

                    if not semesters:
                        st.info("📭 No semesters found. Generate some in Tab 2!")
                    else:
                        st.success(f"📊 Found **{len(semesters)}** semesters")

                        # Debug: Show first semester structure
                        if len(semesters) > 0:
                            with st.expander("🔍 Debug: First Semester Data"):
                                st.json(semesters[0])

                        # Filter options
                        st.markdown("#### 🔍 Filters")
                        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

                        with filter_col1:
                            # Extract unique years
                            all_years = list(set([s['code'].split('/')[0] for s in semesters if s.get('code') and '/' in s['code']]))
                            selected_year = st.selectbox(
                                "📅 Year",
                                ["All"] + sorted(all_years, reverse=True),
                                key="filter_year"
                            )

                        with filter_col2:
                            # Extract unique specializations (base type without age group)
                            all_base_specs = set()
                            for s in semesters:
                                spec_type = s.get('specialization_type')
                                if spec_type and '_' in spec_type:
                                    # Extract base spec (e.g., "LFA_PLAYER_PRE" -> "LFA_PLAYER")
                                    parts = spec_type.split('_')
                                    # Join all parts except the last one (age group)
                                    base_spec = '_'.join(parts[:-1])
                                    all_base_specs.add(base_spec)
                                elif spec_type:
                                    all_base_specs.add(spec_type)

                            selected_base_spec = st.selectbox(
                                "⚽ Specialization",
                                ["All"] + sorted(list(all_base_specs)),
                                key="filter_base_spec"
                            )

                        with filter_col3:
                            # Extract unique age groups
                            all_age_groups = list(set([
                                s['age_group'] for s in semesters if s.get('age_group')
                            ]))
                            selected_age_group = st.selectbox(
                                "👥 Age Group",
                                ["All"] + sorted(all_age_groups),
                                key="filter_age_group"
                            )

                        with filter_col4:
                            # Extract unique locations (city)
                            all_locations = list(set([
                                s['location_city'] for s in semesters if s.get('location_city')
                            ]))
                            selected_location = st.selectbox(
                                "📍 Location",
                                ["All"] + sorted([loc for loc in all_locations if loc]),
                                key="filter_location"
                            )

                        # Apply filters
                        filtered_semesters = semesters

                        # Filter by year
                        if selected_year != "All":
                            filtered_semesters = [s for s in filtered_semesters if s.get('code', '').startswith(selected_year)]

                        # Filter by base specialization (e.g., LFA_PLAYER)
                        if selected_base_spec != "All":
                            filtered_semesters = [s for s in filtered_semesters
                                                if s.get('specialization_type', '').startswith(selected_base_spec)]

                        # Filter by age group
                        if selected_age_group != "All":
                            filtered_semesters = [s for s in filtered_semesters
                                                if s.get('age_group') == selected_age_group]

                        # Filter by location
                        if selected_location != "All":
                            filtered_semesters = [s for s in filtered_semesters
                                                if s.get('location_city') == selected_location]

                        st.divider()

                        # Bulk actions
                        st.markdown(f"#### 📅 Semesters ({len(filtered_semesters)})")

                        # Only show bulk delete for empty semesters
                        deletable_semesters = [s for s in filtered_semesters if s.get('total_sessions', 0) == 0]

                        if deletable_semesters:
                            with st.expander(f"🗑️ Bulk Delete ({len(deletable_semesters)} empty semesters)", expanded=False):
                                st.warning(f"⚠️ You can bulk delete **{len(deletable_semesters)} empty semesters** (semesters with no sessions)")

                                # Show which semesters will be deleted
                                st.caption("**Semesters that will be deleted:**")
                                for s in deletable_semesters[:10]:  # Show first 10
                                    st.text(f"• {s.get('code', 'N/A')} - {s.get('theme', 'N/A')}")
                                if len(deletable_semesters) > 10:
                                    st.caption(f"... and {len(deletable_semesters) - 10} more")

                                st.divider()

                                # Confirmation
                                confirm_bulk = st.checkbox(
                                    f"✅ I confirm I want to delete all {len(deletable_semesters)} empty semesters",
                                    key="confirm_bulk_delete"
                                )

                                if confirm_bulk:
                                    if st.button(f"🗑️ DELETE ALL {len(deletable_semesters)} EMPTY SEMESTERS", type="primary", use_container_width=True):
                                        # Delete all empty semesters
                                        success_count = 0
                                        error_count = 0
                                        errors = []

                                        progress_bar = st.progress(0)
                                        status_text = st.empty()

                                        for i, sem in enumerate(deletable_semesters):
                                            status_text.text(f"Deleting {i+1}/{len(deletable_semesters)}: {sem.get('code', 'N/A')}")

                                            try:
                                                delete_response = requests.delete(
                                                    f"{API_BASE_URL}/api/v1/semesters/{sem['id']}",
                                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                    timeout=10
                                                )

                                                if delete_response.status_code == 200:
                                                    success_count += 1
                                                else:
                                                    error_count += 1
                                                    errors.append(f"{sem.get('code', 'N/A')}: {delete_response.json().get('detail', 'Unknown error')}")
                                            except Exception as e:
                                                error_count += 1
                                                errors.append(f"{sem.get('code', 'N/A')}: {str(e)}")

                                            # Update progress
                                            progress_bar.progress((i + 1) / len(deletable_semesters))

                                        # Summary
                                        status_text.empty()
                                        progress_bar.empty()

                                        if success_count > 0:
                                            st.success(f"✅ Successfully deleted **{success_count}** semesters!")
                                            add_log(f"Bulk deleted {success_count} empty semesters", "success")

                                        if error_count > 0:
                                            st.error(f"❌ Failed to delete **{error_count}** semesters")
                                            with st.expander("View Errors"):
                                                for err in errors:
                                                    st.text(err)
                                            add_log(f"Bulk delete failed for {error_count} semesters", "error")

                                        # Refresh after bulk delete
                                        st.rerun()

                        st.divider()

                        # Individual semester list
                        for semester in filtered_semesters:
                            # Status indicator
                            is_active = semester.get('is_active', False)
                            status_icon = "✅" if is_active else "⏸️"
                            status_text = "ACTIVE" if is_active else "INACTIVE"

                            with st.expander(f"{status_icon} **{semester.get('code', 'N/A')}** - {semester.get('name', 'N/A')} [{status_text}]"):
                                # Semester details
                                info_col1, info_col2, info_col3 = st.columns(3)

                                with info_col1:
                                    st.markdown(f"**📅 Period:**")
                                    st.caption(f"Start: {semester.get('start_date', 'N/A')}")
                                    st.caption(f"End: {semester.get('end_date', 'N/A')}")
                                    st.caption(f"Theme: {semester.get('theme', 'N/A')}")

                                with info_col2:
                                    st.markdown(f"**📊 Statistics:**")
                                    st.caption(f"Groups: {semester.get('total_groups', 0)}")
                                    st.caption(f"Sessions: {semester.get('total_sessions', 0)}")
                                    st.caption(f"Bookings: {semester.get('total_bookings', 0)}")
                                    st.caption(f"Active Users: {semester.get('active_users', 0)}")

                                with info_col3:
                                    st.markdown(f"**👨‍🏫 Master Instructor:**")
                                    master_id = semester.get('master_instructor_id')
                                    if master_id:
                                        st.caption(f"✅ Assigned (ID: {master_id})")
                                    else:
                                        st.caption("❌ Not assigned yet")

                                    st.markdown(f"**📍 Status:**")
                                    if not master_id:
                                        st.error("❌ Cannot activate - No instructor")
                                    elif is_active:
                                        st.success("✅ Active")
                                    else:
                                        st.warning("⏸️ Inactive (ready to activate)")

                                st.markdown(f"**🎯 Focus:** {semester.get('focus_description', 'N/A')}")

                                st.divider()

                                # Instructor assignment & activation section
                                st.markdown("### 👨‍🏫 Instructor Assignment & Activation")

                                assign_col1, assign_col2 = st.columns(2)

                                with assign_col1:
                                    # Fetch instructors list
                                    try:
                                        instructors_response = requests.get(
                                            f"{API_BASE_URL}/api/v1/users/?role=instructor&limit=100",
                                            headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                            timeout=10
                                        )

                                        if instructors_response.status_code == 200:
                                            instructors_data = instructors_response.json()
                                            instructors = instructors_data.get('users', [])

                                            # Create instructor options
                                            instructor_options = {
                                                "None (No instructor)": None
                                            }
                                            for inst in instructors:
                                                instructor_options[f"{inst.get('name', 'Unknown')} ({inst.get('email', 'N/A')})"] = inst['id']

                                            # Find current selection
                                            current_selection = "None (No instructor)"
                                            for label, inst_id in instructor_options.items():
                                                if inst_id == master_id:
                                                    current_selection = label
                                                    break

                                            selected_instructor = st.selectbox(
                                                "Assign Master Instructor",
                                                options=list(instructor_options.keys()),
                                                index=list(instructor_options.keys()).index(current_selection),
                                                key=f"instructor_select_{semester['id']}"
                                            )

                                            new_instructor_id = instructor_options[selected_instructor]

                                            if new_instructor_id != master_id:
                                                if st.button("💾 Update Instructor", key=f"update_inst_{semester['id']}", type="primary"):
                                                    update_response = requests.patch(
                                                        f"{API_BASE_URL}/api/v1/semesters/{semester['id']}",
                                                        headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                        json={"master_instructor_id": new_instructor_id},
                                                        timeout=10
                                                    )

                                                    if update_response.status_code == 200:
                                                        st.success("✅ Instructor updated!")
                                                        add_log(f"Updated instructor for semester {semester['code']}", "success")
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Failed: {update_response.text}")
                                        else:
                                            st.error(f"❌ Failed to fetch instructors: {instructors_response.status_code}")

                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")

                                    # NEW: Send Assignment Request to Available Instructors
                                    st.divider()
                                    st.markdown("**📨 OR Send Assignment Request**")
                                    st.caption("Find available instructors and send them a request")

                                    # Initialize session state for available instructors if not exists
                                    if f"avail_inst_{semester['id']}" not in st.session_state:
                                        st.session_state[f"avail_inst_{semester['id']}"] = None

                                    if st.button("🔍 Find Available Instructors", key=f"find_avail_{semester['id']}"):
                                        # Get semester details for filtering
                                        sem_year = semester['start_date'][:4] if semester.get('start_date') else None

                                        # Determine time period from semester dates
                                        if semester.get('start_date'):
                                            start_month = int(semester['start_date'][5:7])
                                            if 1 <= start_month <= 3:
                                                time_period = "Q1"
                                            elif 4 <= start_month <= 6:
                                                time_period = "Q2"
                                            elif 7 <= start_month <= 9:
                                                time_period = "Q3"
                                            else:
                                                time_period = "Q4"
                                        else:
                                            time_period = None

                                        if sem_year and time_period:
                                            # Fetch available instructors (location comes from assignment request, not availability!)
                                            try:
                                                avail_response = requests.get(
                                                    f"{API_BASE_URL}/api/v1/instructor-assignments/available-instructors",
                                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                    params={
                                                        "year": sem_year,
                                                        "time_period": time_period
                                                    },
                                                    timeout=10
                                                )

                                                if avail_response.status_code == 200:
                                                    available_instructors = avail_response.json()
                                                    # STORE IN SESSION STATE!
                                                    st.session_state[f"avail_inst_{semester['id']}"] = available_instructors

                                                    if available_instructors:
                                                        st.success(f"✅ Found {len(available_instructors)} available instructor(s)!")

                                                        for avail_inst in available_instructors:
                                                            with st.expander(f"👨‍🏫 {avail_inst['instructor_name']} ({avail_inst['instructor_email']})"):
                                                                # Display licenses - show only HIGHEST level per type
                                                                licenses = avail_inst.get('licenses', [])
                                                                if licenses:
                                                                    # Find highest level for each specialization type
                                                                    max_levels = {}
                                                                    for lic in licenses:
                                                                        spec_type = lic['specialization_type']
                                                                        current_level = lic['current_level']
                                                                        if spec_type not in max_levels or current_level > max_levels[spec_type]:
                                                                            max_levels[spec_type] = current_level

                                                                    # Display as compact badges with ONLY highest level
                                                                    badges = []

                                                                    if "PLAYER" in max_levels:
                                                                        belt_emoji = {1: "🤍", 2: "💛", 3: "💚", 4: "💙", 5: "🤎", 6: "🩶", 7: "🖤", 8: "❤️"}
                                                                        belt_names = {
                                                                            1: "Bamboo Student",
                                                                            2: "Morning Dew",
                                                                            3: "Flexible Reed",
                                                                            4: "Sky River",
                                                                            5: "Strong Root",
                                                                            6: "Winter Moon",
                                                                            7: "Midnight Guardian",
                                                                            8: "Dragon Wisdom"
                                                                        }
                                                                        level = max_levels["PLAYER"]
                                                                        badges.append(f"🥋 {belt_emoji.get(level, '⚪')} {belt_names.get(level, f'L{level}')}")

                                                                    if "COACH" in max_levels:
                                                                        age_groups = {
                                                                            1: "LFA PRE Assistant",
                                                                            2: "LFA PRE Head",
                                                                            3: "LFA YOUTH Assistant",
                                                                            4: "LFA YOUTH Head",
                                                                            5: "LFA AMATEUR Assistant",
                                                                            6: "LFA AMATEUR Head",
                                                                            7: "LFA PRO Assistant",
                                                                            8: "LFA PRO Head"
                                                                        }
                                                                        level = max_levels["COACH"]
                                                                        badges.append(f"👨‍🏫 {age_groups.get(level, f'L{level}')}")

                                                                    if "INTERNSHIP" in max_levels:
                                                                        intern_emoji = {1: "🔰", 2: "📈", 3: "🎯", 4: "👑", 5: "🚀"}
                                                                        intern_names = {
                                                                            1: "Junior Intern",
                                                                            2: "Mid-level Intern",
                                                                            3: "Senior Intern",
                                                                            4: "Lead Intern",
                                                                            5: "Principal Intern"
                                                                        }
                                                                        level = max_levels["INTERNSHIP"]
                                                                        badges.append(f"{intern_emoji.get(level, '📚')} {intern_names.get(level, f'L{level}')}")

                                                                    st.markdown(f"**🏮 Licenses:** {' • '.join(badges)}")

                                                                    # Show ALL license details in expander if user wants to see
                                                                    with st.expander("View all license details"):
                                                                        for lic in licenses:
                                                                            spec_type = lic['specialization_type']
                                                                            current_level = lic['current_level']
                                                                            license_id = lic['license_id']

                                                                            # Format display based on specialization type
                                                                            if spec_type == "PLAYER":
                                                                                belt_emoji = {1: "🤍", 2: "💛", 3: "💚", 4: "💙", 5: "🤎", 6: "🩶", 7: "🖤", 8: "❤️"}
                                                                                st.markdown(f"{belt_emoji.get(current_level, '⚪')} Level {current_level}")
                                                                            elif spec_type == "COACH":
                                                                                age_groups = {1: "PRE Asst", 2: "PRE Head", 3: "YOUTH Asst", 4: "YOUTH Head",
                                                                                             5: "AMATEUR Asst", 6: "AMATEUR Head", 7: "PRO Asst", 8: "PRO Head"}
                                                                                st.markdown(f"👨‍🏫 {age_groups.get(current_level, f'Level {current_level}')}")
                                                                            elif spec_type == "INTERNSHIP":
                                                                                intern_emoji = {1: "🔰", 2: "📈", 3: "🎯", 4: "👑", 5: "🚀"}
                                                                                st.markdown(f"{intern_emoji.get(current_level, '📚')} Level {current_level}")
                                                                            else:
                                                                                st.markdown(f"**{spec_type}** Level {current_level}")
                                                                else:
                                                                    st.info("ℹ️ No licenses found")

                                                                st.markdown(f"**Availability Windows:** {len(avail_inst.get('availability_windows', []))}")

                                                                # Check if request already exists
                                                                existing_req_response = requests.get(
                                                                    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/semester/{semester['id']}",
                                                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                                    timeout=10
                                                                )

                                                                existing_requests = []
                                                                if existing_req_response.status_code == 200:
                                                                    all_requests = existing_req_response.json()
                                                                    existing_requests = [
                                                                        req for req in all_requests
                                                                        if req['instructor_id'] == avail_inst['instructor_id']
                                                                        and req['status'] == 'PENDING'
                                                                    ]

                                                                if existing_requests:
                                                                    st.warning(f"⚠️ PENDING request already sent to this instructor (Request #{existing_requests[0]['id']})")
                                                                else:
                                                                    request_message = st.text_area(
                                                                        "Message to instructor",
                                                                        value=f"Would you be available to teach {semester.get('specialization_type', '')} {semester.get('code', '')}?",
                                                                        key=f"msg_{semester['id']}_{avail_inst['instructor_id']}"
                                                                    )

                                                                    priority = st.slider(
                                                                        "Priority (0-10)",
                                                                        min_value=0,
                                                                        max_value=10,
                                                                        value=5,
                                                                        key=f"priority_{semester['id']}_{avail_inst['instructor_id']}"
                                                                    )

                                                                    if st.button(
                                                                        f"📨 Send Request to {avail_inst['instructor_name']}",
                                                                        key=f"send_req_{semester['id']}_{avail_inst['instructor_id']}",
                                                                        type="primary"
                                                                    ):
                                                                        # DEBUG LOG
                                                                        st.write(f"🔍 DEBUG: Button clicked! Sending request...")
                                                                        st.write(f"🔍 DEBUG: semester_id={semester['id']}, instructor_id={avail_inst['instructor_id']}")

                                                                        # Send assignment request
                                                                        try:
                                                                            req_response = requests.post(
                                                                                f"{API_BASE_URL}/api/v1/instructor-assignments/requests",
                                                                                headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                                                json={
                                                                                    "semester_id": semester['id'],
                                                                                    "instructor_id": avail_inst['instructor_id'],
                                                                                    "request_message": request_message,
                                                                                    "priority": priority
                                                                                },
                                                                                timeout=10
                                                                            )
                                                                            st.write(f"🔍 DEBUG: Response status: {req_response.status_code}")
                                                                        except Exception as e:
                                                                            st.error(f"❌ Exception during POST: {str(e)}")
                                                                            req_response = None

                                                                        if req_response and req_response.status_code == 201:
                                                                            st.success(f"✅ Assignment request sent to {avail_inst['instructor_name']}!")
                                                                            add_log(f"Sent assignment request for semester {semester['code']} to {avail_inst['instructor_name']}", "success")
                                                                            st.rerun()
                                                                        elif req_response and req_response.status_code == 409:
                                                                            st.error("❌ A pending request already exists for this semester/instructor")
                                                                        elif req_response:
                                                                            st.error(f"❌ Failed to send request: {req_response.text}")
                                                    else:
                                                        st.info(f"ℹ️ No instructors available for {time_period} {sem_year}")
                                                        st.caption("💡 Instructors set general availability (time period only). Location is specified when sending the assignment request.")
                                                else:
                                                    st.error(f"❌ Failed to fetch available instructors: {avail_response.status_code}")

                                            except Exception as e:
                                                st.error(f"❌ Error finding instructors: {str(e)}")
                                        else:
                                            st.warning("⚠️ Semester missing required fields (year/location/dates)")

                                    # DISPLAY AVAILABLE INSTRUCTORS FROM SESSION STATE (if exists)
                                    if st.session_state.get(f"avail_inst_{semester['id']}"):
                                        st.divider()
                                        st.markdown(f"**👨‍🏫 Available Instructors ({len(st.session_state[f'avail_inst_{semester['id']}'])})**")

                                        for avail_inst in st.session_state[f"avail_inst_{semester['id']}"]:
                                            with st.expander(f"👨‍🏫 {avail_inst['instructor_name']} ({avail_inst['instructor_email']})"):
                                                # Display licenses - show only HIGHEST level per type
                                                licenses = avail_inst.get('licenses', [])
                                                if licenses:
                                                    # Find highest level for each specialization type
                                                    max_levels = {}
                                                    for lic in licenses:
                                                        spec_type = lic['specialization_type']
                                                        current_level = lic['current_level']
                                                        if spec_type not in max_levels or current_level > max_levels[spec_type]:
                                                            max_levels[spec_type] = current_level

                                                    # Display as compact badges with ONLY highest level
                                                    badges = []

                                                    if "PLAYER" in max_levels:
                                                        belt_emoji = {1: "🤍", 2: "💛", 3: "💚", 4: "💙", 5: "🤎", 6: "🩶", 7: "🖤", 8: "❤️"}
                                                        belt_names = {
                                                            1: "Bamboo Student",
                                                            2: "Morning Dew",
                                                            3: "Flexible Reed",
                                                            4: "Sky River",
                                                            5: "Strong Root",
                                                            6: "Winter Moon",
                                                            7: "Midnight Guardian",
                                                            8: "Dragon Wisdom"
                                                        }
                                                        level = max_levels["PLAYER"]
                                                        badges.append(f"🥋 {belt_emoji.get(level, '⚪')} {belt_names.get(level, f'L{level}')}")

                                                    if "COACH" in max_levels:
                                                        age_groups = {
                                                            1: "LFA PRE Assistant",
                                                            2: "LFA PRE Head",
                                                            3: "LFA YOUTH Assistant",
                                                            4: "LFA YOUTH Head",
                                                            5: "LFA AMATEUR Assistant",
                                                            6: "LFA AMATEUR Head",
                                                            7: "LFA PRO Assistant",
                                                            8: "LFA PRO Head"
                                                        }
                                                        level = max_levels["COACH"]
                                                        badges.append(f"👨‍🏫 {age_groups.get(level, f'L{level}')}")

                                                    if "INTERNSHIP" in max_levels:
                                                        intern_emoji = {1: "🔰", 2: "📈", 3: "🎯", 4: "👑", 5: "🚀"}
                                                        intern_names = {
                                                            1: "Junior Intern",
                                                            2: "Mid-level Intern",
                                                            3: "Senior Intern",
                                                            4: "Lead Intern",
                                                            5: "Principal Intern"
                                                        }
                                                        level = max_levels["INTERNSHIP"]
                                                        badges.append(f"{intern_emoji.get(level, '📚')} {intern_names.get(level, f'L{level}')}")

                                                    st.markdown(f"**🏮 Licenses:** {' • '.join(badges)}")
                                                else:
                                                    st.info("ℹ️ No licenses found")

                                                st.markdown(f"**Availability Windows:** {len(avail_inst.get('availability_windows', []))}")

                                                # Check if request already exists
                                                existing_req_response = requests.get(
                                                    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/semester/{semester['id']}",
                                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                    timeout=10
                                                )

                                                existing_requests = []
                                                if existing_req_response.status_code == 200:
                                                    all_requests = existing_req_response.json()
                                                    existing_requests = [
                                                        req for req in all_requests
                                                        if req['instructor_id'] == avail_inst['instructor_id']
                                                        and req['status'] == 'PENDING'
                                                    ]

                                                if existing_requests:
                                                    st.warning(f"⚠️ PENDING request already sent to this instructor (Request #{existing_requests[0]['id']})")
                                                else:
                                                    request_message = st.text_area(
                                                        "Message to instructor",
                                                        value=f"Would you be available to teach {semester.get('specialization_type', '')} {semester.get('code', '')}?",
                                                        key=f"msg_{semester['id']}_{avail_inst['instructor_id']}"
                                                    )

                                                    priority = st.slider(
                                                        "Priority (0-10)",
                                                        min_value=0,
                                                        max_value=10,
                                                        value=5,
                                                        key=f"priority_{semester['id']}_{avail_inst['instructor_id']}"
                                                    )

                                                    if st.button(
                                                        f"📨 Send Request to {avail_inst['instructor_name']}",
                                                        key=f"send_req_{semester['id']}_{avail_inst['instructor_id']}",
                                                        type="primary"
                                                    ):
                                                        # DEBUG LOG
                                                        st.write(f"🔍 DEBUG: Button clicked! Sending request...")
                                                        st.write(f"🔍 DEBUG: semester_id={semester['id']}, instructor_id={avail_inst['instructor_id']}")

                                                        # Send assignment request
                                                        try:
                                                            req_response = requests.post(
                                                                f"{API_BASE_URL}/api/v1/instructor-assignments/requests",
                                                                headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                                json={
                                                                    "semester_id": semester['id'],
                                                                    "instructor_id": avail_inst['instructor_id'],
                                                                    "request_message": request_message,
                                                                    "priority": priority
                                                                },
                                                                timeout=10
                                                            )
                                                            st.write(f"🔍 DEBUG: Response status: {req_response.status_code}")
                                                        except Exception as e:
                                                            st.error(f"❌ Exception during POST: {str(e)}")
                                                            req_response = None

                                                        if req_response and req_response.status_code == 201:
                                                            st.success(f"✅ Assignment request sent to {avail_inst['instructor_name']}!")
                                                            add_log(f"Sent assignment request for semester {semester['code']} to {avail_inst['instructor_name']}", "success")
                                                            st.rerun()
                                                        elif req_response and req_response.status_code == 409:
                                                            st.error("❌ A pending request already exists for this semester/instructor")
                                                        elif req_response:
                                                            st.error(f"❌ Failed to send request: {req_response.text}")

                                with assign_col2:
                                    # Activation toggle
                                    st.markdown("**Activate Semester**")

                                    if not master_id:
                                        st.warning("⚠️ Cannot activate: No instructor assigned")
                                        st.caption("Please assign a master instructor first")
                                    else:
                                        if is_active:
                                            if st.button("⏸️ Deactivate Semester", key=f"deactivate_{semester['id']}", type="secondary"):
                                                update_response = requests.patch(
                                                    f"{API_BASE_URL}/api/v1/semesters/{semester['id']}",
                                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                    json={"is_active": False},
                                                    timeout=10
                                                )

                                                if update_response.status_code == 200:
                                                    st.success("✅ Semester deactivated!")
                                                    add_log(f"Deactivated semester {semester['code']}", "success")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Failed: {update_response.text}")
                                        else:
                                            if st.button("✅ Activate Semester", key=f"activate_{semester['id']}", type="primary"):
                                                update_response = requests.patch(
                                                    f"{API_BASE_URL}/api/v1/semesters/{semester['id']}",
                                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                    json={"is_active": True},
                                                    timeout=10
                                                )

                                                if update_response.status_code == 200:
                                                    st.success("✅ Semester activated!")
                                                    add_log(f"Activated semester {semester['code']}", "success")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Failed: {update_response.text}")

                                st.divider()

                                # Delete button (only if no sessions)
                                total_sessions = semester.get('total_sessions', 0)

                                if total_sessions == 0:
                                    st.warning("⚠️ This semester has no sessions and can be safely deleted")

                                    if st.button(f"🗑️ Delete Semester", key=f"delete_sem_{semester['id']}", type="secondary"):
                                        # Confirm deletion
                                        delete_response = requests.delete(
                                            f"{API_BASE_URL}/api/v1/semesters/{semester['id']}",
                                            headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                            timeout=10
                                        )

                                        if delete_response.status_code == 200:
                                            st.success(f"✅ Semester deleted successfully!")
                                            add_log(f"Deleted semester: {semester['code']}", "success")
                                            st.rerun()
                                        else:
                                            error_msg = delete_response.json().get('detail', 'Unknown error')
                                            st.error(f"❌ Failed to delete: {error_msg}")
                                            add_log(f"Failed to delete semester: {error_msg}", "error")
                                else:
                                    st.info(f"ℹ️ Cannot delete: This semester has **{total_sessions}** sessions")
                                    st.caption("Delete all sessions first to remove this semester")

                else:
                    st.error(f"❌ Failed to fetch semesters: {response.status_code}")
                    st.caption(f"Error: {response.text}")

            except Exception as e:
                st.error(f"❌ Error loading semesters: {str(e)}")

        # TAB 4: Instructor General Availability
        with tab4:
            st.markdown("### 👨‍🏫 Instructor General Availability")
            st.caption("📅 Mark when and where you are generally available to teach")
            st.info("💡 **NEW CONCEPT:** Just choose time periods + locations. Admin will send specific assignment requests later!")

            # Get all instructors
            instructors_response = requests.get(
                f"{API_BASE_URL}/api/v1/users/?role=instructor&limit=100",
                headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                timeout=10
            )

            if instructors_response.status_code != 200:
                st.error("❌ Failed to fetch instructors")
            else:
                instructors_data = instructors_response.json()
                instructors = instructors_data.get('users', []) if isinstance(instructors_data, dict) else instructors_data

                # Ensure instructors is a list
                if not isinstance(instructors, list):
                    st.error(f"❌ Invalid instructors data format: {type(instructors)}")
                    st.write(instructors_data)  # Debug output
                elif not instructors:
                    st.warning("⚠️ No instructors found in the system")
                else:
                    # Instructor selector
                    instructor_options = {f"{i['name']} ({i['email']})": i['id'] for i in instructors}
                    selected_instructor_label = st.selectbox(
                        "👨‍🏫 Select Instructor",
                        options=list(instructor_options.keys())
                    )
                    selected_instructor_id = instructor_options[selected_instructor_label]

                    st.divider()

                    # Fetch current availability windows
                    try:
                        windows_response = requests.get(
                            f"{API_BASE_URL}/api/v1/instructor-assignments/availability/instructor/{selected_instructor_id}",
                            headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                            timeout=10
                        )

                        if windows_response.status_code == 200:
                            windows = windows_response.json()

                            st.markdown("### 📋 Current Availability Windows")

                            if windows:
                                for window in windows:
                                    col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
                                    with col1:
                                        st.write(f"📅 **{window['year']}**")
                                    with col2:
                                        st.write(f"📆 **{window['time_period']}**")
                                    with col3:
                                        if window['is_available']:
                                            st.success("✅ Available")
                                        else:
                                            st.error("❌ Unavailable")
                                    with col4:
                                        if st.button("🗑️", key=f"delete_window_{window['id']}"):
                                            delete_response = requests.delete(
                                                f"{API_BASE_URL}/api/v1/instructor-assignments/availability/{window['id']}",
                                                headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                                timeout=10
                                            )
                                            if delete_response.status_code == 204:
                                                st.success("✅ Deleted!")
                                                st.rerun()
                                            else:
                                                st.error("❌ Delete failed")
                            else:
                                st.info("ℹ️ No availability windows set yet")

                            st.divider()

                            # Add new availability window
                            st.markdown("### ➕ Add New Availability Window")
                            st.caption("Mark when instructor is available - location will be specified in assignment requests")

                            col1, col2 = st.columns(2)

                            with col1:
                                current_year = datetime.now().year
                                current_month = datetime.now().month

                                if current_month == 12:
                                    year_options = [current_year + 1, current_year + 2, current_year + 3]
                                else:
                                    year_options = [current_year, current_year + 1, current_year + 2]

                                new_year = st.selectbox(
                                    "📅 Year",
                                    options=year_options,
                                    index=0,
                                    key="new_window_year"
                                )

                            with col2:
                                time_periods = ['Q1', 'Q2', 'Q3', 'Q4']
                                period_labels = {
                                    'Q1': 'Q1 (Jan-Mar)',
                                    'Q2': 'Q2 (Apr-Jun)',
                                    'Q3': 'Q3 (Jul-Sep)',
                                    'Q4': 'Q4 (Oct-Dec)'
                                }
                                new_period_label = st.selectbox(
                                    "📆 Time Period",
                                    options=[period_labels[p] for p in time_periods],
                                    key="new_window_period"
                                )
                                # Extract Q1, Q2, Q3, or Q4 from label
                                new_period = [k for k, v in period_labels.items() if v == new_period_label][0]

                            new_notes = st.text_area(
                                "📝 Notes (optional)",
                                placeholder="Any special notes about this availability...",
                                key="new_window_notes"
                            )

                            if st.button("➕ Add Availability Window", type="primary"):
                                create_response = requests.post(
                                    f"{API_BASE_URL}/api/v1/instructor-assignments/availability",
                                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                    json={
                                        "instructor_id": selected_instructor_id,
                                        "year": new_year,
                                        "time_period": new_period,
                                        "is_available": True,
                                        "notes": new_notes if new_notes else None
                                    },
                                    timeout=10
                                )

                                if create_response.status_code == 201:
                                    st.success("✅ Availability window added!")
                                    st.rerun()
                                elif create_response.status_code == 409:
                                    st.error("❌ This availability window already exists!")
                                else:
                                    st.error(f"❌ Failed to add window: {create_response.text}")

                        else:
                            st.error(f"❌ Failed to fetch availability windows: {windows_response.status_code}")

                    except Exception as e:
                        st.error(f"❌ Error loading availability: {str(e)}")

        # TAB 5: Campus Calendar View
        with tab5:
            st.markdown("### 📅 Campus Calendar - Sessions by Location")
            st.caption("View all sessions grouped by country, region, and campus")

            # Fetch all locations
            try:
                locations_response = requests.get(
                    f"{API_BASE_URL}/api/v1/admin/locations/",
                    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                    params={"include_inactive": False},
                    timeout=10
                )

                if locations_response.status_code != 200:
                    st.error(f"❌ Failed to fetch locations: {locations_response.status_code}")
                else:
                    all_locations = locations_response.json()

                    if not all_locations:
                        st.info("ℹ️ No active locations found. Please create locations in Tab 1 first.")
                    else:
                        # Fetch all sessions
                        sessions_response = requests.get(
                            f"{API_BASE_URL}/api/v1/sessions",
                            headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                            params={
                                "size": 100,  # Maximum allowed by API
                                "specialization_filter": False  # Admin sees all sessions regardless of specialization
                            },
                            timeout=10
                        )

                        if sessions_response.status_code != 200:
                            st.error(f"❌ Failed to fetch sessions: {sessions_response.status_code}")
                            if sessions_response.status_code == 422:
                                st.error(f"Response: {sessions_response.text}")
                        else:
                            sessions_data = sessions_response.json()

                            # Handle SessionList response format
                            if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
                                all_sessions = sessions_data['sessions']
                            else:
                                all_sessions = sessions_data if isinstance(sessions_data, list) else []

                            # Fetch semesters ONCE (not inside location loop)
                            semesters_response = requests.get(
                                f"{API_BASE_URL}/api/v1/semesters",
                                headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
                                timeout=10
                            )

                            all_semesters = []
                            semester_lookup = {}
                            if semesters_response.status_code == 200:
                                semesters_data = semesters_response.json()
                                # Handle SemesterList response format
                                if isinstance(semesters_data, dict) and 'semesters' in semesters_data:
                                    all_semesters = semesters_data['semesters']
                                else:
                                    all_semesters = semesters_data if isinstance(semesters_data, list) else []
                                semester_lookup = {s['id']: s for s in all_semesters if isinstance(s, dict)}
                            else:
                                st.error(f"❌ Failed to fetch semesters: {semesters_response.status_code}")
                                st.code(f"Response: {semesters_response.text}")

                            # Specialization display names
                            spec_display_names = {
                                'LFA_PLAYER_PRE': '⚽ LFA Player - PRE Academy',
                                'LFA_PLAYER_YOUTH': '⚽ LFA Player - YOUTH Academy',
                                'LFA_PLAYER_AMATEUR': '⚽ LFA Player - AMATEUR Team',
                                'LFA_PLAYER_PRO': '⚽ LFA Player - PRO Team',
                                'INTERNSHIP': '💼 LFA Internship Program',
                                'GANCUJU': '🥋 Gāncùjū'
                            }

                            # Build hierarchical structure: Country → Campus → Specialization → Semester → Sessions
                            countries = {}

                            for session in all_sessions:
                                if isinstance(session, dict):
                                    semester_id = session.get('semester_id')
                                    semester = semester_lookup.get(semester_id, {})

                                    # Get location info from semester
                                    semester_city = semester.get('location_city', '')
                                    semester_venue = semester.get('location_venue', '')

                                    # Match to location for country
                                    matched_location = None
                                    for loc in all_locations:
                                        loc_city = loc.get('city', '')
                                        loc_venue = loc.get('venue', '')

                                        # Match by city or venue
                                        if (semester_city == loc_city) or (semester_venue == loc_venue and loc_venue):
                                            matched_location = loc
                                            break

                                    if matched_location:
                                        country = matched_location.get('country', 'Unknown Country')
                                        campus_venue = matched_location.get('venue', 'Unknown Campus')
                                        spec_type = semester.get('specialization_type', 'UNKNOWN')
                                        spec_display = spec_display_names.get(spec_type, spec_type)

                                        # Country level
                                        if country not in countries:
                                            countries[country] = {}

                                        # Campus level
                                        if campus_venue not in countries[country]:
                                            countries[country][campus_venue] = {
                                                'location': matched_location,
                                                'specializations': {}
                                            }

                                        # Specialization level
                                        if spec_type not in countries[country][campus_venue]['specializations']:
                                            countries[country][campus_venue]['specializations'][spec_type] = {
                                                'spec_display': spec_display,
                                                'semesters': {}
                                            }

                                        # Semester level
                                        if semester_id not in countries[country][campus_venue]['specializations'][spec_type]['semesters']:
                                            countries[country][campus_venue]['specializations'][spec_type]['semesters'][semester_id] = {
                                                'semester': semester,
                                                'sessions': []
                                            }

                                        # Add session
                                        countries[country][campus_venue]['specializations'][spec_type]['semesters'][semester_id]['sessions'].append(session)

                            # Display hierarchy: Country → Campus → Specialization → Semester → Sessions
                            for country in sorted(countries.keys()):
                                st.markdown(f"## 🌍 {country.upper()}")

                                for campus_venue in sorted(countries[country].keys()):
                                    campus_data = countries[country][campus_venue]
                                    location = campus_data['location']

                                    # Count total sessions for this campus
                                    total_campus_sessions = sum(
                                        len(sem_data['sessions'])
                                        for spec_data in campus_data['specializations'].values()
                                        for sem_data in spec_data['semesters'].values()
                                    )

                                    st.markdown(f"### 📍 {campus_venue.upper()}")
                                    st.caption(f"{location.get('city', 'N/A')} • {location.get('address', 'N/A')} • {total_campus_sessions} sessions")
                                    st.divider()

                                    # Specialization level
                                    for spec_type in sorted(campus_data['specializations'].keys()):
                                        spec_data = campus_data['specializations'][spec_type]
                                        spec_display = spec_data['spec_display']

                                        # Count sessions for this specialization
                                        total_spec_sessions = sum(
                                            len(sem_data['sessions'])
                                            for sem_data in spec_data['semesters'].values()
                                        )

                                        with st.expander(f"{spec_display} ({total_spec_sessions} sessions)", expanded=False):
                                            # Sort semesters by start_date
                                            sorted_semesters = sorted(
                                                spec_data['semesters'].items(),
                                                key=lambda x: x[1]['semester'].get('start_date', '')
                                            )

                                            for semester_id, semester_data in sorted_semesters:
                                                semester = semester_data['semester']
                                                sessions = semester_data['sessions']

                                                semester_name = semester.get('name', 'N/A')
                                                start_date = semester.get('start_date', 'N/A')
                                                end_date = semester.get('end_date', 'N/A')

                                                st.markdown(f"#### 📚 {semester_name}")
                                                st.caption(f"Period: {start_date} → {end_date} • {len(sessions)} sessions")

                                                # Sort sessions by date
                                                sessions.sort(key=lambda x: x.get('date_start', ''))

                                                # Display sessions
                                                for session in sessions:
                                                    session_title = session.get('title', 'Untitled Session')
                                                    session_type = session.get('session_type', 'on_site')
                                                    date_start = session.get('date_start', '')
                                                    date_end = session.get('date_end', '')
                                                    capacity = session.get('capacity', 0)
                                                    credit_cost = session.get('credit_cost', 1)

                                                    # Format dates
                                                    try:
                                                        start_dt = dt.fromisoformat(date_start.replace('Z', '+00:00'))
                                                        end_dt = dt.fromisoformat(date_end.replace('Z', '+00:00'))
                                                        date_display = start_dt.strftime('%Y-%m-%d %H:%M')
                                                        time_range = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                                                    except:
                                                        date_display = str(date_start)
                                                        time_range = "N/A"

                                                    # Session type icon
                                                    type_icons = {
                                                        'on_site': '🏟️',
                                                        'virtual': '💻',
                                                        'hybrid': '🔀'
                                                    }
                                                    type_icon = type_icons.get(session_type, '📍')

                                                    with st.container():
                                                        col1, col2, col3 = st.columns([3, 2, 1])

                                                        with col1:
                                                            st.markdown(f"**{type_icon} {session_title}**")

                                                        with col2:
                                                            st.markdown(f"📅 {date_display}")
                                                            st.caption(f"⏰ {time_range}")

                                                        with col3:
                                                            st.markdown(f"👥 {capacity}")
                                                            st.caption(f"💳 {credit_cost} cr")

                                                st.divider()

            except Exception as e:
                st.error(f"❌ Error loading campus calendar: {str(e)}")

elif st.session_state.active_workflow == "instructor":
    # ========================================================================
    # INSTRUCTOR DASHBOARD
    # ========================================================================

    st.header("👨‍🏫 Instructor Dashboard")
    st.caption("Manage Your Availability • View Assignment Requests")
    st.divider()

    if not st.session_state.instructor_token:
        st.warning("⚠️ Please log in as Instructor to access this dashboard")
        st.info("📝 Use the Instructor Login tab in the sidebar")
    else:
        # Get current instructor info
        success, user_info = get_user_info(st.session_state.instructor_token)

        if not success:
            st.error("❌ Failed to get user info")
        else:
            instructor_id = user_info.get('id')
            instructor_name = user_info.get('name', 'Instructor')

            st.success(f"✅ Logged in as: **{instructor_name}**")
            st.divider()

            # Tab structure for instructor
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 My Availability", "📬 Assignment Requests", "💰 My Credits", "📚 My Sessions", "📅 Campus Calendar"])

            # TAB 1: My Availability
            with tab1:
                st.markdown("### 📅 My Availability Windows")
                st.caption("Set when you are generally available to teach (location comes from assignment requests)")

                # Fetch current availability windows
                try:
                    windows_response = requests.get(
                        f"{API_BASE_URL}/api/v1/instructor-assignments/availability/instructor/{instructor_id}",
                        headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                        timeout=10
                    )

                    if windows_response.status_code == 200:
                        windows = windows_response.json()

                        st.markdown("### 📋 Current Availability Windows")

                        if windows:
                            for window in windows:
                                col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
                                with col1:
                                    st.write(f"📅 **{window['year']}**")
                                with col2:
                                    st.write(f"📆 **{window['time_period']}**")
                                with col3:
                                    if window['is_available']:
                                        st.success("✅ Available")
                                    else:
                                        st.error("❌ Unavailable")
                                with col4:
                                    if st.button("🗑️", key=f"delete_window_{window['id']}"):
                                        delete_response = requests.delete(
                                            f"{API_BASE_URL}/api/v1/instructor-assignments/availability/{window['id']}",
                                            headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                            timeout=10
                                        )
                                        if delete_response.status_code == 204:
                                            st.success("✅ Deleted!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Delete failed")
                        else:
                            st.info("ℹ️ No availability windows set yet")

                        st.divider()

                        # Add new availability window
                        st.markdown("### ➕ Add New Availability Window")
                        st.caption("Mark when you're available - location will be specified in assignment requests")

                        col1, col2 = st.columns(2)

                        with col1:
                            current_year = datetime.now().year
                            current_month = datetime.now().month

                            if current_month == 12:
                                year_options = [current_year + 1, current_year + 2, current_year + 3]
                            else:
                                year_options = [current_year, current_year + 1, current_year + 2]

                            new_year = st.selectbox(
                                "📅 Year",
                                options=year_options,
                                index=0,
                                key="instructor_new_window_year"
                            )

                        with col2:
                            time_periods = ['Q1', 'Q2', 'Q3', 'Q4']
                            period_labels = {
                                'Q1': 'Q1 (Jan-Mar)',
                                'Q2': 'Q2 (Apr-Jun)',
                                'Q3': 'Q3 (Jul-Sep)',
                                'Q4': 'Q4 (Oct-Dec)'
                            }
                            new_period_label = st.selectbox(
                                "📆 Time Period",
                                options=[period_labels[p] for p in time_periods],
                                key="instructor_new_window_period"
                            )
                            new_period = [k for k, v in period_labels.items() if v == new_period_label][0]

                        new_notes = st.text_area(
                            "📝 Notes (optional)",
                            placeholder="Any special notes about this availability...",
                            key="instructor_new_window_notes"
                        )

                        if st.button("➕ Add Availability Window", type="primary", key="instructor_add_window"):
                            create_response = requests.post(
                                f"{API_BASE_URL}/api/v1/instructor-assignments/availability",
                                headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                json={
                                    "instructor_id": instructor_id,
                                    "year": new_year,
                                    "time_period": new_period,
                                    "is_available": True,
                                    "notes": new_notes if new_notes else None
                                    },
                                timeout=10
                            )

                            if create_response.status_code == 201:
                                st.success("✅ Availability window added!")
                                st.rerun()
                            elif create_response.status_code == 409:
                                st.error("❌ This availability window already exists!")
                            else:
                                st.error(f"❌ Failed to add window: {create_response.text}")

                    else:
                        st.error(f"❌ Failed to fetch availability windows: {windows_response.status_code}")

                except Exception as e:
                    st.error(f"❌ Error loading availability: {str(e)}")

            # TAB 2: Assignment Requests Inbox
            with tab2:
                st.markdown("### 📬 Assignment Request Inbox")
                st.caption("View and respond to assignment requests from admins")

                # Filter UI (before API call)
                st.markdown("#### 🔍 Filter Requests")

                # Fetch instructor's teachable specializations dynamically
                teachable_specs = []
                try:
                    teachable_response = requests.get(
                        f"{API_BASE_URL}/api/v1/licenses/instructor/{instructor_id}/teachable-specializations",
                        headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                        timeout=5
                    )
                    if teachable_response.status_code == 200:
                        teachable_specs = teachable_response.json()
                except Exception as e:
                    st.warning(f"Could not fetch teachable specializations: {e}")

                # First row: Status, Specialization, Age Group
                filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)

                with filter_row1_col1:
                    status_filter = st.selectbox(
                        "Status",
                        options=["All", "PENDING", "ACCEPTED", "DECLINED", "CANCELLED"],
                        key="filter_status"
                    )

                with filter_row1_col2:
                    # Dynamic specialization dropdown based on instructor's licenses
                    spec_options = ["All"] + teachable_specs
                    specialization_filter = st.selectbox(
                        "Specialization",
                        options=spec_options,
                        key="filter_specialization",
                        help="Based on your active licenses"
                    )

                with filter_row1_col3:
                    age_group_filter = st.selectbox(
                        "Age Group",
                        options=["All", "PRE", "YOUTH", "ADULT"],
                        key="filter_age_group"
                    )

                # Second row: Location, Priority
                filter_row2_col1, filter_row2_col2, filter_row2_col3 = st.columns(3)

                with filter_row2_col1:
                    location_filter = st.selectbox(
                        "Location",
                        options=["All", "Budapest", "Budaörs"],
                        key="filter_location"
                    )

                with filter_row2_col2:
                    priority_filter = st.selectbox(
                        "Min Priority",
                        options=["All", "5", "6", "7", "8", "9", "10"],
                        key="filter_priority"
                    )

                st.divider()

                # Build API query parameters
                params = {}
                if status_filter != "All":
                    params["status_filter"] = status_filter
                if specialization_filter != "All":
                    params["specialization_type"] = specialization_filter
                if age_group_filter != "All":
                    params["age_group"] = age_group_filter
                if location_filter != "All":
                    params["location_city"] = location_filter
                if priority_filter != "All":
                    params["priority_min"] = int(priority_filter)

                # Fetch assignment requests with filters
                try:
                    requests_response = requests.get(
                        f"{API_BASE_URL}/api/v1/instructor-assignments/requests/instructor/{instructor_id}",
                        headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                        params=params,
                        timeout=10
                    )

                    if requests_response.status_code == 200:
                        filtered_requests = requests_response.json()

                        if filtered_requests:
                            st.markdown(f"**Total Requests:** {len(filtered_requests)}")
                            st.divider()

                            # Display requests
                            for req in filtered_requests:
                                with st.expander(f"📋 Request #{req['id']} - **{req['status']}** - Semester ID: {req['semester_id']}"):
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        st.markdown(f"**Semester ID:** {req['semester_id']}")
                                        st.markdown(f"**Status:** {req['status']}")
                                        st.markdown(f"**Created:** {req['created_at'][:10]}")

                                    with col2:
                                        if req['request_message']:
                                            st.markdown(f"**Admin Message:**")
                                            st.info(req['request_message'])

                                        if req['response_message']:
                                            st.markdown(f"**Your Response:**")
                                            st.success(req['response_message'])

                                    # Actions for PENDING requests
                                    if req['status'] == "PENDING":
                                        st.divider()
                                        st.markdown("### 🎯 Action Required")

                                        action_col1, action_col2 = st.columns(2)

                                        with action_col1:
                                            response_message_accept = st.text_area(
                                                "Optional message (for accepting)",
                                                placeholder="I'm happy to teach this semester!",
                                                key=f"accept_msg_{req['id']}"
                                            )

                                            if st.button(f"✅ Accept Request", type="primary", key=f"accept_{req['id']}"):
                                                accept_response = requests.patch(
                                                    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/{req['id']}/accept",
                                                    headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                                    json={"response_message": response_message_accept if response_message_accept else None},
                                                    timeout=10
                                                )

                                                if accept_response.status_code == 200:
                                                    st.success("✅ Request accepted! You are now assigned to this semester.")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Failed to accept: {accept_response.text}")

                                        with action_col2:
                                            response_message_decline = st.text_area(
                                                "Reason for declining (required)",
                                                placeholder="I'm not available for this period...",
                                                key=f"decline_msg_{req['id']}"
                                            )

                                            if st.button(f"❌ Decline Request", key=f"decline_{req['id']}"):
                                                if not response_message_decline:
                                                    st.error("❌ Please provide a reason for declining")
                                                else:
                                                    decline_response = requests.patch(
                                                        f"{API_BASE_URL}/api/v1/instructor-assignments/requests/{req['id']}/decline",
                                                        headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                                        json={"response_message": response_message_decline},
                                                        timeout=10
                                                    )

                                                    if decline_response.status_code == 200:
                                                        st.success("✅ Request declined")
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Failed to decline: {decline_response.text}")
                        else:
                            st.info("ℹ️ No assignment requests yet")

                    else:
                        st.error(f"❌ Failed to fetch assignment requests: {requests_response.status_code}")

                except Exception as e:
                    st.error(f"❌ Error loading assignment requests: {str(e)}")

            # TAB 3: My Credits
            with tab3:
                st.markdown("### 💰 My Credit Balance & Transaction History")
                st.caption("View your credit balance and all credit transactions")

                # Show current credit balance
                credit_balance = user_info.get('credit_balance', 0)
                st.metric("Current Credit Balance", f"{credit_balance} credits")

                st.divider()

                # Display transaction history using the helper function
                display_credit_transactions(st.session_state.instructor_token, credit_balance)

            # TAB 4: My Sessions (Master Instructor Only)
            with tab4:
                st.markdown("### 📚 Session Management")
                st.caption("Manage sessions for semesters where you are the master instructor")

                # Fetch semesters where instructor is master instructor
                try:
                    semesters_response = requests.get(
                        f"{API_BASE_URL}/api/v1/semesters",
                        headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                        timeout=10
                    )

                    if semesters_response.status_code == 200:
                        all_semesters_data = semesters_response.json()

                        # Handle both list and dict responses
                        if isinstance(all_semesters_data, dict):
                            all_semesters = all_semesters_data.get('semesters', [])
                        else:
                            all_semesters = all_semesters_data

                        # Filter semesters where this instructor is master instructor (with type checking)
                        my_semesters = [s for s in all_semesters if isinstance(s, dict) and s.get('master_instructor_id') == instructor_id]

                        if not my_semesters:
                            st.info("ℹ️ You are not assigned as master instructor for any semester yet")
                            st.caption("Accept an assignment request to become a master instructor")
                        else:
                            st.success(f"✅ You are master instructor for **{len(my_semesters)}** semester(s)")

                            # 🔍 PERSISTENT DEBUG: Show last save attempt result
                            if 'last_save_attempt' in st.session_state and st.session_state.last_save_attempt:
                                attempt = st.session_state.last_save_attempt
                                if attempt.get('success'):
                                    st.success(f"✅ Last save successful - Session {attempt.get('session_id')} updated!")
                                    st.json({"saved_values": {
                                        "credit_cost": attempt.get('credit_cost'),
                                        "capacity": attempt.get('capacity'),
                                        "timestamp": attempt.get('timestamp')
                                    }})
                                elif 'error' in attempt:
                                    st.error(f"❌ Last save FAILED - Session {attempt.get('session_id')}")
                                    st.error(f"Error: {attempt.get('error')}")
                                    st.json({"attempted_values": {
                                        "credit_cost": attempt.get('credit_cost'),
                                        "capacity": attempt.get('capacity'),
                                        "timestamp": attempt.get('timestamp')
                                    }})

                                # Clear button
                                if st.button("🗑️ Clear Debug Info", key="clear_debug_info"):
                                    st.session_state.last_save_attempt = {}
                                    st.rerun()

                            # Semester selector
                            semester_options = {f"{s['name']} ({s['specialization_type']})": s['id'] for s in my_semesters}
                            selected_semester_label = st.selectbox(
                                "Select Semester",
                                options=list(semester_options.keys()),
                                key="session_mgmt_semester"
                            )

                            if selected_semester_label:
                                selected_semester_id = semester_options[selected_semester_label]
                                selected_semester = next(s for s in my_semesters if s['id'] == selected_semester_id)

                                st.divider()

                                # Show semester details
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Specialization", selected_semester.get('specialization_type', 'N/A'))
                                with col2:
                                    st.metric("Age Group", selected_semester.get('age_group', 'N/A'))
                                with col3:
                                    st.metric("Location", selected_semester.get('location', 'N/A'))

                                st.divider()

                                # Fetch sessions for this semester
                                try:
                                    # 🔧 FIX: Use timestamp to FORCE fresh data - no cache!
                                    cache_bust = int(time.time() * 1000)  # milliseconds timestamp

                                    # 🔍 DEBUG: Verify we're fetching fresh data
                                    print(f"🟢 FETCHING SESSIONS - semester_id={selected_semester_id}, cache_bust={cache_bust}")

                                    sessions_response = requests.get(
                                        f"{API_BASE_URL}/api/v1/sessions",
                                        params={
                                            "semester_id": selected_semester_id,
                                            "_cache_bust": cache_bust  # Unique timestamp every time!
                                        },
                                        headers={
                                            "Authorization": f"Bearer {st.session_state.instructor_token}",
                                            "Cache-Control": "no-cache, no-store, must-revalidate",  # Disable ALL caching
                                            "Pragma": "no-cache",
                                            "Expires": "0"
                                        },
                                        timeout=10
                                    )

                                    # 🔍 DEBUG: Log what we got
                                    if sessions_response.status_code == 200:
                                        temp_data = sessions_response.json()
                                        temp_sessions = temp_data.get('sessions', []) if isinstance(temp_data, dict) else temp_data
                                        print(f"🟢 RECEIVED {sessions_response.status_code} - {len(temp_sessions)} sessions")
                                        # Log credit_cost of first session for debugging
                                        if temp_sessions:
                                            print(f"   First session: id={temp_sessions[0].get('id')}, title={temp_sessions[0].get('title')}, credit_cost={temp_sessions[0].get('credit_cost')}")

                                    if sessions_response.status_code == 200:
                                        sessions_data = sessions_response.json()

                                        # Handle SessionList response format
                                        if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
                                            sessions = sessions_data['sessions']
                                        else:
                                            sessions = sessions_data if isinstance(sessions_data, list) else []

                                        # Create new session section
                                        with st.expander("➕ Create New Session", expanded=False):
                                            st.markdown("#### Session Details")

                                            # Parse semester dates for default values
                                            semester_start = dt.fromisoformat(selected_semester['start_date']) if isinstance(selected_semester.get('start_date'), str) else selected_semester.get('start_date')
                                            semester_end = dt.fromisoformat(selected_semester['end_date']) if isinstance(selected_semester.get('end_date'), str) else selected_semester.get('end_date')

                                            col1, col2 = st.columns(2)
                                            with col1:
                                                new_session_title = st.text_input("Title", key="new_session_title")
                                                new_session_date_start = st.datetime_input(
                                                    "Start Date/Time",
                                                    value=semester_start,
                                                    min_value=semester_start,
                                                    max_value=semester_end,
                                                    key="new_session_date_start"
                                                )

                                            with col2:
                                                new_session_description = st.text_area("Description", key="new_session_description")
                                                new_session_date_end = st.datetime_input(
                                                    "End Date/Time",
                                                    value=semester_start,
                                                    min_value=semester_start,
                                                    max_value=semester_end,
                                                    key="new_session_date_end"
                                                )

                                            col3, col4, col5 = st.columns(3)
                                            with col3:
                                                new_session_type = st.selectbox(
                                                    "Session Type",
                                                    options=["on_site", "virtual", "hybrid"],
                                                    key="new_session_type"
                                                )

                                            with col4:
                                                new_session_capacity = st.number_input(
                                                    "Capacity",
                                                    min_value=1,
                                                    max_value=100,
                                                    value=20,
                                                    key="new_session_capacity"
                                                )

                                            with col5:
                                                new_session_credit_cost = st.number_input(
                                                    "💳 Credit Cost",
                                                    min_value=0,
                                                    max_value=10,
                                                    value=1,
                                                    help="Standard: 1 credit, Workshops: 2+ credits, Promo: 0 credits",
                                                    key="new_session_credit_cost"
                                                )

                                            if new_session_type in ["on_site", "hybrid"]:
                                                # Session automatically inherits semester location
                                                semester_location_city = selected_semester.get('location_city', '')
                                                semester_location_venue = selected_semester.get('location_venue', '')
                                                semester_location_address = selected_semester.get('location_address', '')

                                                # Build full location string from semester data
                                                location_parts = []
                                                if semester_location_venue:
                                                    location_parts.append(semester_location_venue)
                                                if semester_location_city:
                                                    location_parts.append(semester_location_city)
                                                if semester_location_address:
                                                    location_parts.append(semester_location_address)

                                                semester_full_location = ", ".join(location_parts) if location_parts else "Budapest"

                                                # Display as read-only info (inherited from semester)
                                                st.info(f"📍 Location (from semester): **{semester_full_location}**")
                                                new_session_location = semester_full_location
                                            else:
                                                new_session_location = None

                                            if new_session_type == "virtual":
                                                new_session_meeting_link = st.text_input("Meeting Link", key="new_session_meeting_link")
                                            else:
                                                new_session_meeting_link = None

                                            if st.button("✅ Create Session", key="create_session_btn"):
                                                if not new_session_title:
                                                    st.error("❌ Title is required")
                                                else:
                                                    # Create session payload
                                                    session_payload = {
                                                        "title": new_session_title,
                                                        "description": new_session_description,
                                                        "date_start": new_session_date_start.isoformat(),
                                                        "date_end": new_session_date_end.isoformat(),
                                                        "session_type": new_session_type,
                                                        "capacity": new_session_capacity,
                                                        "semester_id": selected_semester_id,
                                                        "instructor_id": instructor_id,
                                                        "location": new_session_location,
                                                        "meeting_link": new_session_meeting_link,
                                                        "credit_cost": new_session_credit_cost
                                                    }

                                                    try:
                                                        create_response = requests.post(
                                                            f"{API_BASE_URL}/api/v1/sessions",
                                                            json=session_payload,
                                                            headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                                            timeout=10
                                                        )

                                                        if create_response.status_code == 200:
                                                            st.success("✅ Session created successfully!")
                                                            st.rerun()
                                                        else:
                                                            st.error(f"❌ Failed to create session: {create_response.status_code}")
                                                            st.json(create_response.json())
                                                    except Exception as e:
                                                        st.error(f"❌ Error: {str(e)}")

                                        st.divider()

                                        # List existing sessions
                                        st.markdown(f"### 📋 Existing Sessions ({len(sessions)})")

                                        if not sessions:
                                            st.info("ℹ️ No sessions created yet for this semester")
                                        else:
                                            for session in sessions:
                                                session_id = session['id']
                                                with st.expander(f"📅 {session['title']} - {session.get('date_start', 'N/A')[:10]}"):
                                                    # Edit mode toggle
                                                    edit_key = f"edit_mode_{session_id}"
                                                    if edit_key not in st.session_state:
                                                        st.session_state[edit_key] = False

                                                    # Action buttons at top
                                                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 8])
                                                    with btn_col1:
                                                        if not st.session_state[edit_key]:
                                                            if st.button("✏️ Edit", key=f"edit_btn_{session_id}"):
                                                                st.session_state[edit_key] = True
                                                                st.rerun()
                                                        else:
                                                            if st.button("❌ Cancel", key=f"cancel_btn_{session_id}"):
                                                                st.session_state[edit_key] = False
                                                                st.rerun()

                                                    with btn_col2:
                                                        if st.button("🗑️ Delete", key=f"delete_session_{session_id}"):
                                                            try:
                                                                delete_response = requests.delete(
                                                                    f"{API_BASE_URL}/api/v1/sessions/{session_id}",
                                                                    headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                                                    timeout=10
                                                                )

                                                                if delete_response.status_code == 200:
                                                                    st.success("✅ Session deleted!")
                                                                    st.rerun()
                                                                else:
                                                                    st.error(f"❌ Delete failed: {delete_response.status_code}")
                                                                    st.json(delete_response.json())
                                                            except Exception as e:
                                                                st.error(f"❌ Error: {str(e)}")

                                                    st.divider()

                                                    # EDIT MODE
                                                    if st.session_state[edit_key]:
                                                        st.markdown("#### ✏️ Edit Session")

                                                        # Parse current dates
                                                        current_start = dt.fromisoformat(session['date_start'].replace('Z', '+00:00'))
                                                        current_end = dt.fromisoformat(session['date_end'].replace('Z', '+00:00'))

                                                        edit_col1, edit_col2 = st.columns(2)
                                                        with edit_col1:
                                                            edit_title = st.text_input(
                                                                "Title",
                                                                value=session.get('title', ''),
                                                                key=f"edit_title_{session_id}"
                                                            )
                                                            edit_date_start = st.datetime_input(
                                                                "Start Date/Time",
                                                                value=current_start,
                                                                key=f"edit_date_start_{session_id}"
                                                            )

                                                        with edit_col2:
                                                            edit_description = st.text_area(
                                                                "Description",
                                                                value=session.get('description', ''),
                                                                key=f"edit_description_{session_id}"
                                                            )
                                                            edit_date_end = st.datetime_input(
                                                                "End Date/Time",
                                                                value=current_end,
                                                                key=f"edit_date_end_{session_id}"
                                                            )

                                                        edit_col3, edit_col4, edit_col5 = st.columns(3)
                                                        with edit_col3:
                                                            edit_type = st.selectbox(
                                                                "Session Type",
                                                                options=["on_site", "virtual", "hybrid"],
                                                                index=["on_site", "virtual", "hybrid"].index(session.get('session_type', 'on_site')),
                                                                key=f"edit_type_{session_id}"
                                                            )

                                                        with edit_col4:
                                                            edit_capacity = st.number_input(
                                                                "Capacity",
                                                                min_value=1,
                                                                max_value=100,
                                                                value=session.get('capacity', 20),
                                                                key=f"edit_capacity_{session_id}"
                                                            )

                                                        with edit_col5:
                                                            edit_credit_cost = st.number_input(
                                                                "💳 Credit Cost",
                                                                min_value=0,
                                                                max_value=10,
                                                                value=session.get('credit_cost', 1),
                                                                key=f"edit_credit_cost_{session_id}"
                                                            )

                                                        # 🔍 REAL-TIME DEBUG: Show current values BEFORE save
                                                        st.warning(f"🔍 DEBUG - Current values: capacity={edit_capacity}, credit_cost={edit_credit_cost}")

                                                        # Location and meeting link
                                                        if edit_type in ["on_site", "hybrid"]:
                                                            # Session automatically inherits semester location
                                                            semester_location_city = selected_semester.get('location_city', '')
                                                            semester_location_venue = selected_semester.get('location_venue', '')
                                                            semester_location_address = selected_semester.get('location_address', '')

                                                            # Build full location string from semester data
                                                            location_parts = []
                                                            if semester_location_venue:
                                                                location_parts.append(semester_location_venue)
                                                            if semester_location_city:
                                                                location_parts.append(semester_location_city)
                                                            if semester_location_address:
                                                                location_parts.append(semester_location_address)

                                                            semester_full_location = ", ".join(location_parts) if location_parts else "Budapest"

                                                            # Display as read-only info (inherited from semester)
                                                            st.info(f"📍 Location (from semester): **{semester_full_location}**")
                                                            edit_location = semester_full_location
                                                        else:
                                                            edit_location = None

                                                        if edit_type == "virtual":
                                                            edit_meeting_link = st.text_input(
                                                                "Meeting Link",
                                                                value=session.get('meeting_link', ''),
                                                                key=f"edit_meeting_link_{session_id}"
                                                            )
                                                        else:
                                                            edit_meeting_link = None

                                                        if st.button("💾 Save Changes", key=f"save_btn_{session_id}", type="primary"):
                                                            # 🔍 CRITICAL DEBUG: Store attempt in session_state for persistence
                                                            if 'last_save_attempt' not in st.session_state:
                                                                st.session_state.last_save_attempt = {}

                                                            st.session_state.last_save_attempt = {
                                                                'session_id': session_id,
                                                                'credit_cost': int(edit_credit_cost),
                                                                'capacity': int(edit_capacity),
                                                                'timestamp': datetime.now().isoformat()
                                                            }

                                                            update_payload = {
                                                                "title": edit_title,
                                                                "description": edit_description,
                                                                "date_start": edit_date_start.isoformat(),
                                                                "date_end": edit_date_end.isoformat(),
                                                                "session_type": edit_type,
                                                                "capacity": int(edit_capacity),
                                                                "credit_cost": int(edit_credit_cost),
                                                                "location": edit_location,
                                                                "meeting_link": edit_meeting_link
                                                            }

                                                            try:
                                                                # 🔍 DEBUG: Log to backend terminal
                                                                print(f"🟢 FRONTEND: Attempting PATCH to session {session_id}")
                                                                print(f"   Payload credit_cost: {update_payload['credit_cost']}")
                                                                print(f"   Payload capacity: {update_payload['capacity']}")

                                                                update_response = requests.patch(
                                                                    f"{API_BASE_URL}/api/v1/sessions/{session_id}",
                                                                    json=update_payload,
                                                                    headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                                                    timeout=10
                                                                )

                                                                # Store result in session_state
                                                                st.session_state.last_save_attempt['status_code'] = update_response.status_code
                                                                st.session_state.last_save_attempt['response'] = update_response.json()

                                                                if update_response.status_code == 200:
                                                                    st.session_state.last_save_attempt['success'] = True
                                                                    st.session_state[edit_key] = False
                                                                    # Cache-bust már a fetch-nél van időbélyeggel!
                                                                    st.rerun()
                                                                else:
                                                                    st.session_state.last_save_attempt['success'] = False
                                                                    st.session_state.last_save_attempt['error'] = f"HTTP {update_response.status_code}"
                                                            except Exception as e:
                                                                st.session_state.last_save_attempt['success'] = False
                                                                st.session_state.last_save_attempt['error'] = str(e)
                                                                print(f"🔴 FRONTEND ERROR: {str(e)}")

                                                    # VIEW MODE
                                                    else:
                                                        # Build location from semester data (same as edit mode)
                                                        semester_location_city = selected_semester.get('location_city', '')
                                                        semester_location_venue = selected_semester.get('location_venue', '')
                                                        semester_location_address = selected_semester.get('location_address', '')

                                                        location_parts = []
                                                        if semester_location_venue:
                                                            location_parts.append(semester_location_venue)
                                                        if semester_location_city:
                                                            location_parts.append(semester_location_city)
                                                        if semester_location_address:
                                                            location_parts.append(semester_location_address)

                                                        display_location = ", ".join(location_parts) if location_parts else "Virtual"

                                                        col1, col2, col3 = st.columns(3)

                                                        with col1:
                                                            st.write(f"**Type**: {session.get('session_type', 'N/A')}")
                                                            st.write(f"**Capacity**: {session.get('capacity', 'N/A')}")

                                                        with col2:
                                                            st.write(f"**Start**: {session.get('date_start', 'N/A')[:16]}")
                                                            st.write(f"**End**: {session.get('date_end', 'N/A')[:16]}")

                                                        with col3:
                                                            st.write(f"**💳 Credit Cost**: {session.get('credit_cost', 1)} credits")
                                                            st.write(f"**Location**: {display_location}")

                                                        st.caption(f"**Description**: {session.get('description', 'No description')}")

                                    else:
                                        st.error(f"❌ Failed to fetch sessions: {sessions_response.status_code}")

                                except Exception as e:
                                    st.error(f"❌ Error fetching sessions: {str(e)}")

                    else:
                        st.error(f"❌ Failed to fetch semesters: {semesters_response.status_code}")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

            # TAB 5: My Sessions Calendar
            with tab5:
                st.markdown("### 📅 My Sessions Calendar")
                st.caption("View your sessions grouped by specialization and age group")

                # Fetch sessions for this instructor
                try:
                    sessions_response = requests.get(
                        f"{API_BASE_URL}/api/v1/sessions",
                        headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                        params={
                            "size": 100,
                            "instructor_id": instructor_id
                        },
                        timeout=10
                    )

                    if sessions_response.status_code != 200:
                        st.error(f"❌ Failed to fetch sessions: {sessions_response.status_code}")
                    else:
                        sessions_data = sessions_response.json()

                        # Handle SessionList response format
                        if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
                            my_sessions = sessions_data['sessions']
                        else:
                            my_sessions = sessions_data if isinstance(sessions_data, list) else []

                        if not my_sessions:
                            st.info("ℹ️ You have no sessions yet")
                        else:
                            # Fetch semesters to get specialization and age group info
                            semesters_response = requests.get(
                                f"{API_BASE_URL}/api/v1/semesters",
                                headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                                timeout=10
                            )

                            semester_lookup = {}
                            if semesters_response.status_code == 200:
                                semesters_data = semesters_response.json()
                                # Handle SemesterList response format
                                if isinstance(semesters_data, dict) and 'semesters' in semesters_data:
                                    all_semesters = semesters_data['semesters']
                                else:
                                    all_semesters = semesters_data if isinstance(semesters_data, list) else []
                                semester_lookup = {s['id']: s for s in all_semesters if isinstance(s, dict)}

                            # Hierarchical grouping: Campus → Specialization → Semester → Sessions
                            spec_display_names = {
                                'LFA_PLAYER_PRE': '⚽ LFA Player - PRE Academy',
                                'LFA_PLAYER_YOUTH': '⚽ LFA Player - YOUTH Academy',
                                'LFA_PLAYER_AMATEUR': '⚽ LFA Player - AMATEUR Team',
                                'LFA_PLAYER_PRO': '⚽ LFA Player - PRO Team',
                                'INTERNSHIP': '💼 LFA Internship Program',
                                'GANCUJU': '🥋 Gāncùjū'
                            }

                            # Build hierarchy
                            campuses = {}
                            for session in my_sessions:
                                if isinstance(session, dict):
                                    semester_id = session.get('semester_id')
                                    semester = semester_lookup.get(semester_id, {})

                                    campus_venue = semester.get('location_venue', 'Unknown Campus')
                                    spec_type = semester.get('specialization_type', 'UNKNOWN')
                                    spec_display = spec_display_names.get(spec_type, spec_type)

                                    # Campus level
                                    if campus_venue not in campuses:
                                        campuses[campus_venue] = {}

                                    # Specialization level
                                    if spec_type not in campuses[campus_venue]:
                                        campuses[campus_venue][spec_type] = {
                                            'spec_display': spec_display,
                                            'semesters': {}
                                        }

                                    # Semester level
                                    if semester_id not in campuses[campus_venue][spec_type]['semesters']:
                                        campuses[campus_venue][spec_type]['semesters'][semester_id] = {
                                            'semester': semester,
                                            'sessions': []
                                        }

                                    # Add session
                                    campuses[campus_venue][spec_type]['semesters'][semester_id]['sessions'].append(session)

                            # Display hierarchy
                            for campus_venue in sorted(campuses.keys()):
                                st.markdown(f"## 📍 {campus_venue.upper()}")

                                for spec_type, spec_data in sorted(campuses[campus_venue].items()):
                                    spec_display = spec_data['spec_display']
                                    total_sessions = sum(len(sem['sessions']) for sem in spec_data['semesters'].values())

                                    with st.expander(f"{spec_display} ({total_sessions} sessions)", expanded=True):

                                        # Sort semesters by start_date
                                        sorted_semesters = sorted(
                                            spec_data['semesters'].items(),
                                            key=lambda x: x[1]['semester'].get('start_date', '')
                                        )

                                        for semester_id, semester_data in sorted_semesters:
                                            semester = semester_data['semester']
                                            sessions = semester_data['sessions']

                                            semester_name = semester.get('name', 'N/A')
                                            start_date = semester.get('start_date', '')
                                            end_date = semester.get('end_date', '')

                                            # Format semester dates
                                            try:
                                                start_dt = dt.fromisoformat(start_date) if isinstance(start_date, str) else start_date
                                                end_dt = dt.fromisoformat(end_date) if isinstance(end_date, str) else end_date
                                                semester_period = f"{start_dt.strftime('%Y-%m-%d')} - {end_dt.strftime('%Y-%m-%d')}"
                                            except:
                                                semester_period = "N/A"

                                            with st.expander(f"📅 {semester_name} ({len(sessions)} sessions)", expanded=False):
                                                st.caption(f"Period: {semester_period}")
                                                st.divider()

                                                # Sort sessions by date
                                                sessions.sort(key=lambda x: x.get('date_start', ''))

                                                for session in sessions:
                                                    session_title = session.get('title', 'Untitled Session')
                                                    session_type = session.get('session_type', 'on_site')
                                                    date_start = session.get('date_start', '')
                                                    date_end = session.get('date_end', '')
                                                    capacity = session.get('capacity', 0)
                                                    credit_cost = session.get('credit_cost', 1)
                                                    location = session.get('location', 'N/A')

                                                    # Format dates
                                                    try:
                                                        start_dt = dt.fromisoformat(date_start.replace('Z', '+00:00'))
                                                        end_dt = dt.fromisoformat(date_end.replace('Z', '+00:00'))
                                                        date_display = start_dt.strftime('%Y-%m-%d %H:%M')
                                                        time_range = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                                                    except:
                                                        date_display = str(date_start)
                                                        time_range = "N/A"

                                                    # Session type icon
                                                    type_icons = {
                                                        'on_site': '🏟️',
                                                        'virtual': '💻',
                                                        'hybrid': '🔀'
                                                    }
                                                    type_icon = type_icons.get(session_type, '📍')

                                                    with st.container():
                                                        col1, col2, col3 = st.columns([3, 2, 1])

                                                        with col1:
                                                            st.markdown(f"**{type_icon} {session_title}**")
                                                            st.caption(f"📍 {location}")

                                                        with col2:
                                                            st.markdown(f"📅 {date_display}")
                                                            st.caption(f"⏰ {time_range}")

                                                        with col3:
                                                            st.markdown(f"👥 {capacity}")
                                                            st.caption(f"💳 {credit_cost} cr")

                                                        st.divider()

                except Exception as e:
                    st.error(f"❌ Error loading sessions: {str(e)}")

# ============================================================================
# VIEW PUBLIC PROFILE MODAL
# ============================================================================

if st.session_state.viewing_profile_user_id:
    st.divider()
    st.header("👤 Public Profile")

    user_id = st.session_state.viewing_profile_user_id
    profile_type = st.session_state.get("viewing_profile_type", "STUDENT")  # Default to STUDENT

    # Close button
    if st.button("❌ Close Profile", key="close_profile_btn"):
        st.session_state.viewing_profile_user_id = None
        st.session_state.viewing_profile_type = None
        st.rerun()

    # Fetch profile data based on role
    try:
        # If INSTRUCTOR role, show instructor profile
        if profile_type == "INSTRUCTOR":
            instructor_response = requests.get(
                f"{API_BASE_URL}/api/v1/public/users/{user_id}/profile/instructor",
                timeout=10
            )

            if instructor_response.status_code == 200:
                profile = instructor_response.json()

                # Display Instructor Profile
                st.markdown("## 👨‍🏫 Instructor Profile")

                # Header with basic info
                col1, col2, col3 = st.columns([1, 2, 1])

                with col1:
                    st.markdown("### 📸 Photo")
                    st.info("🖼️ No photo")

                with col2:
                    st.markdown(f"### 🏆 {profile['name']}")
                    st.caption(f"📧 {profile['email']}")
                    st.caption(f"🌍 Nationality: {profile.get('nationality', 'N/A')}")
                    st.caption(f"📅 DOB: {profile.get('date_of_birth', 'N/A')[:10] if profile.get('date_of_birth') else 'N/A'}")

                with col3:
                    st.metric("🏮 Total Licenses", profile['license_count'])
                    st.metric("📅 Availability Windows", profile['availability_windows_count'])

                st.divider()

                # Licenses with belt/level - GROUPED BY SPECIALIZATION IN TABS
                st.markdown("### 🏮 Instructor Licenses & Belts")

                if profile['licenses']:
                    # Group licenses by specialization type
                    grouped_licenses = defaultdict(list)
                    for lic in profile['licenses']:
                        grouped_licenses[lic['specialization_type']].append(lic)

                    # Create tabs for each specialization
                    tab_labels = []
                    tab_specs = []

                    if 'PLAYER' in grouped_licenses:
                        tab_labels.append(f"🥋 GānCuju PLAYER ({len(grouped_licenses['PLAYER'])})")
                        tab_specs.append('PLAYER')
                    if 'COACH' in grouped_licenses:
                        tab_labels.append(f"👨‍🏫 LFA COACH ({len(grouped_licenses['COACH'])})")
                        tab_specs.append('COACH')
                    if 'INTERNSHIP' in grouped_licenses:
                        tab_labels.append(f"📚 INTERNSHIP ({len(grouped_licenses['INTERNSHIP'])})")
                        tab_specs.append('INTERNSHIP')

                    if tab_labels:
                        tabs = st.tabs(tab_labels)

                        for idx, spec_type in enumerate(tab_specs):
                            with tabs[idx]:
                                licenses = sorted(grouped_licenses[spec_type], key=lambda x: x['current_level'])

                                # Show all levels in this specialization
                                for lic in licenses:
                                    with st.expander(f"{lic['belt_emoji']} Level {lic['current_level']} - {lic['belt_name']}", expanded=False):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.caption(f"**License ID:** {lic['license_id']}")
                                            st.caption(f"**Current Level:** {lic['current_level']}")
                                            st.caption(f"**Max Achieved:** {lic['max_achieved_level']}")
                                        with col2:
                                            st.caption(f"**Started:** {lic['started_at'][:10] if lic['started_at'] else 'N/A'}")
                                            if lic['last_advanced_at']:
                                                st.caption(f"**Last Advanced:** {lic['last_advanced_at'][:10]}")
                else:
                    st.info("No licenses found")

                st.divider()

                # Additional info
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Credit Balance", profile['credit_balance'])
                with col2:
                    st.caption(f"**Registered:** {profile['created_at'][:10] if profile['created_at'] else 'N/A'}")
                    st.caption(f"**Status:** {'🟢 Active' if profile['is_active'] else '🔴 Inactive'}")

                # Show credit transaction history if viewing own profile with instructor token
                if st.session_state.instructor_token:
                    # Get current instructor info to check if viewing own profile
                    success_info, user_info = get_user_info(st.session_state.instructor_token)
                    if success_info and user_info.get('id') == user_id:
                        # Viewing own profile - show transaction history
                        display_credit_transactions(st.session_state.instructor_token, profile['credit_balance'])

            else:
                st.error(f"❌ Failed to load instructor profile (HTTP {instructor_response.status_code})")

        else:
            # Student profile - try LFA Player first
            lfa_player_response = requests.get(
                f"{API_BASE_URL}/api/v1/public/users/{user_id}/profile/lfa-player",
                timeout=10
            )

            if lfa_player_response.status_code == 200:
                # User has LFA Player license - show detailed FIFA-style profile
                profile = lfa_player_response.json()

                # Display FIFA-style profile
                st.markdown("## ⚽ LFA Football Player Profile")

                # Header with basic info
                col1, col2, col3 = st.columns([1, 2, 1])

                with col1:
                    st.markdown("### 📸 Photo")
                    st.info("🖼️ No photo")

                with col2:
                    st.markdown(f"### 🏆 {profile['name']}")
                    st.caption(f"📧 {profile['email']}")
                    st.caption(f"🌍 Nationality: {profile.get('nationality', 'N/A')}")
                    st.caption(f"📅 DOB: {profile.get('date_of_birth', 'N/A')[:10] if profile.get('date_of_birth') else 'N/A'}")

                with col3:
                    st.metric("⭐ Overall Rating", f"{profile['overall_rating']}/100")
                    st.caption(f"📊 Level: {profile['level']}")
                    st.caption(f"🎯 Position: {profile['position']}")

                st.divider()

                # Skills (7 skills)
                st.markdown("### 📊 Skills")

                skills = profile['skills']

                # All 7 skills in one column, coherently listed
                st.progress(skills['shooting'] / 100, text=f"Shooting: {skills['shooting']}/100")
                st.progress(skills['crossing'] / 100, text=f"Crossing: {skills['crossing']}/100")
                st.progress(skills['heading'] / 100, text=f"Heading: {skills['heading']}/100")
                st.progress(skills['passing'] / 100, text=f"Passing: {skills['passing']}/100")
                st.progress(skills['dribbling'] / 100, text=f"Dribbling: {skills['dribbling']}/100")
                st.progress(skills['defending'] / 100, text=f"Defending: {skills['defending']}/100")
                st.progress(skills['ball_control'] / 100, text=f"Ball Control: {skills['ball_control']}/100")

                st.divider()

                # Recent assessments
                st.markdown("### 📝 Recent Assessments")
                if profile.get('recent_assessments'):
                    for assessment in profile['recent_assessments']:
                        with st.expander(f"✅ {assessment['skill_name'].title()} - {assessment['percentage']}%"):
                            st.caption(f"**Instructor:** {assessment['instructor_name']}")
                            st.caption(f"**Points:** {assessment['points_earned']}/{assessment['points_total']}")
                            st.caption(f"**Date:** {assessment['assessed_at'][:10] if assessment['assessed_at'] else 'N/A'}")
                else:
                    st.info("No assessments yet")

                st.divider()

                # Additional info
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Credit Balance", profile['credit_balance'])
                with col2:
                    st.caption(f"**Age Group:** {profile['age_group']}")
                    st.caption(f"**Max Level:** {profile['max_level_achieved']}")

                # Show credit transaction history if viewing own profile with student token
                if st.session_state.student_token:
                    # Get current student info to check if viewing own profile
                    success_info, user_info = get_user_info(st.session_state.student_token)
                    if success_info and user_info.get('id') == user_id:
                        # Viewing own profile - show transaction history
                        display_credit_transactions(st.session_state.student_token, profile['credit_balance'])

            else:
                # User doesn't have LFA Player license - show basic profile
                basic_profile_response = requests.get(
                    f"{API_BASE_URL}/api/v1/public/users/{user_id}/profile/basic",
                    timeout=10
                )

                if basic_profile_response.status_code == 200:
                    profile = basic_profile_response.json()

                    st.markdown("## 📋 Basic Profile")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"### 👤 {profile['name']}")
                        st.caption(f"📧 {profile['email']}")
                        st.caption(f"🌍 Nationality: {profile.get('nationality', 'N/A')}")
                        st.caption(f"📅 DOB: {profile.get('date_of_birth', 'N/A')[:10] if profile.get('date_of_birth') else 'N/A'}")
                        st.metric("💰 Credit Balance", profile['credit_balance'])

                    with col2:
                        st.markdown("### 🎓 Active Licenses")
                        for license in profile['licenses']:
                            st.info(f"**{license['specialization']}** - Level {license['level']} (Max: {license['max_level']})")
                            st.caption(f"Started: {license['started_at'][:10] if license['started_at'] else 'N/A'}")

                    # Show credit transaction history if viewing own profile with student token
                    if st.session_state.student_token:
                        # Get current student info to check if viewing own profile
                        success_info, user_info = get_user_info(st.session_state.student_token)
                        if success_info and user_info.get('id') == user_id:
                            # Viewing own profile - show transaction history
                            display_credit_transactions(st.session_state.student_token, profile['credit_balance'])

                else:
                    st.error(f"❌ Failed to load basic profile (HTTP {basic_profile_response.status_code})")

    except Exception as e:
        st.error(f"❌ Error loading profile: {str(e)}")

    st.divider()

# ============================================================================
# REGISTERED USERS LIST
# ============================================================================

st.divider()
st.subheader("📋 Recently Registered Users")

if st.session_state.admin_token:
    col_refresh, col_limit = st.columns([3, 1])

    with col_limit:
        user_limit = st.selectbox("Limit", [5, 10, 20, 50], index=1, key="user_limit")

    with col_refresh:
        if st.button("🔄 Refresh User List", use_container_width=True):
            st.rerun()

    success, users = get_recent_registered_users(st.session_state.admin_token, limit=user_limit)

    if success and users:
        st.success(f"✅ Found {len(users)} users")

        for idx, user in enumerate(users):
            with st.container():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 2, 1, 1, 0.7, 0.7, 0.8])

                with col1:
                    st.markdown(f"**👤 {user.get('name', 'N/A')}**")
                    st.caption(f"📧 {user.get('email', 'N/A')}")

                with col2:
                    role = user.get('role', 'N/A')
                    role_upper = role.upper() if role and role != 'N/A' else 'N/A'
                    role_emoji = "🎓" if role_upper == "STUDENT" else "👨‍🏫" if role_upper == "INSTRUCTOR" else "👑"
                    st.markdown(f"{role_emoji} **{role}**")

                    is_active = user.get('is_active', False)
                    status_color = "🟢" if is_active else "🔴"
                    status_text = "Active" if is_active else "Inactive"
                    st.caption(f"{status_color} {status_text}")

                with col3:
                    credit_balance = user.get('credit_balance', 0)
                    st.metric("💰 Credits", credit_balance)

                with col4:
                    st.caption(f"ID: {user.get('id', 'N/A')}")
                    created_at = user.get('created_at', 'N/A')
                    if created_at != 'N/A' and created_at:
                        try:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            st.caption(f"📅 {dt.strftime('%Y-%m-%d %H:%M')}")
                        except:
                            # Safe string slicing - handle None or short strings
                            st.caption(f"📅 {str(created_at)[:10] if created_at else 'N/A'}")
                    else:
                        st.caption("📅 N/A")

                user_id = user.get('id')

                with col5:
                    # Reset Password button
                    if user_id and role_upper != "ADMIN":  # Don't reset admin passwords
                        if st.button("🔑", key=f"reset_pwd_{user_id}_{idx}", use_container_width=True, help="Reset Password"):
                            # Generate secure random password
                            alphabet = string.ascii_letters + string.digits + "!@#$%"
                            new_password = ''.join(secrets.choice(alphabet) for _ in range(12))

                            success_reset, message = reset_user_password(st.session_state.admin_token, user_id, new_password)

                            if success_reset:
                                # Store the new password in session state for display
                                if "reset_passwords" not in st.session_state:
                                    st.session_state.reset_passwords = {}
                                st.session_state.reset_passwords[user_id] = new_password
                                add_log(f"Password reset for {user.get('name', 'User')}", "success")
                                st.rerun()
                            else:
                                add_log(f"Failed to reset password: {message}", "error")
                                st.error(f"❌ {message}")

                with col6:
                    # Edit User button
                    if user_id and role_upper != "ADMIN":  # Don't edit admin users
                        if st.button("✏️", key=f"edit_user_{user_id}_{idx}", use_container_width=True, help="Edit User"):
                            # Toggle edit mode for this user
                            if st.session_state.editing_user_id == user_id:
                                st.session_state.editing_user_id = None
                            else:
                                st.session_state.editing_user_id = user_id
                            st.rerun()

                with col7:
                    # View Profile button (both students and instructors)
                    if user_id and (role_upper == "STUDENT" or role_upper == "INSTRUCTOR"):
                        button_help = "View Student Profile" if role_upper == "STUDENT" else "View Instructor Profile"
                        if st.button("👁️", key=f"view_profile_{user_id}_{idx}", use_container_width=True, help=button_help):
                            st.session_state.viewing_profile_user_id = user_id
                            st.session_state.viewing_profile_type = role_upper  # Store role type
                            st.rerun()

                # Show newly generated password if exists
                if "reset_passwords" in st.session_state and user_id in st.session_state.reset_passwords:
                    st.success("✅ Password reset successfully!")
                    st.info("**🔑 New Password (copyable):**")
                    st.code(st.session_state.reset_passwords[user_id], language=None)
                    st.caption("⚠️ Save this password and send it to the user!")

                    # Clear button to dismiss the password display
                    if st.button("✓ Got it, clear password", key=f"clear_pwd_{user_id}_{idx}"):
                        del st.session_state.reset_passwords[user_id]
                        st.rerun()

                # Show edit form if this user is being edited
                if st.session_state.editing_user_id == user_id:
                    with st.expander("✏️ **Edit User Profile**", expanded=True):
                        st.markdown("**📋 Update User Information**")

                        # Create form
                        with st.form(key=f"edit_form_{user_id}"):
                            # Basic info
                            edit_name = st.text_input("Name", value=user.get('name', ''), key=f"edit_name_{user_id}")
                            edit_email = st.text_input("Email", value=user.get('email', ''), key=f"edit_email_{user_id}")

                            # Required fields from registration
                            col_a, col_b = st.columns(2)

                            with col_a:
                                # Date of birth
                                dob_value = user.get('date_of_birth', None)
                                if dob_value:
                                    try:
                                        if isinstance(dob_value, str):
                                            dob_dt = datetime.fromisoformat(dob_value.replace('Z', '+00:00'))
                                        else:
                                            dob_dt = dob_value
                                        edit_dob = st.date_input("Date of Birth", value=dob_dt.date(), key=f"edit_dob_{user_id}")
                                    except:
                                        edit_dob = st.date_input("Date of Birth", value=datetime(2000, 1, 1), key=f"edit_dob_{user_id}")
                                else:
                                    edit_dob = st.date_input("Date of Birth", value=datetime(2000, 1, 1), key=f"edit_dob_{user_id}")

                                # Nationality with flags
                                nationality_options = [
                                    "🇭🇺 Hungarian", "🇷🇴 Romanian", "🇸🇰 Slovak", "🇦🇹 Austrian",
                                    "🇩🇪 German", "🇬🇧 British", "🇫🇷 French", "🇪🇸 Spanish",
                                    "🇮🇹 Italian", "🇵🇱 Polish", "🇨🇿 Czech", "🇺🇦 Ukrainian",
                                    "🇷🇸 Serbian", "🇭🇷 Croatian", "🇸🇮 Slovenian", "🇧🇬 Bulgarian",
                                    "🇺🇸 American", "🇨🇦 Canadian", "🇧🇷 Brazilian", "🇦🇷 Argentine",
                                    "🇲🇽 Mexican", "🇨🇱 Chilean", "🇨🇴 Colombian", "🇵🇪 Peruvian",
                                    "🇨🇳 Chinese", "🇯🇵 Japanese", "🇰🇷 Korean", "🇮🇳 Indian",
                                    "🇦🇺 Australian", "🇳🇿 New Zealand", "🇿🇦 South African", "Other"
                                ]
                                # Find current nationality in the list
                                current_nationality = user.get('nationality') or 'Hungarian'
                                nationality_index = 0
                                for idx, option in enumerate(nationality_options):
                                    if current_nationality in option:
                                        nationality_index = idx
                                        break
                                edit_nationality = st.selectbox("Nationality", options=nationality_options, index=nationality_index, key=f"edit_nationality_{user_id}")

                            with col_b:
                                gender_value = user.get('gender', 'Prefer not to say')
                                gender_options = ["Male", "Female", "Other", "Prefer not to say"]
                                gender_index = gender_options.index(gender_value) if gender_value in gender_options else 3
                                edit_gender = st.selectbox("Gender", options=gender_options, index=gender_index, key=f"edit_gender_{user_id}")

                                edit_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"edit_phone_{user_id}")

                            # Submit buttons
                            col_submit, col_cancel = st.columns(2)
                            with col_submit:
                                submit_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)
                            with col_cancel:
                                cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)

                            if submit_edit:
                                # Prepare updates
                                # Extract nationality name without flag (remove emoji and space)
                                nationality_clean = edit_nationality.split(" ", 1)[1] if " " in edit_nationality else edit_nationality
                                updates = {
                                    "name": edit_name,
                                    "email": edit_email,
                                    "date_of_birth": edit_dob.strftime("%Y-%m-%dT00:00:00"),
                                    "nationality": nationality_clean,
                                    "gender": edit_gender,
                                    "phone": edit_phone if edit_phone else None
                                }

                                # Send update request
                                success_update, message = update_user_profile(st.session_state.admin_token, user_id, updates)

                                if success_update:
                                    st.session_state.editing_user_id = None
                                    add_log(f"User {edit_name} updated successfully", "success")
                                    st.success("✅ User updated successfully!")
                                    st.rerun()
                                else:
                                    add_log(f"Failed to update user: {message}", "error")
                                    st.error(f"❌ {message}")

                            if cancel_edit:
                                st.session_state.editing_user_id = None
                                st.rerun()

                st.divider()

        with st.expander("🔍 View Raw User Data (JSON)"):
            st.json(users)

    elif success and not users:
        st.info("ℹ️ No users found")
    else:
        st.error("❌ Failed to fetch users")

    # DEPRECATED - old workflow section end

elif st.session_state.active_workflow == "session_rules":
    # ========================================================================
    # SESSION RULES TESTING WORKFLOW
    # ========================================================================

    st.header("🧪 Session Rules Testing")
    st.caption("Test all 6 session booking rules • Instructor creates sessions • Student tests booking/cancellation")
    st.divider()

    # Check if both users are logged in
    if not st.session_state.instructor_token:
        st.warning("⚠️ Please log in as Instructor in the sidebar to create test sessions")

    if not st.session_state.student_token:
        st.warning("⚠️ Please log in as Student in the sidebar to test booking/cancellation")

    # Helper functions for session rules testing
    def create_test_session_sr(token: str, hours_from_now: int, title: str) -> Optional[Dict]:
        """Create a test session for rules testing"""
        try:
            headers = {"Authorization": f"Bearer {token}"}

            # Get active semesters
            semesters_response = requests.get(
                f"{API_BASE_URL}/api/v1/semesters/",
                headers=headers,
                timeout=10
            )

            if semesters_response.status_code != 200:
                st.error("Nem sikerült lekérdezni a szemesztereket")
                return None

            semesters = semesters_response.json()
            session_date = (datetime.now() + timedelta(hours=hours_from_now)).date()

            valid_semesters = [
                s for s in semesters
                if s.get("is_active") and
                   datetime.fromisoformat(s["start_date"]).date() <= session_date <=
                   datetime.fromisoformat(s["end_date"]).date()
            ]

            if not valid_semesters:
                st.error(f"Nincs aktív szemeszter a dátumhoz: {session_date}")
                return None

            active_semester = valid_semesters[0]

            # Create session
            session_start = datetime.now() + timedelta(hours=hours_from_now)
            session_end = session_start + timedelta(hours=2)

            session_data = {
                "title": title or f"Teszt Session ({hours_from_now}h)",
                "description": "Automatikus teszt session - szabály validációhoz",
                "date_start": session_start.isoformat(),
                "date_end": session_end.isoformat(),
                "capacity": 10,
                "level": "beginner",
                "sport_type": "FOOTBALL",
                "location": "Test Location",
                "semester_id": active_semester["id"]
            }

            response = requests.post(
                f"{API_BASE_URL}/api/v1/sessions/",
                headers=headers,
                json=session_data,
                timeout=10
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                st.error(f"Session létrehozás sikertelen: {response.text}")
                return None

        except Exception as e:
            st.error(f"Hiba a session létrehozása során: {str(e)}")
            return None

    def create_booking_sr(token: str, session_id: int) -> Optional[Dict]:
        """Create a booking for a session"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{API_BASE_URL}/api/v1/bookings/",
                headers=headers,
                json={"session_id": session_id},
                timeout=10
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                return {"error": response.json(), "status_code": response.status_code}

        except Exception as e:
            return {"error": str(e)}

    def cancel_booking_sr(token: str, booking_id: int) -> Optional[Dict]:
        """Cancel a booking"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.delete(
                f"{API_BASE_URL}/api/v1/bookings/{booking_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.json(), "status_code": response.status_code}

        except Exception as e:
            return {"error": str(e)}

    # Show overview of all 6 rules
    st.markdown("### 📋 6 Session Rules Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        **🔒 Rule #1: 24h Booking Deadline**
        Students can only book sessions at least 24 hours in advance.
        """)

        st.info("""
        **⏱️ Rule #2: 12h Cancel Deadline**
        Students can cancel bookings up to 12 hours before session starts.
        """)

    with col2:
        st.info("""
        **✅ Rule #3: 15min Check-in Window**
        Students can check-in 15 minutes before session starts.
        """)

        st.info("""
        **💬 Rule #4: Bidirectional Feedback (24h Window)**
        Both students and instructors can give feedback within 24 hours after session ends.
        """)

    with col3:
        st.info("""
        **📝 Rule #5: Hybrid/Virtual Quiz (Session Time Window)**
        Quiz only available during session time for HYBRID/VIRTUAL sessions.
        """)

        st.info("""
        **⭐ Rule #6: Intelligent XP Calculation**
        XP based on session type, instructor rating, and quiz performance.
        """)

    st.divider()

    # Tab structure for testing each rule
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔒 Rule #1: Booking Deadline",
        "⏱️ Rule #2: Cancel Deadline",
        "✅ Rule #3: Check-in Window",
        "💬 Rule #4: Feedback",
        "📝 Rule #5: Quiz System",
        "⭐ Rule #6: XP Rewards"
    ])

    # TAB 1: Rule #1 - 24h Booking Deadline
    with tab1:
        st.markdown("### 🔒 Rule #1: 24-Hour Booking Deadline")
        st.info("**Szabály**: Hallgatók csak minimum 24 órával a session kezdete előtt tudnak foglalni.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ✅ Teszt 1A: Foglalás 48 órával előre")
            st.caption("Expected: SUCCESS - Booking should be allowed")

            if st.button("🚀 Teszt 1A Futtatása", key="test_1a", use_container_width=True):
                if not st.session_state.instructor_token:
                    st.error("❌ Instructor login szükséges session létrehozásához!")
                elif not st.session_state.student_token:
                    st.error("❌ Student login szükséges foglaláshoz!")
                else:
                    with st.spinner("Session létrehozása..."):
                        session = create_test_session_sr(st.session_state.instructor_token, 48, "Teszt 1A - 48h előre")

                        if session:
                            st.success(f"✅ Session létrehozva: {session['id']}")
                            add_log(f"Test 1A: Session {session['id']} created 48h in advance", "success")

                            with st.spinner("Foglalás..."):
                                result = create_booking_sr(st.session_state.student_token, session['id'])

                                if result and 'error' not in result:
                                    st.success("✅ **PASS**: Foglalás 48 órával előre megengedett!")
                                    add_log(f"Test 1A: PASS - Booking allowed 48h in advance", "success")
                                    st.json(result)
                                else:
                                    st.error("❌ **FAIL**: A foglalást vissza kellett volna fogadni!")
                                    add_log(f"Test 1A: FAIL - Booking rejected unexpectedly", "error")
                                    if result:
                                        st.json(result)

        with col2:
            st.markdown("#### ❌ Teszt 1B: Foglalás 12 órával előre")
            st.caption("Expected: BLOCKED - Booking should be rejected")

            if st.button("🚀 Teszt 1B Futtatása", key="test_1b", use_container_width=True):
                if not st.session_state.instructor_token:
                    st.error("❌ Instructor login szükséges session létrehozásához!")
                elif not st.session_state.student_token:
                    st.error("❌ Student login szükséges foglaláshoz!")
                else:
                    with st.spinner("Session létrehozása..."):
                        session = create_test_session_sr(st.session_state.instructor_token, 12, "Teszt 1B - 12h előre")

                        if session:
                            st.success(f"✅ Session létrehozva: {session['id']}")
                            add_log(f"Test 1B: Session {session['id']} created 12h in advance", "info")

                            with st.spinner("Foglalás kísérlet..."):
                                result = create_booking_sr(st.session_state.student_token, session['id'])

                                if result and 'error' in result:
                                    st.success("✅ **PASS**: Foglalás 12 órával előre helyesen blokkolva!")
                                    add_log(f"Test 1B: PASS - Booking correctly blocked within 24h", "success")
                                    st.json(result)
                                else:
                                    st.error("❌ **FAIL**: A foglalást blokkolni kellett volna!")
                                    add_log(f"Test 1B: FAIL - Booking allowed within 24h (should be blocked)", "error")
                                    if result:
                                        st.json(result)

    # TAB 2: Rule #2 - 12h Cancel Deadline
    with tab2:
        st.markdown("### ⏱️ Rule #2: 12-Hour Cancellation Deadline")
        st.info("**Szabály**: Hallgatók a foglalást 12 órával a session kezdete előtt tudják lemondani.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ✅ Teszt 2A: Törlés 24 órával előre")
            st.caption("Expected: SUCCESS - Cancellation should be allowed")

            if st.button("🚀 Teszt 2A Futtatása", key="test_2a", use_container_width=True):
                if not st.session_state.instructor_token:
                    st.error("❌ Instructor login szükséges!")
                elif not st.session_state.student_token:
                    st.error("❌ Student login szükséges!")
                else:
                    with st.spinner("Session létrehozása..."):
                        session = create_test_session_sr(st.session_state.instructor_token, 48, "Teszt 2A - Cancel 24h előre")

                        if session:
                            st.success(f"✅ Session létrehozva: {session['id']}")

                            with st.spinner("Foglalás..."):
                                booking = create_booking_sr(st.session_state.student_token, session['id'])

                                if booking and 'error' not in booking:
                                    st.success(f"✅ Foglalás létrehozva: {booking.get('id')}")
                                    add_log(f"Test 2A: Booking {booking.get('id')} created", "info")

                                    with st.spinner("Törlés..."):
                                        cancel_result = cancel_booking_sr(st.session_state.student_token, booking['id'])

                                        if cancel_result and 'error' not in cancel_result:
                                            st.success("✅ **PASS**: Törlés 24 órával előre megengedett!")
                                            add_log(f"Test 2A: PASS - Cancellation allowed 24h in advance", "success")
                                            st.json(cancel_result)
                                        else:
                                            st.error("❌ **FAIL**: A törlést vissza kellett volna fogadni!")
                                            add_log(f"Test 2A: FAIL - Cancellation rejected unexpectedly", "error")
                                            if cancel_result:
                                                st.json(cancel_result)
                                else:
                                    st.error("❌ Nem sikerült a foglalás!")
                                    if booking:
                                        st.json(booking)

        with col2:
            st.markdown("#### ❌ Teszt 2B: Törlés 6 órával előre")
            st.caption("Expected: BLOCKED - Cancellation should be rejected")
            st.info("⚠️ **Figyelem**: Ez a teszt függ a Szabály #1-től! A foglalást 24+ órával előre kell létrehoznod.")

            st.markdown("""
            **Tesztelési sorrend:**
            1. Hozz létre sessiont 48 órára előre (Rule #1)
            2. Foglalj rá azonnal (24h window-n belül van)
            3. Várj ~36 órát (vagy módosítsd manuálisan a session időt)
            4. Próbáld meg törölni (most már <12h)
            """)

    # TAB 3: Rule #3 - 15min Check-in Window
    with tab3:
        st.markdown("### ✅ Rule #3: 15-Minute Check-in Window")
        st.info("**Szabály**: Hallgatók 15 perccel a session kezdete előtt tudnak check-in-elni.")

        st.warning("⚠️ **Automated testing korlát**: Nem tudunk sessiont létrehozni 15 percen belül Rule #1 miatt (24h minimum).")

        st.markdown("""
        **Manuális teszt lépések:**
        1. Instructor/Admin módosítja egy létező session időpontját az admin panelből
        2. Állítsa be a session kezdetét 10 percre előre (ha az admin panel engedélyezi)
        3. Student megpróbál check-in-elni a foglalásra
        4. Várt eredmény: Check-in sikeres ha a session -15min és start time között van
        """)

        st.info("""
        **Endpoint**: `POST /api/v1/attendance/{booking_id}/checkin`

        **Validáció a backendben**:
        - ✅ Check-in engedélyezett: 15 perccel session start előtt
        - ❌ Check-in blokkolt: >15 perc session start előtt
        - ❌ Check-in blokkolt: session start után
        """)

    # TAB 4: Rule #4 - Bidirectional Feedback
    with tab4:
        st.markdown("### 💬 Rule #4: Bidirectional Feedback (24h Window)")
        st.info("**Szabály**: Session után mind a hallgató, mind az oktató tud visszajelzést adni **24 órán belül**.")

        st.success("""
        ✅ **ÚJ Backend Validáció**:
        - Feedback csak a session vége után adható
        - Feedback csak 24 órán belül adható a session vége után
        - 24h után a feedback ablak lezárul
        """)

        st.markdown("""
        **Feedback Endpoints:**

        1. **Student → Instructor feedback:**
           - `POST /api/v1/feedback/`
           - Student értékeli az instructort és a sessiont
           - ⏱️ **Validáció**: session_end < current_time < session_end + 24h

        2. **Instructor → Student feedback:**
           - `POST /api/v1/feedback/instructor`
           - Instructor értékeli a student teljesítményét
           - ⏱️ **Validáció**: session_end < current_time < session_end + 24h
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 👨‍🎓 Student Feedback (Student → Instructor)")
            if st.session_state.student_token:
                session_id_student = st.number_input("Session ID", min_value=1, key="feedback_session_student")
                rating = st.slider("Rating", 1, 5, 5, key="feedback_rating_student")
                comment = st.text_area("Comment", "Great session!", key="feedback_comment_student")

                if st.button("📤 Submit Student Feedback", key="submit_student_feedback"):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/api/v1/feedback/",
                            headers={"Authorization": f"Bearer {st.session_state.student_token}"},
                            json={
                                "session_id": int(session_id_student),
                                "rating": rating,
                                "comment": comment
                            },
                            timeout=10
                        )

                        if response.status_code in [200, 201]:
                            st.success("✅ Student feedback submitted!")
                            add_log(f"Student feedback submitted for session {session_id_student}", "success")
                            st.json(response.json())
                        else:
                            st.error(f"❌ Failed: {response.text}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Student login szükséges")

        with col2:
            st.markdown("#### 👨‍🏫 Instructor Feedback (Instructor → Student)")
            if st.session_state.instructor_token:
                session_id_instructor = st.number_input("Session ID", min_value=1, key="feedback_session_instructor")
                student_id = st.number_input("Student ID", min_value=1, key="feedback_student_id")
                performance_rating = st.slider("Performance Rating", 1, 5, 4, key="feedback_performance")
                instructor_comment = st.text_area("Comment", "Good performance!", key="feedback_comment_instructor")

                if st.button("📤 Submit Instructor Feedback", key="submit_instructor_feedback"):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/api/v1/feedback/instructor",
                            headers={"Authorization": f"Bearer {st.session_state.instructor_token}"},
                            json={
                                "session_id": int(session_id_instructor),
                                "student_id": int(student_id),
                                "performance_rating": performance_rating,
                                "comment": instructor_comment
                            },
                            timeout=10
                        )

                        if response.status_code in [200, 201]:
                            st.success("✅ Instructor feedback submitted!")
                            add_log(f"Instructor feedback submitted for student {student_id}", "success")
                            st.json(response.json())
                        else:
                            st.error(f"❌ Failed: {response.text}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Instructor login szükséges")

    # TAB 5: Rule #5 - Quiz System
    with tab5:
        st.markdown("### 📝 Rule #5: Hybrid/Virtual Quiz System (Session Time Window)")
        st.info("**Szabály**: Quiz csak HYBRID/VIRTUAL sessionök alatt elérhető, **kizárólag a session időtartama alatt**.")

        st.success("""
        ✅ **ÚJ Backend Validáció**:
        - Quiz csak HYBRID és VIRTUAL session típusokhoz
        - Quiz csak a session start és end között elérhető
        - Quiz csak ha az instructor unlock-olta
        - Session start előtt: "Quiz is not available yet"
        - Session end után: "Quiz is no longer available"
        """)

        st.markdown("""
        **Quiz System Features:**
        - ✅ Session type validation (HYBRID/VIRTUAL only)
        - ✅ Time window validation (session start → end)
        - ✅ Instructor unlock requirement
        - ✅ Adaptive difficulty
        - ✅ Progress tracking
        """)

        st.markdown("""
        **Quiz Endpoints:**
        - `GET /api/v1/quiz/{quiz_id}?session_id=X` - Get quiz (with session validation)
        - `POST /api/v1/quiz/{quiz_id}/start` - Start quiz attempt
        - `POST /api/v1/quiz/{quiz_id}/submit` - Submit answers
        - `GET /api/v1/quiz/results/{attempt_id}` - Get results

        **Validation Logic**:
        ```python
        # Only HYBRID/VIRTUAL sessions allow quizzes
        if session.sport_type not in ["HYBRID", "VIRTUAL"]:
            raise HTTPException(403, "Quizzes only for HYBRID/VIRTUAL")

        # Quiz must be unlocked by instructor
        if not session.quiz_unlocked:
            raise HTTPException(403, "Quiz not unlocked yet")

        # Current time must be within session window
        if current_time < session_start:
            raise HTTPException(403, "Quiz not available yet")
        if current_time > session_end:
            raise HTTPException(403, "Quiz no longer available")
        ```
        """)

        if st.session_state.student_token:
            if st.button("📋 Fetch Available Quizzes", key="fetch_quizzes"):
                try:
                    response = requests.get(
                        f"{API_BASE_URL}/api/v1/quiz/",
                        headers={"Authorization": f"Bearer {st.session_state.student_token}"},
                        timeout=10
                    )

                    if response.status_code == 200:
                        quizzes = response.json()
                        st.success(f"✅ Found {len(quizzes)} quizzes")
                        add_log(f"Fetched {len(quizzes)} quizzes", "info")

                        for quiz in quizzes:
                            with st.expander(f"📝 {quiz.get('title', 'Quiz')}"):
                                st.json(quiz)
                    else:
                        st.error(f"❌ Failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Student login szükséges")

    # TAB 6: Rule #6 - XP Rewards
    with tab6:
        st.markdown("### ⭐ Rule #6: Intelligent XP Calculation System")
        st.info("**Szabály**: Intelligens XP számítás session típus alapján, instructor értékelés ÉS/VAGY quiz eredmény alapján.")

        st.success("""
        ✅ **ÚJ Backend Kalkuláció**:

        **XP = Base (50) + Instructor (0-50) + Quiz (0-150)**

        **Session Típus Alapú Maximumok:**
        - ONSITE: max 100 XP (base 50 + instructor 50)
        - HYBRID: max 250 XP (base 50 + instructor 50 + quiz 150)
        - VIRTUAL: max 250 XP (base 50 + instructor 50 + quiz 150)
        """)

        st.markdown("""
        **Intelligent XP Components:**

        1. **Base XP (50 XP)** - Check-in sikeres minden session típushoz

        2. **Instructor Evaluation XP (0-50 XP)** - Minden session típushoz
           - 5 stars: +50 XP
           - 4 stars: +40 XP
           - 3 stars: +30 XP
           - 2 stars: +20 XP
           - 1 star: +10 XP
           - No rating: +0 XP

        3. **Quiz XP (0-150 XP)** - Csak HYBRID/VIRTUAL sessionökhoz
           - Excellent (≥90%): +150 XP
           - Pass (70-89%): +75 XP
           - Fail (<70%): +0 XP

        **Level Progression:** 500 XP = 1 Level
        """)

        if st.session_state.student_token:
            if st.button("📊 Fetch My XP & Achievements", key="fetch_xp"):
                try:
                    # Fetch gamification profile
                    response = requests.get(
                        f"{API_BASE_URL}/api/v1/students/gamification/profile",
                        headers={"Authorization": f"Bearer {st.session_state.student_token}"},
                        timeout=10
                    )

                    if response.status_code == 200:
                        profile = response.json()
                        st.success("✅ Gamification profile loaded!")
                        add_log("Fetched gamification profile", "info")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Total XP", profile.get('total_xp', 0))
                        with col2:
                            st.metric("Level", profile.get('level', 1))
                        with col3:
                            st.metric("Achievements", len(profile.get('achievements', [])))

                        st.json(profile)
                    else:
                        st.error(f"❌ Failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Student login szükséges")

        st.divider()

        st.markdown("#### 🎯 XP Calculation Examples")

        example_col1, example_col2, example_col3 = st.columns(3)

        with example_col1:
            st.markdown("**ONSITE Session**")
            st.code("""
Base XP:         +50
Instructor (4★): +40
Quiz:            +0 (N/A)
───────────────────
TOTAL XP:        90
            """)

        with example_col2:
            st.markdown("**HYBRID Session (Pass Quiz)**")
            st.code("""
Base XP:         +50
Instructor (5★): +50
Quiz (75%):      +75
───────────────────
TOTAL XP:        175
            """)

        with example_col3:
            st.markdown("**VIRTUAL Session (Excellent Quiz)**")
            st.code("""
Base XP:         +50
Instructor (5★): +50
Quiz (95%):      +150
───────────────────
TOTAL XP:        250 (MAX)
            """)

        st.divider()

        st.markdown("#### 🎯 Additional XP Triggers")
        st.markdown("""
        **Egyéb XP források:**
        - Project milestone → +200 XP
        - Feedback adása → +25 XP
        - Achievement unlock → Variable XP
        """)

# ============================================================================
# WORKFLOW LOGS
# ============================================================================

st.divider()
st.subheader("📋 Workflow Logs")

if st.session_state.workflow_logs:
    for log in st.session_state.workflow_logs[-15:]:
        st.text(log)
else:
    st.caption("No logs yet")
