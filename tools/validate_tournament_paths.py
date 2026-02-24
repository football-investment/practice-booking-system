"""
P0 Tool: Validate Tournament Test Paths Against Actual Routes

Purpose: Identify 404 errors by comparing test paths with actual FastAPI routes
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def load_actual_routes(json_path: str) -> Dict[str, Set[str]]:
    """Load actual routes from JSON, organized by method."""
    with open(json_path) as f:
        routes = json.load(f)

    method_routes = {}
    for route in routes:
        path = route['path'].replace('/api/v1/tournaments', '')  # Normalize to test format
        if not path:
            path = '/'

        for method in route['methods']:
            method = method.lower()
            if method not in method_routes:
                method_routes[method] = set()
            method_routes[method].add(path)

    return method_routes


def extract_test_paths(test_file: str) -> List[Tuple[str, str, int]]:
    """Extract test paths from test file. Returns (method, path, line_number)."""
    test_paths = []

    with open(test_file) as f:
        for line_no, line in enumerate(f, 1):
            # Match patterns like: api_client.get(f"/{test_tournament['tournament_id']}/sessions", headers=...)
            # or: api_client.post("/admin/list", json={})
            match = re.search(r'api_client\.(get|post|put|patch|delete)\((f)?"([^"]+)"', line)
            if match:
                method = match.group(1)
                is_fstring = match.group(2) == 'f'
                path = match.group(3)

                # Normalize f-string paths to parameter format
                if is_fstring:
                    # Replace {test_tournament['tournament_id']} with {tournament_id}
                    path = re.sub(r"\{test_tournament\['tournament_id'\]\}", "{tournament_id}", path)
                    path = re.sub(r"\{test_campus_id\}", "{campus_id}", path)
                    path = re.sub(r"\{test_student_id\}", "{user_id}", path)
                    path = re.sub(r"\{test_instructor_id\}", "{instructor_id}", path)
                    # Handle remaining literal values (session_id, mapping_id, etc.)
                    path = re.sub(r"/\d+", "/{id}", path)  # Replace /1 with /{id}

                test_paths.append((method, path, line_no))

    return test_paths


def normalize_path(path: str) -> str:
    """Normalize path parameters for comparison."""
    # Standardize parameter names
    path = re.sub(r'\{application_id\}', '{id}', path)
    path = re.sub(r'\{request_id\}', '{id}', path)
    path = re.sub(r'\{session_id\}', '{id}', path)
    path = re.sub(r'\{round_number\}', '{id}', path)
    path = re.sub(r'\{mapping_id\}', '{id}', path)
    path = re.sub(r'\{policy_name\}', '{name}', path)
    path = re.sub(r'\{task_id\}', '{id}', path)
    return path


def compare_paths(actual_routes: Dict[str, Set[str]], test_paths: List[Tuple[str, str, int]]) -> Dict:
    """Compare test paths against actual routes."""

    results = {
        'matching': [],
        'missing': [],
        'wrong_method': [],
        'stats': {}
    }

    for method, test_path, line_no in test_paths:
        # Check if route exists for this method
        if method in actual_routes:
            # Exact match
            if test_path in actual_routes[method]:
                results['matching'].append({
                    'method': method.upper(),
                    'path': test_path,
                    'line': line_no,
                    'status': 'OK'
                })
            else:
                # Check if path exists but with different method
                found_in_other_method = False
                for other_method, paths in actual_routes.items():
                    if test_path in paths and other_method != method:
                        results['wrong_method'].append({
                            'method': method.upper(),
                            'path': test_path,
                            'line': line_no,
                            'actual_method': other_method.upper(),
                            'status': 'WRONG_METHOD'
                        })
                        found_in_other_method = True
                        break

                if not found_in_other_method:
                    results['missing'].append({
                        'method': method.upper(),
                        'path': test_path,
                        'line': line_no,
                        'status': 'NOT_FOUND'
                    })
        else:
            results['missing'].append({
                'method': method.upper(),
                'path': test_path,
                'line': line_no,
                'status': 'METHOD_NOT_SUPPORTED'
            })

    # Calculate stats
    total = len(test_paths)
    results['stats'] = {
        'total_tests': total,
        'matching': len(results['matching']),
        'missing': len(results['missing']),
        'wrong_method': len(results['wrong_method']),
        'match_rate': f"{len(results['matching']) / total * 100:.1f}%" if total > 0 else "0%"
    }

    return results


def generate_report(results: Dict) -> str:
    """Generate markdown report."""
    report = []

    report.append("# P0: Tournament Endpoint Path Validation Report")
    report.append("")
    report.append("**Generated:** 2026-02-24")
    report.append("**Goal:** Identify and fix 404 errors (<5 target)")
    report.append("")
    report.append("---")
    report.append("")

    # Stats
    stats = results['stats']
    report.append("## Summary Statistics")
    report.append("")
    report.append(f"- **Total Test Paths:** {stats['total_tests']}")
    report.append(f"- **Matching Routes:** {stats['matching']} ({stats['match_rate']})")
    report.append(f"- **Missing Routes:** {stats['missing']} (404 candidates)")
    report.append(f"- **Wrong Method:** {stats['wrong_method']}")
    report.append("")

    # Status indicator
    if stats['missing'] < 5:
        report.append("✅ **Target Achieved:** <5 missing routes")
    else:
        report.append(f"❌ **Target Not Met:** {stats['missing']} missing routes (target: <5)")

    report.append("")
    report.append("---")
    report.append("")

    # Missing routes
    if results['missing']:
        report.append("## Missing Routes (404 Errors)")
        report.append("")
        report.append("These test paths do NOT match any actual FastAPI route:")
        report.append("")
        report.append("| Method | Path | Line | Action |")
        report.append("|--------|------|------|--------|")

        for item in results['missing']:
            action = "DELETE TEST" if "NOT_SUPPORTED" in item['status'] else "FIX PATH"
            report.append(f"| {item['method']} | `{item['path']}` | {item['line']} | {action} |")

        report.append("")

    # Wrong method
    if results['wrong_method']:
        report.append("## Wrong Method (405 Errors)")
        report.append("")
        report.append("These test paths exist but use wrong HTTP method:")
        report.append("")
        report.append("| Test Method | Path | Line | Actual Method | Action |")
        report.append("|-------------|------|------|---------------|--------|")

        for item in results['wrong_method']:
            report.append(f"| {item['method']} | `{item['path']}` | {item['line']} | {item['actual_method']} | FIX METHOD |")

        report.append("")

    # Matching routes (summary)
    report.append("## Matching Routes")
    report.append("")
    report.append(f"✅ {len(results['matching'])} test paths correctly match actual routes")
    report.append("")

    return "\n".join(report)


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent.parent

    # Paths
    actual_routes_json = "/tmp/actual_tournament_routes.json"
    test_file = root_dir / "tests/integration/api_smoke/test_tournaments_smoke.py"
    output_file = root_dir / "P0_PATH_VALIDATION_REPORT.md"

    print("P0: Validating Tournament Test Paths...")
    print(f"Actual routes: {actual_routes_json}")
    print(f"Test file: {test_file}")

    # Load actual routes
    print("\n1. Loading actual FastAPI routes...")
    actual_routes = load_actual_routes(actual_routes_json)
    total_routes = sum(len(paths) for paths in actual_routes.values())
    print(f"   Found {total_routes} routes across {len(actual_routes)} HTTP methods")

    # Extract test paths
    print("\n2. Extracting test paths...")
    test_paths = extract_test_paths(str(test_file))
    print(f"   Found {len(test_paths)} test endpoint calls")

    # Compare
    print("\n3. Comparing paths...")
    results = compare_paths(actual_routes, test_paths)

    # Generate report
    print("\n4. Generating report...")
    report = generate_report(results)

    # Write report
    output_file.write_text(report)
    print(f"\n✅ Report written: {output_file}")

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total test paths: {results['stats']['total_tests']}")
    print(f"Matching: {results['stats']['matching']} ({results['stats']['match_rate']})")
    print(f"Missing (404): {results['stats']['missing']}")
    print(f"Wrong method (405): {results['stats']['wrong_method']}")

    if results['stats']['missing'] < 5:
        print("\n✅ TARGET ACHIEVED: <5 missing routes")
    else:
        print(f"\n❌ TARGET NOT MET: {results['stats']['missing']} missing routes (target: <5)")

    print("\nNext steps:")
    print("1. Review P0_PATH_VALIDATION_REPORT.md")
    print("2. Fix or delete incorrect test paths")
    print("3. Re-run validation until <5 missing routes")


if __name__ == "__main__":
    main()
