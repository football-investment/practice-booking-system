"""
Tournament Session Grid Components

Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
Provides session grid rendering with phase-based organization.
"""

from typing import Any, Dict, List, Optional
from collections import defaultdict
import streamlit as st
import pandas as pd

# Import shared utilities
from .utils import phase_icon, phase_label_short, phase_label


# ─── Session Card Rendering ──────────────────────────────────────────────────

def render_session_card(session: Dict[str, Any]) -> None:
    """Render a single match card inside an st.container."""
    result_submitted = session.get("result_submitted", False) or session.get("game_results") is not None
    icon = "✅" if result_submitted else "⏳"
    names = session.get("participant_names") or []
    match_fmt = session.get("match_format", "")
    is_individual = match_fmt in ("INDIVIDUAL_RANKING",)

    group_id = session.get("group_identifier")
    if is_individual:
        n = len(names)
        title = f"{n} players (Individual Ranking)" if n else f"Session {session.get('id', '?')}"
    elif group_id and names:
        title = f"Group {group_id}: {' vs '.join(names)}"
    elif names:
        title = " vs ".join(names)
    else:
        phase = session.get("tournament_phase", "")
        if phase in ("KNOCKOUT", "FINALS", "BRONZE"):
            title = "TBD vs TBD"  # TICKET-UI-03: Replace with "BYE" when participant_count==1
        else:
            title = f"Session {session.get('id', '?')}"

    phase = session.get("tournament_phase", "")
    round_ = session.get("tournament_round")
    phase_str = phase_label(phase, round_)

    match_format = session.get("match_format", "")
    if match_format:
        format_short = "H2H" if match_format == "HEAD_TO_HEAD" else "IND"
        phase_str = f"{format_short} · {phase_str}"

    date_start = (session.get("date_start") or "")[:16].replace("T", " ")

    col_icon, col_info = st.columns([1, 6])
    with col_icon:
        st.markdown(f"### {icon}")
    with col_info:
        st.markdown(f"**{title}**")
        st.caption(f"{phase_str}  ·  {date_start}")


def parse_score(session: Dict[str, Any]) -> str:
    """Extract score string from game_results for a 2-player H2H session.

    Returns e.g. '3-1' or '' if not applicable/available.
    """
    import json as _json
    raw = session.get("game_results")
    if not raw:
        return ""
    try:
        results = _json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(results, list) or len(results) < 2:
            return ""
        p_ids = session.get("participant_user_ids") or []
        if not p_ids or len(p_ids) < 2:
            return ""
        score_map = {r.get("user_id"): r.get("score", r.get("goals", 0)) for r in results}
        s0 = score_map.get(p_ids[0], "?")
        s1 = score_map.get(p_ids[1], "?")
        return f"{s0}-{s1}"
    except Exception:
        return ""


