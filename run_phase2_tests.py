#!/usr/bin/env python3
"""
Phase 2: Run 11 re-enabled input validation tests
"""
import pytest
import sys

# List of exactly 11 tests to run
tests = [
    "tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_create_tournament_root_input_validation",
    "tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_update_tournament_input_validation",
    "tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_record_match_results_input_validation",
    "tests/integration/api_smoke/test_sessions_smoke.py::TestSessionsSmoke::test_create_session_input_validation",
    "tests/integration/api_smoke/test_sessions_smoke.py::TestSessionsSmoke::test_update_session_input_validation",
    "tests/integration/api_smoke/test_semester_enrollments_smoke.py::TestSemesterenrollmentsSmoke::test_create_enrollment_input_validation",
    "tests/integration/api_smoke/test_semester_enrollments_smoke.py::TestSemesterenrollmentsSmoke::test_approve_enrollment_request_input_validation",
    "tests/integration/api_smoke/test_bookings_smoke.py::TestBookingsSmoke::test_create_booking_input_validation",
    "tests/integration/api_smoke/test_bookings_smoke.py::TestBookingsSmoke::test_confirm_booking_input_validation",
    "tests/integration/api_smoke/test_users_smoke.py::TestUsersSmoke::test_update_user_input_validation",
    "tests/integration/api_smoke/test_users_smoke.py::TestUsersSmoke::test_create_user_input_validation",
]

if __name__ == "__main__":
    args = [
        "-v",
        "--tb=short",
        "--strict-markers",
        "-ra",
    ] + tests

    exit_code = pytest.main(args)
    sys.exit(exit_code)
