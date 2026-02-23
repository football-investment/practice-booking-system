# 🚀 NEXT SESSION: Start Here for Phase 2.2 Implementation

**Previous Session:** 2026-02-07 (Phase 2.1 Complete + Phase 2.2 Foundation)
**This Session Goal:** Complete Phase 2.2 - Service Layer Isolation
**Estimated Time:** 2-2.5 hours

---

## ⚡ Quick Start

### 1. Read These Documents First (5 min)

**Priority Order:**
1. **This document** - Action plan and quick reference
2. **[PHASE2_COMPLETE_SESSION_SUMMARY.md](PHASE2_COMPLETE_SESSION_SUMMARY.md)** - Full context
3. **[PHASE2_2_PROGRESS_CHECKPOINT.md](PHASE2_2_PROGRESS_CHECKPOINT.md)** - Technical details

### 2. Environment Setup (2 min)

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Verify FastAPI is running
lsof -i:8000
# If not running:
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

### 3. Verify Phase 2.1 is Complete (2 min)

```bash
# Check database enum type exists
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "\dT tournament_phase_enum"

# Should show:
#  Schema |         Name          | Type | Owner
# --------+-----------------------+------+----------
#  public | tournament_phase_enum | enum | postgres
```

---

## 📋 Implementation Checklist

### ✅ Already Done (Phase 2.1 + Foundation)

- [x] Database migration (6,173 sessions normalized)
- [x] PostgreSQL enum type created
- [x] 8 files refactored with enum references
- [x] Golden Path test verified (Phases 0-7 PASS)
- [x] Service protocol defined (`protocols.py`)
- [x] Repository pattern implemented (`repositories.py`)
- [x] SQL & Fake implementations ready

### 🔄 To Do This Session (Phase 2.2 Implementation)

#### Task 1: Refactor KnockoutProgressionService (30-40 min)

**File:** `app/services/tournament/knockout_progression_service.py`

**Goal:** Add dependency injection and split into calculate + execute

**Steps:**

1. **Update Constructor:**
   ```python
   # Current (line 26-27):
   def __init__(self, db: Session):
       self.db = db

   # New:
   from app.services.tournament.repositories import SessionRepository
   import logging

   def __init__(self, repository: SessionRepository, logger=None):
       self.repo = repository
       self.logger = logger or logging.getLogger(__name__)
   ```

2. **Add `can_progress()` Method:**
   ```python
   def can_progress(self, session: SessionModel, tournament: Semester) -> bool:
       """Fast guard check - is this a knockout session?"""
       return session.tournament_phase == TournamentPhase.KNOCKOUT
   ```

3. **Rename & Split `process_knockout_progression()`:**
   ```python
   # Old name: process_knockout_progression()
   # New name: calculate_progression()

   def calculate_progression(
       self,
       session: SessionModel,
       tournament: Semester,
       game_results: Dict[str, Any]
   ) -> Optional[Dict[str, Any]]:
       """
       PURE - Calculate what progression should occur (READ-ONLY).
       """
       if not self.can_progress(session, tournament):
           return None

       # Replace self.db.query() with self.repo methods
       rounds = self.repo.get_distinct_rounds(tournament.id, TournamentPhase.KNOCKOUT)

       all_matches = self.repo.get_sessions_by_phase_and_round(
           tournament.id,
           TournamentPhase.KNOCKOUT,
           session.tournament_round,
           exclude_bronze=True
       )

       completed_count = self.repo.count_completed_sessions(all_matches)

       if completed_count < len(all_matches):
           return {
               "action": "wait",
               "message": f"Match completed. Waiting for other matches ({completed_count}/{len(all_matches)} done)"
           }

       # Keep existing _handle_round_completion logic, but return plan instead of executing
       return self._plan_next_round(
           round_num=session.tournament_round,
           total_rounds=len(rounds),
           completed_matches=all_matches,
           tournament=tournament
       )
   ```

4. **Add `execute_progression()` Method:**
   ```python
   def execute_progression(
       self,
       plan: Dict[str, Any],
       tournament: Semester
   ) -> Dict[str, Any]:
       """
       WRITE - Execute the progression plan (single mutation point).
       """
       if plan["action"] == "wait":
           return {"message": plan["message"]}

       created_sessions = []
       for session_data in plan.get("sessions_to_create", []):
           new_session = self.repo.create_session(tournament, session_data)
           created_sessions.append({
               "session_id": new_session.id,
               "title": new_session.title,
               "participants": new_session.participant_user_ids
           })

       self.logger.info(
           f"Created {len(created_sessions)} next-round sessions",
           extra={"created_sessions": created_sessions}
       )

       return {
           "success": True,
           "message": f"✅ Created {len(created_sessions)} next-round matches",
           "created_sessions": created_sessions
       }
   ```

