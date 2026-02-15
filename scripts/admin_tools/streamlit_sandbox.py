"""
Sandbox Tournament Test - Streamlit UI (Admin-Grade UX)

Restructured to follow admin mental model:
- No auth screen (assumes admin is already authenticated)
- Participant mode radio (Random Pool vs Specific Users)
- Conditional player count OR user selection (never both)
- Instructor assignment only for Specific Users mode

Run: streamlit run streamlit_sandbox.py --server.port 8502
"""
import streamlit as st
import requests
import time
from typing import Dict, Any, List, Optional

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
SANDBOX_ENDPOINT = f"{API_BASE_URL}/sandbox/run-test"
AUTH_ENDPOINT = f"{API_BASE_URL}/auth/login"
USERS_ENDPOINT = f"{API_BASE_URL}/sandbox/users"
INSTRUCTORS_ENDPOINT = f"{API_BASE_URL}/sandbox/instructors"
CAMPUSES_ENDPOINT = f"{API_BASE_URL}/admin/campuses"

# Available options
TOURNAMENT_TYPES = ["league", "knockout", "hybrid"]
AVAILABLE_SKILLS = [
    "passing", "dribbling", "shooting", "defending", "physical", "pace"
]

# Page configuration
st.set_page_config(
    page_title="Sandbox Tournament Test",
    page_icon="🧪",
    layout="wide"
)

