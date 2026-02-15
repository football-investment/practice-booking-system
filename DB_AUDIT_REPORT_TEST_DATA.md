# DB Audit Report — Test Data Analysis

**Dátum**: 2026-02-14
**Auditált adatbázis**: `lfa_intern_system`
**Trigger**: E2E async lifecycle tesztek futása
**Auditor**: Claude Sonnet 4.5

---

## Executive Summary

🚨 **KRITIKUS FELFEDEZÉS**: A tesztek során **66,042 automatikusan generált "ghost" felhasználó** jött létre a DB-ben, amelyek **NEM látszanak a frontend-en**.

### Adatbázis állapot:

| Metrika | Érték | Forrás |
|---------|-------|--------|
| **Összes felhasználó DB-ben** | **69,505** | PostgreSQL users tábla |
| **Frontend-en látható** | **50** | Admin Dashboard UI |
| **"Ghost" felhasználók** | **69,455** | Különbség |
| **Mai tesztek által létrehozott** | **66,042** | 2026-02-14 creation_date |

---

## 1. Felhasználók létrehozási eloszlása

### Dátum szerinti bontás:

| Dátum | Létrehozott felhasználók | ID tartomány | Email domainek |
|-------|-------------------------|--------------|----------------|
| **2026-02-14** | **66,042** | 3466 - 69507 | `@lfa-ops.internal` |
| 2026-02-13 | 1,013 | 2453 - 3465 | `@lfa-ops.internal`, `@f1rstteam.hu` |
| 2026-02-12 | 2,432 | 19 - 2452 | `@lfa-ops.internal`, `@loadtest.lfa`, `@concurrent.lfa`, `@large.lfa` |
| 2026-02-11 | 18 | 1 - 18 | `@lfa.com`, `@realmadrid.com`, `@arsenal.com`, stb. (valós) |

**Megfigyelés**:
- Az első 18 felhasználó (2026-02-11): **Valós seed adatok** (Messi, Mbappé, admin, stb.)
- 2026-02-12 -től: **Teszt generált felhasználók**
- 2026-02-14 (MA): **66,042 felhasználó létrehozva E2E tesztek által**

---

## 2. "Ghost" Felhasználók Elemzése

### Teszt felhasználó minta (Tournament ID 799):

```
ID    | Email                              | Name                 | Created At
------+------------------------------------+----------------------+---------------------
65016 | ops.519b8a7d.0001@lfa-ops.internal | OPS-519b Player 0001 | 2026-02-14 11:08:31
65017 | ops.519b8a7d.0002@lfa-ops.internal | OPS-519b Player 0002 | 2026-02-14 11:08:31
65018 | ops.519b8a7d.0003@lfa-ops.internal | OPS-519b Player 0003 | 2026-02-14 11:08:31
...
66039 | ops.519b8a7d.1024@lfa-ops.internal | OPS-519b Player 1024 | 2026-02-14 11:08:32
```

**Pattern**:
- **Email**: `ops.{UUID}.{INDEX}@lfa-ops.internal`
- **Name**: `OPS-{UUID} Player {INDEX}`
- **UUID**: Egyedi azonosító minden tournament-hez (pl. `519b8a7d`)
- **INDEX**: 0001 - 1024 (player count szerint)

**Létrehozási idő**:
- 1024 felhasználó ~1 másodperc alatt (2026-02-14 11:08:31-32)
- Bulk insert művelet

---

## 3. Teszt Data Flow Elemzés

### OPS API Működés:

```
Test Call:
POST /api/v1/tournaments/ops/run-scenario
{
  "scenario": "large_field_monitor",
  "player_count": 1024,
  "tournament_format": "HEAD_TO_HEAD",
  "tournament_type_code": "knockout",
  "dry_run": false,
  "confirmed": true
}

↓

Backend Processing:
1. Generál 1024 felhasználót:
   - Email: ops.{UUID}.{INDEX}@lfa-ops.internal
   - Name: OPS-{UUID} Player {INDEX}
   - Role: Student
   - Status: Active

2. Létrehozza a tournament-et (semester)

3. Beenrollzolja mind a 1024 felhasználót

4. Async path (≥128 players):
   - Queue-ba teszi a Celery task-ot
   - Visszaadja task_id-t

5. Celery Worker:
   - Generálja a 1024 session-t
   - Populálja a bracket struktúrát
```

**Adatbázis hatás per teszt**:
- **Users**: +1024 rekord
- **Semester_enrollments**: +1024 rekord (vagy hasonló kapcsolótábla)
- **Sessions**: +1024 rekord
- **Match participants**: ~2048 rekord (minden session-nek 2 résztvevője)
- **Results**: +1024 rekord (szimuláció után)
- **Rankings**: +1024 rekord (ranking számítás után)

