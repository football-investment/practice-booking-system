# Coverage Baseline — Sprint 36
**Frozen: 2026-03-08 | Tag: `v0.36.1-baseline` | Commit: `77c5744`**

---

## Baseline Numbers

| Metric | Value | Delta vs Sprint 35 | CI threshold |
|--------|-------|--------------------|--------------|
| **Statement coverage** | **87.6%** | +0.6pp | ≥ 75% ✅ |
| **Branch coverage (pure)** | **78.3%** | +1.3pp | ≥ 78% ✅ (target MET) |
| Combined (stmt+branch) | 86% | +0.3pp | ≥ 75% ✅ |
| Total statements | 31 482 | — | — |
| Total branches | 8 294 | — | — |
| BrPart (partially hit) | 554 | — | — |

**CI run confirming baseline:** `22811568540` (PR #10, branch `feature/api-tests-stabilization`)

---

## Test Suite Numbers

| Suite | Passed | Failed | Skipped | Xfailed |
|-------|--------|--------|---------|---------|
| Unit + tournament integration | 6 059 | 0 | 0 | 1 |
| API smoke (integration) | 1 654 | 0 | 1 | — |
| Cypress E2E (CI gate, 7 specs) | 7/7 ✅ | 0 | — | — |
| Playwright integration_critical | BLOCKING | — | — | — |

The 1 xfail is `test_b02_race_window_produces_overbooking_documents_the_unsafe_state` — documented intentional: mock DB cannot simulate `SELECT FOR UPDATE` serialisation; real-DB concurrency proof deferred to future `tests/database/` suite.

---

## Sprint 36 — What Moved the Needle

| File | Tests added | Branch before → after |
|------|------------|----------------------|
| `endpoints/students.py` | 17 | 45% → 100% |
| `endpoints/analytics.py` | 18 | 56% → 97% |
| `endpoints/bookings/student.py` | 30 | 38% → 100% |
| `services/quiz_service.py` | 17 | +17 branch tests |
| `services/adaptive_learning_service.py` | 18 | +18 branch tests |
| `services/enrollment_conflict_service.py` | 3 | +3 branch tests |
| **Total** | **103** | **77.0% → 78.3%** |

---

## Regression Detection

To verify the baseline is maintained:

```bash
# Full CI scope (mirrors GitHub Actions step 1+2)
pytest tests/unit/ tests/integration/tournament/ tests/integration/api_smoke/ \
  --cov=app --cov-branch --cov-report=xml -q

# Check coverage
python -m coverage report --show-missing --fail-under=75
python .github/scripts/check_coverage.py
```

**Alert condition:** If `pure-branch` drops below **78.3%**, a regression has occurred. Investigate the delta with:

```bash
python -m coverage report --show-missing | grep -E "^\s*(TOTAL|.*\d+%)" | sort -k5 -n
```

---

## Known Quality Gaps (next sprint targets)

### 1. Hollow API Smoke Payloads — 257 instances across 66 files

POST/PATCH endpoints called with `json={}` → 422 Unprocessable Entity.
These tests prove the endpoint *exists* but do not validate business logic.

**Top files by hollow payload count:**

| File | Count | Priority endpoints |
|------|-------|--------------------|
| `test_tournaments_smoke.py` | 37 | create-tournament, enroll, confirm |
| `test_licenses_smoke.py` | 11 | activate, advance, renew |
| `test_instructor_management_smoke.py` | 11 | apply, approve, assign |
| `test_semester_enrollments_smoke.py` | 9 | enroll, approve, reject |
| `test_projects_smoke.py` | 9 | submit, grade, assess |
| `test_auth_smoke.py` | 8 | register, login |
| `test_sessions_smoke.py` | 7 | create, update |
| `test_instructor_smoke.py` | 7 | create-availability, accept |
| `test_attendance_smoke.py` | 6 | mark-present, mark-absent |
| `test_coupons_smoke.py` | 6 | create, apply, redeem |

**Action:** Enrich the top 5 files with realistic payloads using `conftest.py` fixture IDs.
Expected impact: validates business rules in smoke, catches 422→200 regressions.

### 2. Unit Test Skips — 0 systematic skips ✅

Local run: `6059 passed, 1 xfailed, 0 skipped`.
The only `pytest.skip()` call is a legitimate conditional in `test_skill_weight_pipeline.py:616`
(fires when delta rounds to zero at clamp boundary — ratio undefined).
**No action required.**

### 3. E2E Critical Business Flow Gaps

**Currently covered** (`tests/e2e/integration_critical/` — BLOCKING CI gate):

| Test | Flow covered |
|------|-------------|
| `test_student_lifecycle.py` | Enrollment → credit deduction → session visibility |
| `test_instructor_lifecycle.py` | Application → assignment → session check-in |
| `test_multi_role_integration.py` | Student + instructor parallel workflow |
| `test_multi_campus.py` | Cross-campus enrollment isolation |
| `test_payment_workflow.py` | Invoice → credit top-up → deduction |
| `test_refund_workflow.py` | Cancellation → refund → balance restore |
| `test_skill_assessment_lifecycle.py` | Skill upload → assessment → license advance |

**Missing flows (not covered by any BLOCKING test):**

| Gap | Risk | Recommended test location |
|-----|------|--------------------------|
| Booking lifecycle (create → confirm → cancel → auto-promote) | HIGH — core revenue flow | `integration_critical/test_booking_lifecycle.py` |
| Waitlist promotion after cancellation | HIGH — correctness | same as above |
| Concurrent booking capacity guard (two students, one slot) | HIGH — data integrity | `integration_critical/test_booking_lifecycle.py` |
| Quiz attempt → project enrollment → grade → license progression | MEDIUM | `integration_critical/test_quiz_to_license.py` |
| Coupon redemption → discounted booking | MEDIUM | `integration_critical/test_coupon_flow.py` |

**Cypress coverage (7/7 green):** `booking_lifecycle.cy.js` and `enrollment_flow.cy.js` cover UI-layer booking/enrollment, but these are not in the BLOCKING Python API gate.

---

## Next Sprint Recommendation (priority order)

1. **Hollow smoke payloads** — enrich `test_tournaments_smoke.py` (37 hollows) and `test_auth_smoke.py` (8 hollows) first; highest ROI per file.
2. **Booking lifecycle integration_critical** — add `test_booking_lifecycle.py` to the BLOCKING Python E2E gate; covers auto-promote and capacity guard.
3. **Quiz→license flow** — add `test_quiz_to_license.py` to `integration_critical/`; completes the learning progression chain.
4. **Branch coverage buffer** — current margin is +0.3pp above target. Consider adding 5–10 branch tests to `services/skill_progression_service.py` (14 miss, 91.5%) as a safety buffer.

---

*Generated by Claude Code · Sprint 36 · 2026-03-08*
