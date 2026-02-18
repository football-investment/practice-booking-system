"""
OPS Wizard Package

Tournament creation wizard with state management and launch execution.
Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
"""

import streamlit as st

from .wizard_state import init_wizard_state, reset_wizard_state
from .launch import execute_launch
from .wizard_config import (
    SCENARIO_CONFIG,
    TOURNAMENT_TYPE_CONFIG,
    INDIVIDUAL_SCORING_CONFIG,
    SIMULATION_MODE_CONFIG,
    scoring_label,
)
from .steps.step1_scenario import render_step1_scenario
from .steps.step2_format import render_step2_format
from .steps.step3_individual import render_step3_individual_scoring
from .steps.step3_h2h import render_step3_h2h
from .steps.step4_players import render_step3_player_count
from .steps.step5_simulation import render_step4_simulation_mode
from .steps.step6_preset import render_step_game_preset
from .steps.step7_reward import render_step_reward_config
from .steps.step8_review import render_step5_review_launch


def render_wizard_progress(current_step: int):
    """Render wizard progress indicator (8 steps)"""
    steps = ["Scenario", "Format", "Type", "Game", "Count", "Simulation", "Reward", "Review"]

    cols = st.columns(8)
    for idx, (col, step_name) in enumerate(zip(cols, steps), start=1):
        with col:
            if idx < current_step:
                st.markdown(f"✅ **{step_name}**")
            elif idx == current_step:
                st.markdown(f"➡️ **{step_name}**")
            else:
                st.markdown(f"⬜ {step_name}")


def render_wizard_summary_bar(current_step: int):
    """Persistent summary bar — shows confirmed selections above every wizard step."""
    if current_step < 2:
        return

    ss = st.session_state
    scenario    = ss.get("wizard_scenario_saved")
    fmt         = ss.get("wizard_format_saved")
    t_type      = ss.get("wizard_tournament_type_saved")
    scoring     = ss.get("wizard_scoring_type_saved")
    ranking_dir = ss.get("wizard_ranking_direction_saved")
    game_preset = ss.get("wizard_game_preset_saved")
    player_count = ss.get("wizard_player_count_saved")
    pinned_ids  = ss.get("wizard_player_ids_saved")
    sim_mode    = ss.get("wizard_simulation_mode_saved")
    reward_cfg  = ss.get("wizard_reward_config_saved")
    campus_ids  = ss.get("wizard_campus_ids_saved", [])

    parts = []

    if scenario and scenario in SCENARIO_CONFIG:
        parts.append(f"🎯 {SCENARIO_CONFIG[scenario]['label']}")

    if fmt:
        fmt_label = "⚔️ H2H" if fmt == "HEAD_TO_HEAD" else "🏃 Individual"
        parts.append(fmt_label)

    if fmt == "HEAD_TO_HEAD" and t_type and t_type in TOURNAMENT_TYPE_CONFIG:
        parts.append(f"🏆 {TOURNAMENT_TYPE_CONFIG[t_type]['label']}")
    elif fmt == "INDIVIDUAL_RANKING" and scoring and scoring in INDIVIDUAL_SCORING_CONFIG:
        parts.append(f"📊 {scoring_label(scoring, ranking_dir)}")

    if campus_ids:
        parts.append(f"🏟️ {len(campus_ids)} campus(es)")

    if current_step >= 5:  # step 4 (game preset) was completed
        if game_preset is not None:
            parts.append(f"🎮 Preset #{game_preset}")
        else:
            parts.append("🎮 No preset")

    if player_count:
        if pinned_ids:
            n_pinned = len(pinned_ids)
            auto_fill = player_count - n_pinned
            parts.append(f"👥 {player_count}p ({n_pinned} pinned + {auto_fill} auto)")
        else:
            parts.append(f"👥 {player_count} players")

    if sim_mode and sim_mode in SIMULATION_MODE_CONFIG:
        parts.append(f"⚡ {SIMULATION_MODE_CONFIG[sim_mode]['label']}")

    if current_step >= 8:  # step 7 (rewards) was completed
        if reward_cfg:
            fp = reward_cfg.get("first_place", {})
            parts.append(f"🥇 {fp.get('xp', '?')} XP / {fp.get('credits', '?')} cr")
        else:
            parts.append("🎁 OPS Default rewards")

    if not parts:
        return

    with st.container(border=True):
        st.caption("📋 **Summary:**  " + "  ·  ".join(parts))


