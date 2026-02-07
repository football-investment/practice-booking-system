# Phase 2.2 Design: Service Layer Isolation

**Date:** 2026-02-07
**Status:** 🔄 IN PROGRESS - Design Phase
**Goal:** Decouple progression logic from HTTP layer for testability and determinism

---

## Current Architecture Analysis

### Coupling Points Identified

#### 1. **Tight Coupling to HTTP Request Lifecycle**
**Location:** [app/api/api_v1/endpoints/sessions/results.py:309-333](app/api/api_v1/endpoints/sessions/results.py#L309-L333)

**Problem:**
```python
# Progression service instantiated and called within endpoint handler
if session.tournament_phase == TournamentPhase.KNOCKOUT:
    try:
        from app.services.tournament.knockout_progression_service import KnockoutProgressionService
        progression_service = KnockoutProgressionService(db)
        progression_result = progression_service.process_knockout_progression(...)
        # Logging inline
        if progression_result and "updated_sessions" in progression_result:
            logger.info(...)
    except Exception as e:
        logger.error(...)
```

**Issues:**
- Service instantiation inside request handler (lazy import)
- Logging logic mixed with business logic
- Exception handling in endpoint (service doesn't fail fast)
- No separation between "result submission" and "progression triggering"

#### 2. **Direct Database Session Dependency**
**Location:** [app/services/tournament/knockout_progression_service.py:26-27](app/services/tournament/knockout_progression_service.py#L26-L27)

**Problem:**
```python
def __init__(self, db: Session):
    self.db = db  # Direct SQLAlchemy session dependency
```

**Issues:**
- Hard to mock for unit tests
- Requires real database connection
- No abstraction over data access layer
- Service tightly coupled to SQLAlchemy ORM

#### 3. **No Service Interface/Protocol**
**Current State:** Concrete class with no interface

**Issues:**
- Can't swap implementations (e.g., async version, cached version)
- No contract enforcement
- Difficult to test with mocks
- No clear service boundaries

#### 4. **Side Effects in Service Methods**
**Location:** Throughout `knockout_progression_service.py`

**Problem:**
```python
def process_knockout_progression(...):
    # Queries database
    total_rounds = self.db.query(...).count()
    all_matches = self.db.query(...).all()

    # Modifies database
    return self._handle_round_completion(...)  # Creates new sessions
```

**Issues:**
- Service both reads and writes to database
- No clear separation between query and command
- Difficult to test individual components
- State changes hidden within method calls

---

## Phase 2.2 Design Goals

### 1. **Service Interface (Protocol)**
Create abstract protocol for progression services to enforce contracts

### 2. **Dependency Injection**
Explicit dependencies, no hidden coupling

### 3. **Testability**
Easy to mock, fast unit tests, no database required

### 4. **Separation of Concerns**
- **Query**: Read tournament state
- **Command**: Update tournament state (create sessions)
- **Orchestration**: Coordinate queries and commands

### 5. **Deterministic Behavior**
Predictable outcomes, no side effects, clear input/output

---

## Proposed Architecture

### Layer 1: Service Protocol (Interface)

**File:** `app/services/tournament/protocols.py` (new)

```python
from typing import Protocol, Optional, Dict, Any, List
from app.models.session import Session as SessionModel
from app.models.semester import Semester

class TournamentProgressionService(Protocol):
    """
    Protocol for tournament progression services.

    Defines the contract for handling automatic tournament progression
    (e.g., knockout bracket advancement, group stage completion).
    """

    def can_progress(
        self,
        session: SessionModel,
        tournament: Semester
    ) -> bool:
        """
        Check if a completed session triggers progression.

        Args:
            session: Completed session
            tournament: Tournament context

        Returns:
            True if progression should occur, False otherwise
        """
        ...

    def calculate_progression(
        self,
        session: SessionModel,
        tournament: Semester,
        game_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate what progression should occur (read-only).

        Args:
            session: Completed session
            tournament: Tournament context
            game_results: Match results

        Returns:
            Progression plan (what sessions to create, with participants)
            or None if no progression needed
        """
        ...

    def execute_progression(
        self,
        progression_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the progression plan (write operation).

        Args:
            progression_plan: Output from calculate_progression()

        Returns:
            Result summary with created session IDs
        """
        ...
```

**Benefits:**
- Clear contract for progression services
- Separation between calculation (read) and execution (write)
- Easy to mock for testing
- Can swap implementations without changing client code

### Layer 2: Repository Pattern (Data Access)

**File:** `app/services/tournament/repositories.py` (new)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel
from app.models.tournament_enums import TournamentPhase

class SessionRepository(ABC):
    """Abstract repository for session data access"""

    @abstractmethod
    def get_knockout_sessions_by_round(
        self,
        tournament_id: int,
        round_num: int
    ) -> List[SessionModel]:
        """Get all knockout sessions for a specific round"""
        ...

    @abstractmethod
    def get_distinct_rounds(
        self,
        tournament_id: int,
        phase: TournamentPhase
    ) -> List[int]:
        """Get list of distinct round numbers for a phase"""
        ...

    @abstractmethod
    def create_session(
        self,
        session_data: Dict[str, Any]
    ) -> SessionModel:
        """Create a new session"""
        ...

class SQLSessionRepository(SessionRepository):
    """SQLAlchemy implementation of SessionRepository"""

    def __init__(self, db: Session):
        self.db = db

    def get_knockout_sessions_by_round(self, tournament_id, round_num):
        return self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament_id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.tournament_round == round_num,
                SessionModel.is_tournament_game == True,
                ~SessionModel.title.ilike("%bronze%"),
                ~SessionModel.title.ilike("%3rd%")
            )
        ).all()

    # ... other methods
```

**Benefits:**
- Abstraction over database operations
- Easy to create fake repositories for testing
- Can add caching, logging, etc. without changing business logic
- Clear data access boundaries

### Layer 3: Refactored Progression Service

**File:** `app/services/tournament/knockout_progression_service.py` (refactored)

```python
from app.services.tournament.protocols import TournamentProgressionService
from app.services.tournament.repositories import SessionRepository

class KnockoutProgressionService:
    """
    Knockout tournament progression service with dependency injection.

    Phase 2.2: Refactored for testability and separation of concerns.
    """

    def __init__(self, session_repository: SessionRepository, logger=None):
        """
        Initialize with injected dependencies.

        Args:
            session_repository: Repository for session data access
            logger: Optional logger instance (defaults to module logger)
        """
        self.repo = session_repository
        self.logger = logger or logging.getLogger(__name__)

    def can_progress(self, session, tournament) -> bool:
        """Check if session is knockout phase"""
        return session.tournament_phase == TournamentPhase.KNOCKOUT

    def calculate_progression(self, session, tournament, game_results):
        """
        Calculate progression plan (read-only, no side effects).

        Returns:
            {
                "action": "create_next_round",
                "sessions_to_create": [
                    {
                        "title": "Final",
                        "participants": [user_id_1, user_id_2],
                        "tournament_round": 2,
                        ...
                    }
                ]
            }
        """
        if not self.can_progress(session, tournament):
            return None

        # Pure logic - no database writes
        round_num = session.tournament_round
        all_matches = self.repo.get_knockout_sessions_by_round(
            tournament.id,
            round_num
        )

        completed_count = sum(1 for m in all_matches if m.game_results)

        if completed_count < len(all_matches):
            return {
                "action": "wait",
                "message": f"Waiting for other matches ({completed_count}/{len(all_matches)} done)"
            }

        # Calculate what sessions should be created
        return self._plan_next_round(
            round_num=round_num,
            completed_matches=all_matches,
            tournament=tournament
        )

    def execute_progression(self, progression_plan):
        """
        Execute progression plan (write operation).

        This is the ONLY method that modifies database state.
        """
        if progression_plan["action"] == "wait":
            return {"message": progression_plan["message"]}

        created_sessions = []
        for session_data in progression_plan["sessions_to_create"]:
            new_session = self.repo.create_session(session_data)
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
            "message": f"✅ Created {len(created_sessions)} next-round matches",
            "updated_sessions": created_sessions
        }
