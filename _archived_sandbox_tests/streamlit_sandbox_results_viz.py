"""
Streamlit Sandbox Results Visualization
Enhanced visual presentation of tournament test results
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any

def render_results_dashboard(result: Dict[str, Any]):
    """
    Enhanced results visualization with charts and metrics
    """

    # Header with verdict
    verdict = result.get("verdict", "UNKNOWN")
    tournament = result.get("tournament", {})
    execution = result.get("execution_summary", {})

    # Hero Section
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if verdict == "WORKING":
            st.success(f"### 🎉 {verdict}")
        elif verdict == "PARTIAL":
            st.warning(f"### ⚠️ {verdict}")
        else:
            st.error(f"### ❌ {verdict}")

    with col2:
        st.metric(
            "⏱️ Duration",
            f"{execution.get('duration_seconds', 0):.2f}s"
        )

    with col3:
        st.metric(
            "🏆 Tournament ID",
            tournament.get('id', 'N/A')
        )

    st.markdown("---")

    # Game Preset Information (if used)
    game_preset_id = tournament.get('game_preset_id')
    game_config_overrides = tournament.get('game_config_overrides')

    if game_preset_id:
        st.markdown("### 🎮 Game Configuration")

        with st.expander("📋 Preset & Configuration Details", expanded=False):
            # Fetch preset details
            import requests
            try:
                preset_response = requests.get(f"http://localhost:8000/api/v1/game-presets/{game_preset_id}")
                if preset_response.status_code == 200:
                    preset_details = preset_response.json()

                    col_a, col_b = st.columns([1, 1])

                    with col_a:
                        st.markdown("**🎯 Selected Preset:**")
                        st.info(f"**{preset_details['name']}**")
                        st.caption(preset_details.get('description', 'N/A'))

                        game_config = preset_details.get('game_config', {})
                        skill_config = game_config.get('skill_config', {})

                        st.markdown("**⚽ Skills Tested:**")
                        skills = skill_config.get('skills_tested', [])
                        for skill in skills:
                            st.markdown(f"- {skill.replace('_', ' ').title()}")

                        st.markdown("**📊 Skill Weights:**")
                        weights = skill_config.get('skill_weights', {})
                        for skill, weight in weights.items():
                            st.markdown(f"- {skill.replace('_', ' ').title()}: {weight * 100:.0f}%")

                    with col_b:
                        format_config = game_config.get('format_config', {})
                        h2h_config = format_config.get('HEAD_TO_HEAD', {})
                        match_sim = h2h_config.get('match_simulation', {})

                        st.markdown("**🎲 Match Probabilities (Preset):**")
                        if match_sim:
                            st.markdown(f"- Draw: {match_sim.get('draw_probability', 0) * 100:.0f}%")
                            st.markdown(f"- Home Win: {match_sim.get('home_win_probability', 0) * 100:.0f}%")
                            away_prob = 1.0 - match_sim.get('draw_probability', 0) - match_sim.get('home_win_probability', 0)
                            st.markdown(f"- Away Win: {away_prob * 100:.0f}%")

                        # Show override status
                        if game_config_overrides:
                            st.markdown("---")
                            st.warning("**⚠️ Custom Overrides Applied:**")
                            st.json(game_config_overrides)
                        else:
                            st.markdown("---")
                            st.success("**✅ Pure Preset** (no overrides)")

                else:
                    st.warning(f"⚠️ Could not fetch preset details (ID: {game_preset_id})")
            except Exception as e:
                st.error(f"❌ Error fetching preset: {e}")

        st.markdown("---")

    # Key Metrics Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "👥 Players",
            tournament.get('player_count', 0)
        )

    with col2:
        skills_count = len(tournament.get('skills_tested', []))
        st.metric(
            "🎯 Skills Tested",
            skills_count
        )

    with col3:
        top_performers = result.get('top_performers', [])
        if top_performers:
            top_gain = top_performers[0].get('total_skill_gain', 0)
            st.metric(
                "⭐ Top Performer Gain",
                f"+{top_gain:.1f}",
                delta=f"{top_gain:.1f}",
                delta_color="normal"
            )

    with col4:
        bottom_performers = result.get('bottom_performers', [])
        if bottom_performers:
            bottom_loss = bottom_performers[0].get('total_skill_gain', 0)
            st.metric(
                "📉 Bottom Performer Loss",
                f"{bottom_loss:.1f}",
                delta=f"{bottom_loss:.1f}",
                delta_color="inverse"
            )

    st.markdown("---")

    # Skill Progression Chart
    st.subheader("🎯 Skill Progression Overview")

    skill_progression = result.get('skill_progression', {})
    if skill_progression:
        # Prepare data for chart
        skills = []
        changes = []
        colors = []

        for skill_name, skill_data in skill_progression.items():
            before_avg = skill_data.get('before', {}).get('average', 0)
            after_avg = skill_data.get('after', {}).get('average', 0)
            change = after_avg - before_avg

            skills.append(skill_name.replace('_', ' ').title())
            changes.append(change)
            colors.append('green' if change > 0 else 'red')

        # Create horizontal bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=changes,
                y=skills,
                orientation='h',
                marker=dict(
                    color=changes,
                    colorscale=['red', 'yellow', 'green'],
                    cmid=0
                ),
                text=[f"{c:+.1f}" for c in changes],
                textposition='outside',
            )
        ])

        fig.update_layout(
            title="Average Skill Change (Points)",
            xaxis_title="Change (points)",
            yaxis_title="Skill",
            height=400,
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Top vs Bottom Performers Comparison
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Top 3 Performers")
        top_performers = result.get('top_performers', [])

        if top_performers:
            # Create DataFrame
            top_df = pd.DataFrame([
                {
                    'Rank': f"#{p.get('rank')}",
                    'Player': p.get('username', 'Unknown'),
                    'Points': float(p.get('points', 0)),
                    'Total Gain': f"+{p.get('total_skill_gain', 0):.1f}"
                }
                for p in top_performers[:3]
            ])

            st.dataframe(
                top_df,
                hide_index=True,
                use_container_width=True
            )

            # Pie chart of points distribution
            fig_pie = px.pie(
                top_df,
                names='Player',
                values='Points',
                title='Points Distribution (Top 3)',
                color_discrete_sequence=px.colors.sequential.Greens_r
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("📉 Bottom 2 Performers")
        bottom_performers = result.get('bottom_performers', [])

        if bottom_performers:
            # Create DataFrame
            bottom_df = pd.DataFrame([
                {
                    'Rank': f"#{p.get('rank')}",
                    'Player': p.get('username', 'Unknown'),
                    'Points': float(p.get('points', 0)),
                    'Total Loss': f"{p.get('total_skill_gain', 0):.1f}"
                }
                for p in bottom_performers[:2]
            ])

            st.dataframe(
                bottom_df,
                hide_index=True,
                use_container_width=True
            )

            # Bar chart of losses
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=[p.get('username', 'Unknown') for p in bottom_performers[:2]],
                    y=[p.get('total_skill_gain', 0) for p in bottom_performers[:2]],
                    marker=dict(color='red'),
                    text=[f"{p.get('total_skill_gain', 0):.1f}" for p in bottom_performers[:2]],
                    textposition='outside'
                )
            ])

            fig_bar.update_layout(
                title='Skill Loss (Bottom 2)',
                yaxis_title='Total Skill Change',
                showlegend=False,
                height=300
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Detailed Player Skill Changes
    st.subheader("🔍 Detailed Skill Changes")

    # Select player to inspect
    all_performers = top_performers + bottom_performers
    player_names = [p.get('username', 'Unknown') for p in all_performers]

    if player_names:
        selected_player = st.selectbox("Select Player", player_names)

        # Find selected player data
        player_data = None
        for p in all_performers:
            if p.get('username') == selected_player:
                player_data = p
                break

        if player_data:
            skills_changed = player_data.get('skills_changed', {})

            if skills_changed:
                # Create DataFrame
                skill_details = []
                for skill_name, skill_data in skills_changed.items():
                    skill_details.append({
                        'Skill': skill_name.replace('_', ' ').title(),
                        'Before': skill_data.get('before', 0),
                        'After': skill_data.get('after', 0),
                        'Change': skill_data.get('change', '0'),
                    })

                skill_df = pd.DataFrame(skill_details)

                # Display table
                st.dataframe(skill_df, hide_index=True, use_container_width=True)

                # Line chart showing before/after
                fig_line = go.Figure()

                fig_line.add_trace(go.Scatter(
                    x=skill_df['Skill'],
                    y=skill_df['Before'],
                    mode='lines+markers',
                    name='Before',
                    line=dict(color='blue', width=2)
                ))

                fig_line.add_trace(go.Scatter(
                    x=skill_df['Skill'],
                    y=skill_df['After'],
                    mode='lines+markers',
                    name='After',
                    line=dict(color='green', width=2)
                ))

                fig_line.update_layout(
                    title=f"Skill Progression: {selected_player}",
                    xaxis_title="Skill",
                    yaxis_title="Skill Value",
                    height=400
                )

                st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # Execution Steps Timeline
    st.subheader("⏱️ Execution Timeline")

    steps = execution.get('steps_completed', [])
    if steps:
        for idx, step in enumerate(steps, 1):
            st.markdown(f"**{idx}.** {step}")

    st.markdown("---")

    # Insights
    st.subheader("💡 Insights")

    insights = result.get('insights', [])
    if insights:
        for insight in insights:
            severity = insight.get('severity', 'INFO')
            message = insight.get('message', '')
            category = insight.get('category', 'GENERAL')

            if severity == 'SUCCESS':
                st.success(f"✅ **{category}**: {message}")
            elif severity == 'WARNING':
                st.warning(f"⚠️ **{category}**: {message}")
            elif severity == 'ERROR':
                st.error(f"❌ **{category}**: {message}")
            else:
                st.info(f"ℹ️ **{category}**: {message}")

    st.markdown("---")

    # Export Section
    st.subheader("📥 Export Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📄 Export PDF", use_container_width=True):
            export_url = result.get('export_data', {}).get('export_url', '')
            if export_url:
                st.info(f"PDF Export URL: {export_url}")
            else:
                st.warning("PDF export not available")

    with col2:
        if st.button("📊 Export CSV", use_container_width=True):
            st.info("CSV export coming soon")

    with col3:
        if st.button("📋 Copy JSON", use_container_width=True):
            st.code(str(result), language='json')


# Test with your result data
if __name__ == "__main__":
    st.set_page_config(page_title="Sandbox Results Viz", layout="wide")

    # Mock data for testing (replace with actual result)
    mock_result = {
        "verdict": "WORKING",
        "tournament": {"id": 137, "player_count": 16, "skills_tested": ["ball_control", "passing"]},
        "execution_summary": {"duration_seconds": 5.17, "steps_completed": ["Step 1", "Step 2"]},
        "top_performers": [
            {"rank": 1, "username": "player1", "points": "94.00", "total_skill_gain": 47.8, "skills_changed": {}},
        ],
        "bottom_performers": [
            {"rank": 8, "username": "player8", "points": "14.00", "total_skill_gain": -177.5, "skills_changed": {}},
        ],
        "skill_progression": {
            "ball_control": {"before": {"average": 69.9}, "after": {"average": 70.9}},
            "passing": {"before": {"average": 66.7}, "after": {"average": 70.4}},
        },
        "insights": [
            {"category": "STATUS", "severity": "SUCCESS", "message": "All good"},
        ]
    }

    render_results_dashboard(mock_result)
