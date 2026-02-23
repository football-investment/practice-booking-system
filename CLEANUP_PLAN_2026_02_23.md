# Gyökérkönyvtár Tisztítási Terv - 2026-02-23

## Összefoglaló

**Probléma:** Rendezetlen gyökérkönyvtár, 120+ markdown fájl, debug screenshot-ok, SQL scriptek, felesleges asset-ek.

**Cél:** Tiszta, strukturált projekt struktúra, minden fájl a helyén, könnyű navigáció, CI-ready.

---

## 1️⃣ Asset Fájlok (Screenshots, Logók, Képek)

### 🔍 Jelenlegi Helyzet

**Root directory screenshot-ok (15 fájl):**
```
./error_after_new_tournament_click.png
./screenshot_after_new_tournament.png
./screenshot_02a_scrolled_to_tournament_config.png
./debug_streamlit_form.png
./screenshot_03_scrolled.png
./screenshot_01_config_loaded.png
./screenshot_FAILURE.png
./debug_streamlit_530.png
./screenshot_02_form_filled.png
./debug_streamlit_532.png
./screenshot_00_home.png
./screenshot_home.png
./screenshot_EXCEPTION.png
./debug_streamlit.png
./screenshot_form_filled.png
```

### ✅ Akció

**Célkönyvtár:** `docs/debug_screenshots/` (létrehozni ha nem létezik)

**Parancsok:**
```bash
mkdir -p docs/debug_screenshots
mv *.png docs/debug_screenshots/
mv *.jpg docs/debug_screenshots/ 2>/dev/null || true
mv *.svg docs/debug_screenshots/ 2>/dev/null || true
```

**Tisztítás után:**
- Root directory: 0 képfájl
- `docs/debug_screenshots/`: 15 képfájl (archivált debug asset-ek)

---

## 2️⃣ SQL Script Fájlok

### 🔍 Jelenlegi Helyzet

**Root directory SQL scriptek (3 fájl):**
```
./cleanup_test_tournaments.sql
./create_test_presets_sql.sql
./CLEANUP_DUPLICATE_REWARDS.sql
```

### ✅ Akció

**Célkönyvtár:** `scripts/sql/cleanup/` (létrehozni)

**Parancsok:**
```bash
mkdir -p scripts/sql/cleanup
mv cleanup_test_tournaments.sql scripts/sql/cleanup/
mv create_test_presets_sql.sql scripts/sql/cleanup/
mv CLEANUP_DUPLICATE_REWARDS.sql scripts/sql/cleanup/
```

**Tisztítás után:**
- Root directory: 0 SQL script
- `scripts/sql/cleanup/`: 3 SQL script (archivált cleanup szkriptek)

---

## 3️⃣ Markdown Dokumentáció (120+ fájl!)

### 🔍 Jelenlegi Helyzet

**Root directory: 120 markdown fájl** (túl sok!)

**Kategorizálás:**

**Kategória 1: FONTOS (KEEP in root)**
```
README.md
CONTRIBUTING.md
ARCHITECTURE.md
```

**Kategória 2: Sprint Planning / Session Notes**
```
ACTION_PLAN_IMMEDIATE.md
BASELINE_*.md
CLEANUP_*.md
CONFIG_CONSOLIDATION_PLAN.md
CRITICAL_*.md
CYPRESS_*.md
DAY1_*.md
EPIC_*.md
EXECUTION_CHECKLIST.md
... (50+ planning docs)
```

**Kategória 3: Deprecated**
```
COMPLETE_E2E_VALIDATION_RESULTS_2026_02_02.md.DEPRECATED
... (deprecated suffix fájlok)
```

### ✅ Akció

**Struktúra:**
```
docs/
├── planning/           # Sprint planning, action plans
├── baselines/          # Baseline reports, frozen states
├── cleanup/            # Cleanup reports, execution logs
├── deprecated/         # .DEPRECATED fájlok
└── debug_screenshots/  # Debug screenshots (already created)
```

**Parancsok:**
```bash
# Create structure
mkdir -p docs/planning
mkdir -p docs/baselines
mkdir -p docs/cleanup
mkdir -p docs/deprecated

# Move planning docs
mv ACTION_PLAN_*.md docs/planning/ 2>/dev/null || true
mv EXECUTION_*.md docs/planning/ 2>/dev/null || true
mv CONFIG_*.md docs/planning/ 2>/dev/null || true
mv EPIC_*.md docs/planning/ 2>/dev/null || true

# Move baseline docs
mv BASELINE_*.md docs/baselines/ 2>/dev/null || true
mv CRITICAL_UNIT_TEST_STATUS_*.md docs/baselines/ 2>/dev/null || true

# Move cleanup docs
mv CLEANUP_*.md docs/cleanup/ 2>/dev/null || true
mv DAY1_*.md docs/cleanup/ 2>/dev/null || true

# Move deprecated docs
mv *.DEPRECATED docs/deprecated/ 2>/dev/null || true

# Cypress docs
mv CYPRESS_*.md docs/cypress/ 2>/dev/null || true
mkdir -p docs/cypress
mv CYPRESS_*.md docs/cypress/
```