def render_launch_success():
    """Show post-launch success screen with full summary until user starts a new wizard."""
    result = st.session_state.get("wizard_launch_result", {})
    t_id         = result.get("tournament_id")
    enrolled     = result.get("enrolled_count", 0)
    sessions     = result.get("session_count", 0)
    scenario     = result.get("scenario", "")
    fmt          = result.get("tournament_format", "HEAD_TO_HEAD")
    t_type       = result.get("tournament_type")
    scoring      = result.get("scoring_type")
    player_count = result.get("player_count", 0)
    player_ids   = result.get("player_ids")
    sim_mode     = result.get("simulation_mode", "")
    preset_id    = result.get("game_preset_id")
    t_name       = result.get("tournament_name") or f"OPS Tournament #{t_id}"

    st.success(f"✅ **Tournament #{t_id} launched and tracking started!**")

    with st.container(border=True):
        st.markdown(f"### 📋 Launch Summary — {t_name}")
        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🆔 Tournament ID", f"#{t_id}")
        with c2:
            st.metric("👥 Enrolled Players", enrolled)
        with c3:
            st.metric("🎮 Sessions Created", sessions)
        if sessions == 0 and player_count >= 128:
            st.info("⏳ Sessions are being generated in the background. Refresh the monitor card in a few seconds.")

        st.markdown("---")

        details = []
        if scenario and scenario in SCENARIO_CONFIG:
            details.append(f"**Scenario:** {SCENARIO_CONFIG[scenario]['label']}")
        if fmt == "HEAD_TO_HEAD":
            details.append("**Format:** ⚔️ Head-to-Head")
            if t_type and t_type in TOURNAMENT_TYPE_CONFIG:
                details.append(f"**Type:** {TOURNAMENT_TYPE_CONFIG[t_type]['label']}")
        else:
            details.append("**Format:** 🏃 Individual Ranking")
            if scoring and scoring in INDIVIDUAL_SCORING_CONFIG:
                _rd = st.session_state.get("wizard_ranking_direction_saved")
                details.append(f"**Scoring:** {scoring_label(scoring, _rd)}")
        if preset_id is not None:
            details.append(f"**Game Preset:** id={preset_id}")
        else:
            details.append("**Game Preset:** *(none)*")
        if player_ids:
            n_pinned = len(player_ids)
            details.append(f"**Players:** {player_count} ({n_pinned} pinned + {player_count - n_pinned} auto-fill)")
        else:
            details.append(f"**Players:** {player_count} (auto-fill from seed pool)")
        if sim_mode and sim_mode in SIMULATION_MODE_CONFIG:
            details.append(f"**Simulation:** {SIMULATION_MODE_CONFIG[sim_mode]['label']}")

        for line in details:
            st.markdown(line)

        st.markdown("---")
        st.info("🔴 **Live tracking active** — the tournament is shown in the monitoring panel above. Auto-refresh is enabled.")

    st.markdown("")
    if st.button("🔄 Launch another tournament", type="primary"):
        del st.session_state["wizard_launch_result"]
        st.rerun()


def render_wizard():
    """Main wizard renderer — 8-step flow with format-aware routing.

    Step 1: Scenario
    Step 2: Format (HEAD_TO_HEAD vs INDIVIDUAL_RANKING)
    Step 3: HEAD_TO_HEAD → Tournament Type  |  INDIVIDUAL_RANKING → Scoring Method
    Step 4: Game Preset (GānFootvolley, GānFoottennis, Custom…)
    Step 5: Player Count
    Step 6: Simulation Mode
    Step 7: Reward Configuration
    Step 8: Review & Launch
    """
    init_wizard_state()

    # If a tournament was just launched, show success screen until user starts a new one
    if st.session_state.get("wizard_launch_result"):
        render_launch_success()
        return

    current_step = st.session_state["wizard_current_step"]

    render_wizard_progress(current_step)
    render_wizard_summary_bar(current_step)

    st.markdown("---")

    if current_step == 1:
        render_step1_scenario()
    elif current_step == 2:
        render_step2_format()
    elif current_step == 3:
        fmt = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
        if fmt == "INDIVIDUAL_RANKING":
            render_step3_individual_scoring()
        else:
            render_step3_h2h()
    elif current_step == 4:
        render_step_game_preset()
    elif current_step == 5:
        render_step3_player_count()
    elif current_step == 6:
        render_step4_simulation_mode()
    elif current_step == 7:
        render_step_reward_config()
    elif current_step == 8:
        render_step5_review_launch()
    else:
        st.error(f"Invalid wizard step: {current_step}")
        st.session_state["wizard_current_step"] = 1
        st.rerun()


__all__ = [
    "init_wizard_state",
    "reset_wizard_state",
    "execute_launch",
    "render_wizard",
    "render_wizard_progress",
    "render_wizard_summary_bar",
    "render_launch_success",
]
