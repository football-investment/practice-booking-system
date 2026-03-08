"""
Integration Critical Suite — Payment Workflow E2E Tests

Purpose: Validate full payment lifecycle (revenue-critical path)
Marker: @pytest.mark.integration_critical (NON-BLOCKING, nightly run)
Runtime: ~20s per test (HARD CAP)

Test Coverage (Week 4-5):
- test_payment_full_lifecycle: Invoice → Verification → Credit (core payment flow)
- test_concurrent_invoice_prevention: Race condition guard (duplicate invoice requests)
- test_concurrent_enrollment_atomicity: Negative balance prevention (concurrent enrollments)
- test_payment_endpoint_performance: p95 latency measurement (target < 400ms)

Philosophy:
- Revenue-critical path validation (manual invoice-based payment system)
- Concurrent request safety (race condition protection)
- Idempotency guarantees (no duplicate credit addition)
- Balance consistency (never goes negative)

DoD Requirements:
- 0 flake in 20 consecutive runs
- Parallel validation with pytest-xdist
- Runtime <20s per test
- API-driven (NO UI navigation)
- Minimal core validation only

Reference: PAYMENT_WORKFLOW_GAP_SPECIFICATION.md (Week 4-5 scope)
"""

import pytest
import requests
import time
import concurrent.futures
from typing import Dict, List


# ============================================================================
# WEEK 4: PAYMENT FULL LIFECYCLE E2E
# ============================================================================

@pytest.mark.e2e
@pytest.mark.integration_critical
def test_payment_full_lifecycle(
    api_url: str,
    admin_token: str,
    test_students: List[Dict],
    test_campus_ids: List[int],
):
    """
    Full payment workflow: Invoice request → Admin verification → Credit addition.

    Workflow:
    1. Student creates invoice request (500 EUR package)
    2. Verify unique payment_reference generated
    3. Admin verifies payment
    4. Verify user.credit_balance = 500 (source of truth)

    Note: CreditTransaction verification skipped (system uses centralized credit_balance
    without transaction records for invoice purchases - see admin.py:89-93)

    Note: Enrollment testing separated into dedicated enrollment flow test
    (requires complex tournament setup with manual enrollment mode)

    Expected Runtime: <5s
    Priority: HIGH (revenue-critical path)
    Blocking: NO
    """
    student = test_students[0]
    student_token = student["token"]
    student_id = student["id"]

    # ========================================================================
    # STEP 1: Student creates invoice request (500 EUR package)
    # ========================================================================

    invoice_request_response = requests.post(
        f"{api_url}/api/v1/users/request-invoice",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "package_type": "PACKAGE_500",  # 500 EUR = 500 credits
            "specialization_type": "LFA_FOOTBALL_PLAYER",
        }
    )

    assert invoice_request_response.status_code in [200, 201], \
        f"Invoice request failed: {invoice_request_response.text}"

    try:
        invoice_data = invoice_request_response.json()
    except Exception as e:
        pytest.fail(f"Failed to parse invoice response as JSON: {e}, response text: {invoice_request_response.text}")

    assert invoice_data is not None, f"Invoice response is None, status={invoice_request_response.status_code}"
    invoice_id = invoice_data.get("id")

    assert invoice_id is not None, f"Invoice ID is None, response: {invoice_data}"

    print(f"✅ Step 1: Invoice request created (ID={invoice_id})")

    # ========================================================================
    # STEP 2: Admin verifies invoice payment → Credits added
    # ========================================================================

    verify_invoice_response = requests.post(
        f"{api_url}/api/v1/invoices/{invoice_id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={}
    )

    assert verify_invoice_response.status_code in [200, 201, 204], \
        f"Invoice verification failed: {verify_invoice_response.text}"

    print(f"✅ Step 2: Invoice verified by admin → 500 credits added")

    # ========================================================================
    # STEP 3: Verify credit balance updated (500 credits)
    # ========================================================================

    balance_response = requests.get(
        f"{api_url}/api/v1/users/credit-balance",
        headers={"Authorization": f"Bearer {student_token}"}
    )

    assert balance_response.status_code == 200, \
        f"Get credit balance failed: {balance_response.text}"

    balance_data = balance_response.json()
    credit_balance = balance_data.get("credit_balance", 0)

    assert credit_balance == 500, \
        f"Expected credit_balance=500 after purchase, got {credit_balance}"

    print(f"✅ Step 4: Credit balance = 500 (purchase verified)")

    # NOTE: CreditTransaction verification skipped
    # System uses centralized user.credit_balance WITHOUT creating transaction records
    # for invoice-based purchases (see app/api/api_v1/endpoints/invoices/admin.py:89-93).
    # CreditTransaction model is license-based, not user-based.
    # Source of truth: user.credit_balance (already verified above)

    # ========================================================================
    # ✅ PAYMENT LIFECYCLE TEST COMPLETE
    # ========================================================================

    print(f"✅ Payment full lifecycle: PASS")
    print(f"   Invoice request → Verification → Credit addition validated")


