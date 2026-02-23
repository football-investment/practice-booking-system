# Payment System Architecture

> **Version:** 2.0 (Invoice-Based Manual Payment)
> **Last Updated:** 2026-02-22
> **Status:** ✅ Production (CI-gated, 0 flake validated)

---

## Executive Summary

**Payment Model:** Manual invoice-based system (NO automated payment gateway)
**Architecture:** Centralized `user.credit_balance` (single source of truth)
**Legacy System:** `CreditTransaction` model (license-based, NOT used for invoice purchases)

---

## 1. Core Architecture Principle

### **Single Source of Truth: `user.credit_balance`**

```python
# Database schema (app/models/user.py)
class User(Base):
    credit_balance: int       # Current available credits (AUTHORITATIVE)
    credit_purchased: int     # Lifetime purchased credits (audit)
    payment_verified: bool    # Payment verification status
    payment_verified_at: datetime
    payment_verified_by: int  # Admin who verified payment
```

**Design Decision:** Direct balance tracking WITHOUT dependency on `CreditTransaction` records.

**Why?**
1. **Performance:** 1 DB read (`SELECT credit_balance`) vs aggregating transaction history
2. **Simplicity:** Direct UPDATE vs INSERT + aggregate queries
3. **Consistency:** Balance is always current, no need to recompute from transactions

---

## 2. Payment Lifecycle

### **Phase 1: Invoice Request (Student)**

**Endpoint:** `POST /api/v1/users/request-invoice`

```json
{
  "package_type": "PACKAGE_500",  // 500 EUR = 500 credits
  "specialization_type": "LFA_FOOTBALL_PLAYER"
}
```

**Response:**
```json
{
  "id": 123,
  "payment_reference": "LFA-20260222-173334-00123-A3F2",
  "amount_eur": 500.0,
  "credit_amount": 500,
  "status": "PENDING",
  "message": "Please transfer 500 EUR with reference: LFA-20260222-173334-00123-A3F2"
}
```

**Implementation:**
```python
# app/api/api_v1/endpoints/users/credits.py:85-122

# 1. Validate package type
package_info = PACKAGE_MAPPINGS[package_type]  # {amount_eur, credit_amount}

# 2. Check for duplicate PENDING invoice (race condition guard)
existing_invoice = db.query(InvoiceRequest).filter(
    InvoiceRequest.user_id == current_user.id,
    InvoiceRequest.status == "PENDING"
).first()
if existing_invoice:
    raise HTTPException(status_code=409, detail="Duplicate invoice")

# 3. Create InvoiceRequest with temp payment_reference
invoice = InvoiceRequest(
    user_id=current_user.id,
    amount_eur=amount_eur,
    credit_amount=credit_amount,
    status="PENDING",
    payment_reference="TEMP"
)
db.add(invoice)
db.flush()  # Get ID

# 4. Generate unique payment reference
payment_reference = f"LFA-{date}-{time}-{id:05d}-{hash:4}"
invoice.payment_reference = payment_reference
db.commit()
```

**Payment Reference Format:** `LFA-YYYYMMDD-HHMMSS-{id:05d}-{hash:4}`
- **Length:** 30 characters (SWIFT-compatible)
- **Uniqueness:** Timestamp + DB ID + MD5 hash
- **Example:** `LFA-20260222-173334-00123-A3F2`

---

### **Phase 2: Admin Verification**

**Endpoint:** `POST /api/v1/invoices/{invoice_id}/verify`

**Implementation:**
```python
# app/api/api_v1/endpoints/invoices/admin.py:31-115

# 1. Load InvoiceRequest
invoice = db.query(InvoiceRequest).get(invoice_id)

# 2. Validate status (must be PENDING)
if invoice.status != "PENDING":
    raise HTTPException(400, "Already verified")

# 3. Update user balance (CRITICAL: NO CreditTransaction created)
user.credit_balance += invoice.credit_amount
user.credit_purchased += invoice.credit_amount
user.payment_verified = True
user.payment_verified_at = datetime.utcnow()
user.payment_verified_by = admin_user.id

# 4. Update invoice status
invoice.status = "VERIFIED"
invoice.verified_at = datetime.utcnow()
invoice.verified_by = admin_user.id

# 5. Create UserLicense (if specialization provided)
if invoice.specialization:
    license = UserLicense(
        user_id=user.id,
        specialization_type=invoice.specialization,
        payment_verified=True
    )
    db.add(license)

db.commit()
```

