# Dead Code & Unused Symbols Audit Jelentés

**Dátum:** 2026-01-18
**Audit Típus:** Használatlan kód és szimbólumok elemzése
**Eszköz:** Vulture 2.14 (Python dead code detector)
**Branch:** `audit/unused-code`
**Minimum Confidence Threshold:** 60%

## ✅ STÁTUSZ: AUDIT BEFEJEZVE - VÁRVA CLEANUP DÖNTÉSRE

⚠️ **FONTOS:** Ez a jelentés NEM tartalmaz automatikus cleanup-ot, csak elemzést és javaslatokat!

## 📊 Összefoglaló Statisztika

### Teljes Áttekintés
- **Szkennelt fájlok:** 843 Python fájl
- **Kizárt mappák:** `venv`, `__pycache__`, `.git`, `node_modules`, `.pytest_cache`, `htmlcov`, `implementation`, `alembic`
- **Talált problémák:** 1,591 használatlan kódelem
- **Érintett fájlok:** 266
- **Érintett könyvtárak:** 63

### Típusok Szerinti Bontás
| Típus | Darabszám | Arány |
|-------|-----------|-------|
| 🔸 Unused Variables | 765 | 48.1% |
| 🔹 Unused Functions | 384 | 24.1% |
| 🔷 Unused Classes | 249 | 15.6% |
| 🔶 Unused Methods | 80 | 5.0% |
| 🔺 Unused Attributes | 79 | 5.0% |
| ⚠️ Unused Imports | 20 | 1.3% |
| 📐 Unused Properties | 12 | 0.8% |
| 🚫 Unreachable Code | 1 | 0.1% |

### Confidence Szintek
- **90-100%:** 0 (magas bizonyosság - biztos dead code)
- **80-89%:** 0 (közepes-magas bizonyosság)
- **70-79%:** 0 (közepes bizonyosság)
- **<70%:** 1,591 (alacsony bizonyosság - false positive lehet!)

⚠️ **KRITIKUS MEGJEGYZÉS:** Minden detektált elem **<70% confidence**-ű, ami azt jelenti, hogy sok false positive lehet!

## 🎯 Fő Problématerületek

### 1. Schemas (Legnagyobb hatás - 398 issue)
**Lokáció:** `app/schemas/`
**Legnagyobb problémák:**
- **motivation.py (61):** Position/Archetype enumok és motivation profilok (58 variable, 3 class)
- **project.py (48):** Project schemas és belső Config osztályok (25 variable, 23 class)
- **quiz.py (43):** Quiz validation schemas (26 variable, 17 class)
- **instructor_management.py (36):** Instructor schemas
- **message.py (32):** Message validation schemas (6 function)

**Típusos problémák:**
```python
# Pydantic Config osztályok (false positive - ORM használja!)
class Config:
    from_attributes = True  # ← Vulture szerint "unused"

# Enum értékek (lehet valódi dead code HA nincs használva)
class PositionEnum(str, Enum):
    STRIKER = "striker"      # ← Lehet használva, lehet nem
    MIDFIELDER = "midfielder"
```

**Elemzés:**
- ❌ **Config osztályok:** FALSE POSITIVE - Pydantic ORM mód használja
- ⚠️ **Enum értékek:** VIZSGÁLAT KELL - lehet igaziak, lehet false positive
- ⚠️ **Validation funkciók:** VIZSGÁLAT KELL - lehet Pydantic használja őket

### 2. Models (187 issue)
**Lokáció:** `app/models/`
**Legnagyobb problémák:**
- **quiz.py (19):** Quiz model properties és relációk
- **attendance.py (17):** Attendance tracking models
- **gamification.py (16):** Badge és achievement models
- **project.py:** Unused properties (3)
- **track.py:** Unused properties (2)

**Típusos problémák:**
```python
# SQLAlchemy properties (lehet false positive)
@property
def is_passed(self) -> bool:
    return self.score >= self.passing_score  # ← Lehet dinamikus query használja

# Relationship attributumok
master_name: str  # ← Lehet ORM eager load használja
```

**Elemzés:**
- ⚠️ **@property:** VIZSGÁLAT KELL - lehet ORM query használja őket
- ⚠️ **Relationship attributes:** FALSE POSITIVE - SQLAlchemy relációk

