# 🔍 Rendszer Határesetek és Szinkronizációs Analízis

## 📊 Executive Summary

Ez a dokumentum részletesen elemzi a curriculum/license rendszer **határeseteit**, **szinkronizációs problémáit** és **adatintegritási kockázatait**.

---

## 🎯 1. ADATFORRÁS ÉS SZINKRONIZÁCIÓS SZENÁRIÓK

### 1.1 Új szint az adatbázisban, amit a Helper nem ismer

**Szenárió**: Valaki beszúr egy új `PlayerLevel(id=9)` rekordot az adatbázisba.

**Jelenlegi viselkedés**:
```python
# app/models/license.py:198-205
max_levels = {
    "COACH": 8,
    "PLAYER": 8,
    "INTERNSHIP": 5
}
```

**❌ PROBLÉMA**:
- A `LicenseSystemHelper.get_specialization_max_level("PLAYER")` továbbra is `8`-at ad vissza
- A `validate_advancement()` elutasítja a 9. szintre lépést
- A `get_level_requirements(PLAYER, 9)` **MŰKÖDIK** (DB query), de validáció **BLOKKOLJA**

**🔧 FIX SZÜKSÉGES**:
```python
# Helyette: dinamikus lekérdezés
@staticmethod
def get_specialization_max_level(specialization: str, db: Session) -> int:
    """Get max level from database"""
    if specialization == "PLAYER":
        return db.query(func.max(PlayerLevel.id)).scalar() or 8
    elif specialization == "COACH":
        return db.query(func.max(CoachLevel.id)).scalar() or 8
    elif specialization == "INTERNSHIP":
        return db.query(func.max(InternshipLevel.id)).scalar() or 5
    return 1
```

**Kockázati szint**: 🔴 **MAGAS** - Blokkolja az új szintek használatát

---

### 1.2 Szint törlése az adatbázisból

**Szenárió**: `DELETE FROM player_levels WHERE id = 5`

**Jelenlegi viselkedés**:
```python
# app/services/specialization_service.py:33
level_data = self.db.query(PlayerLevel).filter(PlayerLevel.id == level).first()
if not level_data:
    return None  # ✅ Helyes kezelés
```

**✅ JÓ**: A `get_level_requirements()` `None`-t ad vissza
**✅ JÓ**: A `can_level_up()` `False`-t ad vissza (line 180-181)

**⚠️  PROBLÉMA**: Mi van a meglévő progress-szel?
```python
# Ha user current_level = 5, de level törölve
progress = SpecializationProgress(
    student_id=123,
    specialization_id='PLAYER',
    current_level=5  # Orphan szint!
)
```

**🔧 FIX SZÜKSÉGES**: Migration constraint
```sql
ALTER TABLE specialization_progress
ADD CONSTRAINT fk_player_level
FOREIGN KEY (current_level) REFERENCES player_levels(id)
ON DELETE RESTRICT;  -- NE engedje törölni használt szintet
```

**Kockázati szint**: 🟡 **KÖZEPES** - Ritkán fordul elő, de adatvesztést okozhat

---

### 1.3 Ellentmondás a max_level értékekben

**Szenárió**:
- Migration: `INSERT INTO internship_levels (id=1,2,3)` → 3 szint
- Helper: `"INTERNSHIP": 5` → 5 szint
- License enum: 5 szint definíció

**Jelenlegi validáció**:
```python
# app/services/license_service.py:123
max_level = LicenseSystemHelper.get_specialization_max_level(specialization)
# Mindig a HELPER értékét használja! (hardcoded 5)
```

**❌ PROBLÉMA**:
- User level 4-re léphet, de `get_level_requirements(INTERNSHIP, 4)` → `None`
- Frontend crash vagy üres adatok

**🔧 FIX SZÜKSÉGES**:
```python
# Prioritás: MINDIG az adatbázis
max_level = db.query(func.max(InternshipLevel.id)).scalar() or
            LicenseSystemHelper.get_specialization_max_level(specialization)
```

**Kockázati szint**: 🔴 **MAGAS** - Jelenleg aktív ellentmondás van (3 vs 5)

---

### 1.4 Üres license_metadata tábla

**Szenárió**: Migration nem futott, vagy adatok törölve

**Jelenlegi viselkedés**:
```python
# app/services/license_service.py:25-35
licenses = self.db.query(LicenseMetadata).filter(
    LicenseMetadata.specialization_type == specialization.upper()
).order_by(LicenseMetadata.level_number).all()

return [license.to_dict() for license in licenses]
# Üres lista, ha nincs adat → []
```

