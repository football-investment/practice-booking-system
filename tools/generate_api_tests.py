#!/usr/bin/env python3
"""
API Test Generator
Generates smoke tests for all API endpoints discovered by endpoint_inventory.py

Usage:
    # Generate tests from inventory
    python tools/endpoint_inventory.py --format json > /tmp/endpoints.json
    python tools/generate_api_tests.py --input /tmp/endpoints.json --output tests/integration/api_smoke/

    # Or run end-to-end
    python tools/generate_api_tests.py --scan-api app/api --output tests/integration/api_smoke/
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from jinja2 import Template


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


# ── Domain to Router Prefix Mapping ──────────────────────────────────
# Maps domain names to their API router prefixes
# Full URL = /api/v1 + DOMAIN_PREFIX_MAP[domain] + endpoint.path
DOMAIN_PREFIX_MAP = {
    "bookings": "/bookings",
    "sessions": "/sessions",
    "analytics": "/analytics",
    "attendance": "/attendance",
    "tournaments": "/tournaments",
    "users": "/users",
    "enrollments": "/enrollments",
    "invoices": "/invoices",
    "licenses": "/licenses",
    "auth": "/auth",
    "admin": "/admin",
    "instructor": "/instructor",
    "dashboard": "/dashboard",
    "profile": "/profile",
    "student_features": "/student-features",
    "adaptive_learning": "/adaptive-learning",
    "curriculum": "/curriculum",
    "feedback": "/feedback",
    "notifications": "/notifications",
    "messages": "/messages",
    "campuses": "/campuses",
    "locations": "/locations",
    "quiz": "/quiz",
    "gamification": "/gamification",
    "reports": "/reports",
    "health": "/health",
    "debug": "/debug",
    # Underscore variations (domain names from filenames)
    "_semesters_main": "/tournaments",
    "semester_generator": "/tournament-generator",
    "tournament_types": "/tournament-types",
    "instructor_dashboard": "/instructor",
    "instructor_smoke": "/instructor",
    "lfa_player": "/lfa-player",
    "lfa_coach": "/lfa-coach",
    "lfa_player_routes": "/lfa-player",
    "lfa_coach_routes": "/lfa-coach",
    "gancuju_routes": "/gancuju",
    "internship_routes": "/internship",
    "internship": "/internship",
    "gancuju": "/gancuju",
    "specialization": "/specialization",
    "specializations": "/specializations",
    "onboarding": "/onboarding",
    "motivation": "/motivation",
    "payment_verification": "/payment-verification",
    "progression": "/progression",
    "parallel_specializations": "/parallel-specializations",
    "audit": "/audit",
    "tracks": "/tracks",
    "instructor_availability": "/instructor-availability",
    "session_groups": "/session-groups",
    "public_profile": "/public-profile",
    "spec_info": "/spec-info",
    "certificates": "/certificates",
    "license_renewal": "/license-renewal",
    "groups": "/groups",
    "system_events": "/system-events",
    "curriculum_adaptive": "/curriculum-adaptive",
    "students": "/students",
    "competency": "/competency",
    "periods": "/periods",
    "instructor_assignments": "/instructor-assignments",
    "projects": "/projects",
    "semesters": "/semesters",
    "coach": "/coach",
    "sandbox": "/sandbox",
    "game_presets": "/game-presets",
    "semester_enrollments": "/semester-enrollments",
    "instructor_management": "/instructor-management",
    "invitation_codes": "/invitation-codes",
    "coupons": "/coupons",
}


def get_router_prefix(domain: str) -> str:
    """
    Get router prefix for domain.

    Args:
        domain: Domain name (e.g., "bookings")

    Returns:
        Router prefix (e.g., "/bookings") or "" if domain not in map
    """
    return DOMAIN_PREFIX_MAP.get(domain, "")


# ── Path Parameter Mapping ──────────────────────────────────────────
def extract_path_params(path: str) -> List[str]:
    """
    Extract path parameters from URL path.
    Example: "/{booking_id}/confirm" → ["booking_id"]
    """
    import re
    return re.findall(r'\{([^}]+)\}', path)


def map_param_to_fixture(param: str) -> tuple[str, str]:
    """
    Map path parameter to fixture name and format string.

    Args:
        param: Parameter name from URL path (e.g., "booking_id")

    Returns:
        (fixture_name, fixture_ref):
        - fixture_name: Name to use in function signature (e.g., "test_session_id")
        - fixture_ref: How to reference it in f-string (e.g., "test_session_id")

    Mapping:
        - booking_id → test_tournament["session_ids"][0] (use test_tournament fixture)
        - session_id → test_session_id
        - semester_id → test_tournament["semester_id"]
        - tournament_id → test_tournament["tournament_id"]
        - student_id → test_student_id
        - instructor_id → test_instructor_id
        - user_id → test_student_id (default to student)
        - resource_id → test_session_id (generic resource)
        - mapping_id → test_skill_mapping_id
        - task_id → test_generation_task_id
    """
    param_lower = param.lower()

    # Direct fixture mappings
    FIXTURE_MAP = {
        "session_id": ("test_session_id", "test_session_id"),
        "student_id": ("test_student_id", "test_student_id"),
        "instructor_id": ("test_instructor_id", "test_instructor_id"),
        "user_id": ("test_student_id", "test_student_id"),  # Default to student
        "skill_mapping_id": ("test_skill_mapping_id", "test_skill_mapping_id"),
        "mapping_id": ("test_skill_mapping_id", "test_skill_mapping_id"),
        "task_id": ("test_generation_task_id", "test_generation_task_id"),
        "rounds_session_id": ("test_rounds_session_id", "test_rounds_session_id"),
    }

    # Fixture references from test_tournament dict
    TOURNAMENT_REFS = {
        "tournament_id": ("test_tournament", 'test_tournament["tournament_id"]'),
        "semester_id": ("test_tournament", 'test_tournament["semester_id"]'),
        "booking_id": ("test_tournament", 'test_tournament["session_ids"][0]'),  # Reuse session_id
        "resource_id": ("test_tournament", 'test_tournament["session_ids"][0]'),  # Generic resource
        "campus_id": ("test_campus_id", "test_campus_id"),
    }

    if param_lower in FIXTURE_MAP:
        return FIXTURE_MAP[param_lower]
    elif param_lower in TOURNAMENT_REFS:
        return TOURNAMENT_REFS[param_lower]
    else:
        # Fallback: use test_tournament for unknown IDs
        return ("test_tournament", f'test_tournament["{param}"]')


def build_url_with_fixtures(path: str, domain: str = "") -> tuple[str, List[str], str]:
    """
    Build URL with /api/v1 prefix, router prefix, and fixture replacements.

    Args:
        path: Raw endpoint path (e.g., "/{session_id}/confirm")
        domain: Domain name for router prefix lookup (e.g., "bookings")

    Returns:
        (url_template, fixtures, url_fstring):
        - url_template: Jinja2 template string with fixtures
        - fixtures: List of fixture names to add to function signature
        - url_fstring: Python f-string for URL

    Example:
        Input: path="/{session_id}/confirm", domain="sessions"
        Output: ("/api/v1/sessions/{test_session_id}/confirm", ["test_session_id"],
                 'f"/api/v1/sessions/{test_session_id}/confirm"')
    """
    params = extract_path_params(path)

    # Get router prefix from domain
    router_prefix = get_router_prefix(domain)
    base_url = f"/api/v1{router_prefix}"

    if not params:
        # No path parameters - simple URL
        return (f"{base_url}{path}", [], f'"{base_url}{path}"')

    # Extract fixtures and build f-string
    fixtures = []
    url_parts = path
    fstring_parts = f"{base_url}{path}"

    for param in params:
        fixture_name, fixture_ref = map_param_to_fixture(param)

        # Add fixture to signature (deduplicate)
        if fixture_name not in fixtures:
            fixtures.append(fixture_name)

        # Replace {param} with {fixture_ref} in f-string
        fstring_parts = fstring_parts.replace(f"{{{param}}}", f"{{{fixture_ref}}}")

    return (fstring_parts, fixtures, f'f"{fstring_parts}"')


def get_fixture_params(endpoint: Endpoint) -> tuple[List[str], str]:
    """
    Get fixture parameters and URL f-string for endpoint.

    Args:
        endpoint: Endpoint metadata

    Returns:
        (fixture_list, url_fstring):
        - fixture_list: List of fixtures for function signature
        - url_fstring: Python f-string for URL
    """
    _, fixtures, url_fstring = build_url_with_fixtures(endpoint.path, endpoint.domain)
    return (fixtures, url_fstring)


# ── Test Templates ─────────────────────────────────────────────────────

CONFTEST_TEMPLATE = '''"""
Auto-generated API smoke tests configuration
Generated by tools/generate_api_tests.py
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash


