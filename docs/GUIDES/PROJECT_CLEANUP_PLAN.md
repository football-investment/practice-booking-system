# Project Cleanup & Reorganization Plan

**Dátum:** 2025-12-20
**Típus:** 🧹 TELJES PROJEKT AUDIT ÉS TISZTÍTÁSI TERV
**Státusz:** AUDIT COMPLETE - CLEANUP PENDING

---

## 🚨 KRITIKUS PROBLÉMA

**Root directory:** 122+ fájl (dokumentumok, scriptek, tesztek)
**Mappák:** 14 mappa (beleszámítva __pycache__, old backupok, stb.)

**Következmények:**
- ❌ Áttekinthetetlen projekt struktúra
- ❌ Nehéz megtalálni a releváns fájlokat
- ❌ Deployment zavaró (mi kell, mi nem?)
- ❌ Git repo zajos (sok felesleges fájl)

---

## 📊 JELENLEGI PROJEKT STRUKTÚRA

### Root Mappák (14 db)

| Mappa | Cél | Státusz | Akció |
|-------|-----|---------|-------|
| **`__pycache__/`** | Python cache | ❌ FELESLEGES | TÖRÖLD (.gitignore-ba!) |
| **`alembic/`** | DB migrations | ✅ KELL | MEGTART |
| **`app/`** | Backend API (FastAPI) | ✅ KELL | MEGTART |
| **`config/`** | Configuration files | ✅ KELL | MEGTART |
| **`docs/`** | Documentation | ✅ KELL | **REORGANIZE** |
| **`implementation/`** | Implementation notes | ⚠️ ÁTMOZGAT | → `docs/implementation/` |
| **`logs/`** | Application logs | ❌ GITIGNORE | .gitignore-ba |
| **`old_reports/`** | Old test reports | ❌ ARCHÍV | TÖRÖLD vagy archive |
| **`scripts/`** | Utility scripts | ✅ KELL | **REORGANIZE** |
| **`streamlit_app/`** | Streamlit frontend | ✅ KELL | MEGTART |
| **`streamlit_app_OLD.../`** | OLD backup | ❌ BACKUP | **TÖRÖLD** |
| **`test_results/`** | Test output | ❌ GITIGNORE | .gitignore-ba |
| **`test_scenarios/`** | Test scenarios | ⚠️ ÁTMOZGAT | → `tests/scenarios/` |
| **`venv/`** | Python virtualenv | ❌ GITIGNORE | .gitignore-ba |

### Root Fájlok Kategóriák

#### 📋 Dokumentációk (55 db .md fájl!)

**Kategóriák:**

1. **Aktuális/Releváns (MEGTART):**
   - `README.md` ✅
   - `START_HERE.md` ✅
   - `PRODUCTION_DEPLOYMENT_CHECKLIST.md` ✅
   - `ADMIN_DASHBOARD_AUDIT_COMPLETE.md` ✅ (új)
   - `LFA_PLAYER_SEASON_ENROLLMENT_FIX.md` ✅ (új)
   - `SPEC_SERVICES_REFACTOR_COMPLETE.md` ✅ (új)

2. **Feature Implementation Docs (ARCHÍV → docs/completed/):**
   - `ADMIN_DASHBOARD_COMPLETE_IMPLEMENTATION.md`
   - `CAMPUS_CRUD_COMPLETE.md`
   - `FINANCIAL_MANAGEMENT_COMPLETE.md`
   - `LICENSE_DISPLAY_FEATURE_COMPLETE.md`
   - `LOCATION_MANAGEMENT_COMPLETE.md`
   - `N+1_FIXES_COMPLETE.md`
   - `PAYMENT_VERIFICATION_UI_FIX_COMPLETE.md`
   - `SEMESTER_MANAGEMENT_IMPLEMENTATION_COMPLETE.md`
   - `SESSION_DISPLAY_FIX_COMPLETE.md`
   - `STREAMLIT_FRONTEND_PHASE_1_COMPLETE.md`
   - `STREAMLIT_FRONTEND_PHASE_2_COMPLETE.md`
   - (+ ~20 hasonló)

3. **Phase Completion Docs (ARCHÍV → docs/phases/):**
   - `PHASE_4_LFA_COACH_SERVICE_COMPLETE.md`
   - `PHASE_5_LFA_INTERNSHIP_SERVICE_COMPLETE.md`
   - `PHASE_6_API_INTEGRATION_COMPLETE.md`
   - `P0_TASKS_COMPLETE.md`
   - `P1_TASKS_COMPLETE_SUMMARY.md`

