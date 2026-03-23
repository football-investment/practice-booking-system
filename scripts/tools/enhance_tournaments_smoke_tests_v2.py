"""
Phase 1 Enhancement Tool v2: Transform tournaments smoke tests with proper f-strings

Improvements over v1:
- Proper f-string formatting for URLs with path parameters
- Preserve admin_token/student_token/instructor_token variables
- Clean replacement logic

USAGE:
    python tools/enhance_tournaments_smoke_tests_v2.py
"""

import re
from pathlib import Path
from typing import Dict, Set


def identify_needed_fixtures(method_content: str) -> Set[str]:
    """
    Identify which fixtures are needed for a test method based on path parameters.

    Returns:
        Set of fixture names, e.g., {"test_tournament", "test_campus_id"}
    """
    fixtures = set()

    if "{tournament_id}" in method_content or "{semester_id}" in method_content:
        fixtures.add("test_tournament")
    if "{campus_id}" in method_content:
        fixtures.add("test_campus_id")
    if "{user_id}" in method_content:
        fixtures.add("test_student_id")
    if "{student_id}" in method_content:
        fixtures.add("test_student_id")
    if "{instructor_id}" in method_content:
        fixtures.add("test_instructor_id")

    return fixtures


def transform_url_paths(content: str) -> str:
    """
    Transform URL paths to use proper f-strings with fixture values.

    Examples:
        "/{tournament_id}" -> f"/{test_tournament['tournament_id']}"
        "/{tournament_id}/campus-schedules/{campus_id}" ->
            f"/{test_tournament['tournament_id']}/campus-schedules/{test_campus_id}"
    """

    # Replace tournament_id and semester_id
    content = re.sub(
        r'api_client\.(get|post|put|patch|delete)\("(/[^"]*\{tournament_id\}[^"]*)"',
        lambda m: f'api_client.{m.group(1)}(f"{m.group(2).replace("{tournament_id}", "{test_tournament[" + chr(39) + "tournament_id" + chr(39) + "]}")}"',
        content
    )

    content = re.sub(
        r'api_client\.(get|post|put|patch|delete)\("(/[^"]*\{semester_id\}[^"]*)"',
        lambda m: f'api_client.{m.group(1)}(f"{m.group(2).replace("{semester_id}", "{test_tournament[" + chr(39) + "tournament_id" + chr(39) + "]}")}"',
        content
    )

    # Replace campus_id
    content = re.sub(
        r'(f?"[^"]*)\{campus_id\}([^"]*")',
        r'\1{test_campus_id}\2',
        content
    )

    # Replace user_id and student_id
    content = re.sub(
        r'(f?"[^"]*)\{user_id\}([^"]*")',
        r'\1{test_student_id}\2',
        content
    )

    content = re.sub(
        r'(f?"[^"]*)\{student_id\}([^"]*")',
        r'\1{test_student_id}\2',
        content
    )

    # Replace instructor_id
    content = re.sub(
        r'(f?"[^"]*)\{instructor_id\}([^"]*")',
        r'\1{test_instructor_id}\2',
        content
    )

    # Replace hardcoded fallbacks (mapping_id, session_id, etc.)
    fallbacks = ["mapping_id", "session_id", "policy_id", "task_id", "request_id", "application_id", "round_number"]
    for fb in fallbacks:
        content = re.sub(
            rf'(f?"[^"]*)\{{{fb}\}}([^"]*")',
            r'\g<1>1\2',
            content
        )

    # Replace policy_name
    content = re.sub(
        r'(f?"[^"]*)\{policy_name\}([^"]*")',
        r'\1default_policy\2',
        content
    )

    return content


def transform_method_signature(method_content: str, needed_fixtures: Set[str]) -> str:
    """
    Add fixture parameters to method signature.

    Example:
        def test_xxx(self, api_client: TestClient, admin_token: str):
        ->
        def test_xxx(self, api_client: TestClient, admin_token: str, test_tournament: Dict, test_campus_id: int):
    """

    if not needed_fixtures:
        return method_content

    # Find the method signature
    signature_pattern = r'(def test_\w+\(self, api_client: TestClient(?:, \w+_token: str)?)\):'

    def add_fixtures(match):
        base_sig = match.group(1)

        # Build fixture list
        fixture_params = []
        if "test_tournament" in needed_fixtures:
            fixture_params.append("test_tournament: Dict")
        if "test_campus_id" in needed_fixtures:
            fixture_params.append("test_campus_id: int")
        if "test_student_id" in needed_fixtures:
            fixture_params.append("test_student_id: int")
        if "test_instructor_id" in needed_fixtures:
            fixture_params.append("test_instructor_id: int")

        if fixture_params:
            return f"{base_sig}, {', '.join(fixture_params)}):"
        else:
            return f"{base_sig}):"

    return re.sub(signature_pattern, add_fixtures, method_content)