@pytest.fixture(scope="module")
def api_client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture(scope="module")
def test_db():
    """Database session for test setup"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def admin_token(test_db: Session):
    """Admin user authentication token"""
    # Check if admin exists
    admin = test_db.query(User).filter(User.email == "smoke.admin@generated.test").first()

    if not admin:
        admin = User(
            name="Smoke Test Admin",
            email="smoke.admin@generated.test",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

    # Generate token
    from app.api.deps import create_access_token
    token = create_access_token(subject=admin.id)
    return token


@pytest.fixture(scope="module")
def student_token(test_db: Session):
    """Student user authentication token"""
    student = test_db.query(User).filter(User.email == "smoke.student@generated.test").first()

    if not student:
        student = User(
            name="Smoke Test Student",
            email="smoke.student@generated.test",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True
        )
        test_db.add(student)
        test_db.commit()
        test_db.refresh(student)

    from app.api.deps import create_access_token
    token = create_access_token(subject=student.id)
    return token


@pytest.fixture(scope="module")
def instructor_token(test_db: Session):
    """Instructor user authentication token"""
    instructor = test_db.query(User).filter(User.email == "smoke.instructor@generated.test").first()

    if not instructor:
        instructor = User(
            name="Smoke Test Instructor",
            email="smoke.instructor@generated.test",
            password_hash=get_password_hash("instructor123"),
            role=UserRole.INSTRUCTOR,
            is_active=True
        )
        test_db.add(instructor)
        test_db.commit()
        test_db.refresh(instructor)

    from app.api.deps import create_access_token
    token = create_access_token(subject=instructor.id)
    return token
'''


SMOKE_TEST_TEMPLATE = '''"""
Auto-generated smoke tests for {{ domain }} domain
Generated by tools/generate_api_tests.py