4. **Audit Reports (ARCHÍV → docs/audits/):**
   - `ADATBAZIS_AUDIT_OSSZEFOGLALO.md`
   - `DATABASE_AUDIT_SUMMARY.md`
   - `BACKEND_LOGIC_ANALYSIS_COMPLETE.md`

5. **Quick Guides (MEGTART → docs/guides/):**
   - `LOGIN_GUIDE.md`
   - `STREAMLIT_QUICK_START.md`
   - `INDITAS.md` (Startup guide)
   - `INVOICE_VS_CREDIT_PURCHASE_EXPLAINED.md`

6. **Fix/Bug Reports (ARCHÍV → docs/fixes/):**
   - `BROWSER_CACHE_FIX_HUNGARIAN.md`
   - `CACHE_PROBLEMA_MEGOLDVA.md`
   - `SESSION_PERSISTENCE_FIX.md`
   - `INVITATION_CODE_MODAL_FIX.md`
   - (+ ~10 hasonló)

#### 🐍 Python Scriptek (60+ db .py fájl!)

**Kategóriák:**

1. **Test Files (ÁTMOZGAT → tests/):**
   - `test_*.py` (45+ fájl!)
   - Példák:
     - `test_lfa_player_service.py`
     - `test_lfa_coach_service.py`
     - `test_lfa_internship_service.py`
     - `test_api_integration.py`
     - `test_semester_generation.py`
     - stb.

2. **Utility Scripts (MEGTART → scripts/utility/):**
   - `check_api_keys.py`
   - `check_api_session_209.py`
   - `check_sessions_list_api.py`
   - `debug_bookings.py`

3. **Database Scripts (MEGTART → scripts/database/):**
   - `create_fresh_database.py`
   - `migrate_instructor_specializations_to_licenses.py`
   - `migrate_locations_to_campuses.py`
   - `delete_internship_semester.py`
   - `create_retroactive_license_transactions.py`

4. **Admin Scripts (MEGTART → scripts/admin/):**
   - `reset_admin_password.py`
   - `reset_admin_simple.py`
   - `reset_grandmaster_password.py`
   - `reset_grandmaster_via_api.py`
   - `create_grandmaster_all_licenses.py`

5. **Test Data Scripts (MEGTART → scripts/test_data/):**
   - `create_test_student.py`
   - `create_test_sessions_with_scenarios.py`

6. **Dashboard Scripts (MEGTART → scripts/dashboards/):**
   - `interactive_workflow_dashboard.py`
   - `credit_purchase_workflow_dashboard.py`
   - `invitation_code_workflow_dashboard.py`
   - `session_rules_testing_dashboard.py`
   - `unified_workflow_dashboard.py`
   - `clean_testing_dashboard.py`

7. **Fix Scripts (ARCHÍV → scripts/deprecated/):**
   - `fix_license_endpoints.py`
   - `test_credit_validation_fix.py`
   - `test_sessions_fix.py`

#### 🔧 Shell Scripts (15+ db .sh fájl!)

**Kategóriák:**

1. **Startup Scripts (MEGTART → scripts/startup/):**
   - `start_backend.sh`
   - `start_streamlit_app.sh`
   - `start_streamlit_production.sh`
   - `run_backend_now.sh`

2. **Dashboard Launchers (MEGTART → scripts/dashboards/):**
   - `start_clean_dashboard.sh`
   - `start_improved_dashboard.sh`
   - `start_credit_purchase_workflow.sh`
   - `start_interactive_testing.sh`
   - `start_interactive_workflow.sh`
   - `start_invitation_workflow.sh`
   - `start_session_rules_dashboard.sh`
   - `start_unified_dashboard.sh`

3. **Setup Scripts (MEGTART → scripts/setup/):**
   - `setup_new_database.sh`

#### 📄 Other Files

- `requirements.txt` ✅ MEGTART (root-ban kell)
- `requirements-test.txt` ⚠️ → `tests/requirements.txt`
- `test_output.txt` ❌ TÖRÖLD (gitignore)
- `test_summary.txt` ❌ TÖRÖLD (gitignore)

---

## 🎯 JAVASOLT ÚJ PROJEKT STRUKTÚRA

