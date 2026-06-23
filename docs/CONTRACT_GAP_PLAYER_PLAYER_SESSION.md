# Contract Gap: Pure Player–Player Session (No Instructor/Coordinator)

**Status:** Identified — not supported in current domain model
**Identified during:** PR #332 staging E2E smoke (2026-06-23)
**Affects:** `POST /api/v1/multicamera/sessions` + session transitions

## Current Behaviour

1. `POST /sessions` → creator is **always** auto-joined as participant role
   `"instructor"` ([sessions.py:163](../app/api/api_v1/endpoints/multicamera/sessions.py#L163)).
2. All session state transitions (`devices_ready`, `recording_pending`, `stopped`,
   etc.) require `_require_instructor` guard — HTTP 403 for any non-instructor
   participant ([sessions.py:100-104](../app/api/api_v1/endpoints/multicamera/sessions.py#L100-L104)).
3. A STUDENT `UserRole` user CAN create a session (the endpoint checks
   `is_active` only, not `UserRole`), but is **forced** into instructor
   participant role by the backend.

## Consequence

A session with two player-only participants cannot complete its lifecycle:
no one can transition the session past `lobby`. The creator is always the
coordinator, regardless of their account role.

## Why This Is By Design (Current Model)

The multicamera session uses a **server-authority coordinator model**:
one designated participant (the instructor) synchronises capture start/stop
across all devices via `scheduled_start_at`. Without a coordinator, there
is no authority to trigger `recording_pending` → synchronized capture.

## Future Options (Requires Separate Approval)

| Option | Description | Complexity |
|--------|-------------|------------|
| A. Peer election | First `ready` device becomes coordinator | Medium — needs election protocol + conflict resolution |
| B. Server auto-start | Server triggers `recording` after all devices `ready`, no human coordinator | Low — but removes manual start control |
| C. Player-coordinator | Allow a player participant to hold transition rights | Low — relax `_require_instructor` to `_require_coordinator` with a new flag |
| D. No change | Accept coordinator model as product decision — two-player sessions always have one player acting as coordinator | None |

## Recommendation

Option D (no change) for PR #332 scope. The coordinator model is intentional
for multicamera capture synchronisation. If a pure player–player mode is
needed, Option C is the lowest-risk path: add a `is_coordinator` flag on
`SessionParticipant` and check that instead of participant role.

## Testing Implication

Scenario A in the staging smoke tests a session created by a STUDENT account.
The creator is forced into instructor participant role. This validates that
`UserRole` does not block session creation, but it does **not** prove
instructor-free player–player functionality.
