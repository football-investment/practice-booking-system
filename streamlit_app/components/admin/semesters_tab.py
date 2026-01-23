"""
Admin Dashboard - Semesters Tab Component
Semesters management with generation and assignment
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Semester components (modular)
from components.semesters import (
    render_semester_generation,
    render_semester_management,
    render_semester_overview,
    render_smart_matrix
)


def render_semesters_tab(token, user):
    """
    Render the Semesters tab with semester management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    st.markdown("### 📅 Semester Generation & Management")
    st.caption("Manage semesters, generate periods, and assign instructors")

    # Tip box - Location management is elsewhere
    st.info("💡 **Location kezelés**: Location-ök létrehozásához és szerkesztéséhez használd az Admin Dashboard **📍 Locations** tab-ját!")

    st.divider()

    # 4 tabs (Locations nélkül!)
    semester_tab1, semester_tab2, semester_tab3, semester_tab4 = st.tabs([
        "📊 Overview",
        "📊 Smart Matrix",
        "🚀 Generate",
        "🎯 Manage"
    ])

    # ========================================
    # OVERVIEW SUB-TAB
    # ========================================
    with semester_tab1:
        render_semester_overview(token)

    # ========================================
    # SMART MATRIX SUB-TAB (NEW - Combined Generate + Manage with Gap Detection)
    # ========================================
    with semester_tab2:
        render_smart_matrix(token)

    # ========================================
    # GENERATE SEMESTERS SUB-TAB
    # ========================================
    with semester_tab3:
        render_semester_generation(token)

    # ========================================
    # MANAGE SEMESTERS SUB-TAB
    # ========================================
    with semester_tab4:
        render_semester_management(token)