**Tisztítás után:**
- Root directory: 3-5 markdown fájl (README, CONTRIBUTING, ARCHITECTURE, COVERAGE_GAP_RISK_REPORT)
- `docs/`: Strukturált dokumentáció

---

## 4️⃣ Test Directory Konszolidálás

### 🔍 Jelenlegi Helyzet

**3 fő test könyvtár:**
1. `tests/` - Komplex, sok alkönyvtár (unit, api, e2e, stb.)
2. `tests_cypress/` - Cypress E2E tesztek + node_modules
3. `tests_e2e/` - Integration critical E2E tesztek

**`tests/` alkönyvtárak (40+):**
```
tests/api/
tests/architecture/
tests/auth/
tests/component/
tests/database/
tests/debug/
tests/e2e/
tests/e2e_frontend/
tests/features/
tests/formatters/
tests/integration/
tests/manual/
tests/manual_integration/
tests/parsers/
tests/performance/
tests/phases/
tests/playwright/
tests/ranking/
tests/regression/
tests/results/
tests/rewards/
tests/sandbox_validation/
tests/scenarios/
tests/schemas/
tests/security/
tests/sessions/
tests/skills/
tests/tournament/
tests/tournament_types/
tests/unit/
tests/validation/
... (még sok más)
```

### ✅ Akció - Opció 1: KEEP jelenlegi struktúra (RECOMMENDED)

**Indoklás:**
- `tests/` = pytest unit/integration tesztek
- `tests_cypress/` = Cypress E2E tesztek (frontend)
- `tests_e2e/` = API E2E tesztek (backend)

**Csak node_modules kitakarítás:**
```bash
# Add to .gitignore if not already there
echo "tests_cypress/node_modules/" >> .gitignore
```

**Nincs move, csak cleanup:**
- Archive alkönyvtárak review (`.archive/`, `deprecated/`)
- Delete vagy move deprecated tesztek

### ✅ Akció - Opció 2: Konszolidálás (OPTIONAL, több munka)

**Cél struktúra:**
```
tests/
├── unit/               # Unit tesztek (pytest)
├── integration/        # Integration tesztek (pytest)
├── e2e/
│   ├── api/           # API E2E (tests_e2e/ ide)
│   ├── frontend/      # Frontend E2E (tests/e2e_frontend/ ide)
│   └── cypress/       # Cypress tesztek (tests_cypress/ ide)
├── playwright/         # Playwright tesztek
├── security/          # Security tesztek
└── performance/       # Performance tesztek
```

**⚠️ NEM AJÁNLOTT:** Sok test import path változik, CI break kockázat!

---

## 5️⃣ Fixtures és Helper Fájlok Review

### 🔍 Áttekintendő

**Pytest fixtures:**
```
tests/conftest.py
tests/unit/conftest.py
tests/integration/conftest.py
tests_e2e/conftest.py
```

**Helper modulok:**
```
tests_e2e/utils/
tests/e2e_frontend/shared/
tests/playwright/fixtures/
```

### ✅ Akció

**Review checklist:**
- ✅ Duplikált fixtures felderítése
- ✅ Unused fixtures törlése
- ✅ Shared helper konzolidálása (ha van overlap)

**Nincs automatikus move, csak manual review!**

---

## 6️⃣ .gitignore Frissítés

### ✅ Hozzáadandó

```gitignore
# Test artifacts
tests_cypress/node_modules/
tests_cypress/cypress/videos/
tests_cypress/cypress/screenshots/
tests_e2e/screenshots/
tests_e2e/videos/
*.pyc
__pycache__/
.pytest_cache/

# Debug screenshots (moved to docs/)
docs/debug_screenshots/*.png
docs/debug_screenshots/*.jpg

# SQL cleanup scripts (moved to scripts/)
scripts/sql/cleanup/*.sql

# Documentation (moved to docs/)
docs/planning/
docs/baselines/
docs/cleanup/
docs/deprecated/
```

---

## 7️⃣ Végrehajtási Sorrend (Safe Cleanup)