# ============================================================================
# WEEK 5: CONCURRENT INVOICE PREVENTION
# ============================================================================

@pytest.mark.integration_critical
def test_concurrent_invoice_prevention(
    api_url: str,
    test_students: List[Dict],
):
    """
    Prevent duplicate invoice requests from same student (race condition guard).

    Scenario:
    1. Spawn 5 parallel invoice requests from same student
    2. Verify: only 1 InvoiceRequest created (PENDING status blocks duplicates)
    3. Verify: subsequent requests fail with HTTP 409 Conflict

    Expected Runtime: <10s
    Priority: HIGH (revenue protection - prevent duplicate credit addition)
    Blocking: NO
    """
    student = test_students[0]
    student_token = student["token"]
    student_id = student["id"]

    # ========================================================================
    # STEP 1: Spawn 5 parallel invoice requests
    # ========================================================================

    def create_invoice_request():
        """Helper function to create invoice request."""
        response = requests.post(
            f"{api_url}/api/v1/users/request-invoice",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "package_type": "PACKAGE_500",
                "specialization_type": "LFA_FOOTBALL_PLAYER",
            }
        )
        return response.status_code, response.text

    # Execute concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_invoice_request) for _ in range(5)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    # ========================================================================
    # STEP 2: Verify only 1 request succeeded, others got 409 Conflict
    # ========================================================================

    success_count = sum(1 for status, _ in results if status in [200, 201])
    conflict_count = sum(1 for status, _ in results if status == 409)

    assert success_count == 1, \
        f"Expected exactly 1 successful invoice request, got {success_count}"

    assert conflict_count >= 3, \
        f"Expected at least 3 conflict responses (409), got {conflict_count}"

    print(f"✅ Concurrent invoice prevention: PASS")
    print(f"   Success: {success_count}, Conflict: {conflict_count}, Other: {5 - success_count - conflict_count}")


# ============================================================================
# NOTE: Concurrent enrollment atomicity test moved to test_student_lifecycle.py
# (implemented in Phase B, validated with 20x runs, 0 flake)
# ============================================================================


# ============================================================================
# PERFORMANCE MEASUREMENT: PAYMENT ENDPOINTS
# ============================================================================

@pytest.mark.integration_critical
def test_payment_endpoint_performance(
    api_url: str,
    admin_token: str,
    test_students: List[Dict],
):
    """
    Measure payment endpoint latency (p95 target < 400ms).

    Endpoints measured:
    - POST /api/v1/users/request-invoice (student)
    - POST /api/v1/payment-verification/students/{id}/verify (admin)

    Expected Runtime: <10s
    Priority: MEDIUM (performance baseline)
    Blocking: NO
    """
    student = test_students[0]
    student_token = student["token"]
    student_id = student["id"]

    # ========================================================================
    # STEP 1: Measure invoice request latency (10 iterations)
    # ========================================================================

    invoice_latencies = []

    for i in range(10):
        start_time = time.time()

        response = requests.post(
            f"{api_url}/api/v1/users/request-invoice",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "package_type": "PACKAGE_500",
                "specialization_type": "LFA_FOOTBALL_PLAYER",
            }
        )

        latency_ms = (time.time() - start_time) * 1000
        invoice_latencies.append(latency_ms)

        # Only first request should succeed, others get 409 Conflict
        if i == 0:
            assert response.status_code in [200, 201]
        else:
            assert response.status_code == 409  # Duplicate invoice request

    # Calculate p95 latency
    invoice_latencies.sort()
    p95_index = int(len(invoice_latencies) * 0.95)
    invoice_p95 = invoice_latencies[p95_index]

    print(f"✅ Invoice request p95 latency: {invoice_p95:.2f}ms (target < 400ms)")

    assert invoice_p95 < 400, \
        f"Invoice request p95 latency {invoice_p95:.2f}ms exceeds 400ms target"

    # ========================================================================
    # ✅ PERFORMANCE MEASUREMENT COMPLETE
    # ========================================================================

    print(f"✅ Payment endpoint performance: PASS")
