# SM-BUG-01 — IN_PROGRESS→ENROLLMENT_CLOSED Rollback Guard Collision

**Priority:** P2 — Operational (rare but blocks admin recovery path)
**Status:** Documented / Fix designed / Not yet implemented
**Discovered:** 2026-02-18 during state machine audit sprint
**Tests:** `test_state_machine.py::TestRollbackEdgeInProgressToEnrollmentClosed`

---

## Problem

`IN_PROGRESS → ENROLLMENT_CLOSED` is an intentional admin rollback edge for
tournaments stuck in `IN_PROGRESS` with 0 sessions generated (e.g., an OPS
scenario failure after enrollment closed but before session generation completed).

**The guard collision:** `validate_status_transition()` applies the same guard
for both the forward edge and the rollback edge:

```python
if new_status == "ENROLLMENT_CLOSED":
    active_enrollments = [e for e in enrollments if e.is_active]
    player_count = len(active_enrollments)
    if player_count < min_players_required:  # default: 2
        return False, f"Cannot close enrollment: Minimum ..."
```

This guard was designed for `ENROLLMENT_OPEN → ENROLLMENT_CLOSED`, meaning:
"don't close enrollment if nobody signed up." For the rollback case
(`IN_PROGRESS → ENROLLMENT_CLOSED`), the semantics are different:
"let the admin rewind to fix a stuck tournament."

**Failure scenario:**

```
1. Tournament IN_PROGRESS, 8 players enrolled
2. OPS scenario runs, crashes before session generation
3. Admin deactivates some players via enrollment management
4. Active enrollment count drops to 1
5. Admin tries rollback: IN_PROGRESS → ENROLLMENT_CLOSED
   → BLOCKED: "Cannot close enrollment: Minimum 2 participants required (current: 1)"
6. Admin is stuck — cannot use the API to fix the tournament
```

---

## Affected Code

```
app/services/tournament/status_validator.py
Lines 89–110: "ENROLLMENT_CLOSED" guard (shared between forward and rollback)
```

---

## Reproduction

```python
# From test_state_machine.py::TestRollbackEdgeInProgressToEnrollmentClosed
t = _tournament(enrollments=[])  # or _active_enrollments(1)
ok, err = validate_status_transition("IN_PROGRESS", "ENROLLMENT_CLOSED", t)
assert ok is False  # SM-BUG-01: rollback blocked
```

---

## Fix Design (P2)

### Option A — Source-state-aware guard (recommended)

In `validate_status_transition()`, bifurcate the `ENROLLMENT_CLOSED` guard
on the `current_status` argument:

```python
if new_status == "ENROLLMENT_CLOSED":
    # Rollback path: admin rewinding a stuck IN_PROGRESS tournament
    # Player count guard is irrelevant — admin explicitly chose to rewind
    if current_status == "IN_PROGRESS":
        pass  # allow unconditionally (graph already validated above)
    else:
        # Forward path: ENROLLMENT_OPEN → ENROLLMENT_CLOSED
        # Player count must meet minimum
        active_enrollments = [e for e in enrollments if e.is_active]
        player_count = len(active_enrollments)
        min_players_required = _get_min_players(tournament)
        if player_count < min_players_required:
            return False, f"Cannot close enrollment: Minimum {min_players_required} ..."
```

**Impact:** Only affects `IN_PROGRESS → ENROLLMENT_CLOSED` path. Forward
path unchanged. 2 new tests to add (rollback with 0 and 1 players now pass).

### Option B — Admin-only bypass via `reason` field (looser)

Add an explicit `force_rollback: bool = False` parameter to
`validate_status_transition()`. The HTTP endpoint passes `force_rollback=True`
only when `current_user.role == ADMIN` and `new_status == ENROLLMENT_CLOSED`.

```python
def validate_status_transition(
    current_status, new_status, tournament, *, force_rollback=False
) -> Tuple[bool, Optional[str]]:
    ...
    if new_status == "ENROLLMENT_CLOSED" and force_rollback:
        return True, None  # admin bypass
```

This requires changing the API endpoint signature, which is a larger change.

### Recommendation

**Option A** is the correct fix. The guard was written without the rollback
edge in mind. Source-state-aware bifurcation is the minimal, correct change.
No API changes needed.

---

## Implementation Checklist

- [ ] Update `validate_status_transition()` guard for `ENROLLMENT_CLOSED`
      to skip player count check when `current_status == "IN_PROGRESS"`
- [ ] Update `test_state_machine.py::TestRollbackEdgeInProgressToEnrollmentClosed`:
      `test_rollback_blocked_when_no_players` and
      `test_rollback_blocked_when_one_player` should become `assert ok is True`
      after the fix
- [ ] Add regression test: rollback succeeds even with 0 active enrollments
- [ ] Verify forward path (`ENROLLMENT_OPEN → ENROLLMENT_CLOSED`) still
      blocked when player count insufficient

---

## Risk Assessment

| Dimension | Assessment |
|---|---|
| Production frequency | Rare (requires OPS crash + enrollment management before rollback) |
| Admin impact | Medium (blocked recovery path, may force DB-level intervention) |
| Fix complexity | Low (3-line change in status_validator.py) |
| Regression risk | Low (guard only relaxed on the rollback sub-path) |
| Priority | P2 — fix before next production OPS scenario |
