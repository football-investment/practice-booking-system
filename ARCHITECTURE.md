# LFA Practice Booking System — Architecture Overview

> Last updated: 2026-02-17
> Status: Post-cleanup (48h stability gate passed)

---

## Tournament Handling — Unified Architecture

Tournament management is unified under a single entry point with role-based permissions.
**No inline `if role == "admin":` checks exist in rendering code.**
All capability branching goes through `TournamentManagerPermissions`.

### Entry point

```
pages/Tournament_Manager.py          ← Canonical entry for all roles
```

Both dashboards surface this page via a sidebar button:

```
Admin Dashboard sidebar    →  🏆 Tournament Manager  (pages/Tournament_Manager.py)
Instructor Dashboard sidebar →  🏆 Tournament Manager  (pages/Tournament_Manager.py)
```

### Role permissions

Defined in one place: `streamlit_app/components/admin/tournament_manager_permissions.py`

| Role | can_create | can_enter_results | can_finalize |
|---|:---:|:---:|:---:|
| admin | ✅ | ✅ | ✅ |
| instructor | ❌ | ✅ | ❌ |

```python
# Usage pattern (Tournament_Manager.py)
perms = get_permissions(role)         # None if role not allowed
render_tournament_manager(token, perms)
```

### Rendering layer

```
components/admin/tournament_monitor.py
  render_tournament_manager(token, perms)   ← role-aware entry point
  render_tournament_monitor(token)          ← backward-compat wrapper (admin-only)

components/admin/tournament_card/
  leaderboard.py      render_leaderboard(rankings, ...)
  result_entry.py     render_manual_result_entry(token, tid, sessions)
  session_grid.py     render_phase_grid / render_campus_grid
  utils.py            phase_icon, phase_label, phase_label_short

components/admin/ops_wizard/
  __init__.py         render_wizard(), render_wizard_progress()
  wizard_state.py     init_wizard_state(), reset_wizard_state()
  launch.py           execute_launch()
  steps/
    step1_scenario.py … step8_review.py
```

### Legacy / archived

```
pages/_DEPRECATED_Tournament_Monitor.py   ← archived (removed from auto-discovery);
                                             was superseded by Tournament_Manager.py
```

---

## Match Command Center (MCC)

Used by instructors for live match management (attendance + result entry).

### Access path

**Canonical:** `Instructor Dashboard sidebar → 🏆 Tournament Manager`
Role-gated, uses `render_manual_result_entry` from `tournament_card/result_entry.py`.

The legacy embedded "⚽ Match Command Center" sub-tab in `Instructor_Dashboard.py`
now shows a redirect button to the Tournament Manager (no longer renders MCC inline).

### Key files

```
components/tournaments/instructor/
  match_command_center.py           ← main view; _match_to_session_dict adapter
  match_command_center_helpers.py   ← API wrappers (get_active_match unwraps envelope)
  match_command_center_screens.py   ← render_attendance_step only (all other functions removed)
```

### API envelope contract

`GET /api/v1/tournaments/{tid}/active-match` returns an envelope:
```json
{
  "active_match": { "session_id": ..., "match_participants": [...], ... } | null,
  "upcoming_matches": [...],
  "tournament_id": ...
}
```

`get_active_match()` unwraps this and returns the inner `active_match` dict (or `None`).

`_match_to_session_dict()` adapts the inner dict to the flat session format expected by
`render_manual_result_entry`:

| active_match field | session dict key |
|---|---|
| `session_id` | `id` |
| `match_participants[].user_id` | `participant_user_ids` |
| `match_participants[].name` | `participant_names` |
| `game_results is not None` | `result_submitted` |
| all others | same key |

---

## Leaderboard — Shared Component

```
components/admin/tournament_card/leaderboard.py
  render_leaderboard(rankings, status, has_knockout, scoring_type, is_individual_ranking)
```

Called from:
- `tournament_monitor.py` — admin tournament cards
- `match_command_center.py` — MCC sidebar + final leaderboard
- (future) any page needing tournament standings

Data source: `GET /api/v1/tournaments/{tid}/rankings` (flat list, not `/leaderboard`)

---

## Scoring types & format detection

`match_format` is the **sole authoritative signal** for format branching.
`tournament_phase` tracks phase progress only — never used for format detection.

```
match_format == "INDIVIDUAL_RANKING"  →  IR result entry
match_format == "HEAD_TO_HEAD"        →  H2H result entry
match_format == "TEAM_MATCH"          →  team result entry
```

For ROUNDS_BASED IR sessions, the underlying measurement type is in
`structure_config.scoring_method` (unwrap ROUNDS_BASED → TIME_BASED / SCORE_BASED / etc.)

---

## Frontend page registry

All pages are in `streamlit_app/pages/` (Streamlit multi-page auto-discovery):

| Page | Role | Status |
|---|---|---|
| `Admin_Dashboard.py` | admin | Active |
| `Instructor_Dashboard.py` | instructor | Active (monolit — modularization planned) |
| `Tournament_Manager.py` | admin, instructor | Active — **canonical tournament entry point** |
| `_DEPRECATED_Tournament_Monitor.py` | admin | Archived — not in auto-discovery |
| `LFA_Player_Dashboard.py` | student | Active |
| `LFA_Player_Onboarding.py` | student | Active |
| `My_Credits.py` | student | Active |
| `My_Profile.py` | student | Active |
| `Specialization_Hub.py` | student | Active |
| `Specialization_Info.py` | student | Active |

