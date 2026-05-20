#!/usr/bin/env python3
"""Seed Adaptive Learning questions from JSON content files.

Usage:
  python scripts/seed_adaptive_learning_questions.py [--spec SPEC] [--dry-run]

Arguments:
  --spec   Specialization filter, e.g. LFA_FOOTBALL_PLAYER  (default: LFA_FOOTBALL_PLAYER)
  --dry-run  Validate and report without writing to the database

Content is loaded from content/adaptive_learning/ following two-gate filtering:
  Gate 1: folder scan — only files under _shared/ and <spec_slug>/ directories are considered
  Gate 2: field validation — file must list the requested specialization in its "specializations" field

Idempotency: Quiz rows are matched by quiz_title. Existing quizzes are skipped in full.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.quiz import Quiz

# Re-export service symbols so that tests that import from this script still work.
from app.services.al_import_service import (  # noqa: F401
    SPECIALIZATION_CATEGORY_ALLOWLIST,
    VALID_SCHEMA_VERSIONS,
    ValidationError,
    _validate_file,
    _validate_question,
    _validate_question_v2,
    _seed_options_v1,
    _seed_options_v2,
    _seed_quiz,
)

# ── Constants ─────────────────────────────────────────────────────────────────

CONTENT_ROOT = Path(__file__).resolve().parent.parent / "content" / "adaptive_learning"

# Maps specialization token (as used in JSON) → folder slug under content/adaptive_learning/
SPEC_FOLDER_MAP: dict[str, str] = {
    "LFA_FOOTBALL_PLAYER": "lfa_football_player",
    "LFA_FOOTBALL_COACH": "lfa_football_coach",
}


# ── File discovery ─────────────────────────────────────────────────────────────

def _discover_files(spec: str) -> list[Path]:
    """Gate 1: collect JSON files from _shared/ and the spec-specific folder."""
    spec_folder = SPEC_FOLDER_MAP.get(spec)
    if not spec_folder:
        print(f"[ERROR] No folder mapping for spec {spec!r}. Known: {list(SPEC_FOLDER_MAP)}")
        sys.exit(1)

    candidate_dirs = [
        CONTENT_ROOT / "_shared",
        CONTENT_ROOT / spec_folder,
    ]

    files: list[Path] = []
    for d in candidate_dirs:
        if d.exists():
            files.extend(sorted(d.rglob("*.json")))

    return files


# ── Seeding ───────────────────────────────────────────────────────────────────

def _seed_file(db, data: dict[str, Any], path: Path, dry_run: bool) -> dict[str, int]:
    """Seed one quiz file. Returns {"skipped": 1} or {"quizzes": 1, "questions": N}."""
    quiz_title = data["quiz_title"].strip()

    existing = db.query(Quiz).filter(Quiz.title == quiz_title).first()
    if existing:
        return {"skipped": 1, "questions": 0}

    if dry_run:
        return {"dry_run_would_create": 1, "questions": len(data["questions"])}

    counts = _seed_quiz(db, data)
    return {"quizzes": counts["quizzes"], "questions": counts["questions"]}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Adaptive Learning questions from JSON")
    parser.add_argument(
        "--spec",
        default="LFA_FOOTBALL_PLAYER",
        help="Specialization filter (default: LFA_FOOTBALL_PLAYER)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing to the database",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Language filter, e.g. 'hu' or 'en'. If omitted, all languages are included.",
    )
    args = parser.parse_args()
    spec = args.spec.upper()
    dry_run: bool = args.dry_run
    lang_filter: str | None = args.lang.lower() if args.lang else None

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  Adaptive Learning Question Seeder  [{mode}]")
    print(f"  Spec: {spec}")
    if lang_filter:
        print(f"  Language filter: {lang_filter!r}")
    print(f"{'='*60}\n")

    files = _discover_files(spec)
    if not files:
        print("[WARN] No JSON files found. Check content/ folder structure.")
        return

    print(f"Discovered {len(files)} candidate file(s):\n")

    # Gate 2 + validate all files before touching the DB
    valid_files: list[tuple[Path, dict]] = []
    error_count = 0
    for path in files:
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  [SKIP] {path.relative_to(CONTENT_ROOT)} — JSON parse error: {e}")
            error_count += 1
            continue

        # Gate 2: specializations field
        if spec not in data.get("specializations", []):
            print(f"  [SKIP] {path.relative_to(CONTENT_ROOT)} — spec {spec!r} not in specializations")
            continue

        # Gate 3: language filter (optional)
        if lang_filter is not None:
            file_lang = data.get("language", "").lower()
            if file_lang != lang_filter:
                print(f"  [SKIP] {path.relative_to(CONTENT_ROOT)} — language {file_lang!r} != {lang_filter!r}")
                continue

        try:
            _validate_file(data, spec)
        except ValidationError as e:
            print(f"  [ERROR] {path.relative_to(CONTENT_ROOT)} — {e}")
            error_count += 1
            continue

        print(f"  [OK]   {path.relative_to(CONTENT_ROOT)}")
        print(f"         quiz_title={data['quiz_title']!r}  category={data['category']}  "
              f"difficulty={data['difficulty']}  questions={len(data['questions'])}")
        valid_files.append((path, data))

    if error_count:
        print(f"\n[ABORT] {error_count} file(s) had errors. Fix them before seeding.")
        sys.exit(1)

    print(f"\n{len(valid_files)} file(s) passed validation.\n")

    if not valid_files:
        print("Nothing to seed.")
        return

    # Seed
    db = SessionLocal()
    try:
        totals = {"quizzes_created": 0, "questions_created": 0, "skipped": 0}

        for path, data in valid_files:
            result = _seed_file(db, data, path, dry_run)

            rel = path.relative_to(CONTENT_ROOT)
            if result.get("skipped"):
                print(f"  [SKIP]   {rel} — quiz already exists ({data['quiz_title']!r})")
                totals["skipped"] += 1
            elif result.get("dry_run_would_create"):
                print(f"  [DRY]    {rel} — would create quiz + {result['questions']} questions")
                totals["quizzes_created"] += 1
                totals["questions_created"] += result["questions"]
            else:
                print(f"  [CREATE] {rel} — created quiz + {result['questions']} questions")
                totals["quizzes_created"] += 1
                totals["questions_created"] += result["questions"]

        print(f"\n{'='*60}")
        action = "Would create" if dry_run else "Created"
        print(f"  {action}:  {totals['quizzes_created']} quiz(zes), {totals['questions_created']} question(s)")
        print(f"  Skipped: {totals['skipped']} quiz(zes) (already exist)")
        print(f"{'='*60}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
