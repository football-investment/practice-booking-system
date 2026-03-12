"""
Tournament Result Entry Component

Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
Provides manual result submission interface for pending H2H sessions.
"""

from typing import Any, Dict, List, Optional
import streamlit as st
import requests

# Import API helpers
import sys
from pathlib import Path
# Add parent directory to path to import api_helpers_monitor
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from api_helpers_monitor import submit_h2h_result, submit_individual_ranking_results, submit_ir_round
from config import API_BASE_URL

# Import shared utilities
from .utils import phase_icon as _phase_icon, phase_label_short as _phase_label_short, phase_label as _phase_label
from .session_grid import build_campus_field_map


# ─── Main Component ──────────────────────────────────────────────────────────

def _render_individual_ranking_entry(token: str, tid: int, sessions: List[Dict[str, Any]]) -> None:
    """Result entry panel for pending INDIVIDUAL_RANKING sessions.

    Handles two sub-types:
    - Single-round (scoring_type != ROUNDS_BASED): one bulk submission per session
    - Multi-round (scoring_type == ROUNDS_BASED): per-round submission, form stays
      open until all rounds are complete (completed_rounds >= total_rounds)
    """
    import random as _random

    pending_ir = [
        s for s in sessions
        if not s.get("result_submitted")
        and s.get("match_format") == "INDIVIDUAL_RANKING"
    ]
    if not pending_ir:
        return

    for s in pending_ir:
        p_ids = s.get("participant_user_ids") or []
        names = s.get("participant_names") or []
        raw_scoring = s.get("scoring_type") or "SCORE_BASED"
        is_rounds_based = raw_scoring == "ROUNDS_BASED"

        sid = s.get("id")

        # Unwrap ROUNDS_BASED → underlying measurement type for unit labels
        if is_rounds_based:
            scoring = (s.get("structure_config") or {}).get("scoring_method")
            if not scoring:
                st.warning(f"⚠️ Session #{sid} missing scoring_method in structure_config. Cannot enter results.")
                continue
        else:
            scoring = raw_scoring

        # Round progress from rounds_data
        rd = s.get("rounds_data") or {}
        if is_rounds_based:
            total_rounds = int(rd.get("total_rounds", 0))
            if total_rounds < 1:
                st.warning(f"⚠️ Session #{sid} has missing or invalid rounds_data. Cannot enter results.")
                continue
        else:
            total_rounds = 1
        completed_rounds = int(rd.get("completed_rounds", 0)) if is_rounds_based else 0
        next_round = completed_rounds + 1

        # Unit / range for numeric inputs
        if "TIME" in scoring:
            unit, min_v, max_v, step = "seconds", 0.0, 120.0, 0.1
            _sim_min = 5.0
        elif "DISTANCE" in scoring:
            unit, min_v, max_v, step = "meters", 0.0, 200.0, 0.1
            _sim_min = 1.0
        else:
            unit, min_v, max_v, step = "score", 0.0, 100.0, 1.0
            _sim_min = 0.0

        # Expander title
        if is_rounds_based:
            expander_title = (
                f"📝 Individual Ranking — Session #{sid} · {len(p_ids)} players · "
                f"{scoring} · Round {next_round}/{total_rounds}"
            )
        else:
            expander_title = (
                f"📝 Individual Ranking — Session #{sid} · {len(p_ids)} players · {scoring}"
            )

        with st.expander(expander_title, expanded=True):

            # ── Round progress bar (multi-round only) ────────────────────────
            if is_rounds_based:
                st.progress(completed_rounds / total_rounds,
                            text=f"Rounds completed: {completed_rounds} / {total_rounds}")

            col_sim, col_fill = st.columns(2)

            # ⚡ Simulate button label differs for multi-round
            sim_label = (
                f"⚡ Simulate Round {next_round} ({len(p_ids)} players)"
                if is_rounds_based
                else f"⚡ Simulate All ({len(p_ids)} players)"
            )

            with col_sim:
                if st.button(
                    sim_label,
                    key=f"sim_ir_{sid}_{next_round}",
                    type="primary",
                    use_container_width=True,
                ):
                    import random as _r
                    if is_rounds_based:
                        # Submit this single round via round endpoint
                        round_results = {
                            str(uid): str(round(_r.uniform(_sim_min, max_v), 2))
                            for uid in p_ids
                        }
                        ok, err, _ = submit_ir_round(token, tid, sid, next_round, round_results)
                        if ok:
                            new_completed = completed_rounds + 1
                            st.toast(
                                f"✅ Round {next_round}/{total_rounds} submitted!"
                                + (" — All rounds done!" if new_completed >= total_rounds else ""),
                                icon="🏃",
                            )
                            st.rerun()
                        else:
                            st.error(f"Failed: {err}")
                    else:
                        # Single-round: bulk submit
                        results = [
                            {"user_id": uid, "measured_value": round(_r.uniform(_sim_min, max_v), 2)}
                            for uid in p_ids
                        ]
                        ok, err, _ = submit_individual_ranking_results(token, tid, sid, results)
                        if ok:
                            st.toast(f"✅ {len(p_ids)} results submitted!", icon="🏃")
                            st.rerun()
                        else:
                            st.error(f"Failed: {err}")

            # ⚡ Simulate All Rounds — multi-round only (submits every remaining round at once)
            if is_rounds_based and completed_rounds < total_rounds:
                with col_fill:
                    remaining = total_rounds - completed_rounds
                    if st.button(
                        f"⚡ Simulate All {remaining} remaining rounds",
                        key=f"sim_ir_all_{sid}",
                        use_container_width=True,
                        help="Submit all remaining rounds with random values",
                    ):
                        import random as _r
                        fail_count = 0
                        for rn in range(next_round, total_rounds + 1):
                            round_results = {
                                str(uid): str(round(_r.uniform(_sim_min, max_v), 2))
                                for uid in p_ids
                            }
                            ok, err, _ = submit_ir_round(token, tid, sid, rn, round_results)
                            if not ok:
                                fail_count += 1
                        if fail_count == 0:
                            st.toast(f"✅ All {remaining} rounds submitted!", icon="🏃")
                        else:
                            st.toast(f"⚠️ {fail_count} rounds failed", icon="⚠️")
                        st.rerun()
            elif not is_rounds_based:
                # Auto-fill for single-round
                with col_fill:
                    if st.button(
                        "🎲 Auto-fill",
                        key=f"autofill_ir_{sid}",
                        use_container_width=True,
                        help="Fill fields with random values — review before submitting",
                    ):
                        import random as _r
                        shown_ids = [uid for uid, _ in (list(zip(p_ids, names))[:8] if names else list(zip(p_ids, p_ids))[:8])]
                        for uid in shown_ids:
                            if "TIME" in scoring or "DISTANCE" in scoring:
                                st.session_state[f"ir_{sid}_{uid}"] = round(_r.uniform(_sim_min, max_v), 2)
                            else:
                                st.session_state[f"ir_{sid}_{uid}"] = float(_r.randint(0, int(max_v)))
                        st.rerun()

            # Per-player inputs (show first 8 to keep UI manageable)
            shown = list(zip(p_ids, names))[:8] if names else list(zip(p_ids, p_ids))[:8]
            cols_data = {}
            for uid, name in shown:
                display = name.split()[-1] if isinstance(name, str) else f"P{uid}"
                val = st.number_input(
                    f"{display} ({unit})",
                    min_value=float(min_v), max_value=float(max_v),
                    value=0.0, step=float(step),
                    key=f"ir_{sid}_{uid}",
                )
                cols_data[uid] = val

            if len(p_ids) > 8:
                st.caption(f"Showing first 8 of {len(p_ids)} players. Use ⚡ Simulate to bulk-submit all.")

            # Submit button label and action differ per mode
            if is_rounds_based:
                submit_label = f"⚽ Submit Round {next_round}"
            else:
                submit_label = "⚽ Submit entries"

            if st.button(submit_label, key=f"submit_ir_{sid}", use_container_width=False):
                if is_rounds_based:
                    round_results = {
                        str(uid): str(v) for uid, v in cols_data.items()
                    }
                    ok, err, _ = submit_ir_round(token, tid, sid, next_round, round_results)
                    if ok:
                        new_completed = completed_rounds + 1
                        st.toast(
                            f"✅ Round {next_round}/{total_rounds} saved!"
                            + (" — All rounds complete!" if new_completed >= total_rounds else ""),
                            icon="🏃",
                        )
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
                else:
                    results = [{"user_id": uid, "measured_value": v} for uid, v in cols_data.items()]
                    ok, err, _ = submit_individual_ranking_results(token, tid, sid, results)
                    if ok:
                        st.toast("✅ Results submitted!", icon="🏃")
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")


