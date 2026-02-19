"""
Streamlit AppTest component tests for tournament check-in UI.

Tests the CRITICAL requirement: Tournament sessions show ONLY 2 attendance buttons
(Present, Absent) and NOT 4 buttons (Present, Absent, Late, Excused).

This validates the frontend rendering of the 2-button rule.
"""

import pytest
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# ============================================================================
# CRITICAL: 2-Button Rule UI Tests
# ============================================================================

@pytest.mark.component
@pytest.mark.tournament
@pytest.mark.ui
class TestTournamentCheckinUI:
    """Test tournament check-in UI shows ONLY 2 attendance buttons."""

    def test_tournament_attendance_shows_only_2_buttons(self):
        """
        🔥 CRITICAL TEST: Tournament check-in shows ONLY Present/Absent buttons.

        This test validates that the frontend correctly renders 2 buttons
        for tournament sessions, not 4 buttons like regular sessions.
        """
        # Mock API responses
        mock_bookings = [
            {
                'id': 1,
                'user_id': 101,
                'user': {'id': 101, 'name': 'Test Player 1', 'email': 'player1@test.com'},
                'status': 'confirmed'
            },
            {
                'id': 2,
                'user_id': 102,
                'user': {'id': 102, 'name': 'Test Player 2', 'email': 'player2@test.com'},
                'status': 'confirmed'
            }
        ]

        mock_attendance = []

        mock_tournament_session = {
            'id': 1,
            'title': 'Tournament Final',
            'date_start': (datetime.now() + timedelta(hours=2)).isoformat(),
            'is_tournament_game': True,
            'game_type': 'Final',
            'capacity': 20,
            'bookings_count': 2
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_tournament_session])):
                    # Initialize AppTest with tournament check-in component
                    # Note: This would load the actual component file
                    at = AppTest.from_file(
                        "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                        default_timeout=10
                    )

                    # Set session state to Step 2 (attendance marking)
                    at.session_state['wizard_step'] = 2
                    at.session_state['selected_session_id'] = 1
                    at.session_state['selected_session'] = mock_tournament_session

                    # Run the app
                    at.run()

                    # Assert: ONLY 2 buttons per student (Present, Absent)
                    present_buttons = [b for b in at.button if '✅ Present' in str(b.label)]
                    absent_buttons = [b for b in at.button if '❌ Absent' in str(b.label)]
                    late_buttons = [b for b in at.button if '⏰ Late' in str(b.label)]
                    excused_buttons = [b for b in at.button if '🎫 Excused' in str(b.label)]

                    # Should have 2 students × 2 buttons = 4 total attendance buttons
                    assert len(present_buttons) == 2, "Should have 2 Present buttons (one per student)"
                    assert len(absent_buttons) == 2, "Should have 2 Absent buttons (one per student)"

                    # CRITICAL: NO Late or Excused buttons
                    assert len(late_buttons) == 0, "❌ FAIL: Tournament should NOT show Late buttons"
                    assert len(excused_buttons) == 0, "❌ FAIL: Tournament should NOT show Excused buttons"

    def test_tournament_attendance_summary_shows_3_metrics(self):
        """
        Tournament attendance summary shows ONLY 3 metrics (Present, Absent, Pending).

        Regular sessions show 5 metrics (Present, Absent, Late, Excused, Pending).
        """
        mock_bookings = [
            {'id': 1, 'user_id': 101, 'user': {'id': 101, 'name': 'Player 1', 'email': 'p1@test.com'}, 'status': 'confirmed'}
        ]

        mock_attendance = []

        mock_tournament_session = {
            'id': 1,
            'title': 'Semifinal',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': True,
            'game_type': 'Semifinal',
            'capacity': 20,
            'bookings_count': 1
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                with patch('api_helpers.get_sessions', return_value=(True, [mock_tournament_session])):
                    at = AppTest.from_file(
                        "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                        default_timeout=10
                    )

                    at.session_state['wizard_step'] = 2
                    at.session_state['selected_session_id'] = 1
                    at.session_state['selected_session'] = mock_tournament_session

                    at.run()

                    # Check metrics
                    metrics = at.metric
                    metric_labels = [m.label for m in metrics]

                    # Should have: Present, Absent, Pending (3 total)
                    assert "✅ Present" in metric_labels or "Present" in metric_labels
                    assert "❌ Absent" in metric_labels or "Absent" in metric_labels
                    assert "⏳ Pending" in metric_labels or "Pending" in metric_labels

                    # Should NOT have: Late, Excused
                    assert "⏰ Late" not in metric_labels and "Late" not in metric_labels, \
                        "Tournament should NOT show Late metric"
                    assert "🎫 Excused" not in metric_labels and "Excused" not in metric_labels, \
                        "Tournament should NOT show Excused metric"

    def test_tournament_wizard_shows_tournament_icons(self):
        """Tournament wizard uses tournament-specific icons and labels."""
        mock_tournament_session = {
            'id': 1,
            'title': 'Championship',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': True,
            'game_type': 'Final',
            'capacity': 20,
            'bookings_count': 0
        }

        with patch('api_helpers.get_sessions', return_value=(True, [mock_tournament_session])):
            at = AppTest.from_file(
                "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                default_timeout=10
            )

            at.session_state['wizard_step'] = 1

            at.run()

            # Check for tournament-specific UI elements
            markdown_content = ' '.join([m.value for m in at.markdown])

            # Should show tournament branding
            assert "Tournament" in markdown_content or "🏆" in markdown_content, \
                "Should show tournament branding"

            # Should NOT show "Regular Session" text
            assert "Regular Session" not in markdown_content, \
                "Should NOT show regular session branding"

    def test_tournament_filters_only_tournament_sessions(self):
        """
        Tournament check-in ONLY shows sessions with is_tournament_game=True.

        Regular sessions should be filtered out.
        """
        mock_sessions = [
            {
                'id': 1,
                'title': 'Tournament Game',
                'date_start': datetime.now().isoformat(),
                'is_tournament_game': True,
                'game_type': 'Quarterfinal',
                'capacity': 20,
                'bookings_count': 5
            },
            {
                'id': 2,
                'title': 'Regular Training',
                'date_start': datetime.now().isoformat(),
                'is_tournament_game': False,  # NOT a tournament
                'capacity': 20,
                'bookings_count': 10
            }
        ]

        with patch('api_helpers.get_sessions', return_value=(True, mock_sessions)):
            at = AppTest.from_file(
                "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                default_timeout=10
            )

            at.session_state['wizard_step'] = 1

            at.run()

            # Check that ONLY tournament session is shown
            page_content = ' '.join([m.value for m in at.markdown])

            assert "Tournament Game" in page_content, "Should show tournament session"
            assert "Regular Training" not in page_content, "Should NOT show regular session"


# ============================================================================
# Tournament-Specific UI Behavior Tests
# ============================================================================

@pytest.mark.component
@pytest.mark.tournament
@pytest.mark.ui
class TestTournamentUIBehavior:
    """Test tournament-specific UI behaviors."""

    def test_tournament_info_banner_shows_2_button_notice(self):
        """Tournament attendance page shows info banner about 2-button mode."""
        mock_bookings = []
        mock_attendance = []
        mock_tournament_session = {
            'id': 1,
            'title': 'Test Tournament',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': True,
            'game_type': 'Game',
            'capacity': 20,
            'bookings_count': 0
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                at = AppTest.from_file(
                    "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                    default_timeout=10
                )

                at.session_state['wizard_step'] = 2
                at.session_state['selected_session_id'] = 1
                at.session_state['selected_session'] = mock_tournament_session

                at.run()

                # Check for info banner about tournament mode
                info_boxes = at.info

                # Should have at least one info banner
                assert len(info_boxes) > 0, "Should show tournament mode info banner"

                # Info text should mention Present and Absent
                info_text = ' '.join([i.value for i in info_boxes])
                assert ("Present" in info_text and "Absent" in info_text) or \
                       "Tournament Mode" in info_text, \
                       "Info banner should mention tournament attendance rules"

    def test_tournament_step1_shows_game_type_labels(self):
        """Tournament selection shows game_type labels (Semifinal, Final, etc)."""
        mock_tournament_sessions = [
            {
                'id': 1,
                'title': 'Match 1',
                'date_start': datetime.now().isoformat(),
                'is_tournament_game': True,
                'game_type': 'Semifinal',
                'capacity': 20,
                'bookings_count': 10
            },
            {
                'id': 2,
                'title': 'Match 2',
                'date_start': datetime.now().isoformat(),
                'is_tournament_game': True,
                'game_type': 'Final',
                'capacity': 20,
                'bookings_count': 15
            }
        ]

        with patch('api_helpers.get_sessions', return_value=(True, mock_tournament_sessions)):
            at = AppTest.from_file(
                "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                default_timeout=10
            )

            at.session_state['wizard_step'] = 1

            at.run()

            # Check for game type labels
            page_content = ' '.join([m.value for m in at.markdown])

            assert "Semifinal" in page_content, "Should show Semifinal game type"
            assert "Final" in page_content, "Should show Final game type"


# ============================================================================
# Performance & Edge Cases
# ============================================================================

@pytest.mark.component
@pytest.mark.tournament
@pytest.mark.ui
@pytest.mark.slow
class TestTournamentUIPerformance:
    """Test tournament UI performance with many students."""

    def test_tournament_attendance_renders_fast_with_20_students(self):
        """Tournament attendance page renders in <2s with 20 students."""
        import time

        # Create 20 mock students
        mock_bookings = [
            {
                'id': i,
                'user_id': 100 + i,
                'user': {'id': 100 + i, 'name': f'Player {i}', 'email': f'player{i}@test.com'},
                'status': 'confirmed'
            }
            for i in range(20)
        ]

        mock_attendance = []
        mock_tournament_session = {
            'id': 1,
            'title': 'Large Tournament',
            'date_start': datetime.now().isoformat(),
            'is_tournament_game': True,
            'game_type': 'Final',
            'capacity': 20,
            'bookings_count': 20
        }

        with patch('api_helpers_session_groups.get_session_bookings', return_value=(True, mock_bookings)):
            with patch('api_helpers_session_groups.get_session_attendance', return_value=(True, mock_attendance)):
                at = AppTest.from_file(
                    "streamlit_app/components/tournaments/instructor/tournament_checkin.py",
                    default_timeout=10
                )

                at.session_state['wizard_step'] = 2
                at.session_state['selected_session_id'] = 1
                at.session_state['selected_session'] = mock_tournament_session

                start_time = time.time()
                at.run()
                end_time = time.time()

                render_time = end_time - start_time

                # Should render in <2 seconds
                assert render_time < 2.0, f"Render took {render_time:.2f}s, should be <2s"

                # Should still have correct button count (20 students × 2 buttons = 40)
                present_buttons = [b for b in at.button if '✅ Present' in str(b.label)]
                absent_buttons = [b for b in at.button if '❌ Absent' in str(b.label)]

                assert len(present_buttons) == 20, "Should have 20 Present buttons"
                assert len(absent_buttons) == 20, "Should have 20 Absent buttons"


# ============================================================================
# Snapshot/Visual Regression Tests (Optional)
# ============================================================================

@pytest.mark.component
@pytest.mark.tournament
@pytest.mark.ui
@pytest.mark.skip(reason="Snapshot testing requires additional setup")
class TestTournamentUISnapshots:
    """Visual regression tests for tournament UI."""

    def test_tournament_attendance_page_snapshot(self):
        """Capture snapshot of tournament attendance page for visual regression."""
        # This would use a visual regression tool like Percy or similar
        # Left as placeholder for future enhancement
        pass