```
practice_booking_system/
├── .gitignore                           # ✅ Frissítendő
├── README.md                            # ✅ MEGTART (root)
├── START_HERE.md                        # ✅ MEGTART (root)
├── PRODUCTION_DEPLOYMENT_CHECKLIST.md   # ✅ MEGTART (root)
├── requirements.txt                     # ✅ MEGTART (root)
│
├── alembic/                             # ✅ DB migrations
├── app/                                 # ✅ Backend API
├── config/                              # ✅ Configuration
├── streamlit_app/                       # ✅ Frontend
│
├── docs/                                # 📋 REORGANIZÁLT DOKUMENTÁCIÓ
│   ├── README.md                        # Index of all docs
│   ├── guides/                          # User/Admin guides
│   │   ├── LOGIN_GUIDE.md
│   │   ├── STREAMLIT_QUICK_START.md
│   │   ├── INDITAS.md
│   │   └── INVOICE_VS_CREDIT_PURCHASE_EXPLAINED.md
│   ├── audits/                          # Audit reports
│   │   ├── ADMIN_DASHBOARD_AUDIT_COMPLETE.md
│   │   ├── DATABASE_AUDIT_SUMMARY.md
│   │   └── BACKEND_LOGIC_ANALYSIS_COMPLETE.md
│   ├── phases/                          # Phase completion docs
│   │   ├── PHASE_4_LFA_COACH_SERVICE_COMPLETE.md
│   │   ├── PHASE_5_LFA_INTERNSHIP_SERVICE_COMPLETE.md
│   │   └── PHASE_6_API_INTEGRATION_COMPLETE.md
│   ├── completed/                       # Completed feature docs
│   │   ├── ADMIN_DASHBOARD_COMPLETE_IMPLEMENTATION.md
│   │   ├── CAMPUS_CRUD_COMPLETE.md
│   │   ├── FINANCIAL_MANAGEMENT_COMPLETE.md
│   │   └── (35+ fájl)
│   └── fixes/                           # Bug fix documentation
│       ├── BROWSER_CACHE_FIX_HUNGARIAN.md
│       ├── SESSION_PERSISTENCE_FIX.md
│       └── (10+ fájl)
│
├── scripts/                             # 🔧 REORGANIZÁLT SCRIPTEK
│   ├── README.md                        # What each script does
│   ├── startup/                         # Startup scripts
│   │   ├── start_backend.sh
│   │   ├── start_streamlit_app.sh
│   │   └── run_backend_now.sh
│   ├── setup/                           # Setup scripts
│   │   └── setup_new_database.sh
│   ├── database/                        # DB maintenance
│   │   ├── create_fresh_database.py
│   │   ├── migrate_instructor_specializations_to_licenses.py
│   │   └── (5+ fájl)
│   ├── admin/                           # Admin utilities
│   │   ├── reset_admin_password.py
│   │   └── (4+ fájl)
│   ├── test_data/                       # Test data creation
│   │   ├── create_test_student.py
│   │   └── create_test_sessions_with_scenarios.py
│   ├── dashboards/                      # Interactive dashboards
│   │   ├── interactive_workflow_dashboard.py
│   │   ├── start_clean_dashboard.sh
│   │   └── (10+ fájl)
│   ├── utility/                         # Misc utilities
│   │   ├── check_api_keys.py
│   │   └── debug_bookings.py
│   └── deprecated/                      # Old/deprecated scripts
│       └── fix_license_endpoints.py
│
├── tests/                               # 🧪 REORGANIZÁLT TESZTEK
│   ├── README.md                        # Test documentation
│   ├── requirements.txt                 # Test dependencies
│   ├── unit/                            # Unit tests
│   │   ├── test_lfa_player_service.py
│   │   ├── test_lfa_coach_service.py
│   │   ├── test_lfa_internship_service.py
│   │   └── (10+ fájl)
│   ├── integration/                     # Integration tests
│   │   ├── test_api_integration.py
│   │   ├── test_semester_generation.py
│   │   └── (15+ fájl)
│   ├── e2e/                             # End-to-end tests
│   │   └── test_complete_quiz_workflow.py
│   ├── scenarios/                       # Test scenarios
│   │   └── (from test_scenarios/)
│   └── performance/                     # Performance tests
│       └── test_session_list_performance.py
│
└── .gitignore                           # 🔥 FRISSÍTENDŐ!
    # Add:
    # __pycache__/
    # venv/
    # logs/
    # *.pyc
    # test_results/
    # test_output.txt
    # test_summary.txt
    # .pytest_cache/
    # streamlit_app_OLD*/
```

---

## 🗑️ TÖRÖLENDŐ ELEMEK

### 1. Backup Mappák
```bash
rm -rf streamlit_app_OLD_20251218_093433/
rm -rf old_reports/
```

