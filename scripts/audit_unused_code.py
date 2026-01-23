#!/usr/bin/env python3
"""
Dead Code & Unused Symbols Audit Script

This script identifies unused code elements in the Python codebase:
- Unused imports
- Unused variables
- Unused functions
- Unused classes
- Unused methods
- Unused attributes
- Unreachable code

Uses vulture for detection with custom whitelists for known false positives.

Usage:
    python scripts/audit_unused_code.py [--min-confidence <0-100>]

Options:
    --min-confidence: Minimum confidence threshold (default: 80)
                     Lower = more potential issues but more false positives
                     Higher = fewer issues but might miss some dead code
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import argparse


def get_vulture_path() -> str:
    """Get path to vulture executable."""
    # Try venv first
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_vulture = os.path.join(project_root, 'venv', 'bin', 'vulture')
    if os.path.exists(venv_vulture):
        return venv_vulture

    # Try system vulture
    return 'vulture'


def check_vulture_installed() -> bool:
    """Check if vulture is installed."""
    try:
        vulture_path = get_vulture_path()
        result = subprocess.run(
            [vulture_path, '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_vulture() -> bool:
    """Install vulture if not present."""
    print("📦 Installing vulture...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'vulture'],
            check=True,
            capture_output=True
        )
        print("✅ Vulture installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install vulture: {e}")
        return False


def create_vulture_whitelist(project_root: str) -> str:
    """
    Create a whitelist file for known false positives.

    Common false positives in our codebase:
    - FastAPI route decorators (appear unused but are registered)
    - SQLAlchemy model attributes (used via ORM)
    - Pydantic model fields (used for validation)
    - pytest fixtures (used via dependency injection)
    - Streamlit session_state keys (dynamic access)
    """
    whitelist_path = os.path.join(project_root, '.vulture_whitelist.py')

    whitelist_content = '''
# Vulture whitelist for known false positives

# FastAPI route handlers (registered via decorators)
_.get
_.post
_.put
_.patch
_.delete
_.options
_.head

# SQLAlchemy model attributes (ORM access)
_.id
_.created_at
_.updated_at
_.is_active
_.metadata
_.__tablename__

# Pydantic model fields
_.model_config
_.model_fields
_.model_validate

# Pytest fixtures (dependency injection)
_.db
_.client
_.admin_token
_.user_token

# Streamlit session state (dynamic access)
_.session_state

# Common base class methods
_.setup
_.teardown
_.setUp
_.tearDown

# Magic methods that might not be directly called
_.__init__
_.__str__
_.__repr__
_.__eq__
_.__hash__
_.__call__

# Alembic migrations
_.upgrade
_.downgrade

# Click CLI commands
_.command
_.group
'''

    with open(whitelist_path, 'w') as f:
        f.write(whitelist_content)

    return whitelist_path


def run_vulture_scan(
    project_root: str,
    min_confidence: int,
    exclude_dirs: Set[str]
) -> List[Dict]:
    """
    Run vulture scan on the project.

    Returns list of issues found.
    """
    print(f"\n🔍 Scanning for unused code (min confidence: {min_confidence}%)...\n")

    # Create whitelist
    whitelist_path = create_vulture_whitelist(project_root)

    # Directories to scan
    scan_dirs = []
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if os.path.isdir(item_path) and item not in exclude_dirs and not item.startswith('.'):
            if any(Path(item_path).rglob('*.py')):
                scan_dirs.append(item_path)

    # Also scan root level Python files
    for item in os.listdir(project_root):
        if item.endswith('.py'):
            scan_dirs.append(os.path.join(project_root, item))

    if not scan_dirs:
        print("❌ No Python files found to scan")
        return []

    # Run vulture
    vulture_path = get_vulture_path()
    cmd = [
        vulture_path,
        *scan_dirs,
        whitelist_path,
        f'--min-confidence={min_confidence}',
        '--sort-by-size'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False
        )

        # Parse vulture output
        issues = parse_vulture_output(result.stdout, project_root)

        # Clean up whitelist
        os.remove(whitelist_path)

        return issues

    except Exception as e:
        print(f"❌ Error running vulture: {e}")
        if os.path.exists(whitelist_path):
            os.remove(whitelist_path)
        return []


def parse_vulture_output(output: str, project_root: str) -> List[Dict]:
    """Parse vulture's text output into structured data."""
    issues = []

    for line in output.strip().split('\n'):
        if not line.strip() or line.startswith('#'):
            continue

        # Vulture output format: path/to/file.py:line: message (confidence%)
        parts = line.split(':', 2)
        if len(parts) >= 3:
            file_path = parts[0].strip()
            try:
                line_num = int(parts[1].strip())
            except ValueError:
                continue

            # Extract message and confidence
            rest = parts[2].strip()
            if '(' in rest and rest.endswith(')'):
                message_part, conf_part = rest.rsplit('(', 1)
                message = message_part.strip()
                confidence = conf_part.rstrip(')').replace('%', '').strip()
                try:
                    confidence = int(confidence)
                except ValueError:
                    confidence = 0
            else:
                message = rest
                confidence = 0

            # Categorize issue type
            issue_type = categorize_issue(message)

            # Get relative path
            rel_path = os.path.relpath(file_path, project_root)

            issues.append({
                'file': rel_path,
                'line': line_num,
                'message': message,
                'confidence': confidence,
                'type': issue_type
            })

    return issues


