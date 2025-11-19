# ❓ Határeset Kérdések - Részletes Válaszok

## 📋 Tartalom

Ez a dokumentum válaszol a felvetett határeset kérdésekre, és összefoglalja a jelenlegi rendszer viselkedését.

---

## 🎯 1. ADATFORRÁS ÉS SZINKRONIZÁCIÓS SZENÁRIÓK

### ❓ Mi történik, ha az adatbázisban egy új szint szerepel, amit a `LicenseSystemHelper` még nem ismer?

**Válasz**: ❌ **BLOKKOLVA**

**Jelenlegi működés**:
```python
# Új szint az adatbázisban
INSERT INTO player_levels (id=9, name='Level 9', ...)

# Helper továbbra is
max_levels = {"PLAYER": 8}  # Hardcoded!

# Validáció
validate_advancement(current=8, target=9, max=8)
→ False, "Maximum level for this specialization is 8"
```

**Következmények**:
- ✅ `get_level_requirements(PLAYER, 9)` → **MŰKÖDIK** (DB query)
- ❌ Frontend látja a szintet, de user **NEM TUD RÁLÉPNI**
- ❌ Admin manuális level set is blokkolva

**Fix**: Lásd [EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md](EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md#11-új-szint-az-adatbázisban-amit-a-helper-nem-ismer)

---

### ❓ Mi történik, ha egy szintet törlünk az adatbázisból, de a helper továbbra is hivatkozik rá?

**Válasz**: ⚠️ **RÉSZBEN MŰKÖDIK, DE VESZÉLYES**

**Jelenlegi működés**:
```sql
DELETE FROM player_levels WHERE id = 5;
```

**Backend reakció**:
```python
# Service
get_level_requirements('PLAYER', 5)
→ None  # ✅ Helyes kezelés

# Validáció
can_level_up(progress) # current_level=4
→ False  # ✅ Nem engedi 5-re lépni
```

**DE**: Mi van a meglévő user-ekkel?
```python
# User current_level = 5 (orphan!)
progress = SpecializationProgress(
    student_id=123,
    current_level=5  # ← Ez a szint már NEM LÉTEZIK!
)

# Frontend kérés
get_student_progress(123, 'PLAYER')
→ current_level: None  # ❌ Frontend crash lehetséges
```

**Probléma**: **NINCS** Foreign Key constraint!

**Fix szükséges**:
```sql
ALTER TABLE specialization_progress
ADD CONSTRAINT fk_check_player_level
FOREIGN KEY (current_level)
REFERENCES player_levels(id)
ON DELETE RESTRICT;  -- NE engedje törölni használt szintet
```

---

### ❓ Ha egy `max_level` érték eltér a két helyen, melyik forrás élvez prioritást a validáció során?

**Válasz**: 🔴 **MINDIG A HELPER (HARDCODED) - Ez a probléma!**

**Példa - INTERNSHIP konfliktus**:
```python
# Adatbázis
SELECT COUNT(*) FROM internship_levels;
→ 3 szint (id: 1, 2, 3)

# Helper
max_levels = {"INTERNSHIP": 5}  # ← Hardcoded

# Migration comment
"""Startup Spirit Internship levels (3 levels)"""  # ← Dokumentáció szerint 3!
```

**Jelenlegi prioritás sorrend**:
1. **Validációnál**: Helper (5) ← **Ez fut először**
2. **Adat lekérésnél**: DB (3)

**Következmény**:
```python
# User próbál level 4-re lépni
validate_advancement(current=3, target=4, max=5)
→ True  # ✅ Validáció ENGEDÉLYEZI (max=5)

# DE:
get_level_requirements('INTERNSHIP', 4)
→ None  # ❌ Nincs ilyen szint a DB-ben (csak 3 van)

# Frontend
progress.next_level = None  # ❌ Üres adat
```

**Fix**: [Dinamikus max_level lekérdezés](EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md#13-ellentmondás-a-max_level-értékekben)

---

### ❓ Mi történik, ha a `license_metadata` tábla üres, de a specialization-adatok elérhetők?

**Válasz**: ✅ **MŰKÖDIK, DE UX PROBLÉMA**

**Jelenlegi működés**:
```python
# app/services/license_service.py:25-35
licenses = db.query(LicenseMetadata).filter(
    LicenseMetadata.specialization_type == 'PLAYER'
).all()

return [license.to_dict() for license in licenses]
→ []  # Üres lista
```

**Frontend kap**:
```json
{
  "licenses": [],
  "current_level": {
    "name": "Bambusz Tanítvány",
    "required_xp": 12000
    // DE: nincs marketing_narrative, icon_emoji, stb.
  }
}
```

**Következmények**:
- ✅ Nem crashel
- ❌ Nincs színes badge
- ❌ Nincs marketing szöveg
- ❌ Nincs kulturális kontextus

**Fallback opciók**:
1. Generálj default metadata-t a level táblákból
2. Hardcoded fallback színek/ikonok
3. Frontend default szövegek

---

## 🧭 2. HALADÁS ÉS VALIDÁCIÓS SZENÁRIÓK

### ❓ Mi történik, ha a user XP-je eléri a követelményt, de nincs rögzítve a szükséges óraszám (`practice_hours`)?

**Válasz**: ✅ **HELYESEN BLOKKOLJA**

**Példa (COACH specializáció)**:
```python
progress = SpecializationProgress(
    specialization_id='COACH',
    current_level=1,
    total_xp=15000,  # ✅ Elég (requirement: 15000)
    completed_sessions=15,  # ✅ Elég
    theory_hours_completed=0,  # ❌ Kellene: 30
    practice_hours_completed=0  # ❌ Kellene: 50
)

# Validáció
can_level_up(progress)
→ False
```

**Kód (app/services/specialization_service.py:190-194)**:
```python
if progress.specialization_id == 'COACH':
    can_level = can_level and (
        progress.theory_hours_completed >= next_level_req.get('theory_hours', 0) and
        progress.practice_hours_completed >= next_level_req.get('practice_hours', 0)
    )
```

**Frontend látja**:
```json
{
  "can_level_up": false,
  "theory_hours_needed": 30,
  "practice_hours_needed": 50,
  "xp_needed": 0,
  "sessions_needed": 0
}
```

✅ **Tökéletesen működik!**

---

### ❓ Mi történik, ha valaki átugrik egy szintet (pl. `level_id + 2`)?

**Válasz**: ✅ **BLOKKOLVA**

**Manuális próbálkozás**:
```python
# User current_level = 3
advance_license(user_id=123, specialization='PLAYER', target_level=5)

# Validáció (app/models/license.py:244-246)
if target_level > current_level + 1:
    return False, "Can only advance one level at a time"

→ HTTPException(400, "Can only advance one level at a time")
```

**Automatikus level up**:
```python
# app/services/specialization_service.py:246-249
while self.can_level_up(progress):
    progress.current_level += 1  # Egyesével!
    leveled_up = True
    levels_gained += 1
```

✅ **Biztonságos, step-by-step**

---

### ❓ Engedi-e a rendszer, hogy a user „visszalépjen" egy korábbi szintre?

**Válasz**: ❌ **NEM ENGEDI**

**Próbálkozás**:
```python
# User current_level = 5
advance_license(user_id=123, specialization='PLAYER', target_level=3)

# Validáció
if target_level <= current_level:
    return False, "Target level must be higher than current level"
```

**DE**: ❓ **Mi van admin downgrade esetén?**

**Hiányzó funkciók**:
- Admin által kezdeményezett visszasorolás
- Téves szintadás javítása
- Fegyelmi eljárás miatti visszaléptetés
- Level reset funkció

**Javasolt megoldás**: [Admin downgrade API](EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md#23-visszalépés-korábbi-szintre)

---

### ❓ Ha a `required_sessions` mező 0, akkor automatikus előrelépés történik, vagy blokkol?

**Válasz**: ✅ **AUTOMATIKUS ELŐRELÉPÉS** (matematikailag helyes)

**Szenárió**:
```sql
UPDATE player_levels
SET required_sessions = 0
WHERE id = 1;
```

**Validáció**:
```python
can_level = (
    progress.total_xp >= next_level_req['required_xp'] and
    progress.completed_sessions >= next_level_req['required_sessions']
    # 0 >= 0 → True!
)
```

**Kérdés**: Szándékos vagy hiba?

**Vélemény**:
- Ha szándékos (pl. bonus level): ✅ Működik
- Ha hiba: ❌ Biztonsági kockázat

**Ajánlott**: DB constraint
```sql
ALTER TABLE player_levels
ADD CONSTRAINT check_positive_requirements
CHECK (required_sessions > 0 AND required_xp > 0);
```

---

## 🧩 3. LICENSE-KEZELÉSI SZENÁRIÓK

### ❓ Mi történik, ha egy licenszhez nincs `marketing_narrative` megadva?

**Válasz**: ✅ **MŰKÖDIK, DE ÜRES**

**Adatbázis**:
```sql
UPDATE license_metadata
SET marketing_narrative = NULL
WHERE id = 1;
```

**API Response**:
```json
{
  "id": 1,
  "title": "Bambusz Tanítvány",
  "marketing_narrative": null,  // ← NULL érték
  "icon_emoji": "🤍"
}
```

**Frontend megjelenítés**:
```javascript
<p>{license.marketing_narrative || "Complete this level to progress."}</p>
```

✅ **Frontend fallback szükséges, de működőképes**

---

### ❓ Mi történik, ha a `LicenseMetadata` rekord hibás JSON-t tartalmaz a `advancement_criteria` mezőben?

**Válasz**: 🔴 **POSTGRES VÉDI, DE CRASH LEHETSÉGES**

**PostgreSQL védelem**:
```sql
-- Ez NEM megy át
UPDATE license_metadata
SET advancement_criteria = '{invalid json'
WHERE id = 1;

→ ERROR: invalid input syntax for type json
```

**SQLAlchemy error**:
```python
try:
    licenses = db.query(LicenseMetadata).all()
except DataError as e:
    # ❌ NINCS ERROR HANDLING!
    # Exception propagálódik → HTTP 500
```

**Fix szükséges**:
```python
try:
    licenses = db.query(LicenseMetadata).filter(...).all()
    return [license.to_dict() for license in licenses]
except (DataError, JSONDecodeError) as e:
    logger.error(f"Invalid JSON in license_metadata: {e}")
    return []  # Vagy fallback
```

**Ritkán fordul elő**: PostgreSQL JSONB típus elég biztonságos

---

### ❓ Ha egy user több specializációhoz is rendelkezik licensszel, hogyan választja ki az aktívat a rendszer?

**Válasz**: ℹ️ **NINCS "AKTÍV" KONCEPCIÓ - Párhuzamos track-ek**

**Design**:
```python
# User-nek lehet
user_licenses = [
    UserLicense(user_id=123, specialization='PLAYER', current_level=5),
    UserLicense(user_id=123, specialization='COACH', current_level=3)
]

# Mindegyik önálló, nincs "primary"
```

**Frontend kérés**:
```python
# Explicit specialization-t kér
GET /api/v1/licenses/PLAYER
GET /api/v1/licenses/COACH
```

**Dashboard**: Mindkettőt mutatja

**Hiányzó funkció**: User preferencia (pl. "primary specialization badge")

**Javasolt**:
```sql
ALTER TABLE users
ADD COLUMN primary_specialization VARCHAR(20);
```

---

### ❓ Mi történik, ha a userhez még nincs `user_licenses` rekord, de progression-adat már van?

**Válasz**: 🔴 **KRITIKUS - KÉT KÜLÖN RENDSZER!**

**Jelenlegi állapot**:

1. **SpecializationProgress** (player_levels alapú):
```python
progress = SpecializationProgress(
    student_id=123,
    specialization_id='PLAYER',
    current_level=5
)
```

2. **UserLicense** (license_metadata alapú):
```python
license = UserLicense(
    user_id=123,
    specialization_type='PLAYER',
    current_level=3  # ← ELTÉRŐ!
)
```

**Probléma**: **NINCS SZINKRONIZÁCIÓ**

**Következmények**:
- Frontend progress-t mutat: level 5
- Frontend badge-t mutat: level 3
- User zavaros UX

**Fix szükséges**: [Sync mechanizmus](EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md#34-user_licenses-nincs-de-progression-van)

---

## ⚙️ 4. TELJESÍTMÉNY ÉS HIBATŰRÉS

### ❓ Hogyan viselkedik a rendszer, ha a `specialization_progress` tábla több rekordot tartalmaz ugyanahhoz a userhez és specialization-höz?

**Válasz**: 🔴 **NINCS VÉDELEM - Duplikáció lehetséges!**

**Jelenlegi helyzet**:
```sql
-- Ez ÁTMEGY, mert NINCS UniqueConstraint!
INSERT INTO specialization_progress (student_id, specialization_id, current_level)
VALUES (123, 'PLAYER', 3), (123, 'PLAYER', 5);
```

**Service behavior**:
```python
# app/services/specialization_service.py:92-97
progress = db.query(SpecializationProgress).filter(
    and_(
        SpecializationProgress.student_id == student_id,
        SpecializationProgress.specialization_id == specialization_id
    )
).first()  # ← Csak az ELSŐT veszi!
```

**Következmény**: Random melyik rekordot használja

**KRITIKUS FIX SZÜKSÉGES**:
```python
# alembic migration
op.create_unique_constraint(
    'uq_student_specialization',
    'specialization_progress',
    ['student_id', 'specialization_id']
)
```

---

### ❓ Mi történik, ha a `player_levels` tábla üres, de a frontend progression-t kér?

**Válasz**: ❌ **FRONTEND CRASH LEHETSÉGES**

**Backend**:
```python
get_level_requirements('PLAYER', 1)
→ None

get_student_progress(123, 'PLAYER')
→ {
    "current_level": None,
    "next_level": None,
    "total_xp": 0
}
```

**Frontend**:
```javascript
const progress_percent = (current_xp / current_level.required_xp) * 100;
// current_level is None → TypeError: Cannot read property 'required_xp' of null
```

**Fix szükséges**: Backend error handling
```python
if not level_data:
    raise HTTPException(
        status_code=500,
        detail=f"System configuration error: {specialization_id} levels not initialized"
    )
```

---

### ❓ Van-e cache-rendszer, ami ideiglenesen tárolja a `LicenseMetadata` adatait?

**Válasz**: ❌ **NINCS CACHE**

**Jelenlegi működés**:
- Minden request → Fresh DB query
- `get_level_requirements()` → DB query
- `get_license_metadata()` → DB query

**Probléma**:
- Level követelmények **RITKÁN VÁLTOZNAK**
- License metadata **SOHA NEM VÁLTOZIK** élesben
- De **GYAKRAN LEKÉRDEZETT** (minden progress check)

**Performance impact**:
- 1000 user, 100 req/sec → 100,000 DB query/sec (level requirements)

**Javasolt megoldás**: [Cache mechanizmus](EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md#43-cache-rendszer)

```python
from functools import lru_cache
from datetime import datetime, timedelta

# In-memory cache (5 perc)
@lru_cache(maxsize=256)
def get_level_requirements_cached(spec: str, level: int):
    return get_level_requirements(spec, level)

# Vagy Redis
redis.setex(
    f"level_req:{spec}:{level}",
    300,  # 5 perc TTL
    json.dumps(level_data)
)
```

---

## 📈 ÖSSZEFOGLALÓ VÁLASZOK

| Kérdés | Válasz | Kockázat |
|--------|--------|----------|
| Új szint DB-ben, Helper nem ismer | ❌ BLOKKOLVA | 🔴 MAGAS |
| Szint törlés DB-ből | ⚠️ RÉSZBEN VÉDETT | 🟡 KÖZEPES |
| max_level konfliktus | 🔴 HELPER PRIORITÁS | 🔴 MAGAS |
| Üres license_metadata | ✅ MŰKÖDIK (UX ↓) | 🟢 ALACSONY |
| XP elég, órák nem | ✅ HELYESEN BLOKKOLJA | 🟢 ALACSONY |
| Szint átugrás | ✅ BLOKKOLVA | 🟢 ALACSONY |
| Visszalépés | ❌ NINCS FUNKCIÓ | 🟡 KÖZEPES |
| required_sessions=0 | ✅ AUTO LEVEL UP | 🟡 KÖZEPES |
| Hiányzó marketing_narrative | ✅ NULL (Frontend fallback) | 🟢 ALACSONY |
| Hibás JSON | 🔴 CRASH LEHETSÉGES | 🟢 ALACSONY |
| Több license - aktív? | ℹ️ NINCS KONCEPCIÓ | 🟢 ALACSONY |
| Progress ≠ License | 🔴 SZINKRONIZÁLATLAN | 🔴 MAGAS |
| Duplikált progress | 🔴 NINCS VÉDELEM | 🔴 KRITIKUS |
| Üres level tábla | ❌ CRASH | 🟡 KÖZEPES |
| Cache | ❌ NINCS | 🟡 KÖZEPES |

---

## 🛠️ KÖVETKEZŐ LÉPÉSEK

1. **Futtasd a tesztet**:
   ```bash
   python3 scripts/test_edge_cases.py
   ```

2. **Olvasd el a részletes elemzést**:
   [EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md](EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md)

3. **Implementáld a P0 fixeket**:
   - UniqueConstraint hozzáadása
   - Dinamikus max_level
   - Progress ↔ License sync
   - INTERNSHIP 3 vs 5 fix

---

**Készítette**: Claude Code Assistant
**Dátum**: 2025-10-25
**Verzió**: 1.0