**✅ JÓ**: Nem crashel
**❌ PROBLÉMA**: Frontend marketing tartalom nélkül (üres badge-ek, nincs narrative)

**🔧 FIX SZÜKSÉGES**: Fallback mechanizmus
```python
if not licenses:
    # Generálj alapértelmezett metadata-t a player_levels-ből
    return self.generate_fallback_metadata(specialization)
```

**Kockázati szint**: 🟢 **ALACSONY** - UX probléma, de működik

---

## 🧭 2. HALADÁS ÉS VALIDÁCIÓS SZENÁRIÓK

### 2.1 XP elért, de óraszám hiányzik (COACH)

**Szenárió**:
```python
progress = SpecializationProgress(
    specialization_id='COACH',
    current_level=1,
    total_xp=15000,  # ✅ Elég (15000 >= 15000)
    completed_sessions=15,  # ✅ Elég
    theory_hours_completed=0,  # ❌ Kellene 30
    practice_hours_completed=0  # ❌ Kellene 50
)
```

**Jelenlegi validáció**:
```python
# app/services/specialization_service.py:190-194
if progress.specialization_id == 'COACH':
    can_level = can_level and (
        progress.theory_hours_completed >= next_level_req.get('theory_hours', 0) and
        progress.practice_hours_completed >= next_level_req.get('practice_hours', 0)
    )
```

**✅ JÓ**: Blokkolja a level up-ot
**✅ JÓ**: Frontend látja a hiányzó órákat (line 158-161)

**Kockázati szint**: 🟢 **ALACSONY** - Helyesen működik

---

### 2.2 Szint átugrás (level_id + 2)

**Szenárió**: User current_level=3, megpróbál level=5-re ugrani

**Jelenlegi validáció**:
```python
# app/models/license.py:242-252
def validate_advancement(current_level: int, target_level: int, max_level: int):
    if target_level > current_level + 1:
        return False, "Can only advance one level at a time"
```

**✅ JÓ**: Blokkolja az átugrást
**✅ JÓ**: Megfelelő hibaüzenet

**⚠️  EDGE CASE**: Mi van automatikus level up-nál?
```python
# app/services/specialization_service.py:246-249
while self.can_level_up(progress):
    progress.current_level += 1
    leveled_up = True
    levels_gained += 1
```

**✅ JÓ**: Loop végigmegy minden szinten egyesével

**Kockázati szint**: 🟢 **ALACSONY** - Helyesen védett

---

### 2.3 Visszalépés korábbi szintre

**Szenárió**: User current_level=5, próbál level=3-ra "visszalépni"

**Jelenlegi validáció**:
```python
# app/models/license.py:244-245
if target_level <= current_level:
    return False, "Target level must be higher than current level"
```

**✅ JÓ**: Blokkolja a visszalépést

**❌ FUNKCIÓ HIÁNY**: Nincs "downgrade" vagy "reset" mechanizmus adminoknak
- Mi van, ha tévedésből rossz szintet adtak?
- Mi van büntetés/visszasorolás esetén?

**🔧 JAVASOLT**: Admin-only downgrade funkció
```python
def admin_downgrade_level(
    user_id: int,
    specialization: str,
    target_level: int,
    admin_id: int,
    reason: str
):
    # Csak ADMIN role esetén
    # Log-olja az eseményt
    # Frissíti a progress-t
```

**Kockázati szint**: 🟡 **KÖZEPES** - Funkció hiány, nem bug

---

### 2.4 required_sessions = 0

**Szenárió**: `UPDATE player_levels SET required_sessions = 0 WHERE id = 1`

**Jelenlegi validáció**:
```python
# app/services/specialization_service.py:184-186
can_level = (
    progress.total_xp >= next_level_req['required_xp'] and
    progress.completed_sessions >= next_level_req['required_sessions']  # 0 >= 0 → True
)
```

**✅ JÓ**: Matematikailag helyes (0 >= 0 = True)
**⚠️  EDGE CASE**: Szándékos vagy hiba?

**🔧 JAVASOLT**: Validáció a migration-ben
```sql
ALTER TABLE player_levels
ADD CONSTRAINT check_required_sessions_positive
CHECK (required_sessions > 0);
```

**Kockázati szint**: 🟡 **KÖZEPES** - Adatintegritási kérdés

---

## 🧩 3. LICENSE-KEZELÉSI SZENÁRIÓK

