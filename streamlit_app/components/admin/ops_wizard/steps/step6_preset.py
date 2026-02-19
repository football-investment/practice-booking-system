"""OPS Wizard — Step 6/4: Game Preset Selection"""
import streamlit as st
import requests
from config import API_BASE_URL


def render_step_game_preset():
    """Step 4 of 8: Game Preset Selection"""
    st.markdown("### Step 4 of 8: Select Game Preset")
    st.info(
        "Choose a **game preset** to automatically configure which skills this tournament develops "
        "and their relative weights. Select *None* to skip skill configuration entirely."
    )
    st.markdown("---")

    # ── Fetch preset list (summary) ───────────────────────────────────────────
    @st.cache_data(ttl=60, show_spinner=False)
    def _fetch_presets(token: str) -> list:
        try:
            resp = requests.get(
                f"{API_BASE_URL}/api/v1/game-presets/",
                headers={"Authorization": f"Bearer {token}"},
                params={"active_only": "true"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("presets", data) if isinstance(data, dict) else data
        except Exception:
            pass
        return []

    # ── Fetch full detail for skill weights (cached per id) ───────────────────
    @st.cache_data(ttl=120, show_spinner=False)
    def _fetch_preset_detail(token: str, preset_id: int) -> dict:
        try:
            resp = requests.get(
                f"{API_BASE_URL}/api/v1/game-presets/{preset_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    token = st.session_state.get("token", "")

    col_reload, _ = st.columns([1, 4])
    with col_reload:
        if st.button("🔄 Reload presets", key="reload_presets", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    presets = _fetch_presets(token)
    active_presets = [p for p in presets if p.get("is_active", True)]

    if not active_presets:
        st.warning("No active game presets found. Check API connection or click 🔄 Reload.")
        active_presets = []

    # ── Selectbox: None + sorted presets (recommended first) ─────────────────
    recommended = [p for p in active_presets if p.get("is_recommended")]
    others = [p for p in active_presets if not p.get("is_recommended")]
    sorted_presets = recommended + others

    def _preset_label(p: dict) -> str:
        badge = "⭐ " if p.get("is_recommended") else ""
        cat = p.get("game_category", "")
        cat_str = f"  [{cat}]" if cat else ""
        diff = p.get("difficulty_level", "")
        diff_str = f"  {diff}" if diff else ""
        n_skills = len(p.get("skills_tested") or [])
        skills_str = f"  · {n_skills} skills" if n_skills else ""
        return f"{badge}{p['name']}{cat_str}{diff_str}{skills_str}  (id={p['id']})"

    none_label = "— None (no game preset) —"
    preset_labels = [none_label] + [_preset_label(p) for p in sorted_presets]
    preset_by_label = {_preset_label(p): p for p in sorted_presets}

    saved_id = st.session_state.get("wizard_game_preset_saved")
    default_label = none_label
    if saved_id is not None:
        for lbl, p in preset_by_label.items():
            if p.get("id") == saved_id:
                default_label = lbl
                break
    default_idx = preset_labels.index(default_label)

    selected_label = st.selectbox(
        f"Game Preset ({len(active_presets)} available)",
        options=preset_labels,
        index=default_idx,
        key="wizard_game_preset_widget",
        help="Presets define skill mappings, weights, and progression rules for this tournament.",
    )

    selected_preset = preset_by_label.get(selected_label)

    # ── Preview selected preset ───────────────────────────────────────────────
    if selected_preset:
        pid = selected_preset["id"]

        skills_tested: list = selected_preset.get("skills_tested") or []
        desc = selected_preset.get("description", "")
        category = selected_preset.get("game_category", "")
        difficulty = selected_preset.get("difficulty_level", "")
        rec_count = selected_preset.get("recommended_player_count") or {}

        detail = _fetch_preset_detail(token, pid)
        skill_cfg = (detail.get("game_config") or {}).get("skill_config", {})
        skill_weights: dict = skill_cfg.get("skill_weights", {})

        badges = []
        if selected_preset.get("is_recommended"):
            badges.append("⭐ Recommended")
        if selected_preset.get("is_locked"):
            badges.append("🔒 Locked")
        if category:
            badges.append(f"🎮 {category}")
        if difficulty:
            badges.append(f"📶 {difficulty}")
        badge_str = "  ·  ".join(badges)

        st.success(f"**{selected_preset['name']}**" + (f"  —  {badge_str}" if badge_str else ""))
        if desc:
            st.caption(desc)
        if rec_count:
            min_p = rec_count.get("min", "?")
            max_p = rec_count.get("max", "?")
            st.caption(f"Recommended player count: {min_p}–{max_p}")

        if skills_tested:
            sorted_skills = sorted(
                skills_tested,
                key=lambda s: skill_weights.get(s, 0),
                reverse=True,
            )
            skill_parts = []
            for skill in sorted_skills:
                weight = skill_weights.get(skill)
                label = skill.replace("_", " ").title()
                if weight is not None:
                    pct = weight * 100
                    skill_parts.append(f"**{label}** {pct:.0f}%")
                else:
                    skill_parts.append(f"**{label}**")
            st.caption(f"{len(skills_tested)} skills: " + "  ·  ".join(skill_parts))
        else:
            st.caption("No skill configuration details available for this preset.")
    else:
        st.caption("No preset selected — tournament will run without automated skill syncing.")

    # Mark step valid (optional step — always valid)
    st.session_state["wizard_step4_valid"] = True
    st.session_state["wizard_completed_steps"].add(4)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="game_preset_back"):
            st.session_state["wizard_current_step"] = 3
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="game_preset_next"):
            st.session_state["wizard_game_preset_saved"] = selected_preset["id"] if selected_preset else None
            st.session_state["wizard_current_step"] = 5
            st.rerun()
