"""
Admin Dashboard — Game Presets Tab
====================================
Full CRUD interface for game presets.
Presets declared here become selectable in the OPS Wizard (Step 4).

Endpoint map:
  GET    /api/v1/game-presets/             — list all presets
  GET    /api/v1/game-presets/{id}         — get full detail
  POST   /api/v1/game-presets/             — create
  PATCH  /api/v1/game-presets/{id}         — update
  DELETE /api/v1/game-presets/{id}         — delete
"""

import re
import sys
from pathlib import Path
import requests
import streamlit as st
from config import API_BASE_URL, API_TIMEOUT

# Make the project root importable so we can reach app.skills_config
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.skills_config import SKILL_CATEGORIES  # noqa: E402


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _extract_error(r) -> str:
    """Extract a human-readable error string from an API response."""
    if r.status_code == 401:
        return "SESSION_EXPIRED"
    try:
        body = r.json()
        # Custom error envelope: {"error": {"message": "..."}}
        if "error" in body:
            return body["error"].get("message", str(body))
        # FastAPI default: {"detail": "..."}
        return str(body.get("detail", r.text))
    except Exception:
        return r.text


def _list_presets(token: str) -> list:
    try:
        r = requests.get(
            f"{API_BASE_URL}/api/v1/game-presets/",
            headers=_headers(token),
            params={"active_only": "false"},
            timeout=API_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("presets", data) if isinstance(data, dict) else data
    except Exception:
        pass
    return []


def _get_preset(token: str, preset_id: int) -> dict:
    try:
        r = requests.get(
            f"{API_BASE_URL}/api/v1/game-presets/{preset_id}",
            headers=_headers(token),
            timeout=API_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def _create_preset(token: str, payload: dict) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_BASE_URL}/api/v1/game-presets/",
            headers=_headers(token),
            json=payload,
            timeout=API_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return True, ""
        return False, _extract_error(r)
    except Exception as e:
        return False, str(e)


def _update_preset(token: str, preset_id: int, payload: dict) -> tuple[bool, str]:
    try:
        r = requests.patch(
            f"{API_BASE_URL}/api/v1/game-presets/{preset_id}",
            headers=_headers(token),
            json=payload,
            timeout=API_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return True, ""
        return False, _extract_error(r)
    except Exception as e:
        return False, str(e)


def _delete_preset(token: str, preset_id: int) -> tuple[bool, str]:
    try:
        r = requests.delete(
            f"{API_BASE_URL}/api/v1/game-presets/{preset_id}",
            headers=_headers(token),
            timeout=API_TIMEOUT,
        )
        if r.status_code in (200, 204):
            return True, ""
        return False, _extract_error(r)
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_code(name: str) -> str:
    """Convert display name to a valid code (lowercase, underscores)."""
    code = name.lower().strip()
    code = re.sub(r"[^a-z0-9]+", "_", code)
    code = code.strip("_")
    return code[:50] or "preset"


def _fractional_to_pct(fractional_weights: dict[str, float]) -> dict[str, int]:
    """
    Convert stored fractional skill_weights (sum ≈ 1.0) to integer percentages
    summing to exactly 100.

    Used in edit mode to re-display stored weights back as % inputs.
    Largest skill absorbs any rounding residual so the sum is always 100.
    """
    if not fractional_weights:
        return {}
    pcts = {k: max(1, round(v * 100)) for k, v in fractional_weights.items()}
    diff = 100 - sum(pcts.values())
    if diff != 0:
        # Absorb rounding residual into the skill with the largest fraction
        largest = max(pcts, key=lambda k: fractional_weights.get(k, 0))
        pcts[largest] = max(1, pcts[largest] + diff)
    return pcts


def _build_game_config(
    skills: list[str],
    weights_raw: dict[str, int | float],
    category: str,
    difficulty: str,
    min_players: int,
    skill_impact: bool,
) -> dict:
    """
    Assemble the game_config JSONB structure required by the API.

    weights_raw: integer % values per skill (e.g. {passing: 40, dribbling: 35, finishing: 25}).
    Normalisation (÷ sum) converts them to fractional skill_weights (e.g. 0.40, 0.35, 0.25).
    This normalisation acts as a safety net — when the UI enforces sum=100%, dividing by 100
    is equivalent.
    """
    total = sum(weights_raw.get(s, 1) for s in skills) or 1
    skill_weights = {s: round(weights_raw.get(s, 1) / total, 4) for s in skills}

    cfg = {
        "version": "1.0",
        "format_config": {},
        "skill_config": {
            "skills_tested": skills,
            "skill_weights": skill_weights,
            "skill_impact_on_matches": skill_impact,
        },
        "simulation_config": {},
        "metadata": {
            "game_category": category or None,
            "difficulty_level": difficulty or None,
            "min_players": min_players or None,
        },
    }
    return cfg


# ---------------------------------------------------------------------------
# Sub-renderers
# ---------------------------------------------------------------------------

_DIFFICULTY_OPTIONS = ["", "Beginner", "Intermediate", "Advanced", "Expert"]

# Derive skill catalogue directly from the canonical backend config.
# This guarantees the form always mirrors the skills the tournament engine
# actually tracks on player profiles — no manual sync needed.
#
# Structure built from SKILL_CATEGORIES (app/skills_config.py):
#   _SKILL_GROUPS_ORDERED : {"{emoji} {name_en}": [skill_key, ...]}  — for the checkbox grid
#   _SKILL_DISPLAY_EN     : {skill_key: name_en}                     — for human-readable labels
#   _KNOWN_SKILLS         : [skill_key, ...]                         — flat list for exclusion logic

_SKILL_GROUPS_ORDERED: dict[str, list[str]] = {}
_SKILL_DISPLAY_EN: dict[str, str] = {}

for _cat in SKILL_CATEGORIES:
    _label = f"{_cat['emoji']} {_cat['name_en']}"
    _SKILL_GROUPS_ORDERED[_label] = [s["key"] for s in _cat["skills"]]
    for _s in _cat["skills"]:
        _SKILL_DISPLAY_EN[_s["key"]] = _s["name_en"]

_KNOWN_SKILLS: list[str] = [k for keys in _SKILL_GROUPS_ORDERED.values() for k in keys]

_MAX_CB_COLS = 5  # max checkbox columns per row within a skill group


def _render_preset_form(
    token: str,
    form_key: str,
    preset_data: dict | None = None,
) -> None:
    """
    Render a create-or-edit form WITHOUT st.form wrapper.

    Removing st.form allows Streamlit to rerun on every widget interaction,
    so weight sliders appear immediately as the user types skill names —
    both in create mode (blank form) and edit mode (pre-filled).

    preset_data=None  → create mode
    preset_data=dict  → edit mode (pre-filled)
    """
    editing = preset_data is not None
    gc = (preset_data.get("game_config") or {}) if editing else {}
    sc = gc.get("skill_config", {})
    meta = gc.get("metadata", {})

    initial_name       = preset_data.get("name", "") if editing else ""
    initial_desc       = preset_data.get("description", "") if editing else ""
    initial_skills     = list(sc.get("skills_tested") or [])
    # Stored as fractional (0.0–1.0); rescale to integer % for the UI
    initial_weights_pct: dict[str, int] = _fractional_to_pct(sc.get("skill_weights") or {})
    initial_category   = meta.get("game_category") or ""
    initial_difficulty = meta.get("difficulty_level") or ""
    initial_min        = meta.get("min_players") or 4
    initial_impact     = sc.get("skill_impact_on_matches", True)

    # ── Name + Code ───────────────────────────────────────────────────────────
    col_name, col_code = st.columns([3, 2])
    with col_name:
        name = st.text_input(
            "Name *",
            value=initial_name,
            placeholder="e.g. Footvolley Sprint",
            key=f"{form_key}_name",
        )

    with col_code:
        if editing:
            # Code is immutable after creation — show for reference only
            st.text_input(
                "Code",
                value=preset_data.get("code", ""),
                disabled=True,
                key=f"{form_key}_code_display",
                help="Code cannot be changed after creation.",
            )
            code = preset_data.get("code", "")
        else:
            # Auto-fill code from name; update while user hasn't diverged
            auto_code = _to_code(name) if name else ""
            _ck = f"{form_key}_code"
            _pk = f"{form_key}_prev_auto"
            prev_auto = st.session_state.get(_pk, None)
            stored   = st.session_state.get(_ck, "")
            if prev_auto is None or stored == prev_auto:
                st.session_state[_ck] = auto_code
            st.session_state[_pk] = auto_code
            code = st.text_input(
                "Code *",
                key=_ck,
                help="Auto-filled from name. Edit freely — lowercase, digits, underscores.",
            )

    # ── Description ───────────────────────────────────────────────────────────
    description = st.text_area(
        "Description",
        value=initial_desc,
        height=68,
        key=f"{form_key}_desc",
    )

    # ── Skills selection — grouped checkboxes ────────────────────────────────
    # Source of truth: SKILL_CATEGORIES from app/skills_config.py (29 skills).
    # Each checkbox tick triggers an immediate Streamlit rerun — weight inputs
    # appear/disappear instantly, no keyboard shortcut required.
    st.markdown("**Skills tested** — check each skill to include")

    skills_from_checkboxes: list[str] = []
    for group_label, group_skills in _SKILL_GROUPS_ORDERED.items():
        st.caption(group_label)
        # Render in rows of at most _MAX_CB_COLS to keep columns readable
        for row_start in range(0, len(group_skills), _MAX_CB_COLS):
            row = group_skills[row_start : row_start + _MAX_CB_COLS]
            gcols = st.columns(_MAX_CB_COLS)
            for j, skill in enumerate(row):
                display = _SKILL_DISPLAY_EN.get(skill, skill.replace("_", " ").title())
                if gcols[j].checkbox(
                    display,
                    value=(skill in initial_skills),
                    key=f"{form_key}_cb_{skill}",
                ):
                    skills_from_checkboxes.append(skill)

    # Optional free-text area for non-standard skills (also used by E2E tests
    # via Ctrl+Enter to trigger the Streamlit rerun)
    _custom_defaults = [s for s in initial_skills if s not in _KNOWN_SKILLS]
    custom_text = st.text_area(
        "Custom skills (one per line, optional)",
        value="\n".join(_custom_defaults),
        height=56,
        key=f"{form_key}_skills_custom",
        help="Skills not in the standard list above. Use lowercase_underscore. Press ⌘+Enter to apply.",
    )
    skills_from_custom: list[str] = [
        s.strip().lower().replace(" ", "_")
        for s in custom_text.splitlines()
        if s.strip()
    ]

    # Deduplicated union: checkbox order first, then custom additions
    skills: list[str] = list(dict.fromkeys(skills_from_checkboxes + skills_from_custom))

    # ── Skill weights — direct % input, must sum to 100% ─────────────────────
    # Each selected skill gets an integer % spinbutton (1–99).
    # The live sum counter turns green at exactly 100% and red otherwise.
    # The Save button is disabled until the sum reaches 100%.
    weights: dict[str, int] = {}
    if skills:
        st.markdown("**Skill weights (%)** — assign a percentage to each skill; must sum to **100%**")
        wcols = st.columns(min(len(skills), 4))
        for i, skill in enumerate(skills):
            # Edit mode: rescale stored fractional → int %
            # Create mode / new skill: default 10% per new tick
            default_pct: int = initial_weights_pct.get(skill, 10)
            _display = _SKILL_DISPLAY_EN.get(skill, skill.replace("_", " ").title())
            weights[skill] = wcols[i % 4].number_input(
                f"{_display} %",
                min_value=1,
                max_value=100,
                value=default_pct,
                step=1,
                key=f"{form_key}_w_{skill}",
            )

        # ── Live sum indicator + dominant skill badge ─────────────────────────
        weight_sum: int = sum(weights.values())
        sum_valid: bool = weight_sum == 100
        if sum_valid:
            st.success(f"✅ Sum: **{weight_sum}%** — ready to save")
            # Dominant skill badge (only meaningful when sum is valid)
            if len(weights) > 1:
                _dom_key = max(weights, key=lambda k: weights[k])
                _dom_display = _SKILL_DISPLAY_EN.get(
                    _dom_key, _dom_key.replace("_", " ").title()
                )
                st.caption(f"Dominant skill: **{_dom_display}** ({weights[_dom_key]}%)")
        else:
            _diff = weight_sum - 100
            _sign = "+" if _diff > 0 else ""
            st.error(
                f"❌ Sum: **{weight_sum}%** ({_sign}{_diff}%) — "
                "must be exactly 100%.  Save is disabled until corrected."
            )
    else:
        weight_sum = 0
        sum_valid = False
        st.caption("☝️ Tick skills above — weight inputs appear here automatically.")

    # ── Metadata ──────────────────────────────────────────────────────────────
    st.markdown("**Metadata (optional)**")
    col_cat, col_diff = st.columns(2)
    with col_cat:
        category = st.text_input(
            "Category",
            value=initial_category,
            placeholder="e.g. Football",
            key=f"{form_key}_category",
        )
    with col_diff:
        diff_idx = (
            _DIFFICULTY_OPTIONS.index(initial_difficulty)
            if initial_difficulty in _DIFFICULTY_OPTIONS else 0
        )
        difficulty = st.selectbox(
            "Difficulty",
            _DIFFICULTY_OPTIONS,
            index=diff_idx,
            key=f"{form_key}_difficulty",
        )

    col_min, col_impact = st.columns([1, 2])
    with col_min:
        min_players = st.number_input(
            "Min players",
            min_value=2, max_value=1024,
            value=int(initial_min), step=1,
            key=f"{form_key}_min_players",
            help="Minimum recommended player count for this preset. Tournament size is set separately.",
        )
    with col_impact:
        skill_impact = st.checkbox(
            "Skill impact on matches",
            value=initial_impact,
            key=f"{form_key}_skill_impact",
        )

    # ── Submit ────────────────────────────────────────────────────────────────
    st.divider()
    submit_label = "💾 Save changes" if editing else "➕ Create preset"
    # Disable save when: no skills selected, OR sum ≠ 100%
    _save_disabled = (not skills) or (not sum_valid)
    submitted = st.button(
        submit_label,
        type="primary",
        use_container_width=True,
        key=f"{form_key}_submit",
        disabled=_save_disabled,
    )

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Name is required.")
        if not editing:
            if not code.strip():
                errors.append("Code is required.")
            elif not re.match(r"^[a-z0-9_]+$", code):
                errors.append("Code must be lowercase letters, digits, and underscores only.")
        if not skills:
            errors.append("At least one skill must be defined.")
        if skills and sum(weights.values()) != 100:
            errors.append(
                f"Skill weights must sum to 100% (current: {sum(weights.values())}%). "
                "Adjust the percentages above."
            )

        if errors:
            for e in errors:
                st.error(e)
            return

        game_config = _build_game_config(
            skills=skills,
            weights_raw=weights,
            category=category,
            difficulty=difficulty,
            min_players=min_players,
            skill_impact=skill_impact,
        )

        if editing:
            ok, err = _update_preset(token, preset_data["id"], {
                "name": name.strip(),
                "description": description.strip() or None,
                "game_config": game_config,
            })
            if ok:
                st.success(f"Preset **{name}** updated.")
                st.cache_data.clear()
                del st.session_state["_gp_edit_id"]
                st.rerun()
            else:
                _show_error(f"Update failed: {err}")
        else:
            ok, err = _create_preset(token, {
                "code": code.strip(),
                "name": name.strip(),
                "description": description.strip() or None,
                "game_config": game_config,
                "is_active": True,
            })
            if ok:
                st.success(f"Preset **{name}** created.")
                st.cache_data.clear()
                st.session_state["_gp_show_create"] = False
                # Wipe form session-state so the next create starts fresh
                for k in list(st.session_state.keys()):
                    if k.startswith(form_key + "_"):
                        del st.session_state[k]
                st.rerun()
            else:
                _show_error(f"Create failed: {err}")


def _show_error(err: str) -> None:
    """Display an error, with special handling for session expiry."""
    if err == "SESSION_EXPIRED":
        st.error("Session expired. Please refresh the page and log in again.")
    else:
        st.error(err)


def _render_preset_list(token: str, presets: list) -> None:
    """Render the table of existing presets with actions."""
    if not presets:
        st.info("No game presets found. Create the first one below.")
        return

    for p in presets:
        pid = p["id"]
        is_active = p.get("is_active", True)
        status_icon = "🟢" if is_active else "⚫"
        rec_icon = "⭐ " if p.get("is_recommended") else ""
        locked = p.get("is_locked", False)

        skills: list = p.get("skills_tested") or []
        skill_weights: dict = (
            p.get("game_config", {}).get("skill_config", {}).get("skill_weights", {})
        )

        # Build "Skill Name 60% · Other Skill 25% · ..." string when weights exist
        if skill_weights:
            total_w = sum(skill_weights.values()) or 1.0
            skills_str = "  ·  ".join(
                f"{s.replace('_', ' ').title()} {round(skill_weights.get(s, 0) / total_w * 100)}%"
                for s in skills
                if s in skill_weights
            ) or "—"
        else:
            skills_str = ", ".join(s.replace("_", " ").title() for s in skills) if skills else "—"

        with st.expander(
            f"{status_icon} {rec_icon}**{p['name']}**  ·  `{p['code']}`  ·  {len(skills)} skills",
            expanded=False,
        ):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                if p.get("description"):
                    st.caption(p["description"])
                st.markdown(f"**Skills:** {skills_str}")
                meta_parts = []
                if p.get("game_category"):
                    meta_parts.append(f"🎮 {p['game_category']}")
                if p.get("difficulty_level"):
                    meta_parts.append(f"📶 {p['difficulty_level']}")
                if p.get("min_players"):
                    meta_parts.append(f"👥 min {p['min_players']} players")
                if meta_parts:
                    st.caption("  ·  ".join(meta_parts))
                st.caption(f"id={pid}  ·  code={p['code']}")

            with col_actions:
                if not locked:
                    if st.button("✏️ Edit", key=f"edit_{pid}", use_container_width=True):
                        st.session_state["_gp_edit_id"] = pid
                        st.session_state["_gp_show_create"] = False
                        st.rerun()

                # Toggle active/inactive
                toggle_label = "⚫ Deactivate" if is_active else "🟢 Activate"
                if st.button(toggle_label, key=f"toggle_{pid}", use_container_width=True):
                    ok, err = _update_preset(token, pid, {"is_active": not is_active})
                    if ok:
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        _show_error(err)

                if not locked:
                    if st.button("🗑️ Delete", key=f"del_{pid}", use_container_width=True,
                                 type="secondary"):
                        st.session_state[f"_gp_confirm_del_{pid}"] = True
                        st.rerun()

            # Delete confirmation
            if st.session_state.get(f"_gp_confirm_del_{pid}"):
                st.warning(f"Delete **{p['name']}**? This cannot be undone.")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Yes, delete", key=f"del_confirm_{pid}", type="primary"):
                        ok, err = _delete_preset(token, pid)
                        if ok:
                            st.success("Deleted.")
                            st.cache_data.clear()
                            del st.session_state[f"_gp_confirm_del_{pid}"]
                            st.rerun()
                        else:
                            _show_error(err)
                with dc2:
                    if st.button("Cancel", key=f"del_cancel_{pid}"):
                        del st.session_state[f"_gp_confirm_del_{pid}"]
                        st.rerun()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_game_presets_tab(token: str, user: dict) -> None:
    """Render the Game Presets admin tab."""
    st.header("🎮 Game Presets")
    st.caption(
        "Declare game presets here. Each preset defines which skills a tournament will develop "
        "and their relative weights. Presets are selectable in the OPS Wizard (Step 4)."
    )
    st.divider()

    # Load presets (fresh on each render — no caching at this level)
    presets = _list_presets(token)
    active_count = sum(1 for p in presets if p.get("is_active", True))
    st.caption(f"{len(presets)} presets total  ·  {active_count} active")

    # ── Edit mode ────────────────────────────────────────────────────────────
    edit_id = st.session_state.get("_gp_edit_id")
    if edit_id is not None:
        detail = _get_preset(token, edit_id)
        if detail:
            st.subheader(f"Edit: {detail.get('name', edit_id)}")
            if st.button("← Cancel edit", key="cancel_edit"):
                del st.session_state["_gp_edit_id"]
                st.rerun()
            _render_preset_form(token, form_key=f"edit_form_{edit_id}", preset_data=detail)
            return
        else:
            st.error(f"Could not load preset id={edit_id}.")
            del st.session_state["_gp_edit_id"]

    # ── Existing presets ──────────────────────────────────────────────────────
    _render_preset_list(token, presets)

    st.divider()

    # ── Create new preset ────────────────────────────────────────────────────
    show_create = st.session_state.get("_gp_show_create", False)
    create_btn_label = "✕ Cancel" if show_create else "➕ New Game Preset"
    if st.button(create_btn_label, key="toggle_create", type="primary" if not show_create else "secondary"):
        st.session_state["_gp_show_create"] = not show_create
        st.rerun()

    if show_create:
        st.subheader("Create New Game Preset")
        _render_preset_form(token, form_key="create_form")
