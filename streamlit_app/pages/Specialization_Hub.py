"""
Specialization Hub - Student Landing Page
Adapted from hub_specializations.html

Students unlock specializations (100 credits each) to access training programs.
Currently available: LFA Football Player only
"""

import streamlit as st
from datetime import datetime, date
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SPECIALIZATIONS
from api_helpers_general import get_current_user, unlock_specialization
from components.credits.credit_purchase_button import render_credit_purchase_button
from components.credits.credit_purchase_form import render_credit_purchase_form
from components.credits.coupon_redemption import render_coupon_redemption

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - Specialization Hub",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CUSTOM_CSS to hide page navigation list
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Authentication check
if SESSION_TOKEN_KEY not in st.session_state:
    st.error("Please log in first")
    st.switch_page("🏠_Home.py")
    st.stop()

token = st.session_state[SESSION_TOKEN_KEY]

# ✅ CRITICAL FIX: Always fetch fresh user data from API on page load
# This ensures licenses are ALWAYS up-to-date after unlock
success, error, user = get_current_user(token)
if not success:
    st.error(f"Failed to load user data: {error}")
    st.session_state.clear()
    st.switch_page("🏠_Home.py")
    st.stop()

# Update session state with fresh data
st.session_state[SESSION_USER_KEY] = user