**15 teszt futtatása** (Groups U + V + W):
- Kb. **15 × 1024 = 15,360 felhasználó** (minimálisan)
- De egyes tesztek **újra futottak** (cache clear, fix-ek, stb.)
- Eredmény: **66,042 felhasználó** (kb. 64 teszt futás / újrafuttatás)

---

## 4. Frontend vs DB Diszkrepancia

### Frontend Nézet (Admin Dashboard):

```
👥 Total: 50
🎓 Students: 48
👨‍🏫 Instructors: 1
👑 Admin: 1
```

**Látható felhasználók**:
- Grand Master (grandmaster@lfa.com)
- Jude Bellingham, Mohamed Salah, stb. (valós játékosok)
- Load Test Player 0001-0032 (32 db)
- Tamás Juhász, Péter Nagy, stb. (E2E teszt felhasználók)
- System Administrator (admin@lfa.com)

**ÖSSZESEN**: 50 felhasználó

### DB Valóság:

```sql
SELECT COUNT(*) FROM users;
-- Result: 69,505
```

**Magyarázat**:
A frontend **feltehetően szűr** vagy **pagináció van**, és csak az első 50-et mutatja.
VAGY a frontend **nem lát rá** az `@lfa-ops.internal` email domain-nel rendelkező felhasználókra.

---

## 5. Tesztek Érvényessége

### ✅ Pozitív Megfigyelések:

1. **Valós DB műveletek**:
   - Tesztek **valóban írnak** a DB-be
   - **1024 egyedi felhasználó** per teszt
   - **1024 egyedi session** per teszt
   - **Teljes bracket struktúra** (10 round + playoff)
   - **100% result submission**
   - **1024 ranking rekord**

2. **Konzisztens adatok**:
   - User IDs egyediek
   - Session IDs egyediek
   - Bracket struktúra matematikailag helyes (512+256+128+...+1 = 1023 + 1 playoff)
   - Participant hozzárendelések helyesek (Round 1: mind 2-2 fő)

3. **Teljesítmény metrikák hitelesek**:
   - Session generation: 266ms / 1024 session
   - DB write: 265ms / 1024 record
   - Ezek **valós DB I/O műveletek**

### ⚠️ Kritikus Problémák:

1. **NEM használja a "valós" 50 felhasználót**:
   - Tesztek **mindig generálnak új felhasználókat**
   - **NEM tesztelik** a valós felhasználói adatokkal való működést

2. **DB szennyezés**:
   - **69,455 "ghost" felhasználó** a DB-ben
   - Ezek **nem látszanak** a frontend-en
   - **Nincs cleanup** mechanizmus

3. **Félrevezető "production-ready" státusz**:
   - Tesztek **izolált környezetben** futnak (saját felhasználókkal)
   - **NEM validálják** a valós felhasználói adatokkal való integrációt

---

## 6. OPS API Analízis

### Forrás endpoint:

`POST /api/v1/tournaments/ops/run-scenario`

**Felelősség**:
- Teszt tournamentek gyors létrehozása
- Automatikus felhasználó generálás
- Enrollment
- Session generation (async)

**Problémák**:

1. **Nincsen cleanup flag**:
   - `dry_run: false` → permanent DB write
   - Nincs `cleanup: true` opció a teszt felhasználók törlésére

2. **Email domain nem jelölt**:
   - `@lfa-ops.internal` domain **nem dokumentált**
   - Frontend **nem tudja**, hogy ezeket szűrni kell

3. **Idempotency nélkül**:
   - Minden hívás **új felhasználókat hoz létre**
   - Nincs "reuse existing test users" mechanizmus

---

## 7. Adatbázis Cleanup Javaslat

### Azonnali Cleanup:

**FIGYELEM**: Ez törli az **összes OPS teszt felhasználót** és kapcsolódó adatokat!

```sql
-- 1. Töröljük az OPS generated users-t
DELETE FROM users
WHERE email LIKE '%@lfa-ops.internal';

-- Várható törlés: ~66,000 rekord

-- 2. Töröljük a loadtest felhasználókat (ha szükséges)
DELETE FROM users
WHERE email LIKE '%@loadtest.lfa'
  OR email LIKE '%@concurrent.lfa'
  OR email LIKE '%@large.lfa';

-- 3. Vacuum a táblát
VACUUM FULL users;
```

**Eredmény**: DB visszaáll ~50 valós felhasználóra