### 3.1 Hiányzó marketing_narrative

**Szenárió**: `license_metadata.marketing_narrative IS NULL`

**Jelenlegi viselkedés**:
```python
# app/models/license.py:92-114 (to_dict)
"marketing_narrative": self.marketing_narrative,  # None → JSON null
```

**✅ JÓ**: Nem crashel
**❌ UX PROBLÉMA**: Frontend üres szöveg helyett talán default kellene

**🔧 JAVASOLT**: Frontend fallback
```javascript
const narrative = license.marketing_narrative ||
                  `Complete Level ${license.level_number} to unlock this achievement.`;
```

**Kockázati szint**: 🟢 **ALACSONY** - Frontend probléma

---

### 3.2 Hibás JSON a advancement_criteria mezőben

**Szenárió**:
```sql
UPDATE license_metadata
SET advancement_criteria = '{invalid json'
WHERE id = 1;
```

**Jelenlegi viselkedés**:
- PostgreSQL JSONB típus → **NEM ENGEDI** a rossz JSON-t
- SQLAlchemy query → **HIBA**: `DataError: invalid input syntax for type json`

**✅ JÓ**: PostgreSQL védi az integritást
**❌ PROBLÉMA**: Nincs try-except a query körül

**🔧 FIX SZÜKSÉGES**:
```python
try:
    licenses = self.db.query(LicenseMetadata).filter(...).all()
except DataError as e:
    logger.error(f"Invalid JSON in license_metadata: {e}")
    return []  # Vagy fallback adatok
```

**Kockázati szint**: 🟢 **ALACSONY** - PostgreSQL védi, de crash lehetséges

---

### 3.3 Több specializáció - aktív kiválasztása

**Szenárió**: User-nek van PLAYER és COACH license is

**Jelenlegi viselkedés**:
```python
# app/services/license_service.py:75-105
def get_user_license(self, user_id: int, specialization: str):
    license = self.db.query(UserLicense).filter(
        UserLicense.user_id == user_id,
        UserLicense.specialization_type == specialization.upper()
    ).first()
```

**✅ JÓ**: Specializációnként külön license (helyes design)
**✅ JÓ**: Nincs "aktív" koncepció (párhuzamos track-ek)

**❌ FRONTEND KÉRDÉS**: Melyiket jelenítse meg először?
- Jelenleg: mindkettőt
- Kéne: user preferencia vagy "primary specialization"

**Kockázati szint**: 🟢 **ALACSONY** - Design döntés, nem bug

---

### 3.4 user_licenses nincs, de progression van

**Szenárió**:
```sql
-- Létezik
SELECT * FROM specialization_progress WHERE student_id = 123;

-- NEM létezik
SELECT * FROM user_licenses WHERE user_id = 123;
```

**Jelenlegi viselkedés**:
- `license_service.py` → `get_or_create_user_license()` automatikusan létrehozza
- `specialization_service.py` → Külön tábla, nem függ össze közvetlenül

**⚠️  PROBLÉMA**: KÉT KÜLÖN RENDSZER!
1. **SpecializationProgress** (player_levels, coach_levels alapú)
2. **UserLicense** (license_metadata alapú)

**❌ INKONZISZTENCIA LEHETSÉGES**:
```python
# Progress szerint
progress.current_level = 5

# License szerint
license.current_level = 3
```

**🔧 FIX SZÜKSÉGES**: Szinkronizáció vagy egységesítés
```python
def sync_license_with_progress(user_id: int, specialization: str):
    progress = get_specialization_progress(user_id, specialization)
    license = get_user_license(user_id, specialization)

    if progress.current_level != license.current_level:
        # Melyik a source of truth?
        # Döntés: progress az elsődleges
        license.current_level = progress.current_level
        db.commit()
```

**Kockázati szint**: 🔴 **MAGAS** - Két párhuzamos rendszer szinkronizálatlan

---

## ⚙️ 4. TELJESÍTMÉNY ÉS HIBATŰRÉS

### 4.1 Duplikált specialization_progress rekord

**Szenárió**:
```sql
INSERT INTO specialization_progress (student_id, specialization_id, current_level)
VALUES (123, 'PLAYER', 3), (123, 'PLAYER', 5);  -- DUPLIKÁCIÓ!
```

**Jelenlegi védelem**:
```python
# app/models/user_progress.py:84
# UniqueConstraint NINCS explicit definiálva!
```

**❌ KRITIKUS PROBLÉMA**: Nincs DB constraint a duplikáció ellen!

