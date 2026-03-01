# Test Skip Decision Matrix
**Created:** 2026-03-01
**Purpose:** Definitive guide for which skipped tests should be unskipped with domain payloads

---

## TIER 1: CRITICAL - MUST UNSKIP (2 weeks) ⚠️

**Total:** ~50 tests
**Risk:** Business-critical, security, financial integrity

### 1.1 Financial Operations (Priority: P0)
| Endpoint | Test Count | Domain Payload Required | Business Risk |
|----------|-----------|-------------------------|---------------|
| POST /api/v1/invoices/request | 1 | Negative amounts, missing fields | Revenue loss, fraud |
| POST /api/v1/coupons/apply | 1 | Invalid codes, expired coupons | Discount abuse |
| PATCH /api/v1/invoices/{id} | 1 | Amount tampering, status bypass | Financial integrity |

**Domain Payloads:**
```python
# Negative amount
{"amount": -100, "description": "Test", "user_id": 1}

# Missing required fields
{"amount": 100}  # No description, user_id

# Type mismatch
{"amount": "not_a_number", "description": None}
```

---

### 1.2 Authentication & Authorization (Priority: P0)
| Endpoint | Test Count | Domain Payload Required | Business Risk |
|----------|-----------|-------------------------|---------------|
| POST /api/v1/auth/register | 1 | Invalid email, weak password, role escalation | Security breach |
| POST /api/v1/auth/login | 1 | SQL injection, brute force patterns | Unauthorized access |
| PATCH /api/v1/users/{id}/role | 1 | Privilege escalation (STUDENT→ADMIN) | Authorization bypass |

**Domain Payloads:**
```python
# Privilege escalation attempt
{"role": "ADMIN", "email": "student@test.com"}

# Weak password
{"email": "test@test.com", "password": "123"}

# Invalid email format
{"email": "not-an-email", "password": "ValidPass123!"}
```

---

### 1.3 Tournament/Session State Machine (Priority: P0)
| Endpoint | Test Count | Domain Payload Required | Business Risk |
|----------|-----------|-------------------------|---------------|
| POST /api/v1/tournaments | 1 | Past dates, invalid capacity | Data inconsistency |
| POST /api/v1/tournaments/{id}/enroll | 1 | Concurrent enrollment, insufficient credits | Race condition, balance corruption |
| POST /api/v1/sessions/{id}/results | 1 | Invalid scores, wrong status | Ranking corruption |

**Domain Payloads:**
```python
# Temporal inconsistency
{"start_date": "2020-01-01", "end_date": "2019-12-31"}

# Invalid capacity
{"max_players": -5, "tournament_type": "INVALID_ENUM"}

# Concurrent enrollment (test with threading)
# Student with 500 credits enrolls in 3x 250-credit tournaments simultaneously
```

---

## TIER 2: MEDIUM - SHOULD UNSKIP (1 month) ⏳

**Total:** ~80 tests
**Risk:** UX degradation, data quality issues

### 2.1 Profile & Settings
| Endpoint | Test Count | Domain Payload Required | Business Risk |
|----------|-----------|-------------------------|---------------|
| PATCH /api/v1/users/{id}/profile | 1 | XSS in bio, invalid phone format | UX issues, minor security |
| POST /api/v1/settings/preferences | 1 | Invalid notification settings | User experience |

---

## TIER 3: LOW - DELETE OR KEEP SKIPPED 🗑️

**Total:** ~180 tests
**Decision:** If not implemented in 3 months → DELETE

### 3.1 Analytics & Reports (Consider Deletion)
| Endpoint | Test Count | Justification for Deletion |
|----------|-----------|---------------------------|
| POST /api/v1/analytics/query | 1 | Complex domain logic, low value smoke test |
| POST /api/v1/reports/generate | 1 | External service dependency, flaky |

**Alternative:** Convert to lightweight "endpoint exists" tests:
```python
def test_analytics_query_endpoint_exists():
    """Verify endpoint exists and requires auth"""
    response = api_client.post('/api/v1/analytics/query')
    assert response.status_code == 401  # Not 404
```

---

## VALID SKIPS - KEEP AS-IS ✅

**Total:** ~115 tests
**Justification:** Architecturally correct

### GET/DELETE Endpoints (~109 tests)
**Reason:** No request body → cannot validate input
```python
@pytest.mark.skip(reason="GET endpoints don't have request body validation")
def test_get_users_input_validation():
    # Architecturally impossible to test
    pass
```

### Bulk/Toggle Operations (6 tests)
**Reason:** Implicit operations, no payload required
```python
@pytest.mark.skip(reason="POST /logout doesn't require request body")
def test_logout_input_validation():
    # Correct design - session invalidation is implicit
    pass
```

---

## IMPLEMENTATION SCHEDULE

### Week 1: Financial Operations
- [ ] Invoice request validation (negative amounts, type errors)
- [ ] Coupon application validation (expired, invalid codes)
- [ ] Payment verification validation

### Week 2: Auth & Authorization
- [ ] Registration validation (weak password, invalid email)
- [ ] Login validation (SQL injection patterns)
- [ ] Role modification validation (privilege escalation)

### Week 3: Tournament State Machine
- [ ] Tournament creation validation (temporal consistency)
- [ ] Enrollment validation (concurrent enrollment atomicity)
- [ ] Session result validation (score boundaries)

### Week 4: Profile & Settings
- [ ] Profile update validation (XSS prevention)
- [ ] Settings validation (notification preferences)

---

## DELETION CANDIDATES (Review after Week 4)

If these are still skipped after 1 month → DELETE:
- `test_analytics_query_input_validation`
- `test_reports_generate_input_validation`
- `test_dashboard_stats_input_validation`
- All "POST /admin/sync/*" bulk operations

**Rationale:** If we haven't prioritized them in 1 month, they're not critical.

---

## METRICS TRACKING

| Week | Target Skipped | Actual Skipped | TIER 1 Complete | TIER 2 Complete |
|------|---------------|----------------|-----------------|-----------------|
| 0 (Baseline) | 427 | 427 | 0% | 0% |
| 1 | 410 | TBD | 20% | 0% |
| 2 | 395 | TBD | 60% | 0% |
| 3 | 380 | TBD | 100% | 20% |
| 4 | 300 | TBD | 100% | 100% |

**Goal:** 427 → ~300 skipped (valid architectural skips + TIER 3 deletions)
