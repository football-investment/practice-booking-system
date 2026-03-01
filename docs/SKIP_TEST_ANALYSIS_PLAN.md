# Skip Test Elemzés és Tisztítási Terv

**Dátum**: 2026-03-01
**Összesen**: 333 skip test (408 skip reason az auto-generált kódban)
**Cél**: Strukturált döntés a skip tesztek kezeléséről (törlés vs. megtartás vs. implementáció)

---

## Executive Summary

A 333 skip teszt **3 fő kategóriába** sorolható:

| Kategória | Darabszám | Döntés | Indoklás |
|-----------|-----------|--------|----------|
| **Kategória A**: Nem implementált feature-ök | ~150 | ✅ **MEGTART** | Jövőbeli fejlesztéshez kell |
| **Kategória B**: GET/DELETE input validation | ~150 | ❌ **TÖRÖL** | Értelmetlen tesztek (GET nem validál input-ot) |
| **Kategória C**: POST/PATCH/PUT input validation | ~25 | ⚠️ **IMPLEMENTÁL** | Hasznos validáció, implementálni kell |
| **Kategória D**: Műszaki skip-ek | 8 | ✅ **MEGTART** | Indokolt skip (nincs request body, bulk ops) |

---

## Kategória A: Nem Implementált Feature-ök (MEGTART)

### Érintett Domain-ek

| Domain | Skip Count | Skip Reason | Táblák Léteznek? | Javaslat |
|--------|------------|-------------|------------------|----------|
| **curriculum** | 59 | Exercise/Lesson modellek nem léteznek | ❌ NEM | ✅ MEGTART (class-level skip) |
| **curriculum_adaptive** | 22 | Depends on curriculum feature | ❌ NEM | ✅ MEGTART (class-level skip) |
| **competency** | 25 | competency_categories tábla nem létezik | ❌ NEM | ✅ MEGTART (class-level skip) |
| **tracks** | ~10-15 | Track/Module táblák üresek (no seed data) | ✅ IGEN | ✅ MEGTART (seed data kell) |
| **progression** | 10 | Depends on competency | ❌ NEM | ✅ MEGTART (class-level skip) |

**Összesen**: ~150 test

### Indoklás: Miért MEGTART?

1. **Jövőbeli feature backlog**
   - Curriculum, competency, tracks - tervezett feature-ök
   - Auto-generált tesztek később aktiválhatók
   - Nincs értelme törölni és később újra generálni

2. **Dokumentáció értéke**
   - Skip reason egyértelműen jelzi, mi hiányzik
   - Fejlesztők látják, milyen endpoint-ok várnak implementálásra

3. **CI/CD overhead**
   - Class-level skip: ~0.001s/test (pytest collection overhead)
   - Minimális futási idő, nem blokkoló

### Javasolt Akció: NINCS

**Status quo fenntartása:**
- ✅ Megtartjuk a class-level skip decorator-t
- ✅ Skip reason frissítése, ha szükséges
- ✅ Re-enable when feature implemented (future sprint)

---

## Kategória B: GET/DELETE Input Validation (TÖRÖL)

### Probléma

Az auto-generált tesztek minden endpoint-hoz készítenek `test_*_input_validation` tesztet, **még GET/DELETE endpoint-okhoz is**, amelyek **nem validálnak request payload-ot**.

### Példa GET Endpoint Input Validation Test

```python
@pytest.mark.skip(reason="Input validation requires domain-specific payloads")
def test_get_exercise_details_input_validation(
    self,
    api_client: TestClient,
    admin_token: str,
    test_tournament,
):
    """
    Input validation: GET /api/v1/exercise/{exercise_id} validates request data
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # GET/DELETE don't typically have input validation
    pytest.skip("No input validation for GET endpoints")
```

### Érintett Domain-ek (részletes)

| Domain | GET/DELETE Tests | Reasoning |
|--------|------------------|-----------|
| licenses | ~30 | Túlnyomórészt GET endpoint-ok |
| admin | ~18 | Admin dashboard GET endpoint-ok |
| sessions | ~20 | Session query GET endpoint-ok |
| bookings | ~8 | Booking list/details GET endpoint-ok |
| certificates | ~8 | Certificate download GET endpoint-ok |
| quiz | ~15 | Quiz questions GET endpoint-ok |
| projects | ~20 | Project list/details GET endpoint-ok |
| analytics | ~8 | Analytics query GET endpoint-ok |
| **ÖSSZESEN** | **~150** | **GET/DELETE input validation tesztek** |