def render_session_cell(s: Dict[str, Any]) -> None:
    """Render a single session cell: icon + matchup + score + location.

    Handles 3 cases:
    1. Completed match: Show participants from game_results + score
    2. Pending knockout: Show seeding info from structure_config
    3. Group stage: Show participant_names
    """
    import json as _json

    result_submitted = s.get("result_submitted", False)
    cell_icon = "✅" if result_submitted else "⏳"
    names = s.get("participant_names") or []
    sfmt = s.get("match_format", "")
    location = s.get("location") or ""

    # ── Case 1: COMPLETED match → extract names from game_results ──
    if result_submitted and s.get("game_results"):
        try:
            raw_results = s.get("game_results")
            results = _json.loads(raw_results) if isinstance(raw_results, str) else raw_results

            # NEW API FORMAT: {"match_format": "HEAD_TO_HEAD", "participants": [...]}
            if isinstance(results, dict) and "participants" in results:
                parts = results["participants"]
                if len(parts) >= 2:
                    # Extract user_id and scores from participants
                    p0, p1 = parts[0], parts[1]
                    uid0 = p0.get("user_id")
                    uid1 = p1.get("user_id")
                    score0 = p0.get("score", "?")
                    score1 = p1.get("score", "?")

                    # Get names from participant_names array (matches user_id order)
                    name0 = names[0] if len(names) > 0 else f"P{uid0}"
                    name1 = names[1] if len(names) > 1 else f"P{uid1}"

                    # Format: "Müller 3-1 Schmidt"
                    short0 = name0.split()[-1] if name0 else "?"
                    short1 = name1.split()[-1] if name1 else "?"
                    matchup = f"{short0} **{score0}-{score1}** {short1}"
                    loc_str = f"  ·  📍{location}" if location else ""
                    st.caption(f"{cell_icon} {matchup}{loc_str}")
                    return

            # LEGACY FORMAT: [{"name": ..., "score": ...}, ...]
            elif isinstance(results, list) and len(results) >= 2:
                r0, r1 = results[0], results[1]
                name0 = r0.get("name", f"P{r0.get('user_id', '?')}")
                name1 = r1.get("name", f"P{r1.get('user_id', '?')}")
                score0 = r0.get("score", r0.get("goals", "?"))
                score1 = r1.get("score", r1.get("goals", "?"))

                short0 = name0.split()[-1] if name0 else "?"
                short1 = name1.split()[-1] if name1 else "?"
                matchup = f"{short0} **{score0}-{score1}** {short1}"
                loc_str = f"  ·  📍{location}" if location else ""
                st.caption(f"{cell_icon} {matchup}{loc_str}")
                return
        except Exception:
            pass  # Fallback to original logic

    # ── Case 2: PENDING knockout → show seeding info from structure_config ──
    if not result_submitted and not names:
        structure = s.get("structure_config") or {}
        bracket_info = structure.get("matchup") or structure.get("round_name")
        if bracket_info:
            # Show "A1 vs B2" or "Winner QF1 vs Winner QF2" or "3rd Place Match"
            loc_str = f"  ·  📍{location}" if location else ""
            st.caption(f"{cell_icon} {bracket_info}{loc_str}")
            return

    # ── Case 3: GROUP STAGE or fallback ──
    if sfmt == "INDIVIDUAL_RANKING":
        matchup = f"{len(names)} players"
    elif names:
        matchup = " vs ".join(n.split()[-1] if n else "?" for n in names)
    elif not result_submitted and s.get("tournament_phase") in ("KNOCKOUT", "FINALS", "BRONZE"):
        # TICKET-UI-03: Distinguish bye from pending matchup:
        #   len(participant_user_ids) == 1 → matchup = "BYE" (auto-advance)
        #   len(participant_user_ids) == 0 → matchup = "TBD vs TBD" (not yet seeded)
        matchup = "TBD vs TBD"
    else:
        matchup = f"S{s.get('id', '?')}"

    score = parse_score(s) if result_submitted else ""
    score_str = f" **{score}**" if score else ""
    loc_str = f"  ·  📍{location}" if location else ""
    st.caption(f"{cell_icon} {matchup}{score_str}{loc_str}")


# ─── Phase Qualifiers ────────────────────────────────────────────────────────

def get_phase_qualifiers(sessions: List[Dict[str, Any]], phase: str, rankings: List[Dict[str, Any]]) -> List[str]:
    """Extract qualifier names from a completed phase.

    For GROUP_STAGE: Top 2 from each group
    For knockout rounds: Winners of all matches
    """
    qualifiers = []
    phase_sessions = [s for s in sessions if s.get("tournament_phase") == phase]

    if phase == "GROUP_STAGE":
        # Group winners from rankings
        groups_seen = set(s.get("group_identifier") for s in phase_sessions if s.get("group_identifier"))
        for group_id in sorted(groups_seen):
            group_rankings = [
                r for r in rankings
                if r.get("group_identifier") == group_id
            ][:2]  # Top 2 from each group
            for r in group_rankings:
                name = r.get("name") or r.get("username") or f"Player {r.get('user_id', '?')}"
                qualifiers.append(f"{name} (G{group_id})")
    else:
        # Knockout: winners from game_results
        import json as _json
        for s in phase_sessions:
            if not s.get("result_submitted") or not s.get("game_results"):
                continue
            try:
                results = s.get("game_results")
                results = _json.loads(results) if isinstance(results, str) else results
                if isinstance(results, list) and len(results) >= 2:
                    # Find winner (higher score)
                    r0, r1 = results[0], results[1]
                    sc0 = r0.get("score", r0.get("goals", 0))
                    sc1 = r1.get("score", r1.get("goals", 0))
                    if sc0 > sc1:
                        winner_name = r0.get("name", f"P{r0.get('user_id', '?')}")
                    elif sc1 > sc0:
                        winner_name = r1.get("name", f"P{r1.get('user_id', '?')}")
                    else:
                        winner_name = f"{r0.get('name', '?')} / {r1.get('name', '?')} (tie)"
                    qualifiers.append(winner_name)
            except Exception:
                pass

    return qualifiers


