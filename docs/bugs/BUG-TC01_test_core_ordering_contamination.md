# BUG-TC01 — test_core.py ordering contamination via MatchStructure backref

**Status:** Tracked / Not yet fixed
**Severity:** Low (only affects test suite order; production unaffected)
**Discovered:** 2026-02-18 during P1 scoring pipeline audit

---

## Symptom

Running the full unit suite (`pytest tests/unit/tournament/`) produces 2 failures:

```
FAILED tests/unit/tournament/test_core.py::TestDeleteTournament::test_delete_tournament_cascades_to_sessions
FAILED tests/unit/tournament/test_core.py::TestDeleteTournament::test_delete_tournament_cascades_to_bookings

psycopg2.errors.UndefinedTable: relation "match_structures" does not exist
```

Both tests **pass in isolation** (`pytest tests/unit/tournament/test_core.py`).

---

## Root Cause (confirmed)

### Step 1 — Missing migration

`app/models/match_structure.py` defines the `MatchStructure` ORM model with
`__tablename__ = "match_structures"` and `ForeignKey("sessions.id")`. This
table has **never been migrated** to the test DB. The existing migration
`98e008cea123` ("add_match_structure_fields_to_sessions") only adds columns
to the `sessions` table — it does not CREATE `match_structures`.

### Step 2 — Backref registration on first import

`MatchStructure` declares:

```python
session = relationship("Session", backref="match_structure")
```

This `backref` is registered on the `Session` SQLAlchemy mapper **lazily** —
only when `app.models.match_structure` is first imported.

### Step 3 — Integration test triggers import

`test_campus_scope_guard_integration.py` imports `from app.main import app`,
which transitively imports all models (via `app/models/__init__.py` or similar),
including `MatchStructure`. After this import, every subsequent use of the
SQLAlchemy `Session` model in the same process now carries the
`match_structure` backref relationship.

### Step 4 — Cascade delete fails

`test_delete_tournament_cascades_to_sessions` deletes `SessionModel` objects
via SQLAlchemy `session.delete()`. SQLAlchemy now processes the `match_structure`
backref during the cascade flush, emitting:

```sql
SELECT match_structures.id
FROM match_structures
WHERE match_structures.session_id = ...
```

Since `match_structures` doesn't exist, PostgreSQL raises `UndefinedTable`,
aborting the transaction. The `postgres_db` SAVEPOINT session is now in an
error state for that test function.

---

## Ordering dependency

Contaminating file: `test_campus_scope_guard_integration.py`
Contaminated tests: `test_core.py::TestDeleteTournament::test_delete_tournament_cascades_to_sessions` and `::test_delete_tournament_cascades_to_bookings`

Alphabetical collection order guarantees:
`test_campus_scope_guard_integration.py` **always** runs before `test_core.py`.

---

## Fix options

### Option A — Create the missing migration (recommended)

Generate an Alembic revision that creates `match_structures` and
`match_results` tables in the DB:

```bash
alembic revision --autogenerate -m "create_match_structures_and_match_results"
alembic upgrade head
```

This is the correct long-term fix — aligns DB schema with ORM model.

### Option B — `passive_deletes=True` on the backref (minimal)

Change in `app/models/match_structure.py`:

```python
session = relationship("Session", backref=backref("match_structure", passive_deletes=True))
```

`passive_deletes=True` tells SQLAlchemy to skip the in-memory relationship
cleanup and rely on the DB's ON DELETE CASCADE. SQLAlchemy will no longer
query `match_structures` during Session deletion.
Requires: `REFERENCES sessions(id) ON DELETE CASCADE` in the actual FK DDL.

### Option C — Isolate integration tests (workaround only)

Move `test_campus_scope_guard_integration.py` to a separate directory
(`tests/integration/`) and exclude it from the standard unit suite:

```bash
pytest tests/unit/tournament/  # no contamination
pytest tests/integration/      # separate run
```

---

## Current mitigation

`test_delete_tournament_cascades_to_sessions` and `test_delete_tournament_cascades_to_bookings`
are marked `@pytest.mark.xfail(strict=False, reason="KNOWN-BUG-TC01: ...")`.

They show as `xfail` when contaminated (expected) and as `xpass` when the
integration test hasn't run yet (also acceptable — strict=False means xpass
does not fail CI).

---

## Related

- `app/models/match_structure.py` — MatchStructure + MatchResult models (unmigrated)
- `alembic/versions/2026_01_22_1227-98e008cea123_add_match_structure_fields_to_sessions.py` — adds
  columns to sessions, does NOT create match_structures table
- `tests/unit/tournament/test_campus_scope_guard_integration.py` — contaminating test file