```

**Benefits:**
- Constructor injection makes dependencies explicit
- `calculate_progression()` is pure function (no side effects)
- `execute_progression()` is single point of mutation
- Easy to test each method independently
- Logger is injected (can be mocked)

### Layer 4: Refactored Endpoint

**File:** `app/api/api_v1/endpoints/sessions/results.py` (refactored)

```python
def submit_head_to_head_match_result(...):
    # ... existing result submission logic ...

    db.commit()
    db.refresh(session)

    # Phase 2.2: Use dependency injection for progression service
    progression_result = None
    if session.tournament_phase == TournamentPhase.KNOCKOUT:
        try:
            # Dependency injection: create service with repository
            repo = SQLSessionRepository(db)
            logger = logging.getLogger(__name__)
            progression_service = KnockoutProgressionService(repo, logger)

            # Two-phase progression: calculate then execute
            progression_plan = progression_service.calculate_progression(
                session=session,
                tournament=semester,
                game_results=game_results_data
            )

            if progression_plan and progression_plan["action"] != "wait":
                progression_result = progression_service.execute_progression(
                    progression_plan
                )
            elif progression_plan:
                progression_result = {"message": progression_plan["message"]}

        except Exception as e:
            logger.error(
                "Knockout progression failed",
                extra={"session_id": session_id},
                exc_info=True
            )
            # Don't propagate exception - result submission should succeed

    return {
        "session_id": session_id,
        "knockout_progression": progression_result,
        ...
    }