**Key Design Decision (Lines 89-93):**
```python
# NOTE: CreditTransaction is LICENSE-BASED, not USER-BASED
# We need to find the primary user_license for this user's specialization
# Or we can skip creating CreditTransaction since we moved to centralized user.credit_balance
# For now, let's just update the user balance without creating a transaction
# (CreditTransaction was designed for the old license-based credit system)
```

**Translation:** The system does NOT create `CreditTransaction` records for invoice purchases.

---

## 3. Why NO CreditTransaction for Purchases?

### **Legacy System Context**

**Old Architecture (License-Based):**
```python
CreditTransaction:
  user_license_id  # FK to UserLicense (NOT User!)
  transaction_type  # PURCHASE, ENROLLMENT, REFUND
  amount
  balance_after  # License-specific balance (NOT user balance)
```

**Problem:** `CreditTransaction` was designed for **per-license credit tracking**, NOT centralized user balance.

**New Architecture (User-Based):**
```python
User:
  credit_balance    # Centralized user balance (all licenses)
  credit_purchased  # Lifetime total (audit)
```

### **Trade-offs**

| Approach | Pros | Cons |
|----------|------|------|
| **CreditTransaction** | Granular audit trail | 2x DB writes, complex aggregation queries |
| **user.credit_balance** | 1 DB write, fast balance checks | NO per-transaction history |

**Decision:** Use `user.credit_balance` for simplicity and performance.

**Audit Trail Preserved Via:**
- `InvoiceRequest` table (full payment history: amount, reference, status, timestamps, verified_by)
- `user.payment_verified_at` + `user.payment_verified_by` (admin verification audit)

---

## 4. Package Mappings

```python
PACKAGE_MAPPINGS = {
    "PACKAGE_250":  {"amount_eur": 250.0,  "credit_amount": 250},
    "PACKAGE_500":  {"amount_eur": 500.0,  "credit_amount": 500},
    "PACKAGE_1000": {"amount_eur": 1000.0, "credit_amount": 1000},
    "PACKAGE_2000": {"amount_eur": 2000.0, "credit_amount": 2000},
}
```

**Conversion Rate:** 1 EUR = 1 Credit (fixed rate, no variable pricing)

---

## 5. Race Condition Protection

### **Duplicate Invoice Prevention**

**Problem:** Student clicks "Request Invoice" button multiple times → multiple invoices created.

**Solution:** HTTP 409 Conflict if PENDING invoice already exists.

**Validation (E2E Test):**
```python
# test_payment_workflow.py:test_concurrent_invoice_prevention
# 5 parallel invoice requests → 1 success (200), 4 conflict (409)

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(create_invoice_request) for _ in range(5)]
    results = [future.result() for future in futures]

success_count = sum(1 for status, _ in results if status in [200, 201])
conflict_count = sum(1 for status, _ in results if status == 409)

assert success_count == 1, "Expected exactly 1 success"
assert conflict_count >= 3, "Expected at least 3 conflicts"
```

**Result:** ✅ 20/20 runs PASS (validated in CI)

---

## 6. API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/users/request-invoice` | POST | Student | Create invoice request |
| `/api/v1/users/credit-balance` | GET | Student | Get current balance |
| `/api/v1/users/me/credit-transactions` | GET | All | Transaction history (enrollment only) |
| `/api/v1/invoices/{id}/verify` | POST | Admin | Verify payment |

**Auth Support:** Bearer tokens (API testing) + cookies (web UI)

---

## 7. Database Schema

### **InvoiceRequest**
```python
id: int (PK)
user_id: int (FK → User)
amount_eur: float
credit_amount: int
specialization: str (nullable)
status: str  # PENDING, VERIFIED, CANCELLED
payment_reference: str (unique, indexed)
verified_at: datetime (nullable)
verified_by: int (FK → User, nullable)
created_at: datetime
updated_at: datetime
```