### Phase 1: Asset Cleanup (LOW RISK)
```bash
mkdir -p docs/debug_screenshots
mv *.png docs/debug_screenshots/
mv *.jpg docs/debug_screenshots/ 2>/dev/null || true
```

### Phase 2: SQL Scripts Cleanup (LOW RISK)
```bash
mkdir -p scripts/sql/cleanup
mv *.sql scripts/sql/cleanup/
```

### Phase 3: Markdown Dokumentáció (MEDIUM RISK)
```bash
mkdir -p docs/{planning,baselines,cleanup,deprecated,cypress}

# Move carefully, one category at a time
mv ACTION_PLAN_*.md docs/planning/
mv BASELINE_*.md docs/baselines/
# ... (continue per category)
```

### Phase 4: .gitignore Update (LOW RISK)
```bash
# Add entries to .gitignore
```

### Phase 5: Test Directory Review (HIGH RISK - Manual Only)
```
# MANUAL REVIEW ONLY
# No automated moves for test directories
# Review fixtures, helpers, deprecated tests
```

### Phase 6: Commit Cleanup
```bash
git add .
git commit -m "chore: Clean up root directory structure

Moved:
- 15 debug screenshots → docs/debug_screenshots/
- 3 SQL scripts → scripts/sql/cleanup/
- 100+ markdown docs → docs/ (categorized)

Updated .gitignore for test artifacts and moved files.
"
```

---

## 8️⃣ Cleanup Utáni Struktúra

### ✅ Root Directory (Target)

```
practice_booking_system/
├── .github/                 # CI workflows
├── .venv/                   # Virtual env (gitignored)
├── alembic/                 # DB migrations
├── app/                     # Application code
│   ├── api/
│   ├── models/
│   ├── services/
│   └── tests/              # App-level E2E tests (NEW)
├── docs/                    # Documentation (NEW)
│   ├── planning/           # Sprint planning
│   ├── baselines/          # Baseline reports
│   ├── cleanup/            # Cleanup logs
│   ├── deprecated/         # Archived docs
│   ├── debug_screenshots/  # Debug assets
│   └── cypress/            # Cypress docs
├── scripts/                 # Utility scripts (NEW)
│   └── sql/
│       └── cleanup/        # SQL cleanup scripts
├── streamlit_app/           # Streamlit frontend
├── tests/                   # Pytest tests
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── ...
├── tests_cypress/           # Cypress E2E tests
├── tests_e2e/              # API E2E tests
├── README.md               # Main readme
├── CONTRIBUTING.md         # Contribution guide
├── ARCHITECTURE.md         # Architecture docs
├── COVERAGE_GAP_RISK_REPORT.md  # Coverage report (important!)
├── requirements.txt        # Python deps
└── pytest.ini              # Pytest config
```

**Root directory file count target:** <15 fájl (volt 200+)

---

## 9️⃣ Verification Checklist

**Post-Cleanup Validáció:**

- [ ] Root directory tiszta (<15 fájl)
- [ ] Minden screenshot `docs/debug_screenshots/`-ban
- [ ] Minden SQL script `scripts/sql/cleanup/`-ban
- [ ] Markdown docs strukturálva `docs/` alatt
- [ ] .gitignore frissítve
- [ ] CI pipeline törés ellenőrzés (pytest path-ok)
- [ ] Tesztek futtatása (unit, integration, E2E)

---

## 🎯 Prioritás és Timeline

**HIGH Priority (azonnal):**
1. ✅ Asset cleanup (screenshots, SQL) - 10 perc
2. ✅ .gitignore update - 5 perc
3. ✅ Commit cleanup changes - 5 perc

**MEDIUM Priority (opcionális):**
4. ⏳ Markdown dokumentáció rendezés - 30-60 perc
5. ⏳ Test directory manual review - 1-2 óra

**LOW Priority (post-cleanup):**
6. ⏳ Fixture consolidation - 2-4 óra
7. ⏳ Test directory konszolidálás (ha szükséges) - 4-8 óra

---

## 📝 Notes

- **SAFE cleanup:** Asset és SQL move SAFE (nem törnek semmit)
- **RISKY cleanup:** Test directory move RISKY (import path-ok változnak)
- **Markdown move:** SAFE de időigényes (100+ fájl)
- **CI impact:** Minimal ha csak asset/doc move, MEDIUM ha test path változik

**Recommended approach:** Phase 1-4 azonnal, Phase 5 manual review, Phase 6 commit.

---

**Készítette:** Claude Sonnet 4.5
**Dátum:** 2026-02-23
**Status:** READY for execution
