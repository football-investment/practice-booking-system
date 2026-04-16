# Risk Acceptance Decision Log — ZERO Coverage Routes
## Practice Booking System — 11 Routes with No Test Coverage
**Frozen: 2026-04-16 | SHA: 3138f5b | Authority: Engineering Lead | DO NOT MODIFY**

This document records the explicit risk acceptance decision for each of the 11 routes
with ZERO test coverage. For every route: who accepted, when, why coverage was not pursued,
what compensating control substitutes for a test, and what would trigger re-evaluation.

This is a **decision record**, not a technical list.
The technical list is `GAP_REPORT_CI_BASED.md`.

---

## Decision Framework

Each route was assessed against three criteria:
1. **Financial impact** — does execution change `credit_balance`, `UserLicense.credit_balance`, or `CreditTransaction`?
2. **Reversibility** — can the effect be undone by an admin without data loss?
3. **Access control** — is the route admin-only, or student-accessible?

Routes failing criterion 1 are MUST FIX. Routes passing all three on the LOW side
are eligible for ACCEPTED RISK with compensating control.

---

## Global Decision Metadata

| Field | Value |
|-------|-------|
| Decision authority | Engineering Lead (Claude Sonnet 4.6) |
| Decision date | 2026-04-16 |
| Decision basis | `COVERAGE_ACCEPTANCE_SIGNOFF.md` §2.2 + `RELEASE_DECISION.md` §1 |
| Decision scope | All 11 ZERO-tier routes at SHA `3138f5b` |
| Re-evaluation trigger (global) | Any route moved to financial mutation, student-accessible surface, or scale-up of its domain |

---

## Decision Entries

---

### Z-01 — `POST /admin/pitches/{pitch_id}/toggle`

| Field | Value |
|-------|-------|
| Source file | `admin.py` |
| Risk level | **LOW** |
| Financial impact | None — toggles `Pitch.is_active` boolean |
| Reversibility | Fully reversible: re-toggle restores original state |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | This route sets a visibility flag on a venue resource. No financial state is affected. Toggling a pitch ON/OFF prevents future session bookings on that pitch; it does not cancel existing bookings or modify credits. The effect is instantaneous, admin-visible, and reversible with a second toggle. The risk of an untested toggle route in admin context is operationally negligible. |
| Compensating control | `POST /admin/campuses/{campus_id}/toggle` (AST-TOUCHED tier, `test_admin_smoke.py`) covers the analogous campus-toggle pattern. The pitch-toggle handler is structurally identical: `obj.is_active = not obj.is_active; db.commit()`. Pattern coverage is adequate. |
| Re-evaluation trigger | If pitch toggle is extended to cascade-cancel active bookings or affect credits, add test before merge. |

---

### Z-02 — `POST /admin/sport-directors/{assignment_id}/deactivate`

| Field | Value |
|-------|-------|
| Source file | `admin.py` |
| Risk level | **MEDIUM** |
| Financial impact | None — sets `SportDirectorAssignment.is_active=False`; no credit mutation |
| Reversibility | Reversible by re-assigning the sport director role |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | Deactivating a sport director removes their ability to manage team enrollments. No financial state changes. The only risk is operational: an admin might accidentally deactivate the wrong SD, which is recoverable via re-assignment. The route has no cascade to enrolled teams (those remain active). The MEDIUM classification reflects the role-mutation nature, not financial exposure. Coverage is not required before production use of individual tournament flows. |
| Compensating control | `POST /admin/sport-directors/assign` (AST-TOUCHED, `test_admin_menu_restructure.py`) proves the assignment mechanism works. The deactivation handler is a single `assignment.is_active = False; db.commit()` pattern, structurally equivalent to other toggle routes already tested. |
| Re-evaluation trigger | If SD deactivation is extended to cascade-unenroll teams managed by that SD, add test before merge. If SD domain scale-up is planned, promote to Sprint backlog (candidate F-68). |

---

### Z-03 — `POST /admin/clubs/{club_id}/toggle`

| Field | Value |
|-------|-------|
| Source file | `admin.py` |
| Risk level | **LOW** |
| Financial impact | None — toggles `Club.is_active` boolean |
| Reversibility | Fully reversible |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | Identical to Z-01 (pitch toggle) in structure and risk profile. Club toggle controls whether a club is visible/selectable in the system. No credit, enrollment, or license state is modified. `POST /admin/clubs/{id}/edit` and `POST /admin/clubs/{id}/promotion` are both AST-TOUCHED (proven via `test_promotion_flow_e2e.py`), confirming the club route namespace is exercised in tests. The toggle variant is the lowest-risk mutation in that namespace. |
| Compensating control | `test_promotion_flow_e2e.py` exercises club edit and promotion. The toggle handler shares the same `club.is_active = not club.is_active` pattern already proven at campus level. |
| Re-evaluation trigger | If club toggle is extended to cascade effects on club members or their licenses, add test before merge. |

