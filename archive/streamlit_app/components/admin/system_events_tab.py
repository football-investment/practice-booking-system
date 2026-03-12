"""
System Events admin panel.

Shows structured business/security events emitted by application logic.
Distinct from audit_logs (HTTP trail) — these are deliberate, queryable
records for operational review.

Features:
  - Filter by level: SECURITY / WARNING / INFO
  - Filter by resolved status: open / resolved / all
  - Server-side pagination (page size 50)
  - Mark individual events as resolved / reopen
  - Time-ordered (newest first)
  - Retention purge button (deletes resolved events older than N days)
"""

import streamlit as st
from typing import Any, Dict, List, Optional

from api_helpers_system_events import (
    get_system_events,
    resolve_system_event,
    unresolve_system_event,
    purge_system_events,
)

_PAGE_SIZE = 50

# ── Level badge labels ─────────────────────────────────────────────────────────
_LEVEL_BADGE = {
    "SECURITY": "🔴 SECURITY",
    "WARNING":  "🟡 WARNING",
    "INFO":     "🔵 INFO",
}


def _badge(level: str) -> str:
    return _LEVEL_BADGE.get(level, level)


def _render_event_row(token: str, event: Dict[str, Any]) -> None:
    """Render a single system event as a compact card."""
    level = event.get("level", "INFO")
    resolved = event.get("resolved", False)
    event_id = event.get("id")

    with st.container(border=True):
        left, right = st.columns([5, 1])

        with left:
            st.markdown(
                f"**{_badge(level)}** &nbsp;|&nbsp; "
                f"`{event.get('event_type', '—')}` &nbsp;|&nbsp; "
                f"_{event.get('created_at', '')[:19].replace('T', ' ')}_"
            )

            uid = event.get("user_id")
            role = event.get("role") or "—"
            st.caption(f"user_id={uid if uid else 'anonymous'}  •  role={role}")

            payload = event.get("payload_json")
            if payload:
                with st.expander("Details (payload)", expanded=False):
                    st.json(payload)

            if resolved:
                st.success("Resolved", icon="✅")

        with right:
            if resolved:
                if st.button("Reopen", key=f"unres_{event_id}", use_container_width=True):
                    ok, err, _ = unresolve_system_event(token, event_id)
                    if ok:
                        st.rerun()
                    else:
                        st.error(err)
            else:
                if st.button("Resolve", key=f"res_{event_id}",
                             use_container_width=True, type="primary"):
                    ok, err, _ = resolve_system_event(token, event_id)
                    if ok:
                        st.rerun()
                    else:
                        st.error(err)


def render_system_events_tab(token: str, user: Dict[str, Any]) -> None:
    """
    Main entry point — renders the full System Events panel.
    Called from Admin_Dashboard.py when active_tab == 'system_events'.
    """
    st.header("System Events")
    st.caption(
        "Structured business and security events — separate from audit_logs "
        "(automatic HTTP trail). Retention: **90 days** "
        "(resolved events only); open events are kept until an admin resolves them."
    )

    # ── Filters ────────────────────────────────────────────────────────────────
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        level_options = ["All", "SECURITY", "WARNING", "INFO"]
        selected_level = st.selectbox(
            "Level", options=level_options, index=0, key="sysevt_level"
        )

    with filter_col2:
        resolved_map = {"Open only": False, "Resolved only": True, "All": None}
        selected_resolved_label = st.selectbox(
            "Status", options=list(resolved_map.keys()), index=0, key="sysevt_resolved"
        )
        selected_resolved = resolved_map[selected_resolved_label]

    with filter_col3:
        # Page navigation — stored in session state
        if "sysevt_page" not in st.session_state:
            st.session_state.sysevt_page = 0

    st.divider()

    # ── Fetch ──────────────────────────────────────────────────────────────────
    page = st.session_state.get("sysevt_page", 0)
    level_param = None if selected_level == "All" else selected_level
    offset = page * _PAGE_SIZE

    ok, err, data = get_system_events(
        token,
        level=level_param,
        resolved=selected_resolved,
        limit=_PAGE_SIZE,
        offset=offset,
    )

    if not ok:
        if err == "SESSION_EXPIRED":
            st.error("Session expired. Please log in again.")
        else:
            st.error(f"Failed to load events: {err}")
        return

    items: List[Dict[str, Any]] = data.get("items", [])
    total: int = data.get("total", 0)
    total_pages = max(1, -(-total // _PAGE_SIZE))  # ceiling division

    # ── Summary metrics ────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total records", total)
    m2.metric("Page", f"{page + 1} / {total_pages}")
    m3.metric("Shown", len(items))
    open_count = sum(1 for e in items if not e.get("resolved"))
    m4.metric("Open (this page)", open_count)

    # ── Pagination controls ────────────────────────────────────────────────────
    pg_left, pg_center, pg_right = st.columns([1, 3, 1])
    with pg_left:
        if st.button("◀ Previous", disabled=page == 0, use_container_width=True):
            st.session_state.sysevt_page = max(0, page - 1)
            st.rerun()
    with pg_center:
        st.caption(f"Page {page + 1} / {total_pages}  •  {total} total records")
    with pg_right:
        if st.button("Next ▶", disabled=page >= total_pages - 1,
                     use_container_width=True):
            st.session_state.sysevt_page = page + 1
            st.rerun()

    st.divider()

    if not items:
        st.info("No events match the current filters.")
    else:
        for event in items:
            _render_event_row(token, event)

    # ── Retention purge section ────────────────────────────────────────────────
    st.divider()
    with st.expander("Maintenance — delete old events", expanded=False):
        st.warning(
            "**Warning:** This action permanently deletes **resolved** events older than "
            "the specified number of days. Open events are never deleted automatically.",
            icon="⚠️",
        )
        retention = st.number_input(
            "Retention (days)",
            min_value=7,
            max_value=3650,
            value=90,
            step=30,
            key="sysevt_retention",
            help="Resolved events older than this will be permanently deleted.",
        )
        if st.button("Run purge", type="primary", key="sysevt_purge"):
            ok, err, result = purge_system_events(token, retention_days=int(retention))
            if ok:
                deleted = result.get("deleted", 0)
                st.success(
                    f"Done. **{deleted}** record(s) deleted "
                    f"(resolved events older than {int(retention)} days)."
                )
                st.rerun()
            else:
                st.error(f"Error: {err}")