def get_auth_token(email: str, password: str) -> Optional[str]:
    """Get authentication token"""
    try:
        response = requests.post(
            AUTH_ENDPOINT,
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

def fetch_users(token: str, search: str = None, limit: int = 50) -> List[Dict]:
    """Fetch available users for sandbox testing"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if search:
        params["search"] = search

    try:
        response = requests.get(USERS_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch users: {e}")
        return []

def fetch_instructors(token: str, search: str = None, limit: int = 50) -> List[Dict]:
    """Fetch available instructors for sandbox testing"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if search:
        params["search"] = search

    try:
        response = requests.get(INSTRUCTORS_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch instructors: {e}")
        return []

def fetch_campuses(token: str) -> List[Dict]:
    """Fetch available campuses"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(CAMPUSES_ENDPOINT, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch campuses: {e}")
        return []

def run_sandbox_test(
    token: str,
    tournament_type: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int,
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    user_ids: Optional[List[int]] = None,
    instructor_ids: Optional[List[int]] = None
) -> Optional[Dict[str, Any]]:
    """Call sandbox test endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "tournament_type": tournament_type,
        "skills_to_test": skills_to_test,
        "player_count": player_count,
        "campus_id": campus_id,
        "test_config": {
            "performance_variation": performance_variation,
            "ranking_distribution": ranking_distribution
        }
    }

    if user_ids:
        payload["user_ids"] = user_ids
    if instructor_ids:
        payload["instructor_ids"] = instructor_ids

    try:
        response = requests.post(SANDBOX_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"API Error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

def render_configuration_screen():
    """Screen 1: Configuration (Admin-Grade UX)"""
    st.title("🧪 Sandbox Tournament Test")

    # Simple token input for admin (dev mode)
    # In production, this would integrate with admin dashboard session
    if "token" not in st.session_state:
        st.info("💡 **Quick Setup**: Enter your admin token or use default credentials")

        col1, col2 = st.columns([2, 1])
        with col1:
            email = st.text_input("Admin Email", value="admin@lfa.com")
            password = st.text_input("Password", value="admin123", type="password")

        with col2:
            st.write("")  # spacing
            st.write("")  # spacing
            if st.button("🔑 Authenticate", use_container_width=True):
                token = get_auth_token(email, password)
                if token:
                    st.session_state.token = token
                    st.success("✅ Authenticated!")
                    st.rerun()

        st.stop()

    st.markdown("---")

    # 1️⃣ Tournament Configuration
    st.markdown("### 1️⃣ Tournament Configuration")

    col1, col2 = st.columns(2)

    with col1:
        tournament_type = st.selectbox(
            "Tournament Type",
            TOURNAMENT_TYPES,
            format_func=lambda x: x.upper(),
            help="Select the tournament format to test"
        )

        # Fetch campuses
        campuses = fetch_campuses(st.session_state.token)
        campus_options = {f"{c['name']} ({c.get('location', {}).get('city', 'N/A')})": c['id'] for c in campuses}

        if campus_options:
            campus_display = st.selectbox(
                "Location (Campus)",
                options=list(campus_options.keys()),
                help="Select the campus where tournament will take place"
            )
            campus_id = campus_options[campus_display]
        else:
            st.error("❌ No campuses available")
            st.stop()

    with col2:
        skills_to_test = st.multiselect(
            "Skills to Test (1-4)",
            AVAILABLE_SKILLS,
            default=["passing", "dribbling"],
            max_selections=4,
            help="Select 1-4 skills to validate in this test"
        )

    st.markdown("---")

    # 2️⃣ Participant Selection Mode
    st.markdown("### 2️⃣ Participant Selection Mode")

    participant_mode = st.radio(
        "Choose how to select participants:",
        options=["random_pool", "specific_users"],
        format_func=lambda x: "🎲 Random Pool (Quick Test)" if x == "random_pool" else "👥 Specific Users (Real Impact Analysis)",
        horizontal=False,
        help="Random Pool: Quickly test with random users. Specific Users: Analyze impact on selected real users."
    )

    # Initialize variables
    player_count = 8  # default
    selected_user_ids = []
    selected_instructor_ids = []

    # Conditional UI based on participant mode
    if participant_mode == "random_pool":
        st.markdown("#### Player Count")
        player_count = st.slider(
            "Number of players",
            min_value=4,
            max_value=16,
            value=8,
            step=1,
            help="Select how many random users to include in the test (4-16)"
        )
        st.info(f"✅ Will use {player_count} random users from test pool")

    else:  # specific_users
        st.markdown("#### Select Users")

        # Search functionality
        col_search, col_filter = st.columns([3, 1])
        with col_search:
            search_users = st.text_input(
                "🔍 Search users",
                placeholder="Search by name or email...",
                key="search_users"
            )
        with col_filter:
            st.write("")  # spacing
            if st.button("🔄 Refresh", key="refresh_users"):
                st.rerun()

        # Fetch and display users
        users = fetch_users(st.session_state.token, search=search_users, limit=50)

        if users:
            st.markdown(f"**Available Users** ({len(users)} found)")

            # User selection with skill preview
            for user in users:
                skill_preview = user.get("skill_preview", {})

                # Format skill preview
                if skill_preview:
                    skill_text = " | ".join([
                        f"{k.capitalize()}: {v:.0f}"
                        for k, v in list(skill_preview.items())[:4]
                    ])
                else:
                    skill_text = "No skill data"

                # Checkbox with user info
                col_check, col_info = st.columns([3, 1])
                with col_check:
                    is_selected = st.checkbox(
                        f"**{user['name']}** ({user['email']})",
                        key=f"user_{user['id']}"
                    )
                    if is_selected:
                        selected_user_ids.append(user['id'])

                with col_info:
                    st.caption(skill_text)
                    if user.get("license_type"):
                        st.caption(f"📋 {user['license_type']}")

            # Selection summary
            if selected_user_ids:
                st.success(f"✅ Selected: {len(selected_user_ids)} users")
                player_count = len(selected_user_ids)  # Override player count with actual selection
            else:
                st.warning("⚠️ No users selected yet (minimum 4 required)")

        else:
            st.info("No users found. Try adjusting your search or check API connection.")

        # Instructor Assignment (only for Specific Users mode)
        st.markdown("---")
        st.markdown("#### Instructor Assignment (Optional)")

        assign_instructors = st.checkbox(
            "Assign specific instructors to this test",
            value=False,
            help="Optional: Select instructors to assign to the tournament"
        )

        if assign_instructors:
            col_search_inst, col_filter_inst = st.columns([3, 1])
            with col_search_inst:
                search_instructors = st.text_input(
                    "🔍 Search instructors",
                    placeholder="Search by name or email...",
                    key="search_instructors"
                )
            with col_filter_inst:
                st.write("")  # spacing
                if st.button("🔄 Refresh", key="refresh_instructors"):
                    st.rerun()

            instructors = fetch_instructors(st.session_state.token, search=search_instructors, limit=20)

            if instructors:
                for instructor in instructors:
                    col_check_inst, col_info_inst = st.columns([3, 1])
                    with col_check_inst:
                        is_selected_inst = st.checkbox(
                            f"**{instructor['name']}** ({instructor['email']})",
                            key=f"instructor_{instructor['id']}"
                        )
                        if is_selected_inst:
                            selected_instructor_ids.append(instructor['id'])

                    with col_info_inst:
                        if instructor.get("specialization"):
                            st.caption(f"🎯 {instructor['specialization']}")

                if selected_instructor_ids:
                    st.info(f"ℹ️ Selected: {len(selected_instructor_ids)} instructors (parameter will be passed, logic not yet implemented)")

    st.markdown("---")

    # Validation
    validation_errors = []

    if not skills_to_test:
        validation_errors.append("❌ Please select at least 1 skill")

    if len(skills_to_test) > 4:
        validation_errors.append("❌ Maximum 4 skills allowed")

    if participant_mode == "specific_users" and len(selected_user_ids) < 4:
        validation_errors.append("❌ Please select at least 4 users for testing")

    if participant_mode == "specific_users" and len(selected_user_ids) > 16:
        validation_errors.append("❌ Maximum 16 users allowed")

    # Display validation errors
    if validation_errors:
        for error in validation_errors:
            st.error(error)

    # Run button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run_button_disabled = len(validation_errors) > 0

        if st.button(
            "🚀 Run Sandbox Test",
            type="primary",
            use_container_width=True,
            disabled=run_button_disabled
        ):
            st.session_state.test_config = {
                "tournament_type": tournament_type,
                "skills_to_test": skills_to_test,
                "player_count": player_count,
                "campus_id": campus_id,
                "user_ids": selected_user_ids if participant_mode == "specific_users" else None,
                "instructor_ids": selected_instructor_ids if participant_mode == "specific_users" and selected_instructor_ids else None
            }
            st.session_state.screen = "progress"
            st.rerun()

def render_progress_screen():
    """Screen 2: Progress"""
    st.title("🧪 Sandbox Tournament Test")
    st.markdown("### ⏳ Test in Progress...")

    config = st.session_state.test_config
    token = st.session_state.token

    # Display configuration
    with st.expander("📋 Test Configuration", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Tournament Type:** {config['tournament_type'].upper()}")
            st.write(f"**Player Count:** {config['player_count']}")
            if config.get('user_ids'):
                st.write(f"**Mode:** Specific Users ({len(config['user_ids'])} selected)")
            else:
                st.write(f"**Mode:** Random Pool")
        with col2:
            st.write(f"**Skills:** {', '.join(config['skills_to_test'])}")
            if config.get('instructor_ids'):
                st.write(f"**Instructors:** {len(config['instructor_ids'])} assigned")

    # Progress container
    progress_container = st.container()

    with progress_container:
        st.markdown("#### Execution Steps")
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Simulated steps (actual API call is synchronous)
        steps = [
            "🔧 Creating tournament...",
            "👥 Enrolling participants...",
            "📸 Snapshotting skills...",
            "🏆 Generating rankings...",
            "✅ Transitioning to COMPLETED...",
            "🎁 Distributing rewards...",
            "📊 Calculating verdict..."
        ]

        for i, step in enumerate(steps):
            status_text.markdown(f"**{step}**")
            progress_bar.progress((i + 1) / len(steps))
            time.sleep(0.3)  # Visual feedback

        # Call API
        status_text.markdown("**🚀 Executing test...**")
        result = run_sandbox_test(
            token,
            config["tournament_type"],
            config["skills_to_test"],
            config["player_count"],
            config["campus_id"],
            user_ids=config.get("user_ids"),
            instructor_ids=config.get("instructor_ids")
        )

        if result:
            st.session_state.test_result = result
            st.session_state.screen = "results"
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Test execution failed")
            if st.button("🔄 Back to Configuration"):
                st.session_state.screen = "configuration"
                st.rerun()

def render_results_screen():
    """Screen 3: Results"""
    result = st.session_state.test_result

    st.title("🧪 Sandbox Tournament Test")

    # Verdict header
    verdict = result["verdict"]
    if verdict == "WORKING":
        st.success(f"## ✅ VERDICT: {verdict}")
    else:
        st.error(f"## ❌ VERDICT: {verdict}")

    # Test metadata
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tournament ID", result["tournament"]["id"])
    with col2:
        st.metric("Player Count", result["tournament"]["player_count"])
    with col3:
        st.metric("Duration", f"{result['execution_summary']['duration_seconds']:.2f}s")
    with col4:
        st.metric("Status", result["tournament"]["status"])

    st.markdown("---")

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Skill Progression",
        "🏆 Top Performers",
        "📉 Bottom Performers",
        "💡 Insights"
    ])

    with tab1:
        render_skill_progression(result)

    with tab2:
        render_top_performers(result)

    with tab3:
        render_bottom_performers(result)

    with tab4:
        render_insights(result)

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔄 Run New Test", use_container_width=True):
            # Clear results but keep token
            if "test_result" in st.session_state:
                del st.session_state.test_result
            if "test_config" in st.session_state:
                del st.session_state.test_config
            st.session_state.screen = "configuration"
            st.rerun()

    with col2:
        st.download_button(
            label="📄 Download JSON",
            data=str(result),
            file_name=f"sandbox_test_{result['test_run_id']}.json",
            mime="application/json",
            use_container_width=True
        )

    with col3:
        if result.get("export_data", {}).get("pdf_ready"):
            st.info("PDF export available at API endpoint")

def render_skill_progression(result: Dict):
    """Render skill progression data"""
    skill_progression = result.get("skill_progression", {})

    if not skill_progression:
        st.warning("No skill progression data available")
        return

    for skill_name, stats in skill_progression.items():
        st.markdown(f"### {skill_name.replace('_', ' ').title()}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Before Average",
                f"{stats['before']['average']:.1f}",
                delta=None
            )
            st.caption(f"Min: {stats['before']['min']:.1f} | Max: {stats['before']['max']:.1f}")

        with col2:
            st.metric(
                "After Average",
                f"{stats['after']['average']:.1f}",
                delta=None
            )
            st.caption(f"Min: {stats['after']['min']:.1f} | Max: {stats['after']['max']:.1f}")

        with col3:
            change_value = stats["after"]["average"] - stats["before"]["average"]
            st.metric(
                "Change",
                f"{change_value:+.1f}",
                delta=f"{stats['change']}"
            )

        st.markdown("---")

def render_top_performers(result: Dict):
    """Render top performers"""
    top_performers = result.get("top_performers", [])

    if not top_performers:
        st.warning("No top performers data available")
        return

    for performer in top_performers:
        with st.container():
            col1, col2 = st.columns([1, 3])

            with col1:
                st.markdown(f"### 🥇 Rank {performer['rank']}")
                st.markdown(f"**{performer['username']}**")
                st.metric("Points", performer['points'])
                st.metric("Total Skill Gain", f"{performer['total_skill_gain']:+.1f}")

            with col2:
                st.markdown("#### Skill Changes")
                skills_changed = performer.get("skills_changed", {})

                for skill_name, changes in skills_changed.items():
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.write(f"**{skill_name}**")
                    with col_b:
                        st.write(f"Before: {changes['before']} → After: {changes['after']}")
                    with col_c:
                        change_val = changes['change']
                        if "+" in change_val:
                            st.success(change_val)
                        elif "-" in change_val:
                            st.error(change_val)
                        else:
                            st.info(change_val)

        st.markdown("---")

def render_bottom_performers(result: Dict):
    """Render bottom performers"""
    bottom_performers = result.get("bottom_performers", [])

    if not bottom_performers:
        st.info("No bottom performers data (tournament may have too few players)")
        return

    for performer in bottom_performers:
        with st.container():
            col1, col2 = st.columns([1, 3])

            with col1:
                st.markdown(f"### 📉 Rank {performer['rank']}")
                st.markdown(f"**{performer['username']}**")
                st.metric("Points", performer['points'])
                st.metric("Total Skill Gain", f"{performer['total_skill_gain']:+.1f}")

            with col2:
                st.markdown("#### Skill Changes")
                skills_changed = performer.get("skills_changed", {})

                for skill_name, changes in skills_changed.items():
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.write(f"**{skill_name}**")
                    with col_b:
                        st.write(f"Before: {changes['before']} → After: {changes['after']}")
                    with col_c:
                        change_val = changes['change']
                        if "+" in change_val:
                            st.success(change_val)
                        elif "-" in change_val:
                            st.error(change_val)
                        else:
                            st.info(change_val)

        st.markdown("---")

def render_insights(result: Dict):
    """Render insights"""
    insights = result.get("insights", [])

    if not insights:
        st.warning("No insights available")
        return

    for insight in insights:
        category = insight.get("category", "INFO")
        severity = insight.get("severity", "INFO")
        message = insight.get("message", "")

        if severity == "SUCCESS":
            st.success(f"**{category}**: {message}")
        elif severity == "ERROR":
            st.error(f"**{category}**: {message}")
        elif severity == "WARNING":
            st.warning(f"**{category}**: {message}")
        else:
            st.info(f"**{category}**: {message}")

    # Execution summary
    st.markdown("### Execution Summary")
    execution_summary = result.get("execution_summary", {})
    steps = execution_summary.get("steps_completed", [])

    for i, step in enumerate(steps, 1):
        st.text(f"{i}. {step}")

def main():
    """Main application"""
    # Initialize session state
    if "screen" not in st.session_state:
        st.session_state.screen = "configuration"

    # Route to appropriate screen
    if st.session_state.screen == "configuration":
        render_configuration_screen()
    elif st.session_state.screen == "progress":
        render_progress_screen()
    elif st.session_state.screen == "results":
        render_results_screen()

if __name__ == "__main__":
    main()
