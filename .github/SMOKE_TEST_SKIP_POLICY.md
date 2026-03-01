# Smoke Test Skip Policy
**Effective Date:** 2026-03-01
**Status:** Active - Enforced in CI
**Owner:** Engineering Team

---

## Purpose

This policy defines when and how smoke tests can be skipped, ensuring that:
1. **Valid architectural skips** are properly documented and justified
2. **Coverage gaps** (skipped POST/PATCH/PUT with empty payloads) are systematically eliminated
3. **New tests** automatically fall into the correct category

---

## Skip Categories

### ✅ CATEGORY 1: Valid Architectural Skips (ALLOWED)

**Tests that MUST remain skipped due to technical constraints.**

#### 1.1 GET Endpoint Input Validation (~82 tests)
```python
@pytest.mark.skip(reason="GET endpoints don't have request body - cannot validate input")
def test_get_users_input_validation():
    # GET requests don't send request bodies
    # Input validation testing is architecturally impossible
    pass
```

**Justification:** GET endpoints receive parameters via URL query strings or path params, not request bodies. Pydantic validation testing requires a request body.

**Examples:**
- `test_list_users_input_validation`
- `test_get_tournament_input_validation`
- `test_read_profile_input_validation`

---

#### 1.2 DELETE Endpoint Input Validation (~27 tests)
```python
@pytest.mark.skip(reason="DELETE endpoints don't have request body - cannot validate input")
def test_delete_user_input_validation():
    # DELETE operations use URL path params only
    # No request body → no validation to test
    pass
```

**Justification:** DELETE endpoints identify resources via URL path params. Request bodies are not used (RESTful best practice).

**Examples:**
- `test_delete_tournament_input_validation`
- `test_delete_campus_input_validation`

---

#### 1.3 Implicit Operations (6 tests)
```python
@pytest.mark.skip(reason="POST /logout doesn't require request body - endpoint design is correct")
def test_logout_input_validation():
    # Logout invalidates session implicitly (no input data needed)
    pass

@pytest.mark.skip(reason="POST /admin/sync/all is bulk operation - doesn't require request body")
def test_sync_all_input_validation():
    # Bulk sync operations are idempotent and parameter-free
    pass

@pytest.mark.skip(reason="POST /{id}/toggle-active doesn't require request body - toggle operation")
def test_toggle_active_input_validation():
    # State flip operations derive new state from current state (no input)
    pass
```

**Justification:** These endpoints perform implicit operations where the operation itself is the intent. No request data is needed.

**Examples:**
- `test_logout_input_validation` (session invalidation)
- `test_refresh_token_input_validation` (bulk refresh)
- `test_toggle_active_input_validation` (state flip)
- `test_verify_payment_input_validation` (idempotent verification)
- `test_unverify_payment_input_validation` (idempotent un-verification)

---

### ⚠️ CATEGORY 2: Temporary Coverage Gaps (MUST FIX)

**Tests skipped due to missing domain-specific payloads - systematic elimination required.**

#### 2.1 TIER 1 - Critical (2 weeks deadline) ⏰
**Priority: P0 - Financial + Security**

```python
# ❌ BAD (current state - placeholder skip)
@pytest.mark.skip(reason="Input validation requires domain-specific payloads")
def test_create_invoice_input_validation():
    payload = {}  # Empty payload - useless
    response = api_client.post('/api/v1/invoices/request', json=payload)
    assert response.status_code in [400, 422]

# ✅ GOOD (required implementation)
def test_create_invoice_input_validation():
    """Validate invoice creation rejects invalid data"""
    # Domain-specific invalid payloads
    test_cases = [
        # Negative amount
        ({"amount": -100, "description": "Test", "user_id": 1},
         "amount must be positive"),

        # Missing required fields
        ({"amount": 100},
         "description is required"),

        # Type mismatch
        ({"amount": "not_a_number", "description": "Test", "user_id": "invalid"},
         "amount must be integer"),
    ]

    for payload, expected_error in test_cases:
        response = api_client.post('/api/v1/invoices/request', json=payload, ...)
        assert response.status_code == 422
        assert expected_error.lower() in response.json()["detail"].lower()
```