def transform_test_method(method_content: str) -> str:
    """Transform a single test method."""

    # Step 1: Identify needed fixtures
    needed_fixtures = identify_needed_fixtures(method_content)

    # Step 2: Update method signature
    if needed_fixtures:
        method_content = transform_method_signature(method_content, needed_fixtures)

    # Step 3: Transform URL paths
    method_content = transform_url_paths(method_content)

    # Step 4: Remove 404 from acceptable status codes
    method_content = method_content.replace(
        "assert response.status_code in [200, 201, 404]",
        "assert response.status_code in [200, 201, 204]"
    )

    method_content = method_content.replace(
        "# Accept 200, 201, 404 (if resource doesn't exist in test DB)",
        "# Accept 200 OK, 201 Created, or 204 No Content"
    )

    # Step 5: Update docstring/comments to reflect enhanced URLs
    method_content = re.sub(
        r'(Happy path|Auth validation|Input validation): (GET|POST|PUT|PATCH|DELETE) /\{tournament_id\}',
        lambda m: f'{m.group(1)}: {m.group(2)} ' + '/{{test_tournament["tournament_id"]}}',
        method_content
    )

    return method_content


def transform_test_file(content: str) -> str:
    """Transform entire test file."""

    # Step 1: Update file header
    old_header = '''"""
Auto-generated smoke tests for tournaments domain
Generated by tools/generate_api_tests.py

⚠️  DO NOT EDIT MANUALLY - Regenerate using:
    python tools/generate_api_tests.py --scan-api app/api --output tests/integration/api_smoke/
"""'''

    new_header = '''"""
✅ Phase 1 Enhanced: Real test data fixtures for path parameter resolution

Auto-generated smoke tests for tournaments domain (ENHANCED)
Original generation: tools/generate_api_tests.py
Phase 1 enhancement: tools/enhance_tournaments_smoke_tests_v2.py

Enhancements:
- Path parameters resolved with real test data fixtures
- 404 false greens eliminated (only accept 200/201/204)
- Test tournament, campus, and user IDs from fixtures
"""'''

    content = content.replace(old_header, new_header)

    # Step 2: Add typing import
    if "from typing import Dict" not in content:
        content = content.replace(
            "import pytest\nfrom fastapi.testclient import TestClient",
            "import pytest\nfrom typing import Dict\nfrom fastapi.testclient import TestClient"
        )

    # Step 3: Transform each test method
    # Match test methods (indented with 4 spaces)
    method_pattern = r'(    def test_\w+.*?)(?=\n    def test_|\Z)'

    def transform_match(match):
        return transform_test_method(match.group(1))

    content = re.sub(method_pattern, transform_match, content, flags=re.DOTALL)

    return content


def main():
    """Main entry point."""

    # Paths
    root_dir = Path(__file__).parent.parent
    test_file = root_dir / "tests/integration/api_smoke/test_tournaments_smoke.py"
    backup_file = test_file.with_suffix(".py.backup")

    print(f"Enhancing tournaments smoke tests (v2): {test_file}")

    # Ensure backup exists
    if not backup_file.exists():
        print(f"Creating backup: {backup_file}")
        backup_file.write_text(test_file.read_text())
    else:
        print(f"Using existing backup: {backup_file}")

    # Read original content
    original_content = test_file.read_text()

    # Transform content
    print("Transforming test file...")
    enhanced_content = transform_test_file(original_content)

    # Write enhanced content
    test_file.write_text(enhanced_content)

    print(f"✅ Enhanced test file written: {test_file}")
    print(f"📦 Backup available at: {backup_file}")
    print("\nEnhancements:")
    print("  - Path parameters replaced with fixture values")
    print("  - f-strings used for URL construction")
    print("  - 404 removed from acceptable status codes")
    print("  - Fixtures added to method signatures")
    print("\nNext steps:")
    print("1. Run tests locally: pytest tests/integration/api_smoke/test_tournaments_smoke.py -v --tb=short")
    print("2. Verify 0 flake: pytest tests/integration/api_smoke/test_tournaments_smoke.py --count=20 -v")
    print("3. Push to GitHub Actions for validation")


if __name__ == "__main__":
    main()
