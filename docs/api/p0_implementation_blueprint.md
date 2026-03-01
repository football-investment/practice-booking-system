# P0 Critical Endpoints - Implementation Blueprint

**Status:** Ready for Implementation
**Date:** 2026-02-28
**Target:** -11 failed tests (P0 Critical user-facing core features)

---

## Overview

| # | Endpoint | Type | Existing Logic | Effort |
|---|----------|------|----------------|--------|
| 1 | `POST /api/v1/auth/age-verification` | NEW | Web route exists | 1h |
| 2 | `POST /api/v1/motivation-assessment` | PATH FIX | `/licenses/motivation-assessment` | 5min |
| 3 | `POST /api/v1/admin/students/{id}/motivation/{spec}` | WRAPPER | Web route exists | 30min |
| 4 | `POST /api/v1/specialization/lfa-player/onboarding-submit` | WRAPPER | Web route exists | 30min |
| 5 | `POST /api/v1/specialization/motivation-submit` | WRAPPER | Web route exists | 30min |
| 6 | `POST /api/v1/specialization/select` | WRAPPER | Web route exists | 30min |
| 7 | `POST /api/v1/specialization/switch` | WRAPPER | Web route exists | 30min |
| 8 | `POST /api/v1/specialization/unlock` | WRAPPER | Web route exists | 30min |
| 9 | `POST /api/v1/start` | PATH FIX | `/quizzes/start` exists | 5min |
| 10 | `POST /api/v1/submit` | PATH FIX | `/quizzes/submit` exists | 5min |
| 11 | `POST /api/v1/quizzes/{id}/submit` | CHECK | May already exist | 5min |

**Total Estimated Effort:** ~4-5 hours

---

## 1. POST /api/v1/auth/age-verification

### Current State
- **Web Route:** `/age-verification` (POST, Form-based)
- **Location:** `app/api/web_routes/auth.py:130`
- **Logic:** Parse date, validate age (5-120), save `user.date_of_birth`

### Implementation

**Schema** (`app/schemas/auth.py`):
```python
from datetime import date

class AgeVerificationRequest(BaseModel):
    date_of_birth: date  # ISO format: "YYYY-MM-DD"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date_of_birth": "2010-01-15"
            }
        }
    )

class AgeVerificationResponse(BaseModel):
    success: bool
    age: int
    message: str
```

**Endpoint** (`app/api/api_v1/endpoints/auth.py` - append):
```python
from datetime import date

@router.post("/age-verification", response_model=AgeVerificationResponse)
def verify_age(
    data: AgeVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit age verification (COPPA/GDPR compliance)

    **Requirements:**
    - Age: 5-120 years
    - Date not in future
    - Student role only
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Age verification is only for students"
        )

    # Validate date
    today = date.today()
    dob = data.date_of_birth

    if dob > today:
        raise HTTPException(
            status_code=422,
            detail="Date of birth cannot be in the future"
        )

    # Calculate age
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    if age < 5:
        raise HTTPException(
            status_code=422,
            detail="You must be at least 5 years old to use this platform"
        )

    if age > 120:
        raise HTTPException(
            status_code=422,
            detail="Please enter a valid date of birth"
        )

    # Save
    current_user.date_of_birth = dob
    db.commit()

    return AgeVerificationResponse(
        success=True,
        age=age,
        message=f"Age verified successfully: {age} years old"
    )
```

**Router Registration:** Already registered in `/api/v1/auth`

---

## 2-3. Motivation Assessment Endpoints

### 2. POST /api/v1/motivation-assessment (PATH FIX)

**Current:** `/api/v1/licenses/motivation-assessment` ✅ EXISTS
**Test expects:** `/api/v1/motivation-assessment`

**Fix:** Create alias route

**Implementation** (`app/api/api_v1/api.py`):
```python
# Add alias for motivation-assessment (backward compatibility)
api_router.include_router(
    motivation.router,
    prefix="",  # NO PREFIX - direct under /api/v1
    tags=["motivation-assessment-alias"]
)
```

**Alternative:** Update test to use `/licenses/motivation-assessment` (not recommended - breaks API contract)

### 3. POST /api/v1/admin/students/{id}/motivation/{spec}

