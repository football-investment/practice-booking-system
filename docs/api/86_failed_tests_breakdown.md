# 86 Failed Tests - Teljes Kategorizált Breakdown

**Dátum:** 2026-02-28
**CI Run:** 22525686565
**Eredmény:** 1199 passed, 86 failed, 437 skipped

---

## 📊 Executive Summary

```
KATEGÓRIA                      COUNT    TÍPUS
═══════════════════════════════════════════════════════════
🔴 MISSING_ENDPOINT              39    API implementáció szükséges
🔴 ROUTING_MISMATCH              26    Path/prefix hiba (quick fix)
🔴 VALIDATION_BUG                12    Schema javítás szükséges
🔴 AUTH_PERMISSION                8    Permission logic issue
🚧 INFRA_DB_SCHEMA                1    DB migráció szükséges
───────────────────────────────────────────────────────────
   TOTAL                         86
═══════════════════════════════════════════════════════════
```

**Actionability:**
- **77 teszt** → API implementáció/javítás (immediate action)
- **8 teszt** → Auth/permission logic review
- **1 teszt** → Infrastruktúra (DB schema)

---

## 🔴 1. ROUTING_MISMATCH: 26 tests (QUICK WINS)

**Probléma:** Endpointok léteznek, de ROSSZ PATH alatt vannak mount-olva vagy hiányzik a resource prefix.

### 1.1 Missing Resource Prefix - Path Aliases (17 tests)

Ezek a `/api/v1/action` helyett `/api/v1/resource/action` formátumot várnak:

| Endpoint | Expected Path | Test Count |
|----------|--------------|------------|
| `POST /api/v1/` | Több resource: quiz, location, instructor-management | 6 |
| `POST /api/v1/start` | `/api/v1/quizzes/start` | 1 |
| `POST /api/v1/submit` | `/api/v1/quizzes/submit` | 1 |
| `POST /api/v1/motivation-assessment` | `/api/v1/licenses/motivation-assessment` | 1 |
| `POST /api/v1/generate` | `/api/v1/semesters/generate` | 1 |
| `POST /api/v1/direct-hire` | `/api/v1/instructor-management/direct-hire` | 1 |
| `POST /api/v1/hire-from-application` | `/api/v1/instructor-management/hire-from-application` | 1 |
| `PATCH /api/v1/1` | Több resource: instructor-management | 4 |
| `PUT /api/v1/1` | `/api/v1/locations/1` | 1 |

**Fix Strategy:**
- **NE** használj full router alias-t (okoz konfliktusokat)
- **HELYETTE:** Egyedi endpoint alias-ok vagy test javítás

### 1.2 Missing Resource Prefix - Path Parameters (9 tests)

Ezek `/api/v1/{id}/action` helyett `/api/v1/resource/{id}/action` formátumot várnak:

| Endpoint | Likely Correct Path | Test |
|----------|---------------------|------|
| `POST /api/v1/32/checkin` | `/api/v1/sessions/32/checkin` | attendance |
| `POST /api/v1/47/confirm` | `/api/v1/bookings/47/confirm` | bookings |
| `PATCH /api/v1/41/attendance` | `/api/v1/bookings/41/attendance` | bookings |
| `POST /api/v1/1/verify` | `/api/v1/invoices/1/verify` | invoices |
| `POST /api/v1/1/unverify` | `/api/v1/invoices/1/unverify` | invoices |
| `POST /api/v1/1/confirm-enrollment` | `/api/v1/projects/1/confirm-enrollment` | projects |
| `PATCH /api/v1/1/resolve` | `/api/v1/system-events/1/resolve` | system_events |
| `PATCH /api/v1/1/unresolve` | `/api/v1/system-events/1/unresolve` | system_events |
| `POST /api/v1/3/skills/passing/assess` | `/api/v1/licenses/3/skills/passing/assess` | licenses |

**Fix Strategy:** Tesztek javítása VAGY endpoint alias regisztráció

---

## 🔴 2. MISSING_ENDPOINT: 39 tests (CORE FUNCTIONALITY)

**Probléma:** Endpointok NEM LÉTEZNEK az OpenAPI schémában.

### 2.1 Instructor Tools (9 endpoints)