def categorize_issue(message: str) -> str:
    """Categorize the type of unused code issue."""
    message_lower = message.lower()

    if 'unused import' in message_lower:
        return 'unused_import'
    elif 'unused function' in message_lower:
        return 'unused_function'
    elif 'unused class' in message_lower:
        return 'unused_class'
    elif 'unused method' in message_lower:
        return 'unused_method'
    elif 'unused variable' in message_lower:
        return 'unused_variable'
    elif 'unused attribute' in message_lower:
        return 'unused_attribute'
    elif 'unused property' in message_lower:
        return 'unused_property'
    elif 'unreachable code' in message_lower:
        return 'unreachable_code'
    else:
        return 'other'


def analyze_issues(issues: List[Dict]) -> Dict:
    """Analyze and categorize issues."""
    analysis = {
        'total_issues': len(issues),
        'by_type': defaultdict(int),
        'by_confidence': defaultdict(int),
        'by_file': defaultdict(list),
        'by_directory': defaultdict(int)
    }

    for issue in issues:
        # Count by type
        analysis['by_type'][issue['type']] += 1

        # Count by confidence range
        conf = issue['confidence']
        if conf >= 90:
            conf_range = '90-100%'
        elif conf >= 80:
            conf_range = '80-89%'
        elif conf >= 70:
            conf_range = '70-79%'
        else:
            conf_range = '<70%'
        analysis['by_confidence'][conf_range] += 1

        # Group by file
        analysis['by_file'][issue['file']].append(issue)

        # Count by directory
        directory = os.path.dirname(issue['file'])
        if not directory:
            directory = '.'
        analysis['by_directory'][directory] += 1

    return analysis


def print_audit_report(issues: List[Dict], analysis: Dict, min_confidence: int):
    """Print formatted audit report to console."""

    print("\n" + "=" * 80)
    print("🔍 DEAD CODE & UNUSED SYMBOLS AUDIT REPORT")
    print("=" * 80)

    print(f"\n📊 Summary (min confidence: {min_confidence}%):")
    print(f"   - Total issues found: {analysis['total_issues']}")

    if analysis['total_issues'] == 0:
        print("\n✅ No unused code detected!")
        return

    print(f"   - Files affected: {len(analysis['by_file'])}")
    print(f"   - Directories affected: {len(analysis['by_directory'])}")

    # By type
    print(f"\n📦 Issues by Type:")
    type_labels = {
        'unused_import': 'Unused Imports',
        'unused_function': 'Unused Functions',
        'unused_class': 'Unused Classes',
        'unused_method': 'Unused Methods',
        'unused_variable': 'Unused Variables',
        'unused_attribute': 'Unused Attributes',
        'unused_property': 'Unused Properties',
        'unreachable_code': 'Unreachable Code',
        'other': 'Other'
    }
    for issue_type, count in sorted(analysis['by_type'].items(), key=lambda x: x[1], reverse=True):
        label = type_labels.get(issue_type, issue_type)
        print(f"   - {label}: {count}")

    # By confidence
    print(f"\n🎯 Issues by Confidence:")
    for conf_range in ['90-100%', '80-89%', '70-79%', '<70%']:
        count = analysis['by_confidence'].get(conf_range, 0)
        if count > 0:
            print(f"   - {conf_range}: {count}")

    # Top directories
    print(f"\n📁 Top 10 Directories with Most Issues:")
    top_dirs = sorted(analysis['by_directory'].items(), key=lambda x: x[1], reverse=True)[:10]
    for directory, count in top_dirs:
        print(f"   {count:4d} - {directory}")

    # Top files
    print(f"\n📄 Top 20 Files with Most Issues:")
    top_files = sorted(analysis['by_file'].items(), key=lambda x: len(x[1]), reverse=True)[:20]
    for file_path, file_issues in top_files:
        print(f"   {len(file_issues):4d} - {file_path}")

    print("\n" + "-" * 80)

    # Detailed breakdown by type
    print("\n📋 Detailed Breakdown:\n")

    for issue_type, label in type_labels.items():
        type_issues = [i for i in issues if i['type'] == issue_type]
        if not type_issues:
            continue

        print(f"\n{label} ({len(type_issues)} issues):")

        # Group by file
        by_file = defaultdict(list)
        for issue in type_issues:
            by_file[issue['file']].append(issue)

        # Show top 10 files for this type
        top_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        for file_path, file_issues in top_files:
            print(f"\n  📄 {file_path} ({len(file_issues)} issues)")
            for issue in sorted(file_issues, key=lambda x: x['line'])[:5]:  # Show max 5 per file
                print(f"     Line {issue['line']:4d}: {issue['message']} ({issue['confidence']}%)")
            if len(file_issues) > 5:
                print(f"     ... and {len(file_issues) - 5} more")

    print("\n" + "=" * 80)
    print("🎯 Recommendations:")
    print("   1. Review high-confidence issues (90-100%) first")
    print("   2. Unused imports can usually be safely removed")
    print("   3. Unused functions/classes may be:")
    print("      - Truly dead code (safe to remove)")
    print("      - Public API (keep for backwards compatibility)")
    print("      - Future functionality (document and keep)")
    print("   4. Check unreachable code carefully (may indicate logic errors)")
    print("=" * 80)


