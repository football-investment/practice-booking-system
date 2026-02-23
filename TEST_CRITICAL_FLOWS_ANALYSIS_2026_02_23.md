# test_critical_flows.py — Comprehensive API Behavior Analysis
## 2026-02-23 14:00 CET

> **Goal**: Methodical diagnosis of 4 failing tests
> **Approach**: API behavior vs test expectation analysis → No workarounds
> **Status**: 🔬 IN PROGRESS

---

## 📊 Test Inventory

### Failing Tests (4):
1. ❌ `TestBookingFlow::test_complete_booking_flow_success`
2. ❌ `TestBookingFlow::test_booking_flow_rule_violations`
3. ❌ `TestGamificationFlow::test_complete_gamification_flow_with_xp`
4. ❌ `TestGamificationFlow::test_gamification_xp_calculation_variants`

---

## 🔬 Test Analysis #1: test_complete_booking_flow_success

### Error Details

**Error Type**: `TypeError`
**Error Message**: `'hashed_password' is an invalid keyword argument for User`
**Location**: `app/tests/test_critical_flows.py:289`

**Stack Trace**:
```python
app/tests/test_critical_flows.py:286: in test_complete_booking_flow_success
    student = User(
        name="Booking Test Student",
        email="bookingstudent@test.com",
        hashed_password=get_password_hash("student123"),  # ❌ WRONG FIELD NAME
        role=UserRole.STUDENT,
        onboarding_completed=True,
        specialization="INTERNSHIP"
    )
```

---

### API Behavior Analysis

**Current API Schema** (User model):
```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)  # ✅ CORRECT FIELD NAME
    role = Column(Enum(UserRole), nullable=False)
    onboarding_completed = Column(Boolean, default=False)
    specialization = Column(String, nullable=True)
```

**Test Expectation**:
```python
hashed_password=get_password_hash("student123")  # ❌ LEGACY FIELD NAME
```

**Actual Field Name**:
```python
password_hash=get_password_hash("student123")  # ✅ CORRECT
```

---

### Root Cause

**Category**: Fixture Field Name Mismatch (Legacy Assumption)

**Explanation**:
1. User model field was renamed: `hashed_password` → `password_hash`
2. Naming change occurred during early development or refactoring
3. Test was not updated to reflect model schema change
4. This is NOT a business rule change or API behavior change
5. This is a simple field naming inconsistency

**Evidence**:
- ✅ Field `password_hash` exists in User model (confirmed in conftest.py line 81)
- ❌ Field `hashed_password` does NOT exist in current User schema
- ✅ Same pattern already fixed in `conftest.py::instructor_user` fixture (line 62)
- ✅ Same pattern already fixed in `test_tournament_cancellation_e2e.py`

---

### Decision Matrix

| Option | Correctness | Impact | Recommendation |
|--------|-------------|--------|----------------|
| Fix Test (rename field) | ✅ API is correct | Low (test-side only) | ✅ **RECOMMENDED** |
| Fix Production Code | ❌ API field name is standard | High (schema migration) | ❌ **NOT RECOMMENDED** |
| Workaround (alias field) | ❌ Technical debt | Medium (maintenance burden) | ❌ **FORBIDDEN** |

---

### Decision: ✅ **FIX TEST** (Field Name Correction)

**Reasoning**:
1. **API Correctness**: `password_hash` follows security naming conventions
2. **Consistency**: Field name matches `get_password_hash()` function name
3. **Precedent**: Same fix already applied in other test files
4. **Low Impact**: Test-side change only, no production code affected
5. **No Business Logic Change**: Pure naming fix, no behavior change

**Action Required**:
- Line 289: Change `hashed_password` → `password_hash`
- Line 374: Verify same field in second User creation (likely same issue)

---

### Side Effects Analysis