5. **Refactor Helper Methods:**
   - Rename `_handle_round_completion()` → `_plan_next_round()`
   - Update all `self.db.query()` → `self.repo.get_...()`
   - Make `_plan_next_round()` return plan dict, not execute

**Verification:**
```bash
# Test syntax
python3 -m py_compile app/services/tournament/knockout_progression_service.py
```

#### Task 2: Update Endpoint (15-20 min)

**File:** `app/api/api_v1/endpoints/sessions/results.py`

**Goal:** Use two-phase progression with dependency injection

**Changes:**

1. **Add Import:**
   ```python
   from app.services.tournament.repositories import SQLSessionRepository
   ```

2. **Replace Progression Code (around line 309-333):**
   ```python
   # Old (Phase 2.1):
   if session.tournament_phase == TournamentPhase.KNOCKOUT:
       try:
           from app.services.tournament.knockout_progression_service import KnockoutProgressionService
           progression_service = KnockoutProgressionService(db)
           progression_result = progression_service.process_knockout_progression(...)

   # New (Phase 2.2):
   progression_result = None
   if session.tournament_phase == TournamentPhase.KNOCKOUT:
       try:
           from app.services.tournament.knockout_progression_service import KnockoutProgressionService

           # Dependency injection
           repo = SQLSessionRepository(db)
           logger = logging.getLogger(__name__)
           progression_service = KnockoutProgressionService(repo, logger)

           # Two-phase progression
           progression_plan = progression_service.calculate_progression(
               session=session,
               tournament=semester,
               game_results=game_results_data
           )

           if progression_plan and progression_plan.get("action") != "wait":
               progression_result = progression_service.execute_progression(
                   progression_plan,
                   tournament=semester
               )
           elif progression_plan:
               progression_result = {"message": progression_plan["message"]}

       except Exception as e:
           logger.error(
               "Knockout progression failed",
               extra={"session_id": session_id},
               exc_info=True
           )
   ```

**Verification:**
```bash
# Restart FastAPI
lsof -ti:8000 | xargs kill -9
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Test manually (optional)
curl -X PATCH http://localhost:8000/api/v1/sessions/{session_id}/head-to-head-results \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"results": [{"user_id": 10, "score": 5}, {"user_id": 11, "score": 3}]}'
```

#### Task 3: Create Unit Tests (40-60 min)

**File:** `tests/unit/services/test_knockout_progression_service.py` (new)

**Structure:**

