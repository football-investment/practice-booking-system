"""
LFA Player Dashboard - Player-Specific Training Hub
Shows age category, available semesters, enrollment status, and upcoming sessions
"""

import streamlit as st
from datetime import datetime, date
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY
from api_helpers_general import get_current_user
from utils.age_category import get_age_category_for_season

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - LFA Player",
    page_icon="⚽",
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Authentication check
if SESSION_TOKEN_KEY not in st.session_state:
    st.error("Not authenticated. Please login first.")
    st.switch_page("🏠_Home.py")
    st.stop()

token = st.session_state[SESSION_TOKEN_KEY]

# ✅ CRITICAL FIX: Always fetch fresh user data from API on page load
# This ensures onboarding_completed status is ALWAYS up-to-date
success, error, user = get_current_user(token)
if not success:
    st.error(f"Failed to load user data: {error}")
    st.session_state.clear()
    st.switch_page("🏠_Home.py")
    st.stop()

# Update session state with fresh data
st.session_state[SESSION_USER_KEY] = user

# Check student role
if user.get('role') != 'student':
    st.error("Access denied. Student role required.")
    st.stop()

# ============================================================================
# ONBOARDING CHECK - Ensure user has completed onboarding
# ============================================================================

# Get user's LFA_FOOTBALL_PLAYER license
user_licenses = user.get('licenses', [])
lfa_license = next(
    (lic for lic in user_licenses
     if lic.get('specialization_type') == 'LFA_FOOTBALL_PLAYER'),
    None
)

# If license not found, redirect to hub
if not lfa_license:
    st.error("LFA Player license not found. Please unlock the specialization first.")
    if st.button("Go to Specialization Hub"):
        st.switch_page("pages/Specialization_Hub.py")
    st.stop()

# If onboarding not completed, redirect to onboarding
if not lfa_license.get('onboarding_completed', False):
    st.info("⚠️ Please complete onboarding first to access your dashboard.")
    if st.button("Complete Onboarding Now"):
        st.switch_page("pages/LFA_Player_Onboarding.py")
    st.stop()

# ============================================================================