---

## Planned next steps

### 48-hour stability gate — COMPLETED (2026-02-17)

All gate items resolved:
- [x] Removed deprecated `# DEPRECATED` comment blocks from `match_command_center.py`
- [x] Removed all dead functions from `match_command_center_screens.py` (only `render_attendance_step` remains)
- [x] Replaced MCC embedded tab in `Instructor_Dashboard.py` with redirect to Tournament Manager
- [x] Archived `pages/Tournament_Monitor.py` → `pages/_DEPRECATED_Tournament_Monitor.py`

### Phase 3 — Instructor_Dashboard.py modularization

**Status:** Ready to start. Clean baseline established by Phase 2.

`Instructor_Dashboard.py` is a 1400+ line monolit: 7 tabs, 2 dialogs, a shared
data-fetch block at the top, and the full sidebar in-file.

#### Prerequisite

Full E2E regression suite for instructor flows **must** exist before extraction.
Minimum coverage:
- Today & Upcoming tab renders without error
- My Jobs tab renders without error
- Tournament Applications tab → redirect button → Tournament Manager navigates
- Check-in tab renders without error
- Sidebar: Tournament Manager, Refresh, Logout buttons all present

The smoke tests in `tests_e2e/test_tournament_manager_sidebar_nav.py` cover the
sidebar. Tab-level smoke tests must be added before the first extraction step.

#### Target structure

```
streamlit_app/
  pages/
    Instructor_Dashboard.py        ← slim orchestrator (~60 lines)
  components/instructor/
    dashboard_header.py            auth check, page_config, sidebar render
    data_loader.py                 shared data fetch (sessions, semesters, grouping)
    tabs/
      __init__.py
      tab1_today.py                Today & Upcoming (todays_sessions, upcoming_sessions)
      tab2_jobs.py                 My Jobs (active_jobs, completed_jobs)
      tab3_tournaments.py          Tournament Applications (4 sub-tabs)
      tab4_students.py             My Students
      tab5_checkin.py              Check-in & Groups
      tab6_inbox.py                Inbox
      tab7_profile.py              My Profile
    dialogs/
      __init__.py
      record_results.py            show_record_results_dialog()
      complete_tournament.py       show_complete_tournament_dialog()
```

#### Slim orchestrator shape (target)

```python
# pages/Instructor_Dashboard.py — after Phase 3
from components.instructor.dashboard_header import render_dashboard_header
from components.instructor.data_loader import load_dashboard_data
from components.instructor.tabs import (
    render_today_tab, render_jobs_tab, render_tournaments_tab,
    render_students_tab, render_checkin_tab, render_inbox_tab, render_profile_tab,
)

token, user = render_dashboard_header()
data = load_dashboard_data(token)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([...])
with tab1: render_today_tab(data)
with tab2: render_jobs_tab(token, user, data)
# …
```

#### Shared data contract (data_loader.py)

All tabs receive a single `DashboardData` object (dataclass or TypedDict) containing:

```python
@dataclass
class DashboardData:
    all_sessions: list
    all_semesters: list
    seasons_by_semester: dict
    tournaments_by_semester: dict
    upcoming_sessions: list
    todays_sessions: list
```

This eliminates the current pattern of each tab re-fetching or reaching into
module-level globals.

#### Extraction order (low → high risk)

| Step | File | Risk | Prerequisite |
|------|------|------|--------------|
| 3.1 | `tab7_profile.py` | Low — fully self-contained | Smoke test for profile tab |
| 3.2 | `tab6_inbox.py` | Low — reads notifications only | Smoke test for inbox tab |
| 3.3 | `tab4_students.py` | Low — read-only list | Smoke test for students tab |
| 3.4 | `data_loader.py` | Medium — shared state boundary | All tab tests green |
| 3.5 | `tab1_today.py` | Medium — uses `todays_sessions` | data_loader extracted |
| 3.6 | `tab2_jobs.py` | Medium — uses `seasons_by_semester` | data_loader extracted |
| 3.7 | `tab5_checkin.py` | Medium — uses render_session_checkin | Component import audit |
| 3.8 | `tab3_tournaments.py` | High — 4 sub-tabs, MCC redirect | All other tabs extracted |
| 3.9 | `dashboard_header.py` | High — auth + page config | Full E2E regression pass |
| 3.10 | `dialogs/` | Low (if dialogs are currently `@st.dialog`) | After header extracted |

Each step = one commit. Roll back is safe per step.

#### Risk factors

- `todays_sessions` and `upcoming_sessions` are computed in the data-prep block and
  referenced in multiple tabs — must be in `DashboardData` before any tab is extracted.
- `tab3_tournaments.py` imports from `components.instructor.tournament_applications`
  and `components.tournaments.instructor.*` — import audit required.
- `all_semesters` is used in both `tab2_jobs.py` and `tab3_tournaments.py` —
  the shared data contract is critical here.

#### Not in scope for Phase 3

- Redesign of tab content (UX/feature work)
- Removing the inline `requests` calls inside tabs (follow-up: migrate to `api_client`)
- Admin Dashboard restructuring