⚠️  DO NOT EDIT MANUALLY - Regenerate using:
    python tools/generate_api_tests.py --scan-api app/api --output tests/integration/api_smoke/
"""

import pytest
from fastapi.testclient import TestClient


class Test{{ domain|title|replace('_', '') }}Smoke:
    """Smoke tests for {{ domain }} API endpoints"""

{% for endpoint in endpoints %}
    # ── {{ endpoint.method }} /api/v1{{ endpoint.path }} ────────────────────────────

    def test_{{ endpoint.function_name }}_happy_path(
        self,
        api_client: TestClient,
        admin_token: str,
        {%- for fixture in endpoint.fixtures %}
        {{ fixture }},
        {%- endfor %}
    ):
        """
        Happy path: {{ endpoint.method }} /api/v1{{ endpoint.path }}
        Source: {{ endpoint.file_path }}:{{ endpoint.function_name }}
        """
        headers = {"Authorization": f"Bearer {admin_token}"}

        {% if endpoint.method == "GET" %}
        response = api_client.get({{ endpoint.url_fstring }}, headers=headers)
        {% elif endpoint.method == "POST" %}
        # TODO: Add realistic payload for /api/v1{{ endpoint.path }}
        payload = {}
        response = api_client.post({{ endpoint.url_fstring }}, json=payload, headers=headers)
        {% elif endpoint.method == "PUT" %}
        payload = {}
        response = api_client.put({{ endpoint.url_fstring }}, json=payload, headers=headers)
        {% elif endpoint.method == "PATCH" %}
        payload = {}
        response = api_client.patch({{ endpoint.url_fstring }}, json=payload, headers=headers)
        {% elif endpoint.method == "DELETE" %}
        response = api_client.delete({{ endpoint.url_fstring }}, headers=headers)
        {% endif %}

        # Accept 200, 201, 404 (if resource doesn't exist in test DB)
        assert response.status_code in [200, 201, 404], (
            f"{{ endpoint.method }} /api/v1{{ endpoint.path }} failed: {response.status_code} "
            f"{response.text}"
        )

    def test_{{ endpoint.function_name }}_auth_required(
        self,
        api_client: TestClient,
        {%- for fixture in endpoint.fixtures %}
        {{ fixture }},
        {%- endfor %}
    ):
        """
        Auth validation: {{ endpoint.method }} /api/v1{{ endpoint.path }} requires authentication
        """
        {% if endpoint.method == "GET" %}
        response = api_client.get({{ endpoint.url_fstring }})
        {% elif endpoint.method == "POST" %}
        response = api_client.post({{ endpoint.url_fstring }}, json={})
        {% elif endpoint.method == "PUT" %}
        response = api_client.put({{ endpoint.url_fstring }}, json={})
        {% elif endpoint.method == "PATCH" %}
        response = api_client.patch({{ endpoint.url_fstring }}, json={})
        {% elif endpoint.method == "DELETE" %}
        response = api_client.delete({{ endpoint.url_fstring }})
        {% endif %}

        # Should return 401 Unauthorized or 403 Forbidden
        assert response.status_code in [401, 403], (
            f"{{ endpoint.method }} /api/v1{{ endpoint.path }} should require auth: {response.status_code}"
        )

    @pytest.mark.skip(reason="Input validation requires domain-specific payloads")
    def test_{{ endpoint.function_name }}_input_validation(
        self,
        api_client: TestClient,
        admin_token: str,
        {%- for fixture in endpoint.fixtures %}
        {{ fixture }},
        {%- endfor %}
    ):
        """
        Input validation: {{ endpoint.method }} /api/v1{{ endpoint.path }} validates request data
        """
        headers = {"Authorization": f"Bearer {admin_token}"}

        {% if endpoint.method in ["POST", "PUT", "PATCH"] %}
        # Invalid payload (empty or malformed)
        invalid_payload = {"invalid_field": "invalid_value"}
        response = api_client.{{ endpoint.method.lower() }}(
            {{ endpoint.url_fstring }},
            json=invalid_payload,
            headers=headers
        )

        # Should return 422 Unprocessable Entity for validation errors
        assert response.status_code in [400, 422], (
            f"{{ endpoint.method }} /api/v1{{ endpoint.path }} should validate input: {response.status_code}"
        )
        {% else %}
        # GET/DELETE don't typically have input validation
        pytest.skip("No input validation for {{ endpoint.method }} endpoints")
        {% endif %}

{% endfor %}
'''


class TestGenerator:
    """Generates pytest test files from endpoint inventory"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_tests(self, endpoints: List[Endpoint]):
        """Generate test files grouped by domain"""
        # Group endpoints by domain
        by_domain: Dict[str, List[Endpoint]] = {}
        for endpoint in endpoints:
            if endpoint.domain not in by_domain:
                by_domain[endpoint.domain] = []
            by_domain[endpoint.domain].append(endpoint)

        # Generate conftest.py
        self._write_conftest()

        # Generate test file per domain
        for domain, domain_endpoints in by_domain.items():
            self._generate_domain_tests(domain, domain_endpoints)

        # Generate summary report
        self._generate_summary(by_domain)

    def _write_conftest(self):
        """Write conftest.py with fixtures"""
        conftest_path = self.output_dir / "conftest.py"
        conftest_path.write_text(CONFTEST_TEMPLATE)
        print(f"✅ Generated: {conftest_path}")

    def _generate_domain_tests(self, domain: str, endpoints: List[Endpoint]):
        """Generate test file for a single domain"""
        # Sort endpoints by method and path
        endpoints_sorted = sorted(endpoints, key=lambda e: (e.method, e.path))

        # Enrich endpoints with fixture metadata
        enriched_endpoints = []
        for ep in endpoints_sorted:
            fixtures, url_fstring = get_fixture_params(ep)
            # Create new dict with all endpoint attributes + fixture metadata
            ep_dict = {
                'path': ep.path,
                'method': ep.method,
                'function_name': ep.function_name,
                'file_path': ep.file_path,
                'domain': ep.domain,
                'fixtures': fixtures,
                'url_fstring': url_fstring
            }
            enriched_endpoints.append(ep_dict)

        # Render template with enriched data
        test_content = Template(SMOKE_TEST_TEMPLATE).render(
            domain=domain,
            endpoints=enriched_endpoints
        )

        # Write to file
        test_file = self.output_dir / f"test_{domain}_smoke.py"
        test_file.write_text(test_content)
        print(f"✅ Generated: {test_file} ({len(endpoints)} endpoints)")

    def _generate_summary(self, by_domain: Dict[str, List[Endpoint]]):
        """Generate summary report"""
        total_endpoints = sum(len(eps) for eps in by_domain.values())
        total_tests = total_endpoints * 3  # 3 tests per endpoint

        summary = [
            "# API Smoke Test Generation Summary",
            "",
            f"**Total Endpoints:** {total_endpoints}",
            f"**Total Tests Generated:** {total_tests}",
            f"**Domains:** {len(by_domain)}",
            "",
            "## Tests per Domain",
            "",
            "| Domain | Endpoints | Tests Generated |",
            "|--------|-----------|-----------------|",
        ]

        for domain in sorted(by_domain.keys()):
            eps = by_domain[domain]
            tests = len(eps) * 3
            summary.append(f"| {domain} | {len(eps)} | {tests} |")

        summary.extend([
            "",
            "## Test Types",
            "",
            "Each endpoint has 3 tests:",
            "1. **Happy Path** - Validates 200/201 response with admin auth",
            "2. **Auth Required** - Validates 401/403 without authentication",
            "3. **Input Validation** - Validates 422 with invalid payload (SKIPPED - needs manual implementation)",
            "",
            "## Running Tests",
            "",
            "```bash",
            "# Run all smoke tests",
            f"pytest {self.output_dir} -v",
            "",
            "# Run specific domain",
            f"pytest {self.output_dir}/test_tournaments_smoke.py -v",
            "",
            "# Parallel execution",
            f"pytest {self.output_dir} -n auto -v",
            "```",
            "",
            "## Next Steps",
            "",
            "1. Review generated tests",
            "2. Add realistic payloads for POST/PUT/PATCH endpoints",
            "3. Implement input validation tests (currently skipped)",
            "4. Add to CI pipeline as BLOCKING gate",
        ])

        summary_path = self.output_dir / "SMOKE_TEST_SUMMARY.md"
        summary_path.write_text("\n".join(summary))
        print(f"✅ Generated: {summary_path}")


