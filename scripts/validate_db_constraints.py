"""
validate_db_constraints.py — Runtime DB constraint verification.

Connects to the database (DATABASE_URL env var) and verifies:
  1. uq_user_license_spec unique constraint exists on user_licenses
  2. No duplicate (user_id, specialization_type) pairs exist in user_licenses

Intended to run after `alembic upgrade head` in CI (migration-integrity job)
to catch constraint regressions early.

Usage:
    DATABASE_URL=postgresql://... python scripts/validate_db_constraints.py
    DATABASE_URL=postgresql://... python scripts/validate_db_constraints.py --exit-code
"""

import argparse
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print(
        "ERROR: psycopg2 not installed. Add psycopg2-binary to requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

SEP = "=" * 70


def check_unique_constraint(cur) -> tuple[bool, str]:
    """Verify uq_user_license_spec exists on user_licenses."""
    cur.execute(
        """
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'user_licenses'::regclass
          AND contype  = 'u'
          AND conname  = 'uq_user_license_spec'
        """
    )
    row = cur.fetchone()
    if row:
        return True, "uq_user_license_spec found on user_licenses"
    return (
        False,
        "uq_user_license_spec MISSING from user_licenses — "
        "run migration 2026_03_20_1000",
    )


def check_no_duplicates(cur) -> tuple[bool, str]:
    """Verify no duplicate (user_id, specialization_type) pairs."""
    cur.execute(
        """
        SELECT user_id, specialization_type, COUNT(*) AS cnt
        FROM user_licenses
        GROUP BY user_id, specialization_type
        HAVING COUNT(*) > 1
        """
    )
    rows = cur.fetchall()
    if not rows:
        return True, "No duplicate (user_id, specialization_type) pairs"
    details = "; ".join(
        f"user_id={r['user_id']} spec={r['specialization_type']} n={r['cnt']}"
        for r in rows
    )
    return False, f"Duplicate license pairs found — {details}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify DB constraints for the credit / license system."
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with non-zero status if any check fails",
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set", file=sys.stderr)
        return 2

    try:
        conn = psycopg2.connect(database_url)
    except Exception as exc:
        print(f"ERROR: Cannot connect to database: {exc}", file=sys.stderr)
        return 2

    results: list[tuple[bool, str]] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            results.append(check_unique_constraint(cur))
            results.append(check_no_duplicates(cur))
    finally:
        conn.close()

    print(f"\n{SEP}")
    print("DB CONSTRAINT VALIDATION")
    print(SEP)
    for ok, msg in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {msg}")

    all_ok = all(ok for ok, _ in results)
    print(f"\n{SEP}")
    if all_ok:
        print("✅  All DB constraint checks passed.")
        return 0

    print("❌  DB constraint checks FAILED.")
    print("    Ensure alembic upgrade head ran successfully and no duplicate")
    print("    (user_id, specialization_type) rows exist in user_licenses.")
    return 1 if args.exit_code else 0


if __name__ == "__main__":
    sys.exit(main())
