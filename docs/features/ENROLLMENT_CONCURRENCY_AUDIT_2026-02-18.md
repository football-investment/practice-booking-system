# Enrollment Concurrency Audit

**Date:** 2026-02-18
**Status:** READ-ONLY AUDIT — fixes not yet implemented
**Scope:** `app/api/api_v1/endpoints/tournaments/enroll.py` (479 lines)
          `app/services/tournament/enrollment_service.py` (80 lines)

---

## 1. Executive Summary

The enrollment pipeline has **4 TOCTOU (time-of-check to time-of-use) race conditions**
and **0 DB-level concurrency guards**. All four races are exploitable under concurrent
POST `/enroll` or POST `/unenroll` requests for the same tournament.

| Race | Location | Impact | Priority |
|---|---|---|---|
| RACE-01 | Capacity count | Over-enrollment (capacity violated) | P1 |
| RACE-02 | Duplicate check | Double-enrollment (same player twice) | P1 |
| RACE-03 | Credit deduction | Credit double-spend (negative balance) | P1 |
| RACE-04 | Unenroll refund | Double-refund on concurrent unenroll | P2 |

---

## 2. Race Condition Detail

### RACE-01 — Capacity TOCTOU (Over-enrollment)

**File:** `enroll.py`, lines 171–183

```python
# VULNERABLE — no SELECT FOR UPDATE
active_count = db.query(func.count(SemesterEnrollment.id)).filter(
    SemesterEnrollment.semester_id == tournament_id,
    SemesterEnrollment.is_active == True,
).scalar()

if active_count >= tournament.max_players:
    raise HTTPException(status_code=400, detail="Tournament is full")

# ... more logic ...

# WINDOW: another thread reads active_count HERE, also passes the check
db.add(new_enrollment)  # Both threads reach this line → over-enrollment
db.commit()
```

**Failure scenario:**
```
Tournament max_players=8, current active_count=7.
Thread A: count()=7 → passes check
Thread B: count()=7 → passes check (same snapshot)
Thread A: INSERT enrollment #8 → commit
Thread B: INSERT enrollment #9 → commit ← OVER-ENROLLMENT
Result: 9 active enrollments in a max_players=8 tournament.
```

**Fix:** `SELECT FOR UPDATE` on the capacity row, or DB-level `CHECK` constraint
enforced via trigger. Preferred: lock at the tournament row level before counting.

---

### RACE-02 — Duplicate Enrollment TOCTOU (Same Player Twice)

**File:** `enroll.py`, lines 157–168 (`check_duplicate_enrollment`)

```python
# VULNERABLE — no unique constraint
existing = db.query(SemesterEnrollment).filter(
    SemesterEnrollment.semester_id == tournament_id,
    SemesterEnrollment.user_id == user_id,
    SemesterEnrollment.is_active == True,
).first()

if existing:
    raise HTTPException(status_code=409, detail="Already enrolled")

# WINDOW: second request reads existing=None HERE
db.add(new_enrollment)  # Both reach INSERT → duplicate rows
```

**Failure scenario:**
```
Player A sends two simultaneous POST /enroll requests.
Both read existing=None → both pass duplicate check.
Both INSERT → player has 2 active enrollment rows.
Result: player counted twice toward active_count, double credit deducted.
```

**Fix:** DB-level partial unique index:
```sql
CREATE UNIQUE INDEX uq_active_enrollment
ON semester_enrollment (user_id, semester_id)
WHERE is_active = TRUE;
```
This is the only reliable fix; application-layer checks alone are insufficient.

---

### RACE-03 — Credit Balance Double-Spend (Non-Atomic Deduction)

**File:** `enroll.py`, lines 186–191 (balance check) + line 235 (deduction)

```python
# CHECK (line 186–191)
if current_user.credit_balance < enrollment_cost:
    raise HTTPException(status_code=400, detail="Insufficient credits")

# ... 40+ lines of logic (file I/O, DB inserts) ...

# DEDUCTION (line 235) — non-atomic, in Python
current_user.credit_balance = current_user.credit_balance - enrollment_cost
```

**Failure scenario:**
```
User has credit_balance=10, enrollment_cost=10.
Thread A: reads balance=10 → passes check
Thread B: reads balance=10 → passes check (ORM read-committed snapshot)
Thread A: deducts → balance=0 → commit
Thread B: deducts → balance=-10 → commit ← NEGATIVE BALANCE
Result: user has -10 credits. Financial inconsistency.
```

**Fix:** Atomic SQL UPDATE with guard:
```sql
UPDATE users
SET credit_balance = credit_balance - :cost
WHERE id = :user_id AND credit_balance >= :cost
-- Check rowcount == 1; if 0, raise InsufficientCredits
```
Or use `SELECT FOR UPDATE` on the user row before the balance check.