### Indoklás: Miért TÖRÖL?

1. **Értelmetlen teszt**
   - GET request **NEM tartalmaz request body-t**
   - FastAPI/Pydantic **NEM validál input-ot GET-re**
   - A teszt mindig skip-el magát: `pytest.skip("No input validation for GET endpoints")`

2. **Maintenance overhead**
   - Auto-generátor újra generálja őket
   - Developer confusion: "Miért van skip-elve?"
   - Code bloat: 150 test × ~20 sor = 3000 sor felesleges kód

3. **False signal**
   - Test count elfed hasznos metrikákat
   - "333 skipped" → "150 skipped" sokkal informatívabb

### Javasolt Akció: TÖRLÉS

**Módszer**:

1. **Auto-generátor módosítása**
   - `tools/generate_api_tests.py` frissítése
   - GET/DELETE endpoint-okhoz **NE** generáljon `test_*_input_validation` tesztet
   - Csak POST/PATCH/PUT/DELETE(with body) endpoint-okhoz generáljon

2. **Meglévő tesztek törlése**
   - Batch delete: `test_*_input_validation` GET/DELETE endpoint-okhoz
   - Script készítése: `tools/cleanup_get_input_validation_tests.py`

3. **Verifikáció**
   - Teszt suite újrafuttatása
   - Skipped count: 333 → ~180-200 (várt csökkenés: ~150)

---

## Kategória C: POST/PATCH/PUT Input Validation (IMPLEMENTÁL)

### Probléma

POST/PATCH/PUT endpoint-ok input validation tesztjei **léteznek**, de **skip-elve vannak**:

```python
@pytest.mark.skip(reason="Input validation requires domain-specific payloads")
def test_create_tournament_input_validation(
    self,
    api_client: TestClient,
    admin_token: str,
):
    """
    Input validation: POST /api/v1/tournaments validates request data
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Invalid payload (empty or malformed)
    invalid_payload = {"invalid_field": "invalid_value"}
    response = api_client.post(
        '/api/v1/tournaments',
        json=invalid_payload,
        headers=headers
    )

    # Should return 422 Unprocessable Entity for validation errors
    assert response.status_code in [400, 422], (
        f"POST /api/v1/tournaments should reject invalid payload: {response.status_code}"
    )
```

### Érintett Endpoint-ok (példák)

| Endpoint | Method | Input Validation Test Status | Priority |
|----------|--------|------------------------------|----------|
| POST /api/v1/tournaments | POST | ⏸️ SKIPPED | P1 (HIGH) |
| POST /api/v1/sessions | POST | ⏸️ SKIPPED | P1 (HIGH) |
| PATCH /api/v1/users/{id} | PATCH | ⏸️ SKIPPED | P2 (MEDIUM) |
| POST /api/v1/enrollments | POST | ⏸️ SKIPPED | P1 (HIGH) |
| POST /api/v1/bookings | POST | ⏸️ SKIPPED | P2 (MEDIUM) |

**Összesen**: ~25-30 POST/PATCH/PUT endpoint input validation test

### Indoklás: Miért IMPLEMENTÁL?

1. **Hasznos validáció**
   - Pydantic v2 `extra='forbid'` validációt tesztel
   - Biztonsági teszt: API nem fogad el extra field-eket
   - 422 Unprocessable Entity helyes működését ellenőrzi

2. **Sprint 1 precedens**
   - TICKET-SMOKE-003: `test_specialization_select_submit_input_validation` **RE-ENABLED**
   - Sikeres validáció: 422 response extra field-ekre
   - **Best practice**: Input validation tesztek hasznos védelem

3. **Low effort, high value**
   - Tesztek már léteznek, csak skip-elve vannak
   - Skip decorator eltávolítása: ~5 perc/domain
   - Payload customization: ~10-15 perc/domain (domain-specific invalid data)

### Javasolt Akció: IMPLEMENTÁCIÓ (Phased Approach)

