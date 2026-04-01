# Test Coverage Audit — LFA Practice Booking System

> **Living document.** Update after every PR that adds, removes, or modifies tests or CI workflows.
> Last updated: 2026-03-23 | Branch: `fix/e2e-ops-seed-1024`

---

## 1. Test Suite Overview

| Layer | Files | Tests | % of total |
|---|---|---|---|
| Unit | ~80 | ~6 170 | 71% |
| Integration — API smoke | ~40 | ~1 746 | 20% |
| Integration — web flows | 15 | 296 | 3.4% |
| Integration — domain/tournament | ~15 | ~93 | 1.1% |
| E2E Playwright — admin UI / team | 4 | 31 | 0.4% |
| E2E Playwright — integration critical | 12 | 48 | 0.6% |
| E2E Playwright — lifecycle / legacy | ~20 | ~180 | 2.1% |
| Cypress — web UI (all roles) | 29 specs | ~200 | 2.3% |
| Security (CSRF + SQLi) | 5 | 63 | 0.7% |
| **Total** | **~220** | **~8 831** | — |

### Unit sub-domains

| Sub-domain | Tests |
|---|---|
| `unit/services/` | 3 919 |
| `unit/tournament/` | 1 189 |
| `unit/api/` | 406 |
| `unit/models/` | 134 |
| `unit/endpoints/` | 124 |
| `unit/core/` | 112 |

---

## 2. Business Flow Coverage

### ✅ Fully covered

| Flow | Unit | Integration | Playwright E2E | Cypress |
|---|---|---|---|---|
| Team creation (cost deduction, 402 guard, race condition) | TEAM-10/11/11b | web_flows | TM-01/02 | — |
| Team invite → accept (captain → invitee) | TEAM-12/13 | web_flows | TM-01, GF-01 | — |
| Team auth boundary (wrong user cannot accept) | TEAM-14/15 | web_flows | TM-04 | — |
| Admin bypass add member (no invite) | TEAM-16 | web_flows | TM-03 | — |
| Tournament lifecycle (DRAFT→COMPLETED→REWARDS) | state machine | lifecycle_e2e | lifecycle/ | tournament_lifecycle |
| Skill progression / EMA (delta, clamp, timeline) | 50+ tests | player_game_loop | skill_progression | student_journey |
| Credit system (grant, deduct, audit trail, race guard) | audit tests | concurrency | — | — |
| User onboarding (registration, specialization, license) | 200+ tests | student_lifecycle | integration_critical | onboarding_flow |
| Auth flow (login, logout, CSRF, CORS) | CSRF/CORS | auth_lifecycle | — | login_logout |
| Admin user management (CRUD, credit, license) | ✅ | admin_smoke | admin_user_mgmt | user_management |
| Booking lifecycle (create, confirm, cancel, attendance) | ✅ | booking_lifecycle | admin_bookings | booking_workflow |
| Payment / invoice (verify, unverify, audit) | ✅ | payment_workflow | — | — |
| Session lifecycle (generate, result, reward) | 55+ | session_management | — | session_lifecycle |
| Multi-campus (location isolation, cross-campus guard) | ✅ | multi_campus | — | — |
| Skill weight pipeline (EMA weight regression) | 50 tests | — | — | — |
| CSRF double-submit cookie (28 tests) | — | — | — | — |
| SQL injection prevention (35 tests) | — | — | — | — |

### ⚠️ Partially covered

| Flow | What's missing |
|---|---|
| Team invite cancel (captain cancels pending) | Service + integration ✅; no Playwright E2E (TM-05 planned) |
| Team captain transfer | Service ✅; no UI, no E2E |
| Team 0-credit UI error | TM-02 tests HTTP level; no Cypress assertion on the error message |
| Instructor skill update (merge logic) | Unit ✅; no Cypress E2E flow |
| Coupon redemption | Unit + audit fix ✅; no web flow E2E |
| License renewal | Service + unit ✅; no Cypress E2E |
| Enrollment cancellation / refund | `refund-workflow-gate` CI ✅; Cypress coverage thin |

### ❌ Not covered

| Area | Notes |
|---|---|
| Team delete / dissolve | Not implemented |
| Mobile / responsive — student | Only `admin_responsive.cy.js` exists; no student responsive spec |
| Notifications / messaging E2E | Only API smoke; no user-facing E2E flow |
| XP system E2E | `test_xp_grant.py` integration only; no Playwright / Cypress proof |
| CORS config tests | `test_cors_config.py` exists but references Streamlit :8501 (stale — decommissioned Sprint 59h); excluded from CI |