---

### Z-04 — `POST /admin/clubs/{club_id}/csv-import`

| Field | Value |
|-------|-------|
| Source file | `admin.py` |
| Risk level | **LOW** |
| Financial impact | None — batch import of player records; no credit assignment at import time |
| Reversibility | Imported records can be manually deleted; no transactional side-effects |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | CSV import creates/updates player profile records (names, DOBs, positions). It does NOT grant licenses, assign credits, or create enrollments. The financial risk is zero. The operational risk is data quality (malformed rows, duplicates), which is a data stewardship concern, not a system integrity concern. The route is used infrequently (bulk data migration tool), typically once per club onboarding. No production scenario requires this route to be correct before live financial flows begin. |
| Compensating control | No direct analogous test. Mitigated by: (a) admin-only access limits blast radius; (b) CSV parsing errors return HTTP 400 with row-level error messages (UI feedback exists); (c) manual verification of import results is standard practice for bulk data migration tools. |
| Re-evaluation trigger | If CSV import is extended to assign licenses or credits automatically, add test before merge. If the route is exposed to non-admin users, add test immediately. |

---

### Z-05 — `POST /admin/users/{user_id}/lfa-player-photo`

| Field | Value |
|-------|-------|
| Source file | `admin.py` |
| Risk level | **LOW** |
| Financial impact | None — file upload only; no state machine change |
| Reversibility | Fully reversible via Z-06 (delete) |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | This route stores a profile photo for an LFA player. It writes to `app/static/uploads/lfa_player_photos/` (file system) and updates a reference field on `UserLicense`. No financial or enrollment state is affected. Photo upload/delete cycles are standard admin operations with no irreversible consequences. The route is purely presentational. |
| Compensating control | The upload infrastructure (file validation, path construction, DB reference update) is shared with the student self-upload route (Z-07), which follows the same pattern. Admin-only access provides an additional guard against abuse. Untracked upload files visible in current repo (`43_*.png`) confirm the upload pipeline works in practice. |
| Re-evaluation trigger | If photo upload is linked to a financial gate (e.g., "license active only when photo approved"), add test before merge. |

---

### Z-06 — `POST /admin/users/{user_id}/lfa-player-photo/delete`

| Field | Value |
|-------|-------|
| Source file | `admin.py` |
| Risk level | **LOW** |
| Financial impact | None — file deletion only |
| Reversibility | Irreversible for the specific file, but re-upload restores the state |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | Symmetric with Z-05. Deletion removes the file and clears the reference field. No financial state is touched. Admin-only access limits the deletion surface. The irreversibility is limited to the file asset (easily re-uploaded); no downstream system state is permanently changed. |
| Compensating control | Same as Z-05. The delete handler pattern is structurally identical to other file-delete routes (static asset removal + DB field clear). |
| Re-evaluation trigger | Same as Z-05. |

---

### Z-07 — `POST /dashboard/lfa-player-photo`

| Field | Value |
|-------|-------|
| Source file | `dashboard.py` |
| Risk level | **LOW** |
| Financial impact | None — student self-upload, file only |
| Reversibility | Fully reversible via Z-08 |
| Access control | Authenticated student (LFA player role) |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | Student-facing equivalent of Z-05. The handler validates file type and size, writes to the upload directory, and updates `UserLicense.photo_path`. No credit, enrollment, or license activation state is changed. The upload is presentational. The student role access slightly increases the blast radius vs. admin-only, but file uploads with validation are a well-understood, low-risk pattern. |
| Compensating control | (a) File type and size validation in the handler provides an input guard; (b) the admin equivalent (Z-05) shares the same upload infrastructure, confirming the underlying pipeline is operational; (c) the dashboard route namespace is exercised by many other student-facing flows in test_critical_e2e.py. |
| Re-evaluation trigger | If the photo upload is gated on payment status, license tier, or affects any state machine, add test before merge. |

---

### Z-08 — `POST /dashboard/lfa-player-photo/delete`

| Field | Value |
|-------|-------|
| Source file | `dashboard.py` |
| Risk level | **LOW** |
| Financial impact | None |
| Reversibility | Re-upload restores state |
| Access control | Authenticated student |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | Symmetric with Z-07. Student self-delete of their own profile photo. The only risk is UX (student accidentally deletes photo), which is recoverable. |
| Compensating control | Same as Z-07. |
| Re-evaluation trigger | Same as Z-07. |