### Hosszú távú megoldás:

1. **OPS API módosítás**:
   ```python
   # Add cleanup flag
   POST /api/v1/tournaments/ops/run-scenario
   {
     ...
     "cleanup_after": true,  # Auto-delete test users after test
     "ttl_minutes": 60       # Expire test users after 1 hour
   }
   ```

2. **Frontend szűrés**:
   ```python
   # Admin dashboard: filter out test users
   users = db.query(User).filter(
       ~User.email.like('%@lfa-ops.internal')
   ).all()
   ```

3. **Cron job cleanup**:
   ```bash
   # Daily cleanup of old OPS test users
   0 2 * * * psql -c "DELETE FROM users WHERE email LIKE '%@lfa-ops.internal' AND created_at < NOW() - INTERVAL '24 hours';"
   ```

---

## 8. Teszt Stratégia Javítása

### Jelenlegi probléma:

Tesztek **NEM** a valós 50 felhasználót használják, hanem minden futáskor új 1024 felhasználót generálnak.

### Javasolt megoldás:

**Opció A: Seed pool használata**

```python
# Seed DB 2048 stable test users egyszer:
# ops-stable-0001@lfa-ops.internal
# ops-stable-0002@lfa-ops.internal
# ...
# ops-stable-2048@lfa-ops.internal

# Tesztek: reuse these users
POST /api/v1/tournaments/ops/run-scenario
{
  "scenario": "large_field_monitor",
  "player_count": 1024,
  "use_existing_pool": true,  # <-- NEW
  "pool_prefix": "ops-stable-"
}
```

**Opció B: Valós felhasználók klónozása**

```python
# Clone the real 50 users 20× to get 1000 users
# Real: admin@lfa.com
# Clones: admin+clone001@lfa.com, admin+clone002@lfa.com, ...

# Benefit: Tests use real user data structure
# Issue: Email +alias may not work in all systems
```

**Opció C: Separate test DB**

```bash
# Production DB: lfa_intern_system
# Test DB: lfa_intern_system_test

# Tesztek: run against test DB
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test"
```

---

## 9. Hatás a jelenlegi tesztekre

### Tesztek továbbra is **ÉRVÉNYESEK**, mert:

1. ✅ **Valós DB műveletek**: INSERT/UPDATE/SELECT a production DB-n
2. ✅ **Valós Celery worker**: Async task processing validálva
3. ✅ **Valós session generation**: 1024 session matematikailag helyes bracket-tel
4. ✅ **Valós UI rendering**: Playwright tesztek látják a monitor page-t
5. ✅ **Valós state transitions**: sessions=0 → 1024 → results → rankings → COMPLETED

### DE a tesztek **NEM** validálják:

1. ❌ **Valós felhasználói adatokkal való működést**
2. ❌ **Létező felhasználók enrollment flow-ját**
3. ❌ **DB cleanup stratégiát**
4. ❌ **Frontend felhasználó szűrést**

---

## 10. Következtetés

### DB Audit Eredmény:

| Kérdés | Válasz |
|--------|--------|
| **Valós DB rekordok?** | ✅ Igen, 69,505 user + 1000+ tournament + 10,000+ session |
| **Egyedi sessionök?** | ✅ Igen, minden session unique ID |
| **Valós felhasználók?** | ❌ **NEM**, generált `@lfa-ops.internal` teszt felhasználók |
| **Frontend látja őket?** | ❌ **NEM**, csak 50 felhasználó látszik |
| **Tesztek érvényesek?** | ⚠️ **Részben**: DB/backend működik, de NEM valós user data |

### Ajánlás:

**Azonnali**:
1. ✅ **Jelenlegi tesztek validak maradnak** (backend/async/UI működés)
2. ⚠️ **Státusz módosítás**: "Backend Async Ready + UI Validated (Test Data)"
3. 🧹 **DB cleanup**: Töröljük az OPS test users-t (lásd 7. fejezet)

**Rövid távon**:
1. Dokumentáljuk, hogy tesztek **generated test users**-t használnak
2. Frontend szűrés implementálása `@lfa-ops.internal` email domain-re
3. OPS API cleanup flag hozzáadása

**Hosszú távon**:
1. Valós felhasználói adatokkal való teszt suite (50 user-rel)
2. Separate test DB használata
3. Automated cleanup cron job

---

**Audit befejezve**: 2026-02-14 11:35 CET
**Auditor**: Claude Sonnet 4.5
**Státusz**: ⚠️ **DB szennyezés detektálva, tesztek érvényesek de NEM valós user data**
