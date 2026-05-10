"""
Backfill legacy nationality values in the users table to ISO 3166-1 alpha-2 codes.

Usage:
    python scripts/backfill_nationality.py           # audit mode (read-only)
    python scripts/backfill_nationality.py --apply   # write changes to DB
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.utils.country_codes import COUNTRY_CODES, LEGACY_NATIONALITY_MAP


def audit(db):
    rows = db.query(User.nationality).filter(User.nationality.isnot(None)).all()
    values: dict[str, int] = {}
    for (nat,) in rows:
        values[nat] = values.get(nat, 0) + 1

    mappable = {}
    already_ok = {}
    manual_review = {}

    for val, count in sorted(values.items(), key=lambda x: -x[1]):
        if val in COUNTRY_CODES:
            already_ok[val] = count
        elif val in LEGACY_NATIONALITY_MAP:
            mappable[val] = (LEGACY_NATIONALITY_MAP[val], count)
        else:
            manual_review[val] = count

    return already_ok, mappable, manual_review


def print_report(already_ok, mappable, manual_review):
    print("\n=== Nationality Backfill Audit ===\n")

    print(f"Already valid ISO codes ({len(already_ok)} distinct values):")
    for val, count in sorted(already_ok.items()):
        print(f"  {val:5s}  {count} row(s)  — no change needed")

    print(f"\nMappable legacy values ({len(mappable)} distinct values):")
    for val, (target, count) in sorted(mappable.items()):
        print(f"  '{val}'  →  '{target}'  ({count} row(s))")

    print(f"\nManual review required ({len(manual_review)} distinct values):")
    if manual_review:
        for val, count in sorted(manual_review.items()):
            print(f"  '{val}'  ({count} row(s))")
    else:
        print("  (none)")

    total_mappable = sum(c for _, c in mappable.values())
    print(f"\nSummary: {total_mappable} row(s) will be updated on --apply.\n")


def apply_backfill(db, mappable):
    total = 0
    for legacy_val, (iso_code, _) in mappable.items():
        updated = (
            db.query(User)
            .filter(User.nationality == legacy_val)
            .update({"nationality": iso_code}, synchronize_session=False)
        )
        total += updated
        print(f"  '{legacy_val}' → '{iso_code}': {updated} row(s) updated")
    db.commit()
    print(f"\nDone. {total} row(s) updated.")


def main():
    parser = argparse.ArgumentParser(description="Backfill legacy nationality values to ISO alpha-2.")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        already_ok, mappable, manual_review = audit(db)
        print_report(already_ok, mappable, manual_review)

        if args.apply:
            if not mappable:
                print("Nothing to update.")
                return
            print("Applying backfill...")
            apply_backfill(db, mappable)
        else:
            print("Dry run. Pass --apply to write changes.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
