# SCHED Discipline — Scheduling Core Freeze Rules
**Effective: 2026-04-17 | Rollback tag: `v1.0-scheduling-core` (SHA 7366926)**

---

## What Is Frozen

The scheduling/enrollment core is **hard verified** as of `v1.0-scheduling-core`:
- 88/88 business flows covered (100%)
- 24/24 `@pytest.mark.sched` tests green on CI
- 3 invariant smoke tests (SCHED_INV-01..03)
- 5 guard negative-path tests (SCHED_G3-11..15)
- 2 runtime production guards (GUARD-01 credit, GUARD-02 capacity)

This is a rollback point, not a development freeze. New features are welcome
— but the discipline rules below are **non-negotiable before merge**.

---

## Core Invariants (never break)

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-01 | `user.credit_balance >= 0` always | 3-layer: app check → conditional UPDATE rowcount → DB CHECK constraint + GUARD-01 runtime alert |
| INV-02 | `confirmed_count(session) <= session.capacity` always | Pessimistic lock (`with_for_update()`) + GUARD-02 runtime alert |
| INV-03 | `SemesterEnrollment` unique per `(user_id, semester_id, user_license_id)` | DB UNIQUE constraint + app-level duplicate check |

---

## Feature Gate — Mandatory Before Merge

Every commit that touches **any** of these files:

```
app/api/web_routes/programs.py
app/services/semester_service.py
app/api/api_v1/endpoints/semesters/schedule_generator.py
app/api/api_v1/endpoints/bookings/helpers.py
app/services/runtime_guards.py
```

**MUST include at least one of:**

1. A new `@pytest.mark.sched` test covering the changed behavior, OR
2. A new invariant test (`SCHED_INV-*`) if touching credit/capacity/booking logic

**AND** the CI gate must be green:
```
e2e-scheduling.yml → pytest -m sched → ALL sched tests pass
```

No green CI = no phase complete. No green CI = no merge.

---

## Runtime Guards (production, non-blocking)

File: `app/services/runtime_guards.py`

| Guard | Trigger | Log level | Metric |
|-------|---------|-----------|--------|
| `GUARD-01` `guard_credit_balance()` | post-enroll, post-withdraw | CRITICAL | `invariant_violations_total` |
| `GUARD-02` `guard_capacity()` | post-enroll (per CONFIRMED booking) | CRITICAL | `invariant_violations_total` |

**If `invariant_violations_total > 0` on `/metrics`**: stop, investigate, fix before next deploy.

---

## Current Test Map (24 tests)

```
SCHED_G1-01..04  Session generation API (generate, conflict-block, skip-conflicts, attendance-guard)
SCHED_G2-01..02  Admin web UI (schedule page render, web form generate)
SCHED_G3-01..15  Student enrollment flows:
  01  browse page renders
  02  auto-enroll (credits + sessions booked)
  03  session visibility after enroll
  04  withdraw (50% refund + bookings deleted)
  05  capacity enforcement (WAITLISTED when full)
  06  re-enrollment after withdraw
  07  waitlist auto-promote on withdraw
  08  audit log on enroll
  09  enrollment blocked when semester COMPLETED
  10  session delete cleans bookings
  11  role guard (INSTRUCTOR blocked)             ← audit addition
  12  license guard (no license blocked)          ← audit addition
  13  duplicate guard (already enrolled blocked)  ← audit addition
  14  credit guard (insufficient credits blocked) ← audit addition
  15  ownership guard (wrong user withdraw blocked) ← audit addition
SCHED_INV-01..03  Invariant smoke tests (credit exact math, capacity count, post-withdraw count)
```

---

## Documented Design Gaps (accepted)

These are known limitations, documented as accepted, no new tests required:

1. **Waitlist positions NULL** — `semester_service.py` creates WAITLISTED bookings without
   `waitlist_position`. `auto_promote_from_waitlist` orders by position ASC (NULL LAST in PG),
   so promotion order within a semester enrollment is **non-deterministic** (not FIFO).
   Tests only check COUNT invariants, not which user is promoted. Accepted.

2. **Odd-cost refund truncation** — `cost // 2` with odd cost truncates down (e.g. 3→1).
   Only even costs are tested. Accepted: integer division is intentional business rule.

3. **Concurrent enrollment race E2E not tested** — The `rowcount=0` path (atomic UPDATE guard)
   requires parallel requests. DB constraint is the final guard. Accepted documented limitation.

---

## Rollback Procedure

```bash
# Inspect the tag
git show v1.0-scheduling-core

# Restore to tag in a new branch
git checkout -b rollback/pre-phase6 v1.0-scheduling-core

# Or create a clean deploy from tag
git checkout v1.0-scheduling-core
```

Tag: `v1.0-scheduling-core` = SHA `7366926` (2026-04-17)
