"""OPS Wizard — Step 4/5: Player Selection (target count + optional pinned players)"""
import streamlit as st
import requests
from config import API_BASE_URL
from ..wizard_config import (
    SCENARIO_CONFIG,
    TOURNAMENT_TYPE_CONFIG,
    _SAFETY_CONFIRMATION_THRESHOLD,
    get_group_knockout_config,
    estimate_session_count,
    estimate_duration_hours,
)


def validate_step3_detailed():
    """Validate Step 4: Player Count Selection"""
    player_count = st.session_state.get("wizard_player_count_saved") or st.session_state.get("wizard_player_count_widget")
    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")

    if not player_count or not scenario:
        return False, ["Configuration incomplete"], [], []

    # INDIVIDUAL_RANKING doesn't need tournament_type
    if tournament_format == "HEAD_TO_HEAD" and not tournament_type:
        return False, ["No tournament type selected"], [], []

    scenario_config = SCENARIO_CONFIG[scenario]

    # For INDIVIDUAL_RANKING, use generic type_config with min_players=2
    if tournament_format == "INDIVIDUAL_RANKING" or not tournament_type:
        type_config = {"min_players": 2}
    else:
        type_config = TOURNAMENT_TYPE_CONFIG[tournament_type]

    errors = []
    warnings = []
    info = []

    # Check scenario constraints
    if player_count < scenario_config["min_players"]:
        errors.append(f"Player count ({player_count}) below scenario minimum ({scenario_config['min_players']})")
    elif player_count > scenario_config["max_players"]:
        errors.append(f"Player count ({player_count}) exceeds scenario maximum ({scenario_config['max_players']})")
    else:
        info.append(f"Scenario constraint: {scenario_config['min_players']} ≤ count ≤ {scenario_config['max_players']}")

    # Check tournament type constraints
    type_min = type_config["min_players"]
    type_max = type_config.get("max_players")  # None = no limit
    if player_count < type_min:
        errors.append(f"Player count ({player_count}) below tournament type minimum ({type_min})")
    elif type_max is not None and player_count > type_max:
        _type_label = TOURNAMENT_TYPE_CONFIG.get(tournament_type, {}).get("label", tournament_type)
        errors.append(
            f"Player count ({player_count}) exceeds {_type_label} maximum ({type_max})."
        )
    else:
        constraint_note = f"count ≥ {type_min}" + (f", ≤ {type_max}" if type_max else "")
        info.append(f"Tournament type constraint: {constraint_note}")

    # Tournament-specific validation
    if tournament_type == "group_knockout":
        valid_config = get_group_knockout_config(player_count)
        if valid_config:
            info.append(
                f"Group configuration valid: {valid_config['groups']} groups × "
                f"{valid_config['players_per_group']} players"
            )
        else:
            errors.append(
                f"No valid group configuration for {player_count} players. "
                f"Valid counts: 8, 12, 16, 24, 32, 48, 64, ..."
            )

    # Estimate session count and duration
    if not errors:
        if tournament_format == "INDIVIDUAL_RANKING":
            warnings.append(f"Expected sessions: ~{player_count} (1 per player)")
            warnings.append("Estimated duration: depends on scoring setup")
        else:
            session_count = estimate_session_count(tournament_type, player_count)
            duration_hours = estimate_duration_hours(tournament_type, player_count)
            warnings.append(f"Expected sessions: ~{session_count} matches")
            warnings.append(f"Estimated duration: ~{duration_hours:.1f} hours")

        if player_count >= _SAFETY_CONFIRMATION_THRESHOLD:
            warnings.append(
                f"LARGE SCALE OPERATION: {player_count} players. "
                f"Safety confirmation will be required."
            )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings, info