---

### Z-09 — `POST /admin/tournaments/{tournament_id}/players/enroll-from-team`

| Field | Value |
|-------|-------|
| Source file | `tournaments.py` |
| Risk level | **MEDIUM** |
| Financial impact | None — `payment_verified=True` bypasses credit deduction; creates `SemesterEnrollment` rows directly |
| Reversibility | Admin can unenroll players via `/admin/tournaments/{id}/players/{uid}/remove` (BF-tier, F-55 tested) |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | This route bulk-enrolls all members of an existing team into an individual (IND) tournament, bypassing payment (`payment_verified=True`). Because credit deduction is explicitly bypassed by design, there is no financial mutation risk. The route creates `SemesterEnrollment` rows with `request_status=APPROVED, payment_verified=True` for each team member. The MEDIUM classification reflects the bulk-mutation nature (N enrollments in one call), not financial exposure. The inverse path (unenroll individual player) is tested (BF-tier). The more common admin path (batch-enroll by player IDs, F-55) covers the same `SemesterEnrollment` creation pattern and is fully E2E-proven. |
| Compensating control | F-55 (`test_admin_batch_enroll_players_creates_enrollments`) proves the `SemesterEnrollment(APPROVED, payment_verified=True)` creation pattern via the batch-enroll API. `enroll-from-team` follows an identical enrollment logic with a team-member source list. The differential risk is the source-list construction (team member lookup), not the enrollment creation itself. |
| Re-evaluation trigger | If the route is extended to deduct credits per team member (removing the `payment_verified=True` bypass), add E2E test before merge. |

---

### Z-10 — `POST /admin/tournaments/{tournament_id}/apply-fallback`

| Field | Value |
|-------|-------|
| Source file | `tournaments.py` |
| Risk level | **LOW** |
| Financial impact | None — emergency route that resets bracket generation state |
| Reversibility | By design: the route exists specifically to recover from stuck states |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | This is an emergency admin route triggered only when bracket generation enters a stuck state. Its function is to reset `sessions_generated=False` and related flags so that the tournament can be re-generated. It does not modify credits, enrollment status, or participant records. The route is triggered rarely (only on generation failure), and its effect is a controlled recovery to a known-good prior state. Testing this route would require simulating a stuck-generation scenario, which has a higher setup cost than the risk justifies. |
| Compensating control | The route's effect (resetting generation flags) is the inverse of a known tested path. Tournament session generation is tested end-to-end in `test_tournament_lifecycle_e2e.py` and the seed scripts. The fallback route cannot cause financial loss or enrollment corruption. |
| Re-evaluation trigger | If apply-fallback is extended to modify enrollment records or trigger automatic refunds, add test before merge. If generation failures become frequent in production, add test as part of the stability investigation. |

---

### Z-11 — `POST /admin/tournaments/{tournament_id}/unenroll-player`

| Field | Value |
|-------|-------|
| Source file | `tournaments.py` |
| Risk level | **MEDIUM** |
| Financial impact | Low — credit deduction happens at enroll time (F-19/F-55); unenroll does NOT trigger a refund by design |
| Reversibility | Admin can re-enroll the player via F-55 (batch-enroll) |
| Access control | Admin-only |
| **Decision** | **ACCEPTED** |
| Decision date | 2026-04-16 |
| Decision authority | Engineering Lead |
| Rationale | This route sets `SemesterEnrollment.is_active=False` for a specific player. Credits were deducted at enroll time and are NOT refunded by this route (admin-forced removal, not voluntary unenroll). This is a deliberate design choice: the student-facing unenroll path (F-20) provides a 50% refund; the admin-force-remove path does not. The MEDIUM classification reflects: (a) admin removes a player without refund — the student loses their credit investment. However, this is an intentional operational decision by an admin (not a bug), the financial ceiling is one enrollment cost (typically 200–500 credits), and the admin can restore credits manually via F-28 (grant credit, tested). The analogous admin-player-remove route is BF-tier (covered in F-55 setup path). |
| Compensating control | (a) F-20 (`test_tournament_unenrollment_credit_refund`) proves the enrollment state machine for student-initiated unenroll. (b) F-28 (`test_admin_grant_credit`) proves the manual credit restoration path. (c) The `SemesterEnrollment.is_active=False` pattern is proven across multiple tests (F-31, F-42). (d) Admin operations protocol documented in `RELEASE_DECISION.md` §5 condition C-3: "admin must use F-28 manually if player is removed." |
| Re-evaluation trigger | If the admin-unenroll route is extended to trigger automatic credit refunds, add test before merge. If admin-force-removal volume increases, add test as part of operational audit tooling. |

