#!/usr/bin/env python3
"""
Endpoint Inventory Script
Scans the FastAPI codebase and extracts all API endpoints.

Usage:
    python tools/endpoint_inventory.py --format json > docs/API_ENDPOINTS.json
    python tools/endpoint_inventory.py --format markdown > docs/API_ENDPOINTS.md
"""

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, asdict


@dataclass
class Endpoint:
    """API endpoint metadata"""
    path: str
    method: str
    function_name: str
    file_path: str
    domain: str
    has_test: bool = False
    test_file: str = ""


class EndpointScanner:
    """Scans FastAPI router files for endpoint definitions"""

    def __init__(self, api_dir: Path):
        self.api_dir = api_dir
        self.endpoints: List[Endpoint] = []
        self.http_methods = {"get", "post", "put", "patch", "delete"}

    def scan(self) -> List[Endpoint]:
        """Scan all Python files in api directory"""
        python_files = list(self.api_dir.rglob("*.py"))

        for file_path in python_files:
            if "__pycache__" in str(file_path) or file_path.name == "__init__.py":
                continue

            self._scan_file(file_path)

        return self.endpoints

    def _scan_file(self, file_path: Path):
        """Extract endpoints from a single file"""
        try:
            content = file_path.read_text()

            # Regex pattern for @router.METHOD("/path")
            pattern = r'@router\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']'
            matches = re.finditer(pattern, content)

            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)

                # Extract domain from file path
                domain = self._extract_domain(file_path)

                # Find function name (next line after decorator)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if f'@router.{match.group(1)}' in line and f'"{path}"' in line:
                        # Function definition is typically on the next line
                        if i + 1 < len(lines):
                            func_match = re.search(r'def\s+(\w+)', lines[i + 1])
                            if func_match:
                                function_name = func_match.group(1)
                                break
                        else:
                            function_name = "unknown"
                else:
                    function_name = "unknown"

                try:
                    relative_path = str(file_path.relative_to(Path.cwd()))
                except ValueError:
                    # Path is not relative to cwd, use absolute path
                    relative_path = str(file_path)

                endpoint = Endpoint(
                    path=path,
                    method=method,
                    function_name=function_name,
                    file_path=relative_path,
                    domain=domain
                )

                self.endpoints.append(endpoint)

        except Exception as e:
            import sys
            print(f"Error scanning {file_path}: {e}", file=sys.stderr)

    def _extract_domain(self, file_path: Path) -> str:
        """Extract domain name from file path"""
        # Example: app/api/api_v1/endpoints/tournaments/create.py -> tournaments
        parts = file_path.parts

        # Find 'endpoints' in path
        if 'endpoints' in parts:
            idx = parts.index('endpoints')
            if idx + 1 < len(parts):
                # If there's a subdirectory, that's the domain
                if parts[idx + 1].endswith('.py'):
                    # Single file domain (e.g., auth.py)
                    return parts[idx + 1].replace('.py', '')
                else:
                    # Multi-file domain (e.g., tournaments/create.py)
                    return parts[idx + 1]

        # Fallback: use filename
        return file_path.stem


class TestCoverageAnalyzer:
    """Analyzes test coverage for endpoints"""

    def __init__(self, test_dirs: List[Path]):
        self.test_dirs = test_dirs
        self.test_files: Set[str] = set()
        self._scan_test_files()

    def _scan_test_files(self):
        """Find all test files"""
        for test_dir in self.test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("test_*.py"):
                    self.test_files.add(test_file.stem)

    def check_coverage(self, endpoints: List[Endpoint]) -> List[Endpoint]:
        """Check if each endpoint has a corresponding test"""
        for endpoint in endpoints:
            # Heuristic: Check if domain has a test file
            domain_test_name = f"test_{endpoint.domain}"

            if domain_test_name in self.test_files:
                endpoint.has_test = True
                endpoint.test_file = f"{domain_test_name}.py"

        return endpoints


def generate_json_report(endpoints: List[Endpoint]) -> str:
    """Generate JSON report"""
    return json.dumps([asdict(e) for e in endpoints], indent=2)


def generate_markdown_report(endpoints: List[Endpoint]) -> str:
    """Generate Markdown report"""
    # Group by domain
    by_domain: Dict[str, List[Endpoint]] = {}
    for endpoint in endpoints:
        if endpoint.domain not in by_domain:
            by_domain[endpoint.domain] = []
        by_domain[endpoint.domain].append(endpoint)

    # Calculate statistics
    total_endpoints = len(endpoints)
    tested_endpoints = sum(1 for e in endpoints if e.has_test)
    coverage_pct = (tested_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0

    # Build markdown
    lines = [
        "# API Endpoint Inventory",
        "",
        f"**Generated:** {Path(__file__).name}",
        "",
        "## Summary",
        "",
        f"- **Total Endpoints:** {total_endpoints}",
        f"- **Tested Endpoints:** {tested_endpoints}",
        f"- **Coverage:** {coverage_pct:.1f}%",
        f"- **Domains:** {len(by_domain)}",
        "",
        "## Coverage by Domain",
        "",
        "| Domain | Endpoints | Tested | Coverage |",
        "|--------|-----------|--------|----------|",
    ]

    for domain in sorted(by_domain.keys()):
        eps = by_domain[domain]
        tested = sum(1 for e in eps if e.has_test)
        domain_coverage = (tested / len(eps) * 100) if eps else 0

        lines.append(
            f"| {domain} | {len(eps)} | {tested} | {domain_coverage:.0f}% |"
        )

    lines.extend([
        "",
        "## All Endpoints",
        "",
        "| Method | Path | Function | File | Domain | Tested |",
        "|--------|------|----------|------|--------|--------|",
    ])

    for endpoint in sorted(endpoints, key=lambda e: (e.domain, e.path)):
        tested_icon = "✅" if endpoint.has_test else "❌"
        lines.append(
            f"| {endpoint.method} | `{endpoint.path}` | `{endpoint.function_name}` | "
            f"`{endpoint.file_path}` | {endpoint.domain} | {tested_icon} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="API Endpoint Inventory Scanner")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format"
    )
    parser.add_argument(
        "--api-dir",
        type=Path,
        default=Path("app/api"),
        help="API directory to scan"
    )
    parser.add_argument(
        "--test-dirs",
        nargs="+",
        type=Path,
        default=[Path("tests"), Path("app/tests"), Path("tests_e2e")],
        help="Test directories to check coverage"
    )

    args = parser.parse_args()

    # Scan endpoints
    scanner = EndpointScanner(args.api_dir)
    endpoints = scanner.scan()

    # Check test coverage
    analyzer = TestCoverageAnalyzer(args.test_dirs)
    endpoints = analyzer.check_coverage(endpoints)

    # Generate report
    if args.format == "json":
        print(generate_json_report(endpoints))
    else:
        print(generate_markdown_report(endpoints))


if __name__ == "__main__":
    main()
