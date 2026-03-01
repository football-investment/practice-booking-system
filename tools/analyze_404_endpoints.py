#!/usr/bin/env python3
"""
Analyze 404 endpoint failures and categorize them

Purpose: Determine which endpoints should be implemented vs which tests should be removed

Categories:
1. IMPLEMENTED - Endpoint exists in OpenAPI spec (likely inline schema issue)
2. MISSING_IMPLEMENT - Should exist per API design, needs implementation
3. MISSING_REMOVE_TEST - Shouldn't exist, remove test

Usage:
    python tools/analyze_404_endpoints.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

def get_openapi_endpoints() -> Set[Tuple[str, str]]:
    """
    Get all endpoints from OpenAPI schema.

    Returns:
        Set of (method, path) tuples
    """
    schema = app.openapi()
    endpoints = set()

    for path, methods_dict in schema['paths'].items():
        for method in methods_dict.keys():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                # Normalize path for comparison
                # OpenAPI paths like /api/v1/foo/{bar_id} should match test paths
                endpoints.add((method.upper(), path))

    return endpoints


def extract_endpoint_from_test(test_file: Path) -> List[Tuple[str, str, str]]:
    """
    Extract endpoint information from test file.

    Returns:
        List of (method, path, test_name) tuples
    """
    content = test_file.read_text()
    endpoints = []

    # Pattern: def test_NAME_TYPE(...)
    # Where TYPE is: happy_path, auth_required, input_validation
    test_pattern = r'def (test_\w+(?:_happy_path|_auth_required|_input_validation))\s*\('
    # Pattern: HTTP method calls like api_client.post('/api/v1/...'
    method_pattern = r'api_client\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]'

    test_functions = re.finditer(test_pattern, content)

    for test_match in test_functions:
        test_name = test_match.group(1)
        # Find the method call within this test function
        # Extract code block for this function (until next 'def' or end of file)
        start_pos = test_match.end()
        next_def = content.find('\n    def ', start_pos)
        if next_def == -1:
            test_code = content[start_pos:]
        else:
            test_code = content[start_pos:next_def]

        # Find HTTP method calls in this test
        method_matches = re.finditer(method_pattern, test_code)
        for method_match in method_matches:
            method = method_match.group(1).upper()
            path = method_match.group(2)
            # Normalize path (remove variable interpolations like {test_tournament["session_ids"][0]})
            # Replace f-string variables with OpenAPI placeholders
            normalized_path = re.sub(r'\{test_tournament\["(\w+)"\]\[0\]\}', r'{\1}', path)
            normalized_path = re.sub(r'\{test_tournament\["(\w+)"\]\}', r'{\1}', normalized_path)
            normalized_path = re.sub(r'\{test_(\w+)\}', r'{\1}', normalized_path)

            endpoints.append((method, normalized_path, test_name))

    return endpoints


def categorize_endpoint(method: str, path: str, openapi_endpoints: Set[Tuple[str, str]]) -> str:
    """
    Categorize an endpoint that returns 404.

    Returns:
        Category string: IMPLEMENTED, MISSING_IMPLEMENT, or MISSING_REMOVE_TEST
    """
    # Check exact match
    if (method, path) in openapi_endpoints:
        return "IMPLEMENTED"

    # Known endpoints that should NOT exist (test artifacts, deprecated features)
    SHOULD_NOT_EXIST = [
        ('POST', '/api/v1/coupons/apply'),  # Should be /coupons/{id}/apply
        ('POST', '/api/v1/onboarding/set-birthdate'),  # Legacy onboarding
        ('POST', '/api/v1/specialization/select'),  # Legacy specialization
        ('POST', '/api/v1/profile/edit'),  # Should be PATCH /profile
        ('POST', '/api/v1/log-error'),  # Frontend error logging (optional)
        ('POST', '/api/v1/check-now'),  # Admin utility (optional)
        ('POST', '/api/v1/check-expirations'),  # Admin utility (optional)
    ]

    if (method, path) in SHOULD_NOT_EXIST:
        return "MISSING_REMOVE_TEST"

    # Default: endpoint should be implemented
    return "MISSING_IMPLEMENT"


def main():
    """Analyze 404 endpoint failures."""
    print("🔍 Analyzing 404 endpoint failures...\n")

    # Get OpenAPI endpoints
    print("Loading OpenAPI schema...")
    openapi_endpoints = get_openapi_endpoints()
    print(f"✅ Found {len(openapi_endpoints)} endpoints in OpenAPI schema\n")

    # Scan smoke test files
    test_dir = Path("tests/integration/api_smoke")
    test_files = list(test_dir.glob("test_*_smoke.py"))

    all_test_endpoints = []
    for test_file in test_files:
        endpoints = extract_endpoint_from_test(test_file)
        for method, path, test_name in endpoints:
            all_test_endpoints.append((method, path, test_name, test_file.name))

    print(f"Found {len(all_test_endpoints)} test endpoints\n")

    # Categorize all endpoints
    categories = {
        "IMPLEMENTED": [],
        "MISSING_IMPLEMENT": [],
        "MISSING_REMOVE_TEST": [],
    }

    for method, path, test_name, file_name in all_test_endpoints:
        category = categorize_endpoint(method, path, openapi_endpoints)
        categories[category].append((method, path, test_name, file_name))

    # Report
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n📊 Category 1: IMPLEMENTED ({len(categories['IMPLEMENTED'])} endpoints)")
    print("These endpoints exist in OpenAPI - likely inline schema issue")
    print("-" * 80)
    for method, path, test_name, file_name in sorted(categories['IMPLEMENTED'])[:10]:
        print(f"  {method:6} {path:50} ({file_name})")
    if len(categories['IMPLEMENTED']) > 10:
        print(f"  ... and {len(categories['IMPLEMENTED']) - 10} more")

    print(f"\n📋 Category 2: MISSING_IMPLEMENT ({len(categories['MISSING_IMPLEMENT'])} endpoints)")
    print("These should exist - need implementation")
    print("-" * 80)
    for method, path, test_name, file_name in sorted(categories['MISSING_IMPLEMENT']):
        print(f"  {method:6} {path:50} ({file_name})")

    print(f"\n❌ Category 3: MISSING_REMOVE_TEST ({len(categories['MISSING_REMOVE_TEST'])} endpoints)")
    print("These should NOT exist - remove tests")
    print("-" * 80)
    for method, path, test_name, file_name in sorted(categories['MISSING_REMOVE_TEST']):
        print(f"  {method:6} {path:50} ({file_name})")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Implemented (inline schema): {len(categories['IMPLEMENTED'])}")
    print(f"  Need implementation: {len(categories['MISSING_IMPLEMENT'])}")
    print(f"  Remove tests: {len(categories['MISSING_REMOVE_TEST'])}")
    print("=" * 80)


if __name__ == "__main__":
    main()