**Database**: None (test uses fixtures, no schema change)
**Credit Transactions**: None (test doesn't involve credit system)
**State Transitions**: None (test creates User model only)
**Audit Trail**: None (no audit records created in fixture setup)
**Idempotency**: N/A (fixture creation, not API call)

---

### Verification Plan

**After Fix**:
1. Run test individually: `pytest app/tests/test_critical_flows.py::TestBookingFlow::test_complete_booking_flow_success -xvs`
2. Verify User fixture creates successfully
3. Verify booking flow executes (may encounter additional issues downstream)
4. Check for similar `hashed_password` usages in same file
5. Full regression run on all critical tests

---

## 🔬 Test Analysis #2: test_booking_flow_rule_violations

### Initial Scan (Before Detailed Analysis)

**Likely Issue**: Same `hashed_password` field name issue at line 374

**Code Inspection**:
```python
# Line 371-378
student = User(
    name="Rule Test Student",
    email="rulestudent@test.com",
    hashed_password=get_password_hash("student123"),  # ❌ LIKELY SAME ISSUE
    role=UserRole.STUDENT,
    onboarding_completed=True,
    specialization="INTERNSHIP"
)
```

**Additional Issue Spotted** (Line 393):
```python
mode=SessionType.hybrid  # ❌ WRONG FIELD NAME (should be session_type)
```

**Decision**: Analyze after fixing Test #1 to isolate issues

---

## 🔬 Test Analysis #3-4: Gamification Flow Tests

### Initial Scan (Before Detailed Analysis)

**Status**: Not yet analyzed (sequential approach)

**Strategy**:
1. Fix Test #1 first
2. Fix Test #2 second
3. Analyze Test #3-4 only after #1-2 pass
4. Isolate API behavior issues from fixture issues

---

## 📋 Fix Priority Queue

### Priority #1: Field Name Corrections (Fixture Bugs)
- [ ] test_complete_booking_flow_success (line 289)
- [ ] test_booking_flow_rule_violations (line 374)
- [ ] test_booking_flow_rule_violations (line 393 - mode → session_type)

### Priority #2: API Behavior Analysis (After Fixture Fixes)
- [ ] Analyze booking flow API endpoints
- [ ] Analyze check-in API endpoint
- [ ] Analyze feedback API endpoint
- [ ] Analyze gamification XP calculation

### Priority #3: Business Rule Validation
- [ ] Verify 24h booking deadline rule
- [ ] Verify 15min check-in window rule
- [ ] Verify 24h feedback window rule
- [ ] Verify XP calculation formulas

---

## 🎯 Success Criteria

**Fixture Fixes**:
- ✅ All User creations use `password_hash`
- ✅ All SessionModel creations use `session_type`
- ✅ No schema workarounds or aliases

**API Behavior Validation**:
- ✅ Test expectations match actual API responses
- ✅ Business rules correctly implemented in API
- ✅ State transitions validated
- ✅ Side effects documented

**Final State**:
- ✅ 4/4 tests PASSING
- ✅ No new failures introduced
- ✅ Full regression run clean
- ✅ Pipeline ≥86% pass rate

---

---

## 🔬 Production Bug Analysis #2: spec_validation.py

### Error Details

**Error Type**: `AttributeError`
**Error Message**: `'Session' object has no attribute 'specialization_type'. Did you mean: 'specialization_badge'?`
**Location**: `app/api/helpers/spec_validation.py:47`

**Stack Trace**:
```python
app/api/helpers/spec_validation.py:47: in validate_can_book_session
    if not session.specialization_type:  # ❌ WRONG FIELD NAME
        raise HTTPException(...)

app/api/helpers/spec_validation.py:55: in validate_can_book_session
    spec_service = get_spec_service(session.specialization_type)  # ❌ WRONG FIELD NAME
```

---

### API Behavior Analysis

**Session Model Schema** (app/models/session.py):
```python
# Line 40-44: Actual specialization field
target_specialization = Column(
    Enum(SpecializationType),
    nullable=True,
    comment="Target specialization for this session (null = all specializations)"
)

# Line 46-50: Mixed specialization flag
mixed_specialization = Column(
    Boolean,
    default=False,
    comment="Whether this session is open to all specializations"
)

# Line 267-269: Helper property
@property
def is_accessible_to_all(self) -> bool:
    """Check if session is accessible to all specializations"""
    return self.mixed_specialization or self.target_specialization is None
```

**Current (WRONG) Validation Code**:
```python
if not session.specialization_type:  # ❌ Field doesn't exist
    raise HTTPException(...)
spec_service = get_spec_service(session.specialization_type)  # ❌ Field doesn't exist
```

**Correct Field Names**:
- ✅ `target_specialization` (Column, Enum) - Database field
- ✅ `mixed_specialization` (Column, Boolean) - Database field
- ⚠️ `specialization_badge` (@property) - Computed property, NOT for validation
- ✅ `is_accessible_to_all` (@property) - Helper for validation logic

---

### Root Cause

**Category**: Production Code Bug - Field Name + Logic Error

**Explanation**:
1. Field `specialization_type` does NOT exist in Session model
2. Correct field name is `target_specialization` (Enum)
3. **Business Logic Issue**: Validation code raises error when `target_specialization=None`
4. **Correct Business Logic**: `target_specialization=None` means "session accessible to ALL specializations" (per model comment)
5. Validation should SKIP spec service check when `is_accessible_to_all=True`

**Evidence**:
- ❌ Field `specialization_type` does NOT exist in Session model
- ✅ Field `target_specialization` exists (Line 40-44, Enum(SpecializationType))
- ✅ Session model comment: "null = all specializations" (Line 43)
- ✅ Property `is_accessible_to_all` implements correct logic (Line 267-269)

---

### Decision Matrix

| Option | Correctness | Impact | Recommendation |
|--------|-------------|--------|----------------|
| Fix Production Code (field name + logic) | ✅ Session model is correct | Medium (API validation logic) | ✅ **RECOMMENDED** |
| Add `specialization_type` to Session model | ❌ Creates redundant field | High (schema migration) | ❌ **NOT RECOMMENDED** |
| Workaround (alias property) | ❌ Technical debt | Medium (maintenance burden) | ❌ **FORBIDDEN** |

---

### Decision: ✅ **FIX PRODUCTION CODE** (Field Name + Business Logic)

**Reasoning**:
1. **Model Correctness**: Session model uses `target_specialization`, not `specialization_type`
2. **Business Logic**: Session model explicitly supports "null = all specs" (Line 43 comment)
3. **Clean API**: Property `is_accessible_to_all` exists for this exact validation scenario
4. **No Schema Change**: Fix is API-only, no database migration required
5. **User Directive**: "Ha a teszt helyes → production code fix (nem workaround)"

**Action Required**:
- Line 47: Use `session.is_accessible_to_all` check instead of raising error
- Line 55: Change `session.specialization_type` → `session.target_specialization.value`
- Add early return for sessions accessible to all specializations

---

### Side Effects Analysis

**Database**: None (API validation logic only, no schema change)
**Credit Transactions**: Indirect (fixes booking flow, enables credit deduction)
**State Transitions**: Indirect (fixes booking creation flow)
**Audit Trail**: None (no audit records affected)
**Idempotency**: N/A (validation function, no state mutation)

---

### Corrected Validation Logic

**Before (BROKEN)**:
```python
def validate_can_book_session(user, session, db):
    if not session.specialization_type:  # ❌ Field doesn't exist
        raise HTTPException(...)
    spec_service = get_spec_service(session.specialization_type)  # ❌ Field doesn't exist
    return spec_service.can_book_session(user, session, db)
```

**After (CORRECT)**:
```python
def validate_can_book_session(user, session, db):
    # If session is accessible to all specializations, allow booking
    if session.is_accessible_to_all:  # ✅ Uses correct property
        return True, "Session is accessible to all specializations"

    # Validate against specific specialization
    spec_service = get_spec_service(session.target_specialization.value)  # ✅ Correct field
    return spec_service.can_book_session(user, session, db)
```

---

### Verification Plan

**After Fix**:
1. Run test individually: `pytest app/tests/test_critical_flows.py::TestBookingFlow::test_complete_booking_flow_success -xvs`
2. Verify booking creation succeeds (no AttributeError)
3. Verify specialization validation works for restricted sessions
4. Verify all-access sessions bypass spec validation
5. Run all 4 critical_flows tests
6. Full regression run on app/tests/

---

## 📝 Change Log

### 2026-02-23 14:00 - Initial Analysis
- Analyzed test_complete_booking_flow_success
- Root cause identified: `hashed_password` field name mismatch
- Decision: Fix test (field name correction)
- Status: Ready for implementation

### 2026-02-23 14:30 - Fixture Bugs Fixed
- Fixed 6 field name instances in test_critical_flows.py
- `hashed_password` → `password_hash` (3 instances)
- `mode` → `session_type` (2 instances)
- Status: Test fixtures corrected

### 2026-02-23 14:45 - Production Bug Discovered
- Re-ran tests after fixture fix
- Discovered PRODUCTION BUG in spec_validation.py
- Root cause: `session.specialization_type` field doesn't exist
- Analyzed Session model schema
- Decision: Fix production code (field name + business logic)
- Status: Ready for production fix

---

**Created**: 2026-02-23 14:00 CET
**Updated**: 2026-02-23 14:45 CET
**Analyst**: Claude Sonnet 4.5
**Status**: 🔬 Production Bug Analysis Complete - Ready for Fix
