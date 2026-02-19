"""
Specialization Information Page
Displays detailed information about a specific specialization

URL Parameters:
- spec: Specialization type (LFA_PLAYER, INTERNSHIP, GANCUJU_PLAYER, LFA_COACH)
"""

import streamlit as st
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - Specialization Info",
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
user = st.session_state.get(SESSION_USER_KEY, {})

# Get specialization from session state (set by Specialization Hub)
spec_type = st.session_state.get('selected_spec', 'LFA_PLAYER')

# Specialization data
SPECIALIZATIONS = {
    "LFA_PLAYER": {
        "icon": "⚽",
        "name": "LFA Football Player",
        "age_requirement": "Ages 5-99",
        "description": "Modern football training with age-specific programs",
        "levels": ["PRE (5-13)", "YOUTH (14-18)", "AMATEUR (14+)", "PRO (14+, master-led)"],
        "color": "#f1c40f"
    },
    "INTERNSHIP": {
        "icon": "💼",
        "name": "Internship",
        "age_requirement": "Ages 18+",
        "description": "Build your startup career from zero to co-founder",
        "levels": ["Semester 1-5 journey"],
        "color": "#e74c3c"
    },
    "GANCUJU_PLAYER": {
        "icon": "🥋",
        "name": "GānCuju Player",
        "age_requirement": "Ages 5+",
        "description": "Master the 4000-year-old Chinese football art",
        "levels": ["Belt system progression", "Authentic Ganball™ equipment"],
        "color": "#8e44ad"
    },
    "LFA_COACH": {
        "icon": "👨‍🏫",
        "name": "LFA Coach",
        "age_requirement": "Ages 14+",
        "description": "Become a certified football coach with LFA methodology",
        "levels": ["Teaching certification", "Methodology training"],
        "color": "#27ae60"
    }
}

spec_data = SPECIALIZATIONS.get(spec_type, SPECIALIZATIONS["LFA_PLAYER"])

# Custom CSS for info page
st.markdown(f"""
<style>
    .spec-info-header {{
        background: linear-gradient(135deg, {spec_data['color']}22 0%, {spec_data['color']}11 100%);
        border-left: 4px solid {spec_data['color']};
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
    }}

    .spec-icon-large {{
        font-size: 5rem;
        text-align: center;
        margin-bottom: 1rem;
    }}

    .coming-soon-box {{
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    }}

    .info-section {{
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'User')}!")
    st.caption(f"Role: **{user.get('role', 'Student').title()}**")

    st.markdown("---")

    if st.button("⬅️ Back to Specialization Hub", use_container_width=True):
        st.switch_page("pages/Specialization_Hub.py")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("🏠_Home.py")

# Header
st.markdown(f'<div class="spec-icon-large">{spec_data["icon"]}</div>', unsafe_allow_html=True)
st.title(f"{spec_data['name']}")
st.caption(f"Age Requirement: {spec_data['age_requirement']}")

st.divider()

# Coming Soon Notice
st.markdown("""
<div class="coming-soon-box">
    <h2>🚧 Coming Soon...</h2>
    <p>Detailed information about this specialization is currently being prepared.</p>
    <p>This page will soon include:</p>
</div>
""", unsafe_allow_html=True)

# What's Coming
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="info-section">', unsafe_allow_html=True)
    st.subheader("📚 What You'll Learn")
    st.markdown(f"""
    - {spec_data['description']}
    - Comprehensive curriculum details
    - Skill progression paths
    - Learning objectives
    """)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="info-section">', unsafe_allow_html=True)
    st.subheader("🎓 Program Structure")
    st.markdown("**Levels:**")
    for level in spec_data['levels']:
        st.markdown(f"- {level}")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="info-section">', unsafe_allow_html=True)
    st.subheader("👨‍🏫 Instructors")
    st.markdown("""
    - Meet our expert instructors
    - Teaching philosophy
    - Success stories
    - Student testimonials
    """)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="info-section">', unsafe_allow_html=True)
    st.subheader("💰 Investment")
    st.markdown("""
    - **Unlock Cost:** 100 credits
    - Monthly payment options (coming soon)
    - Scholarship opportunities
    - Return on investment
    """)
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Call to Action
st.info("💡 Ready to get started? Return to the Specialization Hub to unlock this program!")

if st.button("🚀 Go to Specialization Hub", type="primary", use_container_width=True):
    st.switch_page("pages/Specialization_Hub.py")

# Footer
st.markdown("---")
st.caption("Have questions? Contact us at admin@lfa.com")
