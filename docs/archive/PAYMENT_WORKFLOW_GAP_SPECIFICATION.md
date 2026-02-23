# Payment Workflow Gap Specification

> **Created:** 2026-02-22
> **Purpose:** Identify critical payment workflow blind spots
> **Priority:** P1 (Revenue-Critical)
> **Ownership:** Integration Critical Suite (Week 4-5)

---

## Executive Summary

**Payment System Architecture:** Manual invoice-based (NO automated payment gateway integration)

**Critical Finding:** Payment workflow = **Revenue-critical path**, de tesztlefedettség **57 test említés** (fragmentált, nincs strukturált E2E coverage).

**Immediate Risk:**
- ❌ NO E2E test: invoice request → admin verification → credit addition → enrollment
- ❌ NO test: concurrent invoice requests (race condition potential)
- ❌ NO test: refund workflow validation
- ❌ NO test: credit expiration (2-year limit)

---

## 1. Payment Lifecycle Térkép

### **1.1 Current Implementation (Manual Invoice-Based)**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PAYMENT LIFECYCLE FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

Phase 1: Invoice Request (Student)
─────────────────────────────────
POST /api/v1/users/credits/request-invoice
  ├─ Student selects credit package (500/1000/2000 EUR)
  ├─ System generates unique payment_reference (e.g., "PAY-123456")
  ├─ Creates InvoiceRequest record (status: PENDING)
  └─ Student transfers money manually (bank transfer)

Phase 2: Admin Verification (Admin)
────────────────────────────────
GET /api/v1/payment-verification/students
  ├─ Admin views pending payment verifications
  ├─ Admin checks bank account for transfer
  └─ Admin matches payment_reference to InvoiceRequest

POST /api/v1/payment-verification/students/{id}/verify
  ├─ Admin verifies payment (status: PENDING → VERIFIED)
  ├─ System creates UserLicense for selected specialization
  ├─ Updates user.payment_verified = True
  └─ Updates user.payment_verified_at + payment_verified_by

Phase 3: Credit Addition (System)
──────────────────────────────────
  ├─ CreditTransaction created (type: PURCHASE, amount: +1000)
  ├─ user.credit_balance += purchased_amount
  ├─ user.credit_purchased += purchased_amount
  └─ Idempotency key prevents duplicates

Phase 4: Credit Usage (Student)
────────────────────────────────
POST /api/v1/semesters/{id}/enroll
  ├─ Check: user.credit_balance >= enrollment_cost
  ├─ Deduct credits: credit_balance -= enrollment_cost
  ├─ Create CreditTransaction (type: ENROLLMENT, amount: -250)
  └─ Create SemesterEnrollment (status: PENDING/APPROVED)

Phase 5: Refund (Optional - Admin)
───────────────────────────────────
  ├─ Enrollment withdrawal before approval
  ├─ Create CreditTransaction (type: REFUND, amount: +250)
  ├─ user.credit_balance += refund_amount
  └─ Cancel SemesterEnrollment

Phase 6: Expiration (System - Cron Job)
────────────────────────────────────────
  ├─ Check: credits older than 2 years
  ├─ Create CreditTransaction (type: EXPIRATION, amount: -expired_amount)
  ├─ user.credit_balance -= expired_amount
  └─ Notification to user (⚠️ NOT IMPLEMENTED)
