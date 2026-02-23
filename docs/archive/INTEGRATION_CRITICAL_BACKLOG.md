# Integration Critical Suite — Backlog

> **Created:** 2026-02-22
> **Purpose:** Deferred Integration Critical Suite tasks (future sprints)
> **Policy:** All items are BLOCKING suite candidates when implemented

---

## 🔒 Payment Workflow (FROZEN — Do NOT modify)

**Status:** ✅ CI-gated, 20/20 validation PASS, architecture documented

**Architecture Decision (PERMANENT):**
- `user.credit_balance` = single source of truth
- NO CreditTransaction dependency for invoice purchases
- Reference: [docs/PAYMENT_SYSTEM_ARCHITECTURE.md](docs/PAYMENT_SYSTEM_ARCHITECTURE.md)

**Policy:**
- ❌ DO NOT modify `user.credit_balance` model
- ❌ DO NOT reintroduce transaction layer for purchases
- ❌ DO NOT bypass duplicate invoice prevention (409 Conflict)
- ✅ All payment changes require 20-run validation (0 flake) before PR

---

## ⚙️ Core Access & State Sanity (CI-gated, INFRA-LEVEL ONLY)

**Status:** ✅ CI-gated (BLOCKING), 2/2 tests passing (20/20 validation)

**⚠️ IMPORTANT: FULL LIFECYCLE NOT YET COVERED**

**Current Coverage (Infra-Level):**
- ✅ Tournament creation via OPS scenario
- ✅ Auto-enrollment (4 players via @lfa-seed.hu pool)
- ✅ Session auto-generation
- ✅ Student API access (authentication works)
- ✅ Instructor API access (authentication works)
- ✅ Basic state validation (tournament IN_PROGRESS, session count > 0)

**NOT Covered (Production-Level Gaps):**
- ❌ Manual student enrollment workflow (missing GET `/api/v1/tournaments/{id}` endpoint)
- ❌ Credit deduction during enrollment (deferred to TICKET-002)
- ❌ Session visibility for enrolled students (missing API infrastructure)
- ❌ Instructor assignment lifecycle (tournament IN_PROGRESS blocks assignment)
- ❌ Instructor check-in workflow (no assigned instructor)
- ❌ Instructor result submission (no assigned instructor)
- ❌ Full state transition validation (PENDING → STARTED → COMPLETED)

**Purpose:**
- Acts as sanity gate: ensures basic tournament creation and auth infrastructure works
- Does NOT guarantee full business logic correctness
- Does NOT replace integration testing of enrollment/instructor workflows

**Policy:**
- ✅ Maintain CI gate (prevents basic infrastructure regressions)
- ✅ Do NOT expand coverage until enrollment API ready
- ✅ Label clearly as "infra-level" in all documentation
- ❌ Do NOT claim "production-grade" coverage (unlike payment workflow)

**Reference:** [tests_e2e/integration_critical/test_multi_role_integration.py](tests_e2e/integration_critical/test_multi_role_integration.py)

---

## 📋 Deferred Tasks (Future Sprints)

### **TICKET-001: Refund E2E Workflow** (Week 6-7)

**Priority:** HIGH (Revenue-critical path)
**Blocking:** YES (will be added to CI BLOCKING suite)

**Scope:**
- Enrollment withdrawal before approval
- Credit refund: `credit_balance += refund_amount`
- CreditTransaction (type: REFUND) creation validation
- SemesterEnrollment cancellation

**Acceptance Criteria:**
- E2E test: `test_refund_full_workflow`
  - Student enrolls in tournament (250 credits deducted)
  - Student withdraws before approval
  - Verify: `credit_balance` restored (+250)
  - Verify: SemesterEnrollment status = CANCELLED
- 0 flake in 20 runs
- Runtime <10s
- Parallel execution stable

**Blockers:**
- None (payment infrastructure ready)

**Estimated Effort:** 1-2 days

---

### **TICKET-002: Enrollment Atomicity Test** (Week 6-7)

**Priority:** HIGH (Balance consistency protection)
**Blocking:** YES (will be added to CI BLOCKING suite)

**Scope:**
- Prevent negative credit balance during concurrent enrollments
- Race condition validation (3 parallel enrollments, 500 credits available)
- Expected: 2 succeed (500 - 250 - 250 = 0), 1 fails (HTTP 402 Insufficient Credits)

**Acceptance Criteria:**
- E2E test: `test_concurrent_enrollment_atomicity` (currently SKIPPED)
- Unskip test after enrollment API ready
- 0 flake in 20 runs
- Runtime <10s
- Parallel execution stable

