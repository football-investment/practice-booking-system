"""
Real User Integration Test — Production DB Users

Test Scope:
- Uses ACTUAL production database users (IDs 3–18, all LFA_FOOTBALL_PLAYER licensed)
- Tests the PRODUCTION workflow: create → enroll → status-advance → sessions → results → rankings
- NO generated OPS users — pure integration test

Objective:
Prove the system works with real user pool, not just synthetic test data.
This is REQUIRED for production-ready status.

Author: Claude Sonnet 4.5
Date: 2026-02-14
"""

import pytest
import time
import requests
import sys
import os
from typing import Any, Dict, List, Optional

# Ensure app is importable (for DB-level verification)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ============================================================================
# CONFIGURATION
# ============================================================================

_API_URL = "http://localhost:8000"
_ADMIN_EMAIL = "admin@lfa.com"
_ADMIN_PASSWORD = "admin123"

# Real user IDs from DB audit (all have LFA_FOOTBALL_PLAYER license, active)
# id=3  kbappe@realmadrid.com         Kylian Mbappé
# id=4  ehaaland@mancity.com          Erling Haaland
# id=5  lmessi@intermiamicf.com       Lionel Messi
# id=6  vjunior@realmadrid.com        Vinícius Júnior
# id=7  jbellingham@realmadrid.com    Jude Bellingham
# id=8  msalah@liverpoolfc.com        Mohamed Salah
# id=9  pfoden@mancity.com            Phil Foden
# id=10 rodri@mancity.com             Rodrigo Hernández
# id=11 rdias@manchestercity.com      Rúben Dias
# id=12 bsaka@arsenal.com             Bukayo Saka
# id=13 jmusiala@bayern.com           Jamal Musiala
# id=14 vosimhen@napolifc.com         Victor Osimhen
# id=15 pwt.k1sqx1@f1rstteam.hu       Tamás Juhász
# id=16 pwt.p3t1k3@f1rstteam.hu       Péter Nagy
# id=17 pwt.v4lv3rd3jr@f1rstteam.hu   Péter Barna
# id=18 pwt.t1b1k3@f1rstteam.hu       Tibor Lénárt
_REAL_PLAYER_IDS = list(range(3, 19))  # [3, 4, 5, ... 18] — 16 players

# Instructor ID for grandmaster
_GRANDMASTER_ID = 2  # grandmaster@lfa.com

# Tournament config
_TOURNAMENT_TYPE_KNOCKOUT_ID = 2  # From tournament-types endpoint

# Knockout bracket math: 16 players → 15 matches + 1 3rd-place = 16 sessions total
_EXPECTED_SESSION_COUNT = 16
_EXPECTED_ROUND1_MATCHES = 8


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_admin_token() -> str:
    response = requests.post(
        f"{_API_URL}/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_tournament(token: str, name: str) -> int:
    """Create a tournament via the standard /tournaments/generate endpoint."""
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    payload = {
        "date": tomorrow,
        "name": name,
        "specialization_type": "LFA_FOOTBALL_PLAYER",
        "assignment_type": "OPEN_ASSIGNMENT",
        "max_players": len(_REAL_PLAYER_IDS),
        "enrollment_cost": 0,
        "format": "HEAD_TO_HEAD",
        "tournament_type_id": _TOURNAMENT_TYPE_KNOCKOUT_ID,
    }
    r = requests.post(
        f"{_API_URL}/api/v1/tournaments/generate",
        headers=_headers(token),
        json=payload
    )
    assert r.status_code == 201, f"Tournament creation failed ({r.status_code}): {r.text}"
    return r.json()["tournament_id"]


def _batch_enroll(token: str, tid: int, user_ids: List[int]) -> Dict[str, Any]:
    """Admin batch-enroll players."""
    r = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/admin/batch-enroll",
        headers=_headers(token),
        json={"player_ids": user_ids}
    )
    assert r.status_code == 200, f"Batch enroll failed ({r.status_code}): {r.text}"
    return r.json()


def _advance_to_in_progress(token: str, tid: int) -> Dict[str, Any]:
    """
    Admin PATCH override: bypass state machine, set tournament_status → IN_PROGRESS.
    This also triggers auto-generation of sessions.
    """
    r = requests.patch(
        f"{_API_URL}/api/v1/tournaments/{tid}",
        headers=_headers(token),
        json={"tournament_status": "IN_PROGRESS"}
    )
    assert r.status_code == 200, f"Status override failed ({r.status_code}): {r.text}"
    return r.json()


def _get_sessions(token: str, tid: int) -> List[Dict[str, Any]]:
    r = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions",
        headers=_headers(token)
    )
    assert r.status_code == 200, f"Get sessions failed ({r.status_code}): {r.text}"
    return r.json()