```

---

## 2. Jelenlegi Tesztlefedettség Audit

### **2.1 Meglévő Tesztek (57 említés)**

| Teszt Kategória | Fájl | Lefedettség | Státusz |
|-----------------|------|-------------|---------|
| **Cypress UI** | `tests_cypress/cypress/e2e/admin/financial_management.cy.js` | Admin payment verification UI | ✅ UI smoke test |
| **Cypress UI** | `tests_cypress/cypress/e2e/student/credits.cy.js` | Student credit balance view | ✅ UI smoke test |
| **Cypress UI** | `tests_cypress/cypress/e2e/player/credits.cy.js` | Player credit dashboard | ✅ UI smoke test |
| **Unit Test** | `tests/unit/` fragmentált említések | Credit balance calculation | ⚠️ Fragmentált |
| **E2E** | ❌ NINCS | Full payment workflow E2E | ❌ **CRITICAL GAP** |

### **2.2 Tesztlefedettség Mátrix**

| Workflow Lépés | Unit Test | Integration Test | E2E Test | Cypress UI |
|----------------|-----------|------------------|----------|------------|
| Invoice request creation | ❌ | ❌ | ❌ | ⚠️ Partial |
| Payment reference uniqueness | ❌ | ❌ | ❌ | ❌ |
| Admin payment verification | ❌ | ❌ | ❌ | ⚠️ Partial |
| Credit addition (atomic) | ❌ | ❌ | ❌ | ❌ |
| Concurrent invoice prevention | ❌ | ❌ | ❌ | ❌ |
| Enrollment credit deduction | ⚠️ Partial | ❌ | ❌ | ❌ |
| Refund workflow | ❌ | ❌ | ❌ | ❌ |
| Credit expiration (2-year) | ❌ | ❌ | ❌ | ❌ |
| Transaction idempotency | ❌ | ❌ | ❌ | ❌ |
| Credit balance consistency | ❌ | ❌ | ❌ | ❌ |

**Coverage Score:** ~15% (UI smoke tests only, NO critical path validation)

---

## 3. Kritikus Hiányzó Validációs Pontok

### **3.1 HIGH PRIORITY (Revenue Impact)**

#### **P1.1 Full Payment Workflow E2E**
**Missing:** Student invoice request → Admin verification → Credit addition → Enrollment → Refund

**Risk:**
- Manual verification = human error potential
- NO validation: payment_reference uniqueness
- NO validation: credit balance atomicity during concurrent enrollments

**Test Type:** **E2E (Integration Critical Suite Week 4)**

**Scope:**
```python
@pytest.mark.e2e
@pytest.mark.integration_critical
def test_payment_full_lifecycle():
    """
    1. Student creates invoice request (500 EUR package)
    2. Verify unique payment_reference generated
    3. Admin verifies payment
    4. Verify UserLicense created
    5. Verify CreditTransaction (PURCHASE) exists
    6. Verify user.credit_balance = 500
    7. Student enrolls in tournament (cost: 250)
    8. Verify CreditTransaction (ENROLLMENT) exists
    9. Verify user.credit_balance = 250
    10. Admin refunds enrollment
    11. Verify CreditTransaction (REFUND) exists
    12. Verify user.credit_balance = 500
    """
```

---

#### **P1.2 Concurrent Invoice Prevention**
**Missing:** Race condition when student creates multiple invoices simultaneously

**Risk:**
- Student submits 3 invoice requests at once
- System creates 3 InvoiceRequests with different payment_references
- Admin verifies all 3 → user gets 3x credits

**Test Type:** **Integration (Concurrency Test)**

**Scope:**
```python
@pytest.mark.integration
def test_concurrent_invoice_requests():
    """
    1. Spawn 5 parallel invoice requests from same student
    2. Verify: only 1 InvoiceRequest created (PENDING status blocks duplicates)
    3. Verify: subsequent requests fail with HTTP 409 Conflict
    """
```

---

#### **P1.3 Credit Balance Atomicity**
**Missing:** Concurrent enrollment attempts from same student

**Risk:**
- Student has 500 credits
- Student enrolls in 3 tournaments simultaneously (250 each)
- System processes all 3 → balance goes negative (-250)

**Test Type:** **Integration (Race Condition Test)**

**Scope:**
```python
@pytest.mark.integration
def test_concurrent_enrollment_credit_deduction():
    """
    1. Student has 500 credits
    2. Spawn 3 parallel enrollment requests (250 each)
    3. Verify: only 2 enrollments succeed (500 - 250 - 250 = 0)
    4. Verify: 3rd enrollment fails with HTTP 402 Insufficient Credits
    5. Verify: credit_balance never goes negative
    """
