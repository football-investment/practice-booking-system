# P2 Feature Backlog — Missing Endpoints
**Created:** 2026-03-01
**Status:** Approved for Implementation
**Priority:** P2 (Post-Stabilization)
**Total Tickets:** 3

---

## TICKET-SMOKE-001: Assignment Cancellation Endpoint

**Type:** Feature Implementation
**Priority:** P2 (Medium)
**Estimated Effort:** 2-3 days
**Blocked By:** None
**Blocks:** test_cancel_assignment_request_input_validation (currently skipped)

### **Description**
Implement instructor assignment cancellation endpoint to allow admins/instructors to cancel pending assignment requests.

### **Endpoint Specification**
```
PATCH /api/v1/instructor-assignments/requests/{request_id}/cancel
```

**Request Body:**
```json
{
  "reason": "string (optional, max 500 chars)"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Assignment request cancelled",
  "request_id": 123,
  "status": "CANCELLED",
  "cancelled_at": "2026-03-01T12:00:00Z",
  "cancelled_by": 456
}
```

**Error Responses:**
- `404` - Request not found
- `403` - Unauthorized (not admin/owner)
- `409` - Cannot cancel (already accepted/completed)
- `422` - Validation error (invalid reason length)

### **Acceptance Criteria**

#### **AC-001: Cancel Pending Request**
**Given** an admin user
**When** they cancel a pending assignment request with valid reason
**Then** the request status changes to CANCELLED
**And** the cancellation timestamp is recorded
**And** the cancelling user ID is stored
**And** the response returns 200 OK with request details

#### **AC-002: Reject Invalid Cancellations**
**Given** an assignment request in ACCEPTED status
**When** admin attempts to cancel it
**Then** the API returns 409 Conflict
**And** the error message is "Cannot cancel accepted assignment"
**And** the request status remains ACCEPTED

#### **AC-003: Input Validation**
**Given** a cancel request with invalid payload
**When** the payload contains extra fields OR reason > 500 chars
**Then** the API returns 422 Unprocessable Entity
**And** the error details specify which field is invalid

#### **AC-004: Authorization**
**Given** a student user (non-admin/non-instructor)
**When** they attempt to cancel an assignment
**Then** the API returns 403 Forbidden
**And** no database changes occur

#### **AC-005: Audit Trail**
**Given** a successful cancellation
**When** the request is cancelled
**Then** an audit log entry is created with:
- `action: ASSIGNMENT_CANCELLED`
- `user_id: {cancelling_user_id}`
- `resource_id: {request_id}`
- `metadata: {reason, original_status}`

### **Test Coverage Requirements**
- [x] `test_cancel_assignment_request_happy_path` (already exists)
- [x] `test_cancel_assignment_request_auth_required` (already exists)
- [ ] `test_cancel_assignment_request_input_validation` (currently SKIPPED - re-enable)
- [ ] `test_cancel_accepted_assignment_409_conflict` (NEW)
- [ ] `test_cancel_nonexistent_request_404` (NEW)

### **Implementation Checklist**
- [ ] Create endpoint handler in `app/api/api_v1/endpoints/instructor_assignments.py`
- [ ] Add `CancelAssignmentRequest` Pydantic schema with `extra='forbid'`
- [ ] Implement business logic in service layer
- [ ] Add state machine validation (PENDING → CANCELLED only)
- [ ] Add audit logging via `AuditService`
- [ ] Update router registration in `__init__.py`
- [ ] Remove `@pytest.mark.skip` from `test_cancel_assignment_request_input_validation`
- [ ] Add new test cases (AC-002, AC-005)
- [ ] Update API documentation
- [ ] Verify CI passes (0 failed tests)

### **Definition of Done**
- [ ] All acceptance criteria pass
- [ ] Test coverage ≥ 90% for new code
- [ ] Smoke test `test_cancel_assignment_request_input_validation` passes
- [ ] API documentation updated
- [ ] Code review approved by 2+ engineers
- [ ] CI pipeline green (0 failed tests)

---

## TICKET-SMOKE-002: LFA Player Onboarding Submission Endpoint

**Type:** Feature Implementation
**Priority:** P2 (Medium)
**Estimated Effort:** 3-4 days
**Blocked By:** None
**Blocks:** test_lfa_player_onboarding_submit_input_validation (currently skipped)

### **Description**
Implement LFA player onboarding submission endpoint to finalize player onboarding workflow after specialization selection.

### **Endpoint Specification**
```
POST /api/v1/onboarding/specialization/lfa-player/onboarding-submit
```