#### Phase 1: Quick Wins (P1 - Core Business Logic)

**Scope**: 10-12 endpoint input validation test re-enable

| Domain | Endpoint-ok | Estimated Effort | Priority |
|--------|------------|------------------|----------|
| tournaments | POST /create, PATCH /update | 30 min | P0 |
| sessions | POST /create, PATCH /update | 30 min | P0 |
| enrollments | POST /enroll, DELETE /unenroll | 30 min | P0 |
| bookings | POST /create, PATCH /update | 20 min | P1 |
| users | PATCH /update, POST /create | 20 min | P1 |

**Total Effort**: 2-3 hours

**Deliverable**: Re-enable 10-12 input validation tests with domain-specific invalid payloads

#### Phase 2: Extended Coverage (P2 - Secondary Features)

**Scope**: 10-15 további endpoint

| Domain | Endpoint-ok | Estimated Effort | Priority |
|--------|------------|------------------|----------|
| licenses | POST /advance, PATCH /update | 30 min | P2 |
| instructor_assignments | POST /assign, PATCH /update | 30 min | P2 |
| quiz | POST /submit, PATCH /update | 30 min | P2 |
| certificates | POST /generate | 20 min | P2 |
| invoices | POST /create, PATCH /verify | 30 min | P2 |

**Total Effort**: 2-3 hours

**Deliverable**: 20-25 total input validation tests re-enabled

#### Phase 3: Comprehensive (P3 - Complete Coverage)

**Scope**: Maradék 5-10 endpoint

**Total Effort**: 1-2 hours

**Deliverable**: Teljes POST/PATCH/PUT input validation coverage

---

## Kategória D: Műszaki Skip-ek (MEGTART)

### Érintett Tesztek (8 darab)

```plaintext
1. POST /{enrollment_id}/verify-payment doesn't require request body
2. POST /{enrollment_id}/unverify-payment doesn't require request body
3. POST /{enrollment_id}/toggle-active doesn't require request body
4. POST /refresh/{id} doesn't require request body (bulk operation)
5. POST /logout doesn't require request body
6. POST /log-error endpoint behavior needs investigation
7. POST /admin/sync/user/{id}/all is bulk operation
8. POST /admin/sync/all is bulk operation
```

### Indoklás: Miért MEGTART?

1. **Legitimate skip reason**
   - POST endpoint **NINCS** request body (action-based endpoint-ok)
   - Bulk operation: user_id path parameter-ben van
   - Input validation értelmetlen (nincs mit validálni)

2. **Endpoint design**
   - Toggle operation: `/toggle-active` → POST **NINCS** body
   - Verify payment: `/verify-payment` → POST **NINCS** body (implicit verification)
   - Logout: `/logout` → POST **NINCS** body (session-based)

3. **Investigation needed**
   - POST /log-error: "needs investigation" → később eldöntendő

### Javasolt Akció: MEGTART (Review)

**Action**:
1. ✅ Megtartjuk a skip-et (indokolt)
2. ⏳ POST /log-error: Investigation ticket létrehozása (P3)

---

## Összefoglaló Ajánlás

### Döntési Mátrix

| Kategória | Darabszám | Akció | Indoklás | Effort | Priority |
|-----------|-----------|-------|----------|--------|----------|
| **A**: Feature skip-ek | ~150 | ✅ **MEGTART** | Jövőbeli feature backlog | 0 óra | N/A |
| **B**: GET/DELETE input validation | ~150 | ❌ **TÖRÖL** | Értelmetlen tesztek | 2-3 óra | P1 |
| **C**: POST/PATCH/PUT input validation | ~25 | ⚠️ **IMPLEMENTÁL** | Hasznos validáció | 4-6 óra | P1-P2 |
| **D**: Műszaki skip-ek | 8 | ✅ **MEGTART** | Indokolt skip | 0 óra | N/A |

### Várható Eredmények

**Előtte**:
- 333 skipped tests
- Signal-to-noise ratio: LOW
- Developer confusion: "Miért van skip-elve?"

**Utána**:
- ~180 skipped tests (Feature skip-ek + Műszaki skip-ek)
- ~25 **AKTÍV** input validation test (POST/PATCH/PUT)
- ~150 **TÖRÖLT** értelmetlen test (GET/DELETE input validation)