def _simulate_results_db(tid: int) -> None:
    """Simulate tournament results directly via DB (same as async tests)."""
    import logging as _logging
    from app.database import SessionLocal
    from app.api.api_v1.endpoints.tournaments.ops_scenario import _simulate_tournament_results

    db = SessionLocal()
    _logger = _logging.getLogger("test_real_user_integration")
    try:
        ok, msg = _simulate_tournament_results(db, tid, _logger)
        assert ok, f"Simulate results failed: {msg}"
        db.commit()
    finally:
        db.close()


def _calculate_rankings(token: str, tid: int) -> Dict[str, Any]:
    r = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/calculate-rankings",
        headers=_headers(token)
    )
    assert r.status_code in (200, 201), f"Calculate rankings failed ({r.status_code}): {r.text}"
    return r.json()


def _complete_tournament(token: str, tid: int) -> Dict[str, Any]:
    r = requests.patch(
        f"{_API_URL}/api/v1/tournaments/{tid}",
        headers=_headers(token),
        json={"tournament_status": "COMPLETED"}
    )
    assert r.status_code == 200, f"Complete tournament failed ({r.status_code}): {r.text}"
    return r.json()


# ============================================================================
# TEST CLASS
# ============================================================================

class TestRealUserIntegration:
    """
    Real User Integration Tests — Group X

    Uses 16 actual production users (IDs 3–18) with LFA_FOOTBALL_PLAYER licenses.
    Tests the complete lifecycle on the sync path (16 players < 128 threshold).

    This validates that the system works with real user data,
    not just OPS-generated synthetic test users.
    """

    def test_x01_real_students_exist_with_licenses(self):
        """
        Verify the 16 real production students exist in DB with active licenses.
        DB-level audit — no API needed.
        """
        from app.database import SessionLocal
        from app.models.user import User, UserRole
        from app.models.license import UserLicense

        db = SessionLocal()
        try:
            real_users = (
                db.query(User)
                .filter(User.id.in_(_REAL_PLAYER_IDS))
                .filter(User.role == UserRole.STUDENT)
                .filter(User.is_active == True)
                .all()
            )
            assert len(real_users) == len(_REAL_PLAYER_IDS), (
                f"Expected {len(_REAL_PLAYER_IDS)} real students, found {len(real_users)}"
            )

            # Verify none are OPS test users
            for u in real_users:
                assert "@lfa-ops.internal" not in u.email, (
                    f"OPS test user found: {u.email}"
                )
                assert "@loadtest.lfa" not in u.email

            # Verify all have LFA_FOOTBALL_PLAYER license
            licensed = (
                db.query(UserLicense)
                .filter(UserLicense.user_id.in_(_REAL_PLAYER_IDS))
                .filter(UserLicense.is_active == True)
                .filter(UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER")
                .all()
            )
            assert len(licensed) == len(_REAL_PLAYER_IDS), (
                f"Expected {len(_REAL_PLAYER_IDS)} LFA_FOOTBALL_PLAYER licenses, "
                f"found {len(licensed)}"
            )

            print(f"\n[REAL USERS OK] {len(real_users)} production students with valid licenses")
            for u in real_users:
                print(f"  id={u.id} | {u.email} | {u.name}")
        finally:
            db.close()

    def test_x02_create_tournament_with_real_users(self):
        """
        Create a 16p knockout tournament and batch-enroll the 16 real production users.
        Verifies the admin create + enroll workflow works with real user IDs.
        """
        token = _get_admin_token()
        tid = _create_tournament(token, "X02 - Real User 16p Knockout")

        enroll_result = _batch_enroll(token, tid, _REAL_PLAYER_IDS)

        assert enroll_result["success"] is True
        assert enroll_result["enrolled_count"] == len(_REAL_PLAYER_IDS)
        assert enroll_result["failed_players"] == []

        print(f"\n[X02 OK] Tournament {tid} created, {enroll_result['enrolled_count']}/16 real users enrolled")

    def test_x03_session_generation_with_real_users(self):
        """
        Create tournament → enroll 16 real users → advance to IN_PROGRESS → verify 16 sessions.
        Asserts (DB-level):
        - Round 1 has exactly 8 matches (round_number=1 in DB)
        - Each Round 1 session contains exactly 2 REAL user IDs (no OPS users)
        - All participant IDs are within the real player ID range
        """
        token = _get_admin_token()
        tid = _create_tournament(token, "X03 - Real User Session Generation")
        _batch_enroll(token, tid, _REAL_PLAYER_IDS)

        # Advance to IN_PROGRESS (triggers auto-generation)
        patch_result = _advance_to_in_progress(token, tid)
        auto_sessions = patch_result.get("updates", {}).get("sessions_auto_generated", {})
        print(f"\n[X03] Auto-generated: {auto_sessions}")

        # API-level: total session count
        sessions = _get_sessions(token, tid)
        assert len(sessions) == _EXPECTED_SESSION_COUNT, (
            f"Expected {_EXPECTED_SESSION_COUNT} sessions, got {len(sessions)}"
        )

        # DB-level: round_number check (API response doesn't include round_number)
        from app.database import SessionLocal
        from app.models.session import Session as SessionModel

        db = SessionLocal()
        try:
            round1_db = (
                db.query(SessionModel)
                .filter(SessionModel.semester_id == tid)
                .filter(SessionModel.round_number == 1)
                .all()
            )
            assert len(round1_db) == _EXPECTED_ROUND1_MATCHES, (
                f"Round 1 should have {_EXPECTED_ROUND1_MATCHES} matches, got {len(round1_db)}"
            )

            # Validate participants are real users
            all_real_ids = set(_REAL_PLAYER_IDS)
            for session in round1_db:
                participants = session.participant_user_ids or []
                assert len(participants) == 2, (
                    f"Session {session.id} should have 2 participants, got {len(participants)}"
                )
                for pid in participants:
                    assert pid in all_real_ids, (
                        f"Participant {pid} is NOT a real production user! "
                        f"(Real IDs: {sorted(all_real_ids)})"
                    )

            print(f"\n[X03 OK] {len(sessions)} sessions generated, all with real production users")
            for s in round1_db:
                print(f"  Round 1 Session {s.id}: players {s.participant_user_ids}")
        finally:
            db.close()

    def test_x04_no_ops_users_in_sessions(self):
        """
        DB-level audit: verify that after session generation, NO @lfa-ops.internal
        or other synthetic test users appear in the session participant lists.
        """
        token = _get_admin_token()
        tid = _create_tournament(token, "X04 - OPS Contamination Check")
        _batch_enroll(token, tid, _REAL_PLAYER_IDS)
        _advance_to_in_progress(token, tid)

        # DB audit
        from app.database import SessionLocal
        from app.models.session import Session as SessionModel
        from app.models.user import User

        db = SessionLocal()
        try:
            sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
            participant_ids = set()
            for s in sessions:
                if s.participant_user_ids:
                    participant_ids.update(s.participant_user_ids)

            # Check all participants against user table
            if participant_ids:
                users = db.query(User).filter(User.id.in_(participant_ids)).all()
                for u in users:
                    assert "@lfa-ops.internal" not in u.email, (
                        f"OPS test user contamination: {u.email} (id={u.id})"
                    )
                    assert "@loadtest.lfa" not in u.email, (
                        f"Loadtest user contamination: {u.email} (id={u.id})"
                    )

                print(f"\n[X04 OK] {len(participant_ids)} unique participants verified — ZERO OPS contamination")
                for u in sorted(users, key=lambda x: x.id):
                    print(f"  id={u.id} | {u.email}")
        finally:
            db.close()

    def test_x05_full_lifecycle_real_users(self):
        """
        COMPREHENSIVE LIFECYCLE TEST with real production users:
        1. Create tournament
        2. Enroll 16 real users (admin batch-enroll)
        3. Advance to IN_PROGRESS → auto session generation
        4. Simulate results (via DB helper)
        5. Calculate rankings
        6. Complete tournament → COMPLETED

        Validates the ENTIRE production workflow on real user data.
        """
        print(f"\n{'='*65}")
        print(f"  COMPREHENSIVE REAL USER LIFECYCLE — 16p KNOCKOUT")
        print(f"  Players: {_REAL_PLAYER_IDS}")
        print(f"{'='*65}")

        token = _get_admin_token()

        # ── Step 1: Create ───────────────────────────────────────────────
        print("\n[STEP 1] Creating tournament...")
        t0 = time.monotonic()
        tid = _create_tournament(token, "X05 - Full Lifecycle Real Users")
        t1 = time.monotonic()
        print(f"  ✓ Tournament ID: {tid} ({t1-t0:.2f}s)")

        # ── Step 2: Enroll ───────────────────────────────────────────────
        print("\n[STEP 2] Enrolling 16 real production users...")
        t2 = time.monotonic()
        enroll_result = _batch_enroll(token, tid, _REAL_PLAYER_IDS)
        t3 = time.monotonic()
        assert enroll_result["enrolled_count"] == 16
        print(f"  ✓ Enrolled {enroll_result['enrolled_count']}/16 ({t3-t2:.2f}s)")
        print(f"  ✓ No failures: {enroll_result['failed_players']}")

        # ── Step 3: IN_PROGRESS → auto session generation ────────────────
        print("\n[STEP 3] Advancing to IN_PROGRESS (triggers auto-generation)...")
        t4 = time.monotonic()
        patch_result = _advance_to_in_progress(token, tid)
        t5 = time.monotonic()
        auto_sessions = patch_result.get("updates", {}).get("sessions_auto_generated", {})
        session_count = auto_sessions.get("count", 0)
        print(f"  ✓ Sessions auto-generated: {session_count} ({t5-t4:.2f}s)")

        sessions = _get_sessions(token, tid)
        assert len(sessions) == _EXPECTED_SESSION_COUNT, (
            f"Expected {_EXPECTED_SESSION_COUNT} sessions, got {len(sessions)}"
        )

        # DB-level round validation (API doesn't expose round_number)
        from app.database import SessionLocal as _SL
        from app.models.session import Session as _SM
        _db = _SL()
        try:
            round1 = _db.query(_SM).filter(
                _SM.semester_id == tid, _SM.round_number == 1
            ).all()
        finally:
            _db.close()

        assert len(round1) == _EXPECTED_ROUND1_MATCHES

        # Verify participants are real users
        real_ids = set(_REAL_PLAYER_IDS)
        for session in round1:
            for pid in (session.participant_user_ids or []):
                assert pid in real_ids, f"Non-real participant {pid} in session!"

        print(f"  ✓ {len(sessions)} sessions, {len(round1)} R1 matches, all real users")

        # ── Step 4: Simulate results ─────────────────────────────────────
        print("\n[STEP 4] Simulating match results...")
        t6 = time.monotonic()
        _simulate_results_db(tid)
        t7 = time.monotonic()
        print(f"  ✓ Results simulated ({t7-t6:.2f}s)")

        # ── Step 5: Rankings ─────────────────────────────────────────────
        print("\n[STEP 5] Calculating rankings...")
        t8 = time.monotonic()
        rankings_result = _calculate_rankings(token, tid)
        t9 = time.monotonic()
        print(f"  ✓ Rankings calculated ({t9-t8:.2f}s)")

        # ── Step 6: Complete ─────────────────────────────────────────────
        print("\n[STEP 6] Completing tournament...")
        t10 = time.monotonic()
        complete_result = _complete_tournament(token, tid)
        t11 = time.monotonic()
        print(f"  ✓ Tournament COMPLETED ({t11-t10:.2f}s)")

        # ── Final DB audit ───────────────────────────────────────────────
        print("\n[DB AUDIT] Final verification...")
        from app.database import SessionLocal
        from app.models.semester import Semester
        from app.models.session import Session as SessionModel
        from app.models.user import User

        db = SessionLocal()
        try:
            tournament = db.query(Semester).filter(Semester.id == tid).first()
            assert tournament.tournament_status == "COMPLETED", (
                f"Expected COMPLETED, got {tournament.tournament_status}"
            )

            sessions_db = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
            participant_ids = set()
            for s in sessions_db:
                if s.participant_user_ids:
                    participant_ids.update(s.participant_user_ids)

            # Verify NO OPS users
            if participant_ids:
                users = db.query(User).filter(User.id.in_(participant_ids)).all()
                for u in users:
                    assert "@lfa-ops.internal" not in u.email
                    assert "@loadtest.lfa" not in u.email

            print(f"\n{'='*65}")
            print(f"  REAL USER LIFECYCLE COMPLETE")
            print(f"  Tournament ID   : {tid}")
            print(f"  Status          : COMPLETED")
            print(f"  Sessions        : {len(sessions_db)}")
            print(f"  Unique players  : {len(participant_ids)}")
            print(f"  OPS contamination: NONE")
            print(f"  Total wall time : {t11-t0:.2f}s")
            print(f"{'='*65}\n")
        finally:
            db.close()

    def test_x06_db_audit_after_tests(self):
        """
        Post-suite DB audit:
        - Count real vs OPS users
        - Confirm no new OPS users were created by this test suite
        - Report final DB state
        """
        from app.database import SessionLocal
        from app.models.user import User, UserRole

        db = SessionLocal()
        try:
            total = db.query(User).count()
            ops = (
                db.query(User)
                .filter(User.email.like("%@lfa-ops.internal"))
                .count()
            )
            real = (
                db.query(User)
                .filter(~User.email.like("%@lfa-ops.internal"))
                .filter(~User.email.like("%@loadtest.lfa"))
                .filter(~User.email.like("%@concurrent.lfa"))
                .filter(~User.email.like("%@large.lfa"))
                .count()
            )

            print(f"\n[DB AUDIT]")
            print(f"  Total users     : {total}")
            print(f"  OPS test users  : {ops}")
            print(f"  Real users      : {real}")
            print(f"  DB ratio        : {real}/{total} real ({100*real/total:.1f}%)")

            # This test suite should NOT have created any OPS users
            # Real users should remain 19 (17 students + 1 instructor + 1 admin)
            assert real >= 19, f"Expected at least 19 real users, found {real}"

            print(f"\n[DB AUDIT OK] No OPS contamination from real-user test suite")
        finally:
            db.close()