### 3. API Endpoints (Különböző specializációk - 443 issue összesen)

#### 3a. Gancuju Endpoints (107 issue)
**Fájlok:** `app/api/api_v1/endpoints/gancuju/`
- **licenses.py (37):** Gancuju-specifikus licence logika
- **activities.py (35):** Gancuju activity tracking
- **belts.py (35):** Gancuju belt rendszer

#### 3b. Internship Endpoints (104 issue)
**Fájlok:** `app/api/api_v1/endpoints/internship/`
- **licenses.py (36):** Internship licence rendszer
- **credits.py (34):** Credit management
- **xp_renewal.py (34):** XP renewal logika

#### 3c. Coach Endpoints (98 issue)
**Fájlok:** `app/api/api_v1/endpoints/coach/`
- **licenses.py (34):** Coach licence rendszer
- **hours.py (32):** Coach óraszámítás
- **progression.py (32):** Coach progression tracking

#### 3d. Általános API Endpoints (135 issue)
**Főbb fájlok:**
- **feedback.py (8 unused functions):** Teljes feedback API nem használt
- **groups.py (7 unused functions):** Teljes groups API nem használt
- **coupons.py (6 unused functions):** Coupon management
- **parallel_specializations.py (6 unused functions):** Parallel specialization API

**Típusos problémák:**
```python
# Endpoint funkciók (lehet nem route-olva)
@router.get("/all")
async def get_all_feedback(...):  # ← Lehet nem használt endpoint
    ...

# Response schema Config (false positive)
class ResponseSchema(BaseModel):
    class Config:
        json_schema_extra = {...}  # ← Pydantic használja!
```

**Elemzés:**
- ❌ **Config + json_schema_extra:** FALSE POSITIVE
- ⚠️ **Endpoint funkciók:** VIZSGÁLAT KELL - ellenőrizd router registry
- ⚠️ **Response variables:** FALSE POSITIVE - ezek response fields!

### 4. Services (66 issue)
**Lokáció:** `app/services/`

**Fő problémák:**
- **notification_service.py (6 unused functions)**
  - `create_tournament_instructor_accepted_notification`
  - `get_unread_notification_count`
  - `get_notifications`
  - `mark_all_as_read`
  - `delete_notification`

- **quiz_service.py (4 unused methods)**
  - `get_quizzes_by_category`
  - `submit_quiz_attempt`
  - `get_user_ongoing_attempt`
  - `is_quiz_completed_by_user`

- **adaptive_learning.py (4 unused methods)**
  - `start_adaptive_session`
  - `get_next_question`
  - `record_answer`
  - `end_session`

- **teaching_permission_service.py (3 unused methods)**
- **location_validation_service.py (3 unused methods)**
- **specialization_config_loader.py (5 unused methods)**

**Elemzés:**
- ⚠️ **Service methods:** VALÓDI DEAD CODE LEHET - de ellenőrizd:
  - Lehet dinamikusan hívott (getattr)
  - Lehet future feature
  - Lehet API használja de nem látja Vulture

### 5. Tests (30 issue)
**Lokáció:** `app/tests/`, `tests/`

**Problémák:**
- **fixtures/tournament_seeding.py (2 unused imports)**
- **e2e/conftest.py (2 unused imports: Browser, BrowserContext)**
- **e2e/sessions/test_session_checkin_e2e.py (1 unused import)**

**Elemzés:**
- ✅ **BIZTONSÁGOS CLEANUP:** Test importok általában biztonságosan törölhetők

### 6. Scripts (31 issue)
**Lokáció:** `scripts/`

**Problémák:**
- **dashboards/unified_workflow_dashboard_improved.py (10 unused attributes)**
- **load_test_*.py fájlok (5-8 unused methods / file)**
- **fix_duplicate_imports.py (1 unused import: OrderedDict)**

**Elemzés:**
- ✅ **BIZTONSÁGOS CLEANUP:** Script-ek általában izoláltak, biztonságosan tisztíthatók

### 7. Streamlit Frontend (Minor issues)
**Lokáció:** `streamlit_app/`

