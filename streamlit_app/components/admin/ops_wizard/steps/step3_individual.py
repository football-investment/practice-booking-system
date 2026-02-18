"""OPS Wizard — Step 3a: Individual Scoring Type (INDIVIDUAL_RANKING path)"""
import streamlit as st
from ..wizard_config import SCENARIO_CONFIG, INDIVIDUAL_SCORING_CONFIG
from .step3_h2h import _render_campus_selector


def render_step3_individual_scoring(token: str = None):
    """Step 3 (alternate): Individual Scoring Type — only for INDIVIDUAL_RANKING"""
    if token is None:
        token = st.session_state.get("token", "")
    st.markdown("### Step 3 of 8: Select Scoring Method")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    if not scenario:
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    st.info(f"""
**Scenario:** {SCENARIO_CONFIG[scenario]['label']}
**Format:** 🏃 Individual Ranking
    """)
    st.markdown("---")

    scoring_options = list(INDIVIDUAL_SCORING_CONFIG.keys())
    default_scoring = st.session_state.get("wizard_scoring_type_saved", "SCORE_BASED")
    default_scoring_index = scoring_options.index(default_scoring) if default_scoring in scoring_options else 0

    scoring_type = st.radio(
        "Choose scoring method",
        options=scoring_options,
        format_func=lambda x: INDIVIDUAL_SCORING_CONFIG[x]["label"],
        key="wizard_scoring_type_widget",
        index=default_scoring_index,
    )

    if scoring_type:
        cfg = INDIVIDUAL_SCORING_CONFIG[scoring_type]
        st.info(f"""
**{cfg['label']}**

{cfg['description']}

**Example:** {cfg['example']}
        """)

        # ── Ranking direction override ────────────────────────────────────────
        if cfg["ranking_direction"] is not None:
            # Human-friendly labels per direction × scoring type
            _dir_labels = {
                ("TIME_BASED",     "ASC"):  "⬇️ Lowest time wins  (fastest — e.g. sprint)",
                ("TIME_BASED",     "DESC"): "⬆️ Highest time wins (longest — e.g. endurance)",
                ("SCORE_BASED",    "ASC"):  "⬇️ Lowest score wins (e.g. fewest errors)",
                ("SCORE_BASED",    "DESC"): "⬆️ Highest score wins (e.g. goals, points)",
                ("DISTANCE_BASED", "ASC"):  "⬇️ Shortest distance wins (e.g. closest-to-pin)",
                ("DISTANCE_BASED", "DESC"): "⬆️ Farthest distance wins (e.g. long jump)",
            }
            default_dir = cfg["ranking_direction"]
            saved_dir = st.session_state.get("wizard_ranking_direction_saved", default_dir)
            if saved_dir not in ("ASC", "DESC"):
                saved_dir = default_dir

            chosen_dir = st.radio(
                "Ranking direction",
                options=["ASC", "DESC"],
                format_func=lambda d: _dir_labels.get((scoring_type, d), d),
                index=0 if saved_dir == "ASC" else 1,
                key=f"wizard_ranking_dir_widget_{scoring_type}",
                horizontal=True,
            )
            st.session_state["wizard_ranking_direction_saved"] = chosen_dir
        else:
            # PLACEMENT — no numeric direction
            chosen_dir = None
            st.caption("Ranking by finish position — no numeric direction applies.")

        # ── Number of rounds (1–10, IR only) ─────────────────────────────────
        st.markdown("**Number of rounds**")
        _saved_rounds = st.session_state.get("wizard_num_rounds_saved", 1)
        if not isinstance(_saved_rounds, int) or not (1 <= _saved_rounds <= 10):
            _saved_rounds = 1
        chosen_rounds = st.slider(
            "How many rounds / attempts per player?",
            min_value=1, max_value=10,
            value=_saved_rounds,
            step=1,
            key="wizard_num_rounds_widget",
            help="Each round = one session where all players submit a measured_value. "
                 "Best result (or total) is used for final ranking depending on backend config.",
        )
        if chosen_rounds > 1:
            st.caption(f"→ {chosen_rounds} sessions will be created, each with all {scoring_type or 'IR'} players.")
        else:
            st.caption("→ 1 session (single attempt per player).")

        # ── Campus / venue selection (required) ──────────────────────────────
        campus_valid = _render_campus_selector(token)
        scoring_valid = True
        st.session_state["wizard_step3_valid"] = scoring_valid and campus_valid
        st.session_state["wizard_completed_steps"].add(3)
    else:
        chosen_dir = None
        chosen_rounds = 1
        campus_valid = False
        st.session_state["wizard_step3_valid"] = False

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step3_ind_back"):
            st.session_state["wizard_current_step"] = 2
            st.rerun()
    with col2:
        next_enabled = st.session_state.get("wizard_step3_valid", False)
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step3_ind_next"):
            st.session_state["wizard_scoring_type_saved"] = scoring_type
            st.session_state["wizard_ranking_direction_saved"] = chosen_dir
            st.session_state["wizard_num_rounds_saved"] = chosen_rounds
            st.session_state["wizard_current_step"] = 4
            st.rerun()
