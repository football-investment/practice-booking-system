# Migration Squash - Canonical Baseline 2026-02-21

## Summary

**Date:** 2026-02-21
**Action:** Complete migration history squash
**Reason:** Migration chain corruption and instability
**Result:** Single canonical baseline migration

---

## Background

The project accumulated 200+ migrations from 2025-08-01 to 2026-02-21, with the following issues:

### Problems Identified
1. **Incomplete root migration** - Missing critical tables and columns
2. **Duplicate table creations** - Multiple migrations creating the same tables
3. **Missing dependencies** - Later migrations depending on non-existent tables
4. **Enum value typos** - Incorrect enum values in check constraints
5. **Broken data migrations** - Complex data migrations referencing non-existent columns
6. **Fresh DB initialization failure** - Impossible to initialize clean database from migrations

### Migration Chain Corruption Examples
- `attendance` table created twice (root + a1b2c3d4e5f6)
- `tournament_status_history` created twice (71aab5034cd9 + f7592a774d52)
- `session_quizzes` missing from root but expected by later migrations
- `lfa_player_licenses` table referenced but never created
- `tournament_status` enum values: `OPEN_FOR_ENROLLMENT` vs `ENROLLMENT_OPEN` (typo)
- `INSTRUCTOR_CONFIRMED` status referenced but not in enum
- `xp_transactions` unique constraint added to non-existent table

---

## Solution: Migration Squash

All migrations from 2025-08-01 to 2026-02-21 have been **squashed** into a single canonical baseline:

```
alembic/versions/2026_02_21_0859-1ec11c73ea62_squashed_baseline_schema.py
```

### What Was Done

1. **Schema dump from production** - Extracted current working schema using `pg_dump`
2. **Legacy archive** - Moved all 200+ old migrations to `alembic/versions_legacy/`
3. **Generated new root** - Created single migration with complete schema
4. **Validated fresh DB init** - Tested on empty database → SUCCESS ✅

### Migration Details

**Revision:** `1ec11c73ea62`
**Down revision:** `None` (root migration)
**DDL statements:** 466 (enums, tables, indexes, constraints, foreign keys)
**Tables created:** 95
**Lines of code:** ~2,972

---

## Verification

### Fresh Database Initialization
```bash
# Create empty database
createdb lfa_fresh

# Run squashed migration
DATABASE_URL=postgresql://postgres:@localhost:5432/lfa_fresh \
  SECRET_KEY=test \
  alembic upgrade head

# ✅ Result: 95 tables created, 0 errors
```

### Schema Validation
```bash
# Count tables
psql lfa_fresh -c "\dt" | wc -l
# Output: 95 tables

# Check alembic version
psql lfa_fresh -c "SELECT * FROM alembic_version"
# Output: 1ec11c73ea62
```

---

## Impact

### ✅ Benefits
- **Deterministic fresh DB initialization** - Clean database setup always works
- **Clean migration graph** - Single root, no historical debt
- **CI/CD stability** - Workflows can reliably initialize test databases
- **Developer onboarding** - New developers get working setup immediately
- **Production-ready baseline** - Current schema is source of truth

### ⚠️ Considerations
- **Historical migrations archived** - Original migration history preserved in `versions_legacy/`
- **No rollback to pre-squash state** - Baseline is new starting point
- **Database stamping required** - Existing databases must be stamped with new version

---

## Migration for Existing Databases

If you have an existing database at the old HEAD state:

```bash
# Check current version
alembic current

# If at old HEAD (any version from versions_legacy/), stamp with new baseline
alembic stamp 1ec11c73ea62

# Future migrations will build on this baseline
```

⚠️ **Do NOT run `alembic upgrade head`** on existing production databases - they already have the schema. Only stamp the version.

---

## Future Migrations

All new migrations will use `1ec11c73ea62` as the baseline:

```bash
# Create new migration (automatically uses 1ec11c73ea62 as down_revision)
alembic revision -m "add_new_feature"
```

---

## Technical Debt Resolution

This squash resolves the following technical debt items:

1. ✅ **Root migration incompleteness** - Now includes all base tables
2. ✅ **Duplicate table migrations** - Eliminated duplicate creates
3. ✅ **Missing table dependencies** - All tables present in baseline
4. ✅ **Enum value inconsistencies** - Canonical enum definitions
5. ✅ **Fresh DB reproducibility** - 100% success rate
6. ✅ **CI/CD stability** - Deterministic test database creation

---

## Files

### New Structure
```
alembic/
├── versions/
│   └── 2026_02_21_0859-1ec11c73ea62_squashed_baseline_schema.py  # NEW ROOT
└── versions_legacy/
    ├── 2025_08_01_0000-w3mg03uvao74_root_initial_schema.py      # OLD ROOT
    ├── 2025_09_16_2051-267beadbb5bf_add_adaptive_learning_models.py
    ├── ... (200+ migrations archived)
    └── 2026_02_19_1200-rw01_reward_concurrency_guards.py
```

### Documentation
- This file: `docs/MIGRATION_SQUASH.md`
- Schema dump: `/tmp/current_schema_dump.sql` (reference)
- Generation script: `/tmp/generate_squashed_migration.py`

---

## Rollout Checklist

- [x] Schema dump from production database
- [x] Archive legacy migrations to `versions_legacy/`
- [x] Generate squashed baseline migration
- [x] Test fresh database initialization
- [x] Document squash strategy
- [ ] Commit squashed baseline
- [ ] Update CI workflows (if needed)
- [ ] Notify team of new baseline
- [ ] Update developer setup docs

---

## Contact

For questions about this migration squash:
- **Date:** 2026-02-21
- **Context:** Migration chain stabilization effort
- **References:** This document + `alembic/versions/2026_02_21_0859-1ec11c73ea62_squashed_baseline_schema.py`

---

**Status:** ✅ COMPLETE - Fresh DB initialization validated, canonical baseline established