**Metrikák**:
- Skipped count: 333 → ~180 (-46%)
- Meaningful skip ratio: 54% → 95%
- Active input validation coverage: 0 → 25 tests

---

## Implementációs Terv (3 Fázis)

### Fázis 1: Értelmetlen Tesztek Törlése (P0 - Immediate)

**Cél**: GET/DELETE input validation tesztek törlése

**Lépések**:

1. **Auto-generátor módosítása** (1 óra)
   - File: `tools/generate_api_tests.py`
   - Logic: Skip `test_*_input_validation` for GET/DELETE methods
   - Validation: Dry-run mode test

2. **Cleanup script készítése** (30 perc)
   - File: `tools/cleanup_get_input_validation_tests.py`
   - Logic: Remove `test_*_input_validation` if method in [GET, DELETE]
   - Safety: Backup before delete

3. **Batch törlés végrehajtása** (30 perc)
   - Backup: `git stash` vagy commit
   - Execute: `python tools/cleanup_get_input_validation_tests.py`
   - Verify: `pytest tests/integration/api_smoke/ -v --tb=no | grep SKIPPED | wc -l`

4. **Teszt suite újrafuttatása** (2 perc)
   - Expected: 333 skipped → ~180 skipped
   - Verify: 0 FAILED tests

**Total Effort**: 2-3 óra

**Deliverable**: 150 értelmetlen teszt törölve, auto-generátor frissítve

---

### Fázis 2: Hasznos Input Validation Tesztek Re-Enable (P1 - High Priority)

**Cél**: POST/PATCH/PUT input validation tesztek aktiválása

**Scope**: Phase 1 (10-12 core endpoint)

**Lépések**:

1. **Domain-specific invalid payload-ok definiálása** (1 óra)
   - tournaments: invalid tournament_type_id, missing required fields
   - sessions: invalid instructor_id, past start_date
   - enrollments: invalid semester_id, negative credits
   - bookings: invalid session_id, double booking
   - users: invalid email format, extra forbidden fields

2. **Skip decorator eltávolítása** (30 perc)
   - Remove `@pytest.mark.skip(reason="Input validation requires domain-specific payloads")`
   - Replace `pytest.skip("...")` with actual test logic

3. **Payload customization** (1 óra)
   - Replace `{"invalid_field": "invalid_value"}` with domain-specific invalid data
   - Example: `{"tournament_type_id": 99999, "extra_field": "forbidden"}`

4. **Teszt suite futtatása** (5 perc)
   - Expected: 10-12 tests **PASSING** (422 validation errors)
   - Verify: No new failures introduced

**Total Effort**: 2.5-3 óra

**Deliverable**: 10-12 input validation test re-enabled and passing

---

### Fázis 3: Extended Coverage (P2 - Medium Priority)

**Cél**: Maradék 10-15 POST/PATCH/PUT input validation test aktiválása

**Scope**: Phase 2 + Phase 3 (~20-25 total)

**Effort**: 2-4 óra (Phase 2 tapasztalat alapján gyorsabb)

**Deliverable**: Teljes POST/PATCH/PUT input validation coverage

---

## Kockázatelemzés

### Kategória A (Feature Skip-ek MEGTART): ✅ ALACSONY KOCKÁZAT

**Kockázat**:
- Nincs kockázat (status quo fenntartása)

**Mitigáció**:
- N/A

---

### Kategória B (GET/DELETE Törlés): ⚠️ KÖZEPES KOCKÁZAT

**Kockázat 1**: Auto-generátor törölhet hasznos teszteket is

**Valószínűség**: Alacsony (GET/DELETE specifikus logic)

**Hatás**: Közepes (hasznos teszt elvesztése)

**Mitigáció**:
- ✅ Dry-run mode: list affected files before delete
- ✅ Git backup: commit before cleanup
- ✅ Manual review: 5-10 teszt manuális ellenőrzése

**Kockázat 2**: Teszt suite törik (import error, syntax error)

**Valószínűség**: Alacsony (tisztán delete operation)

**Hatás**: Közepes (CI failure)

