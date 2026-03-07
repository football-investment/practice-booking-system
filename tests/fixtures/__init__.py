"""
tests.fixtures — shared test data layer.

Baseline credentials (pure data, no DB):
    from tests.fixtures import ADMIN_EMAIL, INSTRUCTOR_EMAIL, STUDENT_EMAIL
    from tests.fixtures import credentials  # credentials(UserRole.ADMIN) → (email, pw)

Entity builders (require a DB session, call db.flush()):
    from tests.fixtures import build_semester, build_session, build_project
    from tests.fixtures import build_user_license, build_enrollment, build_tournament

Baseline seeder (idempotent, composes with SAVEPOINT isolation):
    from tests.fixtures import seed_baseline_to_db
    baseline = seed_baseline_to_db(test_db)
    # → {"admin": User, "instructor": User, "student": User, "semester": Semester}
"""

from .e2e_baseline import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    INSTRUCTOR_EMAIL,
    INSTRUCTOR_PASSWORD,
    SEMESTER_CODE,
    SEMESTER_NAME,
    SEMESTERS,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    USERS,
    credentials,
)
from .builders import (
    build_enrollment,
    build_project,
    build_semester,
    build_session,
    build_tournament,
    build_user_license,
    seed_baseline_to_db,
)

__all__ = [
    # ── Baseline credentials ──────────────────────────────────────────────────
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "INSTRUCTOR_EMAIL",
    "INSTRUCTOR_PASSWORD",
    "STUDENT_EMAIL",
    "STUDENT_PASSWORD",
    "SEMESTER_CODE",
    "SEMESTER_NAME",
    "USERS",
    "SEMESTERS",
    "credentials",
    # ── Entity builders ───────────────────────────────────────────────────────
    "build_semester",
    "build_session",
    "build_project",
    "build_user_license",
    "build_enrollment",
    "build_tournament",
    "seed_baseline_to_db",
]