**Blockers:**
- ❌ GET `/api/v1/tournaments/{id}` endpoint missing (needed to extract `semester_id`)
- **Alternative:** Create dedicated enrollment endpoint that accepts `tournament_id` directly

**Estimated Effort:** 2-3 days (includes enrollment API implementation)

---

### **TICKET-004: Full Student Lifecycle E2E Test** (Week 6-7)

**Priority:** HIGH (Business logic validation)
**Blocking:** YES (will be added to CI BLOCKING suite)

**Scope:**
- Tournament creation WITHOUT auto-session generation
- Manual student enrollment via dedicated endpoint
- Credit deduction during enrollment (atomic transaction)
- Session visibility for enrolled students
- Enrollment cancellation workflow

**Acceptance Criteria:**
- E2E test: `test_student_full_lifecycle` (replaces simplified infra test)
  - Admin creates tournament (DRAFT → ENROLLMENT_OPEN)
  - Student enrolls manually (credit deduction validated)
  - Verify: Session visibility for enrolled student
  - Verify: Credit balance updated correctly
  - Verify: Enrollment state in DB (ACTIVE)
- 0 flake in 20 runs
- Runtime <30s
- Parallel execution stable

**Blockers:**
- ❌ GET `/api/v1/tournaments/{id}` endpoint missing
- ❌ Dedicated enrollment endpoint (accepts `tournament_id`) NOT IMPLEMENTED
- **Alternative:** Implement `POST /api/v1/tournaments/{id}/enroll` endpoint

**Estimated Effort:** 3-4 days (includes enrollment API + tournament query endpoint)

---

### **TICKET-005: Full Instructor Lifecycle E2E Test** (Week 6-7)

**Priority:** HIGH (Business logic validation)
**Blocking:** YES (will be added to CI BLOCKING suite)

**Scope:**
- Tournament creation WITHOUT auto-session generation (manual session creation)
- Instructor assignment to tournament (SEEKING_INSTRUCTOR → ASSIGNED)
- Instructor check-in to session (PENDING → STARTED)
- Instructor result submission (STARTED → COMPLETED)
- Full state transition validation

**Acceptance Criteria:**
- E2E test: `test_instructor_full_lifecycle` (replaces simplified infra test)
  - Admin creates tournament (DRAFT → SEEKING_INSTRUCTOR)
  - Admin assigns instructor (SEEKING_INSTRUCTOR → ASSIGNED)
  - Instructor checks in to session (PENDING → STARTED)
  - Instructor submits results (STARTED → COMPLETED)
  - Verify: All state transitions recorded in DB
- 0 flake in 20 runs
- Runtime <30s
- Parallel execution stable

**Blockers:**
- ❌ Tournament creation WITHOUT auto-session generation (modify OPS scenario)
- ❌ Instructor assignment lifecycle (currently blocked by IN_PROGRESS state)
- ❌ Manual session creation endpoint (POST `/api/v1/tournaments/{id}/sessions`)

**Estimated Effort:** 3-4 days (includes state machine refactoring)

---

### **TICKET-006: Credit Expiration E2E Test** (Week 8-9)

**Priority:** MEDIUM (Regulatory compliance)
**Blocking:** NO (warning-only, nightly run)

**Scope:**
- Validate 2-year credit expiration policy
- Cron job simulation (time-travel fixtures)
- CreditTransaction (type: EXPIRATION) creation
- User notification (email/in-app alert)

**Acceptance Criteria:**
- E2E test: `test_credit_expiration_lifecycle`
  - Create credits with backdated timestamp (2+ years old)
  - Run expiration cron job
  - Verify: expired credits deducted from `credit_balance`
  - Verify: CreditTransaction (EXPIRATION) created
  - Verify: User notification sent
- 0 flake in 20 runs
- Runtime <15s