**Request Body:**
```json
{
  "parent_consent": true,
  "terms_accepted": true,
  "emergency_contact": {
    "name": "string",
    "phone": "string",
    "relationship": "string"
  },
  "medical_info": {
    "allergies": ["string"],
    "medications": ["string"],
    "conditions": ["string"]
  },
  "photo_consent": true
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Onboarding completed",
  "user_id": 123,
  "specialization": "LFA_PLAYER",
  "license_id": 456,
  "onboarding_completed_at": "2026-03-01T12:00:00Z"
}
```

**Error Responses:**
- `400` - Invalid input (missing required fields)
- `403` - Unauthorized (not student role)
- `409` - Already completed onboarding
- `422` - Validation error (invalid phone format, etc.)

### **Acceptance Criteria**

#### **AC-001: Complete Onboarding**
**Given** a student user with LFA_PLAYER specialization selected
**When** they submit valid onboarding data
**Then** their onboarding status changes to COMPLETED
**And** a UserLicense record is created with `specialization_type=LFA_PLAYER`
**And** the response returns 201 Created with license details

#### **AC-002: Validate Required Fields**
**Given** an onboarding submission missing `parent_consent`
**When** the request is submitted
**Then** the API returns 422 Unprocessable Entity
**And** the error message is "parent_consent is required"

#### **AC-003: Prevent Duplicate Submissions**
**Given** a student who already completed onboarding
**When** they submit again
**Then** the API returns 409 Conflict
**And** the error message is "Onboarding already completed"

#### **AC-004: Input Validation**
**Given** invalid payload with extra fields
**When** the payload contains unexpected fields
**Then** the API returns 422 Unprocessable Entity
**And** the error details specify forbidden extra fields

#### **AC-005: Data Persistence**
**Given** successful onboarding submission
**When** the data is saved
**Then** emergency contact is stored in `user_profile.emergency_contact` (JSON)
**And** medical info is stored in `user_profile.medical_info` (JSON)
**And** consent flags are stored in `user_profile.consents` (JSON)

### **Test Coverage Requirements**
- [x] `test_lfa_player_onboarding_submit_happy_path` (already exists)
- [x] `test_lfa_player_onboarding_submit_auth_required` (already exists)
- [ ] `test_lfa_player_onboarding_submit_input_validation` (currently SKIPPED - re-enable)
- [ ] `test_lfa_player_onboarding_duplicate_409_conflict` (NEW)
- [ ] `test_lfa_player_onboarding_creates_license` (NEW)

### **Implementation Checklist**
- [ ] Create endpoint handler in `app/api/api_v1/endpoints/onboarding/lfa_player.py`
- [ ] Add `LfaPlayerOnboardingRequest` Pydantic schema with nested models
- [ ] Implement business logic in `OnboardingService`
- [ ] Add UserLicense creation logic
- [ ] Add idempotency check (prevent duplicate submissions)
- [ ] Update UserProfile with consent/medical data
- [ ] Add router registration in `app/api/api_v1/endpoints/onboarding/__init__.py`
- [ ] Remove `@pytest.mark.skip` from `test_lfa_player_onboarding_submit_input_validation`
- [ ] Add new test cases (AC-003, AC-005)
- [ ] Update API documentation
- [ ] Verify CI passes (0 failed tests)

### **Definition of Done**
- [ ] All acceptance criteria pass
- [ ] Test coverage ≥ 90% for new code
- [ ] Smoke test `test_lfa_player_onboarding_submit_input_validation` passes
- [ ] UserProfile schema migration completed (if needed)
- [ ] Code review approved by 2+ engineers
- [ ] CI pipeline green (0 failed tests)

---

## TICKET-SMOKE-003: Specialization Selection Endpoint

**Type:** Feature Implementation
**Priority:** P2 (Medium)
**Estimated Effort:** 2-3 days
**Blocked By:** None
**Blocks:** test_specialization_select_submit_input_validation (currently skipped)

### **Description**
Implement specialization selection endpoint to allow students to choose their primary specialization during onboarding.

### **Endpoint Specification**
```
POST /api/v1/onboarding/specialization/select
```

**Request Body:**
```json
{
  "specialization_type": "LFA_PLAYER | LFA_COACH | LFA_ANALYST",
  "reason": "string (optional, max 500 chars)",
  "preferred_role": "string (optional, for LFA_PLAYER only)"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Specialization selected",
  "user_id": 123,
  "specialization": "LFA_PLAYER",
  "selected_at": "2026-03-01T12:00:00Z",
  "next_step": "Complete onboarding submission"
}
```

**Error Responses:**
- `400` - Invalid specialization type
- `403` - Unauthorized (not student role)
- `409` - Already selected specialization
- `422` - Validation error (invalid enum, extra fields)

