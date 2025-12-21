#!/usr/bin/env python3
"""
🎮 CLEAN Interactive Backend Testing Dashboard
Professional Streamlit-based API testing tool with real-time progress

Usage:
    streamlit run clean_testing_dashboard.py
"""

import streamlit as st
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"
DB_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Admin account email (for reference only)
ADMIN_EMAIL = "admin@yourcompany.com"

# Session IDs for testing
SESSION_IDS = {
    "ON-SITE": 203,
    "HYBRID": 206,
    "VIRTUAL": 208
}

QUIZ_IDS = {
    "HYBRID": 1,
    "VIRTUAL": 2
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'test_results' not in st.session_state:
    st.session_state.test_results = []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def log_step(message: str, status: str = "info"):
    """Log a test step with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = {"success": "✅", "error": "❌", "info": "ℹ️", "warning": "⚠️"}.get(status, "•")
    st.session_state.test_results.append(f"[{timestamp}] {icon} {message}")
    return message

def login(email: str, password: str) -> Tuple[bool, str, str, str]:
    """Login and return (success, token, email, role)"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            token = response.json()["access_token"]

            # Get user info to verify role
            user_resp = requests.get(
                f"{API_BASE_URL}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            if user_resp.status_code == 200:
                user_data = user_resp.json()
                return True, token, user_data.get('email', ''), user_data.get('role', '')

        return False, "", "", ""
    except Exception as e:
        return False, "", "", ""

def get_headers(token: str) -> Dict[str, str]:
    """Get auth headers"""
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_session_workflow(session_type: str, session_id: int, token: str, progress_placeholder) -> bool:
    """Test complete workflow for a session type"""

    headers = get_headers(token)
    all_passed = True

    # Step 1: Browse sessions
    progress_placeholder.info(f"🔍 Step 1: Browsing {session_type} sessions...")
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/v1/sessions/?session_type={session_type.lower().replace('-', '_')}&limit=10",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200 and resp.json()['total'] > 0:
            log_step(f"Browse {session_type} sessions: SUCCESS", "success")
        else:
            log_step(f"Browse {session_type} sessions: FAILED", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Browse {session_type} sessions: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 2: Create booking
    progress_placeholder.info(f"📝 Step 2: Creating booking for session {session_id}...")
    booking_id = None
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/bookings/",
            headers=headers,
            json={"session_id": session_id},
            timeout=10
        )
        if resp.status_code == 200:
            booking_id = resp.json()['id']
            log_step(f"Create booking: SUCCESS (ID: {booking_id})", "success")
        else:
            log_step(f"Create booking: FAILED - {resp.json().get('detail', 'Unknown error')}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Create booking: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 3: Verify in My Bookings
    progress_placeholder.info(f"🔍 Step 3: Verifying booking in My Bookings...")
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/bookings/me", headers=headers, timeout=10)
        if resp.status_code == 200:
            bookings = resp.json()['bookings']
            found = any(b['id'] == booking_id for b in bookings)
            if found:
                log_step(f"Verify in My Bookings: SUCCESS", "success")
            else:
                log_step(f"Verify in My Bookings: FAILED - Booking not found", "error")
                all_passed = False
        else:
            log_step(f"Verify in My Bookings: FAILED", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Verify in My Bookings: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 4: Get booking details
    if booking_id:
        progress_placeholder.info(f"📋 Step 4: Getting booking details...")
        try:
            resp = requests.get(f"{API_BASE_URL}/api/v1/bookings/{booking_id}", headers=headers, timeout=10)
            if resp.status_code == 200:
                log_step(f"Get booking details: SUCCESS", "success")
            else:
                log_step(f"Get booking details: FAILED", "error")
                all_passed = False
        except Exception as e:
            log_step(f"Get booking details: ERROR - {e}", "error")
            all_passed = False

        time.sleep(0.3)

        # Step 5: Cancel booking
        progress_placeholder.info(f"🗑️ Step 5: Cancelling booking...")
        try:
            resp = requests.delete(f"{API_BASE_URL}/api/v1/bookings/{booking_id}", headers=headers, timeout=10)
            if resp.status_code == 200:
                log_step(f"Cancel booking: SUCCESS", "success")
            else:
                log_step(f"Cancel booking: FAILED", "error")
                all_passed = False
        except Exception as e:
            log_step(f"Cancel booking: ERROR - {e}", "error")
            all_passed = False

    progress_placeholder.empty()
    return all_passed

def test_hybrid_quiz_workflow(token: str, progress_placeholder) -> bool:
    """Test HYBRID session quiz access control"""

    headers = get_headers(token)
    all_passed = True
    quiz_id = QUIZ_IDS["HYBRID"]
    session_id = SESSION_IDS["HYBRID"]

    # Step 1: Try to access quiz without unlock
    progress_placeholder.info("🔍 Step 1: Testing access WITHOUT quiz unlock...")
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/quizzes/{quiz_id}", headers=headers, timeout=10)
        if resp.status_code == 403 and "not yet unlocked" in resp.text.lower():
            log_step("Quiz blocked without unlock: SUCCESS ✓", "success")
        else:
            log_step(f"Quiz blocked without unlock: FAILED - Got {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Quiz access test: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 2: Instructor unlocks quiz
    progress_placeholder.info("🔓 Step 2: Instructor unlocking quiz...")
    try:
        conn = psycopg2.connect(DB_CONN_STRING)
        cur = conn.cursor()
        cur.execute(f"UPDATE sessions SET quiz_unlocked = true WHERE id = {session_id};")
        conn.commit()
        cur.close()
        conn.close()
        log_step("Instructor unlocked quiz: SUCCESS", "success")
    except Exception as e:
        log_step(f"Quiz unlock: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 3: Try to access quiz without attendance
    progress_placeholder.info("🔍 Step 3: Testing access WITHOUT attendance...")
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/quizzes/{quiz_id}", headers=headers, timeout=10)
        if resp.status_code == 403 and "attendance" in resp.text.lower():
            log_step("Quiz blocked without attendance: SUCCESS ✓", "success")
        else:
            log_step(f"Quiz blocked without attendance: FAILED - Got {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Quiz access test: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 4: Get booking and mark attendance
    progress_placeholder.info("✅ Step 4: Marking student PRESENT...")
    try:
        # Get booking
        resp = requests.get(f"{API_BASE_URL}/api/v1/bookings/me", headers=headers, timeout=10)
        bookings = resp.json()['bookings']
        hybrid_booking = next((b for b in bookings if b['session']['id'] == session_id), None)

        if hybrid_booking:
            booking_id = hybrid_booking['id']

            # Mark present
            conn = psycopg2.connect(DB_CONN_STRING)
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO attendance (user_id, session_id, booking_id, status, marked_by, check_in_time)
                SELECT 2, {session_id}, {booking_id}, 'present',
                       (SELECT id FROM users WHERE role = 'INSTRUCTOR' LIMIT 1),
                       NOW()
                ON CONFLICT DO NOTHING
                RETURNING id;
            """)
            result = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            if result:
                log_step(f"Student marked PRESENT: SUCCESS (Attendance ID: {result[0]})", "success")
            else:
                log_step("Student already marked present", "info")
        else:
            log_step("No booking found for HYBRID session", "warning")
            all_passed = False
    except Exception as e:
        log_step(f"Mark attendance: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 5: Access quiz (should work now)
    progress_placeholder.info("🎯 Step 5: Accessing quiz with all requirements met...")
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/quizzes/{quiz_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            log_step("Quiz access with unlock + attendance: SUCCESS ✓", "success")
        else:
            log_step(f"Quiz access: FAILED - Got {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Quiz access: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 6: Start quiz attempt
    progress_placeholder.info("🚀 Step 6: Starting quiz attempt...")
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/quizzes/start",
            headers=headers,
            json={"quiz_id": quiz_id},
            timeout=10
        )
        if resp.status_code == 200:
            attempt_id = resp.json().get('id')
            log_step(f"Quiz attempt started: SUCCESS (Attempt ID: {attempt_id})", "success")
        else:
            log_step(f"Start quiz: FAILED - {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Start quiz: ERROR - {e}", "error")
        all_passed = False

    progress_placeholder.empty()
    return all_passed

def test_virtual_quiz_workflow(token: str, progress_placeholder) -> bool:
    """Test VIRTUAL session quiz access control"""

    headers = get_headers(token)
    all_passed = True
    quiz_id = QUIZ_IDS["VIRTUAL"]
    session_id = SESSION_IDS["VIRTUAL"]

    # Step 1: Try to access quiz before session starts
    progress_placeholder.info("🔍 Step 1: Testing access BEFORE session starts...")
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/quizzes/{quiz_id}", headers=headers, timeout=10)
        if resp.status_code == 400 and "not yet available" in resp.text.lower():
            log_step("Quiz blocked before session starts: SUCCESS ✓", "success")
        else:
            log_step(f"Quiz blocked before start: FAILED - Got {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Quiz access test: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 2: Activate VIRTUAL session
    progress_placeholder.info("⏰ Step 2: Activating VIRTUAL session (setting time window)...")
    try:
        conn = psycopg2.connect(DB_CONN_STRING)
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE sessions
            SET date_start = NOW() - INTERVAL '5 minutes',
                date_end = NOW() + INTERVAL '55 minutes'
            WHERE id = {session_id}
            RETURNING id, title;
        """)
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result:
            log_step(f"VIRTUAL session activated: SUCCESS (Session {result[0]}: {result[1]})", "success")
        else:
            log_step("VIRTUAL session activation: FAILED", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Session activation: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 3: Access quiz (should work now)
    progress_placeholder.info("🎯 Step 3: Accessing quiz WITHIN time window...")
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/quizzes/{quiz_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            log_step("Quiz access within time window: SUCCESS ✓", "success")
        else:
            log_step(f"Quiz access: FAILED - Got {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Quiz access: ERROR - {e}", "error")
        all_passed = False

    time.sleep(0.3)

    # Step 4: Start quiz attempt
    progress_placeholder.info("🚀 Step 4: Starting VIRTUAL quiz attempt...")
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/quizzes/start",
            headers=headers,
            json={"quiz_id": quiz_id},
            timeout=10
        )
        if resp.status_code == 200:
            attempt_id = resp.json().get('id')
            log_step(f"VIRTUAL quiz attempt started: SUCCESS (Attempt ID: {attempt_id})", "success")
        else:
            log_step(f"Start quiz: FAILED - {resp.status_code}", "error")
            all_passed = False
    except Exception as e:
        log_step(f"Start quiz: ERROR - {e}", "error")
        all_passed = False

    progress_placeholder.empty()
    return all_passed

def reset_test_state():
    """Reset test state in database"""
    try:
        conn = psycopg2.connect(DB_CONN_STRING)
        cur = conn.cursor()

        # Delete attendance records FIRST (foreign key constraint)
        cur.execute("DELETE FROM attendance WHERE session_id IN (203, 206, 207, 208);")

        # Delete test student's bookings for test sessions
        cur.execute("""
            DELETE FROM bookings
            WHERE user_id = (SELECT id FROM users WHERE email = 'junior.intern@lfa.com')
            AND session_id IN (203, 206, 207, 208);
        """)

        # Reset HYBRID session
        cur.execute("UPDATE sessions SET quiz_unlocked = false WHERE id = 206;")

        # Reset VIRTUAL session to future time
        cur.execute("""
            UPDATE sessions
            SET date_start = NOW() + INTERVAL '30 hours',
                date_end = NOW() + INTERVAL '32 hours'
            WHERE id = 208;
        """)

        # Delete quiz attempts
        cur.execute("DELETE FROM quiz_attempts WHERE quiz_id IN (1, 2);")

        conn.commit()
        cur.close()
        conn.close()

        return True, "✅ Test state reset successfully (bookings, attendance, quiz state cleared)"
    except Exception as e:
        return False, f"Failed to reset: {e}"

# ============================================================================
# STREAMLIT UI
# ============================================================================

st.set_page_config(
    page_title="Clean Backend Testing Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.title("🎮 Clean Test Dashboard")
    st.markdown("---")

    # Auth Section
    st.subheader("🔐 Authentication")

    if st.session_state.token:
        st.success(f"✅ Logged in: {st.session_state.user_email}")
        st.info(f"Role: {st.session_state.user_role}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_email = None
            st.session_state.user_role = None
            st.rerun()
    else:
        st.warning("⚠️ ADMIN ONLY: This testing dashboard requires administrator credentials.")

        email = st.text_input("Email", value="", placeholder="admin@yourcompany.com")
        password = st.text_input("Password", type="password", value="", placeholder="Enter password")

        if st.button("🔐 Login", use_container_width=True):
            if not email or not password:
                st.error("❌ Please enter both email and password")
            else:
                success, token, user_email, user_role = login(email, password)
                if success:
                    # Verify admin role (case-insensitive)
                    if user_role.upper() != "ADMIN":
                        st.error("🚫 ACCESS DENIED: This dashboard is for administrators only.")
                        st.error(f"Your role: {user_role}")
                        st.stop()

                    st.session_state.token = token
                    st.session_state.user_email = user_email
                    st.session_state.user_role = user_role
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Login failed! Check credentials.")

    st.markdown("---")

    # Reset Button
    if st.button("🔄 Reset Test State", use_container_width=True):
        with st.spinner("Resetting test state..."):
            success, message = reset_test_state()
            if success:
                st.success(message)
            else:
                st.error(message)

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("🎮 Clean Interactive Backend Testing Dashboard")
st.markdown("Professional testing tool with real-time progress tracking")

if not st.session_state.token:
    st.warning("⚠️ Please login from the sidebar to start testing")
    st.info("**ADMIN ACCESS ONLY** - This dashboard requires administrator credentials.")
    st.stop()

# Double-layer protection: Verify admin role (case-insensitive)
if st.session_state.user_role.upper() != "ADMIN":
    st.error("🚫 ACCESS DENIED: This dashboard is for administrators only.")
    st.error(f"Your role: {st.session_state.user_role}")
    st.error("Please contact your system administrator for access.")
    st.session_state.token = None
    st.session_state.user_email = None
    st.session_state.user_role = None
    st.stop()

# Tabs for different test categories
tab1, tab2, tab3, tab4 = st.tabs([
    "📍 Session Workflows",
    "🎯 HYBRID Quiz Tests",
    "🌐 VIRTUAL Quiz Tests",
    "📊 Test Results"
])

# ============================================================================
# TAB 1: Session Workflows
# ============================================================================

with tab1:
    st.header("📍 Session Type Workflow Tests")
    st.markdown("Test complete booking workflow for ON-SITE, HYBRID, and VIRTUAL sessions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🏢 Test ON-SITE", use_container_width=True):
            st.session_state.test_results = []
            progress = st.empty()

            with st.spinner("Running ON-SITE workflow test..."):
                success = test_session_workflow("ON-SITE", SESSION_IDS["ON-SITE"], st.session_state.token, progress)

            if success:
                st.success("✅ ON-SITE workflow: ALL TESTS PASSED")
            else:
                st.error("❌ ON-SITE workflow: SOME TESTS FAILED")

    with col2:
        if st.button("🔀 Test HYBRID", use_container_width=True):
            st.session_state.test_results = []
            progress = st.empty()

            with st.spinner("Running HYBRID workflow test..."):
                success = test_session_workflow("HYBRID", SESSION_IDS["HYBRID"], st.session_state.token, progress)

            if success:
                st.success("✅ HYBRID workflow: ALL TESTS PASSED")
            else:
                st.error("❌ HYBRID workflow: SOME TESTS FAILED")

    with col3:
        if st.button("🌐 Test VIRTUAL", use_container_width=True):
            st.session_state.test_results = []
            progress = st.empty()

            with st.spinner("Running VIRTUAL workflow test..."):
                success = test_session_workflow("VIRTUAL", SESSION_IDS["VIRTUAL"], st.session_state.token, progress)

            if success:
                st.success("✅ VIRTUAL workflow: ALL TESTS PASSED")
            else:
                st.error("❌ VIRTUAL workflow: SOME TESTS FAILED")

    st.markdown("---")

    # Run all session tests
    if st.button("🚀 Run ALL Session Tests", use_container_width=True):
        st.session_state.test_results = []

        results = {}
        for session_type in ["ON-SITE", "HYBRID", "VIRTUAL"]:
            st.markdown(f"### Testing {session_type} Session...")
            progress = st.empty()

            with st.spinner(f"Running {session_type} workflow test..."):
                success = test_session_workflow(
                    session_type,
                    SESSION_IDS[session_type],
                    st.session_state.token,
                    progress
                )
                results[session_type] = success

            time.sleep(0.5)

        st.markdown("---")
        st.subheader("📊 Summary")

        for session_type, success in results.items():
            if success:
                st.success(f"✅ {session_type}: PASSED")
            else:
                st.error(f"❌ {session_type}: FAILED")

# ============================================================================
# TAB 2: HYBRID Quiz Tests
# ============================================================================

with tab2:
    st.header("🎯 HYBRID Session Quiz Access Control")
    st.markdown("Test quiz access with **unlock + attendance** requirements")

    st.info("""
    **HYBRID Quiz Requirements:**
    1. ✅ Confirmed booking
    2. 🔓 Instructor unlocks quiz
    3. ✅ Student marked PRESENT on attendance sheet
    """)

    if st.button("🧪 Run HYBRID Quiz Test", use_container_width=True):
        st.session_state.test_results = []
        progress = st.empty()

        with st.spinner("Running HYBRID quiz access control test..."):
            success = test_hybrid_quiz_workflow(st.session_state.token, progress)

        if success:
            st.success("✅ HYBRID Quiz Test: ALL CHECKS PASSED")
        else:
            st.error("❌ HYBRID Quiz Test: SOME CHECKS FAILED")

# ============================================================================
# TAB 3: VIRTUAL Quiz Tests
# ============================================================================

with tab3:
    st.header("🌐 VIRTUAL Session Quiz Access Control")
    st.markdown("Test quiz access with **time window** requirements")

    st.info("""
    **VIRTUAL Quiz Requirements:**
    1. ✅ Confirmed booking
    2. ⏰ Current time within session window (date_start ≤ NOW ≤ date_end)
    """)

    if st.button("🧪 Run VIRTUAL Quiz Test", use_container_width=True):
        st.session_state.test_results = []
        progress = st.empty()

        with st.spinner("Running VIRTUAL quiz access control test..."):
            success = test_virtual_quiz_workflow(st.session_state.token, progress)

        if success:
            st.success("✅ VIRTUAL Quiz Test: ALL CHECKS PASSED")
        else:
            st.error("❌ VIRTUAL Quiz Test: SOME CHECKS FAILED")

# ============================================================================
# TAB 4: Test Results
# ============================================================================

with tab4:
    st.header("📊 Test Results")

    if st.session_state.test_results:
        st.markdown("### Latest Test Run:")

        # Count successes and failures
        success_count = sum(1 for r in st.session_state.test_results if "✅" in r)
        error_count = sum(1 for r in st.session_state.test_results if "❌" in r)
        total_count = len(st.session_state.test_results)

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Steps", total_count)
        with col2:
            st.metric("Passed", success_count, delta=None, delta_color="normal")
        with col3:
            st.metric("Failed", error_count, delta=None, delta_color="inverse")

        st.markdown("---")

        # Display test log
        st.markdown("### Test Log:")
        for result in st.session_state.test_results:
            if "✅" in result:
                st.success(result)
            elif "❌" in result:
                st.error(result)
            elif "⚠️" in result:
                st.warning(result)
            else:
                st.info(result)

        # Clear results button
        if st.button("🗑️ Clear Results"):
            st.session_state.test_results = []
            st.rerun()
    else:
        st.info("No test results yet. Run a test from the tabs above!")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🎮 Clean Backend Testing Dashboard v2.0 | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