```python
"""
Unit tests for KnockoutProgressionService

Phase 2.2: Tests use FakeSessionRepository for fast, deterministic testing.
No database required - tests run in milliseconds.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

from app.services.tournament.repositories import FakeSessionRepository
from app.services.tournament.knockout_progression_service import KnockoutProgressionService
from app.models.tournament_enums import TournamentPhase


# ==================== Fixtures ====================

@pytest.fixture
def mock_tournament():
    """Create mock tournament for testing"""
    tournament = Mock()
    tournament.id = 100
    tournament.max_participants = 8
    tournament.location = "Test Venue"
    tournament.format = "HEAD_TO_HEAD"
    tournament.specialization_type = "FOOTBALL"
    return tournament


def create_mock_session(session_id, round_num, winner_id=None, participants=None):
    """Helper to create mock session"""
    session = Mock()
    session.id = session_id
    session.semester_id = 100
    session.tournament_round = round_num
    session.tournament_phase = TournamentPhase.KNOCKOUT
    session.is_tournament_game = True
    session.title = f"Match {session_id}"

    if winner_id:
        session.game_results = {"winner_user_id": winner_id}
        session.participant_user_ids = participants or [winner_id, winner_id + 1]
    else:
        session.game_results = None
        session.participant_user_ids = participants or []

    return session


# ==================== Tests: can_progress() ====================

def test_can_progress_returns_true_for_knockout_session(mock_tournament):
    """Test that can_progress returns True for knockout sessions"""
    fake_repo = FakeSessionRepository()
    service = KnockoutProgressionService(fake_repo)

    session = create_mock_session(1, round_num=1)

    assert service.can_progress(session, mock_tournament) == True


def test_can_progress_returns_false_for_non_knockout_session(mock_tournament):
    """Test that can_progress returns False for non-knockout sessions"""
    fake_repo = FakeSessionRepository()
    service = KnockoutProgressionService(fake_repo)

    session = create_mock_session(1, round_num=1)
    session.tournament_phase = TournamentPhase.GROUP_STAGE

    assert service.can_progress(session, mock_tournament) == False


# ==================== Tests: calculate_progression() - Semifinals ====================

def test_calculate_progression_both_semifinals_complete(mock_tournament):
    """When both Semi-finals complete, should plan Final creation"""
    # Arrange: 2 Semi-finals, both complete
    semi1 = create_mock_session(1, round_num=1, winner_id=10)
    semi2 = create_mock_session(2, round_num=1, winner_id=12)

    fake_repo = FakeSessionRepository([semi1, semi2])
    service = KnockoutProgressionService(fake_repo)

    # Act: Complete semi2
    plan = service.calculate_progression(semi2, mock_tournament, {})

    # Assert: Should plan Final
    assert plan is not None
    assert plan["action"] == "create_next_round"
    assert len(plan["sessions_to_create"]) >= 1

    # Check Final match exists
    final_sessions = [s for s in plan["sessions_to_create"] if "final" in s["title"].lower()]
    assert len(final_sessions) == 1

    final = final_sessions[0]
    assert set(final["participant_user_ids"]) == {10, 12}  # Winners
    assert final["tournament_round"] == 2


def test_calculate_progression_one_semifinal_incomplete(mock_tournament):
    """When only one Semi-final complete, should wait"""
    # Arrange: 1 complete, 1 incomplete
    semi1 = create_mock_session(1, round_num=1, winner_id=10)
    semi2 = create_mock_session(2, round_num=1, winner_id=None)  # Incomplete

    fake_repo = FakeSessionRepository([semi1, semi2])
    service = KnockoutProgressionService(fake_repo)

    # Act
    plan = service.calculate_progression(semi1, mock_tournament, {})

    # Assert: Should wait
    assert plan["action"] == "wait"
    assert "1/2" in plan["message"]  # 1 out of 2 done


# ==================== Tests: execute_progression() ====================

def test_execute_progression_creates_sessions(mock_tournament):
    """When executing plan, should create sessions via repository"""
    # Arrange
    fake_repo = FakeSessionRepository([])
    service = KnockoutProgressionService(fake_repo)

    plan = {
        "action": "create_next_round",
        "sessions_to_create": [
            {
                "title": "Final",
                "participant_user_ids": [10, 12],
                "tournament_round": 2,
                "tournament_phase": TournamentPhase.KNOCKOUT,
                "date_start": datetime.now(),
                "date_end": datetime.now() + timedelta(hours=2)
            }
        ]
    }

    # Act
    result = service.execute_progression(plan, mock_tournament)

    # Assert
    assert result["success"] == True
    assert len(result["created_sessions"]) == 1
    assert "✅" in result["message"]

    # Verify repository created session
    assert len(fake_repo.created_sessions) == 1
    created = fake_repo.created_sessions[0]
    assert created.title == "Final"
    assert set(created.participant_user_ids) == {10, 12}


def test_execute_progression_wait_action_returns_message(mock_tournament):
    """When plan action is 'wait', should return message without creating sessions"""
    fake_repo = FakeSessionRepository([])
    service = KnockoutProgressionService(fake_repo)

    plan = {
        "action": "wait",
        "message": "Waiting for other matches (1/2 done)"
    }

    # Act
    result = service.execute_progression(plan, mock_tournament)

    # Assert
    assert result["message"] == "Waiting for other matches (1/2 done)"
    assert len(fake_repo.created_sessions) == 0  # No sessions created


# ==================== Tests: Edge Cases ====================

def test_calculate_progression_non_knockout_returns_none(mock_tournament):
    """Non-knockout sessions should return None"""
    session = create_mock_session(1, round_num=1)
    session.tournament_phase = TournamentPhase.GROUP_STAGE

    fake_repo = FakeSessionRepository([session])
    service = KnockoutProgressionService(fake_repo)

    plan = service.calculate_progression(session, mock_tournament, {})

    assert plan is None


def test_calculate_progression_empty_game_results(mock_tournament):
    """Sessions with empty game_results should be counted as incomplete"""
    semi1 = create_mock_session(1, round_num=1, winner_id=None)  # No results
    semi2 = create_mock_session(2, round_num=1, winner_id=12)

    fake_repo = FakeSessionRepository([semi1, semi2])
    service = KnockoutProgressionService(fake_repo)

    plan = service.calculate_progression(semi2, mock_tournament, {})

    assert plan["action"] == "wait"


# ==================== Tests: Quarterfinals ====================

def test_calculate_progression_all_quarterfinals_complete(mock_tournament):
    """When all 4 Quarterfinals complete, should plan 2 Semifinals"""
    # Arrange: 4 Quarterfinals
    quarter1 = create_mock_session(1, round_num=1, winner_id=10)
    quarter2 = create_mock_session(2, round_num=1, winner_id=12)
    quarter3 = create_mock_session(3, round_num=1, winner_id=14)
    quarter4 = create_mock_session(4, round_num=1, winner_id=16)

    fake_repo = FakeSessionRepository([quarter1, quarter2, quarter3, quarter4])
    service = KnockoutProgressionService(fake_repo)

    # Act
    plan = service.calculate_progression(quarter4, mock_tournament, {})

    # Assert: Should create 2 Semi-finals
    assert plan["action"] == "create_next_round"
    assert len(plan["sessions_to_create"]) == 2  # 2 Semi-finals

    for semi in plan["sessions_to_create"]:
        assert semi["tournament_round"] == 2
        assert len(semi["participant_user_ids"]) == 2


# ==================== Coverage Target ====================

"""
Coverage Goals:
- can_progress: 100%
- calculate_progression: >95%
- execute_progression: >90%
- Overall: >90%

Run with:
pytest tests/unit/services/test_knockout_progression_service.py -v --cov=app.services.tournament.knockout_progression_service --cov-report=term-missing
"""
```

