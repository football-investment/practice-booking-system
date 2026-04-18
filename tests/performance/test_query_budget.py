"""
Query Budget Regression Tests — GET /events/{id}
================================================

Hard limit: ≤15 queries per request to GET /events/{tournament_id}.

Purpose: Prevent N+1 regressions from silently reintroducing unbounded query growth.
The limit is N-INDEPENDENT — it must hold regardless of how many rankings, participants,
or sessions the event has.

Baseline (2026-04-18):
  Before fix: ~28 queries for event 31 (16 N+1 user lookups = 57% of total)
  After fix:  ≤15 queries for any event (selectinload/joinedload — O(1) w.r.t. data)

If you add a new query to public_event_detail and this test fails:
  - Check if you introduced a loop with db.query() inside it (N+1)
  - Use selectinload()/joinedload() for ORM relationships
  - Use WHERE id IN (...) batch queries for non-relationship lookups
  - If the new query is genuinely fixed-count, adjust QUERY_BUDGET to the new minimum

See: tests/performance/DB_PROFILING_300VU.md for full profiling analysis.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event

from app.main import app
from app.database import engine


# Hard limit — must hold for any event ID regardless of data size
QUERY_BUDGET = 15

# Events used in load tests (varying data richness)
# Event 31: REWARDS_DISTRIBUTED, Swiss, 16 rankings, 32 sessions — heaviest case
# Events 1,2,3,33: DRAFT / ENROLLMENT_OPEN, 0 sessions — baseline case
LOAD_TEST_EVENT_IDS = [1, 2, 3, 31, 33]


def _count_queries_for(client: TestClient, path: str) -> int:
    """Return the number of SQL statements executed for a single GET request."""
    count = 0

    def _before_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal count
        count += 1

    sa_event.listen(engine, "before_cursor_execute", _before_execute)
    try:
        client.get(path)
    finally:
        sa_event.remove(engine, "before_cursor_execute", _before_execute)
    return count


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestQueryBudget:
    """
    Each test hits one event page and asserts query count ≤ QUERY_BUDGET.

    Failure means an N+1 regression was introduced — do NOT just raise the budget.
    Fix the regression first, then check if budget needs adjusting.
    """

    @pytest.mark.parametrize("event_id", LOAD_TEST_EVENT_IDS)
    def test_event_detail_query_budget(self, client, event_id):
        """GET /events/{id} must use ≤15 queries for any event in the load test set."""
        n = _count_queries_for(client, f"/events/{event_id}")
        assert n <= QUERY_BUDGET, (
            f"GET /events/{event_id} used {n} queries — exceeds budget of {QUERY_BUDGET}.\n"
            f"N+1 regression detected. Use selectinload()/joinedload() or batch IN queries.\n"
            f"See tests/performance/DB_PROFILING_300VU.md for patterns."
        )

    def test_event_31_is_the_heaviest_case(self, client):
        """Event 31 (16 rankings + 32 sessions) must be within budget — proves N-independence."""
        n = _count_queries_for(client, "/events/31")
        assert n <= QUERY_BUDGET, (
            f"Event 31 used {n} queries (heaviest load test case). "
            f"Budget: {QUERY_BUDGET}. Fix N+1 before raising budget."
        )
        # Also assert it uses more than 3 queries (sanity — confirms real DB access)
        assert n >= 3, f"Suspiciously low query count ({n}) — may indicate test isolation issue"
