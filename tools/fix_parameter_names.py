"""
P0 Fix Tool: Correct parameter names in test paths

Problem: Generic {id} used instead of specific parameter names
Solution: Replace with correct parameter names from actual routes
"""

import re
from pathlib import Path


PARAMETER_CORRECTIONS = [
    # skill-mappings: /1 or /{id} should be /{mapping_id}
    (r'/skill-mappings/1\b', '/skill-mappings/{mapping_id}'),
    (r'/skill-mappings/\{id\}', '/skill-mappings/{mapping_id}'),

    # generation-status: /1 or /{id} should be /{task_id}
    (r'/generation-status/1\b', '/generation-status/{task_id}'),
    (r'/generation-status/\{id\}', '/generation-status/{task_id}'),

    # sessions: /1 or /{id} should be /{session_id}
    (r'/sessions/1/', '/sessions/{session_id}/'),
    (r'/sessions/\{id\}/', '/sessions/{session_id}/'),

    # rounds: /1 or /{id} should be /{round_number}
    (r'/rounds/1/', '/rounds/{round_number}/'),
    (r'/rounds/\{id\}/', '/rounds/{round_number}/'),

    # instructor-applications: /1 or /{id} should be /{application_id}
    (r'/instructor-applications/1/', '/instructor-applications/{application_id}/'),
    (r'/instructor-applications/\{id\}/', '/instructor-applications/{application_id}/'),

    # requests: /1 or /{id} should be /{request_id}
    (r'/requests/1/', '/requests/{request_id}/'),
    (r'/requests/\{id\}/', '/requests/{request_id}/'),

    # policy_name: literal 'default_policy' should stay as-is (it's a valid literal value)
    # No change needed for /reward-policies/default_policy
]


def fix_parameter_names(content: str) -> str:
    """Fix parameter names in test paths."""

    for pattern, replacement in PARAMETER_CORRECTIONS:
        content = re.sub(pattern, replacement, content)

    return content


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent.parent
    test_file = root_dir / "tests/integration/api_smoke/test_tournaments_smoke.py"

    print("P0: Fixing parameter names in test paths...")
    print(f"Test file: {test_file}")

    # Read content
    content = test_file.read_text()

    # Count issues before fix
    issues = []
    for pattern, _ in PARAMETER_CORRECTIONS:
        matches = re.findall(pattern, content)
        if matches:
            issues.append((pattern, len(matches)))

    print(f"\nIssues found:")
    for pattern, count in issues:
        print(f"  {pattern}: {count} occurrences")

    # Fix
    fixed_content = fix_parameter_names(content)

    # Write back
    test_file.write_text(fixed_content)

    # Count remaining issues
    remaining = []
    for pattern, _ in PARAMETER_CORRECTIONS:
        matches = re.findall(pattern, fixed_content)
        if matches:
            remaining.append((pattern, len(matches)))

    fixed_count = sum(count for _, count in issues) - sum(count for _, count in remaining)

    print(f"\n✅ Fixed: {fixed_count} parameter names corrected")

    if remaining:
        print(f"\n⚠️ Remaining issues:")
        for pattern, count in remaining:
            print(f"  {pattern}: {count} occurrences")
    else:
        print("\n✅ All parameter name issues resolved!")


if __name__ == "__main__":
    main()
