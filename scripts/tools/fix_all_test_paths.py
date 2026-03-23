"""
Fix all test paths to use absolute paths instead of relative paths.

Changes:
- api_client.METHOD("/...") → api_client.METHOD("/api/v1/tournaments/...")
- api_client.METHOD(f"/...") → api_client.METHOD(f"/api/v1/tournaments/...")
"""

import re
from pathlib import Path


def fix_paths(content: str) -> str:
    """Fix all API client calls to use absolute paths."""

    # Pattern 1: api_client.METHOD("/path") or api_client.METHOD(f"/path")
    # Replace with api_client.METHOD("/api/v1/tournaments/path")

    # Handle string literals (non f-strings)
    content = re.sub(
        r'api_client\.(get|post|put|patch|delete)\("/',
        r'api_client.\1("/api/v1/tournaments/',
        content
    )

    # Handle f-strings
    content = re.sub(
        r'api_client\.(get|post|put|patch|delete)\(f"/',
        r'api_client.\1(f"/api/v1/tournaments/',
        content
    )

    # Handle single-quote variants
    content = re.sub(
        r"api_client\.(get|post|put|patch|delete)\('/",
        r"api_client.\1('/api/v1/tournaments/",
        content
    )

    content = re.sub(
        r"api_client\.(get|post|put|patch|delete)\(f'/",
        r"api_client.\1(f'/api/v1/tournaments/",
        content
    )

    # Fix double prefixes if any (in case script runs twice)
    content = content.replace("/api/v1/tournaments/api/v1/tournaments/", "/api/v1/tournaments/")

    return content


def main():
    """Main execution."""
    test_file = Path(__file__).parent.parent / "tests" / "integration" / "api_smoke" / "test_tournaments_smoke.py"

    print(f"📝 Fixing paths in: {test_file.name}\n")

    with open(test_file, "r") as f:
        original_content = f.read()

    fixed_content = fix_paths(original_content)

    # Count changes
    original_count = original_content.count('api_client.')
    # Count how many NOW have /api/v1/tournaments
    fixed_count = fixed_content.count('/api/v1/tournaments/')

    print(f"Total api_client calls: {original_count}")
    print(f"Calls with /api/v1/tournaments/ prefix: {fixed_count}")

    if fixed_content != original_content:
        with open(test_file, "w") as f:
            f.write(fixed_content)
        print(f"\n✅ File updated successfully")
    else:
        print(f"\n✅ No changes needed (already fixed)")

    print(f"   File: {test_file}")


if __name__ == "__main__":
    main()