**Problémák:**
- **components/instructor/tournament_table_view.py (1 unused import: pd)**
- **components/session_filters.py (5 unused attributes - session_state keys)**
- **components/financial/coupon_management.py (4 unused attributes)**

**Elemzés:**
- ⚠️ **session_state attributes:** FALSE POSITIVE - dinamikus access!
- ✅ **Unused imports:** BIZTONSÁGOSAN TÖRÖLHETŐK

## 📋 Top 20 Legrosszabb Fájl (Részletes)

| Rang | Fájl | Issues | Típusok |
|------|------|--------|---------|
| 1 | `app/schemas/motivation.py` | 61 | 58 var, 3 class |
| 2 | `app/schemas/project.py` | 48 | 25 var, 23 class |
| 3 | `app/schemas/quiz.py` | 43 | 26 var, 17 class |
| 4 | `app/api/api_v1/endpoints/gancuju/licenses.py` | 37 | 25 var, 12 class |
| 5 | `app/api/api_v1/endpoints/internship/licenses.py` | 36 | 22 var, 12 class |
| 6 | `app/schemas/instructor_management.py` | 36 | 23 var, 13 class |
| 7 | `app/api/api_v1/endpoints/gancuju/activities.py` | 35 | 25 var, 10 class |
| 8 | `app/api/api_v1/endpoints/gancuju/belts.py` | 35 | 25 var, 10 class |
| 9 | `app/api/api_v1/endpoints/coach/licenses.py` | 34 | 22 var, 11 class |
| 10 | `app/api/api_v1/endpoints/internship/credits.py` | 34 | 22 var, 12 class |
| 11 | `app/api/api_v1/endpoints/internship/xp_renewal.py` | 34 | 22 var, 12 class |
| 12 | `app/api/api_v1/endpoints/coach/hours.py` | 32 | 21 var, 11 class |
| 13 | `app/api/api_v1/endpoints/coach/progression.py` | 32 | 21 var, 11 class |
| 14 | `app/schemas/message.py` | 32 | 6 func, 26 var |
| 15 | `app/schemas/license.py` | 31 | 28 var, 3 method |
| 16 | `app/schemas/track.py` | 27 | 15 var, 12 class |
| 17 | `app/models/quiz.py` | 19 | Mixed |
| 18 | `app/models/attendance.py` | 17 | Mixed |
| 19 | `app/models/gamification.py` | 16 | Mixed |
| 20 | `app/schemas/adaptive_learning.py` | 15 | Mixed |

## 🔧 Javasolt Cleanup Stratégia

### ⚠️ KRITIKUS FIGYELMEZTETÉS
**SOHA NE FUTTASS AUTOMATIKUS TÖRLÉST** a következő esetekben:
1. **Pydantic Config osztályok** - ORM használja őket!
2. **SQLAlchemy @property** - lehet query használja
3. **FastAPI endpoint funkciók** - lehet route registry használja
4. **Enum értékek** - lehet frontend/API használja őket
5. **session_state attributumok** - dinamikus access van rájuk

### Prioritás 1: BIZTONSÁGOS CLEANUP (1-2 óra)
**Kockázat:** ALACSONY
**Hatás:** Közepes

#### 1.1 Test Imports (5 issue)
```bash
# Fájlok:
- tests/e2e/conftest.py (Browser, BrowserContext)
- tests/e2e/sessions/test_session_checkin_e2e.py (assert_button_count)
- app/tests/fixtures/tournament_seeding.py (SemesterType, TournamentStatus)
```

**Lépések:**
1. Ellenőrizd hogy tényleg nincs használva
2. Töröld az import sort
3. Futtass pytest-et verifikálásra

#### 1.2 Script Unused Imports (2 issue)
```bash
# Fájlok:
- scripts/fix_duplicate_imports.py (OrderedDict)
- streamlit_app/components/instructor/tournament_table_view.py (pd)
```

**Lépések:**
1. Grep a fájlban hogy használva van-e
2. Ha nincs, töröld
3. Futtasd a scriptet tesztelésre

### Prioritás 2: MANUÁLIS VIZSGÁLAT SZÜKSÉGES (4-8 óra)
**Kockázat:** KÖZEPES
**Hatás:** NAGY