def save_detailed_report(
    issues: List[Dict],
    analysis: Dict,
    output_file: str,
    min_confidence: int
):
    """Save detailed report to file."""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DEAD CODE & UNUSED SYMBOLS - DETAILED REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Minimum Confidence Threshold: {min_confidence}%\n")
        f.write(f"Total Issues Found: {analysis['total_issues']}\n")
        f.write(f"Files Affected: {len(analysis['by_file'])}\n\n")

        # All issues grouped by file
        f.write("=" * 80 + "\n")
        f.write("ISSUES BY FILE\n")
        f.write("=" * 80 + "\n\n")

        for file_path, file_issues in sorted(analysis['by_file'].items()):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"📄 {file_path}\n")
            f.write(f"   Total issues: {len(file_issues)}\n")
            f.write(f"{'=' * 80}\n\n")

            for issue in sorted(file_issues, key=lambda x: x['line']):
                f.write(f"Line {issue['line']:5d} | {issue['type']:20s} | "
                       f"Confidence: {issue['confidence']:3d}%\n")
                f.write(f"           | {issue['message']}\n\n")


def main():
    parser = argparse.ArgumentParser(description='Audit unused code in Python codebase')
    parser.add_argument('--min-confidence', type=int, default=80,
                       help='Minimum confidence threshold (0-100, default: 80)')

    args = parser.parse_args()

    if not 0 <= args.min_confidence <= 100:
        print("❌ Confidence must be between 0 and 100")
        sys.exit(1)

    # Check/install vulture
    if not check_vulture_installed():
        print("⚠️  Vulture not found")
        if not install_vulture():
            print("\n❌ Failed to install vulture. Please install manually:")
            print("   pip install vulture")
            sys.exit(1)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    exclude_dirs = {
        'venv', '__pycache__', '.git', 'node_modules',
        '.pytest_cache', 'htmlcov', 'dist', 'build',
        '.mypy_cache', '.ruff_cache', 'alembic', 'implementation'
    }

    # Run scan
    issues = run_vulture_scan(project_root, args.min_confidence, exclude_dirs)

    # Analyze
    analysis = analyze_issues(issues)

    # Print report
    print_audit_report(issues, analysis, args.min_confidence)

    # Save detailed report
    docs_dir = os.path.join(project_root, 'docs', 'audit')
    os.makedirs(docs_dir, exist_ok=True)

    report_file = os.path.join(docs_dir, 'unused_code_detailed_report.txt')
    save_detailed_report(issues, analysis, report_file, args.min_confidence)
    print(f"\n📝 Detailed report saved to: {os.path.relpath(report_file, project_root)}")

    # Return data for documentation script
    return {
        'issues': issues,
        'analysis': analysis,
        'min_confidence': args.min_confidence
    }


if __name__ == '__main__':
    main()
