# Input Validation Teszt Hibák Részletes Elemzése

## Összefoglaló

**Dátum:** 2026-02-28
**Hibás tesztek száma:** 126
**Teljes tesztszám:** 1736
**Végrehajtott tesztek:** 1298 (74.8%)

### Probléma Definíciója

Az un-skipped input validation tesztek mind **ugyanazzal a problémával** futnak hibára:

```python
# Teszt küld:
payload = {"invalid_field": "invalid_value"}

# Várva: HTTP 422 (Pydantic validation error)
# Kapva: HTTP 200 OK (endpoint elfogadja és ignorálja az extra mezőt)
```

**Gyökér ok:** Pydantic BaseModel alapértelmezetten **engedi az extra mezőket**, hacsak nincs explicit `extra='forbid'` konfiguráció.

---

## Hibák Domainek Szerint (Top 15)

| Domain | Hibás Tesztek | Érintett Endpointok Példái |
|--------|---------------|---------------------------|
| **tournaments** | 11 | update_tournament, accept_instructor_request, apply_to_tournament |
| **instructor_management** | 11 | create_position, respond_to_offer, review_application |
| **instructor** | 7 | evaluate_student_performance, start_session, toggle_specialization |
| **licenses** | 6 | create_skill_assessment, sync_user, advance_license |
| **coupons** | 6 | create_coupon, apply_coupon, validate_coupon |
| **quiz** | 5 | create_quiz, submit_quiz_attempt, unlock_quiz |
| **projects** | 5 | enroll_in_project, approve_milestone, submit_milestone |
| **attendance** | 5 | mark_attendance, checkin, update_attendance |
| **sessions** | 4 | update_session, book_session, check_in_to_session |
| **periods** | 4 | generate_lfa_player_*_season (4 endpoints) |
| **system_events** | 3 | resolve_event, unresolve_event, purge_old_events |
| **specialization** | 3 | motivation_questionnaire, specialization_switch, unlock |
| **semester_enrollments** | 3 | toggle_active, verify_payment, unverify_payment |
| **onboarding** | 3 | set_birthdate, lfa_player_onboarding, select_specialization |
| **invitation_codes** | 3 | create, redeem, validate |

**Összes többi:** 38 teszt 28 különböző domainben (1-2 teszt/domain)

---

## HTTP Metódus Szerinti Bontás

```bash
# Elemzés futtatása
grep "FAILED.*::" test_output.txt | while read line; do
  grep -A 20 "$line" test_file.py | grep "api_client\." | head -1
done | sort | uniq -c
```

**Becsült eloszlás** (manuális mintavétel alapján):
- **POST:** ~90 teszt (71%)
- **PATCH:** ~25 teszt (20%)
- **PUT:** ~11 teszt (9%)

---

## Kritikusság Szerinti Kategorizálás

### 🔴 MAGAS KOCKÁZAT (Security + Business Logic)

**Érintett domainek:** auth, payment_verification, tournaments (enrollment), coupons

**Példák:**
- `auth/logout` - Extra mezők nem befolyásolják a kijelentkezést, **de security audit szempontjából kritikus**
- `coupons/apply_coupon` - Extra mezők potenciálisan manipulálhatják a kedvezmény alkalmazását
- `tournaments/apply_to_tournament` - Extra adatok befolyásolhatják a besorolást
- `payment_verification/unverify_payment` - Pénzügyi tranzakció, szigorú validáció szükséges

**Indok extra='forbid'-re:**
- ✅ Security best practice (OWASP A03:2021 - Injection)
- ✅ Business logic protection (prevent parameter tampering)
- ✅ Clear API contract

---

### 🟡 KÖZEPES KOCKÁZAT (CRUD Operations)

**Érintett domainek:** campuses, locations, groups, messages, notifications

**Példák:**
- `campuses/create_campus` - Admin CRUD, nem kritikus business logic
- `locations/update_location` - Referencia adat módosítás
- `messages/update_message` - Üzenet szerkesztés

**Indok extra='forbid'-re:**
- ✅ Konzisztencia (uniform API behavior)
- ✅ Client-side error prevention
- ⚠️ **Alacsony prioritás** - nem security/business critical

