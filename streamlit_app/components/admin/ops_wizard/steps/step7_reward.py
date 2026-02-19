"""OPS Wizard — Step 7: Reward Configuration"""
import streamlit as st


def render_step_reward_config():
    """Step 7 of 8: Reward Configuration"""
    st.markdown("### Step 7 of 8: Configure Rewards")
    st.info(
        "Choose a **reward template** or create a custom configuration. "
        "Rewards (XP + Credits) are distributed automatically when the tournament finishes."
    )
    st.markdown("---")

    REWARD_TEMPLATES = {
        "ops_default": {
            "label": "OPS Default  (high XP — ideal for testing)",
            "config": {
                "first_place":   {"xp": 2000, "credits": 1000},
                "second_place":  {"xp": 1200, "credits": 500},
                "third_place":   {"xp": 800,  "credits": 250},
                "participation": {"xp": 100,  "credits": 0},
            },
        },
        "standard": {
            "label": "Standard  (500 / 300 / 200 XP)",
            "config": {
                "first_place":   {"xp": 500, "credits": 100},
                "second_place":  {"xp": 300, "credits": 60},
                "third_place":   {"xp": 200, "credits": 30},
                "participation": {"xp": 50,  "credits": 0},
            },
        },
        "championship": {
            "label": "Championship  (1000 / 600 / 400 XP)",
            "config": {
                "first_place":   {"xp": 1000, "credits": 400},
                "second_place":  {"xp": 600,  "credits": 200},
                "third_place":   {"xp": 400,  "credits": 100},
                "participation": {"xp": 100,  "credits": 0},
            },
        },
        "friendly": {
            "label": "Friendly  (200 / 100 / 50 XP)",
            "config": {
                "first_place":   {"xp": 200, "credits": 50},
                "second_place":  {"xp": 100, "credits": 25},
                "third_place":   {"xp": 50,  "credits": 10},
                "participation": {"xp": 25,  "credits": 0},
            },
        },
        "custom": {
            "label": "Custom  (edit values below)",
            "config": None,
        },
    }

    template_keys = list(REWARD_TEMPLATES.keys())
    template_labels = [REWARD_TEMPLATES[k]["label"] for k in template_keys]

    saved_config = st.session_state.get("wizard_reward_config_saved")
    default_template_idx = 0  # ops_default

    selected_label = st.radio(
        "Reward Template",
        options=template_labels,
        index=default_template_idx,
        key="wizard_reward_template_widget",
    )

    selected_key = template_keys[template_labels.index(selected_label)]
    template_cfg = REWARD_TEMPLATES[selected_key]["config"]

    if selected_key == "custom":
        st.markdown("#### Custom Reward Values")
        st.caption("Enter XP and Credits per placement tier:")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**XP**")
            xp_1st  = st.number_input("1st Place XP",    min_value=0, value=(saved_config or {}).get("first_place",   {}).get("xp", 1000), step=50, key="wizard_reward_xp1")
            xp_2nd  = st.number_input("2nd Place XP",    min_value=0, value=(saved_config or {}).get("second_place",  {}).get("xp", 600),  step=50, key="wizard_reward_xp2")
            xp_3rd  = st.number_input("3rd Place XP",    min_value=0, value=(saved_config or {}).get("third_place",   {}).get("xp", 400),  step=50, key="wizard_reward_xp3")
            xp_part = st.number_input("Participation XP", min_value=0, value=(saved_config or {}).get("participation",{}).get("xp", 50),   step=10, key="wizard_reward_xp_part")
        with c2:
            st.markdown("**Credits**")
            cr_1st  = st.number_input("1st Place Credits",     min_value=0, value=(saved_config or {}).get("first_place",   {}).get("credits", 200), step=10, key="wizard_reward_cr1")
            cr_2nd  = st.number_input("2nd Place Credits",     min_value=0, value=(saved_config or {}).get("second_place",  {}).get("credits", 100), step=10, key="wizard_reward_cr2")
            cr_3rd  = st.number_input("3rd Place Credits",     min_value=0, value=(saved_config or {}).get("third_place",   {}).get("credits", 50),  step=10, key="wizard_reward_cr3")
            cr_part = st.number_input("Participation Credits", min_value=0, value=(saved_config or {}).get("participation",{}).get("credits", 0),    step=5,  key="wizard_reward_cr_part")

        final_config = {
            "first_place":   {"xp": int(xp_1st),  "credits": int(cr_1st)},
            "second_place":  {"xp": int(xp_2nd),  "credits": int(cr_2nd)},
            "third_place":   {"xp": int(xp_3rd),  "credits": int(cr_3rd)},
            "participation": {"xp": int(xp_part), "credits": int(cr_part)},
        }
    else:
        final_config = template_cfg
        cfg = final_config
        st.markdown("#### Reward Preview")
        tiers = [
            ("🥇 1st Place",     cfg["first_place"]),
            ("🥈 2nd Place",     cfg["second_place"]),
            ("🥉 3rd Place",     cfg["third_place"]),
            ("⚽ Participation", cfg["participation"]),
        ]
        cols = st.columns(4)
        for col, (label, tier) in zip(cols, tiers):
            col.metric(label, f"+{tier['xp']} XP", f"+{tier['credits']} cr")

    st.session_state["wizard_step7_valid"] = True
    st.session_state["wizard_completed_steps"].add(7)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="reward_config_back"):
            st.session_state["wizard_current_step"] = 6
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="reward_config_next"):
            st.session_state["wizard_reward_config_saved"] = final_config
            st.session_state["wizard_current_step"] = 8
            st.rerun()
