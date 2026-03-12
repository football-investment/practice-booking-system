"""
LFA Football Player Onboarding
5-step wizard: Profile, Position, Skills (4 categories), Goals
"""

import streamlit as st
import sys
import os
from datetime import date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY
from api_helpers_general import get_current_user, submit_lfa_player_onboarding
from app.skills_config import SKILL_CATEGORIES, get_all_skill_keys

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - LFA Player Onboarding",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CUSTOM_CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Authentication check
if SESSION_TOKEN_KEY not in st.session_state:
    st.error("Please log in first")
    st.switch_page("🏠_Home.py")
    st.stop()

token = st.session_state[SESSION_TOKEN_KEY]

# Get fresh user data
success, error, user = get_current_user(token)
if not success:
    st.error(f"Failed to load user data: {error}")
    st.session_state.clear()
    st.switch_page("🏠_Home.py")
    st.stop()

# Update session state
st.session_state[SESSION_USER_KEY] = user

# Only students can access this page
if user.get('role') != 'student':
    st.error("This page is for students only")
    st.stop()

# Check if user has LFA_FOOTBALL_PLAYER license
user_licenses = user.get('licenses', [])

# ✅ FIX: Select ACTIVE license only (not the first one!)
lfa_license = next(
    (lic for lic in user_licenses
     if lic.get('specialization_type') == 'LFA_FOOTBALL_PLAYER'
     and lic.get('is_active') == True),  # ✅ CRITICAL: Filter by is_active!
    None
)

# If no license, redirect to hub
if not lfa_license:
    st.error("LFA Player license not found. Please unlock the specialization first.")
    st.switch_page("pages/Specialization_Hub.py")
    st.stop()

# If onboarding already completed, redirect to dashboard
if lfa_license.get('onboarding_completed', False):
    st.info("You've already completed onboarding. Redirecting to your dashboard...")
    st.switch_page("pages/LFA_Player_Dashboard.py")
    st.stop()

# Initialize session state for wizard (5 steps: profile, position, 4 skill categories, goals)
TOTAL_STEPS = 6  # 1: Profile+Position, 2-5: Skills (4 categories), 6: Goals

if 'onboarding_step' not in st.session_state:
    st.session_state.onboarding_step = 1
if 'onboarding_position' not in st.session_state:
    st.session_state.onboarding_position = None
if 'onboarding_skills' not in st.session_state:
    # Initialize all 36 skills with default value 50
    st.session_state.onboarding_skills = {skill_key: 50 for skill_key in get_all_skill_keys()}
if 'onboarding_goals' not in st.session_state:
    st.session_state.onboarding_goals = ""

# ============================================================================
# SIDEBAR - Progress Indicator
# ============================================================================