**Blockers:**
- ⚠️ Expiration cron job NOT IMPLEMENTED (see [PAYMENT_WORKFLOW_GAP_SPECIFICATION.md](PAYMENT_WORKFLOW_GAP_SPECIFICATION.md#phase-6-expiration))
- ⚠️ User notification system NOT IMPLEMENTED

**Estimated Effort:** 3-5 days (includes cron job + notification system)

---

### **TICKET-007: Invoice PDF Generation** (Week 10+)

**Priority:** LOW (Nice-to-have)
**Blocking:** NO

**Scope:**
- Generate downloadable invoice PDF
- Include: payment_reference, amount, date, user details, company info
- Store in S3/local storage
- Link in user dashboard

**Acceptance Criteria:**
- API endpoint: `GET /api/v1/invoices/{id}/pdf`
- PDF generation (use reportlab or WeasyPrint)
- E2E test: Download + validate PDF structure
- 0 flake in 20 runs

**Blockers:**
- None (optional feature)

**Estimated Effort:** 2-3 days

---

### **TICKET-008: Automated Payment Gateway Integration** (Week 12+)

**Priority:** LOW (Future enhancement)
**Blocking:** NO

**Scope:**
- Stripe/PayPal integration
- Webhook handlers (payment.success, payment.failed)
- Automatic credit addition on webhook confirmation
- Idempotency key validation (prevent duplicate webhook processing)

**Acceptance Criteria:**
- API endpoint: `POST /api/v1/payments/webhook` (Stripe/PayPal)
- E2E test: Mock webhook → verify credits added
- 0 flake in 20 runs
- Performance: webhook processing <500ms (p95)

**Blockers:**
- ⚠️ Business decision: manual vs automated payment model
- ⚠️ PCI compliance requirements (if card payments)

**Estimated Effort:** 5-7 days (includes security review)

---

## 🎯 Current Sprint Status (Week 2-3)

**Status:** ✅ COMPLETE (Infra-level coverage achieved)

**Completed Tasks:**
1. `test_student_full_enrollment_flow` — ✅ PASS (20/20, infra-level only)
2. `test_instructor_full_workflow` — ✅ PASS (20/20, infra-level only)
3. CI integration — ✅ core-access-gate added as BLOCKING

**⚠️ Clarification:**
- Tests validate basic tournament creation + auth infrastructure
- **NOT** full business logic (see "Core Access & State Sanity" section above)
- Full lifecycle deferred to Week 6-7 (TICKET-002, TICKET-004)

**Achievement:**
- ✅ 2 CI-gated cores: Payment (production-grade) + Core Access (infra-level)
- ✅ 20/20 validation PASS, 0 flake, parallel stable
- ✅ Documentation accurately reflects coverage gaps

---

## 📊 Sprint Planning Matrix

| Sprint | Focus | Payment Status | Core Access Status | Lifecycle Status |
|--------|-------|----------------|-------------------|------------------|
| Week 1 | Multi-role integration | ✅ Implemented | - | ✅ Auto-enrolled (OPS) |
| Week 2-3 | Core Access Sanity | 🔒 FROZEN | ✅ INFRA-LEVEL | ⚠️ NOT COVERED |
| Week 4-5 | Payment lifecycle | ✅ PRODUCTION-GRADE | ✅ INFRA-LEVEL | ⚠️ NOT COVERED |
| Week 6-7 | Full Lifecycle Implementation | 🔒 FROZEN | ✅ INFRA-LEVEL | 🎯 TICKET-004, 005 |
| Week 6-7 | Refund + Enrollment atomicity | 🔒 FROZEN | ✅ INFRA-LEVEL | 🎯 TICKET-001, 002 |
| Week 8-9 | Credit expiration | 🔒 FROZEN | ✅ INFRA-LEVEL | 🎯 TICKET-006 |
| Week 10+ | Invoice PDF, Automated gateway | 🔒 FROZEN | ✅ INFRA-LEVEL | 🎯 TICKET-007, 008 |

---

## ⚠️ Regression Prevention Policy

**Payment Workflow Changes:**
- All PR changes to payment endpoints require:
  - ✅ 20-run validation (0 flake)
  - ✅ Performance threshold check (p95 < 400ms)
  - ✅ Parallel execution validation (`pytest -n auto`)
  - ✅ Architecture review (no transaction layer reintroduction)

**Enrollment Workflow Changes:**
- All PR changes to enrollment endpoints require:
  - ✅ Integration Critical Suite PASS (all tests)
  - ✅ Balance consistency validation (no negative balance)
  - ✅ Concurrent request safety (race condition tests)

---

**Status:** ✅ Backlog updated, Week 2-3 complete (infra-level coverage)

**Current State:**
- 🔒 Payment Workflow: FROZEN, production-grade, CI-gated (BLOCKING)
- ⚙️ Core Access: CI-gated (BLOCKING), infra-level ONLY, ⚠️ FULL LIFECYCLE NOT YET COVERED
- 📋 Backlog: 8 tickets (TICKET-001 through TICKET-008)

**Next Steps:**
- Week 6-7: Full Student + Instructor Lifecycle (TICKET-004, TICKET-005)
- Week 6-7: Refund + Enrollment atomicity (TICKET-001, TICKET-002)