def should_show_phase(phase: str, sessions: List[Dict[str, Any]], phase_order: List[str]) -> bool:
    """Determine if a phase should be visible (progressive reveal).

    A phase is visible if:
    1. It's the first phase, OR
    2. All previous phases are completed
    """
    if phase not in phase_order:
        return True  # Unknown phase, show it

    phase_idx = phase_order.index(phase)
    if phase_idx == 0:
        return True  # First phase always visible

    # Check if all previous phases are completed
    for i in range(phase_idx):
        prev_phase = phase_order[i]
        prev_sessions = [s for s in sessions if s.get("tournament_phase") == prev_phase]
        if not prev_sessions:
            continue  # Phase doesn't exist, skip

        # Check if all sessions in previous phase are completed
        prev_done = all(s.get("result_submitted") for s in prev_sessions)
        if not prev_done:
            return False  # Previous phase incomplete, hide this phase

    return True  # All previous phases complete, show this phase


# ─── Phase Completion Banner ─────────────────────────────────────────────────

def render_phase_completion_banner(
    phase: str,
    qualifiers: List[str],
    sessions: List[Dict[str, Any]] = None,
    rankings: List[Dict[str, Any]] = None
) -> None:
    """Render a completion banner with qualifiers list and group standings tables."""
    st.markdown("")  # Spacing

    # Completion message
    phase_label_text = phase_label_short(phase)

    if phase == "GROUP_STAGE":
        banner_text = f"🎉 **{phase_label_text} COMPLETE** — Qualifiers (Top 2 from each group):"
    else:
        banner_text = f"🎉 **{phase_label_text} COMPLETE** — Qualifiers:"

    st.success(banner_text)

    # GROUP_STAGE: Show detailed standings tables
    if phase == "GROUP_STAGE" and rankings:
        # Group rankings by group_identifier
        groups_dict = {}
        for r in rankings:
            group_id = r.get("group_identifier", "?")
            if group_id not in groups_dict:
                groups_dict[group_id] = []
            groups_dict[group_id].append(r)

        # Sort groups alphabetically
        sorted_groups = sorted(groups_dict.items())

        if sorted_groups:
            st.markdown("#### 📊 Group Standings")

            # Display groups in columns (2 columns for better layout)
            cols = st.columns(2)
            for idx, (group_id, group_rankings) in enumerate(sorted_groups):
                with cols[idx % 2]:
                    st.markdown(f"**Group {group_id}**")

                    # Sort by group-stage points (desc), then GD (desc) — NOT final tournament rank
                    sorted_rankings = sorted(
                        group_rankings,
                        key=lambda x: (
                            -(x.get("points") or 0),
                            -(x.get("goal_difference") or 0),
                            -(x.get("goals_for") or 0),
                        )
                    )

                    # Create standings table
                    table_data = []
                    for pos, r in enumerate(sorted_rankings, start=1):
                        name = r.get("name") or r.get("username") or f"Player {r.get('user_id', '?')}"
                        # Shorten name to last name only
                        short_name = name.split()[-1] if name else "?"

                        pts = r.get("points")
                        # Points may be Decimal or float — convert to int for display
                        try:
                            pts = int(float(pts)) if pts is not None else 0
                        except (TypeError, ValueError):
                            pts = 0

                        row = {
                            "Pos": pos,
                            "Player": short_name,
                            "Pts": pts,
                            "W": r.get("wins", 0),
                            "D": r.get("draws", 0),
                            "L": r.get("losses", 0),
                            "GF": r.get("goals_for", 0),
                            "GA": r.get("goals_against", 0),
                        }
                        # Only show GD if at least one entry has a non-zero value
                        if any(x.get("goal_difference") for x in group_rankings):
                            row["GD"] = r.get("goal_difference", 0)
                        table_data.append(row)

                    # Render as dataframe
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, hide_index=True, use_container_width=True)

            st.markdown("")  # Spacing

    # Qualifiers list
    if qualifiers:
        q_cols = st.columns(min(len(qualifiers), 4))
        for i, q_name in enumerate(qualifiers):
            q_cols[i % len(q_cols)].caption(f"✅ {q_name}")
    else:
        st.caption("_(Qualifiers being processed...)_")

    st.markdown("")  # Spacing