# Custom CSS for LFA Player branding
st.markdown("""
<style>
    /* LFA Player brand colors */
    .lfa-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white !important;
        margin-bottom: 2rem;
    }

    .lfa-header h1 {
        color: white !important;
        background: none !important;
        background-image: none !important;
        -webkit-text-fill-color: white !important;
        -webkit-background-clip: unset !important;
    }

    .lfa-header p {
        color: white !important;
    }

    .age-category-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        margin: 0.5rem;
    }

    .badge-pre { background: #fef3c7; color: #92400e; }
    .badge-youth { background: #dbeafe; color: #1e40af; }
    .badge-amateur { background: #d1fae5; color: #065f46; }
    .badge-pro { background: #fce7f3; color: #9f1239; }

    .skill-bar {
        background: #e5e7eb;
        border-radius: 10px;
        height: 24px;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
    }

    .skill-fill {
        background: linear-gradient(90deg, #3b82f6 0%, #1e3a8a 100%);
        height: 100%;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 8px;
        color: white;
        font-size: 0.875rem;
        font-weight: 600;
    }

    .position-badge {
        display: inline-block;
        padding: 0.75rem 1.5rem;
        border-radius: 25px;
        font-size: 1.25rem;
        font-weight: 700;
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: #78350f;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_age(birth_date_str):
    """Calculate age from birth date string"""
    if not birth_date_str:
        return None
    try:
        if isinstance(birth_date_str, str):
            birth_date = datetime.fromisoformat(birth_date_str.replace('Z', '+00:00')).date()
        else:
            birth_date = birth_date_str
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        return age
    except:
        return None

def get_age_category_info(category):
    """Get display info for age category"""
    info = {
        "PRE": {
            "name": "PRE (5-13 years)",
            "description": "Foundation Football Development",
            "frequency": "Monthly semesters",
            "color": "badge-pre",
            "emoji": "🌱"
        },
        "YOUTH": {
            "name": "YOUTH (14-18 years)",
            "description": "Youth Competitive Training",
            "frequency": "Quarterly semesters",
            "color": "badge-youth",
            "emoji": "⚡"
        },
        "AMATEUR": {
            "name": "AMATEUR (14+ years)",
            "description": "Amateur Competitive Play",
            "frequency": "Bi-annual semesters",
            "color": "badge-amateur",
            "emoji": "🎯"
        },
        "PRO": {
            "name": "PRO (14+ years)",
            "description": "Professional Pathway Training",
            "frequency": "Annual semesters",
            "color": "badge-pro",
            "emoji": "🏆"
        }
    }
    return info.get(category, {})

def get_lfa_player_license(user):
    """Extract LFA_PLAYER license from user data"""
    licenses = user.get('licenses', [])
    for license in licenses:
        spec_type = license.get('specialization_type', '')
        if spec_type in ['LFA_PLAYER', 'LFA_FOOTBALL_PLAYER']:
            return license
    return None

def _display_enrollment_card(enrollment: dict, icon: str):
    """Display enrollment card with sessions and results/rewards for tournaments"""
    semester_name = enrollment.get("semester_name", "N/A")
    sessions = enrollment.get("sessions", [])
    enrollment_id = enrollment.get("enrollment_id", 0)
    semester_id = enrollment.get("semester_id")

    # Check if this is a tournament and get status
    semester_data = enrollment.get("semester", {})
    tournament_status = semester_data.get("tournament_status")
    is_tournament = icon == "🏆"

    with st.expander(f"{icon} {semester_name} ({len(sessions)} sessions)", expanded=False):
        # Show tournament status if available
        if is_tournament and tournament_status:
            status_badge_color = {
                "COMPLETED": "#10b981",  # Green
                "REWARDS_DISTRIBUTED": "#8b5cf6",  # Purple
                "IN_PROGRESS": "#f59e0b",  # Orange
                "UPCOMING": "#3b82f6",  # Blue
            }.get(tournament_status, "#6b7280")

            st.markdown(f"""
            <div style="background: {status_badge_color};
                        color: white;
                        padding: 0.5rem 1rem;
                        border-radius: 6px;
                        text-align: center;
                        font-weight: 600;
                        margin-bottom: 1rem;">
                📊 Status: {tournament_status.replace('_', ' ')}
            </div>
            """, unsafe_allow_html=True)

        # Display sessions (if any)
        if sessions:
            for session in sessions:
                is_booked = session.get("is_booked", False)
                date_str = session.get("date", "N/A")
                start_time = session.get("start_time", "N/A")
                end_time = session.get("end_time", "N/A")
                location = session.get("location", {})

                status_icon = "✅" if is_booked else "⭕"
                status_text = "Booked" if is_booked else "Not booked"
                bg_color = "#d1fae5" if is_booked else "#f3f4f6"

                # Location display
                location_text = "Location TBD"
                if location:
                    location_text = location.get('location_name', location.get('location_city', 'N/A'))

                st.markdown(f"""
                <div style="background: {bg_color};
                            padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                    <div style="font-weight: 600; margin-bottom: 0.25rem; color: #1f2937;">
                        {status_icon} {date_str} | {start_time} - {end_time}
                    </div>
                    <div style="font-size: 0.9rem; color: #6b7280;">
                        📍 {location_text}
                    </div>
                    <div style="font-size: 0.85rem; color: #9ca3af; margin-top: 0.25rem;">
                        {status_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ No sessions scheduled yet.")

        # ========================================================================
        # TOURNAMENT RESULTS & REWARDS (for COMPLETED/REWARDS_DISTRIBUTED)
        # ========================================================================
        if is_tournament and tournament_status in ["COMPLETED", "REWARDS_DISTRIBUTED"]:
            st.markdown("---")
            st.markdown("### 🏆 Tournament Results & Rewards")

            # Fetch tournament results and rewards
            token = st.session_state.get('token')
            if token and semester_id:
                try:
                    import requests
                    from config import API_BASE_URL, API_TIMEOUT

                    # Get current user to fetch rankings and rewards
                    user_id = st.session_state.get(SESSION_USER_KEY, {}).get('id')

                    if user_id:
                        # Fetch tournament rankings
                        rankings_response = requests.get(
                            f"{API_BASE_URL}/api/v1/tournaments/{semester_id}/rankings",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )

                        if rankings_response.status_code == 200:
                            rankings_data = rankings_response.json().get('rankings', [])
                            user_ranking = next((r for r in rankings_data if r.get('user_id') == user_id), None)

                            if user_ranking:
                                rank = user_ranking.get('rank')
                                points = user_ranking.get('points', 0)

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("🏅 Your Rank", f"#{rank}")
                                with col2:
                                    st.metric("⚽ Points", points)

                        # Fetch credit transactions to find tournament rewards
                        user_response = requests.get(
                            f"{API_BASE_URL}/api/v1/users/me",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )

                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            credit_transactions = user_data.get('credit_transactions', [])

                            # Find tournament reward transactions
                            tournament_rewards = [
                                tx for tx in credit_transactions
                                if tx.get('transaction_type') == 'TOURNAMENT_REWARD' and
                                tx.get('semester_id') == semester_id
                            ]

                            if tournament_rewards:
                                st.markdown("---")
                                st.markdown("#### 💰 Rewards Received")

                                total_credits = sum(tx.get('amount', 0) for tx in tournament_rewards)

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("💎 Credits Earned", f"+{total_credits}")
                                with col2:
                                    # TODO: XP tracking not implemented yet
                                    st.caption("⭐ XP: Coming soon")

                                # Show transaction details
                                with st.expander("📜 Transaction Details", expanded=False):
                                    for tx in tournament_rewards:
                                        st.caption(f"• {tx.get('description', 'Reward')} - **{tx.get('amount')} credits**")
                            else:
                                st.info("ℹ️ No rewards distributed yet for this tournament")

                except Exception as e:
                    st.warning(f"⚠️ Could not load tournament results: {str(e)}")

        # Enrollment actions
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"📖 View Details", key=f"view_{enrollment_id}", use_container_width=True):
                st.info("Detailed view coming soon!")
        with col2:
            if st.button(f"🗑️ Unenroll", key=f"unenroll_{enrollment_id}", use_container_width=True, type="secondary"):
                # Show unenrollment dialog
                st.session_state['unenroll_tournament_id'] = tournament_id
                st.session_state['unenroll_tournament_name'] = tournament_name
                st.session_state['unenroll_enrollment_id'] = enrollment_id
                st.session_state['show_unenroll_dialog'] = True
                st.rerun()

def parse_motivation_scores(license):
    """Parse motivation_scores JSON from license"""
    if not license:
        return None

    motivation_scores = license.get('motivation_scores')
    if not motivation_scores:
        return None

    # If it's already a dict, return it
    if isinstance(motivation_scores, dict):
        return motivation_scores

    # If it's a string, try to parse it
    if isinstance(motivation_scores, str):
        try:
            import json
            return json.loads(motivation_scores)
        except:
            return None

    return None


@st.dialog("🗑️ Unenroll from Tournament")
def show_unenroll_dialog():
    """Dialog for unenrolling from tournament with credit refund (50% penalty)"""
    tournament_id = st.session_state.get('unenroll_tournament_id')
    tournament_name = st.session_state.get('unenroll_tournament_name', 'Unknown Tournament')
    enrollment_id = st.session_state.get('unenroll_enrollment_id')

    st.warning("⚠️ **Warning: Unenrollment Penalty**")
    st.markdown(f"""
    You are about to unenroll from:
    **{tournament_name}**

    **Credit Refund Policy:**
    - 💰 You will receive a **50% refund**
    - 💸 **50% penalty** will be deducted

    Example:
    - Enrollment cost: 500 credits
    - Refund: 250 credits (50%)
    - Penalty: 250 credits (lost)
    """)

    reason = st.text_area(
        "Reason for unenrollment (optional)",
        placeholder="e.g., Schedule conflict, personal reasons, etc.",
        help="Providing a reason helps us improve our services"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            st.session_state.pop('unenroll_tournament_id', None)
            st.session_state.pop('unenroll_tournament_name', None)
            st.session_state.pop('unenroll_enrollment_id', None)
            st.session_state.pop('show_unenroll_dialog', None)
            st.rerun()

    with col2:
        if st.button("✅ Confirm Unenroll", use_container_width=True, type="primary"):
            # Call unenroll API
            token = st.session_state.get("token")
            if not token:
                st.error("Authentication token missing. Please log in again.")
                return

            try:
                import requests
                response = requests.delete(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/unenroll",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    result = response.json()
                    refund_amount = result.get('refund_amount', 0)
                    penalty_amount = result.get('penalty_amount', 0)
                    credits_remaining = result.get('credits_remaining', 0)
                    bookings_removed = result.get('bookings_removed', 0)

                    st.success(f"""
                    ✅ **Successfully unenrolled from tournament!**

                    📊 **Transaction Summary:**
                    - Refund: {refund_amount} credits (50%)
                    - Penalty: {penalty_amount} credits (50%)
                    - Bookings removed: {bookings_removed}
                    - Final balance: {credits_remaining} credits
                    """)

                    # Clear session state
                    st.session_state.pop('unenroll_tournament_id', None)
                    st.session_state.pop('unenroll_tournament_name', None)
                    st.session_state.pop('unenroll_enrollment_id', None)
                    st.session_state.pop('show_unenroll_dialog', None)

                    # Wait and reload
                    import time
                    time.sleep(2)
                    st.rerun()

                else:
                    error_detail = response.json().get('detail', 'Unknown error')
                    st.error(f"❌ Unenrollment failed: {error_detail}")

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Please try again.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Player')}!")
    st.caption(f"⚽ **LFA Football Player**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    # Credits display
    st.markdown("**💰 Credits**")
    st.metric("Balance", user.get('credit_balance', 0))

    st.markdown("---")

    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Hub", disabled=True, use_container_width=True):
            pass  # Already on Hub
    with col2:
        if st.button("👤 Profile", use_container_width=True):
            st.switch_page("pages/My_Profile.py")
    with col3:
        if st.button("💳 Credits", use_container_width=True):
            st.switch_page("pages/My_Credits.py")

    st.markdown("---")

    # Refresh and Logout buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True, help="Reload data"):
            # Refresh user data from API
            success, error, updated_user = get_current_user(token)
            if success:
                st.session_state[SESSION_USER_KEY] = updated_user
            st.rerun()
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("🏠_Home.py")

# ============================================================================
# MAIN CONTENT
# ============================================================================

# Get LFA Player license
lfa_license = get_lfa_player_license(user)

if not lfa_license:
    st.error("⚠️ LFA Player license not found. Please unlock this specialization first.")
    if st.button("🔓 Go to Specialization Hub"):
        st.switch_page("pages/Specialization_Hub.py")
    st.stop()

# Calculate age and category
# Age category uses season start date (July 1) - stays fixed for entire season
date_of_birth = user.get('date_of_birth')
age_category = get_age_category_for_season(date_of_birth)
age = calculate_age(date_of_birth)  # Still show current age for display

# get_age_category_for_season() automatically determines category based on age AT SEASON START:
# - PRE: 5-13 years old on July 1
# - YOUTH: 14-17 years old on July 1
# - Amateur: 18+ years old on July 1 (default for all adults)
# - Pro: 18+ years old (ONLY if instructor/admin manually sets it)
#
# SEASON LOCK: Category is FIXED for entire season (July 1 - June 30)
# Example: If user turns 18 in December, they remain YOUTH until next July 1

category_info = get_age_category_info(age_category) if age_category else {}

# Parse motivation scores (position, skills, etc.)
motivation_data = parse_motivation_scores(lfa_license)

# ============================================================================
# HEADER
# ============================================================================

st.markdown(f"""
<div class="lfa-header">
    <h1 style="color: white; margin: 0;">⚽ LFA Football Player Dashboard</h1>
    <p style="color: white; font-size: 1.1rem; margin-top: 0.5rem;">Your personalized training and development hub</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# PLAYER INFO SECTION
# ============================================================================

st.markdown("### 👤 Player Information")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Age**")
    if age:
        st.markdown(f"<h2 style='color: #1e3a8a; margin: 0;'>{age} years</h2>", unsafe_allow_html=True)
    else:
        st.warning("Age not set. Please update your profile.")

with col2:
    st.markdown("**Category**")
    if age_category and category_info:
        st.markdown(f"""
        <div class="age-category-badge {category_info['color']}">
            {category_info['emoji']} {age_category}
        </div>
        """, unsafe_allow_html=True)
        st.caption(category_info['description'])
    else:
        st.warning("Category unavailable")

with col3:
    st.markdown("**Position**")
    if motivation_data and 'position' in motivation_data:
        position = motivation_data['position']
        st.markdown(f"""
        <div class="position-badge">
            {position}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Position not set")

st.divider()

# ============================================================================
# SKILLS SECTION
# ============================================================================

if motivation_data and 'initial_self_assessment' in motivation_data:
    st.markdown("### ⚡ Your Football Skills")
    st.caption("Self-assessment from onboarding")

    skills = motivation_data['initial_self_assessment']

    # Display skills in 2 columns
    col1, col2 = st.columns(2)

    skill_names = list(skills.keys())
    mid_point = len(skill_names) // 2

    with col1:
        for skill_name in skill_names[:mid_point]:
            skill_value = skills[skill_name]
            percentage = (skill_value / 10) * 100

            st.markdown(f"**{skill_name.title()}**")
            st.markdown(f"""
            <div class="skill-bar">
                <div class="skill-fill" style="width: {percentage}%;">
                    {skill_value}/10
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        for skill_name in skill_names[mid_point:]:
            skill_value = skills[skill_name]
            percentage = (skill_value / 10) * 100

            st.markdown(f"**{skill_name.title()}**")
            st.markdown(f"""
            <div class="skill-bar">
                <div class="skill-fill" style="width: {percentage}%;">
                    {skill_value}/10
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Average skill level
    if 'average_skill_level' in motivation_data:
        avg_skill = motivation_data['average_skill_level']
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.metric("Average Skill Level", f"{avg_skill:.1f}/100", help="Based on your self-assessment")

st.divider()

# ============================================================================
# SEMESTER ENROLLMENT SECTION - Three-Tier Parallel Enrollment
# ============================================================================

st.markdown("### 📅 Training Programs")

if age_category and category_info:
    st.info(f"**{category_info['emoji']} {category_info['name']}** - {category_info['frequency']}")
else:
    st.warning("⚠️ Age category not determined. Please set your date of birth in your profile.")

# Import enrollment helpers
from api_helpers_enrollments import get_user_schedule, get_enrollments_by_type
from components.enrollment_conflict_warning import display_schedule_conflicts_summary

# Fetch user's complete schedule
success, error, schedule_data = get_user_schedule(token)

if not success:
    st.error(f"Failed to load schedule: {error}")
elif schedule_data:
    # Get enrollments grouped by type
    enrollments = schedule_data.get("enrollments", [])
    grouped_enrollments = get_enrollments_by_type(enrollments)

    # Summary header
    total_sessions = schedule_data.get("total_sessions", 0)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #3b82f6 0%, #1e3a8a 100%);
                padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: white;">📅 Your Schedule</h3>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            {len(enrollments)} active enrollment(s) | {total_sessions} total session(s)
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Four-tab interface
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🏆 My Tournaments ({len(grouped_enrollments['TOURNAMENT'])})",
        f"🌍 Browse Tournaments",
        f"📅 Mini Seasons ({len(grouped_enrollments['MINI_SEASON'])})",
        f"🏫 Academy Season ({len(grouped_enrollments['ACADEMY_SEASON'])})"
    ])

    with tab1:
        st.markdown("#### 🏆 My Tournament Enrollments")
        st.caption("One-day competitive events you're enrolled in")

        if grouped_enrollments['TOURNAMENT']:
            for enrollment in grouped_enrollments['TOURNAMENT']:
                _display_enrollment_card(enrollment, "🏆")
        else:
            st.info("No active tournament enrollments.\n\nTournaments are one-day competitive events. Browse available tournaments in the '🌍 Browse Tournaments' tab.")

    with tab2:
        st.markdown("#### 🌍 Browse Worldwide Tournaments")
        st.caption("Discover and enroll in competitive football tournaments")

        from components.tournaments.tournament_browser import render_tournament_browser
        render_tournament_browser(token, user)

    with tab3:
        st.markdown("#### 📅 Mini Season Enrollments")
        st.caption("Monthly (PRE) or Quarterly (YOUTH) training programs")

        if grouped_enrollments['MINI_SEASON']:
            for enrollment in grouped_enrollments['MINI_SEASON']:
                _display_enrollment_card(enrollment, "📅")
        else:
            st.info("No active mini season enrollments.\n\nMini Seasons are short-term structured training programs:\n- PRE: Monthly cycles (M01-M12)\n- YOUTH: Quarterly cycles (Q1-Q4)")

    with tab4:
        st.markdown("#### 🏫 Academy Season Enrollments")
        st.caption("Full-year commitment (July 1 - June 30)")

        if grouped_enrollments['ACADEMY_SEASON']:
            for enrollment in grouped_enrollments['ACADEMY_SEASON']:
                _display_enrollment_card(enrollment, "🏫")
        else:
            st.info("No active academy season enrollments.\n\nAcademy Season is a full-year intensive program:\n- Duration: July 1 to June 30\n- Only available at CENTER locations\n- Higher cost, comprehensive training\n- Age category locked at season start")
else:
    st.info("📭 No enrollments yet. Enroll in a training program to get started!")

st.divider()

# ============================================================================
# UPCOMING SESSIONS SECTION
# ============================================================================

st.markdown("### 📆 Upcoming Sessions")

# TODO: Add upcoming sessions display
st.info("🚧 **Session schedule coming soon!**\n\nHere you will see:\n- Your next training sessions\n- Location and time details\n- Instructor information\n- Check-in status")

st.divider()

# ============================================================================
# MOTIVATION & GOALS
# ============================================================================

if motivation_data and ('goals' in motivation_data or 'motivation' in motivation_data):
    st.markdown("### 🎯 Your Goals & Motivation")

    col1, col2 = st.columns(2)

    with col1:
        if 'goals' in motivation_data and motivation_data['goals']:
            # Map goal keys to human-readable text
            goals_map = {
                "improve_skills": "Improve my technical skills",
                "play_higher_level": "Play at a higher competitive level",
                "become_professional": "Become a professional player",
                "team_football": "Join a football team",
                "fitness_health": "Stay fit and healthy through football",
                "enjoy_game": "Simply enjoy playing the game"
            }
            goal_text = goals_map.get(motivation_data['goals'], motivation_data['goals'])

            st.markdown("**Goals**")
            st.info(goal_text)

    with col2:
        if 'motivation' in motivation_data and motivation_data['motivation']:
            st.markdown("**Motivation**")
            st.success(motivation_data['motivation'])

# ============================================================================
# DIALOGS (triggered by session state)
# ============================================================================

# Show unenroll dialog if triggered
if st.session_state.get('show_unenroll_dialog'):
    show_unenroll_dialog()

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(f"LFA Player Dashboard | License Level: {lfa_license.get('current_level', 1)} | XP: {lfa_license.get('xp_balance', 0)}")