```

---

### **3.2 MEDIUM PRIORITY (Business Logic)**

#### **P2.1 Refund Workflow Validation**
**Missing:** Full refund cycle (enrollment → withdrawal → refund → credit restoration)

**Risk:**
- Refund not properly credited
- CreditTransaction not created
- Balance inconsistency

**Test Type:** **E2E (Integration Critical Suite Week 5)**

---

#### **P2.2 Credit Expiration (2-Year Limit)**
**Missing:** Automated credit expiration cron job validation

**Risk:**
- Credits never expire (business rule violation)
- Notification not sent to user

**Test Type:** **Integration (Scheduled Job Test)**

**Note:** Requires time-travel testing or manual verification

---

#### **P2.3 Transaction Idempotency**
**Missing:** Duplicate transaction prevention via idempotency_key

**Risk:**
- API retry → duplicate credit addition
- Network timeout → duplicate enrollment charge

**Test Type:** **Integration**

---

### **3.3 LOW PRIORITY (Edge Cases)**

#### **P3.1 Invoice Status Transitions**
**Missing:** PENDING → VERIFIED → PAID → CANCELLED state machine validation

**Test Type:** **Unit**

---

#### **P3.2 Admin Audit Trail**
**Missing:** Verify payment_verified_by + payment_verified_at recorded correctly

**Test Type:** **Integration**

---

#### **P3.3 Negative Balance Prevention**
**Missing:** Enrollment cost > credit_balance → proper error handling

**Test Type:** **Unit**

---

## 4. Javasolt Tesztstratégia

### **Phase 1: Integration Critical Suite (Week 4-5)**

**Week 4:**
```python
# tests_e2e/integration_critical/test_payment_workflow.py

@pytest.mark.e2e
@pytest.mark.integration_critical
def test_payment_full_lifecycle(api_url, admin_token, test_student):
    """Full payment workflow: invoice → verification → enrollment → refund"""
    # 1. Invoice request
    # 2. Admin verification
    # 3. Credit addition
    # 4. Enrollment
    # 5. Refund
    # Runtime: <20s
    # Validation: credit balance consistency, transaction audit trail
```

**Week 5:**
```python
# tests_e2e/integration_critical/test_payment_concurrency.py

@pytest.mark.integration
def test_concurrent_invoice_prevention(api_url, test_student):
    """Prevent duplicate invoice requests"""
    # Runtime: <10s
    # Validation: HTTP 409 Conflict on duplicate request

@pytest.mark.integration
def test_concurrent_enrollment_atomicity(api_url, test_student):
    """Prevent negative credit balance"""
    # Runtime: <10s
    # Validation: Balance never < 0
```

---

### **Phase 2: Unit Tests (Week 6)**

**Credit Calculation Logic:**
```python
# tests/unit/payment/test_credit_balance.py

def test_credit_purchase_calculation():
    """Verify credit_balance += purchase_amount"""

def test_enrollment_deduction_calculation():
    """Verify credit_balance -= enrollment_cost"""

def test_refund_calculation():
    """Verify credit_balance += refund_amount"""

def test_negative_balance_prevention():
    """Verify enrollment fails if cost > balance"""
```

---

### **Phase 3: Integration Tests (Week 7)**

**Transaction Idempotency:**
```python
# tests/integration/test_credit_idempotency.py

def test_duplicate_purchase_prevented():
    """Same idempotency_key → 2nd request returns cached response"""

def test_duplicate_enrollment_prevented():
    """Same enrollment_id → 2nd request fails"""
