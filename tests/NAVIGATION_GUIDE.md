# Test Navigation Guide

**Purpose:** Gyors navigáció a tesztfájlokhoz formátum és teszt típus alapján

**Last Updated:** 2026-02-08

---

## 🎯 Quick Navigation by Tournament Format

### GROUP_AND_KNOCKOUT

**E2E Tests:**
- `tests/e2e/golden_path/test_golden_path_api_based.py` - Production Golden Path (7 players)
- `tests/e2e_frontend/group_knockout/test_group_knockout_7_players.py` - Edge case validation
- `tests/e2e_frontend/group_knockout/test_group_stage_only.py` - Group stage only

**Run Commands:**
```bash
# Golden Path (production critical)
pytest tests/e2e/golden_path/test_golden_path_api_based.py -v

# All group_knockout E2E tests
pytest tests/e2e_frontend/group_knockout/ -v

# By marker
pytest -m golden_path -v
pytest -m group_knockout -v
```

---

### HEAD_TO_HEAD

**E2E Tests:**
- `tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py` - League (4/6/8 players)

**Run Commands:**
```bash
# All HEAD_TO_HEAD tests
pytest tests/e2e_frontend/head_to_head/ -v

# By marker
pytest -m h2h -v
```

**Configurations:**
- H1_League_Basic: 4 players, 6 matches
- H2_League_Medium: 6 players, 15 matches
- H3_League_Large: 8 players, 28 matches

---

### INDIVIDUAL_RANKING

**E2E Tests:**
- `tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py` - 15 configurations

**Run Commands:**
```bash
# All INDIVIDUAL_RANKING tests
pytest tests/e2e_frontend/individual_ranking/ -v

# Specific configuration
pytest tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py::test_full_ui_workflow[T1_Ind_Score_1R] -v
```

**Configurations:**
- SCORE_BASED: 3 configs (1R, 2R, 3R)
- TIME_BASED: 3 configs (1R, 2R, 3R)
- DISTANCE_BASED: 3 configs (1R, 2R, 3R)
- PLACEMENT: 3 configs (1R, 2R, 3R)
- ROUNDS_BASED: 3 configs (1R, 2R, 3R)

---

### KNOCKOUT

**Service-Level Tests:**
- `tests/tournament_types/test_knockout_tournament.py` - Knockout logic

**Run Commands:**
```bash
pytest tests/tournament_types/test_knockout_tournament.py -v
```

---

### LEAGUE

**Service-Level Tests:**
- `tests/tournament_types/test_league_e2e_api.py` - League API tests
- `tests/tournament_types/test_league_api.sh` - League shell tests
- `tests/tournament_types/test_league_interactive.sh` - Interactive tests
- `tests/tournament_types/test_league_with_checkpoints.sh` - Checkpoint tests

**Run Commands:**
```bash
pytest tests/tournament_types/test_league_e2e_api.py -v
```

---

## 📂 Quick Navigation by Test Type

### E2E Tests (End-to-End)

**Golden Path (Production Critical):**
```bash
tests/e2e/golden_path/
└── test_golden_path_api_based.py    # GROUP_AND_KNOCKOUT (7 players)
```

**Frontend E2E:**
```bash
tests/e2e_frontend/
├── group_knockout/
│   ├── test_group_knockout_7_players.py
│   └── test_group_stage_only.py
├── head_to_head/
│   └── test_tournament_head_to_head.py
├── individual_ranking/
│   └── test_tournament_full_ui_workflow.py
└── shared/
    ├── shared_tournament_workflow.py
    └── streamlit_helpers.py
```

**Run All E2E:**
```bash
# All E2E tests
pytest tests/e2e/ tests/e2e_frontend/ -v

# Only Golden Path
pytest tests/e2e/golden_path/ -v

# Only frontend E2E
pytest tests/e2e_frontend/ -v
```

---

### Unit Tests

```bash
tests/unit/tournament/
├── test_core.py                    # CRUD operations
├── test_leaderboard_service.py     # Leaderboard logic
├── test_stats_service.py           # Stats calculations
├── test_team_service.py            # Team management
├── test_tournament_xp_service.py   # XP calculations
└── test_validation.py              # Business logic validation
```

**Run All Unit Tests:**
```bash
pytest tests/unit/tournament/ -v
pytest -m unit -v
```

---

### Integration Tests

