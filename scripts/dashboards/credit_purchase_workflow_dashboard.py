"""
🎟️ Credit Purchase Workflow Dashboard
========================================

Production-ready credit purchase workflow with payment verification.

Workflow:
1. Student requests credit purchase → System generates payment reference
2. Student transfers money with reference code
3. Admin verifies payment → Credits added to student account

Author: Claude Code
Date: 2025-12-11
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Tuple, Optional
import time

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

if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = {
        "step1_student_request": "pending",
        "step2_admin_verify": "pending",
        "step3_check_credits": "pending"
    }

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = None

if "workflow_logs" not in st.session_state:
    st.session_state.workflow_logs = []

# ============================================================================
# HELPER FUNCTIONS
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
            return False, None, f"Login failed: {response.status_code}"

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
            return False, None, f"Login failed: {response.status_code}"

    except Exception as e:
        return False, None, f"Login error: {str(e)}"

def request_credit_purchase(student_token: str, credit_amount: int, amount_eur: float) -> Tuple[bool, dict]:
    """Student requests credit purchase"""
    try:
        # Use cookie-based authentication
        response = requests.post(
            f"{API_BASE_URL}/invoices/request",
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
            f"{API_BASE_URL}/invoices/list?status=pending",
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
            f"{API_BASE_URL}/invoices/{invoice_id}/verify",
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

def reset_workflow():
    """Reset workflow state"""
    st.session_state.workflow_state = {
        "step1_student_request": "pending",
        "step2_admin_verify": "pending",
        "step3_check_credits": "pending"
    }
    st.session_state.invoice_data = None
    st.session_state.workflow_logs = []

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="💳 Credit Purchase Workflow",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# HEADER
# ============================================================================

st.title("💳 Credit Purchase Workflow Dashboard")
st.markdown("**Production-ready:** Student requests → Payment reference → Admin verifies → Credits added")
st.divider()

# ============================================================================
# SIDEBAR: LOGIN
# ============================================================================

with st.sidebar:
    st.header("🔐 Login")

    # Admin Login
    with st.expander("👑 Admin Login", expanded=not st.session_state.admin_token):
        if not st.session_state.admin_token:
            admin_email = st.text_input("Admin Email", value="admin@lfa.com", key="admin_email_input")
            admin_password = st.text_input("Admin Password", type="password", value="admin123", key="admin_password_input")

            if st.button("🔑 Login as Admin", use_container_width=True):
                success, token, message = admin_login(admin_email, admin_password)
                if success:
                    st.session_state.admin_token = token
                    add_log(message, "success")
                    st.success(message)
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

    # Student Login
    with st.expander("🎓 Student Login", expanded=not st.session_state.student_token):
        if not st.session_state.student_token:
            student_email = st.text_input("Student Email", value="student@test.com", key="student_email_input")
            student_password = st.text_input("Student Password", type="password", value="student123", key="student_password_input")

            if st.button("🔑 Login as Student", use_container_width=True):
                success, token, message = student_login(student_email, student_password)
                if success:
                    st.session_state.student_token = token
                    add_log(message, "success")
                    st.success(message)
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

    st.divider()

    # Workflow Control
    st.header("🔄 Workflow Control")
    if st.button("🔄 Reset Workflow", use_container_width=True):
        reset_workflow()
        add_log("Workflow reset", "info")
        st.rerun()

# ============================================================================
# MAIN WORKFLOW: 3 STEPS
# ============================================================================

st.subheader("📋 Workflow: Credit Purchase & Verification")
st.caption("Student requests credits → Admin verifies payment → Credits added")
st.divider()

# 3-column layout for workflow steps
col1, col2, col3 = st.columns(3)

# ============================================================================
# STEP 1: Student Requests Credit Purchase
# ============================================================================

with col1:
    step_status = st.session_state.workflow_state["step1_student_request"]
    status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

    st.markdown(f"### {status_icon} Step 1: Student Request")
    st.caption("**Role:** STUDENT")
    st.caption("**Action:** Request credit purchase")

    if not st.session_state.student_token:
        st.warning("⚠️ Please log in as student first")
    elif step_status == "done":
        st.success("✅ Credit purchase requested!")
        if st.session_state.invoice_data:
            invoice = st.session_state.invoice_data
            st.info(f"**💳 Payment Reference:** `{invoice['payment_reference']}`")
            st.caption(f"Credits: {invoice['credit_amount']}")
            st.caption(f"Amount: €{invoice['amount_eur']}")
    else:
        st.markdown("**💡 Student requests credits**")

        # Get current student info
        if st.session_state.student_token:
            success, user_info = get_user_info(st.session_state.student_token)
            if success:
                st.caption(f"Current balance: **{user_info.get('credit_balance', 0)} credits**")

        credit_amount = st.number_input("Credit Amount", min_value=1, max_value=1000, value=10, key="credit_amount_input")
        amount_eur = st.number_input("Amount (EUR)", min_value=1.0, max_value=10000.0, value=10.0, step=1.0, key="amount_eur_input")

        if st.button("💳 Request Credit Purchase", use_container_width=True, key="request_purchase_btn"):
            st.session_state.workflow_state["step1_student_request"] = "active"

            success, invoice_data = request_credit_purchase(st.session_state.student_token, credit_amount, amount_eur)

            if success:
                st.session_state.invoice_data = invoice_data
                st.session_state.workflow_state["step1_student_request"] = "done"
                st.session_state.workflow_state["step2_admin_verify"] = "active"
                add_log(f"Credit purchase requested: {credit_amount} credits for €{amount_eur}", "success")
                add_log(f"Payment reference: {invoice_data['payment_reference']}", "info")
                st.rerun()
            else:
                st.session_state.workflow_state["step1_student_request"] = "error"
                add_log("Failed to request credit purchase", "error")
                st.error("❌ Failed to request credit purchase")

# ============================================================================
# STEP 2: Admin Verifies Payment
# ============================================================================

with col2:
    step_status = st.session_state.workflow_state["step2_admin_verify"]
    status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

    st.markdown(f"### {status_icon} Step 2: Admin Verify")
    st.caption("**Role:** ADMIN")
    st.caption("**Action:** Verify payment received")

    if st.session_state.workflow_state["step1_student_request"] != "done":
        st.info("⏸️ Waiting for Step 1...")
        st.caption("Student must request credit purchase first.")
    elif not st.session_state.admin_token:
        st.warning("⚠️ Please log in as admin first")
    elif step_status == "done":
        st.success("✅ Payment verified!")
        if st.session_state.invoice_data:
            invoice = st.session_state.invoice_data
            st.caption(f"Invoice ID: {invoice.get('invoice_id', 'N/A')}")
            st.caption(f"Credits added: {invoice.get('credit_amount', 0)}")
    else:
        st.markdown("**💡 Admin checks payment and verifies**")

        if st.session_state.invoice_data:
            invoice = st.session_state.invoice_data
            st.info(f"**Payment Ref:** `{invoice['payment_reference']}`")
            st.caption(f"Amount: €{invoice['amount_eur']}")

        # List pending invoices
        if st.button("🔄 Refresh Pending Invoices", key="refresh_pending_btn"):
            st.rerun()

        if st.session_state.admin_token:
            success, pending_invoices = list_pending_invoices(st.session_state.admin_token)

            if success and pending_invoices:
                st.caption(f"**{len(pending_invoices)} pending invoice(s)**")

                # Find our invoice
                our_invoice = None
                if st.session_state.invoice_data:
                    payment_ref = st.session_state.invoice_data['payment_reference']
                    our_invoice = next((inv for inv in pending_invoices if inv['payment_reference'] == payment_ref), None)

                if our_invoice:
                    st.success(f"✅ Found invoice: {our_invoice['student_name']}")

                    if st.button("✅ Verify Payment", use_container_width=True, key="verify_payment_btn"):
                        st.session_state.workflow_state["step2_admin_verify"] = "active"

                        success, verify_data = verify_invoice_payment(st.session_state.admin_token, our_invoice['id'])

                        if success:
                            st.session_state.workflow_state["step2_admin_verify"] = "done"
                            st.session_state.workflow_state["step3_check_credits"] = "active"
                            add_log(f"Payment verified: {verify_data.get('credits_added', 0)} credits added", "success")
                            st.rerun()
                        else:
                            st.session_state.workflow_state["step2_admin_verify"] = "error"
                            add_log("Failed to verify payment", "error")
                            st.error("❌ Failed to verify payment")
                else:
                    st.warning("⚠️ Invoice not found in pending list")
            elif success:
                st.info("ℹ️ No pending invoices")
            else:
                st.error("❌ Failed to fetch pending invoices")

# ============================================================================
# STEP 3: Check Student Credits
# ============================================================================

with col3:
    step_status = st.session_state.workflow_state["step3_check_credits"]
    status_icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[step_status]

    st.markdown(f"### {status_icon} Step 3: Verify Credits")
    st.caption("**Role:** SYSTEM")
    st.caption("**Action:** Check student credits")

    if st.session_state.workflow_state["step2_admin_verify"] != "done":
        st.info("⏸️ Waiting for Step 2...")
        st.caption("Admin must verify payment first.")
    elif not st.session_state.student_token:
        st.warning("⚠️ Student token missing")
    else:
        st.markdown("**💡 Verify credits were added**")

        if st.button("🔍 Check Credits", use_container_width=True, key="check_credits_btn"):
            st.session_state.workflow_state["step3_check_credits"] = "active"

            success, user_info = get_user_info(st.session_state.student_token)

            if success:
                credit_balance = user_info.get('credit_balance', 0)
                credit_purchased = user_info.get('credit_purchased', 0)

                st.success(f"✅ Credits verified!")
                st.metric("💰 Credit Balance", credit_balance)
                st.metric("🛒 Total Purchased", credit_purchased)

                st.session_state.workflow_state["step3_check_credits"] = "done"
                add_log(f"Credits verified: {credit_balance} available", "success")

                # Check if workflow complete
                if all(status == "done" for status in st.session_state.workflow_state.values()):
                    st.balloons()
                    st.success("🎉 **Complete Credit Purchase Workflow Successful!**")

            else:
                st.session_state.workflow_state["step3_check_credits"] = "error"
                add_log("Failed to check credits", "error")
                st.error("❌ Failed to check credits")

# ============================================================================
# WORKFLOW LOGS
# ============================================================================

st.divider()
st.subheader("📋 Workflow Logs")

if st.session_state.workflow_logs:
    for log in st.session_state.workflow_logs[-10:]:  # Show last 10 logs
        st.text(log)
else:
    st.caption("No logs yet")

# ============================================================================
# WORKFLOW STATUS SUMMARY
# ============================================================================

st.divider()
st.subheader("📊 Workflow Status Summary")

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    status = st.session_state.workflow_state["step1_student_request"]
    icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[status]
    st.metric("Step 1: Student Request", icon)

with status_col2:
    status = st.session_state.workflow_state["step2_admin_verify"]
    icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[status]
    st.metric("Step 2: Admin Verify", icon)

with status_col3:
    status = st.session_state.workflow_state["step3_check_credits"]
    icon = {"pending": "⏸️", "active": "🔵", "done": "✅", "error": "❌"}[status]
    st.metric("Step 3: Verify Credits", icon)
