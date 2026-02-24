"""
Phase 1 Enhancement Tool: Transform auto-generated tournaments smoke tests
to use real test data fixtures.

PURPOSE:
- Replace path parameters {tournament_id} with test_tournament["tournament_id"]
- Replace path parameters {campus_id} with test_campus_id
- Replace path parameters {user_id} with test_student_id
- Remove 404 from acceptable status codes (eliminate false green)
- Add fixtures to test method signatures

USAGE:
    python tools/enhance_tournaments_smoke_tests.py
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


def parse_test_file(file_path: Path) -> str:
    """Read test file content."""
    return file_path.read_text()


def identify_path_parameters(content: str) -> Dict[str, int]:
    """
    Identify all path parameters used in the test file.

    Returns:
        Dict[param_name, count] - e.g., {"tournament_id": 120, "campus_id": 15}
    """
    params = {}
    # Match patterns like /{tournament_id}, /{campus_id}, etc.
    pattern = r'\{(\w+)\}'

    for match in re.finditer(pattern, content):
        param = match.group(1)
        params[param] = params.get(param, 0) + 1

    return params


def generate_fixture_mapping(params: Dict[str, int]) -> Dict[str, str]:
    """
    Generate mapping from path parameter to fixture name.

    Args:
        params: {"tournament_id": 120, "campus_id": 15}

    Returns:
        {"tournament_id": "test_tournament", "campus_id": "test_campus_id", ...}
    """
    mapping = {
        "tournament_id": "test_tournament",
        "semester_id": "test_tournament",
        "campus_id": "test_campus_id",
        "user_id": "test_student_id",
        "student_id": "test_student_id",
        "instructor_id": "test_instructor_id",
        "mapping_id": "1",  # Hardcoded fallback for rare endpoints
        "session_id": "1",  # Hardcoded fallback for rare endpoints
        "policy_id": "1",   # Hardcoded fallback for rare endpoints
    }

    return {param: mapping.get(param, "1") for param in params}


def transform_test_method(method_content: str, fixture_mapping: Dict[str, str]) -> str:
    """
    Transform a single test method to use real test data.

    Steps:
    1. Add fixtures to method signature
    2. Replace path parameters in URL
    3. Remove 404 from acceptable status codes
    """

    # Step 1: Identify which fixtures are needed for this method
    needed_fixtures = set()
    for param in fixture_mapping:
        if f"{{{param}}}" in method_content:
            fixture = fixture_mapping[param]
            if fixture not in ["1"]:  # Skip hardcoded fallbacks
                needed_fixtures.add(fixture)

    # Step 2: Update method signature
    # Pattern: def test_xxx(self, api_client: TestClient, admin_token: str):
    signature_pattern = r'(def test_\w+)\(self, (api_client: TestClient(?:, \w+_token: str)?)\):'

    def add_fixtures_to_signature(match):
        method_name = match.group(1)
        existing_params = match.group(2)

        # Build new signature with needed fixtures
        new_params = [existing_params]

        if "test_tournament" in needed_fixtures:
            new_params.append("test_tournament: Dict")
        if "test_campus_id" in needed_fixtures:
            new_params.append("test_campus_id: int")
        if "test_student_id" in needed_fixtures:
            new_params.append("test_student_id: int")
        if "test_instructor_id" in needed_fixtures:
            new_params.append("test_instructor_id: int")

        return f'{method_name}(self, {", ".join(new_params)}):'

    method_content = re.sub(signature_pattern, add_fixtures_to_signature, method_content)

    # Step 3: Replace path parameters with fixture values
    for param, fixture in fixture_mapping.items():
        if fixture == "test_tournament":
            # Replace {tournament_id} or {semester_id} with test_tournament["tournament_id"]
            method_content = method_content.replace(
                f"{{{param}}}",
                f'{{test_tournament["tournament_id"]}}'
            )
        elif fixture in ["test_campus_id", "test_student_id", "test_instructor_id"]:
            # Replace {campus_id} or {user_id} with {test_campus_id}
            method_content = method_content.replace(
                f"{{{param}}}",
                f"{{{fixture}}}"
            )
        else:
            # Hardcoded fallback (e.g., mapping_id, session_id)
            method_content = method_content.replace(
                f"{{{param}}}",
                fixture
            )

    # Step 4: Remove 404 from acceptable status codes
    # Pattern: assert response.status_code in [200, 201, 404]
    # Replace with: assert response.status_code in [200, 201, 204]
    method_content = re.sub(
        r'assert response\.status_code in \[200, 201, 404\]',
        'assert response.status_code in [200, 201, 204]',
        method_content
    )

    # Update error message comments to reflect 404 removal
    method_content = re.sub(
        r'# Accept 200, 201, 404 \(if resource doesn\'t exist in test DB\)',
        '# Accept 200 OK, 201 Created, or 204 No Content',
        method_content
    )

    return method_content


def transform_test_file(content: str) -> str:
    """
    Transform entire test file to use real test data.
    """

    # Step 1: Update file header
    content = content.replace(
        '"""',
        '"""\nPhase 1 Enhanced: Real test data fixtures for path parameter resolution\n',
        1
    )

    content = content.replace(
        '⚠️  DO NOT EDIT MANUALLY',
        '✅ Phase 1 Enhanced: Path parameters resolved with real test data'
    )

    # Step 2: Add typing import for Dict
    if "from typing import Dict" not in content:
        content = content.replace(
            "import pytest\nfrom fastapi.testclient import TestClient",
            "import pytest\nfrom typing import Dict\nfrom fastapi.testclient import TestClient"
        )

    # Step 3: Identify path parameters
    params = identify_path_parameters(content)
    print(f"Found {len(params)} unique path parameters: {list(params.keys())}")

    # Step 4: Generate fixture mapping
    fixture_mapping = generate_fixture_mapping(params)
    print(f"Fixture mapping: {fixture_mapping}")

    # Step 5: Transform each test method
    # Split by method definitions
    method_pattern = r'(    def test_\w+.*?)(?=\n    def test_|\n\nclass |\Z)'

    def transform_match(match):
        return transform_test_method(match.group(1), fixture_mapping)

    content = re.sub(method_pattern, transform_match, content, flags=re.DOTALL)

    return content


def main():
    """Main entry point."""

    # Paths
    root_dir = Path(__file__).parent.parent
    test_file = root_dir / "tests/integration/api_smoke/test_tournaments_smoke.py"
    backup_file = test_file.with_suffix(".py.backup")

    print(f"Enhancing tournaments smoke tests: {test_file}")

    # Backup original file
    if not backup_file.exists():
        print(f"Creating backup: {backup_file}")
        backup_file.write_text(test_file.read_text())

    # Read original content
    original_content = parse_test_file(test_file)

    # Transform content
    print("Transforming test file...")
    enhanced_content = transform_test_file(original_content)

    # Write enhanced content
    test_file.write_text(enhanced_content)

    print(f"✅ Enhanced test file written: {test_file}")
    print(f"📦 Backup available at: {backup_file}")
    print("\nNext steps:")
    print("1. Run tests locally: pytest tests/integration/api_smoke/test_tournaments_smoke.py -v")
    print("2. Verify 0 flake: pytest tests/integration/api_smoke/test_tournaments_smoke.py --count=20 -v")
    print("3. Push to GitHub Actions for validation")


if __name__ == "__main__":
    main()