**Required Endpoints (50 tests):**
1. **Financial Operations**
   - `POST /api/v1/invoices/request`
   - `POST /api/v1/coupons/apply`
   - `PATCH /api/v1/invoices/{id}`

2. **Authentication & Authorization**
   - `POST /api/v1/auth/register`
   - `POST /api/v1/auth/login`
   - `PATCH /api/v1/users/{id}/role`

3. **Tournament/Session State Machine**
   - `POST /api/v1/tournaments`
   - `POST /api/v1/tournaments/{id}/enroll`
   - `POST /api/v1/sessions/{id}/results`

**Tracking:** See [TEST_SKIP_DECISION_MATRIX.md](../docs/TEST_SKIP_DECISION_MATRIX.md) Week 1-3 schedule

---

#### 2.2 TIER 2 - Medium (1 month deadline) ⏳
**Priority: P1 - UX + Data Quality**

**Required Endpoints (80 tests):**
- Profile updates: `PATCH /api/v1/users/{id}/profile`
- Settings: `POST /api/v1/settings/preferences`
- Notifications: `PATCH /api/v1/notifications/settings`

**Tracking:** See [TEST_SKIP_DECISION_MATRIX.md](../docs/TEST_SKIP_DECISION_MATRIX.md) Week 4 schedule

---

#### 2.3 TIER 3 - Low Priority (3 months or DELETE) 🗑️
**Priority: P2 - Consider Deletion**

**Decision Rule:** If not implemented within 3 months → **DELETE THE TEST**

**Candidates for Deletion (180 tests):**
- Analytics queries: `POST /api/v1/analytics/query`
- Report generation: `POST /api/v1/reports/generate`
- Dashboard stats: `POST /api/v1/dashboard/stats`

**Alternative: Convert to Documentation Tests**
```python
def test_analytics_query_endpoint_exists():
    """Verify endpoint exists and requires auth (no validation test)"""
    response = api_client.post('/api/v1/analytics/query')
    assert response.status_code == 401  # Not 404 - endpoint exists
```

---

## CI Enforcement Rules

### 1. **New Test Requirements**

All new POST/PATCH/PUT smoke tests MUST include:
- ✅ Domain-specific invalid payloads (not empty `{}`)
- ✅ At least 3 test cases:
  1. Missing required field
  2. Type mismatch
  3. Business rule violation
- ✅ Specific error message validation (not just status code)

**Example:**
```python
# ❌ REJECTED IN CODE REVIEW
def test_new_endpoint_input_validation():
    payload = {}  # Empty payload - NO COVERAGE
    assert response.status_code in [400, 422]

# ✅ APPROVED
def test_new_endpoint_input_validation():
    payload = {"field": -1}  # Domain-specific invalid value
    response = api_client.post('/api/v1/new-endpoint', json=payload)
    assert response.status_code == 422
    assert "field must be positive" in response.json()["detail"]
```

---

### 2. **Skip Reason Validation**

CI pipeline validates skip reasons using regex:

```python
# .github/workflows/validate-skips.yml
ALLOWED_SKIP_PATTERNS = [
    r"GET endpoints don't have request body",
    r"DELETE endpoints don't have request body",
    r"POST /logout doesn't require request body",
    r"bulk operation - doesn't require request body",
    r"toggle operation",
    r"idempotent verification",
    r"PHASE \d+ P\d+ BACKLOG.*TICKET-SMOKE-\d{3}",  # NEW: P2 backlog with ticket ID
]

FORBIDDEN_SKIP_PATTERNS = [
    r"Input validation requires domain-specific payloads",  # Temporary only - must fix
    r"Feature not implemented",  # Generic - must reference backlog ticket
    r"TODO",  # Vague - must have concrete backlog ticket
]
```

**CI Failure Triggers:**
- New test added with forbidden skip reason
- New skip without backlog ticket reference (e.g., `TICKET-SMOKE-XXX`)
- Existing TIER 1 test still skipped after 2-week deadline
- Existing TIER 2 test still skipped after 1-month deadline

