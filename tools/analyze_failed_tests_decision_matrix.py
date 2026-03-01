#!/usr/bin/env python3
"""
Analyze 96 Failed Tests - Decision Matrix Generator

Purpose: Create endpoint-level categorization with implementation decisions
Categories:
1. IMPLEMENT - Endpoint should exist, needs implementation
2. REMOVE_TEST - Endpoint shouldn't exist, remove test
3. FIX_TEST - Test has bugs (wrong URL, auth, etc.)

Usage:
    python tools/analyze_failed_tests_decision_matrix.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def get_openapi_endpoints() -> Set[Tuple[str, str]]:
    """Get all endpoints from OpenAPI schema."""
    schema = app.openapi()
    endpoints = set()

    for path, methods_dict in schema['paths'].items():
        for method in methods_dict.keys():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                endpoints.add((method.upper(), path))

    return endpoints


def extract_failed_test_info(test_output_file: Path) -> List[Tuple[str, str, str, str]]:
    """
    Extract endpoint info from failed tests.

    Returns:
        List of (test_file, test_name, method, endpoint) tuples
    """
    failed_tests = []

    if not test_output_file.exists():
        print(f"⚠️  Test output file not found: {test_output_file}")
        return []

    content = test_output_file.read_text()

    # Pattern: tests/integration/api_smoke/test_FILE.py::TestCLASS::test_NAME
    for line in content.split('\n'):
        if not line.startswith('tests/integration/api_smoke/'):
            continue

        # Parse test path
        match = re.match(r'(tests/integration/api_smoke/test_(\w+)_smoke\.py)::Test\w+::(test_\w+)', line)
        if not match:
            continue

        test_file = match.group(1)
        domain = match.group(2)
        test_name = match.group(3)

        # Try to extract HTTP method and endpoint from test file
        test_path = Path(test_file)
        if test_path.exists():
            test_content = test_path.read_text()

            # Find the test function
            func_pattern = rf'def {test_name}\s*\([^)]*\):.*?(?=\n    def |\Z)'
            func_match = re.search(func_pattern, test_content, re.DOTALL)

            if func_match:
                func_body = func_match.group(0)

                # Extract HTTP method call
                method_match = re.search(r'api_client\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]', func_body)
                if method_match:
                    method = method_match.group(1).upper()
                    endpoint = method_match.group(2)

                    # Clean up f-string variables
                    endpoint = re.sub(r'\{test_\w+\}', '{id}', endpoint)
                    endpoint = re.sub(r'\{test_tournament\["[^"]+"\]\[0\]\}', '{id}', endpoint)
                    endpoint = re.sub(r'\{test_tournament\["[^"]+"\]\}', '{value}', endpoint)

                    failed_tests.append((test_file, test_name, method, endpoint))

    return failed_tests


def categorize_endpoint(method: str, endpoint: str, openapi_endpoints: Set[Tuple[str, str]]) -> Tuple[str, str]:
    """
    Categorize endpoint failure.

    Returns:
        (category, reason) tuple
    """
    # Check if endpoint exists in OpenAPI
    if (method, endpoint) in openapi_endpoints:
        return ("IMPLEMENT_OK", "Endpoint exists in OpenAPI - likely inline schema or empty body issue")

    # Known patterns that should NOT exist
    REMOVE_PATTERNS = [
        (r'/onboarding/set-birthdate$', "Legacy onboarding - deprecated"),
        (r'/specialization/select$', "Legacy specialization - deprecated"),
        (r'/profile/edit$', "Use PATCH /profile instead"),
        (r'/coupons/apply$', "Should be /coupons/{id}/apply"),
        (r'/log-error$', "Frontend logging - optional feature"),
        (r'/check-now$', "Admin utility - not core API"),
        (r'/check-expirations$', "Admin utility - not core API"),
    ]

    for pattern, reason in REMOVE_PATTERNS:
        if re.search(pattern, endpoint):
            return ("REMOVE_TEST", reason)

    # Check for empty body endpoints (no request validation)
    EMPTY_BODY_ENDPOINTS = [
        '/logout',
        '/mark-all-read',
        '/sync-all-users',
        '/calculate-rankings',
        '/finalize-group-stage',
        '/finalize-tournament',
    ]

    if any(endpoint.endswith(ep) for ep in EMPTY_BODY_ENDPOINTS):
        return ("FIX_TEST", "Empty body endpoint - remove input_validation test")

    # Default: needs implementation
    return ("IMPLEMENT", "Endpoint missing from API - needs implementation")


def generate_decision_matrix():
    """Generate comprehensive decision matrix for all failed tests."""

    print("🔍 Analyzing 96 failed tests...\n")

    # Get OpenAPI endpoints
    print("Loading OpenAPI schema...")
    openapi_endpoints = get_openapi_endpoints()
    print(f"✅ Found {len(openapi_endpoints)} endpoints in OpenAPI\n")

    # Load failed tests
    failed_tests_file = Path("/tmp/failed_tests_list.txt")
    failed_tests = extract_failed_test_info(failed_tests_file)

    if not failed_tests:
        print("⚠️  No failed tests found. Run pytest first to generate list.")
        return

    print(f"Found {len(failed_tests)} failed tests\n")

    # Categorize by endpoint
    endpoint_categories = defaultdict(list)

    for test_file, test_name, method, endpoint in failed_tests:
        category, reason = categorize_endpoint(method, endpoint, openapi_endpoints)
        endpoint_categories[category].append({
            'method': method,
            'endpoint': endpoint,
            'test_file': test_file,
            'test_name': test_name,
            'reason': reason
        })

    # Generate report
    print("=" * 80)
    print("DECISION MATRIX - 96 FAILED TESTS")
    print("=" * 80)

    for category in ['IMPLEMENT', 'REMOVE_TEST', 'FIX_TEST', 'IMPLEMENT_OK']:
        tests = endpoint_categories[category]
        if not tests:
            continue

        print(f"\n📋 Category: {category} ({len(tests)} tests)")
        print("-" * 80)

        # Group by endpoint
        by_endpoint = defaultdict(list)
        for test in tests:
            key = (test['method'], test['endpoint'])
            by_endpoint[key].append(test)

        for (method, endpoint), test_group in sorted(by_endpoint.items()):
            print(f"\n  {method:6} {endpoint}")
            print(f"  Reason: {test_group[0]['reason']}")
            print(f"  Tests ({len(test_group)}):")
            for test in test_group:
                file_name = Path(test['test_file']).name
                print(f"    - {file_name}::{test['test_name']}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for category in ['IMPLEMENT', 'REMOVE_TEST', 'FIX_TEST', 'IMPLEMENT_OK']:
        count = len(endpoint_categories[category])
        if count > 0:
            print(f"  {category:15} {count:3} tests")
    print("=" * 80)


if __name__ == "__main__":
    generate_decision_matrix()