| Endpoint | Functionality | Priority |
|----------|---------------|----------|
| `POST /api/v1/instructor/students/{id}/skills/{license_id}` | Student skill assessment (2 tests) | **P1** |
| `POST /api/v1/instructor/students/{id}/skills-v2/{license_id}` | Student skill v2 | P1 |
| `POST /api/v1/sessions/{id}/start` | Start session | P1 |
| `POST /api/v1/sessions/{id}/stop` | Stop session | P1 |
| `POST /api/v1/sessions/{id}/unlock-quiz` | Unlock quiz (2 tests) | P1 |
| `POST /api/v1/sessions/{id}/evaluate-instructor` | Evaluate instructor | P2 |
| `POST /api/v1/sessions/{id}/evaluate-student/{student_id}` | Evaluate student | P2 |
| `POST /api/v1/instructor/specialization/toggle` | Toggle specialization | P2 |

### 2.2 Spec-Specific Instructor Tools (4 endpoints)

| Endpoint | Functionality | Spec |
|----------|---------------|------|
| `POST /api/v1/instructor/students/{id}/promote-belt/{license}` | Promote belt | GānCuju (🚧 DB schema issue) |
| `POST /api/v1/instructor/students/{id}/certify/{license}` | Certify coach | LFA Coach |
| `POST /api/v1/instructor/students/{id}/progress-level/{license}` | Progress level | Internship |
| `POST /api/v1/instructor/students/{id}/track-teaching-hours/{license}` | Track hours | LFA Coach |

### 2.3 Attendance Management (3 endpoints)

| Endpoint | Functionality |
|----------|---------------|
| `POST /api/v1/sessions/{id}/attendance/mark` | Mark attendance |
| `POST /api/v1/sessions/{id}/attendance/confirm` | Confirm attendance |
| `POST /api/v1/sessions/{id}/attendance/change-request` | Handle change request |

### 2.4 Campus Management (3 endpoints)

| Endpoint | Functionality |
|----------|---------------|
| `POST /api/v1/locations/{id}/campuses` | Create campus |
| `PUT /api/v1/campuses/{id}` | Update campus |
| `PATCH /api/v1/campuses/{id}/toggle-status` | Toggle campus status |

### 2.5 Coupon System (5 endpoints)

| Endpoint | Functionality |
|----------|---------------|
| `POST /api/v1/admin/coupons` | Create coupon (API) |
| `POST /api/v1/admin/coupons/web` | Create coupon (web) |
| `PUT /api/v1/admin/coupons/{id}` | Update coupon |
| `POST /api/v1/admin/coupons/{id}/toggle` | Toggle coupon |
| `POST /api/v1/coupons/validate/{code}` | Validate coupon |

### 2.6 Period Generators (4 endpoints)

| Endpoint | Period Type |
|----------|-------------|
| `POST /api/v1/lfa-player/pre` | Pre-season |
| `POST /api/v1/lfa-player/youth` | Youth season |
| `POST /api/v1/lfa-player/amateur` | Amateur season |
| `POST /api/v1/lfa-player/pro` | Pro season |

### 2.7 License/Assessment (3 endpoints)

| Endpoint | Functionality |
|----------|---------------|
| `POST /api/v1/assessments/{id}/validate` | Validate assessment |
| `POST /api/v1/assessments/{id}/archive` | Archive assessment |

### 2.8 Other (8 endpoints)

| Endpoint | Functionality | Domain |
|----------|---------------|--------|
| `POST /api/v1/quizzes/{id}/submit` | Submit quiz | Quiz (2 tests) |
| `POST /api/v1/sessions/book/{id}` | Book session | Sessions |
| `POST /api/v1/admin/invitation-codes` | Create invitation code | Invitations |
| `PATCH /api/v1/requests/{id}/cancel` | Cancel assignment request | Instructor Assignments |
| `PATCH /api/v1/offers/{id}/respond` | Respond to offer | Instructor Management |

---

## 🔴 3. VALIDATION_BUG: 12 tests (SCHEMA FIXES)

**Probléma:** Endpoint elfogadja az ÜRES BODY-t (200 OK), pedig 422 Unprocessable Entity-t kellene visszaadnia.

### 3.1 Empty Body Acceptance (12 endpoints)

| Endpoint | Domain | Fix |
|----------|--------|-----|
| `POST /api/v1/log-error` | Debug | Add FrontendErrorRequest schema |
| `POST /api/v1/refresh/{id}` | Gamification | Add RefreshRequest OR remove body |
| `POST /api/v1/logout` | Auth | Remove body requirement (logout needs no input) |
| `POST /api/v1/admin/sync/all` | Licenses | Remove body requirement |
| `POST /api/v1/admin/sync/user/{id}/all` | Licenses | Remove body requirement |
| `POST /api/v1/{enrollment_id}/toggle-active` | Semester Enrollments | Add ToggleRequest OR remove body |
| `POST /api/v1/{enrollment_id}/verify-payment` | Semester Enrollments | Add VerifyRequest OR remove body |
| `POST /api/v1/{enrollment_id}/unverify-payment` | Semester Enrollments | Add UnverifyRequest OR remove body |
| `POST /api/v1/mark-all-as-read` | Notifications | Remove body requirement |
| `POST /api/v1/health/run-check-now` | Health | Remove body requirement |
| `POST /api/v1/purge-old-events` | System Events | Remove body requirement |
| `POST /api/v1/bulk-check-expirations` | License Renewal | Remove body requirement |