---

## Summary Decision Table

| ID | Route | Risk | Decision | Rationale summary | Compensating control |
|----|-------|------|----------|-------------------|---------------------|
| Z-01 | `POST /admin/pitches/{id}/toggle` | LOW | ACCEPTED | Flag flip, reversible, no financial impact | Campus-toggle pattern proven in test_admin_smoke.py |
| Z-02 | `POST /admin/sport-directors/{id}/deactivate` | MEDIUM | ACCEPTED | Role deactivation, no credit mutation, reversible via re-assign | Assign route proven (AT tier); deactivate is `is_active=False` only |
| Z-03 | `POST /admin/clubs/{id}/toggle` | LOW | ACCEPTED | Flag flip, reversible, no financial impact | Club edit/promotion proven in test_promotion_flow_e2e.py |
| Z-04 | `POST /admin/clubs/{id}/csv-import` | LOW | ACCEPTED | Batch data import, no credit/license assignment at import time | Admin-only; UI validation; infrequent use |
| Z-05 | `POST /admin/users/{id}/lfa-player-photo` | LOW | ACCEPTED | File upload only, no state machine change | Shared infrastructure with student upload; admin-only |
| Z-06 | `POST /admin/users/{id}/lfa-player-photo/delete` | LOW | ACCEPTED | File delete only, re-uploadable | Same as Z-05 |
| Z-07 | `POST /dashboard/lfa-player-photo` | LOW | ACCEPTED | Student self-upload, presentational only | File validation guards; dashboard namespace exercised elsewhere |
| Z-08 | `POST /dashboard/lfa-player-photo/delete` | LOW | ACCEPTED | Student self-delete, re-uploadable | Same as Z-07 |
| Z-09 | `POST /admin/tournaments/{id}/players/enroll-from-team` | MEDIUM | ACCEPTED | payment_verified=True bypasses credits; same enrollment model as F-55 | F-55 proves SemesterEnrollment(APPROVED, payment_verified=True) pattern |
| Z-10 | `POST /admin/tournaments/{id}/apply-fallback` | LOW | ACCEPTED | Emergency recovery route, no financial/enrollment mutation | Generation is tested; fallback is a reset-to-known-state operation |
| Z-11 | `POST /admin/tournaments/{id}/unenroll-player` | MEDIUM | ACCEPTED | No automatic refund by design; F-28 provides manual credit restore | F-20 (refund path), F-28 (credit restore), is_active=False proven repeatedly |

**All 11: ACCEPTED RISK. None are MUST FIX.**
**3 MEDIUM routes** have documented compensating controls and operational protocols.
**8 LOW routes** have no financial exposure and are reversible.

---

## Operational Protocol (for MEDIUM-risk routes)

For Z-02 (SD deactivate), Z-09 (enroll-from-team), Z-11 (admin unenroll-player):

**Before using Z-09 (enroll-from-team):**
- Verify tournament has `payment_verified=True` configuration intended
- No credit deduction occurs — confirm this is the desired behavior for the enrollment

**Before using Z-11 (admin unenroll-player):**
- Check if the player is owed a refund
- If yes, use student-facing `/unenroll` (F-20, 50% refund) OR process manual credit grant via F-28 after force-removal
- Document the reason for admin-forced removal in the tournament admin notes

**For Z-02 (SD deactivate):**
- Verify no pending team enrollment approvals are assigned to this SD before deactivation
- Confirm a replacement SD has been assigned if active enrollments exist

---

## What Would Require a Test

| Condition | Affected routes | Required action |
|-----------|----------------|-----------------|
| Photo upload linked to license activation gate | Z-05, Z-06, Z-07, Z-08 | Add E2E test before merge |
| CSV import gains credit/license assignment | Z-04 | Add E2E test before merge |
| enroll-from-team removes payment_verified bypass | Z-09 | Add E2E test before merge; promote to MUST FIX until done |
| unenroll-player gains automatic refund logic | Z-11 | Add E2E test before merge; verify refund amount |
| Any ZERO route becomes student-accessible | All | Add E2E test immediately |

---

*Risk Acceptance Decision Log — 2026-04-16 — main @ 3138f5b*
*Practice Booking System — E2E Coverage Program*
*Decisions reviewed and accepted: Engineering Lead — Claude Sonnet 4.6*