# Only students can access this page
if user.get('role') != 'student':
    st.error("This page is for students only")
    st.stop()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Student')}!")
    st.caption(f"Role: **Student**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    # Credits display
    st.markdown("**💰 Credits**")
    st.metric("Balance", user.get('credit_balance', 0))

    st.markdown("---")

    # Navigation buttons
    if st.button("👤 My Profile", use_container_width=True):
        st.switch_page("pages/My_Profile.py")

    if st.button("💰 My Credits", use_container_width=True):
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

# Custom CSS (adapted from hub_specializations.html)
st.markdown("""
<style>
    /* Header styling */
    .stApp header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    /* Card styling */
    .spec-card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 1.5rem;
        border: 2px solid #e2e8f0;
    }

    .spec-card.unlocked {
        border: 3px solid #52c41a;
    }

    .spec-card.coming-soon {
        opacity: 0.6;
        border: 2px solid #cbd5e0;
    }

    .spec-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }

    .spec-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 0.5rem;
    }

    .spec-age {
        color: #718096;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }

    .spec-description {
        color: #4a5568;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }

    .cost-badge {
        background: #ffd700;
        color: #2d3748;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 1rem;
    }

    .unlocked-badge {
        background: #52c41a;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }

    .coming-soon-badge {
        background: #cbd5e0;
        color: #4a5568;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(f"## Welcome, {user.get('name', 'Student')}! 👋")
st.caption(f"{user.get('email')} · Role: Student")

st.divider()

# ============================================================================
# SPECIALIZATION SELECTION
# ============================================================================

# Page title
st.title("🎓 Choose Your Specialization")
st.markdown("**Unlock specializations to access training programs and semesters.** Each specialization costs **100 credits**.")

st.divider()

# Info banner
user_licenses = user.get('licenses', [])

# A license is "unlocked" if it's active and payment is verified
unlocked_specs = [
    lic.get('specialization_type')
    for lic in user_licenses
    if lic.get('is_active') and lic.get('payment_verified')
]
credit_balance = user.get('credit_balance', 0)

st.info(f"💡 You have **{len(unlocked_specs)} unlocked specialization(s)** · 4 total specializations available")

st.divider()

# ============================================================================
# SPECIALIZATION CARDS
# ============================================================================

# Calculate user age for age-based validation
user_age = user.get('age')  # Age property from User model

# Age requirements mapping
age_requirements_map = {
    "LFA_PLAYER": 5,
    "INTERNSHIP": 18,
    "GANCUJU_PLAYER": 5,
    "LFA_COACH": 14
}

# Define specializations (ALL VISIBLE - business requirement)
specializations = [
    {
        "type": "LFA_PLAYER",
        "icon": "⚽",
        "name": "LFA Football Player",
        "age_requirement": "Ages 5-99",
        "min_age": 5,
        "description": "Modern football training with age-specific programs: PRE (5-13), YOUTH (14-18), AMATEUR (14+), and PRO (14+, master-led)",
        "is_available": True,  # Development status
        "is_unlocked": "LFA_FOOTBALL_PLAYER" in unlocked_specs or "LFA_PLAYER" in unlocked_specs or any(spec.startswith('LFA_PLAYER_') for spec in unlocked_specs),
        "meets_age_req": user_age is not None and user_age >= 5  # Age validation
    },
    {
        "type": "INTERNSHIP",
        "icon": "💼",
        "name": "Internship",
        "age_requirement": "Ages 18+",
        "min_age": 18,
        "description": "Build your startup career from zero to co-founder through hands-on internship program",
        "is_available": False,  # Coming soon (development)
        "is_unlocked": "INTERNSHIP" in unlocked_specs,
        "meets_age_req": user_age is not None and user_age >= 18
    },
    {
        "type": "GANCUJU_PLAYER",
        "icon": "🥋",
        "name": "GānCuju Player",
        "age_requirement": "Ages 5+",
        "min_age": 5,
        "description": "Master the 4000-year-old Chinese football art with authentic Ganball™ equipment and belt system",
        "is_available": False,  # Coming soon (development)
        "is_unlocked": "GANCUJU_PLAYER" in unlocked_specs,
        "meets_age_req": user_age is not None and user_age >= 5
    },
    {
        "type": "LFA_COACH",
        "icon": "👨‍🏫",
        "name": "LFA Coach",
        "age_requirement": "Ages 14+",
        "min_age": 14,
        "description": "Become a certified football coach with LFA methodology and teaching license",
        "is_available": False,  # Coming soon (development)
        "is_unlocked": "LFA_COACH" in unlocked_specs,
        "meets_age_req": user_age is not None and user_age >= 14
    }
]

# Display specialization cards (2 columns)
col1, col2 = st.columns(2)

for idx, spec in enumerate(specializations):
    with (col1 if idx % 2 == 0 else col2):
        # Card container
        card_class = "spec-card"
        if spec['is_unlocked']:
            card_class += " unlocked"
        elif not spec['is_available']:
            card_class += " coming-soon"

        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

            # Icon
            st.markdown(f'<div class="spec-icon">{spec["icon"]}</div>', unsafe_allow_html=True)

            # Title
            st.markdown(f'<div class="spec-title">{spec["name"]}</div>', unsafe_allow_html=True)

            # Age requirement
            st.markdown(f'<div class="spec-age">{spec["age_requirement"]}</div>', unsafe_allow_html=True)

            # Description
            st.markdown(f'<div class="spec-description">{spec["description"]}</div>', unsafe_allow_html=True)

            # Cost badge (if not unlocked)
            if not spec['is_unlocked']:
                st.markdown('<div class="cost-badge">💰 100 Credits</div>', unsafe_allow_html=True)

            # Action buttons
            if spec['is_unlocked']:
                # UNLOCKED - Enter button
                st.markdown('<div class="unlocked-badge">✅ UNLOCKED</div>', unsafe_allow_html=True)

                if st.button(f"🚀 ENTER {spec['name']}", key=f"enter_{spec['type']}", use_container_width=True, type="primary"):
                    # Redirect to specialization-specific dashboard OR onboarding if not completed
                    if spec['type'] == 'LFA_PLAYER':
                        # Check if onboarding completed for this license
                        lfa_license = next((lic for lic in user.get('licenses', [])
                                          if lic.get('specialization_type') == 'LFA_FOOTBALL_PLAYER'), None)

                        if lfa_license and not lfa_license.get('onboarding_completed', False):
                            # Onboarding not complete - redirect to onboarding
                            st.info("Redirecting to onboarding...")
                            st.switch_page("pages/LFA_Player_Onboarding.py")
                        else:
                            # Onboarding complete - go to dashboard
                            st.switch_page("pages/LFA_Player_Dashboard.py")
                    else:
                        # Other specializations coming soon
                        st.info(f"{spec['name']} dashboard coming soon! Each specialization will have its own dedicated dashboard.")

            elif not spec['is_available']:
                # COMING SOON (Development status)
                st.markdown('<div class="coming-soon-badge">🚧 COMING SOON</div>', unsafe_allow_html=True)
                st.caption("This specialization is under development")

            elif not spec['meets_age_req']:
                # AGE REQUIREMENT NOT MET (Business rule)
                st.markdown('<div class="coming-soon-badge">⏳ AGE REQUIREMENT</div>', unsafe_allow_html=True)
                st.caption(f"Available when you turn {spec['min_age']} years old")
                st.caption(f"Your current age: {user_age or 'Not set'}")

            elif credit_balance < 100:
                # INSUFFICIENT CREDITS - SHOW PURCHASE BUTTON (delegates to component)
                render_credit_purchase_button(credit_balance, spec['type'], token)

            else:
                # AVAILABLE TO UNLOCK (all requirements met!)
                if st.button(f"🔓 Unlock Now (100 credits)", key=f"unlock_{spec['type']}", use_container_width=True, type="primary"):
                    # Show confirmation modal via session state
                    st.session_state[f'confirming_unlock_{spec["type"]}'] = True
                    st.rerun()

            # "Learn More" button (ALWAYS visible - business requirement)
            st.divider()
            if st.button(f"ℹ️ Learn More about {spec['name']}", key=f"learn_{spec['type']}", use_container_width=True):
                # Navigate to specialization info page with spec type as query parameter
                # Set query params BEFORE switching page
                st.session_state['selected_spec'] = spec['type']
                st.switch_page("pages/Specialization_Info.py")

            st.markdown('</div>', unsafe_allow_html=True)

            # Unlock confirmation modal
            if st.session_state.get(f'confirming_unlock_{spec["type"]}', False):
                st.divider()
                st.warning(f"⚠️ Unlock **{spec['name']}** for **100 credits**?")
                st.caption(f"Your new balance will be: {credit_balance - 100} credits")

                confirm_col1, confirm_col2 = st.columns(2)

                with confirm_col1:
                    if st.button("✅ Confirm Unlock", key=f"confirm_{spec['type']}", use_container_width=True):
                        # Call unlock API
                        success, error, response = unlock_specialization(token, spec['type'])

                        if success:
                            st.success(f"✅ {spec['name']} unlocked successfully!")
                            st.balloons()

                            # Refresh user data to update credit balance and licenses
                            user_success, user_error, user_data = get_current_user(token)
                            if user_success:
                                st.session_state[SESSION_USER_KEY] = user_data

                            # Clear confirmation state
                            st.session_state[f'confirming_unlock_{spec["type"]}'] = False

                            # ✅ REDIRECT TO ONBOARDING (not dashboard!)
                            if spec['type'] == 'LFA_PLAYER':
                                st.info("Redirecting to onboarding...")
                                st.switch_page("pages/LFA_Player_Onboarding.py")
                            else:
                                # Other specs: stay on hub for now
                                st.rerun()
                        else:
                            st.error(f"❌ Failed to unlock: {error}")
                            st.session_state[f'confirming_unlock_{spec["type"]}'] = False

                with confirm_col2:
                    if st.button("❌ Cancel", key=f"cancel_{spec['type']}", use_container_width=True):
                        st.session_state[f'confirming_unlock_{spec["type"]}'] = False
                        st.rerun()

# Credit purchase form (if triggered)
if st.session_state.get('show_credit_purchase', False):
    render_credit_purchase_form(token)

# Coupon redemption form (always show below specializations)
st.divider()
st.markdown("### 🎁 Have a Coupon Code?")
st.caption("Redeem your BONUS_CREDITS coupon to instantly add credits")
render_coupon_redemption(token)

st.divider()

# Footer links - consistent navigation
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    if st.button("Profile", use_container_width=True):
        st.switch_page("pages/My_Profile.py")

with footer_col2:
    if st.button("Credits", use_container_width=True):
        st.switch_page("pages/My_Credits.py")

with footer_col3:
    if st.button("Help", use_container_width=True):
        # Show help modal or link to documentation
        st.info(
            "**Need Help?**\n\n"
            "- View your profile: Click 'Profile'\n"
            "- Purchase credits: Click 'Credits'\n"
            "- Contact support: admin@lfa.com"
        )