**Fix Strategy:**
- **Bulk operations:** Remove body requirement (accept empty POST)
- **Toggle/verify operations:** Add minimal Pydantic schema OR remove body requirement
- **Frontend logging:** Add proper FrontendErrorRequest schema

---

## 🔴 4. AUTH_PERMISSION: 8 tests (PERMISSION LOGIC)

**Probléma:** 403 Forbidden - Permission denied, bár a user authenticated.

### 4.1 Auth Issues (8 endpoints)

| Endpoint | Domain | Likely Issue |
|----------|--------|--------------|
| `POST /api/v1/{id}/enroll` | Projects | Student-only check too strict? |
| `POST /api/v1/{id}/instructor/enroll/{student_id}` | Projects | Instructor role check |
| `POST /api/v1/{id}/milestones/{mid}/submit` | Projects | Student ownership check |
| `POST /api/v1/{id}/milestones/{mid}/approve` | Projects | Instructor role check |
| `POST /api/v1/{session_id}/check-in` | Sessions | Instructor-only check |
| `POST /api/v1/instructor/advance` | Licenses | Admin-only check too strict |
| `POST /api/v1/requests/{id}/accept` | Tournaments | Instructor acceptance logic |
| `POST /api/v1/tournaments/{id}/instructor-assignment/accept` | Tournaments | Assignment acceptance logic |

**Fix Strategy:** Review permission decorators és role checks - lehet túl szigorúak.

---

## 🚧 5. INFRA_DB_SCHEMA: 1 test (DB MIGRATION REQUIRED)

**Probléma:** DB táblák hiányoznak.

| Endpoint | Missing Table | Test |
|----------|---------------|------|
| `POST /api/v1/instructor/students/{id}/promote-belt/{license}` | `gancuju_licenses` | gancuju_routes |

**Megjegyzés:** A CI logban további DB schema hibák vannak (`coach_licenses`, `internship_licenses`, `lfa_player_licenses`), de csak 1 teszt van ebben a kategóriában.

---

## 📊 Priorizált Implementációs Terv

### PHASE 1: Quick Wins - Routing Fixes (26 tests, 1-2 nap)

**Gyors javítások routing/path alias problémákra:**
1. Quiz path aliases: `/start`, `/submit` → dedikált endpoint alias-ok
2. Motivation path alias: `/motivation-assessment` → dedikált endpoint alias
3. Resource prefix fixes: Tesztek javítása VAGY endpoint alias regisztráció

**Estimated Effort:** 8-16 óra

---

### PHASE 2: P1 High-Value Endpoints (15 tests, 3-4 nap)

**Instructor tools (legnagyobb business value):**
1. ✅ Student skill assessment (`/instructor/students/{id}/skills/{license_id}`)
2. ✅ Session management (`/sessions/{id}/start`, `/sessions/{id}/stop`)
3. ✅ Quiz unlock (`/sessions/{id}/unlock-quiz`)
4. ✅ Attendance management (3 endpoints)

**Estimated Effort:** 24-32 óra

---

### PHASE 3: Validation Bug Fixes (12 tests, 1 nap)

**Schema javítások:**
1. Debug logging schema
2. Bulk operation body requirements eltávolítása
3. Toggle/verify minimal schemas

**Estimated Effort:** 8-12 óra

---

### PHASE 4: Remaining Missing Endpoints (24 tests, 4-5 nap)

**Campus, Coupon, Period generators, stb.**

**Estimated Effort:** 32-40 óra

---

## 🎯 Következő Lépés Javaslat

**Opció 1: ROUTING FIXES (gyors)** → 26 teszt megoldása 1-2 nap alatt
**Opció 2: P1 INSTRUCTOR TOOLS (value)** → 15 teszt, legnagyobb business impact
**Opció 3: VALIDATION BUGS (clean)** → 12 teszt, clean API surface

**Ajánlás:** **PHASE 1 (Routing Fixes)** → Gyors -26 failed count csökkenés, momentumot ad.

---

**Teljes riport generálva:** `tools/categorize_86_tests.py`
**CI Run:** https://github.com/football-investment/practice-booking-system/actions/runs/22525686565