```bash
tests/integration/tournament/
└── ... (integration tests)
```

**Run All Integration Tests:**
```bash
pytest tests/integration/tournament/ -v
pytest -m integration -v
```

---

### Service-Level Tests

```bash
tests/tournament_types/
├── test_knockout_tournament.py
├── test_league_e2e_api.py
└── ... (service-level tests)
```

**Run All Tournament Type Tests:**
```bash
pytest tests/tournament_types/ -v
```

---

## 🏷️ Pytest Markers Reference

### By Format

```bash
# GROUP_AND_KNOCKOUT
pytest -m golden_path -v          # Golden Path only
pytest -m group_knockout -v       # All group_knockout tests

# HEAD_TO_HEAD
pytest -m h2h -v                  # All HEAD_TO_HEAD tests

# INDIVIDUAL_RANKING
pytest tests/e2e_frontend/individual_ranking/ -v  # By directory
```

### By Test Level

```bash
# E2E tests
pytest -m e2e -v

# Unit tests
pytest -m unit -v

# Integration tests
pytest -m integration -v

# Smoke tests (fast CI)
pytest -m smoke -v
```

### By Component

```bash
# Tournament tests
pytest -m tournament -v

# Validation tests
pytest -m validation -v
```

---

## 🔍 Common Search Scenarios

### "Where are the Golden Path tests?"
→ `tests/e2e/golden_path/test_golden_path_api_based.py`

### "Where are the HEAD_TO_HEAD tests?"
→ `tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py`

### "Where are the INDIVIDUAL_RANKING tests?"
→ `tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py`

### "Where are the GROUP_KNOCKOUT tests?"
→ Multiple locations:
- `tests/e2e/golden_path/` - Production Golden Path
- `tests/e2e_frontend/group_knockout/` - Edge cases

### "Where are the KNOCKOUT tests?"
→ `tests/tournament_types/test_knockout_tournament.py`

### "Where are the LEAGUE tests?"
→ `tests/tournament_types/test_league_*.py`

### "Where are the unit tests for tournaments?"
→ `tests/unit/tournament/`

### "Where are the shared test helpers?"
→ `tests/e2e_frontend/shared/`

---

## 📊 Test Coverage Matrix

| Format | E2E Golden Path | E2E Frontend | Unit | Integration | Tournament Types |
|--------|----------------|--------------|------|-------------|------------------|
| **GROUP_AND_KNOCKOUT** | ✅ (`e2e/golden_path/`) | ✅ (`e2e_frontend/group_knockout/`) | ✅ (`unit/tournament/`) | ✅ (`integration/`) | ❌ |
| **HEAD_TO_HEAD** | ❌ | ✅ (`e2e_frontend/head_to_head/`) | ❌ | ❌ | ❌ |
| **INDIVIDUAL_RANKING** | ❌ | ✅ (`e2e_frontend/individual_ranking/`) | ❌ | ❌ | ❌ |
| **KNOCKOUT** | ❌ | ❌ | ❌ | ❌ | ✅ (`tournament_types/`) |
| **LEAGUE** | ❌ | ❌ | ❌ | ❌ | ✅ (`tournament_types/`) |

---

## 🚀 CI/CD Quick Commands

### Run Production Critical Tests Only
```bash
pytest -m golden_path -v
```

### Run Smoke Tests (Fast CI)
```bash
pytest -m smoke -v
```

### Run All E2E Tests
```bash
pytest tests/e2e/ tests/e2e_frontend/ -v
```

### Run Format-Specific Suite
```bash
# GROUP_KNOCKOUT
pytest tests/e2e/golden_path/ tests/e2e_frontend/group_knockout/ -v

# HEAD_TO_HEAD
pytest tests/e2e_frontend/head_to_head/ -v

# INDIVIDUAL_RANKING
pytest tests/e2e_frontend/individual_ranking/ -v
```

### Run All Tournament Tests
```bash
pytest -m tournament -v
```

---

## 🛠️ Development Workflow

### Adding a New Test

**For GROUP_AND_KNOCKOUT:**
→ Add to `tests/e2e_frontend/group_knockout/`

**For HEAD_TO_HEAD:**
→ Add to `tests/e2e_frontend/head_to_head/`

**For INDIVIDUAL_RANKING:**
→ Add to `tests/e2e_frontend/individual_ranking/`