### 2. Cache/Temporary Files
```bash
rm -rf __pycache__/
rm -rf logs/  # Ha nem tartalmaz fontos dolgokat
rm -rf test_results/
rm test_output.txt
rm test_summary.txt
```

### 3. Duplicate/Obsolete Docs (Példák)
```bash
# Ellenőrizd hogy van-e újabb verzió!
# Például:
# SESSION_PERSISTENCE_FIX.md vs SESSION_PERSISTENCE_FIX_COMPLETE.md
# → Csak a COMPLETE kell
```

---

## 📦 ÁTMOZGATANDÓ ELEMEK

### Phase 1: Dokumentációk → docs/

```bash
mkdir -p docs/{guides,audits,phases,completed,fixes}

# Guides
mv LOGIN_GUIDE.md docs/guides/
mv STREAMLIT_QUICK_START.md docs/guides/
mv INDITAS.md docs/guides/
mv INVOICE_VS_CREDIT_PURCHASE_EXPLAINED.md docs/guides/

# Audits
mv ADMIN_DASHBOARD_AUDIT_COMPLETE.md docs/audits/
mv DATABASE_AUDIT_SUMMARY.md docs/audits/
mv ADATBAZIS_AUDIT_OSSZEFOGLALO.md docs/audits/
mv BACKEND_LOGIC_ANALYSIS_COMPLETE.md docs/audits/

# Phases
mv PHASE_4_LFA_COACH_SERVICE_COMPLETE.md docs/phases/
mv PHASE_5_LFA_INTERNSHIP_SERVICE_COMPLETE.md docs/phases/
mv PHASE_6_API_INTEGRATION_COMPLETE.md docs/phases/
mv P0_TASKS_COMPLETE.md docs/phases/
mv P1_TASKS_COMPLETE_SUMMARY.md docs/phases/
mv P1_MEDIUM_N+1_FIXES_COMPLETE.md docs/phases/

# Completed Features (35+ fájl!)
mv ADMIN_DASHBOARD_COMPLETE_IMPLEMENTATION.md docs/completed/
mv ADMIN_DASHBOARD_JAVITASOK.md docs/completed/
mv ADMIN_DASHBOARD_REFACTORING_COMPLETE.md docs/completed/
mv AGE_GROUP_CORRECTION_COMPLETE.md docs/completed/
mv BRANDING_UPDATE_COMPLETE.md docs/completed/
mv CAMPUS_CRUD_COMPLETE.md docs/completed/
mv CAMPUS_MIGRATION_COMPLETE.md docs/completed/
mv FINANCIAL_MANAGEMENT_COMPLETE.md docs/completed/
mv LICENSE_DISPLAY_FEATURE_COMPLETE.md docs/completed/
mv LOCATION_MANAGEMENT_COMPLETE.md docs/completed/
mv N+1_FIXES_COMPLETE.md docs/completed/
mv PAYMENT_VERIFICATION_UI_FIX_COMPLETE.md docs/completed/
mv SEMESTER_MANAGEMENT_IMPLEMENTATION_COMPLETE.md docs/completed/
mv SESSION_DISPLAY_FIX_COMPLETE.md docs/completed/
mv STREAMLIT_FRONTEND_PHASE_1_COMPLETE.md docs/completed/
mv STREAMLIT_FRONTEND_PHASE_2_COMPLETE.md docs/completed/
mv STREAMLIT_FRONTEND_REBUILD_COMPLETE.md docs/completed/
mv STREAMLIT_IMPLEMENTATION_REPORT.md docs/completed/
mv STREAMLIT_LOGIN_FIX.md docs/completed/
mv STREAMLIT_LOGIN_INFO.md docs/completed/
mv UI_UX_JAVITASOK.md docs/completed/
mv FRONTEND_REBUILD_COMPLETE.md docs/completed/
mv DASHBOARD_MIGRATION_STRATEGY.md docs/completed/
mv DEPLOYMENT_READY_SUMMARY.md docs/completed/
mv DOCUMENTATION_REORGANIZATION_COMPLETE.md docs/completed/
mv FINANCIAL_MANAGEMENT_TAB_STRUCTURE_COMPLETE.md docs/completed/
mv FINANCIAL_TAB_SIMPLIFICATION.md docs/completed/
mv GYORS_OSSZEFOGLALO.md docs/completed/

# Fixes
mv BROWSER_CACHE_FIX_HUNGARIAN.md docs/fixes/
mv CACHE_PROBLEMA_MEGOLDVA.md docs/fixes/
mv SESSION_PERSISTENCE_FIX.md docs/fixes/
mv SESSION_PERSISTENCE_FIX_COMPLETE.md docs/fixes/
mv INVITATION_CODE_MODAL_FIX.md docs/fixes/
mv DUPLIKACIO_DEBUG.md docs/fixes/

# Keep in root (strategic docs)
# README.md
# START_HERE.md
# PRODUCTION_DEPLOYMENT_CHECKLIST.md
# SPEC_SERVICES_REFACTOR_COMPLETE.md (recent)
# LFA_PLAYER_SEASON_ENROLLMENT_FIX.md (recent)
# KOVETKEZO_LEPESEK_SPEC_SERVICES.md (recent)
# INTERNSHIP_AGE_CORRECTION_FINAL.md (recent)
```