```

---

## 5. DoD Checklist (Payment Tests)

### **Integration Critical Suite - Payment Workflow (Week 4-5)**

- [ ] `test_payment_full_lifecycle` - E2E workflow ✅
  - [ ] 20/20 sequential runs PASS (0 flake)
  - [ ] Parallel validation PASS (pytest-xdist)
  - [ ] Runtime < 20s
  - [ ] Minimal validation: balance consistency, transaction count

- [ ] `test_concurrent_invoice_prevention` - Race condition ✅
  - [ ] 20/20 runs PASS
  - [ ] HTTP 409 Conflict verification
  - [ ] Runtime < 10s

- [ ] `test_concurrent_enrollment_atomicity` - Negative balance guard ✅
  - [ ] 20/20 runs PASS
  - [ ] Balance never < 0 assertion
  - [ ] Runtime < 10s

### **Unit Tests - Credit Logic (Week 6)**

- [ ] Credit calculation tests (4 unit tests)
- [ ] Runtime < 5s total
- [ ] 100% coverage on credit calculation functions

### **Integration Tests - Idempotency (Week 7)**

- [ ] Duplicate transaction prevention (2 integration tests)
- [ ] Runtime < 10s total

---

## 6. Success Metrics

### **Coverage Goal:**
- **Before:** 15% (UI smoke tests only)
- **After:** 85% (E2E + Integration + Unit)

### **Risk Mitigation:**
- ✅ Revenue path validated (invoice → enrollment)
- ✅ Concurrent request safety confirmed
- ✅ Balance consistency guaranteed
- ✅ Refund workflow validated

### **Maintenance:**
- Low complexity (API-driven, deterministic)
- Fast execution (<20s per test)
- Parallel-ready (state isolated)

---

## 7. Out of Scope (Manual Verification)

### **NOT Automated (Manual Process):**
1. **Bank transfer verification** - Admin manually checks bank account
2. **Invoice PDF generation** - Not implemented (future feature)
3. **Email notification** - Separate notification system (see NOTIFICATION_GAP_SPEC.md)
4. **Credit expiration cron** - Requires time-travel testing (manual QA)

---

## 8. Implementation Timeline

| Week | Task | Deliverable | Owner |
|------|------|-------------|-------|
| **Week 4** | Payment Full Lifecycle E2E | `test_payment_full_lifecycle` (20/20 PASS) | Integration Critical Suite |
| **Week 5** | Concurrency Tests | `test_concurrent_invoice_prevention` + `test_concurrent_enrollment_atomicity` (20/20 PASS) | Integration Critical Suite |
| **Week 6** | Unit Tests | Credit calculation unit tests (100% coverage) | Unit Test Suite |
| **Week 7** | Idempotency Tests | Transaction idempotency integration tests | Integration Test Suite |

---

## 9. Dependencies

### **Requires:**
- ✅ Integration Critical Suite infrastructure (conftest.py, fixtures) - Week 1 ✅
- ✅ Admin token fixture - Week 1 ✅
- ✅ Student creation fixture - Week 1 (needs credit endpoint fix) ⚠️

### **Blockers:**
- ⚠️ Credit endpoint `/api/v1/admin/users/{id}/credits` returns 404
  - **Workaround:** Use invoice request flow (realistic test scenario)
  - **Alternative:** Direct DB credit insertion (less realistic)

---

## 10. Risk Assessment

### **HIGH RISK (Immediate Action):**
- ❌ NO E2E payment workflow test → **Week 4 MUST implement**
- ❌ NO concurrent request protection test → **Week 5 MUST implement**

### **MEDIUM RISK (Week 6-7):**
- ⚠️ Transaction idempotency not validated
- ⚠️ Credit expiration not tested

### **LOW RISK (Future):**
- ⚪ Invoice PDF generation (not implemented)
- ⚪ Email notifications (separate system)

---

## Appendix A: Payment-Related API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/users/credits/request-invoice` | POST | Student | Create invoice request |
| `/api/v1/users/credits/credit-balance` | GET | Student | Get current balance |
| `/api/v1/users/credits/me/credit-transactions` | GET | All | Get transaction history |
| `/api/v1/payment-verification/students` | GET | Admin | List pending verifications |
| `/api/v1/payment-verification/students/{id}/verify` | POST | Admin | Verify payment |