**For Golden Path:**
→ Add to `tests/e2e/golden_path/` (production critical only)

**For Unit Tests:**
→ Add to `tests/unit/tournament/`

### Updating Shared Helpers

**Location:** `tests/e2e_frontend/shared/`

**Files:**
- `shared_tournament_workflow.py` - Workflow functions (DRY principle)
- `streamlit_helpers.py` - UI interaction helpers

---

## 📖 Additional Documentation

- **Test Suite Architecture:** [TEST_SUITE_ARCHITECTURE.md](TEST_SUITE_ARCHITECTURE.md)
- **Test Organization Assessment:** [TEST_ORGANIZATION_ASSESSMENT.md](TEST_ORGANIZATION_ASSESSMENT.md)
- **General Test README:** [tests/README.md](tests/README.md)
- **Golden Path Structure:** [GOLDEN_PATH_STRUCTURE.md](GOLDEN_PATH_STRUCTURE.md)

---

## ⚡ Quick Reference Card

```
FORMAT                  LOCATION
======                  ========
GROUP_KNOCKOUT         → tests/e2e/golden_path/ (Golden Path)
                       → tests/e2e_frontend/group_knockout/ (Edge cases)

HEAD_TO_HEAD          → tests/e2e_frontend/head_to_head/

INDIVIDUAL_RANKING    → tests/e2e_frontend/individual_ranking/

KNOCKOUT              → tests/tournament_types/test_knockout_tournament.py

LEAGUE                → tests/tournament_types/test_league_*.py

Unit Tests            → tests/unit/tournament/

Shared Helpers        → tests/e2e_frontend/shared/
```

---

**Navigation Tips:**
1. Use `pytest -m <marker>` to filter by marker
2. Use directory paths for format-specific tests
3. Check markers in test files with `@pytest.mark.<marker>`
4. Golden Path = production critical (always run before deploy)

---

**Author:** Claude Code (Sonnet 4.5)
**Date:** 2026-02-08
**Maintained By:** Development Team

---

## 📁 Additional Test Categories (Phase P5)

### Manual Tests
**Location:** `tests/manual/`
**Purpose:** Interactive testing scripts (not automated)

```bash
tests/manual/
├── test_registration_validation.py
├── test_validation.py
└── test_tournament_api.py
```

**Run:** Execute manually (not part of CI/CD)
```bash
python tests/manual/test_registration_validation.py
```

---

### Unit Tests
**Location:** `tests/unit/`
**Purpose:** Isolated component testing

```bash
tests/unit/
└── services/
    └── test_skill_progression_service.py
```

**Run All Unit Tests:**
```bash
pytest tests/unit/ -v
pytest -m unit -v
```

---

### Instructor Workflow E2E
**Location:** `tests/e2e/instructor_workflow/`
**Purpose:** Complete instructor workflow validation

```bash
tests/e2e/instructor_workflow/
└── test_instructor_workflow_e2e.py
```

**Run:**
```bash
pytest tests/e2e/instructor_workflow/ -v
```

---

### API Tests (Expanded)
**Location:** `tests/api/`
**Purpose:** API endpoint validation

**New files from Phase P5:**
- `test_reward_distribution.py` (moved from root)
- `test_user_creation.py` (moved from root)

**Run All API Tests:**
```bash
pytest tests/api/ -v
```

---

## 🗂️ Test Directory Structure Summary (Updated P5)

```
tests/
├── e2e/                          # E2E tests
│   ├── golden_path/              # Production critical Golden Path
│   └── instructor_workflow/      # NEW (P5) - Instructor workflow E2E
├── e2e_frontend/                 # Frontend E2E by format
│   ├── head_to_head/
│   ├── individual_ranking/
│   ├── group_knockout/
│   └── shared/
├── api/                          # API endpoint tests (2 new files added)
├── unit/                         # NEW (P5) - Unit tests
│   └── services/
├── integration/                  # Integration tests
├── manual/                       # NEW (P5) - Manual testing scripts
├── debug/                        # Debug tests (not CI/CD)
└── .archive/deprecated/          # Deprecated tests

✅ Total: 0 test files in root (100% organized)
```

---

**Last Updated:** 2026-02-08 (Phase P5 Complete)
**Root Cleanup:** ✅ 100% Complete (0 test files remaining)
**Refactoring Phase:** P0-P5 Complete