### **Acceptance Criteria**

#### **AC-001: Select Valid Specialization**
**Given** a student user without specialization
**When** they submit valid specialization selection
**Then** their user profile is updated with `specialization_type`
**And** the response returns 200 OK with selection details

#### **AC-002: Reject Invalid Specialization**
**Given** a selection request with invalid `specialization_type="INVALID"`
**When** the request is submitted
**Then** the API returns 422 Unprocessable Entity
**And** the error message lists valid enum values

#### **AC-003: Prevent Duplicate Selection**
**Given** a student who already selected specialization
**When** they submit again
**Then** the API returns 409 Conflict
**And** the error message is "Specialization already selected"

#### **AC-004: Input Validation**
**Given** invalid payload with extra fields
**When** the payload contains unexpected fields
**Then** the API returns 422 Unprocessable Entity
**And** the error details specify forbidden extra fields

#### **AC-005: Onboarding Flow Integration**
**Given** successful specialization selection
**When** the specialization is saved
**Then** the user's onboarding status changes to `SPECIALIZATION_SELECTED`
**And** the next step in onboarding workflow is returned

### **Test Coverage Requirements**
- [x] `test_specialization_select_submit_happy_path` (already exists)
- [x] `test_specialization_select_submit_auth_required` (already exists)
- [ ] `test_specialization_select_submit_input_validation` (currently SKIPPED - re-enable)
- [ ] `test_specialization_select_duplicate_409_conflict` (NEW)
- [ ] `test_specialization_select_invalid_enum_422` (NEW)

### **Implementation Checklist**
- [ ] Create endpoint handler in `app/api/api_v1/endpoints/onboarding/specialization.py`
- [ ] Add `SpecializationSelectRequest` Pydantic schema with enum validation
- [ ] Implement business logic in `OnboardingService`
- [ ] Add idempotency check (prevent duplicate selections)
- [ ] Update UserProfile with specialization_type
- [ ] Add onboarding state machine transition (REGISTERED → SPECIALIZATION_SELECTED)
- [ ] Add router registration in `app/api/api_v1/endpoints/onboarding/__init__.py`
- [ ] Remove `@pytest.mark.skip` from `test_specialization_select_submit_input_validation`
- [ ] Add new test cases (AC-003, AC-005)
- [ ] Update API documentation
- [ ] Verify CI passes (0 failed tests)

### **Definition of Done**
- [ ] All acceptance criteria pass
- [ ] Test coverage ≥ 90% for new code
- [ ] Smoke test `test_specialization_select_submit_input_validation` passes
- [ ] Onboarding state machine documented
- [ ] Code review approved by 2+ engineers
- [ ] CI pipeline green (0 failed tests)

---

## Implementation Priority

**Sprint Planning Recommendation:**

| Ticket | Priority | Dependencies | Estimated Days | Sprint Allocation |
|--------|----------|--------------|----------------|-------------------|
| TICKET-SMOKE-003 | Highest | None | 2-3 | Sprint 1 (Week 1) |
| TICKET-SMOKE-002 | High | TICKET-SMOKE-003 | 3-4 | Sprint 1 (Week 2) |
| TICKET-SMOKE-001 | Medium | None | 2-3 | Sprint 2 (Week 3) |

**Rationale:**
1. **TICKET-SMOKE-003 first** - Specialization selection is the foundational step in onboarding workflow
2. **TICKET-SMOKE-002 second** - Depends on specialization being selected first
3. **TICKET-SMOKE-001 last** - Independent feature, can be implemented in parallel or after onboarding

---

## Success Metrics

| Metric | Before | Target After Implementation |
|--------|--------|----------------------------|
| Skipped Tests (P2 backlog) | 3 | 0 |
| Test Coverage | 1292 passed | 1295 passed (+3) |
| Smoke Test Success Rate | 99.8% (3 skipped) | 100% (0 skipped) |
| API Completeness | 97.3% | 100% |

---

## References

- **Root Cause Analysis:** [docs/FAILED_TESTS_ROOT_CAUSE_ANALYSIS.md](FAILED_TESTS_ROOT_CAUSE_ANALYSIS.md)
- **Skip Policy:** [.github/SMOKE_TEST_SKIP_POLICY.md](../.github/SMOKE_TEST_SKIP_POLICY.md)
- **Test Baseline:** [docs/BASELINE_SNAPSHOT_2026-03-01.md](BASELINE_SNAPSHOT_2026-03-01.md) (to be created)

---

**Last Updated:** 2026-03-01
**Owner:** Engineering Team
**Review Cycle:** Sprint Planning (Bi-weekly)