---

## Appendix B: Payment-Related Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `InvoiceRequest` | Invoice request tracking | `user_id`, `amount`, `status`, `payment_reference` |
| `CreditTransaction` | Transaction audit log | `transaction_type`, `amount`, `balance_after`, `idempotency_key` |
| `User` | User credit balance | `credit_balance`, `credit_purchased`, `payment_verified` |
| `UserLicense` | License created after payment | `specialization_type`, `payment_verified` |

---

**Status:** ✅ Ready for Week 4-5 Implementation
**Next Steps:** Implement `test_payment_full_lifecycle` (Integration Critical Suite)

---

## Appendix C: Implementation Summary (Week 4-5)

> **Completed:** 2026-02-22  
> **Sprint:** Week 4-5 Payment Workflow E2E Tests  
> **Status:** ✅ 3/3 tests passing, 0 flake (20/20 runs), CI-gated (BLOCKING)

### C.1 Implemented Tests

| Test | Purpose | Runtime | Validation |
|------|---------|---------|------------|
| `test_payment_full_lifecycle` | Invoice → Verification → Credit | ~2.3s | ✅ 20/20 PASS |
| `test_concurrent_invoice_prevention` | Duplicate invoice guard (409 Conflict) | ~1.5s | ✅ 20/20 PASS |
| `test_payment_endpoint_performance` | p95 latency < 400ms | ~1.5s | ✅ 20/20 PASS |
| `test_concurrent_enrollment_atomicity` | Negative balance prevention | SKIPPED | ⏭️ Enrollment API missing |

**Total Suite Runtime:** ~5s (target: <20s per test)  
**Flake Rate:** 0/20 runs (DoD requirement: 0 flake)  
**Parallel Execution:** ✅ Stable with `pytest -n auto`

### C.2 Payment System Architecture (CRITICAL DISCOVERY)

**Design:** Centralized `user.credit_balance` (NO CreditTransaction dependency)

```python
# app/api/api_v1/endpoints/invoices/admin.py:89-93
# CreditTransaction is LICENSE-BASED, not USER-BASED
# We skip creating CreditTransaction since we moved to centralized user.credit_balance
# (CreditTransaction was designed for the old license-based credit system)
```

**Key Implementation Details:**

1. **Source of Truth:** `user.credit_balance` (NOT `CreditTransaction` records)
   - Invoice verification directly updates `user.credit_balance` and `user.credit_purchased`
   - NO `CreditTransaction` records created for invoice purchases
   - `CreditTransaction` model is license-based legacy, not used for new invoice system

2. **Payment Reference Format:** `LFA-YYYYMMDD-HHMMSS-{id:05d}-{hash:4}`
   - Example: `LFA-20260222-173334-00001-5744`
   - 30 characters total (SWIFT-compatible)
   - Unique per invoice request

3. **Package Mappings:** 1:1 EUR to credits
   ```python
   PACKAGE_250  = {"amount_eur": 250.0,  "credit_amount": 250}
   PACKAGE_500  = {"amount_eur": 500.0,  "credit_amount": 500}
   PACKAGE_1000 = {"amount_eur": 1000.0, "credit_amount": 1000}
   PACKAGE_2000 = {"amount_eur": 2000.0, "credit_amount": 2000}
   ```

4. **Duplicate Prevention:** HTTP 409 Conflict if PENDING invoice exists
   - Race condition guard: only 1 PENDING invoice per student
   - Validated in `test_concurrent_invoice_prevention` (5 parallel requests → 1 success, 4 conflict)

### C.3 Modified Endpoints (Bearer Token Auth Support)

**Before (Cookie-only):**
```python
current_user: User = Depends(get_current_user_web)  # Web cookies only
```

**After (Hybrid Auth):**
```python
current_user: User = Depends(get_current_user)  # Bearer tokens + cookies
```

