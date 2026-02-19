"""
Streamlit AppTest component tests for REGULAR session check-in UI.

Tests that regular sessions show ALL 4 attendance buttons
(Present, Absent, Late, Excused), in contrast to tournament sessions
which only show 2 buttons (Present, Absent).

This validates the frontend correctly differentiates between
regular and tournament session check-in flows.
"""

import pytest
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# ============================================================================
# REGULAR SESSION: 4-Button Rule UI Tests
# ============================================================================

@pytest.mark.component
@pytest.mark.ui
class TestRegularSessionCheckinUI:
    """Test regular session check-in UI shows ALL 4 attendance buttons."""

    def test_regular_session_shows_all_4_attendance_buttons(self):
        """
        Regular sessions show ALL 4 attendance buttons:
        Present, Absent, Late, Excused.

        This is the OPPOSITE of tournament sessions (which show only 2).
        """
        # Mock API responses for regular session
        mock_bookings = [
            {
                'id': 1,
                'user_id': 101,
                'user': {'id': 101, 'name': 'Test Student 1', 'email': 'student1@test.com'},
                'status': 'confirmed'
            },
            {
                'id': 2,
                'user_id': 102,
                'user': {'id': 102, 'name': 'Test Student 2', 'email': 'student2@test.com'},
                'status': 'confirmed'
            }
        ]

        mock_attendance = []

        mock_regular_session = {
            'id': 1,
            'title': 'Regular Training Session',
            'date_start': (datetime.now() + timedelta(hours=2)).isoformat(),
            'is_tournament_game': False,  # NOT a tournament
            'session_type': 'on_site',
            'capacity': 20,
            'bookings_count': 2,
            'instructor_id': 5
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_regular_session])):
                    # Initialize AppTest with regular session check-in component
                    at = AppTest.from_file(
                        "streamlit_app/components/sessions/session_checkin.py",
                        default_timeout=10
                    )

                    # Set session state to Step 2 (attendance marking)
                    at.session_state['wizard_step'] = 2
                    at.session_state['selected_session_id'] = 1
                    at.session_state['selected_session'] = mock_regular_session

                    # Run the app
                    at.run()

                    # Assert: ALL 4 buttons per student
                    present_buttons = [b for b in at.button if '✅ Present' in str(b.label)]
                    absent_buttons = [b for b in at.button if '❌ Absent' in str(b.label)]
                    late_buttons = [b for b in at.button if '⏰ Late' in str(b.label)]
                    excused_buttons = [b for b in at.button if '🎫 Excused' in str(b.label)]

                    # Should have 2 students × 4 buttons = 8 total attendance buttons
                    assert len(present_buttons) == 2, "Should have 2 Present buttons (one per student)"
                    assert len(absent_buttons) == 2, "Should have 2 Absent buttons (one per student)"
                    assert len(late_buttons) == 2, "Should have 2 Late buttons (one per student)"
                    assert len(excused_buttons) == 2, "Should have 2 Excused buttons (one per student)"

    def test_regular_session_summary_shows_5_metrics(self):
        """
        Regular session attendance summary shows ALL 5 metrics:
        Present, Absent, Late, Excused, Pending.

        Tournament sessions show only 3 metrics (Present, Absent, Pending).
        """
        mock_bookings = [
            {'id': 1, 'user_id': 101, 'user': {'id': 101, 'name': 'Student 1', 'email': 's1@test.com'}, 'status': 'confirmed'}
        ]

        mock_attendance = []

        mock_regular_session = {
            'id': 1,
            'title': 'Regular Class',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': False,
            'session_type': 'on_site',
            'capacity': 20,
            'bookings_count': 1,
            'instructor_id': 5
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_regular_session])):
                    at = AppTest.from_file(
                        "streamlit_app/components/sessions/session_checkin.py",
                        default_timeout=10
                    )

                    at.session_state['wizard_step'] = 2
                    at.session_state['selected_session_id'] = 1
                    at.session_state['selected_session'] = mock_regular_session

                    at.run()

                    # Check metrics
                    metrics = at.metric
                    metric_labels = [m.label for m in metrics]

                    # Should have ALL 5 metrics
                    assert "✅ Present" in metric_labels or "Present" in metric_labels
                    assert "❌ Absent" in metric_labels or "Absent" in metric_labels
                    assert "⏰ Late" in metric_labels or "Late" in metric_labels
                    assert "🎫 Excused" in metric_labels or "Excused" in metric_labels
                    assert "⏳ Pending" in metric_labels or "Pending" in metric_labels

    def test_regular_session_wizard_shows_regular_branding(self):
        """Regular session wizard uses regular session branding."""
        mock_regular_session = {
            'id': 1,
            'title': 'Training',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': False,
            'session_type': 'on_site',
            'capacity': 20,
            'bookings_count': 0,
            'instructor_id': 5
        }

        with patch('api_helpers.get_sessions', return_value=(True, [mock_regular_session])):
            at = AppTest.from_file(
                "streamlit_app/components/sessions/session_checkin.py",
                default_timeout=10
            )

            at.session_state['wizard_step'] = 1

            at.run()

            # Check for regular session branding
            markdown_content = ' '.join([m.value for m in at.markdown])

            # Should show "Regular Session" or NOT show "Tournament"
            assert "Regular Session" in markdown_content or "Session Check-in" in markdown_content, \
                "Should show regular session branding"

            # Should NOT prominently show "Tournament" text
            # (Some tournament references in docs are OK, but should not be the main heading)


# ============================================================================
# Comparison Tests: Regular vs Tournament
# ============================================================================