### Phase 2: Scriptek → scripts/

```bash
mkdir -p scripts/{startup,setup,database,admin,test_data,dashboards,utility,deprecated}

# Startup
mv start_backend.sh scripts/startup/
mv start_streamlit_app.sh scripts/startup/
mv start_streamlit_production.sh scripts/startup/
mv run_backend_now.sh scripts/startup/

# Setup
mv setup_new_database.sh scripts/setup/

# Database
mv create_fresh_database.py scripts/database/
mv migrate_instructor_specializations_to_licenses.py scripts/database/
mv migrate_locations_to_campuses.py scripts/database/
mv delete_internship_semester.py scripts/database/
mv create_retroactive_license_transactions.py scripts/database/

# Admin
mv reset_admin_password.py scripts/admin/
mv reset_admin_simple.py scripts/admin/
mv reset_grandmaster_password.py scripts/admin/
mv reset_grandmaster_via_api.py scripts/admin/
mv create_grandmaster_all_licenses.py scripts/admin/

# Test Data
mv create_test_student.py scripts/test_data/
mv create_test_sessions_with_scenarios.py scripts/test_data/

# Dashboards
mv interactive_workflow_dashboard.py scripts/dashboards/
mv credit_purchase_workflow_dashboard.py scripts/dashboards/
mv invitation_code_workflow_dashboard.py scripts/dashboards/
mv session_rules_testing_dashboard.py scripts/dashboards/
mv unified_workflow_dashboard.py scripts/dashboards/
mv unified_workflow_dashboard_improved.py scripts/dashboards/
mv clean_testing_dashboard.py scripts/dashboards/
mv start_clean_dashboard.sh scripts/dashboards/
mv start_improved_dashboard.sh scripts/dashboards/
mv start_credit_purchase_workflow.sh scripts/dashboards/
mv start_interactive_testing.sh scripts/dashboards/
mv start_interactive_workflow.sh scripts/dashboards/
mv start_invitation_workflow.sh scripts/dashboards/
mv start_session_rules_dashboard.sh scripts/dashboards/
mv start_unified_dashboard.sh scripts/dashboards/

# Utility
mv check_api_keys.py scripts/utility/
mv check_api_session_209.py scripts/utility/
mv check_sessions_list_api.py scripts/utility/
mv debug_bookings.py scripts/utility/

# Deprecated
mv fix_license_endpoints.py scripts/deprecated/
```

### Phase 3: Tesztek → tests/

```bash
mkdir -p tests/{unit,integration,e2e,scenarios,performance}

# Unit Tests (Service layer)
mv test_lfa_player_service.py tests/unit/
mv test_lfa_coach_service.py tests/unit/
mv test_lfa_coach_service_simple.py tests/unit/
mv test_lfa_internship_service.py tests/unit/
mv test_gancuju_belt_system.py tests/unit/
mv test_xp_system.py tests/unit/
mv test_teachable_specializations.py tests/unit/

# Integration Tests (API + DB)
mv test_api_integration.py tests/integration/
mv test_api_now.py tests/integration/
mv test_api_quick.py tests/integration/
mv test_semester_generation.py tests/integration/
mv test_hybrid_semester_generation.py tests/integration/
mv test_semester_api.py tests/integration/
mv test_semester_e2e.py tests/integration/
mv test_license_api.py tests/integration/
mv test_license_authorization.py tests/integration/
mv test_license_renewal.py tests/integration/
mv test_payment_codes.py tests/integration/
mv test_assignment_filters.py tests/integration/
mv test_assignment_request.py tests/integration/
mv test_accept_assignment.py tests/integration/
mv test_instructor_requests.py tests/integration/
mv test_instructor_session_edit.py tests/integration/
mv test_enrollments_page.py tests/integration/
mv test_direct_api.py tests/integration/

# E2E Tests (Full workflow)
mv test_complete_quiz_workflow.py tests/e2e/
mv test_session_quiz_access_control.py tests/e2e/
mv test_onsite_workflow.py tests/e2e/

# Performance Tests
mv test_session_list_performance.py tests/performance/

# Test Scenarios
mv test_scenarios/ tests/scenarios/

# Specific feature tests (categorize as needed)
mv test_all_session_types.py tests/integration/
mv test_sessions_detailed.py tests/integration/
mv test_session_rules_comprehensive.py tests/integration/
mv test_generate.py tests/integration/
mv test_pydantic_sem.py tests/unit/
mv test_sem_query.py tests/integration/

# Deprecated/Fix tests
mv test_credit_validation_fix.py tests/deprecated/ || mkdir tests/deprecated && mv test_credit_validation_fix.py tests/deprecated/
mv test_sessions_fix.py tests/deprecated/

# Test dependencies
mv requirements-test.txt tests/requirements.txt
```