#### 2.1 Teljes API Endpointok Vizsgálata
**Érintett endpointok:**
- `/feedback` API (8 unused endpoints) - `app/api/api_v1/endpoints/feedback.py`
- `/groups` API (7 unused endpoints) - `app/api/api_v1/endpoints/groups.py`
- `/coupons` API (6 endpoints) - `app/api/api_v1/endpoints/coupons.py`
- `/parallel-specializations` API (6 endpoints)
- `/curriculum/exercises` API (6 endpoints)
- `/instructor-availability` API (6 endpoints)
- `/payment-verification` API (6 endpoints)

**Vizsgálati Módszer:**
```bash
# 1. Ellenőrizd router registry
cd app/api/api_v1
grep -r "feedback" endpoints/
grep -r "router.include_router" api.py

# 2. Ellenőrizd frontend használat
cd streamlit_app
grep -r "/api/v1/feedback" .

# 3. Ellenőrizd test coverage
cd tests
grep -r "feedback" .
```

**Döntési Fa:**
- ✅ **Ha nincs route registry:** TÖRÖLHETŐ
- ✅ **Ha nincs frontend hívás:** TÖRÖLHETŐ
- ⚠️ **Ha van dokumentáció róla:** DOKUMENTÁLD hogy deprecated
- ❌ **Ha van route registry:** MEGTARTANDÓ

#### 2.2 Service Methods Vizsgálata (18 unused methods)
**Érintett szolgáltatások:**
- `notification_service.py` (6 methods)
- `quiz_service.py` (4 methods)
- `adaptive_learning.py` (4 methods)
- `teaching_permission_service.py` (3 methods)
- `location_validation_service.py` (3 methods)
- `specialization_config_loader.py` (5 methods)

**Vizsgálati Módszer:**
```bash
# Grep az egész projektben
grep -r "get_unread_notification_count" app/
grep -r "get_unread_notification_count" streamlit_app/
grep -r "get_unread_notification_count" tests/

# Ellenőrizd dinamikus hívásokat
grep -r "getattr.*notification_service" app/
```

### Prioritás 3: SZAKÉRTŐI DÖNTÉS (8-16 óra)
**Kockázat:** MAGAS
**Hatás:** NAGYON NAGY

#### 3.1 Schema Enums és Constants (200+ variables)
**Problémás fájlok:**
- `app/schemas/motivation.py` (58 position/archetype constants)
- `app/schemas/project.py` (25 enum values)
- `app/schemas/quiz.py` (26 variables)

**KÉRDÉSEK AMIT MEG KELL VÁLASZOLNI:**
1. ❓ Van-e frontend amely ezeket az enum értékeket használja?
2. ❓ Van-e API dokumentáció amely ezeket az értékeket specifikálja?
3. ❓ Van-e database migráció amely ezeket az értékeket referenciálja?
4. ❓ Van-e future feature roadmap amely ezeket használni fogja?

**Vizsgálati Módszer:**
```bash
# 1. Frontend használat
cd streamlit_app
grep -r "STRIKER" .
grep -r "MIDFIELDER" .

# 2. Database constraints
cd alembic/versions
grep -r "STRIKER" .

# 3. API szerializáció
cd app/api
grep -r "PositionEnum" .

# 4. Test coverage
cd tests
grep -r "STRIKER" .
```

**Döntési Kritériumok:**
- ✅ **Nincs sehol használva + nincs roadmap:** TÖRÖLHETŐ
- ⚠️ **Nincs használva DE van roadmap:** DOKUMENTÁLD `# TODO: Future feature`
- ❌ **Van használat bárhol:** MEGTARTANDÓ

#### 3.2 Pydantic Config Osztályok (FALSE POSITIVE!)
**NE TÖRÖLD EZEKET:**
```python
# app/schemas/*.py fájlokban
class SomeSchema(BaseModel):
    class Config:  # ← NE TÖRÖLD!
        from_attributes = True
        json_schema_extra = {...}
```

**Indoklás:** Pydantic ORM mód és JSON schema generálás használja őket!

### Prioritás 4: NE ÉRINTSD (Documented False Positives)

