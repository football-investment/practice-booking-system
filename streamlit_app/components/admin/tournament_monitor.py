"""
OPS Test Observability Platform
=================================
Live monitoring of automated test tournaments with:
  - OPS Wizard (5-step launch flow)
  - Auto-tracking of launched test tournaments
  - Real-time phase-by-phase execution visibility
  - No production tournament mixing

Architecture: Launch → Auto-Monitor → Live Tracking
"""

from __future__ import annotations

import datetime
import requests
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from config import API_BASE_URL

from api_helpers_monitor import (
    get_all_tournaments_admin,
    get_campus_schedules,
    get_tournament_detail,
    get_tournament_sessions,
    submit_h2h_result,
    trigger_ops_scenario,
)
from api_client import APIClient

# Refactored components (Iteration 3)
from .tournament_card.leaderboard import render_leaderboard
from .tournament_card.result_entry import render_manual_result_entry
from .tournament_card.session_grid import (
    render_campus_grid,
    render_campus_field_grid,
    build_campus_field_map,
    render_session_card,
)
from .tournament_card.utils import phase_icon as _phase_icon, phase_label_short as _phase_label_short
from .ops_wizard import (
    init_wizard_state,
    reset_wizard_state,
    execute_launch,
    render_wizard,
)
from .ops_wizard.wizard_config import (
    SCENARIO_CONFIG,
    FORMAT_CONFIG,
    INDIVIDUAL_SCORING_CONFIG,
    TOURNAMENT_TYPE_CONFIG,
    SIMULATION_MODE_CONFIG,
    _SCORING_DIR_LABELS,
    _SAFETY_CONFIRMATION_THRESHOLD,
    scoring_label as _scoring_label,
    get_group_knockout_config,
    estimate_session_count,
    estimate_duration_hours,
    generate_default_tournament_name,
)
from .tournament_manager_permissions import TournamentManagerPermissions, get_permissions


# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_REFRESH_SECONDS = 10
_MIN_REFRESH = 5
_MAX_REFRESH = 120

# Status badge colours (HTML inline)
_STATUS_COLOURS: Dict[str, str] = {
    "IN_PROGRESS":        "#22c55e",   # green
    "DRAFT":              "#f59e0b",   # amber
    "COMPLETED":          "#6b7280",   # grey
    "REWARDS_DISTRIBUTED": "#a855f7",  # purple
    "CANCELLED":          "#ef4444",   # red
}

_RESULT_ICONS = {True: "✅", False: "⏳", None: "⏳"}


# ── Helper Functions ─────────────────────────────────────────────────────────

def _badge(label: str, colour: str) -> str:
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 8px;"
        f"border-radius:4px;font-size:0.75rem;font-weight:600'>{label}</span>"
    )


def _progress_bar(done: int, total: int) -> str:
    """Return an HTML mini progress bar."""
    pct = (done / total * 100) if total else 0
    return (
        f"<div style='background:#e5e7eb;border-radius:4px;height:8px;width:100%'>"
        f"<div style='background:#3b82f6;width:{pct:.0f}%;height:8px;border-radius:4px'></div>"
        f"</div>"
        f"<small style='color:#6b7280'>{done}/{total} sessions submitted ({pct:.0f}%)</small>"
    )




# ── Monitor Panel Sub-renderers ──────────────────────────────────────────────