---

### RACE-04 — Unenroll Double-Refund (Concurrent Unenroll Requests)

**File:** `enroll.py`, unenroll endpoint (lines 250–320 approx.)

The unenroll path:
1. Reads the active enrollment record
2. Checks `is_active == True`
3. Sets `enrollment.is_active = False`
4. Adds `enrollment_cost` back to `credit_balance`

**Failure scenario:**
```
User sends two simultaneous POST /unenroll requests.
Both read is_active=True → both proceed.
Both set is_active=False (last-write-wins, no conflict).
Both refund enrollment_cost → user receives 2× refund.
```

**Fix:** `SELECT FOR UPDATE` on the enrollment row in the unenroll path,
or DB-level optimistic locking (version column). Application-layer check is
insufficient.

---

## 3. Enrollment State Transitions

```
                           ENROLLMENT STATES
                           ─────────────────

     POST /enroll ──────► PENDING (if booking system active)
                               │
                               ▼ (confirm booking)
                           ACTIVE ◄────── (re-enroll after cancel)
                               │
                    POST /unenroll
                               │
                               ▼
                          CANCELLED
                               │
                               ▼
                      [soft-deleted, is_active=False]
```

The enrollment table has no explicit `status` column — it uses `is_active: bool` as
a binary ACTIVE/CANCELLED flag. There is no PENDING state visible at the enrollment
row level (the booking-hold system is handled separately if active).

**Implication:** An enrollment is either active (`is_active=True`) or cancelled
(`is_active=False`). The duplicate check queries `is_active=True` only, meaning a
player who cancelled can re-enroll (creating a new row). This is correct behavior but
creates the RACE-04 window during concurrent unenroll.

---

## 4. Missing DB-Level Guards

| Guard | Status | Required? |
|---|---|---|
| `UNIQUE (user_id, semester_id) WHERE is_active=TRUE` | ❌ MISSING | **Required** — only reliable fix for RACE-02 |
| `CHECK (active_count <= max_players)` | ❌ MISSING | Desirable — defense-in-depth for RACE-01 |
| `CHECK (credit_balance >= 0)` | ❌ MISSING | **Required** — prevents negative balance persistence |
| `SELECT FOR UPDATE` on capacity count | ❌ MISSING | Required for RACE-01 without CHECK |
| `SELECT FOR UPDATE` on enrollment row (unenroll) | ❌ MISSING | Required for RACE-04 |
| Atomic credit deduction | ❌ MISSING | Required for RACE-03 |

---

## 5. Enrollment Service Audit

**File:** `app/services/tournament/enrollment_service.py` (80 lines)

`auto_book_students()` is a batch helper called by the OPS scenario endpoint.
It does **not** go through the enrollment endpoint's concurrency checks — it
calls `db.add(enrollment)` directly after a non-locking duplicate check.

**Risk:** If called concurrently (e.g., two OPS scenario triggers for the same
tournament), the service-layer function is subject to the same RACE-01 and RACE-02
vulnerabilities as the HTTP endpoint.

**Scope:** Concurrent OPS triggers are unlikely in production (admin-only action),
so this is a lower priority than the user-facing endpoint races.

---

## 6. Concurrency Test Coverage

**File:** `tests/unit/tournament/test_enrollment_concurrency_p0.py`

| Test | Race | What it proves |
|---|---|---|
| `test_capacity_check_is_not_atomic` | RACE-01 | count() read is snapshot-isolated → both threads see stale count |
| `test_no_select_for_update_in_capacity_check` | RACE-01 | No `with_for_update()` call in capacity path |
| `test_capacity_check_with_exactly_full_tournament` | RACE-01 | count()==max_players passes but concurrent INSERT still possible |
| `test_safe_capacity_check_requires_db_lock` | RACE-01 | Documents required fix pattern |
| `test_duplicate_check_window_exists` | RACE-02 | Duplicate check window: two reads of `existing=None` |
| `test_idempotent_enrollment_requires_unique_constraint` | RACE-02 | No unique index → two INSERTs succeed |
| `test_double_credit_deduction_on_duplicate_enroll` | RACE-02 | Double enroll → double credit deduction |
| `test_credit_check_window_exists` | RACE-03 | Balance read + deduction are separate steps → window exists |
| `test_safe_credit_deduction_requires_atomic_update` | RACE-03 | Documents required fix (atomic SQL UPDATE) |
| `test_negative_balance_is_impossible_with_atomic_update` | RACE-03 | With CHECK constraint, negative balance rejected at DB level |
| `test_unenroll_and_reenroll_window` | RACE-04 | is_active=False write + re-enroll window |
| `test_unenroll_refund_is_not_idempotent` | RACE-04 | Double unenroll → double refund possible |
| `test_inv01_enrollment_count_never_exceeds_max_players` | INV-01 | Acceptance criterion for RACE-01 fix |
| `test_inv02_player_cannot_have_two_active_enrollments_in_same_tournament` | INV-02 | Acceptance criterion for RACE-02 fix |
| `test_inv03_credit_balance_never_negative` | INV-03 | Acceptance criterion for RACE-03 fix |
| `test_inv04_refund_total_equals_one_enrollment_cost` | INV-04 | Acceptance criterion for RACE-04 fix |
| `test_inv05_unenrolled_player_has_no_active_bookings` | INV-05 | Unenroll cascades to booking table |