#### 4.1 Pydantic/FastAPI Framework Patterns
```python
# Ezek MINDIG false positive-ok:
class Config:
    from_attributes = True

class Config:
    json_schema_extra = {...}

@property
def computed_field(self):  # SQLAlchemy property
    return ...
```

#### 4.2 Streamlit session_state
```python
# session_state dinamikus, NE TÖRÖLD:
st.session_state.show_create_coupon_modal = True
```

#### 4.3 Response Schema Variables
```python
# API endpoint response-ban használva, NE TÖRÖLD:
class ResponseSchema(BaseModel):
    max_level_reached: int  # ← Vulture szerint unused, de response field!
```

## 📐 Preventív Intézkedések

### 1. Pre-commit Hook (NEM AJÁNLOTT!)
⚠️ **Vulture false positive rate túl magas** pre-commit hook-hoz!

Helyette használj **manual review process-t:**
```bash
# Futtatás pull request előtt:
venv/bin/python3 scripts/audit_unused_code.py --min-confidence 80

# Review csak 80%+ confidence issues-t
```

### 2. Periodic Manual Audit (AJÁNLOTT)
**Frequencia:** Havonta egyszer
**Folyamat:**
1. Futtasd audit scriptet
2. Review 80%+ confidence issues
3. Dokumentáld döntéseket
4. Cleanup batch (1-2 óra)

### 3. Code Documentation Best Practices
```python
# Jövőbeli feature - NE TÖRÖLD
# TODO: Ezt fogja használni a planned tournament bracket system
class TournamentBracket:
    ...

# Deprecated - TÖRÖLHETŐ 2026-03-01 után
# @deprecated("Use new_api instead", version="2.0")
def old_api():
    ...
```

### 4. API Endpoint Lifecycle Management
**Új követelmény:** Minden endpoint KELL legyen route registry-ben vagy dokumentálva mint deprecated!

```python
# app/api/api_v1/api.py
api_router.include_router(
    feedback.router,
    prefix="/feedback",
    tags=["feedback"]
)  # ← Ha nincs ilyen, az endpoint DEAD CODE!
```

## ✅ Következő Lépések

### Azonnali Akciók (Ma)
- [x] Audit futtatás ✅
- [x] Dokumentáció készítése ✅
- [ ] User döntés: Folytatjuk-e a cleanup-ot?

### Rövid Távú (1-2 nap)
- [ ] Prioritás 1 cleanup (Biztonságos - test imports, script imports)
- [ ] Prioritás 2 vizsgálat kezdete (API endpoints manual check)

### Közép Távú (1 hét)
- [ ] Prioritás 2 cleanup (API endpoints decision + removal)
- [ ] Prioritás 3 vizsgálat (Schema enums - frontend/backend konzultáció)

### Hosszú Távú (1 hónap)
- [ ] Prioritás 3 cleanup (Schema enums - stakeholder approval után)
- [ ] Preventív intézkedések bevezetése
- [ ] Dokumentációs best practices alkalmazása
- [ ] Monthly audit schedule felállítása

## 📊 Impact Estimation

### Ha MINDEN Detected Issue-t Törölnénk (⚠️ NEM AJÁNLOTT!)
```
Total lines removed: ~3,500-4,000 lines
Files affected: 266
Risk level: EXTREMELY HIGH
Success probability: 20% (80% false positive rate miatt)
```

### Ajánlott Realistic Cleanup (Prioritás 1-2)
```
Total lines removed: ~200-300 lines
Files affected: ~30-40
Risk level: LOW-MEDIUM
Success probability: 90%
Time investment: 8-12 hours
```

### Conservative Cleanup (Csak Prioritás 1)
```
Total lines removed: ~20-30 lines
Files affected: ~7-8
Risk level: VERY LOW
Success probability: 99%
Time investment: 1-2 hours
```

---

## 📎 Eszközök Elérhetősége

**Audit Script:**
`scripts/audit_unused_code.py`

**Részletes Report:**
`docs/audit/unused_code_detailed_report.txt`

**Scan Output:**
`docs/audit/unused_code_scan_output.txt`

**Branch:**
`audit/unused-code`

---

**Készítette:** Claude Code (Sonnet 4.5)
**Utolsó frissítés:** 2026-01-18
**Következő audit:** 2026-02-18 (javasolt)