def _render_tournament_card(
    token: str,
    tournament: Dict[str, Any],
    perms: TournamentManagerPermissions,
) -> None:
    """Render a full monitoring card for one tournament with phase tracking.

    Capabilities (result entry, finalization) are gated by *perms*.
    """
    tid = tournament.get("id") or tournament.get("tournament_id")
    name = tournament.get("name", f"Tournament {tid}")

    ok_detail, _, fresh = get_tournament_detail(token, tid)
    if ok_detail and fresh:
        status = fresh.get("status", tournament.get("status", "UNKNOWN"))
        enrolled = fresh.get("enrolled_count", fresh.get("participant_count", "?"))
        # TICKET-UI-02: Split header metric into three distinct values once
        # TICKET-UI-01 (summary endpoint seeded_count) is implemented:
        #   enrolled  = fresh.get("enrolled_count")   # total APPROVED
        #   confirmed = fresh.get("checked_in_count")  # confirmed check-ins
        #   seeded    = fresh.get("seeded_count")       # players in bracket
        # Display as: st.metric("Enrolled", enrolled), st.metric("Confirmed", confirmed),
        #             st.metric("Seeded", seeded)
        # Until TICKET-UI-01 ships, enrolled == approved (may differ from seeded).
        game_preset_name = fresh.get("game_preset_name")
        skills_config: dict = fresh.get("skills_config") or {}
    else:
        status = tournament.get("status", "UNKNOWN")
        enrolled = tournament.get("enrolled_count", tournament.get("participant_count", "?"))
        game_preset_name = None
        skills_config = {}

    colour = _STATUS_COLOURS.get(status, "#9ca3af")

    ok_sessions, _, sessions = get_tournament_sessions(token, tid)
    ok_campuses, _, campus_cfg = get_campus_schedules(token, tid)
    _rankings_resp = APIClient.from_config(token).tournaments.get_rankings(tid)
    ok_rankings = _rankings_resp.ok
    _raw = _rankings_resp.data
    rankings = (_raw if isinstance(_raw, list) else _raw.get("rankings", [])) if ok_rankings and _raw else []

    sessions = sessions if (ok_sessions and isinstance(sessions, list)) else []
    campus_cfg = campus_cfg if (ok_campuses and isinstance(campus_cfg, list)) else []

    total_sessions = len(sessions)
    done_sessions = sum(1 for s in sessions if s.get("result_submitted"))

    # Phase tracking
    phases_present = set(s.get("tournament_phase") for s in sessions if s.get("tournament_phase"))
    phase_progress = {}

    for phase in phases_present:
        phase_sessions = [s for s in sessions if s.get("tournament_phase") == phase]
        phase_done = sum(1 for s in phase_sessions if s.get("result_submitted"))
        phase_total = len(phase_sessions)
        phase_progress[phase] = {
            "done": phase_done,
            "total": phase_total,
            "pct": (phase_done / phase_total * 100) if phase_total else 0
        }

    with st.expander(
        f"🔴 {name}  ·  {status}  ·  {done_sessions}/{total_sessions} submitted",
        expanded=True,
    ):
        # Overall metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Status", status)
        m2.metric("Enrolled", enrolled)
        m3.metric("Total Sessions", total_sessions)
        m4.metric("Submitted", done_sessions)

        st.markdown(_progress_bar(done_sessions, total_sessions), unsafe_allow_html=True)

        # Game Preset / Skill Config info row
        if game_preset_name or skills_config:
            if skills_config:
                _total_w = sum(skills_config.values()) or 1.0
                _skill_parts = [
                    f"**{k.replace('_', ' ').title()}** ({v / _total_w:.0%})"
                    for k, v in sorted(skills_config.items(), key=lambda x: -x[1])
                ]
            else:
                _skill_parts = []
            _preset_label = f"🎮 **Game Preset:** {game_preset_name}" if game_preset_name else "🎮 **Skills being tested:**"
            _skill_str = "  ·  ".join(_skill_parts) if _skill_parts else "—"
            st.markdown(f"{_preset_label}  ·  {_skill_str}")

        st.markdown("---")

        # Phase summary badges (compact row)
        if phase_progress:
            _phase_order_list = ["INDIVIDUAL_RANKING", "GROUP_STAGE", "KNOCKOUT", "FINALS", "PLACEMENT"]
            sorted_phases = sorted(
                phase_progress.keys(),
                key=lambda p: _phase_order_list.index(p) if p in _phase_order_list else 99
            )
            badge_cols = st.columns(len(sorted_phases))
            for idx, phase in enumerate(sorted_phases):
                prog = phase_progress[phase]
                icon = _phase_icon(phase)
                lbl = _phase_label_short(phase)
                done_flag = prog["done"] == prog["total"]
                badge_icon = "✅" if done_flag else "⏳"
                badge_cols[idx].metric(
                    f"{icon} {lbl}",
                    f"{prog['done']}/{prog['total']}",
                    delta=f"{prog['pct']:.0f}%",
                )

            # GROUP_STAGE: per-group breakdown
            if "GROUP_STAGE" in phase_progress:
                gs_sessions = [s for s in sessions if s.get("tournament_phase") == "GROUP_STAGE"]
                groups_seen: Dict[Any, dict] = {}
                for s in gs_sessions:
                    gid = s.get("group_identifier")
                    if gid is None:
                        continue
                    if gid not in groups_seen:
                        groups_seen[gid] = {"done": 0, "total": 0}
                    groups_seen[gid]["total"] += 1
                    if s.get("result_submitted"):
                        groups_seen[gid]["done"] += 1

                if len(groups_seen) > 1:
                    st.caption("**Groups:**")
                    g_cols = st.columns(min(len(groups_seen), 8))
                    for i, (gid, gdata) in enumerate(sorted(groups_seen.items(), key=lambda x: str(x[0]))):
                        gicon = "✅" if gdata["done"] == gdata["total"] else "⏳"
                        g_cols[i % len(g_cols)].metric(
                            f"G{gid}",
                            f"{gdata['done']}/{gdata['total']}",
                            delta=gicon,
                        )

            st.markdown("---")

        # ── Campus / Field View (structural RBAC requirement) ────────────────
        # Admin: all campuses + all fields.
        # Instructor: selects their assigned campus + field (RBAC filter).
        st.subheader("Campus & Field View")
        st.caption(
            "Sessions organised by campus and field. "
            "Each campus and each field is shown as a separate card."
        )

        viewer_role = perms.role  # "admin" or "instructor"
        campus_filter: Optional[str] = None
        field_filter: Optional[int] = None

        if not perms.can_see_all_campuses:
            # Build the campus/field map to populate selectors
            _campus_map = build_campus_field_map(sessions, campus_cfg)
            if _campus_map:
                _campus_names = list(_campus_map.keys())
                st.markdown("**Your assignment (RBAC):**")
                _sel_col1, _sel_col2 = st.columns(2)
                with _sel_col1:
                    campus_filter = st.selectbox(
                        "Campus",
                        options=_campus_names,
                        key=f"campus_filter_{tid}",
                        help="Only sessions for this campus will be shown.",
                    )
                with _sel_col2:
                    _field_opts: List[int] = []
                    if campus_filter and campus_filter in _campus_map:
                        _field_opts = sorted(
                            fn for fn in _campus_map[campus_filter]["fields"].keys()
                            if fn > 0  # exclude pseudo-field 0
                        )
                    if _field_opts:
                        field_filter = st.selectbox(
                            "Field",
                            options=_field_opts,
                            format_func=lambda x: f"Field {x}",
                            key=f"field_filter_{tid}",
                            help="Only sessions for this field will be shown.",
                        )

        render_campus_field_grid(
            sessions,
            campus_cfg,
            rankings,
            viewer_role=viewer_role,
            campus_filter=campus_filter,
            field_filter=field_filter,
        )

        # Manual result entry — only for roles with result-entry permission
        if perms.can_enter_results:
            render_manual_result_entry(
                token, tid, sessions,
                campus_cfg,
                campus_filter=campus_filter,
                field_filter=field_filter,
            )

        # Auto-refresh rankings when all sessions are submitted
        has_knockout = any(s.get("tournament_phase") == "KNOCKOUT" for s in sessions)
        knockout_sessions = [s for s in sessions if s.get("tournament_phase") == "KNOCKOUT"]
        all_submitted = total_sessions > 0 and done_sessions == total_sessions
        knockout_complete = has_knockout and knockout_sessions and all(s.get("result_submitted") for s in knockout_sessions)

        # When all sessions are done → auto-finalize + distribute (admin-only)
        if perms.can_finalize:
            if all_submitted and status == "IN_PROGRESS":
                # Step 0: For INDIVIDUAL_RANKING sessions submitted via rounds,
                # game_results is still None (rounds are stored in rounds_data).
                # The tournament finalizer blocks on game_results is None, so we
                # must call the session-level finalize endpoint first.
                for _s in sessions:
                    if (
                        _s.get("match_format") == "INDIVIDUAL_RANKING"
                        and _s.get("result_submitted")
                        and _s.get("game_results") is None
                    ):
                        try:
                            requests.post(
                                f"{API_BASE_URL}/api/v1/tournaments/{tid}"
                                f"/sessions/{_s['id']}/finalize",
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=30,
                            )
                        except Exception:
                            pass

                try:
                    _fin_resp = requests.post(
                        f"{API_BASE_URL}/api/v1/tournaments/{tid}/finalize-tournament",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=30,
                    )
                    if _fin_resp.status_code == 200:
                        ok_detail2, _, fresh2 = get_tournament_detail(token, tid)
                        if ok_detail2 and fresh2:
                            status = fresh2.get("status", status)
                except Exception:
                    pass

            if all_submitted and status == "COMPLETED":
                try:
                    requests.post(
                        f"{API_BASE_URL}/api/v1/tournaments/{tid}/distribute-rewards-v2",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"tournament_id": tid},
                        timeout=30,
                    )
                    ok_detail3, _, fresh3 = get_tournament_detail(token, tid)
                    if ok_detail3 and fresh3:
                        status = fresh3.get("status", status)
                except Exception:
                    pass

        # Only call calculate-rankings while still IN_PROGRESS (intermediate refresh).
        # After finalization (COMPLETED/REWARDS_DISTRIBUTED) rankings are already correct.
        if (knockout_complete or all_submitted) and status == "IN_PROGRESS":
            try:
                requests.post(
                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/calculate-rankings",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
            except Exception:
                pass

        _resp2 = APIClient.from_config(token).tournaments.get_rankings(tid)
        _raw2 = _resp2.data
        rankings2 = (_raw2 if isinstance(_raw2, list) else _raw2.get("rankings", [])) if _resp2.ok and _raw2 else []
        if rankings2:
            rankings = rankings2

        # Detect IR tournament and pass scoring_type so leaderboard can show
        # measured_value instead of meaningless W/D/L stats
        ir_session = next(
            (s for s in sessions if s.get("match_format") == "INDIVIDUAL_RANKING"),
            None,
        )
        ir_scoring_type = ir_session.get("scoring_type", "") if ir_session else ""
        # ROUNDS_BASED wraps the underlying measurement type — unwrap for leaderboard unit label
        if ir_scoring_type == "ROUNDS_BASED" and ir_session:
            cfg = ir_session.get("structure_config") or {}
            _unwrapped = cfg.get("scoring_method") or cfg.get("scoring_type")
            if _unwrapped and _unwrapped != "ROUNDS_BASED":
                ir_scoring_type = _unwrapped

        st.subheader("Leaderboard")
        render_leaderboard(
            rankings,
            status=status,
            has_knockout=has_knockout,
            scoring_type=ir_scoring_type,
            is_individual_ranking=ir_session is not None,
        )


# ── Public Entry Points ──────────────────────────────────────────────────────

def render_tournament_manager(token: str, perms: TournamentManagerPermissions) -> None:
    """Role-aware Tournament Manager render function.

    Args:
        token: Auth token for API calls.
        perms: Caller-supplied permissions (from tournament_manager_permissions.get_permissions).
               Controls which features (wizard, result entry, finalization) are visible.
    """

    # E2E test support: auto-track a specific tournament via ?track_id=N URL param.
    # This allows headless tests to navigate directly to a tournament's monitoring card
    # without going through the OPS Wizard flow.
    _auto_track = st.query_params.get("track_id")
    if _auto_track:
        try:
            _auto_id = int(_auto_track)
            if "_ops_tracked_tournaments" not in st.session_state:
                st.session_state["_ops_tracked_tournaments"] = []
            if _auto_id not in st.session_state["_ops_tracked_tournaments"]:
                st.session_state["_ops_tracked_tournaments"].append(_auto_id)
        except (ValueError, TypeError):
            pass

    with st.sidebar:
        # ── Load tournament data first (needed to decide layout) ──────────────
        if "_ops_tracked_tournaments" not in st.session_state:
            st.session_state["_ops_tracked_tournaments"] = []

        ok, err, all_tournaments = get_all_tournaments_admin(token)
        if not ok:
            if err == "SESSION_EXPIRED":
                # Token expired → clear session and force re-login
                for _k in list(st.session_state.keys()):
                    del st.session_state[_k]
                st.warning("⚠️ Session expired. Please log in again.")
                if st.button("🔑 Go to Login", type="primary"):
                    st.switch_page("🏠_Home.py")
                st.stop()
            st.error(f"Cannot load tournaments: {err}")
            all_tournaments = []

        ops_tournaments = [
            t for t in all_tournaments
            if t.get("name", "").startswith("OPS-")
        ]
        active_ops = [t for t in ops_tournaments if t.get("status") == "IN_PROGRESS"]
        completed_ops = sorted(
            [t for t in ops_tournaments if t.get("status") in ("COMPLETED", "REWARDS_DISTRIBUTED")],
            key=lambda x: x.get("id", 0), reverse=True,
        )[:5]
        visible_ops = active_ops + completed_ops

        tracked_ids = set(st.session_state["_ops_tracked_tournaments"])
        # Include ALL tracked tournaments regardless of name prefix
        # (custom-named tournaments like "Real test V1" are also valid)
        tracked_tournaments = [
            t for t in all_tournaments
            if (t.get("id") or t.get("tournament_id")) in tracked_ids
        ]
        has_active = any(t.get("status") == "IN_PROGRESS" for t in tracked_tournaments)

        # ── MONITORING CONTROLS — shown prominently when a tournament is running ─
        st.markdown("## ⚙️ MONITORING CONTROLS")
        _caption = "Live tracking of OPS test tournaments" if perms.can_create else "Live tournament tracking"
        st.caption(_caption)

        _tracked_label = "Tracked Tests" if perms.can_create else "Tracked Tournaments"
        st.metric(_tracked_label, len(tracked_tournaments))

        if tracked_tournaments:
            _list_label = "**Active Tests:**" if perms.can_create else "**Tracked:**"
            st.markdown(_list_label)
            for t in tracked_tournaments:
                tid = t.get("id") or t.get("tournament_id")
                name = t.get("name", f"T{tid}")
                status = t.get("status", "UNKNOWN")
                status_icon = {
                    "IN_PROGRESS":         "🟢",
                    "COMPLETED":           "⚫",
                    "REWARDS_DISTRIBUTED": "🎁",
                    "DRAFT":               "🟡",
                }.get(status, "")
                clean_name = name
                if name.startswith("OPS-"):
                    parts = name.split("-")
                    if len(parts) >= 4:
                        clean_name = "-".join(parts[1:4])
                st.caption(f"{status_icon} {clean_name}")

            if st.button("🗑️ Clear All Tracked Tests", use_container_width=True):
                st.session_state["_ops_tracked_tournaments"] = []
                st.rerun()
        else:
            st.info("No tests currently tracked.\n\nLaunch a test using the wizard below to start tracking.")

        st.markdown("---")

        # Auto-refresh controls
        _stored = st.session_state.get("monitor_refresh_sec", _DEFAULT_REFRESH_SECONDS)
        if not isinstance(_stored, (int, float)) or not (_MIN_REFRESH <= _stored <= _MAX_REFRESH):
            st.session_state["monitor_refresh_sec"] = _DEFAULT_REFRESH_SECONDS
        refresh_sec = st.slider(
            "Auto-refresh (seconds)",
            min_value=_MIN_REFRESH,
            max_value=_MAX_REFRESH,
            value=_DEFAULT_REFRESH_SECONDS,
            step=5,
            key="monitor_refresh_sec",
        )

        if st.button("🔄 Refresh now", use_container_width=True):
            st.rerun()

        st.caption(f"Last refresh: {time.strftime('%H:%M:%S')}")

        st.markdown("---")

        # ── OPS WIZARD — admin-only, collapsed while a test is running ──────
        if perms.can_create:
            with st.expander(
                "🚀 OPS WIZARD — Launch new test",
                expanded=not has_active,
            ):
                render_wizard()

    # Main area: Show tracked tournaments
    if not tracked_tournaments:
        if perms.can_create:
            st.info("""
## 🎯 OPS Test Observability Platform

**No active test tournaments to track.**

### How to start:

1. Use the **OPS Wizard** in the sidebar to launch a new test tournament
2. After launch, the test will **automatically appear** in the live tracking view
3. Monitor real-time execution with auto-refresh

### What you'll see:
- ✅ Session progress (group stage, knockout, finals)
- 🏆 Live leaderboards
- 📊 Match results and phase transitions
- ⏱️ Real-time status updates

**Launch a test to begin observability.**
            """)
        else:
            st.info("""
## 🏆 Tournament Manager

**No active tournaments are currently being tracked.**

### How to start:

1. Enter a **Tournament ID** in the tracking field above to add a tournament
2. The tournament will appear here with live status and progress

### What you'll see:
- ✅ Session progress by phase
- 🏆 Live leaderboard
- 📊 Match results
- ⏱️ Real-time updates
            """)
        return

    # Fragment: Auto-refresh tracked tournaments (always enabled, interval from slider)
    @st.fragment(run_every=int(refresh_sec))
    def _cards_fragment() -> None:
        st.markdown("## 🔴 LIVE TRACKING")
        st.caption(f"Monitoring {len(tracked_tournaments)} active tournament(s)")
        st.markdown("---")

        for tournament in tracked_tournaments:
            _render_tournament_card(token, tournament, perms)
            st.markdown("---")

        st.caption(f"Data refreshed: {time.strftime('%H:%M:%S')}")

    _cards_fragment()


def render_tournament_monitor(token: str) -> None:
    """Backward-compatible wrapper — always uses admin permissions.

    Retained so existing callers (e.g. old Tournament_Monitor.py page) continue
    to work without modification.  New callers should use render_tournament_manager
    with an explicit permissions object.
    """
    _admin_perms = get_permissions("admin")
    render_tournament_manager(token, _admin_perms)