**Mitigáció**:
- ✅ Syntax validation: `python -m py_compile` minden fájlra
- ✅ Pytest collection test: `pytest --collect-only` before commit

---

### Kategória C (POST/PATCH/PUT Re-Enable): ⚠️ KÖZEPES KOCKÁZAT

**Kockázat 1**: Domain-specific payload hibás, teszt FAIL-el

**Valószínűség**: Közepes (payload trial-and-error kell)

**Hatás**: Alacsony (egyszerű fix: payload módosítás)

**Mitigáció**:
- ✅ Incremental approach: 1-2 domain egyszerre
- ✅ Manual testing: curl with invalid payload before test
- ✅ FastAPI docs: `/docs` endpoint payload schema review

**Kockázat 2**: API bug felfedezése (nem ad 422-t invalid payload-ra)

**Valószínűség**: Alacsony (Pydantic v2 szigorú)

**Hatás**: Magas (security issue: API fogad extra field-eket)

**Mitigáció**:
- ✅ **Pozitív kockázat**: Test coverage növelés célja pont ez
- ✅ Bug fix: Add `ConfigDict(extra='forbid')` to Pydantic schema
- ✅ Security improvement: Identify validation gaps

---

## Sikerkritériumok

### Fázis 1 (GET/DELETE Törlés)

- ✅ 150 értelmetlen teszt törölve
- ✅ Skipped count: 333 → ~180
- ✅ Auto-generátor frissítve (GET/DELETE skip input validation generation)
- ✅ 0 FAILED tests (regression check)

### Fázis 2 (POST/PATCH/PUT Re-Enable - Phase 1)

- ✅ 10-12 input validation test re-enabled
- ✅ All tests PASSING (422 validation errors)
- ✅ Domain-specific invalid payloads dokumentálva
- ✅ 0 new FAILED tests

### Fázis 3 (Extended Coverage)

- ✅ 20-25 total input validation tests re-enabled
- ✅ All tests PASSING
- ✅ Comprehensive POST/PATCH/PUT coverage

---

## Következő Lépések

### Azonnali Akciók (Fázis 1 Előkészítés)

1. **User approval kérése**
   - Review this plan
   - Approve Fázis 1 scope (GET/DELETE törlés)
   - Approve Fázis 2 scope (POST/PATCH/PUT re-enable Phase 1)

2. **Git branch létrehozása**
   - Branch: `feature/cleanup-skip-tests-phase-1`
   - Base: `main` (NOT Sprint 1 branch - Sprint 1 merge után)

3. **Backup strategy**
   - Commit before cleanup: "snapshot: before skip test cleanup"
   - Easy rollback if needed

### Timeline

| Fázis | Effort | Start Date | Target Completion |
|-------|--------|------------|-------------------|
| Fázis 1 | 2-3 óra | 2026-03-02 | 2026-03-02 |
| Fázis 2 | 2-3 óra | 2026-03-03 | 2026-03-03 |
| Fázis 3 | 2-4 óra | 2026-03-04 | 2026-03-05 |

**Total**: 6-10 óra work (2-3 nap sprint)

---

## Döntési Pont

**VÁRTUNK USER APPROVAL:**

1. ✅ **Egyetértés Fázis 1-gyel** (GET/DELETE törlés)?
2. ✅ **Egyetértés Fázis 2-vel** (POST/PATCH/PUT re-enable Phase 1)?
3. ⏳ **Fázis 3 opcionális** (extended coverage) - később döntés?

**User válasza után**:
- Ha APPROVED → Fázis 1 implementáció kezdése
- Ha MODIFIED → Terv módosítása user feedback alapján
- Ha REJECTED → Alternative approach discussion

---

**Status**: ✅ **PHASE 1 COMPLETE** - 338 tests removed
**Phase 1 Results**:
- ✅ Removed 338 GET/DELETE input_validation tests (305 GET + 33 DELETE)
- ✅ Preserved 243 POST/PATCH/PUT tests
- ✅ 68 files modified (-4827 lines)
- ✅ Commit: 23f09bf
- ⏳ Phase 2 (Re-enable POST/PATCH/PUT) - DEFERRED to separate PR

**Author**: Claude Sonnet 4.5
**Date**: 2026-03-01 (Phase 1 completed)
