#!/usr/bin/env python3
"""
Remove extra='forbid' from Base schemas

CRITICAL FIX: Base schemas (like SessionBase, UserBase) should NEVER have
extra='forbid' because Response schemas inherit from them, and Response
schemas must allow extra fields from ORM models.

Architecture:
  ❌ WRONG:
    class SessionBase(BaseModel):
        model_config = ConfigDict(extra='forbid')  # <-- BREAKS RESPONSES!

    class Session(SessionBase):  # Inherits extra='forbid' → FAILS!
        model_config = ConfigDict(from_attributes=True)

  ✅ CORRECT:
    class SessionBase(BaseModel):
        # NO extra='forbid' here!

    class SessionCreate(SessionBase):
        model_config = ConfigDict(extra='forbid')  # ONLY in requests!

    class Session(SessionBase):
        model_config = ConfigDict(from_attributes=True)
"""

import re
from pathlib import Path

SCHEMA_DIR = Path("app/schemas")

def remove_extra_forbid_from_base(file_path: Path) -> bool:
    """Remove extra='forbid' from Base schema classes"""
    content = file_path.read_text()
    original_content = content

    # Pattern: class XxxBase(BaseModel): followed by model_config with extra='forbid'
    # We need to remove ONLY the extra='forbid' part, keep other config if present

    # Step 1: Find Base classes with extra='forbid' in their ConfigDict
    pattern = r"(class\s+\w+Base\([^)]*BaseModel[^)]*\):[^\n]*\n\s+model_config\s*=\s*ConfigDict\()([^)]*extra='forbid'[^)]*)\)"

    def replace_config(match):
        """Remove extra='forbid' from ConfigDict, handle other params"""
        class_def = match.group(1)
        config_content = match.group(2)

        # Remove extra='forbid' and clean up commas
        cleaned = re.sub(r"extra='forbid'\s*,?\s*", "", config_content)
        cleaned = re.sub(r",\s*,", ",", cleaned)  # Fix double commas
        cleaned = re.sub(r",\s*$", "", cleaned)   # Remove trailing comma
        cleaned = re.sub(r"^\s*,", "", cleaned)   # Remove leading comma

        # If nothing left, remove entire model_config line
        if not cleaned.strip():
            # Remove the entire line including newline
            return match.group(0).split('\n')[0] + '\n'  # Keep class def only

        return f"{class_def}{cleaned})"

    content = re.sub(pattern, replace_config, content)

    # Step 2: If model_config is now empty (only has closing paren), remove it
    content = re.sub(
        r"(class\s+\w+Base\([^)]*BaseModel[^)]*\):[^\n]*\n)\s+model_config\s*=\s*ConfigDict\(\s*\)\s*\n",
        r"\1",
        content
    )

    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def main():
    """Remove extra='forbid' from all Base schemas"""
    fixed_files = []

    for schema_file in SCHEMA_DIR.glob("*.py"):
        if schema_file.name == "__init__.py":
            continue

        if remove_extra_forbid_from_base(schema_file):
            fixed_files.append(schema_file.name)
            print(f"✅ Fixed: {schema_file.name}")

    print(f"\n{'='*60}")
    print(f"Fixed {len(fixed_files)} files")
    print(f"{'='*60}")

    if fixed_files:
        print("\nFixed files:")
        for file in sorted(fixed_files):
            print(f"  - {file}")


if __name__ == "__main__":
    main()
