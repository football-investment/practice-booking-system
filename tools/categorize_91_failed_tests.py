#!/usr/bin/env python3
"""
Categorize 91 Failed Tests - Full Breakdown

Categories:
1. MISSING_ENDPOINT - 404, endpoint needs implementation
2. ROUTING_MISMATCH - 404, endpoint exists but path wrong
3. AUTH_PERMISSION - 403, permission issue
4. VALIDATION_INCONSISTENCY - 200, empty body accepted (should be 422)
5. INLINE_SCHEMA_BUG - Known bugs (documented)
6. OTHER - Uncategorized

Usage:
    python tools/categorize_91_failed_tests.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def get_openapi_endpoints() -> set:
    """Get all endpoints from OpenAPI schema."""
    schema = app.openapi()
    endpoints = set()

    for path, methods_dict in schema['paths'].items():
        for method in methods_dict.keys():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                endpoints.add((method.upper(), path))

    return endpoints


def parse_failed_tests(file_path: str) -> List[Dict]:
    """Parse failed tests from file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    failed_tests = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract test file and name
        match = re.match(r'(tests/integration/api_smoke/test_(\w+)_smoke\.py)::Test\w+::(test_\w+)', line)
        if not match:
            continue

        test_file = match.group(1)
        domain = match.group(2)
        test_name = match.group(3)

        # Extract HTTP method and endpoint
        endpoint_match = re.search(r'(GET|POST|PUT|PATCH|DELETE) (/[^ ]+)', line)
        if not endpoint_match:
            continue

        method = endpoint_match.group(1)
        endpoint = endpoint_match.group(2)

        # Extract status code
        status_match = re.search(r'should validate input: (\d{3})', line)
        if not status_match:
            continue

        status_code = int(status_match.group(1))

        failed_tests.append({
            'file': test_file,
            'domain': domain,
            'test_name': test_name,
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'raw': line
        })

    return failed_tests


def categorize_test(test: Dict, openapi_endpoints: set) -> Tuple[str, str]:
    """
    Categorize a failed test.

    Returns:
        (category, reason) tuple
    """
    method = test['method']
    endpoint = test['endpoint']
    status = test['status_code']

    # Known inline schema bugs
    INLINE_SCHEMA_BUGS = [
        ('POST', '/api/v1/debug/log-error'),
        ('POST', '/api/v1/licenses/admin/sync/all'),
        ('POST', '/api/v1/licenses/instructor/advance'),
    ]

    if (method, endpoint) in INLINE_SCHEMA_BUGS:
        return ("INLINE_SCHEMA_BUG", "Known bug - empty schema properties (documented)")

    # 200 OK on input_validation test = validation inconsistency
    if status == 200:
        if (method, endpoint) in openapi_endpoints:
            return ("VALIDATION_INCONSISTENCY", "Endpoint accepts empty body (should return 422)")
        else:
            return ("OTHER", "200 but endpoint not in OpenAPI")

    # 403 Forbidden = auth/permission issue
    if status == 403:
        if (method, endpoint) in openapi_endpoints:
            return ("AUTH_PERMISSION", "Permission denied - role/ownership check")
        else:
            return ("AUTH_PERMISSION", "403 on non-existent endpoint (auth before routing?)")

    # 404 Not Found
    if status == 404:
        # Check if endpoint exists in OpenAPI
        if (method, endpoint) in openapi_endpoints:
            return ("ROUTING_MISMATCH", "Endpoint in OpenAPI but returns 404 (routing issue)")

        # Check for known patterns
        # Pattern: /api/v1/{id}/action (missing /api/v1/resource/{id}/action)
        if re.match(r'/api/v1/\d+/', endpoint):
            return ("ROUTING_MISMATCH", "Path likely missing resource name (e.g., /sessions/{id})")

        # Otherwise, missing endpoint
        return ("MISSING_ENDPOINT", "Endpoint not in OpenAPI - needs implementation")

    # Other status codes
    return ("OTHER", f"Unexpected status {status}")


def main():
    """Categorize all 91 failed tests."""
    print("🔍 Categorizing 91 Failed Tests...\n")

    # Load OpenAPI endpoints
    print("Loading OpenAPI schema...")
    openapi_endpoints = get_openapi_endpoints()
    print(f"✅ Found {len(openapi_endpoints)} endpoints in OpenAPI\n")

    # Parse failed tests
    failed_tests_file = "/tmp/failed_tests_91.txt"
    failed_tests = parse_failed_tests(failed_tests_file)

    if not failed_tests:
        print("⚠️  No failed tests parsed")
        return 1

    print(f"Found {len(failed_tests)} failed tests\n")

    # Categorize
    categories = defaultdict(list)

    for test in failed_tests:
        category, reason = categorize_test(test, openapi_endpoints)
        categories[category].append({
            **test,
            'reason': reason
        })

    # Generate report
    print("=" * 80)
    print("91 FAILED TESTS - FULL CATEGORIZATION")
    print("=" * 80)

    for category in ['MISSING_ENDPOINT', 'ROUTING_MISMATCH', 'AUTH_PERMISSION',
                     'VALIDATION_INCONSISTENCY', 'INLINE_SCHEMA_BUG', 'OTHER']:
        tests = categories[category]
        if not tests:
            continue

        print(f"\n📋 {category}: {len(tests)} tests")
        print("-" * 80)

        # Group by endpoint
        by_endpoint = defaultdict(list)
        for test in tests:
            key = (test['method'], test['endpoint'])
            by_endpoint[key].append(test)

        for (method, endpoint), test_group in sorted(by_endpoint.items()):
            print(f"\n  {method:6} {endpoint}")
            print(f"  Status: {test_group[0]['status_code']}")
            print(f"  Reason: {test_group[0]['reason']}")
            print(f"  Tests ({len(test_group)}):")
            for test in test_group:
                file_name = Path(test['file']).name
                print(f"    - {file_name}::{test['test_name']}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for category in ['MISSING_ENDPOINT', 'ROUTING_MISMATCH', 'AUTH_PERMISSION',
                     'VALIDATION_INCONSISTENCY', 'INLINE_SCHEMA_BUG', 'OTHER']:
        count = len(categories[category])
        if count > 0:
            print(f"  {category:30} {count:3} tests")
    print("=" * 80)

    print("\n" + "=" * 80)
    print("BY STATUS CODE")
    print("=" * 80)
    status_counts = defaultdict(int)
    for test in failed_tests:
        status_counts[test['status_code']] += 1

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count:3} tests")
    print("=" * 80)


if __name__ == "__main__":
    exit(main())