---

### 🟢 ALACSONY KOCKÁZAT (Stateless Actions)

**Érintett domainek:** health, debug, notifications (mark_all_read), gamification

**Példák:**
- `health/run_health_check` - Idempotent, nincs state change
- `debug/log_frontend_error` - Logging endpoint
- `notifications/mark_all_as_read` - Stateless batch operation
- `gamification/refresh_achievements` - Számítás újrafuttatás

**Indok ELLENE extra='forbid':**
- ⚠️ **Szándékos engedékenység lehet** (forward compatibility)
- ⚠️ Debug/logging endpointok extra metaadatot fogadhatnak
- ⚠️ Batch operációk extra flag-eket fogadhatnak

---

## Speciális Esetek Vizsgálata

### 1. Empty Body Endpoints

**Példa:** `auth/logout`, `notifications/mark_all_read`

**Jelenlegi viselkedés:**
```python
# Request
POST /auth/logout
{"invalid_field": "test"}  # ❌ Ignorálva

# Response
200 OK {"message": "Logged out successfully"}
```

**Kérdés:** Van-e business indok az extra mezők engedésére?

**Válasz:** **NINCS.** A logout nem használ request body-t. Az extra mezők ignorálása:
- ❌ Nem ad értéket
- ❌ Security kockázat (client confusion)
- ✅ **Fix:** `extra='forbid'` + empty body validation

---

### 2. Flexible Metadata Endpoints

**Példa:** `debug/log_frontend_error`, `system_events/resolve_event`

**Jelenlegi viselkedés:**
```python
# Request
POST /debug/log-frontend-error
{
  "message": "Error occurred",
  "stack_trace": "...",
  "custom_field_1": "value1",  # Ignorálva
  "custom_field_2": "value2"   # Ignorálva
}
```

**Kérdés:** Szándékos-e az engedékenység?

**Elemzés:**
- **Ha NEM:** Fix: `extra='forbid'`
- **Ha IGEN:** Alternatívák:
  1. Explicit `metadata: Dict[str, Any]` mező a sémában
  2. Dokumentált extra mezők (schema-level examples)
  3. Typed extra fields (Union[KnownField1, KnownField2, ...])

---

### 3. Batch/Bulk Operations

**Példa:** `licenses/sync_all_users`, `periods/generate_*_season`, `license_renewal/bulk_check_expirations`

**Jelenlegi viselkedés:**
```python
# Request
POST /licenses/sync-all-users
{
  "dry_run": false,
  "unknown_flag": true  # ❌ Ignorálva
}
```

**Kérdés:** Forward compatibility szükséges?

**Elemzés:**
- **Bulk operációk:** Gyakran bővülnek új opciókkal
- **Jelenlegi probléma:** Extra mezők **csendesen ignorálva** → client nem tudja, hogy hibás paramétert küldött
- **Fix opciók:**
  1. `extra='forbid'` + explicit new fields (breaking change-kel)
  2. `extra='allow'` + WARNING log unknown fields
  3. Hybrid: `extra='forbid'` + versioned endpoint (`/v2/...`)

---

## Ajánlott Megoldás

### Fázis 1: Azonosítás (KÉSZ ✅)

- [x] 126 sikertelen teszt kategorizálva
- [x] Domainek szerint csoportosítva
- [x] Kockázati szint meghatározva

### Fázis 2: Prioritizált Fixelés

#### 2.1 MAGAS PRIORITÁS (Security + Business Logic) - 35 endpoint

**Azonnal fix szükséges:**

```python
# 1. Adjuk hozzá extra='forbid'-et CSAK ezekhez:
CRITICAL_SCHEMAS = [
    # Auth & Security
    "app/api/api_v1/endpoints/auth.py",
    "app/schemas/user.py:UserUpdate",

    # Payment & Money
    "app/api/api_v1/endpoints/payment_verification.py",
    "app/api/api_v1/endpoints/coupons.py",

    # Tournament Enrollment (business logic critical)
    "app/api/api_v1/endpoints/tournaments/enroll.py",
    "app/api/api_v1/endpoints/tournaments/results/*",

    # Licenses (certification)
    "app/schemas/license.py:SkillAssessmentCreate",
]
```