---

## 📝 FRISSÍTENDŐ .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# Testing
.pytest_cache/
.coverage
htmlcov/
test_results/
test_output.txt
test_summary.txt
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Database
*.db
*.sqlite

# Streamlit
.streamlit/

# Backups
*_OLD*/
old_reports/

# Environment
.env
.env.local
```

---

## ✅ CLEANUP CHECKLIST

### Pre-Cleanup
- [ ] Git commit jelenlegi állapot (backup!)
- [ ] Ellenőrizd hogy nincs-e pending change
- [ ] Backup kritikus konfigurációk

### Phase 1: Törlések
- [ ] Töröld `streamlit_app_OLD_20251218_093433/`
- [ ] Töröld `old_reports/`
- [ ] Töröld `__pycache__/`
- [ ] Töröld `test_results/`
- [ ] Töröld `test_output.txt`, `test_summary.txt`

### Phase 2: Mappa Struktúra
- [ ] Készítsd el `docs/` almappákat
- [ ] Készítsd el `scripts/` almappákat
- [ ] Készítsd el `tests/` almappákat

### Phase 3: Dokumentáció Átmozgatás
- [ ] Mozgasd guides → `docs/guides/`
- [ ] Mozgasd audits → `docs/audits/`
- [ ] Mozgasd phases → `docs/phases/`
- [ ] Mozgasd completed → `docs/completed/`
- [ ] Mozgasd fixes → `docs/fixes/`

### Phase 4: Script Átmozgatás
- [ ] Mozgasd startup scripts → `scripts/startup/`
- [ ] Mozgasd database scripts → `scripts/database/`
- [ ] Mozgasd admin scripts → `scripts/admin/`
- [ ] Mozgasd dashboard scripts → `scripts/dashboards/`
- [ ] Mozgasd utility scripts → `scripts/utility/`

### Phase 5: Test Átmozgatás
- [ ] Mozgasd unit tests → `tests/unit/`
- [ ] Mozgasd integration tests → `tests/integration/`
- [ ] Mozgasd e2e tests → `tests/e2e/`
- [ ] Mozgasd performance tests → `tests/performance/`
- [ ] Mozgasd test scenarios → `tests/scenarios/`

### Phase 6: Konfigurációk
- [ ] Frissítsd `.gitignore`
- [ ] Készíts `docs/README.md` (index)
- [ ] Készíts `scripts/README.md` (index)
- [ ] Készíts `tests/README.md` (test guide)

### Post-Cleanup
- [ ] Futtass teszteket (győződj meg hogy minden működik)
- [ ] Git commit cleanup változások
- [ ] Frissítsd `README.md` új struktúrával
- [ ] Deployment teszt

---

## 🎯 VÁRHATÓ EREDMÉNY

**Előtte:**
- Root: 122+ fájl
- Káosz, áttekinthetetlen
- Git repo zajos

**Utána:**
- Root: ~10 fájl (README, START_HERE, requirements.txt, recent docs)
- Tiszta kategorizálás
- Professzionális projekt struktúra

**Előnyök:**
- ✅ Könnyen navigálható
- ✅ Deployment egyszerű (csak kell mappák)
- ✅ Új fejlesztők gyorsan megértik a struktúrát
- ✅ Git history tisztább

---

**Készítette:** Claude Code
**Verzió:** 1.0
**Dátum:** 2025-12-20
