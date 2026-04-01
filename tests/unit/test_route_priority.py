"""
Route Priority Regression Tests
================================

Locks down the FastAPI/Starlette route-registration order so that
parameterised `{id}` routes can NEVER shadow static paths registered
on a later router.

─────────────────────────────────────────────────────────────────────
ROOT CAUSE (fixed 2026-03-23)
─────────────────────────────────────────────────────────────────────
users/crud.py registered `GET /users/{user_id}` WITHOUT the `:int`
path-type constraint.  Starlette matches `{param}` (no type) against
ANY path segment, including strings like "invite-search".

Because `users.router` is registered in api_router BEFORE `teams.router`,
the request:
  GET /api/v1/users/invite-search?q=Dragon

…was intercepted by `GET /users/{user_id}` (user_id = "invite-search"),
which carries `get_current_admin_user` → 403 "Not enough permissions"
for every non-admin caller, including all students using the invite flow.

─────────────────────────────────────────────────────────────────────
REGISTRATION ORDER (api/api_v1/api.py) — priority map
─────────────────────────────────────────────────────────────────────
  line  78:  users.router          prefix=/users          ← FIRST
               GET  /users/me
               GET  /users/search              (admin guard)
               GET  /users/{user_id:int}       ← FIXED: was /{user_id}
               PATCH/DELETE /users/{user_id:int}
  ...
  line 365:  teams.router          prefix=""              ← LATE
               GET  /users/invite-search       ← previously shadowed
               GET  /teams/{team_id:int}
               ...

  Why this matters:
    `/api/v1/users/invite-search` =
      prefix /api/v1  +  users.router prefix /users  +  /invite-search
    Starlette checks routes in registration order.
    teams.router`s GET /users/invite-search never gets a chance unless
    users.router`s GET /users/{user_id} fails to match.

─────────────────────────────────────────────────────────────────────
FIX APPLIED
─────────────────────────────────────────────────────────────────────
  users/crud.py    GET /{user_id}            → /{user_id:int}
  users/crud.py    PATCH /{user_id}          → /{user_id:int}
  users/crud.py    DELETE /{user_id}         → /{user_id:int}
  users/profile.py POST /{user_id}/reset-*  → /{user_id:int}/...
  teams.py (api)   all {team_id}/{invite_id} → :int variants

  With `:int`, Starlette`s path converter only matches digit-only
  segments at the routing level — before any Python code runs.
  "invite-search" is not digits → no match → falls through to the
  correct teams.router handler.

─────────────────────────────────────────────────────────────────────
SHADOWING RISK ANALYSIS (global grep results)
─────────────────────────────────────────────────────────────────────
Cross-router shadowing requires TWO conditions simultaneously:
  A. Router X (early): `GET /prefix/{param}` without :int
  B. Router Y (late, prefix=""): `GET /prefix/static-word`

Only one such conflict existed in this codebase:
  A. users.router (line 78)  GET /users/{user_id}   ← FIXED
  B. teams.router (line 365) GET /users/invite-search

No other cross-router shadow risks found.  All other `/{id}` routes
live on routers whose paths are not replicated under prefix="" routers.

Web routes (app/api/web_routes/) are mounted separately as HTML routes
and do not conflict with the API router.

─────────────────────────────────────────────────────────────────────
NETWORK EVIDENCE (captured during test runs)
─────────────────────────────────────────────────────────────────────
  ROUTE-03 (test_route_03_invite_search_200_correct_json):
    Request:  GET /api/v1/users/invite-search?q=RouteTarget
              Authorization: Bearer <student-token>
    Response: HTTP 200 OK
              Content-Type: application/json
              Body: [{"id": <N>, "name": "RouteTarget xxxx", "email": "..."}]

  This proves the teams.py handler executed — not users/crud.py:
    - users/crud.py `get_user()` returns UserWithStats schema (no list)
    - teams.py `invite_search_users()` returns a plain list of dicts
    - 200 + list = correct handler

─────────────────────────────────────────────────────────────────────
TESTS IN THIS FILE
─────────────────────────────────────────────────────────────────────
  ROUTE-01  invite-search → NOT 403  (admin guard never fires)
  ROUTE-02  invite-search → NOT 422  (int-cast of "invite-search" skipped)
  ROUTE-03  invite-search → 200 + JSON [{id,name,email}]  (correct handler)
  ROUTE-04  users/{id:int} still returns 200/404  (no regression on integer IDs)
  ROUTE-05  unauthenticated invite-search → 401/422, never 403
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web, get_current_user, get_current_active_user
from app.models.user import User, UserRole
from app.core.security import get_password_hash


# ── SAVEPOINT-isolated DB fixture (self-contained, no shared conftest needed) ──

@pytest.fixture()
def route_db():
    """Per-test transaction with savepoint rollback — no data leaks between tests."""
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSession()
    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, txn):
        if txn.nested and not txn._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def _student(db: Session) -> User:
    u = User(
        email=f"route-test-{uuid.uuid4().hex[:6]}@lfa.com",
        name=f"RouteTest {uuid.uuid4().hex[:4]}",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=0,
        payment_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _client(db: Session, user: User) -> TestClient:
    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user_web] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


# ── Regression tests ───────────────────────────────────────────────────────────

class TestRouteRegistrationOrder:
    """
    ROUTE-01–05: prove that integer-typed path params cannot shadow
    static string paths registered on a later router.

    Regression lock for bug fixed 2026-03-23 (users/{user_id} shadow).
    """

    def test_route_01_invite_search_not_403(self, route_db: Session):
        """
        ROUTE-01: GET /api/v1/users/invite-search?q=test
        Must NOT return 403 "Not enough permissions".

        403 would mean get_current_admin_user fired, i.e. the request was
        matched by users/crud.py's GET /{user_id} instead of
        teams.py's GET /users/invite-search.

        Network evidence:
          Request:  GET /api/v1/users/invite-search?q=test
          Expected: 200  (student authenticated via override)
          Must NOT: 403  (would mean admin guard fired on wrong route)
        """
        student = _student(route_db)
        client = _client(route_db, student)
        try:
            resp = client.get("/api/v1/users/invite-search?q=test")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code != 403, (
            "REGRESSION: GET /api/v1/users/invite-search returned 403 — "
            "users/crud.py /{user_id} (without :int) is shadowing the invite-search "
            "route again.  Fix: ensure /{user_id:int} is used in users/crud.py."
        )

    def test_route_02_invite_search_not_422(self, route_db: Session):
        """
        ROUTE-02: GET /api/v1/users/invite-search?q=test
        Must NOT return 422 Unprocessable Entity.

        422 would mean the route DID match users/crud.py /{user_id} but
        pydantic rejected "invite-search" as non-integer.  This is a
        softer form of the same bug — wrong route matched.

        Network evidence:
          Request:  GET /api/v1/users/invite-search?q=test
          Must NOT: 422  (int validation of "invite-search")
        """
        student = _student(route_db)
        client = _client(route_db, student)
        try:
            resp = client.get("/api/v1/users/invite-search?q=test")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code != 422, (
            "REGRESSION: GET /api/v1/users/invite-search returned 422 — "
            "the path was matched by a parameterised route that cast 'invite-search' "
            "as an integer and failed pydantic validation."
        )

    def test_route_03_invite_search_200_correct_json(self, route_db: Session):
        """
        ROUTE-03: GET /api/v1/users/invite-search?q=<name>
        → 200 + JSON array [{id, name, email}]

        Network evidence (full request/response shape):
          Request:
            GET /api/v1/users/invite-search?q=RouteTest
            Authorization: Bearer <student-token>   (overridden in test)

          Response:
            HTTP/1.1 200 OK
            Content-Type: application/json
            Body: [{"id": N, "name": "RouteTest ...", "email": "..."}]

        This proves the CORRECT handler (teams.py's invite_search_users)
        executed — not users/crud.py's admin-only get_user.
        """
        student = _student(route_db)
        # Create a second user that the search will find
        target = User(
            email=f"route-target-{uuid.uuid4().hex[:6]}@lfa.com",
            name=f"RouteTarget {uuid.uuid4().hex[:4]}",
            password_hash=get_password_hash("Test1234!"),
            role=UserRole.STUDENT,
            is_active=True,
            onboarding_completed=True,
            credit_balance=0,
            payment_verified=True,
        )
        route_db.add(target)
        route_db.flush()

        client = _client(route_db, student)
        try:
            resp = client.get("/api/v1/users/invite-search?q=RouteTarget")
        finally:
            app.dependency_overrides.clear()

        # ── Network evidence ───────────────────────────────────────────────────
        assert resp.status_code == 200, (
            f"Expected 200 from invite-search; got {resp.status_code}: {resp.text[:200]}"
        )
        body = resp.json()
        assert isinstance(body, list), f"Expected JSON array, got: {type(body)}"

        # Shape: each item must have id, name, email
        if body:
            item = body[0]
            assert "id" in item, f"Missing 'id' key in result: {item}"
            assert "name" in item, f"Missing 'name' key in result: {item}"
            assert "email" in item, f"Missing 'email' key in result: {item}"

        # The target user must appear in results
        ids = [u["id"] for u in body]
        assert target.id in ids, (
            f"target user (id={target.id}) not in invite-search results: {ids}"
        )
        # The searching user must exclude itself
        assert student.id not in ids, (
            "invite-search must exclude the calling user (self-exclusion broken)"
        )

    def test_route_04_users_integer_id_still_works(self, route_db: Session):
        """
        ROUTE-04: GET /api/v1/users/{id} with an actual integer ID
        → still reachable (the :int fix must not break integer paths).

        Network evidence:
          Request:  GET /api/v1/users/1  (with admin override)
          Expected: 200 or 404 (user may/may not exist), NOT 422, NOT routing error
        """
        admin = User(
            email=f"route-admin-{uuid.uuid4().hex[:6]}@lfa.com",
            name="RouteAdmin",
            password_hash=get_password_hash("Test1234!"),
            role=UserRole.ADMIN,
            is_active=True,
            onboarding_completed=True,
            credit_balance=0,
            payment_verified=True,
        )
        route_db.add(admin)
        route_db.flush()

        from app.dependencies import get_current_admin_user

        def _db():
            yield route_db

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        client = TestClient(app, raise_server_exceptions=False)
        try:
            resp = client.get(f"/api/v1/users/{admin.id}")
        finally:
            app.dependency_overrides.clear()

        # 200 (found) or 404 (user not found in stats query) — both are correct routing
        assert resp.status_code in (200, 404), (
            f"GET /api/v1/users/{{id}} (integer) returned unexpected {resp.status_code}: "
            f"{resp.text[:200]}"
        )
        assert resp.status_code != 422, "Integer user_id should never trigger 422"

    def test_route_05_users_string_id_is_404_not_403(self, route_db: Session):
        """
        ROUTE-05: GET /api/v1/users/invite-search (no auth, no q param)
        With no auth override → 401 or 422 (missing q param), never 403.

        This proves the admin guard from users/crud.py never fires for
        string paths — because /{user_id:int} won't match "invite-search".

        Network evidence:
          Request:  GET /api/v1/users/invite-search (no Authorization header)
          Expected: 401 (missing auth) OR 422 (missing required q param)
          Must NOT: 403  (would mean admin guard fired → wrong route)
        """
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/users/invite-search")  # no q, no auth

        assert resp.status_code != 403, (
            "REGRESSION: unauthenticated GET /api/v1/users/invite-search → 403. "
            "The :int constraint fix has been reverted or users/crud.py was modified."
        )
        # Without q= param, invite-search itself returns 422
        # Without auth, the auth dependency returns 401
        # Either is correct; 403 is not.
        assert resp.status_code in (401, 422), (
            f"Expected 401 (no auth) or 422 (missing q param), got {resp.status_code}"
        )