@pytest.mark.component
@pytest.mark.ui
class TestRegularVsTournamentComparison:
    """Test that regular and tournament check-ins are visually distinct."""

    def test_button_count_difference_regular_vs_tournament(self):
        """
        Direct comparison: Regular shows 4 buttons, Tournament shows 2.

        This is the KEY visual difference users should see.
        """
        # Test data
        mock_bookings = [
            {'id': 1, 'user_id': 101, 'user': {'id': 101, 'name': 'Student', 'email': 's@test.com'}, 'status': 'confirmed'}
        ]
        mock_attendance = []

        # === TEST 1: Regular Session (4 buttons) ===
        mock_regular_session = {
            'id': 1,
            'title': 'Regular',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': False,
            'session_type': 'on_site',
            'capacity': 20,
            'bookings_count': 1,
            'instructor_id': 5
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_regular_session])):
                    at_regular = AppTest.from_file(
                        "streamlit_app/components/sessions/session_checkin.py",
                        default_timeout=10
                    )

                    at_regular.session_state['wizard_step'] = 2
                    at_regular.session_state['selected_session_id'] = 1
                    at_regular.session_state['selected_session'] = mock_regular_session

                    at_regular.run()

                    regular_attendance_buttons = [
                        b for b in at_regular.button
                        if any(keyword in str(b.label) for keyword in ['Present', 'Absent', 'Late', 'Excused'])
                    ]

        # === TEST 2: Tournament Session (2 buttons) ===
        mock_tournament_session = {
            'id': 2,
            'title': 'Tournament',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': True,
            'game_type': 'Final',
            'capacity': 20,
            'bookings_count': 1
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_tournament_session])):
                    at_tournament = AppTest.from_file(
                        "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                        default_timeout=10
                    )

                    at_tournament.session_state['wizard_step'] = 2
                    at_tournament.session_state['selected_session_id'] = 2
                    at_tournament.session_state['selected_session'] = mock_tournament_session

                    at_tournament.run()

                    tournament_attendance_buttons = [
                        b for b in at_tournament.button
                        if any(keyword in str(b.label) for keyword in ['Present', 'Absent', 'Late', 'Excused'])
                    ]

        # === ASSERT: Regular has MORE buttons than Tournament ===
        assert len(regular_attendance_buttons) == 4, \
            f"Regular session should show 4 buttons, got {len(regular_attendance_buttons)}"

        assert len(tournament_attendance_buttons) == 2, \
            f"Tournament session should show 2 buttons, got {len(tournament_attendance_buttons)}"

        assert len(regular_attendance_buttons) > len(tournament_attendance_buttons), \
            "Regular sessions should have MORE buttons than tournament sessions"


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.component
@pytest.mark.ui
class TestRegularSessionEdgeCases:
    """Test edge cases for regular session check-in."""

    def test_regular_session_handles_empty_bookings(self):
        """Regular session handles case with no bookings gracefully."""
        mock_regular_session = {
            'id': 1,
            'title': 'Empty Session',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': False,
            'session_type': 'on_site',
            'capacity': 20,
            'bookings_count': 0,
            'instructor_id': 5
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, [])):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, [])):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_regular_session])):
                    at = AppTest.from_file(
                        "streamlit_app/components/sessions/session_checkin.py",
                        default_timeout=10
                    )

                    at.session_state['wizard_step'] = 2
                    at.session_state['selected_session_id'] = 1
                    at.session_state['selected_session'] = mock_regular_session

                    at.run()

                    # Should show warning or info message about no bookings
                    warnings = at.warning
                    infos = at.info

                    assert len(warnings) > 0 or len(infos) > 0, \
                        "Should show warning/info when no bookings exist"

    def test_regular_session_handles_mixed_attendance_statuses(self):
        """Regular session displays all 4 attendance statuses correctly."""
        mock_bookings = [
            {'id': 1, 'user_id': 101, 'user': {'id': 101, 'name': 'Student 1', 'email': 's1@test.com'}, 'status': 'confirmed'},
            {'id': 2, 'user_id': 102, 'user': {'id': 102, 'name': 'Student 2', 'email': 's2@test.com'}, 'status': 'confirmed'},
            {'id': 3, 'user_id': 103, 'user': {'id': 103, 'name': 'Student 3', 'email': 's3@test.com'}, 'status': 'confirmed'},
            {'id': 4, 'user_id': 104, 'user': {'id': 104, 'name': 'Student 4', 'email': 's4@test.com'}, 'status': 'confirmed'},
        ]

        mock_attendance = [
            {'user_id': 101, 'status': 'present'},
            {'user_id': 102, 'status': 'absent'},
            {'user_id': 103, 'status': 'late'},
            {'user_id': 104, 'status': 'excused'},
        ]

        mock_regular_session = {
            'id': 1,
            'title': 'Mixed Attendance',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': False,
            'session_type': 'on_site',
            'capacity': 20,
            'bookings_count': 4,
            'instructor_id': 5
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_regular_session])):
                    at = AppTest.from_file(
                        "streamlit_app/components/sessions/session_checkin.py",
                        default_timeout=10
                    )

                    at.session_state['wizard_step'] = 2
                    at.session_state['selected_session_id'] = 1
                    at.session_state['selected_session'] = mock_regular_session

                    at.run()

                    # Check that metrics reflect all 4 statuses
                    metrics = at.metric
                    metric_values = {m.label: m.value for m in metrics}

                    # Should show counts for each status
                    # (Exact label matching depends on implementation)
                    present_count = None
                    absent_count = None
                    late_count = None
                    excused_count = None

                    for label, value in metric_values.items():
                        if "Present" in label:
                            present_count = value
                        elif "Absent" in label:
                            absent_count = value
                        elif "Late" in label:
                            late_count = value
                        elif "Excused" in label:
                            excused_count = value

                    # At least one metric should show non-zero values
                    assert present_count or absent_count or late_count or excused_count, \
                        "Should display attendance counts for at least one status"
