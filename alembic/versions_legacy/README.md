# Legacy Migrations Archive

**Date Archived:** 2026-02-21
**Reason:** Migration chain squash

---

## What Happened

All migrations from 2025-08-01 to 2026-02-21 (200+ files) have been **archived** to this directory and replaced with a single canonical baseline migration.

## Why

The migration chain had accumulated technical debt:
- Duplicate table creations
- Missing dependencies
- Broken data migrations
- Enum value inconsistencies
- **Fresh database initialization was broken**

See `docs/MIGRATION_SQUASH.md` for full details.

## New Baseline

**New root migration:**
```
alembic/versions/2026_02_21_0859-1ec11c73ea62_squashed_baseline_schema.py
```

This single migration creates the complete, production-ready schema as of 2026-02-21.

## These Files Are

✅ **Preserved for reference** - Historical record of schema evolution
❌ **Not executed by Alembic** - Only files in `alembic/versions/` are run
📚 **Documentation** - Shows how schema evolved over time

## Using These Files

If you need to understand:
- When a specific table was added → Search these files
- Why a column exists → Check migration messages
- Schema evolution history → Read through migrations chronologically

**But:** Do NOT copy these back to `alembic/versions/` - they will conflict with the squashed baseline.

---

**Squashed Migration:** 2026-02-21
**Baseline Revision:** 1ec11c73ea62
**Documentation:** `docs/MIGRATION_SQUASH.md`
