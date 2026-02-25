"""
Phase 1: Integrate payload factory into tournament smoke tests

This script modifies test_tournaments_smoke.py to use the payload_factory
for generating valid request payloads, eliminating 422 validation errors.

Transformations:
1. Add payload_factory parameter to happy path test signatures
2. Replace payload = {} with actual factory calls
3. Add context dictionary with fixture values
4. Un-skip input validation tests
"""

import re
from pathlib import Path


def modify_happy_path_test(
    content: str,
    endpoint_path: str,
    method: str,
    test_function_name: str,
    has_tournament_id: bool = False,
    has_session_id: bool = False
) -> str:
    """
    Modify a single happy path test to use payload factory.

    Args:
        content: File content
        endpoint_path: API endpoint path (e.g., "/create", "/{tournament_id}/cancel")
        method: HTTP method (post, put, patch)
        test_function_name: Name of test function
        has_tournament_id: Whether endpoint uses tournament_id
        has_session_id: Whether endpoint uses session_id

    Returns:
        Modified content
    """
    # Pattern to match the test function signature
    sig_pattern = rf"(def {test_function_name}\(self, api_client: TestClient, admin_token: str)"

    # Check if payload_factory is already in signature
    if f"def {test_function_name}(self, api_client: TestClient, admin_token: str, payload_factory" in content:
        print(f"  ✓ {test_function_name} already has payload_factory parameter")
        return content

    # Add required fixtures to signature
    params_to_add = ["payload_factory"]
    if has_tournament_id:
        params_to_add.append("test_tournament: Dict")
    if has_session_id:
        params_to_add.append("session_id: int = 1")

    new_signature = f"def {test_function_name}(self, api_client: TestClient, admin_token: str, {', '.join(params_to_add)}"

    content = re.sub(
        sig_pattern,
        new_signature,
        content
    )

    # Find the test function body
    func_start = content.find(f"def {test_function_name}(")
    if func_start == -1:
        return content

    # Find the payload = {} line
    payload_pattern = r"(\s+)# TODO: Add realistic payload.*\n\s+payload = \{\}"
    payload_replacement = r"\1# Phase 1: Generate schema-compliant payload\n\1payload = payload_factory.create_payload('" + method.upper() + "', '" + endpoint_path + "'"

    # Add context if needed
    if has_tournament_id or has_session_id:
        context_parts = []
        if has_tournament_id:
            context_parts.append("'tournament_id': test_tournament['tournament_id']")
        if has_session_id:
            context_parts.append("'session_id': session_id")

        context_dict = "{" + ", ".join(context_parts) + "}"
        payload_replacement += f", {context_dict}"

    payload_replacement += ")"

    # Apply replacement
    content = re.sub(payload_pattern, payload_replacement, content)

    return content


def add_import_statement(content: str) -> str:
    """Add typing.Dict import if not present."""
    if "from typing import Dict" in content or "from typing import" in content and "Dict" in content:
        return content

    # Find the imports section and add Dict
    imports_pattern = r"(from typing import .*)"
    if re.search(imports_pattern, content):
        content = re.sub(
            r"(from typing import )",
            r"\1Dict, ",
            content,
            count=1
        )
    else:
        # Add new import after other imports
        content = re.sub(
            r"(import pytest\n)",
            r"\1from typing import Dict\n",
            content,
            count=1
        )

    return content


def main():
    """Main execution."""
    test_file = Path(__file__).parent.parent / "tests" / "integration" / "api_smoke" / "test_tournaments_smoke.py"

    print(f"📝 Integrating payload factory into: {test_file.name}\n")

    with open(test_file, "r") as f:
        content = f.read()

    original_content = content

    # Add Dict import
    content = add_import_statement(content)

    # Define endpoint modifications
    modifications = [
        # POST /create
        {
            "endpoint_path": "/api/v1/tournaments/create",
            "method": "POST",
            "test_function_name": "test_create_tournament_happy_path",
            "has_tournament_id": False,
            "has_session_id": False
        },
        # POST / (create tournament v1)
        {
            "endpoint_path": "/api/v1/tournaments/",
            "method": "POST",
            "test_function_name": "test_create_tournament_endpoint_happy_path",
            "has_tournament_id": False,
            "has_session_id": False
        },
        # PATCH /{tournament_id}
        {
            "endpoint_path": "/api/v1/tournaments/{tournament_id}",
            "method": "PATCH",
            "test_function_name": "test_tournament_update_happy_path",
            "has_tournament_id": True,
            "has_session_id": False
        },
        # POST /{tournament_id}/cancel
        {
            "endpoint_path": "/api/v1/tournaments/{tournament_id}/cancel",
            "method": "POST",
            "test_function_name": "test_cancel_tournament_happy_path",
            "has_tournament_id": True,
            "has_session_id": False
        },
        # POST /{tournament_id}/assign-instructor
        {
            "endpoint_path": "/api/v1/tournaments/{tournament_id}/assign-instructor",
            "method": "POST",
            "test_function_name": "test_assign_instructor_happy_path",
            "has_tournament_id": True,
            "has_session_id": False
        },
        # POST /{tournament_id}/admin/batch-enroll
        {
            "endpoint_path": "/api/v1/tournaments/{tournament_id}/admin/batch-enroll",
            "method": "POST",
            "test_function_name": "test_batch_enroll_players_happy_path",
            "has_tournament_id": True,
            "has_session_id": False
        },
        # POST /{tournament_id}/skill-mappings
        {
            "endpoint_path": "/api/v1/tournaments/{tournament_id}/skill-mappings",
            "method": "POST",
            "test_function_name": "test_create_skill_mapping_happy_path",
            "has_tournament_id": True,
            "has_session_id": False
        },
    ]

    print("Applying modifications:")
    for mod in modifications:
        print(f"  • {mod['method']} {mod['endpoint_path']}")
        content = modify_happy_path_test(
            content,
            mod["endpoint_path"],
            mod["method"],
            mod["test_function_name"],
            mod["has_tournament_id"],
            mod["has_session_id"]
        )

    # Check if changes were made
    if content == original_content:
        print("\n⚠️  No changes applied - patterns may not match")
        return

    # Write back
    with open(test_file, "w") as f:
        f.write(content)

    print(f"\n✅ Successfully integrated payload factory")
    print(f"   Modified: {test_file}")


if __name__ == "__main__":
    main()