**Run Tests:**
```bash
# Create test directory if needed
mkdir -p tests/unit/services
touch tests/unit/services/__init__.py

# Run tests
pytest tests/unit/services/test_knockout_progression_service.py -v

# Run with coverage
pytest tests/unit/services/test_knockout_progression_service.py -v \
  --cov=app.services.tournament.knockout_progression_service \
  --cov-report=term-missing
```

**Target:** >90% coverage

#### Task 4: Integration Test (20-30 min)

**File:** `tests/integration/test_knockout_progression_integration.py` (new)

```python
"""
Integration tests for knockout progression with real database.

Phase 2.2: Verify full flow works end-to-end with PostgreSQL.
"""

import pytest
from datetime import datetime, timedelta

from app.services.tournament.repositories import SQLSessionRepository
from app.services.tournament.knockout_progression_service import KnockoutProgressionService
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.models.tournament_enums import TournamentPhase


def test_end_to_end_knockout_progression(test_db_session):
    """Full progression flow with database"""

    # Create test tournament
    tournament = Semester(
        name="Integration Test Tournament",
        # ... other required fields ...
    )
    test_db_session.add(tournament)
    test_db_session.commit()

    # Create 2 Semi-final sessions
    semi1 = SessionModel(
        semester_id=tournament.id,
        title="Semi-final 1",
        tournament_phase=TournamentPhase.KNOCKOUT,
        tournament_round=1,
        participant_user_ids=[10, 11],
        game_results={"winner_user_id": 10},  # Complete
        # ... other fields ...
    )

    semi2 = SessionModel(
        semester_id=tournament.id,
        title="Semi-final 2",
        tournament_phase=TournamentPhase.KNOCKOUT,
        tournament_round=1,
        participant_user_ids=[12, 13],
        game_results={"winner_user_id": 12},  # Complete
        # ... other fields ...
    )

    test_db_session.add_all([semi1, semi2])
    test_db_session.commit()

    # Trigger progression
    repo = SQLSessionRepository(test_db_session)
    service = KnockoutProgressionService(repo)

    plan = service.calculate_progression(semi2, tournament, {})
    result = service.execute_progression(plan, tournament)

    # Verify Final created in database
    final_sessions = test_db_session.query(SessionModel).filter(
        SessionModel.semester_id == tournament.id,
        SessionModel.tournament_round == 2,
        SessionModel.tournament_phase == TournamentPhase.KNOCKOUT
    ).all()

    assert len(final_sessions) >= 1
    final = final_sessions[0]
    assert set(final.participant_user_ids) == {10, 12}
    assert "final" in final.title.lower()
```

