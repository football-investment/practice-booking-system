"""
Phase 1: Add payload factory to POST/PUT/PATCH tests - Simplified version

Direct string replacement approach:
1. Add payload_factory parameter to test signatures
2. Replace payload = {} with factory calls
3. Extract method/path from adjacent code
"""

import re
from pathlib import Path


def process_file(file_path: Path):
    """Process test file with direct replacements."""

    with open(file_path, "r") as f:
        lines = f.readlines()

    modified_lines = []
    i = 0
    changes_count = 0

    while i < len(lines):
        line = lines[i]

        # Check for happy_path test function WITH payload = {} in next ~15 lines
        if "def test_" in line and "_happy_path" in line and "payload_factory" not in line:
            # Look ahead for payload = {}
            has_empty_payload = False
            for j in range(i, min(i + 20, len(lines))):
                if "payload = {}" in lines[j]:
                    has_empty_payload = True
                    break

            if has_empty_payload:
                # Add payload_factory to signature
                if "admin_token: str)" in line:
                    new_line = line.replace("admin_token: str)", "admin_token: str, payload_factory)")
                    modified_lines.append(new_line)
                    print(f"  ✓ Modified signature at line {i+1}")
                    i += 1
                    continue
                elif "admin_token: str," in line:
                    # Find closing paren
                    new_line = line.replace("admin_token: str,", "admin_token: str, payload_factory,")
                    modified_lines.append(new_line)
                    print(f"  ✓ Modified signature at line {i+1}")
                    i += 1
                    continue

        # Replace payload = {} with factory call
        if "payload = {}" in line and i > 0:
            # Look back to find the method call pattern
            method = None
            path = None

            # Look forward to find api_client call (usually within next 5 lines)
            for j in range(i, min(i + 5, len(lines))):
                if "api_client.post(" in lines[j]:
                    method = "POST"
                    # Extract path
                    match = re.search(r'api_client\.post\(([^,]+)', lines[j])
                    if match:
                        path = match.group(1).strip().replace('"', '').replace("'", '').replace('f', '')
                elif "api_client.put(" in lines[j]:
                    method = "PUT"
                    match = re.search(r'api_client\.put\(([^,]+)', lines[j])
                    if match:
                        path = match.group(1).strip().replace('"', '').replace("'", '').replace('f', '')
                elif "api_client.patch(" in lines[j]:
                    method = "PATCH"
                    match = re.search(r'api_client\.patch\(([^,]+)', lines[j])
                    if match:
                        path = match.group(1).strip().replace('"', '').replace("'", '').replace('f', '')

                if method and path:
                    break

            if method and path:
                # Build context
                context_parts = []

                # Check preceding lines for fixture usage
                for j in range(max(0, i-20), i):
                    if "test_tournament" in lines[j]:
                        if "'tournament_id'" not in [c for c in context_parts]:
                            context_parts.append("'tournament_id': test_tournament['tournament_id']")
                    if "session_id" in lines[j] and "{session_id}" in path:
                        if "'session_id'" not in [c for c in context_parts]:
                            context_parts.append("'session_id': session_id")

                # Build new payload line
                indent = " " * (len(line) - len(line.lstrip()))

                if context_parts:
                    context_str = "{" + ", ".join(context_parts) + "}"
                    new_payload = f"{indent}# Phase 1: Generate schema-compliant payload\n"
                    new_payload += f"{indent}payload = payload_factory.create_payload('{method}', '/api/v1/tournaments{path}', {context_str})\n"
                else:
                    new_payload = f"{indent}# Phase 1: Generate schema-compliant payload\n"
                    new_payload += f"{indent}payload = payload_factory.create_payload('{method}', '/api/v1/tournaments{path}')\n"

                # Check if previous line is TODO comment
                if i > 0 and "# TODO: Add realistic payload" in lines[i-1]:
                    # Remove the TODO line
                    modified_lines.pop()

                modified_lines.append(new_payload)
                changes_count += 1
                print(f"  ✓ Added payload at line {i+1}: {method} {path}")
                i += 1
                continue

        modified_lines.append(line)
        i += 1

    # Write back
    if changes_count > 0:
        with open(file_path, "w") as f:
            f.writelines(modified_lines)

    return changes_count


def main():
    """Main execution."""
    test_file = Path(__file__).parent.parent / "tests" / "integration" / "api_smoke" / "test_tournaments_smoke.py"

    print(f"📝 Processing: {test_file.name}\n")

    count = process_file(test_file)

    print(f"\n✅ Transformation complete")
    print(f"   Modified {count} payload assignments")
    print(f"   File: {test_file}")


if __name__ == "__main__":
    main()
