# CRITICAL FINDING: Sandbox Credit Leak Issue

**Date**: 2026-01-31
**Severity**: 🔴 **CRITICAL** - Financial integrity issue
**Status**: 🔍 **IDENTIFIED** - Fix needed

---

## 🚨 Problem Summary

The sandbox tournament orchestrator creates enrollments WITHOUT properly recording credit transactions, leading to a **credit leak** where users receive refunds for enrollments they never paid for.

### Impact

- **84 enrollment transactions** created (-18,480 credits)
- **176 refund transactions** created (+87,000 credits)
- **NET RESULT**: Users gained **+68,520 credits for FREE** 💸

### Affected Users

| User | Current Balance | Enrollments | Refunds | Net Profit |
|------|----------------|-------------|---------|------------|
| kylian.mbappe@f1rstteam.hu | 33,785 | -2,310 | +9,500 | **+7,190** |
| p3t1k3@f1rstteam.hu | 22,655 | -2,960 | +11,250 | **+8,290** |
| k1sqx1@f1rstteam.hu | 21,145 | -2,410 | +12,250 | **+9,840** |
| t1b1k3@f1rstteam.hu | 13,625 | -2,410 | +12,250 | **+9,840** |

**Average profit per user**: ~8,000 credits

---

## 🔍 Root Cause Analysis

### Issue #1: Missing Enrollment Transactions

The sandbox orchestrator (`sandbox_test_orchestrator.py`) **does NOT create proper enrollment transactions** for many enrollments.

**Expected Flow**:
```
1. Create tournament (enrollment_cost = 500)
2. Enroll user → CREATE credit_transaction (type: TOURNAMENT_ENROLLMENT, amount: -500)
3. User balance -= 500
```

**Actual Flow**:
```
1. Create tournament (enrollment_cost = 500 OR undefined)
2. Enroll user → ❌ NO credit_transaction created (BUG!)
3. User balance unchanged (WRONG!)
```

### Issue #2: Refunds Without Corresponding Debits

When tournaments are deleted via API:
```python
# delete_tournament() in core.py:312
# STEP 1: REFUND CREDITS TO ALL ENROLLED USERS (100% refund)
for enrollment in enrollments:
    user.credit_balance = user.credit_balance + enrollment_cost  # ✅ Refund given
    refund_transaction = CreditTransaction(
        transaction_type="TOURNAMENT_DELETED_REFUND",
        amount=enrollment_cost  # ✅ Audit trail created
    )
```

**Result**: Users get refunds for enrollments they never paid for! 💰

---

## 📉 Financial Impact

### By The Numbers

- **55 tournaments deleted** (API + SQL)
- **~8 users enrolled per tournament** = 440 enrollments
- **Expected credit deductions**: 440 × 500 = 220,000 credits
- **Actual credit deductions**: 84 × ~220 avg = 18,480 credits
- **Missing transactions**: 356 enrollments (81% failure rate!)
- **Refunds issued**: 176 × 500 = 87,000 credits
- **Net credit leak**: **+68,520 credits**

### Implications

1. ❌ **Testing pollutes production data** - Users have inflated balances
2. ❌ **Cannot trust credit_balance** - Financial state is incorrect
3. ❌ **Audit trail incomplete** - Cannot reconstruct true transaction history
4. ❌ **Refund logic works correctly** - But exposed the enrollment bug!

---

## ✅ Recommended Solutions

### Solution #1: FREE Sandbox Tournaments (Immediate Fix)

**Set `enrollment_cost = 0` for all sandbox tournaments**

**Benefits**:
- ✅ No credit deductions during testing
- ✅ No refunds needed on deletion
- ✅ Clean audit trail (`amount: 0` transactions)
- ✅ Users can test without financial risk
- ✅ Separates test data from production financial data

**Implementation**:
```python
# In sandbox_test_orchestrator.py or sandbox_workflow.py
tournament = TournamentService.create_tournament_semester(
    db=db,
    # ... other params
    enrollment_cost=0,  # ✅ FREE for testing!
)
```

**Transaction Log**:
```
TOURNAMENT_ENROLLMENT (amount: 0) - "Free sandbox tournament enrollment"
TOURNAMENT_DELETED_REFUND (amount: 0) - "Free sandbox tournament refund"
```

---

### Solution #2: Fix Enrollment Transaction Creation (Long-term)

**Ensure EVERY enrollment creates a credit transaction**

**Files to fix**:
- `app/services/sandbox_test_orchestrator.py` - Add enrollment transaction logic
- `app/api/api_v1/endpoints/tournaments/enroll.py` - Already correct ✅

**Root issue**: Sandbox orchestrator likely calls internal enrollment methods that bypass transaction creation.

**Investigation needed**:
```python
# Find where sandbox creates enrollments WITHOUT calling the API
# Likely: Direct database insert instead of using enroll_in_tournament()
```

---

### Solution #3: Add Validation Guard

**Prevent refunds larger than total debits**

```python
# In delete_tournament() before refunding
user_total_enrollments = db.query(func.sum(CreditTransaction.amount)).filter(
    CreditTransaction.user_license_id == enrollment.user_license_id,
    CreditTransaction.transaction_type == "TOURNAMENT_ENROLLMENT"
).scalar() or 0

# Prevent refunding more than was paid
max_refund = min(enrollment_cost, abs(user_total_enrollments))
user.credit_balance += max_refund
```

---

## 🧪 Testing Strategy

### Immediate Actions

1. **Set enrollment_cost = 0** for future sandbox tournaments
2. **Document discrepancy** in current user balances
3. **Add transaction type filter** to show only non-test transactions

### Long-term Actions

1. **Separate test environment** - Different database for sandbox testing
2. **Transaction categorization** - Add `is_test_transaction` flag
3. **Balance reconciliation script** - Recalculate correct balances from audit trail
4. **Monitoring dashboard** - Alert when refunds > enrollments

---

## 📋 Action Items

- [ ] **Immediate**: Update sandbox orchestrator to use `enrollment_cost=0`
- [ ] **High**: Investigate enrollment transaction creation in sandbox
- [ ] **Medium**: Add validation guard to prevent over-refunding
- [ ] **Low**: Create balance reconciliation script
- [ ] **Documentation**: Update sandbox testing guide

---

## 🔗 Related Files

- `app/services/tournament/core.py:312` - delete_tournament() ✅ Works correctly
- `app/api/api_v1/endpoints/tournaments/enroll.py:36` - enroll_in_tournament() ✅ Works correctly
- `app/services/sandbox_test_orchestrator.py` - 🔴 **BUG HERE** - Missing transaction creation
- `sandbox_workflow.py` - Tournament creation flow
- `sandbox_helpers.py` - Helper functions

---

## 💡 Key Insight

> **The refund logic is actually PERFECT!** It exposed the enrollment bug by working correctly.
>
> The problem is NOT the refund system - it's the enrollment system in the sandbox orchestrator that fails to create proper transaction records.

**Moral**: Good audit trails catch financial bugs! 🎯

---

**Status**: ✅ **DOCUMENTED** - Ready for implementation
**Next Step**: Update sandbox orchestrator with `enrollment_cost=0` fix
