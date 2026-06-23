# Staging Smoke Report — 2026-06-23

## Deployment

| Field | Value |
|-------|-------|
| Staging branch | `deploy/vercel-staging` HEAD `1fa5e9d6` |
| PR #332 branch | `feat/an3b-pr4b3b1b-session-orchestration` HEAD `1619d363` |
| Vercel URL | `practice-booking-system-git-deploy-vercel-staging-lfa-ec-test.vercel.app` |
| Neon endpoint | `ep-plain-boat-aibz4ju6` (staging) |
| Alembic head | `2026_06_22_2000` |
| Health | `{"status":"ok","database":"connected","variant":"staging"}` |

## Three Staging Users

| Email | UserRole | User ID | Purpose |
|-------|----------|---------|---------|
| `staging-player1@lfa-staging.io` | STUDENT | distinct | Scenario A creator / B+C player |
| `staging-player2@lfa-staging.io` | STUDENT | distinct | Scenario A+C player |
| `staging-instructor@lfa-staging.io` | INSTRUCTOR | distinct | Scenario B+C creator/coordinator |

All three user IDs verified distinct. Passwords chosen by tester, stored in
password manager, never logged.

## Scenario Results

### Scenario A: STUDENT-coordinator + STUDENT-player

**Domain note:** Creator is forced into `instructor` participant role by backend
([sessions.py:163](../app/api/api_v1/endpoints/multicamera/sessions.py#L163)).
This does NOT prove pure player–player functionality. See
[CONTRACT_GAP_PLAYER_PLAYER_SESSION.md](CONTRACT_GAP_PLAYER_PLAYER_SESSION.md).

| Step | HTTP | Result |
|------|------|--------|
| S1 create (P1=creator) | 201 | session created, P1→instructor participant |
| S2 join (P2) | 200 | P2→player participant |
| S3a device P1 (ipad/instructor_primary) | 201 | registered |
| S3b device P2 (iphone/player_primary) | 201 | registered |
| S4 both → ready | 200 | both devices ready |
| S5 devices_ready | 200 | session transition OK |
| S6 recording_pending | 200 | scheduled_start_at not null |
| S7 streams (2×) | 201 | 2 capture streams created |
| S8 capture_result (2×) | 200 | both success, duration_ms computed |
| S9 readback + validation | 200 | 2 participants, 2 devices, user_ids distinct, roles correct |

**PASS**

### Scenario B: INSTRUCTOR-creates + STUDENT-player

| Step | HTTP | Result |
|------|------|--------|
| S1 create (Instructor) | 201 | Instructor→instructor participant |
| S2 join (P1) | 200 | P1→player participant |
| S3a device Instr (ipad/instructor_primary) | 201 | registered |
| S3b device P1 (iphone/player_primary) | 201 | registered |
| S4 both → ready | 200 | both devices ready |
| S5 devices_ready | 200 | transition OK |
| S6 recording_pending | 200 | scheduled_start_at not null |
| S7 streams (2×) | 201 | 2 streams |
| S8 capture_result (2×) | 200 | both success |
| S9 readback + validation | 200 | 2 participants, 2 devices, roles + user_ids correct |

**PASS**

### Scenario C: INSTRUCTOR + 2×STUDENT (3-user)

| Step | HTTP | Result |
|------|------|--------|
| S1 create (Instructor) | 201 | max_participants=3 |
| S2 join P1 | 200 | player |
| S2b join P2 | 200 | player |
| S3a/b/c devices (3×) | 201 | instructor_primary + player_primary + player_secondary |
| S4 all → ready | 200 | 3 devices ready |
| S5 devices_ready | 200 | transition OK |
| S6 recording_pending | 200 | scheduled_start_at not null |
| S7 streams (3×) | 201 | 3 streams |
| S8 capture_result (3×) | 200 | all success |
| S9 readback + validation | 200 | 3 participants, 3 devices, 3 distinct user_ids, roles correct |

**PASS**

## Validation Assertions (all scenarios)

- Separate login tokens per user
- Separate user IDs (verified distinct set)
- Expected participant count and roles (1 instructor + N player)
- Expected device count and roles
- Every device status=ready
- session status=recording_pending with scheduled_start_at not null
- Separate capture stream per device
- Every stream capture_result=success with started_at + stopped_at not null
- No 409 revision conflict, no 500, no 403 permission error

## CI Status (PR #332)

38/38 SUCCESS, 1 SKIPPED (informational). State: OPEN.
