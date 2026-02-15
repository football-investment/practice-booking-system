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
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api_helpers_monitor import submit_h2h_result
from config import API_BASE_URL

# Import shared utilities
from .utils import phase_icon as _phase_icon, phase_label_short as _phase_label_short, phase_label as _phase_label


# ─── Main Component ──────────────────────────────────────────────────────────

def render_manual_result_entry(token: str, tid: int, sessions: List[Dict[str, Any]]) -> None:
    """Manual result entry panel for pending H2H sessions.

    Shows:
    - ⚡ Simulate All Pending button (random scores, bulk)
    - Per-session score inputs + Submit button (first 10 shown)
    """
    import random as _random

    pending_h2h = [
        s for s in sessions
        if not s.get("result_submitted")
        and len(s.get("participant_user_ids") or []) == 2
    ]

    if not pending_h2h:
        return

    with st.expander(
        f"📝 Manual Result Entry — {len(pending_h2h)} pending match(es)",
        expanded=True,
    ):
        # Phase-by-phase control: Find first incomplete phase
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

            # Simulate Current Phase button
            with col_phase:
                phase_label = _phase_label_short(current_phase)
                if st.button(
                    f"▶️ Simulate {phase_label}",
                    key=f"simulate_phase_{tid}",
                    type="primary",
                    use_container_width=True,
                    help=f"Simulate all {len(current_phase_pending)} matches in {phase_label} only"
                ):
                    ok_count = 0
                    fail_count = 0
                    for s in current_phase_pending:
                        p_ids = s.get("participant_user_ids") or []
                        s0, s1 = _random.randint(0, 5), _random.randint(0, 5)
                        ok, _err, _ = submit_h2h_result(token, s["id"], p_ids[0], s0, p_ids[1], s1)
                        if ok:
                            ok_count += 1
                        else:
                            fail_count += 1
                    if fail_count == 0:
                        st.toast(f"✅ {phase_label} complete: {ok_count} matches!", icon="🎉")

                        # Auto-finalize GROUP_STAGE for group+knockout tournaments
                        if current_phase == "GROUP_STAGE":
                            try:
                                # Step 1: Calculate rankings
                                rank_resp = requests.post(
                                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/calculate-rankings",
                                    headers={"Authorization": f"Bearer {token}"},
                                    timeout=30
                                )

                                # Step 2: Finalize group stage (populate knockout)
                                if rank_resp.status_code == 200:
                                    finalize_resp = requests.post(
                                        f"{API_BASE_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
                                        headers={"Authorization": f"Bearer {token}"},
                                        timeout=30
                                    )

                                    if finalize_resp.status_code == 200:
                                        result = finalize_resp.json()
                                        if result.get("success"):
                                            st.toast(f"🏆 Knockout populated: {result.get('knockout_sessions_updated', 0)} matches ready!", icon="✅")
                            except Exception as e:
                                # Non-blocking: if finalization fails, just log it
                                print(f"⚠️ Auto-finalize failed: {e}")
                    else:
                        st.toast(f"⚠️ {ok_count} OK · {fail_count} failed", icon="⚠️")
                    st.rerun()

            # Simulate All button
            with col_all:
                if st.button(
                    "⚡ Simulate All Phases",
                    key=f"simulate_all_{tid}",
                    use_container_width=True,
                    help=f"Simulate all {len(pending_h2h)} pending matches across all phases"
                ):
                    ok_count = 0
                    fail_count = 0
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

                        # Auto-finalize GROUP_STAGE if it was completed in this run
                        group_sessions = [s for s in sessions if s.get("tournament_phase") == "GROUP_STAGE"]
                        if group_sessions:
                            try:
                                # Step 1: Calculate rankings
                                rank_resp = requests.post(
                                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/calculate-rankings",
                                    headers={"Authorization": f"Bearer {token}"},
                                    timeout=30
                                )

                                # Step 2: Finalize group stage (populate knockout)
                                if rank_resp.status_code == 200:
                                    finalize_resp = requests.post(
                                        f"{API_BASE_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
                                        headers={"Authorization": f"Bearer {token}"},
                                        timeout=30
                                    )

                                    if finalize_resp.status_code == 200:
                                        result = finalize_resp.json()
                                        if result.get("success"):
                                            st.toast(f"🏆 Knockout populated: {result.get('knockout_sessions_updated', 0)} matches ready!", icon="✅")
                            except Exception as e:
                                # Non-blocking: if finalization fails, just log it
                                print(f"⚠️ Auto-finalize failed: {e}")
                    else:
                        st.toast(f"⚠️ {ok_count} OK · {fail_count} failed", icon="⚠️")
                    st.rerun()

            st.caption(
                f"**▶️ Simulate {phase_label}:** {len(current_phase_pending)} matches in current phase only  ·  "
                f"**⚡ Simulate All Phases:** {len(pending_h2h)} matches across all phases"
            )
        else:
            # No incomplete phase found, show generic bulk button
            col_btn, col_info = st.columns([2, 3])
            with col_btn:
                if st.button(
                    "⚡ Simulate All Pending",
                    key=f"simulate_all_{tid}",
                    type="primary",
                    use_container_width=True,
                ):
                    ok_count = 0
                    fail_count = 0
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

        # Per-session forms (show first 10 to keep the UI manageable)
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