**Current:** `/admin/students/{id}/motivation/{spec}` (web route)
**Location:** `app/api/web_routes/specialization.py` or similar

**Implementation:** Create API wrapper in admin endpoints

---

## 4-8. Specialization Endpoints (Web Route Wrappers)

All exist as web routes (`/specialization/*`), need API v1 wrappers.

### Strategy
1. **Extract business logic** from web routes to service layer (if not already)
2. **Create thin API wrappers** that:
   - Accept JSON instead of Form data
   - Return JSON instead of HTML redirects
   - Reuse validation & business logic

### 4. POST /api/v1/specialization/lfa-player/onboarding-submit

**Web Route:** `/specialization/lfa-player/onboarding-submit`
**Logic:** Complete LFA Player onboarding flow

**Schema:**
```python
class LfaPlayerOnboardingRequest(BaseModel):
    # Extract from web route form fields
    specialization_code: str
    motivation_data: dict  # Specialization-specific
```

### 5. POST /api/v1/specialization/motivation-submit

**Web Route:** `/specialization/motivation-submit`
**Logic:** Submit motivation questionnaire

### 6. POST /api/v1/specialization/select

**Web Route:** `/specialization/select`
**Logic:** Select initial specialization

### 7. POST /api/v1/specialization/switch

**Web Route:** `/specialization/switch`
**Logic:** Switch to different specialization

### 8. POST /api/v1/specialization/unlock

**Web Route:** `/specialization/unlock`
**Logic:** Unlock specialization (spend 100 credits)

**All wrappers location:** Create `app/api/api_v1/endpoints/specialization.py` (if not exists)

---

## 9-11. Quiz Endpoints

### 9. POST /api/v1/start → /api/v1/quizzes/start (PATH FIX)

**Current:** `/api/v1/quizzes/start` ✅ EXISTS
**Test expects:** `/api/v1/start`

**Fix Option A:** Create alias route
**Fix Option B:** Update test (NOT RECOMMENDED)

**Implementation:**
```python
# In app/api/api_v1/endpoints/quiz.py
@router.post("/", response_model=QuizAttemptResponse)  # Mounted at /api/v1/quiz
def start_quiz_attempt_alias(...):
    # Delegate to existing /quizzes/start logic
    pass
```

Wait - this won't work. The test expects `/api/v1/start` which means mounting at root.

**Better fix:** Check if test path is wrong - likely should be `/api/v1/quiz/start` or `/api/v1/quizzes/start`

### 10. POST /api/v1/submit → /api/v1/quizzes/submit (PATH FIX)

Same as above.

### 11. POST /api/v1/quizzes/{quiz_id}/submit

**Check:** This may already exist as `/api/v1/quizzes/submit` with quiz_id in request body.

---

## Implementation Order

### Phase 1: Quick Wins (15 min)
1. ✅ Motivation path fix (alias route)
2. ✅ Quiz path fixes (check & document)

### Phase 2: Age Verification (1h)
3. ✅ Implement age verification endpoint + schema

### Phase 3: Specialization Wrappers (2-3h)
4-8. ✅ Create 5 specialization API wrappers

### Phase 4: Admin Motivation Wrapper (30min)
9. ✅ Admin motivation endpoint wrapper

### Phase 5: Validation & CI (30min)
10. Local testing
11. CI push & validation

---

## Testing Strategy

### Local Testing
```bash
# Test each endpoint
curl -X POST http://localhost:8000/api/v1/auth/age-verification \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date_of_birth": "2010-01-15"}'

# Run smoke tests
pytest tests/integration/api_smoke/test_auth_smoke.py::test_age_verification_submit_input_validation -v
```

### CI Validation
```bash
git add app/api app/schemas
git commit -m "feat(api): Implement P0 critical endpoints (11 endpoints)"
git push
```

**Expected Result:** -11 failed tests (91 → 80)

---

## Notes

- **Service Layer:** Extract web route logic to services if needed (avoid duplication)
- **Auth:** All endpoints require authentication
- **Validation:** Reuse existing Pydantic models where possible
- **Error Handling:** Return 422 for validation errors, 403 for permission errors
- **Audit Logging:** Consider adding audit logs for critical operations

---

**Ready to implement?** Confirm approach before starting.