**Módszer:**
1. Manuálisan add hozzá `model_config = ConfigDict(extra='forbid')` mindegyikhez
2. Futtasd le a CSAK ezekhez tartozó teszteket
3. Fix konfliktuális `class Config:` eseteket (merge json_schema_extra)

#### 2.2 KÖZEPES PRIORITÁS (CRUD) - 60 endpoint

**2 hét múlva fix:**
- Bulk migration script (javított verzió)
- Merge logic `class Config:` + `model_config`

#### 2.3 ALACSONY PRIORITÁS (Stateless) - 31 endpoint

**Döntés szükséges:**
- Egyéni elemzés minden endpointra
- Lehet, hogy szándékos engedékenység
- Alternatív megoldás: `metadata: Dict[str, Any]` explicit mező

---

### Fázis 3: Konfliktusmegoldás

**Probléma:** `class Config:` + `model_config` együtt nem működik

**Megoldás:**

```python
# ELŐTTE
class MyRequest(BaseModel):
    field: str

    class Config:
        json_schema_extra = {"example": {"field": "value"}}

# UTÁNA
class MyRequest(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={"example": {"field": "value"}}
    )

    field: str
```

**Érintett fájlok:** ~25 fájl (gancuju, game_presets, licenses, stb.)

---

## Következő Lépések

### Azonnal (Ma)

1. ✅ **Elemzés dokumentálva** (ez a fájl)
2. ⏳ **Válassz 5 CRITICAL endpointot** manual fixre (teszteld egyesével)
3. ⏳ **Manuálisan fix 5 endpoint sémáját** `extra='forbid'`-del
4. ⏳ **Futtasd le csak ezeket a teszteket** - ellenőrizd, hogy 422-t adnak

### Holnap

5. ⏳ **Bulk script javítás** (merge `class Config:` + `model_config`)
6. ⏳ **Dry-run bulk script** CRITICAL domainen
7. ⏳ **Apply bulk fix** ha dry-run OK

### 1 hét múlva

8. ⏳ **KÖZEPES prioritás fix** (CRUD endpointok)
9. ⏳ **CI/CD validáció** - add hozzá input validation teszteket BLOCKING gate-ként

### 2 hét múlva

10. ⏳ **ALACSONY prioritás egyedi döntések**
11. ⏳ **Dokumentáció frissítés** - API contract clarification

---

## Megjegyzések

### Miért NEM globális fix?

❌ **Problémák global `extra='forbid'`-del:**
1. Breaking change minden kliens számára
2. Nem veszi figyelembe business logic igényeit
3. Debug/logging endpointok elveszítik flexibilitásukat
4. Batch operációk forward compatibility veszélybe kerül

✅ **Miért domain-by-domain?**
1. Kontrollált rollout
2. Business logic tiszteletben tartása
3. Egyedi edge case-ek kezelése
4. Visszagörgethetőség

---

## Példa: Manuális Fix 1 Endpointra

**Endpoint:** `POST /api/v1/tournaments/{id}/apply`
**Séma:** `app/api/api_v1/endpoints/tournaments/enroll.py:TournamentApplicationRequest`

**ELŐTTE:**
```python
class TournamentApplicationRequest(BaseModel):
    motivation: Optional[str] = Field(None, max_length=1000)
    preferred_position: Optional[str] = None
```

**UTÁNA:**
```python
class TournamentApplicationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    motivation: Optional[str] = Field(None, max_length=1000)
    preferred_position: Optional[str] = None
```

**Teszt futtatás:**
```bash
pytest tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_apply_to_tournament_input_validation -xvs
```

**Várva:** ✅ PASSED (422 Validation Error kapva)

---

**Következtetés:** A 126 sikertelen teszt **nem bug, hanem hiányzó input validation**. Nem minden endpoint igényel szigorú validációt, ezért **domain-by-domain, prioritás alapú fix** szükséges, nem automatizált bulk change.
