"""
Instructor Dashboard — Tab Components
======================================

Phase 3 skeleton.  Each tab module will be extracted here following the
10-step order in ARCHITECTURE.md §Phase 3.

Extraction order (low → high risk):
    3.1  tab7_profile.py      — self-contained, no shared data
    3.2  tab6_inbox.py        — notifications only
    3.3  tab4_students.py     — read-only list
    3.4  data_loader.py       — shared data boundary (prerequisite for 3.5+)
    3.5  tab1_today.py        — uses todays_sessions / upcoming_sessions
    3.6  tab2_jobs.py         — uses seasons_by_semester
    3.7  tab5_checkin.py      — uses render_session_checkin
    3.8  tab3_tournaments.py  — 4 sub-tabs + MCC redirect (highest risk)
    3.9  dashboard_header.py  — auth + page config
    3.10 dialogs/             — record_results, complete_tournament

Status: skeleton only — no tab modules extracted yet.
"""