**Run:**
```bash
pytest tests/integration/test_knockout_progression_integration.py -v
```

#### Task 5: Golden Path Verification (10-15 min)

**Goal:** Verify no regressions with refactored service

```bash
# Full E2E test
pytest test_golden_path_api_based.py::test_golden_path_api_based_full_lifecycle -v -s

# Expected: Phases 0-7 PASS (as before)
```

**Success Criteria:**
- ✅ Phases 0-7 PASS
- ✅ 3/3 knockout matches submitted
- ✅ Final participants: `{user_id_1, user_id_2}` populated
- ✅ Logs show structured output

---

## 🎯 Success Criteria for This Session

### Must Have ✅
- [ ] `KnockoutProgressionService` refactored for DI
- [ ] `calculate_progression()` and `execute_progression()` methods work
- [ ] Endpoint uses two-phase progression
- [ ] 15-20 unit tests written
- [ ] >90% code coverage for progression service
- [ ] Golden Path test still passes (Phases 0-7)

### Should Have ✅
- [ ] Integration test with database
- [ ] Clear separation: read vs write operations
- [ ] All database queries through repository
- [ ] Structured logging maintained

### Nice to Have
- [ ] Performance benchmarks (before/after)
- [ ] Additional edge case tests
- [ ] Documentation for new architecture

---

## 📊 Expected Outcomes

**After This Session:**
- Phase 2.2: 100% COMPLETE ✅
- Service layer fully isolated and testable
- >90% unit test coverage
- Golden Path workflow deterministic and production-ready
- Clear path to Phase 2.3 (event-driven) and 2.4 (test infrastructure)

**Production Impact:**
- Faster test execution (unit tests in milliseconds)
- Easier to add new tournament formats
- Clear service boundaries
- Confident refactoring with test safety net

---

## 🆘 Troubleshooting

### Issue: Import errors after refactoring

**Solution:**
```bash
# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Restart FastAPI
lsof -ti:8000 | xargs kill -9
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

### Issue: Tests fail with database errors

**Solution:**
```bash
# Check database connection
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "\dt"

# Verify enum type exists
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "\dT tournament_phase_enum"
```

### Issue: Golden Path test fails

**Solution:**
1. Check FastAPI logs: `tail -f /tmp/fastapi_*.log`
2. Verify database state: Query sessions table
3. Roll back changes: `git diff` and restore if needed
4. Review checkpoint document for correct implementation

---

## 📚 Reference Documents

1. **[PHASE2_COMPLETE_SESSION_SUMMARY.md](PHASE2_COMPLETE_SESSION_SUMMARY.md)** - Full context and examples
2. **[PHASE2_2_PROGRESS_CHECKPOINT.md](PHASE2_2_PROGRESS_CHECKPOINT.md)** - Technical architecture
3. **[PHASE2_2_SERVICE_ISOLATION_DESIGN.md](PHASE2_2_SERVICE_ISOLATION_DESIGN.md)** - Design rationale
4. **[app/services/tournament/protocols.py](app/services/tournament/protocols.py)** - Service protocols
5. **[app/services/tournament/repositories.py](app/services/tournament/repositories.py)** - Repository implementations

---

## ✅ Session Completion Checklist

When you finish this session, create:

```markdown
# Phase 2.2 Implementation Complete

**Date:** [DATE]
**Duration:** [TIME]
**Status:** COMPLETE ✅

## Results
- [ ] Service refactored with DI
- [ ] Endpoint updated for two-phase progression
- [ ] Unit tests: [N] tests written, [X]% coverage
- [ ] Integration test: PASS
- [ ] Golden Path verification: PASS

## Files Modified
1. app/services/tournament/knockout_progression_service.py
2. app/api/api_v1/endpoints/sessions/results.py
3. tests/unit/services/test_knockout_progression_service.py (new)
4. tests/integration/test_knockout_progression_integration.py (new)

## Next Steps
- Phase 2.3: Event-Driven Architecture
- Phase 2.4: Test Infrastructure
```

---

**Start with Task 1 (Service Refactoring) and work sequentially!** 🚀

Good luck! The foundation is solid, and all the examples are in the documentation.