### **User (Credit Fields)**
```python
credit_balance: int       # Current balance (AUTHORITATIVE)
credit_purchased: int     # Lifetime total (audit)
payment_verified: bool    # First payment verified?
payment_verified_at: datetime
payment_verified_by: int  # Admin who verified
```

---

## 8. Testing Strategy

### **E2E Tests (Integration Critical Suite)**

**Location:** `tests_e2e/integration_critical/test_payment_workflow.py`

**Tests:**
1. `test_payment_full_lifecycle` — Invoice → Verification → Credit Balance
2. `test_concurrent_invoice_prevention` — Duplicate prevention (409)
3. `test_payment_endpoint_performance` — p95 latency < 400ms

**DoD Requirements:**
- ✅ 0 flake in 20 consecutive runs
- ✅ Runtime <20s per test (~5s total)
- ✅ Parallel execution stable (`pytest -n auto`)

**CI Integration:** BLOCKING gate in `.github/workflows/test-baseline-check.yml`

**Validation Results (2026-02-22):**
```
Run 1/20: PASS
Run 2/20: PASS
...
Run 20/20: PASS

✅ PASS: 20/20
❌ FAIL: 0/20
🎯 0 FLAKE ACHIEVED
```

---

## 9. Known Limitations

### **Enrollment Credit Deduction**

**Status:** NOT TESTED in E2E suite (missing enrollment API infrastructure)

**Test:** `test_concurrent_enrollment_atomicity` (SKIPPED)

**Blocker:** No GET `/api/v1/tournaments/{id}` endpoint to extract `semester_id` for enrollment.

**Workaround:** Test deferred to Week 6-7 after enrollment API ready.

---

## 10. Future Improvements

### **Potential Enhancements (NOT in scope):**
1. **Automated Payment Gateway** (Stripe/PayPal integration)
2. **Credit Expiration Cron Job** (2-year limit enforcement)
3. **Refund Workflow E2E Test** (enrollment withdrawal)
4. **Invoice PDF Generation** (downloadable receipt)
5. **Email Notifications** (payment confirmation, credit expiration warnings)

---

## 11. Migration from Legacy System

### **If you see `CreditTransaction` queries in old code:**

**DO NOT:**
- ❌ Query `CreditTransaction` to calculate user balance
- ❌ Create `CreditTransaction` records for invoice purchases
- ❌ Aggregate `SUM(amount)` from `CreditTransaction` table

**DO:**
- ✅ Query `user.credit_balance` directly
- ✅ Update `user.credit_balance` on payment verification
- ✅ Preserve audit trail via `InvoiceRequest` table

**Example (OLD vs NEW):**
```python
# ❌ OLD (license-based, complex)
balance = db.query(func.sum(CreditTransaction.amount)).filter(
    CreditTransaction.user_license_id.in_(user_license_ids)
).scalar() or 0

# ✅ NEW (user-based, simple)
balance = user.credit_balance
```

---

## 12. Summary

**Key Takeaways:**
1. **`user.credit_balance` is the single source of truth** — NO dependency on `CreditTransaction`
2. **Invoice purchases do NOT create `CreditTransaction` records** — audit trail via `InvoiceRequest`
3. **Duplicate invoice prevention via 409 Conflict** — validated in E2E tests (20/20 runs)
4. **Payment workflow is CI-gated (BLOCKING)** — 0 flake requirement enforced
5. **Enrollment credit deduction NOT TESTED yet** — deferred to Week 6-7

**Validation:** ✅ Production-ready (E2E tested, CI-gated, 0 flake)

---

**References:**
- [PAYMENT_WORKFLOW_GAP_SPECIFICATION.md](../PAYMENT_WORKFLOW_GAP_SPECIFICATION.md) — Gap analysis + implementation summary
- [app/api/api_v1/endpoints/users/credits.py](../app/api/api_v1/endpoints/users/credits.py) — Invoice request endpoint
- [app/api/api_v1/endpoints/invoices/admin.py](../app/api/api_v1/endpoints/invoices/admin.py) — Payment verification (lines 89-93: design rationale)
- [tests_e2e/integration_critical/test_payment_workflow.py](../tests_e2e/integration_critical/test_payment_workflow.py) — E2E tests
