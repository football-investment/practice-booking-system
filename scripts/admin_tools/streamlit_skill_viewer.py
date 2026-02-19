#!/usr/bin/env python3
"""
Skill Profile Viewer - Frontend Verification UI
================================================

Simple Streamlit app to verify skill persistence via frontend.
"""

import streamlit as st
import requests
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services import skill_progression_service

API_BASE_URL = "http://localhost:8000/api/v1"
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Create DB session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

st.set_page_config(page_title="Skill Profile Viewer", page_icon="⚽", layout="wide")

st.title("⚽ Skill Profile Viewer - Persistence Verification")

st.markdown("""
**Purpose:** Verify skill persistence after tournament participation.

**Test Users:**
- User 4: k1sqx1@f1rstteam.hu (40 tournaments, winner)
- User 5: p3t1k3@f1rstteam.hu
- User 6: v4lv3rd3jr@f1rstteam.hu
- User 7: t1b1k3@f1rstteam.hu
""")

# User selection
user_id = st.selectbox(
    "Select User",
    options=[4, 5, 6, 7],
    format_func=lambda x: f"User {x} ({'k1sqx1' if x == 4 else 'p3t1k3' if x == 5 else 'v4lv3rd3jr' if x == 6 else 't1b1k3'})"
)

if st.button("Load Skill Profile"):
    with st.spinner("Loading skill profile..."):
        db = SessionLocal()

        try:
            # Get skill profile
            profile = skill_progression_service.get_skill_profile(db, user_id)

            st.success(f"✅ Skill profile loaded for User {user_id}")

            # Show user info
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("User ID", user_id)
            with col2:
                st.metric("Email", user.email if user else "N/A")
            with col3:
                st.metric("Name", user.name if user else "N/A")

            st.markdown("---")

            # Show skills
            st.subheader("📊 Skill Profile")

            skills_to_show = ["passing", "dribbling", "shot_power", "ball_control", "finishing", "sprint_speed"]

            for skill_name in skills_to_show:
                if skill_name in profile.get("skills", {}):
                    skill = profile["skills"][skill_name]

                    st.markdown(f"### {skill_name.replace('_', ' ').title()}")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Current Level", f"{skill.get('current_level', 0):.1f}")
                    with col2:
                        st.metric("Baseline", f"{skill.get('baseline', 0):.1f}")
                    with col3:
                        delta = skill.get('total_delta', 0)
                        st.metric("Total Delta", f"{delta:+.1f}", delta=delta)
                    with col4:
                        st.metric("Tournaments", skill.get('tournament_count', 0))

                    # Progress bar
                    progress = skill.get('current_level', 0) / 100.0
                    st.progress(progress)

                    st.markdown("---")

            # Show participation history
            st.subheader("🏆 Tournament Participation History")

            from app.models.tournament_achievement import TournamentParticipation

            participations = db.query(TournamentParticipation).filter(
                TournamentParticipation.user_id == user_id
            ).order_by(TournamentParticipation.achieved_at.desc()).limit(10).all()

            st.write(f"**Total Participations:** {len(participations)}")

            if participations:
                for p in participations:
                    with st.expander(f"Tournament {p.semester_id} - Placement #{p.placement} ({p.achieved_at.strftime('%Y-%m-%d %H:%M')})"):
                        st.json(p.skill_points_awarded)
                        st.write(f"**XP Awarded:** {p.xp_awarded}")
                        st.write(f"**Credits Awarded:** {p.credits_awarded}")

        except Exception as e:
            st.error(f"❌ Error loading skill profile: {e}")
            import traceback
            st.code(traceback.format_exc())

        finally:
            db.close()

st.markdown("---")
st.markdown("**Persistence Check:** If skills are the same tomorrow, persistence is validated ✅")