def render_step3_player_count():
    """Step 5: Player Selection — target count + optional pinned players + hybrid auto-fill"""
    st.markdown("### Step 5 of 8: Player Selection")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")

    if not scenario or scenario not in SCENARIO_CONFIG:
        st.warning("⚠️ No scenario selected. Returning to Step 1.")
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    if tournament_format == "HEAD_TO_HEAD" and (not tournament_type or tournament_type not in TOURNAMENT_TYPE_CONFIG):
        st.warning("⚠️ No tournament type selected. Returning to Step 3.")
        st.session_state["wizard_current_step"] = 3
        st.rerun()
        return

    scenario_config = SCENARIO_CONFIG[scenario]
    if tournament_format == "INDIVIDUAL_RANKING":
        type_min_players = 2
    else:
        type_min_players = TOURNAMENT_TYPE_CONFIG[tournament_type]["min_players"]

    min_players = max(scenario_config["min_players"], type_min_players)
    # Clamp slider upper bound to tournament type's max_players when set
    type_max_players = TOURNAMENT_TYPE_CONFIG.get(tournament_type or "", {}).get("max_players")
    if type_max_players is not None:
        max_players = min(scenario_config["max_players"], type_max_players)
    else:
        max_players = scenario_config["max_players"]
    default_players = scenario_config["default_player_count"]

    # Guard: incompatible scenario × tournament type combination
    if min_players > max_players:
        st.error(
            f"❌ Incompatible combination: scenario minimum ({min_players}) exceeds "
            f"{TOURNAMENT_TYPE_CONFIG.get(tournament_type, {}).get('label', tournament_type)} "
            f"maximum ({type_max_players}). Go back and choose a compatible tournament type."
        )
        if st.button("← Back", key="step4_incompatible_back"):
            st.session_state["wizard_current_step"] = 3
            st.rerun()
        return

    token = st.session_state.get("token", "")

    # ── Target count slider (always visible) ─────────────────────────────────
    _saved_count = st.session_state.get("wizard_player_count_saved", max(min_players, default_players))
    default_value = max(min_players, min(max_players, _saved_count))

    target_count = st.slider(
        "Target player count",
        min_value=min_players,
        max_value=max_players,
        value=default_value,
        step=2,
        key="wizard_player_count_widget",
        help=f"Total players to enroll ({min_players}–{max_players}). Pinned players are always included; remaining slots auto-filled from seed pool.",
    )

    st.markdown("---")
    st.markdown("#### 📌 Pin specific players *(optional)*")
    st.caption("Pinned players are **guaranteed** to be enrolled. Remaining slots filled automatically from seed pool.")

    # ── Player search & pin ───────────────────────────────────────────────────
    if "wizard_selected_players" not in st.session_state:
        st.session_state["wizard_selected_players"] = {}

    selected: dict = st.session_state["wizard_selected_players"]

    col_q, col_btn = st.columns([4, 1])
    with col_q:
        q = st.text_input(
            "Search",
            placeholder="Name or email — e.g. f1rstteam, john, @lfa-seed",
            key="wizard_player_search_q",
            label_visibility="collapsed",
        )
    with col_btn:
        do_search = st.button("🔍 Search", key="wizard_player_search_btn", use_container_width=True)

    if do_search and q.strip():
        try:
            resp = requests.get(
                f"{API_BASE_URL}/api/v1/users/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": q.strip(), "is_active": "true", "limit": 30},
                timeout=10,
            )
            if resp.status_code == 200:
                st.session_state["wizard_player_search_results"] = resp.json()
            else:
                st.session_state["wizard_player_search_results"] = []
                st.warning(f"Search failed: HTTP {resp.status_code}")
        except Exception as exc:
            st.session_state["wizard_player_search_results"] = []
            st.error(f"Search error: {exc}")

    results: list = st.session_state.get("wizard_player_search_results", [])
    if results:
        st.caption(f"{len(results)} result(s) — ➕ pin to guarantee enrollment")
        for u in results:
            uid = u.get("id")
            uname = u.get("name", "?")
            uemail = u.get("email", "")
            already = uid in selected
            c_info, c_btn = st.columns([5, 1])
            c_info.caption(f"{'📌' if already else '  '} **{uname}** `{uemail}`  (id={uid})")
            with c_btn:
                if not already:
                    if st.button("➕", key=f"pin_player_{uid}", help=f"Pin {uname}"):
                        selected[uid] = {"id": uid, "name": uname, "email": uemail}
                        st.session_state["wizard_selected_players"] = selected
                        st.rerun()
                else:
                    if st.button("✖", key=f"unpin_r_{uid}", help=f"Unpin {uname}"):
                        selected.pop(uid, None)
                        st.session_state["wizard_selected_players"] = selected
                        st.rerun()

    # ── Pinned players list ───────────────────────────────────────────────────
    n_pinned = len(selected)
    if selected:
        st.markdown(f"**📌 Pinned ({n_pinned}):**")
        for uid, u in list(selected.items()):
            c_name, c_rm = st.columns([5, 1])
            c_name.caption(f"📌 **{u['name']}** `{u['email']}`")
            with c_rm:
                if st.button("✖", key=f"unpin_{uid}", help=f"Unpin {u['name']}"):
                    selected.pop(uid, None)
                    st.session_state["wizard_selected_players"] = selected
                    st.rerun()
        if st.button("🗑 Clear pins", key="clear_all_pins"):
            st.session_state["wizard_selected_players"] = {}
            st.rerun()

    # ── Summary + validation ──────────────────────────────────────────────────
    st.markdown("---")
    auto_fill = target_count - n_pinned

    if n_pinned > target_count:
        st.error(f"❌ Too many pinned players ({n_pinned}) for target {target_count}. Remove {n_pinned - target_count} pin(s) or increase target.")
        is_valid = False
    elif n_pinned == target_count and n_pinned > 0:
        st.success(f"✅ **{n_pinned} manually selected** — no auto-fill needed")
        is_valid = True
    elif n_pinned > 0:
        st.success(f"✅ **{n_pinned} pinned** + **{auto_fill} auto-fill** from seed pool = **{target_count} total**")
        is_valid = True
    else:
        st.info(f"🎲 **{target_count} auto-fill** from seed pool *(no pinned players)*")
        is_valid, errors, warnings, info = validate_step3_detailed()
        if errors:
            for e in errors:
                st.error(f"❌ {e}")
            is_valid = False
        if warnings:
            for w in warnings:
                st.warning(f"⚠️ {w}")

    st.session_state["wizard_step3_valid"] = is_valid
    if is_valid:
        st.session_state["wizard_completed_steps"].add(4)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True, key="step3_back"):
            st.session_state["wizard_current_step"] = 4
            st.rerun()
    with col2:
        if st.button("Next →", disabled=not is_valid, use_container_width=True, key="step3_next"):
            st.session_state["wizard_player_count_saved"] = target_count
            pinned_ids = [u["id"] for u in selected.values()] if selected else None
            st.session_state["wizard_player_ids_saved"] = pinned_ids
            st.session_state["wizard_current_step"] = 6
            st.rerun()
