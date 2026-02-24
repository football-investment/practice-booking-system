"""
Phase 1: Add payload factory to ALL POST/PUT/PATCH tests

This script performs a comprehensive transformation of test_tournaments_smoke.py:
1. Adds payload_factory parameter to all happy_path test signatures
2. Replaces `payload = {}` with payload_factory.create_payload() calls
3. Automatically extracts method and path from the test code
4. Handles context generation (tournament_id, session_id, etc.)
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


def extract_method_and_path(test_body: str) -> Tuple[str, str]:
    """
    Extract HTTP method and path from test body.

    Returns:
        (method, path) tuple, e.g., ("POST", "/create")
    """
    # Pattern: response = api_client.METHOD(PATH, ...)
    pattern = r'response = api_client\.(post|put|patch)\(([^,]+)'
    match = re.search(pattern, test_body)

    if not match:
        return ("POST", "UNKNOWN")

    method = match.group(1).upper()
    path = match.group(2).strip()

    # Clean up path (remove quotes, f-string markers)
    path = path.replace('f"', '').replace('"', '').replace("f'", '').replace("'", '')

    return (method, path)


def detect_context_vars(test_signature: str, test_body: str) -> List[str]:
    """
    Detect which context variables are needed based on test signature and body.

    Returns:
        List of context variable names, e.g., ['tournament_id', 'session_id']
    """
    context_vars = []

    if "test_tournament" in test_signature:
        context_vars.append("tournament_id")

    if "session_id" in test_signature or "{session_id}" in test_body:
        context_vars.append("session_id")

    if "test_student_id" in test_signature:
        context_vars.append("student_id")

    if "test_instructor_id" in test_signature:
        context_vars.append("instructor_id")

    if "test_campus_id" in test_signature:
        context_vars.append("campus_id")

    return context_vars


def build_context_dict(context_vars: List[str], test_signature: str) -> str:
    """
    Build context dictionary string.

    Args:
        context_vars: List of variable names
        test_signature: Test function signature to check parameter names

    Returns:
        Context dict string, e.g., "{'tournament_id': test_tournament['tournament_id']}"
    """
    if not context_vars:
        return ""

    parts = []
    for var in context_vars:
        if var == "tournament_id" and "test_tournament" in test_signature:
            parts.append(f"'{var}': test_tournament['{var}']")
        elif var == "session_id":
            parts.append(f"'{var}': session_id")
        elif var == "student_id" and "test_student_id" in test_signature:
            parts.append(f"'{var}': test_student_id")
        elif var == "instructor_id" and "test_instructor_id" in test_signature:
            parts.append(f"'{var}': test_instructor_id")
        elif var == "campus_id" and "test_campus_id" in test_signature:
            parts.append(f"'{var}': test_campus_id")

    if not parts:
        return ""

    return "{" + ", ".join(parts) + "}"


def transform_test(test_text: str) -> str:
    """
    Transform a single test function to use payload factory.

    Args:
        test_text: Full text of test function

    Returns:
        Transformed test text
    """
    # Skip if already transformed
    if "payload_factory.create_payload" in test_text:
        return test_text

    # Skip if no payload = {} line
    if "payload = {}" not in test_text:
        return test_text

    # Extract function signature
    sig_match = re.search(r'def (test_\w+_happy_path)\((.*?)\):', test_text, re.DOTALL)
    if not sig_match:
        return test_text

    func_name = sig_match.group(1)
    params = sig_match.group(2)

    # Skip if payload_factory already in signature
    if "payload_factory" in params:
        return test_text

    # Add payload_factory to signature
    # Insert after admin_token
    new_params = params.replace("admin_token: str", "admin_token: str, payload_factory")
    test_text = test_text.replace(f"def {func_name}({params}):", f"def {func_name}({new_params}):")

    # Extract method and path from test body
    method, path = extract_method_and_path(test_text)

    # Detect required context variables
    context_vars = detect_context_vars(params, test_text)
    context_str = build_context_dict(context_vars, params)

    # Build replacement for payload = {}
    if context_str:
        new_payload = f"payload = payload_factory.create_payload('{method}', '{path}', {context_str})"
    else:
        new_payload = f"payload = payload_factory.create_payload('{method}', '{path}')"

    # Replace TODO comment and payload = {}
    test_text = re.sub(
        r'# TODO: Add realistic payload.*\n\s+payload = \{\}',
        f'# Phase 1: Generate schema-compliant payload\n        {new_payload}',
        test_text
    )

    # If no TODO, just replace payload = {}
    if "payload = {}" in test_text:
        test_text = re.sub(
            r'(\s+)payload = \{\}',
            rf'\1# Phase 1: Generate schema-compliant payload\n\1{new_payload}',
            test_text
        )

    return test_text


def process_file(file_path: Path) -> int:
    """
    Process the entire test file.

    Returns:
        Number of tests transformed
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Find all happy_path test functions
    # Pattern: from def test_XXX_happy_path to next def test_ or end of class
    pattern = r'(    def test_\w*happy_path\(.*?\n(?:.*?\n)*?(?=    def test_|^class |$))'

    tests = re.findall(pattern, content, re.MULTILINE)

    print(f"Found {len(tests)} happy_path test functions\n")

    transformed_count = 0
    original_content = content

    for test in tests:
        # Only process if it has payload = {}
        if "payload = {}" in test and "payload_factory" not in test:
            transformed = transform_test(test)
            if transformed != test:
                content = content.replace(test, transformed)
                transformed_count += 1

                # Extract function name for logging
                func_match = re.search(r'def (test_\w+_happy_path)', test)
                if func_match:
                    print(f"  ✓ Transformed: {func_match.group(1)}")

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)

    return transformed_count


def main():
    """Main execution."""
    test_file = Path(__file__).parent.parent / "tests" / "integration" / "api_smoke" / "test_tournaments_smoke.py"

    print(f"📝 Processing: {test_file.name}\n")

    count = process_file(test_file)

    print(f"\n✅ Transformation complete")
    print(f"   Modified {count} test functions")
    print(f"   File: {test_file}")


if __name__ == "__main__":
    main()
