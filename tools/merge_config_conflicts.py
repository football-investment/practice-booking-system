#!/usr/bin/env python3
"""
Merge conflicting class Config: and model_config definitions

Handles cases where both exist in the same class.
"""

import re
from pathlib import Path


def merge_config_in_file(file_path: Path) -> bool:
    """Merge class Config and model_config in a single file"""
    content = file_path.read_text()
    original = content

    # Pattern to find classes with both model_config and class Config
    # This is complex, so we'll do it iteratively

    modified = False

    # Find all BaseModel classes
    class_pattern = re.compile(
        r'(class\s+(\w+)\(BaseModel\):.*?)(?=\nclass\s+\w+\(|\Z)',
        re.DOTALL
    )

    new_content = content

    for class_match in class_pattern.finditer(content):
        class_body = class_match.group(1)
        class_name = class_match.group(2)

        # Check if has both model_config and class Config
        has_model_config = 'model_config = ConfigDict(' in class_body
        has_class_config = 'class Config:' in class_body

        if has_model_config and has_class_config:
            # Extract model_config
            model_config_match = re.search(
                r'model_config = ConfigDict\((.*?)\)',
                class_body,
                re.DOTALL
            )

            # Extract class Config json_schema_extra
            json_schema_match = re.search(
                r'class Config:\s+json_schema_extra\s*=\s*(\{.*?\})',
                class_body,
                re.DOTALL
            )

            if model_config_match and json_schema_match:
                # Build merged config
                existing_config = model_config_match.group(1).strip()
                json_schema = json_schema_match.group(1)

                # Remove trailing comma if present
                if existing_config.endswith(','):
                    existing_config = existing_config[:-1]

                merged_config = f"model_config = ConfigDict(\n        {existing_config},\n        json_schema_extra={json_schema}\n    )"

                # Replace in class body
                new_class_body = class_body

                # Remove old model_config line
                new_class_body = re.sub(
                    r'model_config = ConfigDict\(.*?\)\n',
                    '',
                    new_class_body,
                    flags=re.DOTALL
                )

                # Remove class Config block
                new_class_body = re.sub(
                    r'\n    class Config:.*?\n        \}\n',
                    '',
                    new_class_body,
                    flags=re.DOTALL
                )

                # Find docstring position
                docstring_match = re.search(r'""".*?"""', new_class_body, re.DOTALL)
                if docstring_match:
                    # Insert after docstring
                    insert_pos = docstring_match.end()
                    new_class_body = (
                        new_class_body[:insert_pos] +
                        f'\n    {merged_config}\n' +
                        new_class_body[insert_pos:]
                    )
                else:
                    # Insert after class definition line
                    insert_pos = new_class_body.find(':') + 1
                    new_class_body = (
                        new_class_body[:insert_pos] +
                        f'\n    {merged_config}\n' +
                        new_class_body[insert_pos:]
                    )

                # Replace in full content
                new_content = new_content.replace(class_body, new_class_body)
                modified = True

    if modified:
        file_path.write_text(new_content)
        return True

    return False


def main():
    modified_count = 0

    # Scan all Python files
    for py_file in Path('app').rglob('*.py'):
        if py_file.name == '__init__.py' or 'test_' in py_file.name:
            continue

        if merge_config_in_file(py_file):
            print(f"✓ Merged: {py_file}")
            modified_count += 1

    print(f"\n✅ Total files merged: {modified_count}")


if __name__ == "__main__":
    main()