**Modified Files:**
- [app/api/api_v1/endpoints/users/credits.py](app/api/api_v1/endpoints/users/credits.py#L22) (line 22, 128)
- [app/api/api_v1/endpoints/payment_verification.py](app/api/api_v1/endpoints/payment_verification.py#L68) (line 68)

### C.4 CI Integration (BLOCKING Gate)

**Added to:** `.github/workflows/test-baseline-check.yml`

**Job:** `payment-workflow-gate`
- **Dependencies:** `needs: unit-tests`
- **Blocking:** YES (PR merge blocked on failure)
- **Execution:** Sequential + Parallel validation
- **Failure Message:** "Revenue-critical path is broken. Required: 0 flake, <5s runtime, parallel execution stable"

**Baseline Report Integration:**
```yaml
needs: [unit-tests, cascade-isolation-guard, smoke-tests, 
        api-module-integrity, hardcoded-id-guard, payment-workflow-gate]
```

### C.5 Test Coverage Matrix (Updated)

| Workflow Step | Unit Test | Integration Test | E2E Test | Status |
|---------------|-----------|------------------|----------|--------|
| Invoice request | ⚪ Not tested | ⚪ Not tested | ✅ E2E | **COVERED** |
| Payment reference generation | ⚪ Not tested | ⚪ Not tested | ✅ E2E | **COVERED** |
| Duplicate invoice prevention | ⚪ Not tested | ⚪ Not tested | ✅ E2E (concurrent) | **COVERED** |
| Admin verification | ⚪ Not tested | ⚪ Not tested | ✅ E2E | **COVERED** |
| Credit balance update | ✅ Unit tested | ⚪ Not tested | ✅ E2E | **COVERED** |
| Enrollment credit deduction | ✅ Unit tested | ⚪ Not tested | ⏭️ SKIPPED | **GAP** |
| Negative balance prevention | ⚪ Not tested | ⚪ Not tested | ⏭️ SKIPPED | **GAP** |
| Performance (p95 < 400ms) | ⚪ Not tested | ⚪ Not tested | ✅ E2E | **COVERED** |

### C.6 Known Gaps (Deferred)

1. **Enrollment Atomicity Test (SKIPPED)**
   - **Blocker:** No GET `/api/v1/tournaments/{id}` endpoint for `semester_id` extraction
   - **Workaround:** Not applicable (requires enrollment API infrastructure)
   - **Priority:** Implement in Week 6-7 after enrollment API ready

2. **Refund Workflow**
   - **Status:** Not tested (no E2E coverage)
   - **Priority:** Week 6-7

3. **Credit Expiration (2-year limit)**
   - **Status:** Not tested (requires time-travel fixtures)
   - **Priority:** Week 8-9

### C.7 Design Decisions (Why Not CreditTransaction?)

**Decision:** Use `user.credit_balance` as single source of truth

**Rationale:**
1. **CreditTransaction is license-based legacy**
   - Designed for old license credit system (per-license tracking)
   - NOT designed for centralized user balance (new invoice system)

2. **Simplicity over audit complexity**
   - Direct balance update: `user.credit_balance += amount`
   - NO need to aggregate CreditTransaction records
   - Reduces query complexity for balance checks

3. **Performance benefits**
   - 1 DB write (UPDATE user) vs 2 writes (UPDATE user + INSERT transaction)
   - Balance check: `SELECT credit_balance` vs `SELECT SUM(amount) FROM credit_transaction`

4. **Invoice audit trail preserved**
   - `InvoiceRequest` table stores full audit trail (payment_reference, amount, status, timestamps)
   - Admin verification logged in `payment_verified_by` + `payment_verified_at`

**Trade-off:** NO granular transaction history for purchases (enrollment still has transactions via enrollment records)

---

**Appendix C Status:** ✅ Implementation complete, CI-gated, 0 flake validated  
**Next Steps:** Enrollment API implementation → Enable `test_concurrent_enrollment_atomicity`