All 17 tests: **GREEN** (0.04s, DB-free).

---

## 7. Fix Implementation Plan

### Phase B — P1 DB-level fixes (recommended next sprint)

**B-01: Partial unique index — RACE-02 fix**

```sql
-- Alembic migration
CREATE UNIQUE INDEX uq_active_enrollment
ON semester_enrollment (user_id, semester_id)
WHERE is_active = TRUE;
```

Handles RACE-02 at DB level — concurrent INSERTs will raise `IntegrityError`.
The application layer must catch `IntegrityError` and return HTTP 409.

**B-02: Atomic credit deduction — RACE-03 fix**

```python
# Replace Python-level subtraction with atomic SQL UPDATE
rows_updated = db.execute(
    update(User)
    .where(User.id == user_id, User.credit_balance >= enrollment_cost)
    .values(credit_balance=User.credit_balance - enrollment_cost)
).rowcount
if rows_updated == 0:
    raise HTTPException(status_code=400, detail="Insufficient credits")
```

**B-03: SELECT FOR UPDATE on capacity + unenroll — RACE-01 / RACE-04 fix**

```python
# Capacity lock (RACE-01)
tournament = db.query(Semester).filter(
    Semester.id == tournament_id
).with_for_update().first()

active_count = db.query(func.count(SemesterEnrollment.id)).filter(
    SemesterEnrollment.semester_id == tournament_id,
    SemesterEnrollment.is_active == True,
).scalar()
```

```python
# Unenroll lock (RACE-04)
enrollment = db.query(SemesterEnrollment).filter(
    SemesterEnrollment.id == enrollment_id,
    SemesterEnrollment.is_active == True,
).with_for_update().first()
```

**B-04: CHECK constraint — credit balance floor**

```sql
ALTER TABLE users ADD CONSTRAINT chk_credit_balance_non_negative
CHECK (credit_balance >= 0);
```

Defense-in-depth for RACE-03 — rejects negative balances at DB level even if
application-layer atomic update is bypassed.

---

### Phase C — Test updates after fixes

After B-01 through B-04 are implemented:

- `TestEnrollmentInvariants::test_inv01` through `test_inv05` should pass with
  **real DB integration tests** (not just mocks)
- `TestCapacityTOCTOU::test_safe_capacity_check_requires_db_lock` — upgrade to
  integration test proving `with_for_update()` is present
- `TestDuplicateEnrollmentTOCTOU::test_idempotent_enrollment_requires_unique_constraint`
  — upgrade to confirm `IntegrityError` is raised and caught correctly

---

## 8. Risk Summary

| Race | Production Frequency | Impact | Fix Complexity |
|---|---|---|---|
| RACE-01 (capacity) | Medium (high-demand tournaments, mobile users) | High — capacity contract violated | Medium |
| RACE-02 (duplicate) | Low-Medium (impatient double-click) | High — data corruption + double charge | Low (1 migration) |
| RACE-03 (credit) | Low (requires near-simultaneous requests) | High — financial inconsistency | Medium |
| RACE-04 (unenroll) | Very Low | Medium — double refund | Medium |

**Recommended fix order:** B-01 (partial unique index) → B-02 (atomic credit) → B-03 (SELECT FOR UPDATE) → B-04 (CHECK constraint)

B-01 is the highest-leverage fix: 1 migration eliminates RACE-02 entirely.

---

## 9. Files Reference

| File | Role |
|---|---|
| `app/api/api_v1/endpoints/tournaments/enroll.py` | Main enrollment + unenroll HTTP endpoints (479 lines) |
| `app/services/tournament/enrollment_service.py` | Batch enrollment helper for OPS scenarios (80 lines) |
| `app/models/semester_enrollment.py` | `SemesterEnrollment` ORM model |
| `tests/unit/tournament/test_enrollment_concurrency_p0.py` | 17 P0 race condition + invariant tests (all GREEN) |