**NEW RULE (Effective 2026-03-01):**
All new `@pytest.mark.skip` decorators for missing features MUST include:
1. Priority tier (e.g., `PHASE 3 P2 BACKLOG`)
2. Backlog ticket ID (e.g., `TICKET-SMOKE-001`)
3. Feature description and re-enable condition

**Valid Example:**
```python
@pytest.mark.skip(
    reason=(
        "PHASE 3 P2 BACKLOG (TICKET-SMOKE-001): Endpoint not implemented - "
        "PATCH /api/v1/instructor-assignments/requests/{request_id}/cancel returns 404. "
        "Re-enable when assignment cancellation feature is implemented."
    )
)
```

**Invalid Example (CI REJECTS):**
```python
@pytest.mark.skip(reason="Feature not implemented")  # NO TICKET ID - REJECTED
@pytest.mark.skip(reason="TODO: implement this")     # VAGUE - REJECTED
```

---

### 3. **Metrics Tracking**

CI reports skip metrics in baseline summary:

```markdown
## Smoke Test Skip Metrics

| Category | Count | Target | Status |
|----------|-------|--------|--------|
| Valid Skips (GET/DELETE/Implicit) | 115 | 115 | ✅ Stable |
| TIER 1 (Critical - 2 weeks) | 0 | 0 | ✅ Complete |
| TIER 2 (Medium - 1 month) | 15 | 0 | ⚠️ In Progress |
| TIER 3 (Delete candidates) | 180 | 0 | ⏳ Review Pending |

**Total Skipped:** 310 / 427 (27% reduction achieved)
```

---

## Skip Reason Templates

### For Valid Architectural Skips
```python
@pytest.mark.skip(reason="GET endpoints don't have request body - cannot validate input")
@pytest.mark.skip(reason="DELETE endpoints don't have request body - cannot validate input")
@pytest.mark.skip(reason="POST /logout doesn't require request body - endpoint design is correct")
@pytest.mark.skip(reason="POST /admin/sync/all is bulk operation - doesn't require request body")
@pytest.mark.skip(reason="POST /{id}/toggle-active doesn't require request body - toggle operation")
@pytest.mark.skip(reason="POST /{id}/verify-payment doesn't require request body - verification is implicit")
```

### For Temporary Coverage Gaps (NOT ALLOWED for new tests)
```python
# ⚠️ LEGACY ONLY - Grandfather clause for existing tests
# New tests CANNOT use this reason
@pytest.mark.skip(reason="Input validation requires domain-specific payloads")
```

---

## Enforcement Timeline

| Date | Milestone | Action |
|------|-----------|--------|
| 2026-03-01 | Baseline | 427 skipped tests documented |
| 2026-03-15 | TIER 1 Deadline | All 50 TIER 1 tests must have domain payloads |
| 2026-04-01 | TIER 2 Deadline | All 80 TIER 2 tests must have domain payloads |
| 2026-06-01 | TIER 3 Decision | Delete or convert 180 TIER 3 tests |

**Goal:** 427 skipped → ~115 skipped (valid architectural skips only)

---

## Approval Process

### Adding New Valid Skip
1. Create PR with test + skip reason
2. Justification MUST reference this policy (Category 1.1, 1.2, or 1.3)
3. Code review by 2+ engineers
4. Approved if matches valid categories

### Temporary Skip (Emergency Only)
1. Critical bug needs immediate fix
2. Temporary skip allowed for MAX 1 sprint (2 weeks)
3. JIRA ticket auto-created: "Unskip {test_name} with domain payloads"
4. Ticket assigned to test author
5. CI warning added: "Temporary skip expires {date}"

---

## References

- **Implementation Guide:** [TEST_SKIP_DECISION_MATRIX.md](../docs/TEST_SKIP_DECISION_MATRIX.md)
- **Baseline Report:** [.github/workflows/test-baseline-check.yml](.github/workflows/test-baseline-check.yml)
- **Smoke Test Generator:** [tools/generate_api_tests.py](../tools/generate_api_tests.py)

---

**Last Updated:** 2026-03-01
**Policy Version:** 1.0
**Next Review:** 2026-04-01