def _render_field_round_form(
    token: str,
    tid: int,
    field_num: int,
    field_sessions: List[Dict[str, Any]],
    campus_name: str,
) -> None:
    """Render the next pending round as a dedicated st.form for one field.

    Implements "1 round = 1 form" requirement:
    - Shows only the next incomplete round for this field.
    - Each match in that round gets its own score row inside the form.
    - Two submit buttons: manual entry (⚽ Submit) and simulation (⚡ Simulate).
    - After submission the form closes and the next round becomes active.
    """
    import random as _random

    done = sum(1 for s in field_sessions if s.get("result_submitted"))
    total = len(field_sessions)

    if done == total:
        st.success(f"✅ Field {field_num} — all {total} matches complete")
        return

    # All rounds for this field, in order
    all_rounds = sorted({s.get("tournament_round") or 1 for s in field_sessions})

    # Find incomplete rounds
    incomplete_rounds = [
        rn for rn in all_rounds
        if any(
            not s.get("result_submitted")
            for s in field_sessions
            if (s.get("tournament_round") or 1) == rn
        )
    ]
    done_rounds = len(all_rounds) - len(incomplete_rounds)

    # Progress
    pct = done / total if total else 0
    st.progress(
        pct,
        text=f"{done}/{total} matches · {done_rounds}/{len(all_rounds)} rounds done",
    )

    if not incomplete_rounds:
        st.success("✅ All rounds complete for this field")
        return

    next_round = incomplete_rounds[0]
    round_sessions = [
        s for s in field_sessions
        if (s.get("tournament_round") or 1) == next_round
        and not s.get("result_submitted")
        and len(s.get("participant_user_ids") or []) == 2
    ]

    if not round_sessions:
        st.caption(f"Round {next_round}: no pending H2H matches.")
        return

    st.caption(
        f"**Round {next_round} / {len(all_rounds)}** — "
        f"{len(round_sessions)} match(es) · "
        f"{len(incomplete_rounds) - 1} round(s) remaining after this"
    )

    # One st.form per field-round
    form_key = f"field_round_{tid}_{campus_name}_{field_num}_{next_round}"

    match_scores: Dict[int, tuple] = {}  # sid → (uid0, sc0, uid1, sc1)

    with st.form(key=form_key):
        for s in round_sessions:
            p_ids = s.get("participant_user_ids") or []
            names = s.get("participant_names") or []
            sid = s.get("id")
            name0 = (names[0].split()[-1] if names else f"P{p_ids[0]}")
            name1 = (names[1].split()[-1] if len(names) > 1 else f"P{p_ids[1]}")

            c_info, c0, c_vs, c1 = st.columns([2, 2, 1, 2])
            c_info.caption(f"#{sid}")
            sc0 = c0.number_input(
                name0, min_value=0, max_value=99, value=0,
                key=f"fr_{tid}_{field_num}_{next_round}_{sid}_0",
                label_visibility="visible",
            )
            c_vs.markdown(
                "<div style='text-align:center;padding-top:26px;color:#6b7280'>vs</div>",
                unsafe_allow_html=True,
            )
            sc1 = c1.number_input(
                name1, min_value=0, max_value=99, value=0,
                key=f"fr_{tid}_{field_num}_{next_round}_{sid}_1",
                label_visibility="visible",
            )
            match_scores[sid] = (p_ids[0], sc0, p_ids[1], sc1)

        col_submit, col_sim = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button(
                f"⚽ Submit Round {next_round}",
                type="primary",
                use_container_width=True,
            )
        with col_sim:
            simulated = st.form_submit_button(
                f"⚡ Simulate Round {next_round}",
                use_container_width=True,
            )

    if submitted or simulated:
        ok_count = fail_count = 0
        for sid, (uid0, sc0, uid1, sc1) in match_scores.items():
            if simulated:
                sc0 = _random.randint(0, 5)
                sc1 = _random.randint(0, 5)
            ok, _err, _ = submit_h2h_result(token, sid, uid0, sc0, uid1, sc1)
            if ok:
                ok_count += 1
            else:
                fail_count += 1

        if fail_count == 0:
            st.toast(
                f"✅ Field {field_num} · Round {next_round}: {ok_count} match(es) done!",
                icon="⚽",
            )
        else:
            st.toast(f"⚠️ {ok_count} OK, {fail_count} failed", icon="⚠️")
        st.rerun()


