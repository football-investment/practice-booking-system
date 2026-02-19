"""Position Posting Modal - Master instructor posts new position"""

import streamlit as st
from datetime import datetime, timedelta
import sys
sys.path.append('..')
from api_helpers_instructors import create_position


@st.dialog("Post New Position")
def show_position_posting_modal(location_id: int, token: str) -> None:
    """
    Modal for master instructor to post a new position

    Workflow:
    1. Master fills out position details
    2. Position becomes visible on job board
    3. Instructors can apply
    """

    with st.form(key=f"post_position_form_{location_id}"):
        st.subheader("Post Instructor Position")

        # Specialization and age group
        col1, col2 = st.columns(2)
        with col1:
            specialization = st.selectbox(
                "Specialization",
                options=["LFA_PLAYER", "INTERNSHIP", "GANCUJU", "COACH"],
                help="Type of specialization"
            )
        with col2:
            age_group = st.selectbox(
                "Age Group",
                options=["PRE", "YOUTH", "AMATEUR", "PRO"],
                help="Target age group"
            )

        # Year and period
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input(
                "Year",
                min_value=2025,
                max_value=2030,
                value=2026,
                step=1
            )
        with col2:
            period_type = st.selectbox(
                "Period Type",
                options=["Monthly", "Quarterly", "Annual"],
                help="PRE/YOUTH use monthly, AMATEUR/PRO use quarterly/annual"
            )

        # Period range
        if period_type == "Monthly":
            col1, col2 = st.columns(2)
            with col1:
                start_month = st.selectbox("Start Month", options=[f"M{i:02d}" for i in range(1, 13)])
            with col2:
                end_month = st.selectbox("End Month", options=[f"M{i:02d}" for i in range(1, 13)])
            time_period_start = start_month
            time_period_end = end_month
        elif period_type == "Quarterly":
            col1, col2 = st.columns(2)
            with col1:
                start_quarter = st.selectbox("Start Quarter", options=["Q1", "Q2", "Q3", "Q4"])
            with col2:
                end_quarter = st.selectbox("End Quarter", options=["Q1", "Q2", "Q3", "Q4"])
            time_period_start = start_quarter
            time_period_end = end_quarter
        else:  # Annual
            time_period_start = "Y1"
            time_period_end = "Y1"
            st.info("Annual period: Y1 (full year)")

        # Job description
        description = st.text_area(
            "Job Description",
            height=150,
            placeholder="Describe the position, requirements, expectations...",
            help="Minimum 10 characters"
        )

        # Priority
        priority = st.slider(
            "Priority",
            min_value=1,
            max_value=10,
            value=5,
            help="1=Low, 5=Medium, 10=High"
        )

        # Application deadline
        application_deadline = st.date_input(
            "Application Deadline",
            value=datetime.now() + timedelta(days=14),
            min_value=datetime.now(),
            help="Last day for instructors to apply"
        )

        # Submit
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Post Position", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if cancel:
            st.rerun()

        if submit:
            # Validation
            if not description or len(description) < 10:
                st.error("Description must be at least 10 characters")
                return

            try:
                # Convert deadline to ISO format
                deadline_iso = datetime.combine(
                    application_deadline,
                    datetime.max.time()
                ).isoformat()

                create_position(
                    token=token,
                    location_id=location_id,
                    specialization_type=specialization,
                    age_group=age_group,
                    year=year,
                    time_period_start=time_period_start,
                    time_period_end=time_period_end,
                    description=description,
                    application_deadline=deadline_iso,
                    priority=priority
                )

                st.success("Position posted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error posting position: {e}")