---

## 3. GitHub Actions CI Audit

### Active workflows (trigger on PR)

| Workflow | Blocking? | Covers | Status |
|---|---|---|---|
| `test-baseline-check.yml` | **YES** — 23 gates | Unit, API smoke, migration, operational smoke, credit audit, **security gate** (CSRF + SQLi), hardcoded-id guard | ✅ |
| `e2e-team-flow.yml` | **YES** — gate job | TM-01..04 Playwright + GF-01 golden flow demo | ✅ |
| `skill-weight-regression.yml` | **YES** | Skill weight pipeline 50 tests | ✅ |
| `e2e-wizard-coverage.yml` | **YES** | Playwright API boundary, P1 coverage | ✅ |
| `cypress-web-e2e.yml` | **YES** — all 4 roles | Admin / Instructor / Student / Business-workflow — all blocking as of 2026-03-23 | ✅ |
| `api-smoke-tests.yml` | soft (`continue-on-error: true`) | Integration API smoke | ✅ |

### Scheduled workflows

| Workflow | Schedule | Covers |
|---|---|---|
| `e2e-integration-critical.yml` | Nightly 02:00 UTC + PR | 12 integration critical suites (auth, booking, payment, skill…) |
| `e2e-health-check.yml` | Weekdays 06:00 UTC | API health, login, DB seed sanity (curl) |
| `skill-propagation-review.yml` | Monday 07:00 UTC | EMA pipeline health, skill timeline integrity |
| `flake-detection.yml` | Saturday 03:00 UTC | Flaky test detection (repeat mode, non-blocking) |
| `mutation-testing.yml` | Saturday 04:00 UTC | Mutant kill rate (non-blocking) |

### Deleted / archived (were dead gaps)

| Workflow | Deleted | Reason |
|---|---|---|
| `layout-validation.yml` | 2026-03-23 | Triggered on `frontend/src/**` (no such path in Jinja2 app); `tests/layout-validation.spec.js` never existed — zero real test coverage |
| `cross-platform-testing.yml` | 2026-03-23 | Manual-only trigger; referenced `app/tests/` (non-existent) + Streamlit + BrowserStack — completely dead since Sprint 59h |

---

## 4. P0 Gaps (resolved 2026-03-23)

| Gap | Fix applied |
|---|---|
| G-1: `layout-validation.yml` dead workflow | **DELETED** |
| G-2: `cross-platform-testing.yml` dead workflow | **DELETED** |
| G-3: `tests/security/csrf/` + `tests/security/sql_injection/` not in CI | **FIXED** — `security-gate` job added to `test-baseline-check.yml`; 63 tests now blocking |
| G-4: Admin Cypress `allow_failure: true` | **FIXED** — changed to `allow_failure: false`; admin UI tests now blocking |

---

## 5. Remaining Gaps (prioritized backlog)

### P1 — Next sprint

| ID | Gap | Planned fix |
|---|---|---|
| G-5 | Team invite cancel — no Playwright E2E | Add TM-05 test to `test_team_flow_e2e.py` |
| G-6 | Captain transfer — no UI, no E2E | UI implementation + TM-06 Playwright test |
| G-7 | Coupon redemption — no web flow E2E | Add Cypress spec `student/coupon_redemption.cy.js` |
| G-8 | License renewal — no Cypress E2E | Add Cypress spec `student/license_renewal.cy.js` |

### P2 — Nice to have

| ID | Gap |
|---|---|
| G-9 | Student responsive Cypress (only admin_responsive exists) |
| G-10 | Notifications / XP E2E Playwright flow |
| G-11 | `test_cors_config.py` — update Streamlit:8501 refs to current CORS config, re-enable in security-gate |
| G-12 | `tests/e2e/legacy/` — 7 files, collected by pytest but no CI workflow runs them; archive or integrate |

---

## 6. How to update this document

After every PR that touches tests or CI:

1. Update the test counts in section 1 if files were added/removed
2. Move flows from "Partially covered" / "Not covered" to "Fully covered" when E2E proof exists
3. Add new gaps to section 5 if discovered
4. Move resolved P0/P1 gaps to section 4 with the fix date
5. Update workflow table if a workflow was added, deleted, or changed from non-blocking → blocking

```
# Quick test count snapshot command:
find tests/ -name "test_*.py" | xargs grep -l "def test_" | wc -l
grep -r "def test_" tests/ --include="*.py" | wc -l
```