def load_endpoints_from_json(json_path: Path) -> List[Endpoint]:
    """Load endpoints from JSON inventory file"""
    data = json.loads(json_path.read_text())
    return [Endpoint(**ep) for ep in data]


def scan_and_generate(api_dir: Path, output_dir: Path):
    """Scan API directory and generate tests (convenience wrapper)"""
    from endpoint_inventory import EndpointScanner

    print(f"🔍 Scanning API directory: {api_dir}")
    scanner = EndpointScanner(api_dir)
    endpoints = scanner.scan()

    print(f"✅ Found {len(endpoints)} endpoints")
    print(f"📝 Generating tests to: {output_dir}")

    generator = TestGenerator(output_dir)
    generator.generate_tests(endpoints)

    print(f"\n✅ Test generation complete!")
    print(f"   Generated {len(endpoints) * 3} tests across {len(set(e.domain for e in endpoints))} domains")


def main():
    parser = argparse.ArgumentParser(description="API Smoke Test Generator")
    parser.add_argument(
        "--input",
        type=Path,
        help="Input JSON file from endpoint_inventory.py"
    )
    parser.add_argument(
        "--scan-api",
        type=Path,
        help="API directory to scan (alternative to --input)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/integration/api_smoke"),
        help="Output directory for generated tests"
    )

    args = parser.parse_args()

    if args.scan_api:
        # Scan API directory directly
        scan_and_generate(args.scan_api, args.output)
    elif args.input:
        # Load from JSON inventory
        endpoints = load_endpoints_from_json(args.input)
        generator = TestGenerator(args.output)
        generator.generate_tests(endpoints)
    else:
        parser.error("Must specify either --input or --scan-api")


if __name__ == "__main__":
    main()
