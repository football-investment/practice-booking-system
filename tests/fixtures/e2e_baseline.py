"""
E2E baseline data — single source of truth for CI test environment credentials.

This module is imported by:
  - scripts/init_e2e_environment.py  (CI seed step)
  - .github/workflows/cypress-tests.yml  (Cypress env vars must mirror USERS)
  - .github/workflows/e2e-health-check.yml  (health verification)

When updating credentials here, also update the workflow env vars for Cypress.
"""

from app.models.user import UserRole

# ── Named constants (for direct import in tests / fixtures) ───────────────────

ADMIN_EMAIL    = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

INSTRUCTOR_EMAIL    = "grandmaster@lfa.com"
INSTRUCTOR_PASSWORD = "TestInstructor2026"

STUDENT_EMAIL    = "rdias@manchestercity.com"
STUDENT_PASSWORD = "TestPlayer2026"

SEMESTER_CODE = "E2E-CI-2026"
SEMESTER_NAME = "E2E CI Test Semester"

# ── Structured lists (used by init_e2e_environment.py seed logic) ─────────────

USERS = [
    {
        "email":    ADMIN_EMAIL,
        "name":     "LFA Admin",
        "password": ADMIN_PASSWORD,
        "role":     UserRole.ADMIN,
    },
    {
        "email":    INSTRUCTOR_EMAIL,
        "name":     "Grand Master",
        "password": INSTRUCTOR_PASSWORD,
        "role":     UserRole.INSTRUCTOR,
    },
    {
        "email":    STUDENT_EMAIL,
        "name":     "Ruben Dias",
        "password": STUDENT_PASSWORD,
        "role":     UserRole.STUDENT,
    },
]

SEMESTERS = [
    {
        "code": SEMESTER_CODE,
        "name": SEMESTER_NAME,
        # start/end derived at runtime (today ± 180 days) — see init_e2e_environment.py
    },
]


def credentials(role: UserRole) -> tuple[str, str]:
    """Return (email, password) for the baseline account with the given role."""
    for user in USERS:
        if user["role"] == role:
            return user["email"], user["password"]
    raise KeyError(f"No baseline user with role {role}")