def _render_campus_field_h2h_entry(
    token: str,
    tid: int,
    sessions: List[Dict[str, Any]],
    campus_configs: List[Dict[str, Any]],
    *,
    campus_filter: Optional[str] = None,
    field_filter: Optional[int] = None,
) -> None:
    """H2H result entry organised as Campus → Field → Round form.

    Each field shows a dedicated per-round form (1 round = 1 form).
    Admin sees all campuses and fields.
    Instructor sees only their assigned campus + field (RBAC).
    """
    _ENTRY_CAMPUS_CSS = (
        "background:linear-gradient(135deg,#1e3a5f,#2563eb);"
        "color:#fff;padding:10px 16px;border-radius:8px 8px 0 0;"
        "font-weight:600;font-size:1rem;margin-bottom:2px;"
    )

    # Build campus/field map over ALL sessions (not just pending) for correct counts
    campus_map = build_campus_field_map(sessions, campus_configs)

    if not campus_map:
        return

    # Apply RBAC campus filter
    if campus_filter is not None:
        campus_map = {k: v for k, v in campus_map.items() if k == campus_filter}

    if not campus_map:
        st.warning("No sessions found for your assigned campus.")
        return

    for campus_name, campus_data in campus_map.items():
        fields_dict = dict(campus_data["fields"])

        # Apply RBAC field filter
        if field_filter is not None:
            fields_dict = {k: v for k, v in fields_dict.items() if k == field_filter}

        # Exclude pseudo-field 0 (sessions without a field_number)
        fields_dict = {k: v for k, v in fields_dict.items() if k > 0}

        if not fields_dict:
            continue

        campus_total = sum(len(v) for v in fields_dict.values())
        campus_done = sum(
            sum(1 for s in v if s.get("result_submitted"))
            for v in fields_dict.values()
        )

        # Campus header
        st.markdown(
            f"<div style='{_ENTRY_CAMPUS_CSS}'>"
            f"🏟️ {campus_name}"
            f"<span style='font-weight:400;font-size:.85em;margin-left:16px;opacity:.9'>"
            f"{campus_done}/{campus_total} matches complete"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        with st.container():
            for field_num in sorted(fields_dict.keys()):
                field_all = fields_dict[field_num]
                fn_done = sum(1 for s in field_all if s.get("result_submitted"))
                fn_total = len(field_all)
                fn_pending_h2h = [
                    s for s in field_all
                    if not s.get("result_submitted")
                    and len(s.get("participant_user_ids") or []) == 2
                ]
                fn_icon = "✅" if fn_done == fn_total else "⏳"

                with st.expander(
                    f"{fn_icon} **Field {field_num}** — {fn_done}/{fn_total}",
                    expanded=(fn_pending_h2h != []),
                ):
                    _render_field_round_form(
                        token, tid, field_num, field_all, campus_name
                    )

        st.markdown("")  # spacing


def _render_fallback_h2h_entry(
    token: str,
    tid: int,
    sessions: List[Dict[str, Any]],
    pending_h2h: List[Dict[str, Any]],
) -> None:
    """Fallback H2H entry for tournaments without field_number structure.

    Shows:
    1. Round-by-round simulation panel (for multi-round leagues)
    2. Per-session forms (first 10)
    """
    import random as _random

    # Phase-order round detection (works for GROUP_STAGE, KNOCKOUT, etc.)
    all_rounds = sorted({
        s.get("tournament_round") or 0
        for s in sessions
        if s.get("tournament_round")
    })
    # Multi-round panel when there are more than 5 distinct rounds
    if len(all_rounds) > 5:
        total_rounds = len(all_rounds)
        done_rounds_set = {
            rn for rn in all_rounds
            if all(
                s.get("result_submitted")
                for s in sessions
                if s.get("tournament_round") == rn
            )
        }
        done_rounds = len(done_rounds_set)
        remaining_rounds = [rn for rn in all_rounds if rn not in done_rounds_set]
        next_round = remaining_rounds[0] if remaining_rounds else None

        with st.expander(
            f"⚽ Round-by-Round Simulation — {done_rounds}/{total_rounds} rounds complete",
            expanded=(next_round is not None),
        ):
            st.progress(
                done_rounds / total_rounds,
                text=f"Rounds: {done_rounds}/{total_rounds} complete",
            )

            if next_round is not None:
                round_sessions = [
                    s for s in sessions
                    if s.get("tournament_round") == next_round
                    and not s.get("result_submitted")
                ]
                col_r, col_all = st.columns(2)
                with col_r:
                    if st.button(
                        f"▶ Simulate Round {next_round} ({len(round_sessions)} matches)",
                        key=f"sim_round_{tid}_{next_round}",
                        type="primary",
                        use_container_width=True,
                    ):
                        ok_count = fail_count = 0
                        for s in round_sessions:
                            p_ids = s.get("participant_user_ids") or []
                            if len(p_ids) == 2:
                                s0, s1 = _random.randint(0, 5), _random.randint(0, 5)
                                ok, _err, _ = submit_h2h_result(
                                    token, s["id"], p_ids[0], s0, p_ids[1], s1
                                )
                                if ok:
                                    ok_count += 1
                                else:
                                    fail_count += 1
                        if fail_count == 0:
                            st.toast(f"✅ Round {next_round} done: {ok_count} matches!", icon="⚽")
                        else:
                            st.toast(
                                f"⚠️ Round {next_round}: {ok_count} OK, {fail_count} failed",
                                icon="⚠️",
                            )
                        st.rerun()
                with col_all:
                    st.caption(
                        f"Remaining: {len(remaining_rounds)} rounds "
                        f"({len(pending_h2h)} matches)\n\n"
                        f"Next: Round {next_round} ({len(round_sessions)} matches)"
                    )
            else:
                st.success("✅ All rounds complete!")

    # Per-phase simulate buttons + per-session forms
    with st.expander(
        f"📝 Manual Result Entry — {len(pending_h2h)} pending match(es)",
        expanded=len(all_rounds) <= 5,
    ):
        phase_order = ["INDIVIDUAL_RANKING", "GROUP_STAGE", "KNOCKOUT", "FINALS", "PLACEMENT"]
        current_phase = None
        for phase in phase_order:
            phase_sessions = [s for s in sessions if s.get("tournament_phase") == phase]
            if phase_sessions and not all(s.get("result_submitted") for s in phase_sessions):
                current_phase = phase
                break

        if current_phase:
            current_phase_pending = [
                s for s in pending_h2h
                if s.get("tournament_phase") == current_phase
            ]
            col_phase, col_all = st.columns(2)

            with col_phase:
                lbl = _phase_label_short(current_phase)
                if st.button(
                    f"▶️ Simulate {lbl}",
                    key=f"simulate_phase_{tid}",
                    type="primary",
                    use_container_width=True,
                ):
                    ok_count = fail_count = 0
                    for s in current_phase_pending:
                        p_ids = s.get("participant_user_ids") or []
                        s0, s1 = _random.randint(0, 5), _random.randint(0, 5)
                        ok, _err, _ = submit_h2h_result(token, s["id"], p_ids[0], s0, p_ids[1], s1)
                        if ok:
                            ok_count += 1
                        else:
                            fail_count += 1
                    if fail_count == 0:
                        st.toast(f"✅ {lbl} complete: {ok_count} matches!", icon="🎉")
                        if current_phase == "GROUP_STAGE":
                            try:
                                rr = requests.post(
                                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/calculate-rankings",
                                    headers={"Authorization": f"Bearer {token}"},
                                    timeout=30,
                                )
                                if rr.status_code == 200:
                                    fr = requests.post(
                                        f"{API_BASE_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
                                        headers={"Authorization": f"Bearer {token}"},
                                        timeout=30,
                                    )
                                    if fr.status_code == 200 and fr.json().get("success"):
                                        st.toast(
                                            f"🏆 Knockout populated: "
                                            f"{fr.json().get('knockout_sessions_updated', 0)} ready!",
                                            icon="✅",
                                        )
                            except Exception:
                                pass
                    else:
                        st.toast(f"⚠️ {ok_count} OK · {fail_count} failed", icon="⚠️")
                    st.rerun()

            with col_all:
                if st.button(
                    "⚡ Simulate All Phases",
                    key=f"simulate_all_{tid}",
                    use_container_width=True,
                ):
                    ok_count = fail_count = 0
                    for s in pending_h2h:
                        p_ids = s.get("participant_user_ids") or []
                        s0, s1 = _random.randint(0, 5), _random.randint(0, 5)
                        ok, _err, _ = submit_h2h_result(token, s["id"], p_ids[0], s0, p_ids[1], s1)
                        if ok:
                            ok_count += 1
                        else:
                            fail_count += 1
                    if fail_count == 0:
                        st.toast(f"✅ {ok_count} results submitted!", icon="⚡")
                        group_sessions = [s for s in sessions if s.get("tournament_phase") == "GROUP_STAGE"]
                        if group_sessions:
                            try:
                                rr = requests.post(
                                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/calculate-rankings",
                                    headers={"Authorization": f"Bearer {token}"},
                                    timeout=30,
                                )
                                if rr.status_code == 200:
                                    fr = requests.post(
                                        f"{API_BASE_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
                                        headers={"Authorization": f"Bearer {token}"},
                                        timeout=30,
                                    )
                                    if fr.status_code == 200 and fr.json().get("success"):
                                        st.toast(
                                            f"🏆 Knockout populated: "
                                            f"{fr.json().get('knockout_sessions_updated', 0)} ready!",
                                            icon="✅",
                                        )
                            except Exception:
                                pass
                    else:
                        st.toast(f"⚠️ {ok_count} OK · {fail_count} failed", icon="⚠️")
                    st.rerun()

            st.caption(
                f"**▶️ Simulate {lbl}:** {len(current_phase_pending)} matches in current phase  ·  "
                f"**⚡ Simulate All:** {len(pending_h2h)} matches across all phases"
            )
        else:
            col_btn, col_info = st.columns([2, 3])
            with col_btn:
                if st.button(
                    "⚡ Simulate All Pending",
                    key=f"simulate_all_{tid}",
                    type="primary",
                    use_container_width=True,
                ):
                    ok_count = fail_count = 0
                    for s in pending_h2h:
                        p_ids = s.get("participant_user_ids") or []
                        s0, s1 = _random.randint(0, 5), _random.randint(0, 5)
                        ok, _err, _ = submit_h2h_result(token, s["id"], p_ids[0], s0, p_ids[1], s1)
                        if ok:
                            ok_count += 1
                        else:
                            fail_count += 1
                    if fail_count == 0:
                        st.toast(f"✅ {ok_count} results submitted!", icon="⚡")
                    else:
                        st.toast(f"⚠️ {ok_count} OK · {fail_count} failed", icon="⚠️")
                    st.rerun()
            with col_info:
                st.caption(f"Submits random scores (0–5) for all {len(pending_h2h)} pending matches")

        st.markdown("---")

        # Per-session forms (first 10)
        shown = pending_h2h[:10]
        for s in shown:
            p_ids = s.get("participant_user_ids") or []
            names = s.get("participant_names") or []
            name0 = (names[0].split()[-1] if names else f"P{p_ids[0]}") if p_ids else "?"
            name1 = (names[1].split()[-1] if len(names) > 1 else f"P{p_ids[1]}") if len(p_ids) > 1 else "?"
            sid = s.get("id")
            phase_str = _phase_label(s.get("tournament_phase"), s.get("tournament_round"))

            c_lbl, c0, c_vs, c1, c_btn = st.columns([2, 2, 1, 2, 1])
            c_lbl.caption(f"#{sid} · {phase_str}")
            sc0 = c0.number_input(
                name0, min_value=0, max_value=99, value=0,
                key=f"sc0_{sid}", label_visibility="visible",
            )
            c_vs.markdown(
                "<div style='text-align:center;padding-top:26px;color:#6b7280'>vs</div>",
                unsafe_allow_html=True,
            )
            sc1 = c1.number_input(
                name1, min_value=0, max_value=99, value=0,
                key=f"sc1_{sid}", label_visibility="visible",
            )
            with c_btn:
                st.markdown("<div style='padding-top:20px'>", unsafe_allow_html=True)
                if st.button("⚽", key=f"submit_r_{sid}", help=f"Submit {name0} {sc0}–{sc1} {name1}"):
                    ok, err, _ = submit_h2h_result(token, sid, p_ids[0], sc0, p_ids[1], sc1)
                    if ok:
                        st.toast(f"✅ {name0} {sc0}–{sc1} {name1}", icon="⚽")
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
                st.markdown("</div>", unsafe_allow_html=True)

        if len(pending_h2h) > 10:
            st.caption(
                f"Showing first 10 of {len(pending_h2h)} pending. "
                "Use ⚡ Simulate All to bulk-submit the rest."
            )


def render_manual_result_entry(
    token: str,
    tid: int,
    sessions: List[Dict[str, Any]],
    campus_configs: Optional[List[Dict[str, Any]]] = None,
    *,
    campus_filter: Optional[str] = None,
    field_filter: Optional[int] = None,
) -> None:
    """Manual result entry panel for pending sessions (H2H and Individual Ranking).

    Entry is organised hierarchically:
    - INDIVIDUAL_RANKING: per-player score/time/distance inputs + Simulate button
    - H2H with field structure: Campus → Field → Round form (1 round = 1 form)
    - H2H without field structure: fallback round-by-round + per-session forms

    Args:
        token:          Auth token.
        tid:            Tournament ID.
        sessions:       All tournament sessions (including completed ones).
        campus_configs: Per-campus schedule configs (from /campus-schedules API).
        campus_filter:  Instructor RBAC: restrict to this campus name.
        field_filter:   Instructor RBAC: restrict to this field number.
    """
    # ── Individual Ranking sessions (unchanged) ───────────────────────────────
    _render_individual_ranking_entry(token, tid, sessions)

    # ── H2H sessions ──────────────────────────────────────────────────────────
    pending_h2h = [
        s for s in sessions
        if not s.get("result_submitted")
        and len(s.get("participant_user_ids") or []) == 2
    ]

    if not pending_h2h:
        return

    # Check whether sessions carry field_number (campus/field structure available)
    has_field_nums = any(
        (s.get("structure_config") or {}).get("field_number") is not None
        for s in sessions
    )

    if has_field_nums and campus_configs is not None:
        # ── Structured entry: Campus → Field → Round form ────────────────────
        st.markdown("### ⚽ Result Entry — Campus / Field / Round")
        st.caption(
            "Each campus and field shown separately. "
            "One form per round — enter scores and submit."
        )
        _render_campus_field_h2h_entry(
            token, tid, sessions,
            campus_configs,
            campus_filter=campus_filter,
            field_filter=field_filter,
        )
    else:
        # ── Fallback: round-by-round + flat per-session forms ────────────────
        _render_fallback_h2h_entry(token, tid, sessions, pending_h2h)