# ─── Phase Grid Rendering ────────────────────────────────────────────────────

def render_phase_grid(phase: str, phase_sessions: List[Dict[str, Any]]) -> None:
    """Render the match grid for a single phase."""
    if phase == "INDIVIDUAL_RANKING":
        # Single session with all players — no grid needed
        for s in phase_sessions:
            result_submitted = s.get("result_submitted", False)
            cell_icon = "✅" if result_submitted else "⏳"
            names = s.get("participant_names") or []
            n = len(names)
            st.caption(f"{cell_icon} {n} players — Individual Ranking session (all compete together)")
        return

    if phase == "GROUP_STAGE":
        # Group rows × Round columns
        groups: Dict[Any, Dict[Any, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        for s in phase_sessions:
            gid = s.get("group_identifier") or "?"
            rnd = s.get("tournament_round") or 1
            groups[gid][rnd].append(s)

        all_rounds = sorted({r for grp in groups.values() for r in grp})
        _MAX_R = 6
        displayed_rounds = all_rounds[:_MAX_R]
        if len(all_rounds) > _MAX_R:
            st.caption(f"Showing rounds {displayed_rounds[0]}–{displayed_rounds[-1]} of {len(all_rounds)}")

        n_r = len(displayed_rounds)
        if n_r == 0:
            return

        # Header row
        hcols = st.columns([1] + [3] * n_r)
        hcols[0].markdown("**Group**")
        for i, r in enumerate(displayed_rounds):
            hcols[i + 1].markdown(f"**Round {r}**")

        # Group rows
        for gid in sorted(groups.keys(), key=lambda x: (str(x))):
            grp_done = sum(1 for ss in phase_sessions if ss.get("group_identifier") == gid and ss.get("result_submitted"))
            grp_total = sum(1 for ss in phase_sessions if ss.get("group_identifier") == gid)
            grp_pct = int(grp_done / grp_total * 100) if grp_total else 0
            status_icon = "✅" if grp_done == grp_total else "⏳"

            row_cols = st.columns([1] + [3] * n_r)
            row_cols[0].markdown(f"{status_icon} **Group {gid}**")
            row_cols[0].caption(f"{grp_done}/{grp_total} · {grp_pct}%")

            for i, rnd in enumerate(displayed_rounds):
                cell_sessions = groups[gid].get(rnd, [])
                with row_cols[i + 1]:
                    if not cell_sessions:
                        st.caption("—")
                    else:
                        for s in cell_sessions:
                            render_session_cell(s)
    else:
        # Bracket phase (KNOCKOUT, FINALS, etc.): round columns
        by_round: Dict[Any, List[Dict]] = defaultdict(list)
        for s in phase_sessions:
            rnd = s.get("tournament_round") or 1
            by_round[rnd].append(s)

        all_rounds = sorted(by_round.keys())
        _MAX_R = 6
        displayed_rounds = all_rounds[:_MAX_R]
        n_r = len(displayed_rounds)
        if n_r == 0:
            return

        hcols = st.columns([1] + [3] * n_r)
        hcols[0].markdown("**Phase**")
        for i, r in enumerate(displayed_rounds):
            hcols[i + 1].markdown(f"**Round {r}**")

        row_cols = st.columns([1] + [3] * n_r)
        icon = phase_icon(phase)
        label = phase_label_short(phase)
        row_cols[0].markdown(f"{icon} {label}")

        for i, rnd in enumerate(displayed_rounds):
            cell_sessions = by_round.get(rnd, [])
            with row_cols[i + 1]:
                if not cell_sessions:
                    st.caption("—")
                else:
                    for s in cell_sessions:
                        render_session_cell(s)


# ─── Phase Container ─────────────────────────────────────────────────────────

def render_phase_container(
    phase: str,
    sessions: List[Dict[str, Any]],
    campus_configs: List[Dict[str, Any]],
    rankings: List[Dict[str, Any]],
    phase_complete: bool,
) -> None:
    """Render a single tournament phase as a self-contained logical unit.

    Structure:
    1. Phase header with completion status
    2. Phase grid (campus-parallel sessions)
    3. Phase completion banner with qualifiers (if complete)
    """
    phase_sessions = [s for s in sessions if s.get("tournament_phase") == phase]
    if not phase_sessions:
        return

    icon = phase_icon(phase)
    label = phase_label_short(phase)
    done = sum(1 for s in phase_sessions if s.get("result_submitted"))
    total = len(phase_sessions)
    pct = int(done / total * 100) if total else 0

    # Phase completion status
    if phase_complete:
        status_badge = "✅ COMPLETE"
        badge_color = "#22c55e"
    else:
        status_badge = f"⏳ {done}/{total} ({pct}%)"
        badge_color = "#f59e0b"

    # Phase container with clear separation
    with st.container():
        st.markdown("---")

        # Phase header
        h_col1, h_col2 = st.columns([3, 1])
        with h_col1:
            st.markdown(
                f"### {icon} **{label}**",
                unsafe_allow_html=True
            )
        with h_col2:
            st.markdown(
                f"<div style='text-align:right;padding-top:10px;'>"
                f"<span style='background-color:{badge_color};color:white;padding:4px 12px;"
                f"border-radius:12px;font-weight:bold;font-size:14px;'>{status_badge}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        # Show unique campuses/locations running in parallel
        locations = sorted({s.get("location") for s in phase_sessions if s.get("location")})
        if locations:
            st.caption(f"📍 **Parallel venues:** {' · '.join(locations)}")
        elif campus_configs:
            campus_names = sorted({c.get("campus_name") or c.get("name", "") for c in campus_configs if c.get("campus_name") or c.get("name")})
            if campus_names:
                st.caption(f"📍 **Campuses:** {' · '.join(campus_names)}")

        st.markdown("")  # Spacing

        # Phase grid rendering
        render_phase_grid(phase, phase_sessions)

        # Phase completion banner
        if phase_complete:
            qualifiers = get_phase_qualifiers(sessions, phase, rankings)
            render_phase_completion_banner(phase, qualifiers, sessions, rankings)

        st.markdown("")  # Spacing after phase


# ─── Main Campus Grid ────────────────────────────────────────────────────────

def render_campus_grid(sessions: List[Dict[str, Any]], campus_configs: List[Dict[str, Any]], rankings: List[Dict[str, Any]] = None) -> None:
    """Render sessions with complete phase separation.

    Each phase is rendered as an independent logical unit with:
    - Phase header with completion status
    - Campus-parallel session grid
    - Phase completion banner with qualifiers
    - Progressive reveal (only show phases when dependencies complete)
    """
    if not sessions:
        st.info("No sessions generated yet.")
        return

    rankings = rankings or []

    # Define phase order for progressive reveal
    phase_order = ["INDIVIDUAL_RANKING", "GROUP_STAGE", "KNOCKOUT", "FINALS", "PLACEMENT"]

    # Detect all phases present in sessions
    phases_present = []
    for p in phase_order:
        if any(s.get("tournament_phase") == p for s in sessions):
            phases_present.append(p)

    # Also catch unexpected phases
    for s in sessions:
        ph = s.get("tournament_phase")
        if ph and ph not in phase_order and ph not in phases_present:
            phases_present.append(ph)

    # Render each phase as a separate container
    for phase in phases_present:
        # Progressive reveal: only show phase if previous phases are complete
        if not should_show_phase(phase, sessions, phase_order):
            continue

        phase_sessions = [s for s in sessions if s.get("tournament_phase") == phase]
        phase_complete = all(s.get("result_submitted") for s in phase_sessions)

        render_phase_container(
            phase=phase,
            sessions=sessions,
            campus_configs=campus_configs,
            rankings=rankings,
            phase_complete=phase_complete,
        )


# ─── Campus / Field RBAC Grid ─────────────────────────────────────────────────
#
# Structural requirement: regardless of tournament size or type, campuses and
# fields are always shown as separate cards.
#
# Admin  → all campuses visible, all fields visible.
# Instructor → only their assigned campus + field (campus_filter / field_filter).
#
# Field distribution across campuses (when campus_configs present):
#   campus_configs is an ordered list; parallel_fields defines how many fields
#   each campus hosts.  Field numbers are allocated cumulatively.
#   e.g. [{campus_name:"Alpha", parallel_fields:3}, {campus_name:"Beta", parallel_fields:2}]
#   → fields 1-3 → Alpha, fields 4-5 → Beta
#   Without campus_configs → single "Main Campus" with all field_numbers.
# ──────────────────────────────────────────────────────────────────────────────

_CAMPUS_CARD_CSS = (
    "background:linear-gradient(135deg,#1e3a5f,#2563eb);"
    "color:#fff;padding:10px 16px;border-radius:8px 8px 0 0;"
    "font-weight:600;font-size:1rem;margin-bottom:2px;"
)


def build_campus_field_map(
    sessions: List[Dict[str, Any]],
    campus_configs: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Build a campus → field → sessions mapping.

    Returns:
        {campus_name: {"info": campus_config_dict, "fields": {field_num: [sessions]}}}

    Field numbers are drawn from ``structure_config.field_number`` on each
    session.  Campuses are derived from *campus_configs* (cumulative
    parallel_fields) or from a single implicit "Main Campus" when configs are
    absent.  Sessions without a field_number are placed under pseudo-field 0
    in the first campus.
    """
    # Unique field numbers present in sessions
    field_nums_present = sorted({
        (s.get("structure_config") or {}).get("field_number")
        for s in sessions
        if (s.get("structure_config") or {}).get("field_number") is not None
    })

    # Build field_number → campus_name lookup
    field_to_campus: Dict[int, str] = {}
    campus_info_lookup: Dict[str, Dict] = {}

    if campus_configs:
        offset = 0
        for cfg in campus_configs:
            cname = (
                cfg.get("campus_name")
                or cfg.get("name")
                or cfg.get("venue_label")
                or f"Campus {cfg.get('campus_id', '?')}"
            )
            pf = max(1, int(cfg.get("parallel_fields") or 1))
            for fn in range(offset + 1, offset + pf + 1):
                field_to_campus[fn] = cname
            campus_info_lookup[cname] = cfg
            offset += pf

    if not field_to_campus and field_nums_present:
        # No explicit campus configs — single implicit campus
        cname = "Main Campus"
        for fn in field_nums_present:
            field_to_campus[fn] = cname
        campus_info_lookup[cname] = {
            "campus_name": cname,
            "parallel_fields": len(field_nums_present),
        }

    # Distribute sessions into campus → field buckets
    campus_map: Dict[str, Dict[str, Any]] = {}
    for s in sessions:
        fn = (s.get("structure_config") or {}).get("field_number")
        if fn is None:
            # No field_number → first campus, pseudo-field 0
            cname = next(iter(campus_info_lookup)) if campus_info_lookup else "Main Campus"
            fn = 0
        else:
            cname = field_to_campus.get(fn, f"Campus (F{fn})")

        if cname not in campus_map:
            campus_map[cname] = {
                "info": campus_info_lookup.get(cname, {"campus_name": cname}),
                "fields": defaultdict(list),
            }
        campus_map[cname]["fields"][fn].append(s)

    return campus_map


def _render_field_card(
    field_num: int,
    field_sessions: List[Dict[str, Any]],
) -> None:
    """Render one field as a collapsible card with progress + match preview."""
    if not field_sessions:
        return

    done = sum(1 for s in field_sessions if s.get("result_submitted"))
    total = len(field_sessions)
    pct = done / total if total else 0
    status_icon = "✅" if done == total else "⏳"
    pending = [s for s in field_sessions if not s.get("result_submitted")]

    fn_label = f"Field {field_num}" if field_num else "All Sessions"
    exp_label = f"{status_icon} **{fn_label}** — {done}/{total}"

    # Auto-expand only if small and incomplete
    auto_expand = (done < total and total <= 8)

    with st.expander(exp_label, expanded=auto_expand):
        st.progress(pct, text=f"{done}/{total} matches submitted")

        if pending:
            nxt = min(pending, key=lambda s: (s.get("tournament_round") or 9999))
            rnd = nxt.get("tournament_round", "?")
            names = nxt.get("participant_names") or []
            matchup = (
                " vs ".join((n.split()[-1] if n else "?") for n in names[:2])
                if names else "TBD"
            )
            phase = nxt.get("tournament_phase") or "LEAGUE"
            st.caption(f"▶ **Round {rnd}** ({phase}): {matchup}")

        # Show last 3 completed + next 3 pending (compact preview)
        recent = [s for s in field_sessions if s.get("result_submitted")][-3:]
        upcoming = pending[:3]
        for s in recent + upcoming:
            render_session_cell(s)

        leftover = total - len(recent) - min(len(pending), 3)
        if leftover > 0:
            st.caption(f"_{leftover} more match(es) not shown_")


def _render_campus_block(
    campus_name: str,
    campus_data: Dict[str, Any],
    *,
    field_filter: Optional[int] = None,
) -> None:
    """Render one campus block (header + field cards).

    When *field_filter* is set only that field number is shown (instructor RBAC).
    """
    fields_dict: Dict[int, List] = dict(campus_data["fields"])

    if field_filter is not None:
        fields_dict = {k: v for k, v in fields_dict.items() if k == field_filter}

    if not fields_dict:
        return

    campus_sessions = [s for slist in fields_dict.values() for s in slist]
    campus_done = sum(1 for s in campus_sessions if s.get("result_submitted"))
    campus_total = len(campus_sessions)
    campus_pct = int(campus_done / campus_total * 100) if campus_total else 0
    n_fields = len(fields_dict)

    # Campus header card
    st.markdown(
        f"<div style='{_CAMPUS_CARD_CSS}'>"
        f"🏟️ {campus_name}"
        f"<span style='font-weight:400;font-size:.85em;margin-left:16px;opacity:.9'>"
        f"{n_fields} field(s)&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"{campus_done}/{campus_total} matches ({campus_pct}%)"
        f"</span></div>",
        unsafe_allow_html=True,
    )

    with st.container():
        for field_num in sorted(fields_dict.keys()):
            _render_field_card(field_num, fields_dict[field_num])

    st.markdown("")  # spacing after campus block


def render_campus_field_grid(
    sessions: List[Dict[str, Any]],
    campus_configs: List[Dict[str, Any]],
    rankings: List[Dict[str, Any]] = None,
    *,
    viewer_role: str = "admin",
    campus_filter: Optional[str] = None,
    field_filter: Optional[int] = None,
) -> None:
    """Render sessions grouped by Campus → Field (structural RBAC view).

    Admin  (viewer_role="admin"):
        All campuses visible, all fields visible.

    Instructor (viewer_role="instructor"):
        Only the campus matching *campus_filter* and the field matching
        *field_filter* are shown.  When both are None the full view is
        shown as a fallback (e.g. before the instructor has made a selection).

    Falls back to the phase-based ``render_campus_grid()`` when sessions carry
    no ``structure_config.field_number`` (e.g. INDIVIDUAL_RANKING tournaments).

    Args:
        sessions:       All tournament sessions.
        campus_configs: Per-campus config from GET /tournaments/{id}/campus-schedules.
        rankings:       Tournament rankings (optional, unused but kept for API parity).
        viewer_role:    "admin" or "instructor".
        campus_filter:  Restrict to this campus name (instructor RBAC).
        field_filter:   Restrict to this field number (instructor RBAC).
    """
    if not sessions:
        st.info("No sessions generated yet.")
        return

    # Check whether sessions carry field numbers at all
    has_field_nums = any(
        (s.get("structure_config") or {}).get("field_number") is not None
        for s in sessions
    )
    if not has_field_nums:
        # No field structure → fall back to phase-based view
        render_campus_grid(sessions, campus_configs, rankings or [])
        return

    campus_map = build_campus_field_map(sessions, campus_configs)
    if not campus_map:
        render_campus_grid(sessions, campus_configs, rankings or [])
        return

    # RBAC: instructor sees only their campus
    if viewer_role == "instructor" and campus_filter is not None:
        campus_map = {k: v for k, v in campus_map.items() if k == campus_filter}

    if not campus_map:
        st.warning("No sessions found for your assigned campus.")
        return

    for campus_name, campus_data in campus_map.items():
        _render_campus_block(
            campus_name,
            campus_data,
            field_filter=field_filter if viewer_role == "instructor" else None,
        )