**🔧 MIGRATION SZÜKSÉGES**:
```python
# alembic migration
op.create_unique_constraint(
    'uq_student_specialization',
    'specialization_progress',
    ['student_id', 'specialization_id']
)
```

**Kockázati szint**: 🔴 **KRITIKUS** - Adatintegritási probléma

---

### 4.2 Üres player_levels tábla, frontend progression kérés

**Szenárió**: `TRUNCATE player_levels;`

**Jelenlegi viselkedés**:
```python
# app/services/specialization_service.py:33-35
level_data = self.db.query(PlayerLevel).filter(PlayerLevel.id == level).first()
if not level_data:
    return None
```

**Frontend kap**: `current_level: None, next_level: None`

**❌ PROBLÉMA**: Frontend crash lehetséges
```javascript
const xp_percentage = (current_xp / current_level.required_xp) * 100;
// current_level is None → TypeError
```

**🔧 FIX SZÜKSÉGES**: Backend error response
```python
if not level_data:
    raise HTTPException(
        status_code=500,
        detail=f"Level configuration missing for {specialization_id} level {level}"
    )
```

**Kockázati szint**: 🟡 **KÖZEPES** - Ritka, de kritikus hatású

---

### 4.3 Cache rendszer

**Jelenlegi állapot**: ❌ **NINCS CACHE**

**Probléma**:
- Minden `get_level_requirements()` hívás → DB query
- Minden `get_license_metadata()` → DB query
- License metadata ritkán változik, de gyakran lekérdezett

**🔧 JAVASOLT**: Redis vagy in-memory cache
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_level_requirements_cached(specialization_id: str, level: int):
    # Cache 5 percig
    return get_level_requirements(specialization_id, level)
```

**Vagy**: Database cache table
```sql
CREATE TABLE level_requirements_cache (
    specialization TEXT,
    level INT,
    data JSONB,
    updated_at TIMESTAMP,
    PRIMARY KEY (specialization, level)
);
```

**Kockázati szint**: 🟡 **KÖZEPES** - Teljesítmény probléma nagy user számnál

---

## 📈 ÖSSZEFOGLALÓ KOCKÁZATI MÁTRIX

| Probléma | Szint | Impact | Likelihood | Priority |
|----------|-------|--------|------------|----------|
| Hardcoded max_levels | 🔴 MAGAS | MAGAS | KÖZEPES | **P0** |
| Duplikált progress rekord | 🔴 KRITIKUS | MAGAS | ALACSONY | **P0** |
| Progress/License szinkronizáció | 🔴 MAGAS | MAGAS | MAGAS | **P0** |
| INTERNSHIP 3 vs 5 szint | 🔴 MAGAS | MAGAS | MAGAS | **P0** |
| Szint törlés védelme | 🟡 KÖZEPES | KÖZEPES | ALACSONY | **P1** |
| Admin downgrade funkció hiány | 🟡 KÖZEPES | ALACSONY | ALACSONY | **P2** |
| Cache hiány | 🟡 KÖZEPES | KÖZEPES | MAGAS | **P1** |
| Üres license_metadata | 🟢 ALACSONY | ALACSONY | ALACSONY | **P3** |
| Hibás JSON kezelés | 🟢 ALACSONY | ALACSONY | MUY ALACSONY | **P3** |

---

## 🛠️ JAVASOLT JAVÍTÁSOK PRIORITÁS SZERINT

### P0 - KRITIKUS (azonnal)

1. **UniqueConstraint hozzáadása** specialization_progress táblához
2. **Dinamikus max_level** lekérdezés (DB-ből)
3. **Progress ↔ License szinkronizáció** megoldása
4. **INTERNSHIP szint konfliktus** feloldása (3 vagy 5?)

### P1 - MAGAS (1-2 héten belül)

5. **ON DELETE RESTRICT** constraint level táblákhoz
6. **Cache mechanizmus** implementálása
7. **Error handling** javítása (try-except, HTTP errors)

### P2 - KÖZEPES (1 hónap)

8. **Admin downgrade** funkció
9. **Fallback metadata** generator
10. **Frontend error handling** javítása

### P3 - ALACSONY (backlog)

11. User preferencia: "primary specialization"
12. Audit log level változásokhoz
13. Automated migration testing

---

**Készítette**: Claude Code Assistant
**Dátum**: 2025-10-25
**Verzió**: 1.0
**Status**: 🔍 Analysis Complete - Fixes Needed
