"""
⚠️ Enrollment Conflict Warning Component
=========================================
Displays session time conflicts before enrollment

Shows:
- Time overlap conflicts (blocking severity)
- Travel time conflicts (warning severity)
- User confirmation before enrollment
"""
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime


def display_conflict_warning(
    conflicts: List[Dict],
    semester_name: str,
    enrollment_type: str
) -> bool:
    """
    Display conflict warnings and get user confirmation.

    Args:
        conflicts: List of conflict dictionaries from API
        semester_name: Name of semester user wants to enroll in
        enrollment_type: "TOURNAMENT", "MINI_SEASON", or "ACADEMY_SEASON"

    Returns:
        bool: True if user confirms enrollment despite conflicts, False otherwise
    """
    if not conflicts:
        return True  # No conflicts, proceed

    # Separate conflicts by severity
    blocking_conflicts = [c for c in conflicts if c.get("severity") == "blocking"]
    warning_conflicts = [c for c in conflicts if c.get("severity") == "warning"]

    # Display warning container
    st.markdown("""
    <style>
        .conflict-warning-container {
            background: #fef3c7;
            border: 2px solid #f59e0b;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        }

        .conflict-blocking {
            background: #fee2e2;
            border-left: 4px solid #dc2626;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
        }

        .conflict-warning {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
        }

        .conflict-title {
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
            color: #78350f;
        }

        .conflict-blocking .conflict-title {
            color: #991b1b;
        }

        .conflict-detail {
            font-size: 0.95rem;
            margin: 0.25rem 0;
        }

        .time-detail {
            font-weight: 600;
            color: #1e40af;
        }
    </style>
    """, unsafe_allow_html=True)

    # Warning header
    st.warning(f"⚠️ **FIGYELMEZTETÉS**: Ütközéseket észleltünk a(z) **{semester_name}** beíratásnál!")

    # Display blocking conflicts
    if blocking_conflicts:
        st.markdown("### 🚫 Időbeli Ütközések (Kritikus)")
        st.markdown("""
        **Ezek a sessionök pontosan ugyanabban az időben vannak.**
        Nem tudsz két helyen egyszerre lenni! Kérjük, válassz az egyik közül.
        """)

        for i, conflict in enumerate(blocking_conflicts, 1):
            existing = conflict.get("existing_session", {})
            new = conflict.get("new_semester_session", {})

            st.markdown(f"""
            <div class="conflict-blocking">
                <div class="conflict-title">Ütközés #{i}: {existing.get('date', 'N/A')}</div>

                <div class="conflict-detail">
                    📍 <strong>Meglévő foglalás:</strong> {existing.get('semester_name', 'N/A')}
                </div>
                <div class="conflict-detail time-detail">
                    🕒 {existing.get('start_time', 'N/A')} - {existing.get('end_time', 'N/A')}
                </div>
                <div class="conflict-detail">
                    🏟️ {existing.get('location', {}).get('location_city', 'N/A')} - {existing.get('location', {}).get('campus_name', 'N/A')}
                </div>

                <hr style="margin: 0.75rem 0; border-color: #fca5a5;">

                <div class="conflict-detail">
                    📍 <strong>Új program:</strong> {new.get('semester_name', 'N/A')}
                </div>
                <div class="conflict-detail time-detail">
                    🕒 {new.get('start_time', 'N/A')} - {new.get('end_time', 'N/A')}
                </div>
                <div class="conflict-detail">
                    🏟️ {new.get('location', {}).get('location_city', 'N/A')} - {new.get('location', {}).get('campus_name', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Display travel time conflicts
    if warning_conflicts:
        st.markdown("### ⏱️ Utazási Idő Figyelmeztetések")
        st.markdown("""
        **Ezek a sessionök szorosan követik egymást különböző helyszíneken.**
        Ellenőrizd, hogy lesz-e elég időd utazni a két helyszín között!
        """)

        for i, conflict in enumerate(warning_conflicts, 1):
            existing = conflict.get("existing_session", {})
            new = conflict.get("new_semester_session", {})

            st.markdown(f"""
            <div class="conflict-warning">
                <div class="conflict-title">Figyelmeztetés #{i}: {existing.get('date', 'N/A')}</div>

                <div class="conflict-detail">
                    📍 <strong>Előző session:</strong> {existing.get('semester_name', 'N/A')}
                </div>
                <div class="conflict-detail time-detail">
                    🕒 Vége: {existing.get('end_time', 'N/A')}
                </div>
                <div class="conflict-detail">
                    🏟️ {existing.get('location', {}).get('location_city', 'N/A')} - {existing.get('location', {}).get('campus_name', 'N/A')}
                </div>

                <hr style="margin: 0.75rem 0; border-color: #fbbf24;">

                <div class="conflict-detail">
                    📍 <strong>Következő session:</strong> {new.get('semester_name', 'N/A')}
                </div>
                <div class="conflict-detail time-detail">
                    🕒 Kezdés: {new.get('start_time', 'N/A')}
                </div>
                <div class="conflict-detail">
                    🏟️ {new.get('location', {}).get('location_city', 'N/A')} - {new.get('location', {}).get('campus_name', 'N/A')}
                </div>

                <div style="margin-top: 0.75rem; padding: 0.5rem; background: white; border-radius: 6px;">
                    💡 <strong>Tipp:</strong> Kevesebb mint 30 perc van a két session között. Számolj az utazási idővel!
                </div>
            </div>
            """, unsafe_allow_html=True)

    # User confirmation
    st.markdown("---")

    if blocking_conflicts:
        st.error("""
        **🚫 KRITIKUS ÜTKÖZÉSEK TALÁLHATÓK!**

        Ennek ellenére beíratkozhatsz, de tudnod kell, hogy **nem tudsz mindkét helyen megjelenni**.
        Kérjük, töröld az egyik foglalást, vagy válassz másik időpontot!
        """)

        confirm = st.checkbox(
            "✅ Megértettem az ütközéseket, és felvállalom a felelősséget. Beíratást engedélyezem.",
            key=f"confirm_blocking_{semester_name}"
        )
        return confirm

    elif warning_conflicts:
        st.warning("""
        **⚠️ UTAZÁSI IDŐ FIGYELMEZTETÉSEK**

        Találtunk sessionöket, amelyek szorosan követik egymást különböző helyszíneken.
        Mielőtt beíratkozsz, **ellenőrizd az utazási időt** a két helyszín között!
        """)

        confirm = st.checkbox(
            "✅ Ellenőriztem az utazási időt, folytathatom a beíratást.",
            key=f"confirm_travel_{semester_name}"
        )
        return confirm

    return True


def display_schedule_conflicts_summary(schedule_data: Dict) -> None:
    """
    Display a summary of user's complete schedule with conflict highlights.

    Args:
        schedule_data: Schedule data from API (get_user_schedule endpoint)
    """
    if not schedule_data:
        st.info("Nincs aktív beíratásod.")
        return

    enrollments = schedule_data.get("enrollments", [])
    total_sessions = schedule_data.get("total_sessions", 0)

    if total_sessions == 0:
        st.info("Nincs foglalt session a megadott időszakra.")
        return

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #3b82f6 0%, #1e3a8a 100%);
                padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: white;">📅 Menetrendem</h3>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            Összesen <strong>{total_sessions} session</strong> |
            <strong>{len(enrollments)} aktív beíratás</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Group sessions by enrollment type
    tournaments = []
    mini_seasons = []
    academy_seasons = []

    for enrollment in enrollments:
        enrollment_type = enrollment.get("enrollment_type", "OTHER")
        if enrollment_type == "TOURNAMENT":
            tournaments.append(enrollment)
        elif enrollment_type == "MINI_SEASON":
            mini_seasons.append(enrollment)
        elif enrollment_type == "ACADEMY_SEASON":
            academy_seasons.append(enrollment)

    # Display by tabs
    tab1, tab2, tab3 = st.tabs(["🏆 Tornák", "📅 Mini Szezonok", "🏫 Academy Szezon"])

    with tab1:
        if tournaments:
            for enrollment in tournaments:
                _display_enrollment_schedule(enrollment)
        else:
            st.info("Nincs aktív torna beíratásod.")

    with tab2:
        if mini_seasons:
            for enrollment in mini_seasons:
                _display_enrollment_schedule(enrollment)
        else:
            st.info("Nincs aktív Mini Szezon beíratásod.")

    with tab3:
        if academy_seasons:
            for enrollment in academy_seasons:
                _display_enrollment_schedule(enrollment)
        else:
            st.info("Nincs aktív Academy Szezon beíratásod.")


def _display_enrollment_schedule(enrollment: Dict) -> None:
    """Helper: Display schedule for a single enrollment"""
    semester_name = enrollment.get("semester_name", "N/A")
    sessions = enrollment.get("sessions", [])

    with st.expander(f"📖 {semester_name} ({len(sessions)} session)", expanded=False):
        if not sessions:
            st.info("Nincs elérhető session.")
            return

        for session in sessions:
            is_booked = session.get("is_booked", False)
            date_str = session.get("date", "N/A")
            start_time = session.get("start_time", "N/A")
            end_time = session.get("end_time", "N/A")
            location = session.get("location", {})

            status_icon = "✅" if is_booked else "⭕"
            status_text = "Foglalt" if is_booked else "Nem foglalt"

            st.markdown(f"""
            <div style="background: {'#d1fae5' if is_booked else '#f3f4f6'};
                        padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <div style="font-weight: 600; margin-bottom: 0.25rem;">
                    {status_icon} {date_str} | {start_time} - {end_time}
                </div>
                <div style="font-size: 0.9rem; color: #6b7280;">
                    📍 {location.get('location_city', 'N/A')} - {location.get('campus_name', 'N/A')}
                </div>
                <div style="font-size: 0.85rem; color: #9ca3af; margin-top: 0.25rem;">
                    {status_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