```

**Benefits:**
- Dependencies created explicitly
- Two-phase progression (calculate → execute) is clear
- Service instantiation separated from business logic
- Can easily add additional progression services (e.g., group stage finalization)

---

## Testing Strategy

### Unit Tests (No Database)

**File:** `tests/unit/services/test_knockout_progression_service.py` (new)

```python
import pytest
from unittest.mock import Mock
from app.services.tournament.knockout_progression_service import KnockoutProgressionService
from app.models.tournament_enums import TournamentPhase

class FakeSessionRepository:
    """Fake repository for unit testing"""

    def __init__(self, sessions_data):
        self.sessions = sessions_data
        self.created = []

    def get_knockout_sessions_by_round(self, tournament_id, round_num):
        return [s for s in self.sessions if s.tournament_round == round_num]

    def create_session(self, session_data):
        mock_session = Mock()
        mock_session.id = len(self.created) + 1000
        mock_session.title = session_data["title"]
        mock_session.participant_user_ids = session_data["participant_user_ids"]
        self.created.append(mock_session)
        return mock_session

def test_calculate_progression_when_semifinals_complete():
    """Test that Final match is planned when both Semi-finals are complete"""

    # Arrange: Create fake semi-final sessions (both completed)
    semi1 = Mock()
    semi1.id = 1
    semi1.tournament_round = 1
    semi1.game_results = {"winner_user_id": 10, ...}  # Completed
    semi1.participant_user_ids = [10, 11]

    semi2 = Mock()
    semi2.id = 2
    semi2.tournament_round = 1
    semi2.game_results = {"winner_user_id": 12, ...}  # Completed
    semi2.participant_user_ids = [12, 13]

    fake_repo = FakeSessionRepository([semi1, semi2])
    service = KnockoutProgressionService(fake_repo)

    # Act: Calculate progression
    tournament = Mock()
    tournament.id = 100
    progression_plan = service.calculate_progression(
        session=semi2,  # Just completed semi2
        tournament=tournament,
        game_results={"winner_user_id": 12}
    )

    # Assert: Should plan to create Final match with winners
    assert progression_plan["action"] == "create_next_round"
    assert len(progression_plan["sessions_to_create"]) == 1
    final_session = progression_plan["sessions_to_create"][0]
    assert final_session["title"].lower().contains("final")
    assert set(final_session["participant_user_ids"]) == {10, 12}  # Winners
    assert final_session["tournament_round"] == 2