with st.sidebar:
    st.markdown(f"### LFA Player Onboarding")
    st.caption(f"Welcome, {user.get('name', 'Player')}!")

    st.markdown("---")

    # Progress indicator
    current_step = st.session_state.onboarding_step
    st.markdown(f"**Progress: Step {current_step}/{TOTAL_STEPS}**")

    # Progress bar
    progress = current_step / TOTAL_STEPS
    st.progress(progress)

    st.markdown("")

    # Step indicators
    step_labels = [
        "Position",
        "🟦 Outfield Skills",
        "🟨 Set Pieces",
        "🟩 Mental Skills",
        "🟥 Physical Skills",
        "Goals"
    ]

    for idx, label in enumerate(step_labels, start=1):
        if current_step > idx:
            st.markdown(f"✅ Step {idx}: {label}")
        elif current_step == idx:
            st.markdown(f"🔵 Step {idx}: {label}")
        else:
            st.markdown(f"⚪ Step {idx}: {label}")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("🏠_Home.py")

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .skill-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .skill-header {
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 0.25rem;
        font-size: 1.05rem;
    }

    .skill-description {
        color: #666;
        font-size: 0.85rem;
        margin-bottom: 0.75rem;
        line-height: 1.4;
    }

    .category-header {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .position-card {
        background: white;
        border: 3px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }

    .position-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }

    .position-card.selected {
        border-color: #667eea;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("⚽ LFA Football Player Onboarding")
st.markdown(f"Complete these {TOTAL_STEPS} steps to start your football training journey!")

st.divider()

# ============================================================================
# STEP 1: Profile & Position Selection
# ============================================================================

if st.session_state.onboarding_step == 1:
    st.markdown("### Step 1: Player Profile & Position")
    st.markdown("Let's confirm your profile and select your position:")

    st.markdown("")

    # READ-ONLY: Show birth date from user profile
    user_dob = user.get('date_of_birth')

    if user_dob:
        try:
            # Parse birth date
            from datetime import datetime
            if isinstance(user_dob, str):
                dob = datetime.fromisoformat(user_dob.replace('Z', '+00:00')).date()
            else:
                dob = user_dob

            # Calculate age
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            # Display (read-only)
            st.markdown("**📅 Your Profile**")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Birth Date:** {dob.strftime('%Y-%m-%d')}")
            with col2:
                st.info(f"**Age:** {age} years old")

            # Calculate age AT SEASON START (July 1) - season lock logic
            if today.month >= 7:  # July-December → current season
                season_start = date(today.year, 7, 1)
            else:  # January-June → previous season
                season_start = date(today.year - 1, 7, 1)

            age_at_season_start = season_start.year - dob.year
            if (season_start.month, season_start.day) < (dob.month, dob.day):
                age_at_season_start -= 1

            # Show age category based on SEASON START age (locked for entire season)
            if 5 <= age_at_season_start <= 13:
                st.success("🎯 **Your Category:** PRE (Foundation Years) - Ages 5-13 - Monthly training blocks")
            elif 14 <= age_at_season_start <= 18:
                st.success("🎯 **Your Category:** YOUTH (Technical Development) - Ages 14-18 - Quarterly programs")
            elif age_at_season_start > 18:
                st.info("🎯 **Your Category:** Will be assigned by instructor (AMATEUR or PRO) - Ages 18+")
            else:
                st.warning(f"⚠️ Age at season start ({age_at_season_start}) - Below minimum age requirement (5 years)")
        except Exception as e:
            st.error(f"Error parsing birth date: {e}")
            st.warning("⚠️ Please update your birth date in My Profile before continuing")
            st.stop()
    else:
        # Birth date missing - redirect to profile
        st.error("❌ **Birth date missing from your profile!**")
        st.warning("Please set your birth date in My Profile before starting LFA Player onboarding.")
        if st.button("Go to My Profile", use_container_width=True, type="primary"):
            st.switch_page("pages/My_Profile.py")
        st.stop()

    st.divider()

    # Position selection
    st.markdown("**⚽ Playing Position**")
    st.markdown("Select your primary playing position on the field:")

    st.markdown("")

    positions = [
        {"value": "STRIKER", "icon": "⚡", "name": "Striker", "desc": "Attack and score goals"},
        {"value": "MIDFIELDER", "icon": "🎯", "name": "Midfielder", "desc": "Control the game's tempo"},
        {"value": "DEFENDER", "icon": "🛡️", "name": "Defender", "desc": "Protect the goal"},
        {"value": "GOALKEEPER", "icon": "🧤", "name": "Goalkeeper", "desc": "Last line of defense"}
    ]

    # Create 2x2 grid
    col1, col2 = st.columns(2)

    for idx, pos in enumerate(positions):
        with (col1 if idx < 2 else col2):
            # Create a container for each position card
            selected = st.session_state.onboarding_position == pos['value']

            if st.button(
                f"{pos['icon']}\n\n**{pos['name']}**\n\n{pos['desc']}",
                key=f"pos_{pos['value']}",
                use_container_width=True,
                type="primary" if selected else "secondary"
            ):
                st.session_state.onboarding_position = pos['value']
                st.rerun()

    st.markdown("")

    # Show selected position
    if st.session_state.onboarding_position:
        selected_pos = next(p for p in positions if p['value'] == st.session_state.onboarding_position)
        st.success(f"Selected: {selected_pos['icon']} **{selected_pos['name']}**")

    st.divider()

    # Validation for Next button
    can_continue = st.session_state.onboarding_position is not None

    if not can_continue:
        st.warning("⚠️ Please select your playing position to continue")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col3:
        if st.button("Next →", use_container_width=True, type="primary", disabled=not can_continue):
            st.session_state.onboarding_step = 2
            st.rerun()

# ============================================================================
# STEPS 2-5: Skills Self-Assessment (4 Categories)
# ============================================================================

elif 2 <= st.session_state.onboarding_step <= 5:
    # Map step to category index
    category_idx = st.session_state.onboarding_step - 2  # Step 2 → category 0, etc.
    category = SKILL_CATEGORIES[category_idx]

    st.markdown(f"### Step {st.session_state.onboarding_step}: {category['emoji']} {category['name_hu']}")
    st.markdown(f"Rate your current ability in each skill (0 = Beginner, 100 = Expert):")

    st.markdown("")

    # Display all skills in this category
    for skill in category['skills']:
        st.markdown(f"<div class='skill-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='skill-header'>{skill['name_hu']} ({skill['name_en']})</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='skill-description'>{skill['description_hu']}</div>", unsafe_allow_html=True)

        # Slider for skill rating (0-100)
        st.session_state.onboarding_skills[skill['key']] = st.slider(
            f"Rate your {skill['key']} (0-100)",
            min_value=0,
            max_value=100,
            value=st.session_state.onboarding_skills[skill['key']],
            step=5,
            key=f"slider_{skill['key']}",
            label_visibility="collapsed"
        )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")

    # Show category average
    category_skills = [skill['key'] for skill in category['skills']]
    category_avg = sum(st.session_state.onboarding_skills[sk] for sk in category_skills) / len(category_skills)
    st.info(f"📊 {category['emoji']} Category Average: **{category_avg:.1f}/100**")

    st.divider()

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step -= 1
            st.rerun()

    with col3:
        next_label = "Next →" if st.session_state.onboarding_step < 5 else "Next →"
        if st.button(next_label, use_container_width=True, type="primary"):
            st.session_state.onboarding_step += 1
            st.rerun()

# ============================================================================
# STEP 6: Goals & Motivation
# ============================================================================

elif st.session_state.onboarding_step == 6:
    st.markdown("### Step 6: Goals & Motivation")
    st.markdown("Tell us about your football aspirations:")

    st.markdown("")

    # Show overall skill summary
    st.markdown("**📊 Your Skill Profile Summary**")

    for category in SKILL_CATEGORIES:
        category_skills = [skill['key'] for skill in category['skills']]
        category_avg = sum(st.session_state.onboarding_skills[sk] for sk in category_skills) / len(category_skills)
        st.markdown(f"{category['emoji']} **{category['name_hu']}**: {category_avg:.1f}/100")

    overall_avg = sum(st.session_state.onboarding_skills.values()) / len(st.session_state.onboarding_skills)
    st.info(f"🎯 **Overall Average**: {overall_avg:.1f}/100")

    st.divider()

    # Goals dropdown
    st.markdown("**What are your football goals?**")
    goals_options = [
        ("", "Select your primary goal..."),
        ("improve_skills", "Improve my technical skills"),
        ("play_higher_level", "Play at a higher competitive level"),
        ("become_professional", "Become a professional player"),
        ("team_football", "Join a football team"),
        ("fitness_health", "Stay fit and healthy through football"),
        ("enjoy_game", "Simply enjoy playing the game")
    ]

    st.session_state.onboarding_goals = st.selectbox(
        "Primary Goal",
        options=[opt[0] for opt in goals_options],
        format_func=lambda x: next((opt[1] for opt in goals_options if opt[0] == x), ""),
        index=[opt[0] for opt in goals_options].index(st.session_state.onboarding_goals) if st.session_state.onboarding_goals else 0,
        key="goals_select",
        label_visibility="collapsed"
    )

    st.divider()

    # Validation
    is_valid = st.session_state.onboarding_goals != ""

    if not is_valid:
        st.warning("⚠️ Please select your primary goal")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step = 5
            st.rerun()

    with col3:
        if st.button("🚀 Complete Onboarding", use_container_width=True, type="primary", disabled=not is_valid):
            # Submit to backend
            with st.spinner("Submitting your onboarding data..."):
                success, error, response = submit_lfa_player_onboarding(
                    token=token,
                    date_of_birth=None,  # Already in user profile
                    position=st.session_state.onboarding_position,
                    skills=st.session_state.onboarding_skills,  # All 36 skills, 0-100 scale
                    goals=st.session_state.onboarding_goals,
                    motivation=""  # Empty - motivation field removed
                )

                if success:
                    st.success("✅ Onboarding completed successfully!")
                    st.balloons()

                    # Clear onboarding session state
                    for key in list(st.session_state.keys()):
                        if key.startswith('onboarding_'):
                            del st.session_state[key]

                    # Refresh user data
                    user_success, user_error, user_data = get_current_user(token)
                    if user_success:
                        st.session_state[SESSION_USER_KEY] = user_data

                    # Redirect to dashboard
                    st.info("Redirecting to your dashboard...")
                    st.switch_page("pages/LFA_Player_Dashboard.py")
                else:
                    st.error(f"❌ Failed to submit onboarding: {error}")
                    st.stop()