def test_calculate_progression_when_only_one_semifinal_complete():
    """Test that no progression occurs when waiting for other matches"""

    # Arrange: One semi complete, one incomplete
    semi1 = Mock()
    semi1.tournament_round = 1
    semi1.game_results = {"winner_user_id": 10}  # Completed

    semi2 = Mock()
    semi2.tournament_round = 1
    semi2.game_results = None  # NOT completed

    fake_repo = FakeSessionRepository([semi1, semi2])
    service = KnockoutProgressionService(fake_repo)

    # Act
    progression_plan = service.calculate_progression(...)

    # Assert: Should wait
    assert progression_plan["action"] == "wait"
    assert "1/2" in progression_plan["message"]
```

**Benefits:**
- **Fast**: No database, runs in milliseconds
- **Isolated**: Tests only service logic
- **Deterministic**: Fully controlled test data
- **Coverage**: Easy to test edge cases (ties, dropouts, etc.)

### Integration Tests (With Database)

**File:** `tests/integration/test_knockout_progression_integration.py` (new)

```python
def test_end_to_end_knockout_progression(test_db_session):
    """Test full progression flow with real database"""

    # Setup tournament with 4 players
    tournament = create_test_tournament(test_db_session, player_count=4)

    # Generate knockout bracket (2 semi-finals)
    generate_knockout_sessions(test_db_session, tournament)

    # Submit semi-final results
    semi1, semi2 = get_knockout_sessions(test_db_session, tournament, round=1)
    submit_match_result(test_db_session, semi1, winner_id=10, loser_id=11)
    submit_match_result(test_db_session, semi2, winner_id=12, loser_id=13)

    # Trigger progression
    repo = SQLSessionRepository(test_db_session)
    service = KnockoutProgressionService(repo)
    progression_plan = service.calculate_progression(semi2, tournament, {...})
    result = service.execute_progression(progression_plan)

    # Verify Final created
    final_sessions = get_knockout_sessions(test_db_session, tournament, round=2)
    assert len(final_sessions) == 1
    assert set(final_sessions[0].participant_user_ids) == {10, 12}
```

---

## Implementation Plan

### Step 1: Create Protocol & Repository ✅
- [ ] Create `app/services/tournament/protocols.py`
- [ ] Create `app/services/tournament/repositories.py`
- [ ] Implement `SQLSessionRepository`

### Step 2: Refactor Service ✅
- [ ] Update `KnockoutProgressionService.__init__` for DI
- [ ] Split `process_knockout_progression` into `calculate` + `execute`
- [ ] Extract query logic to use repository
- [ ] Make `calculate_progression` pure (no side effects)

### Step 3: Update Endpoint ✅
- [ ] Refactor `results.py` to use DI
- [ ] Implement two-phase progression call
- [ ] Clean up exception handling

### Step 4: Create Unit Tests ✅
- [ ] Setup test infrastructure (`tests/unit/services/`)
- [ ] Create `FakeSessionRepository`
- [ ] Write unit tests for progression logic
- [ ] Achieve >90% code coverage

### Step 5: Create Integration Tests ✅
- [ ] Setup test fixtures
- [ ] Write end-to-end integration tests
- [ ] Verify database state after progression

### Step 6: Verification ✅
- [ ] Run Golden Path E2E test
- [ ] Verify no regressions
- [ ] Performance testing

---

## Success Criteria

### Must Have ✅
- [ ] Service protocol defined
- [ ] Repository pattern implemented
- [ ] Progression service refactored for DI
- [ ] Unit tests with >90% coverage
- [ ] Golden Path test still passes

### Should Have ✅
- [ ] Integration tests for full lifecycle
- [ ] Clear separation: calculate vs execute
- [ ] All queries go through repository
- [ ] Structured logging in service

### Nice to Have
- [ ] Async version of service
- [ ] Caching layer in repository
- [ ] Performance benchmarks

---

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation:** Implement incrementally, keep old code path until verified

### Risk 2: Test Infrastructure Complexity
**Mitigation:** Start with simple fake repository, expand as needed

### Risk 3: Performance Regression
**Mitigation:** Benchmark before/after, repository should be thin wrapper

---

## Next Actions

1. Create `protocols.py` with `TournamentProgressionService` protocol
2. Create `repositories.py` with `SessionRepository` + `SQLSessionRepository`
3. Begin refactoring `KnockoutProgressionService` for constructor injection
4. Create unit test file with fake repository

Let's proceed with implementation! 🚀
