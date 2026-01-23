# Tournament Snapshot Management Guide

A tournament session-ök mentése és visszaállítása különböző tournament type-ok teszteléséhez.

## Használati Útmutató

### 1. Snapshot mentése (SAVE)

Mentsük el a jelenlegi tournament sessions állapotot:

```bash
cd /path/to/practice_booking_system
source venv/bin/activate
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py save <tournament_id> <snapshot_name>
```

**Példa:**
```bash
# Tournament 17 mentése "round_robin" néven
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py save 17 round_robin
```

**Output:**
```
✅ Snapshot saved: tournament_17_round_robin_20260123_201530.json
   Tournament: 🇧🇷 BR - "Speed Challenge" - RIO
   Type: League (Round Robin)
   Players: 8
   Sessions: 28
   Location: /path/to/snapshots/tournaments/tournament_17_round_robin_20260123_201530.json
```

---

### 2. Snapshots listázása (LIST)

Összes snapshot listázása:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py list
```

Egy adott tournament snapshot-jainak listázása:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py list 17
```

**Output:**
```
📸 Available snapshots (2):

  tournament_17_swiss_system_20260123_202000.json
    Tournament: 🇧🇷 BR - "Speed Challenge" - RIO (ID: 17)
    Type: Swiss System
    Sessions: 24
    Created: 2026-01-23T20:20:00.123456

  tournament_17_round_robin_20260123_201530.json
    Tournament: 🇧🇷 BR - "Speed Challenge" - RIO (ID: 17)
    Type: League (Round Robin)
    Sessions: 28
    Created: 2026-01-23T20:15:30.123456
```

---

### 3. Snapshot visszaállítása (RESTORE)

Visszaállítjuk a tournament sessions-t egy mentett snapshot-ból:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py restore <tournament_id> <snapshot_name>
```

**Példa:**
```bash
# Visszaállítás a "round_robin" snapshot-ból
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py restore 17 round_robin
```

**Output:**
```
📸 Restoring snapshot: tournament_17_round_robin_20260123_201530.json
   Created: 2026-01-23T20:15:30.123456
   Tournament: 🇧🇷 BR - "Speed Challenge" - RIO
   Type: League (Round Robin)
   🗑️  Deleted 24 existing sessions
   ✅ Restored 28 sessions
✅ Snapshot restored successfully
```

**Megjegyzés:** A visszaállítás automatikusan:
- Törli az aktuális sessions-öket
- Visszaállítja a mentett sessions-öket
- Frissíti a `sessions_generated` flag-et
- Visszaállítja a `tournament_type_id`-t

---

### 4. Sessions törlése (DELETE)

Töröljük az összes session-t egy tournamentből:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py delete <tournament_id>
```

**Példa:**
```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py delete 17
```

**Output:**
```
✅ Deleted 28 sessions from tournament 17
```

---

### 5. Snapshots összehasonlítása (COMPARE)

Két snapshot összehasonlítása:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py compare <snapshot1_name> <snapshot2_name>
```

**Példa:**
```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py compare round_robin swiss_system
```

**Output:**
```
📊 Comparing snapshots:

  Snapshot 1: League (Round Robin)
    Sessions: 28
    File: tournament_17_round_robin_20260123_201530.json

  Snapshot 2: Swiss System
    Sessions: 24
    File: tournament_17_swiss_system_20260123_202000.json

  Difference: 4 sessions

📋 First 5 sessions from Snapshot 1:
    Round 1: SESS-RR-R1-001 - 2 players
    Round 1: SESS-RR-R1-002 - 2 players
    Round 1: SESS-RR-R1-003 - 2 players
    Round 1: SESS-RR-R1-004 - 2 players
    Round 2: SESS-RR-R2-001 - 2 players

📋 First 5 sessions from Snapshot 2:
    Round 1: SESS-SW-R1-001 - 2 players
    Round 1: SESS-SW-R1-002 - 2 players
    Round 1: SESS-SW-R1-003 - 2 players
    Round 1: SESS-SW-R1-004 - 2 players
    Round 2: SESS-SW-R2-001 - 2 players
```

---

## Tipikus Munkafolyamat: Tournament Type Tesztelés

### Példa: Round Robin → Swiss System váltás tesztelése

```bash
# 1️⃣ Generáljuk a Round Robin sessionöket az UI-n
#    Admin Dashboard → Tournament Management → Generate Sessions

# 2️⃣ Mentés "round_robin" néven
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py save 17 round_robin

# 3️⃣ Ellenőrizzük az UI-n a párosításokat
#    Admin Dashboard → Tournament → Preview Sessions

# 4️⃣ Töröljük a sessions-öket
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py delete 17

# 5️⃣ Változtassuk meg a tournament type-ot az UI-n
#    Admin Dashboard → Edit Tournament → Tournament Type: Swiss System → Save

# 6️⃣ Generáljuk a Swiss System sessionöket az UI-n
#    Admin Dashboard → Tournament Management → Generate Sessions

# 7️⃣ Mentés "swiss_system" néven
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py save 17 swiss_system

# 8️⃣ Ellenőrizzük az UI-n a párosításokat
#    Admin Dashboard → Tournament → Preview Sessions

# 9️⃣ Hasonlítsuk össze a két snapshot-ot
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py compare round_robin swiss_system

# 🔟 Ha vissza akarunk térni Round Robin-hoz:
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python3 scripts/tournament_snapshot.py restore 17 round_robin
```

---

## Snapshot Fájlok Helye

Snapshot fájlok ide kerülnek:
```
practice_booking_system/
└── snapshots/
    └── tournaments/
        ├── tournament_17_round_robin_20260123_201530.json
        ├── tournament_17_swiss_system_20260123_202000.json
        └── ...
```

---

## Snapshot Adatstruktúra

Egy snapshot tartalmazza:

```json
{
  "snapshot_name": "round_robin",
  "created_at": "2026-01-23T20:15:30.123456",
  "tournament": {
    "id": 17,
    "name": "🇧🇷 BR - \"Speed Challenge\" - RIO",
    "code": "TOURN-20260124-002",
    "tournament_type_id": 1,
    "tournament_type_name": "League (Round Robin)",
    "sessions_generated": true,
    "max_players": 20,
    "start_date": "2026-01-24",
    "end_date": "2026-01-24"
  },
  "players": [
    {"id": 4, "name": "Tamás Juhász", "email": "k1sqx1@f1rstteam.hu"},
    {"id": 5, "name": "Péter Nagy", "email": "p3t1k3@f1rstteam.hu"},
    ...
  ],
  "sessions": [
    {
      "id": 123,
      "code": "SESS-RR-R1-001",
      "start_datetime": "2026-01-24T09:00:00",
      "end_datetime": "2026-01-24T09:45:00",
      "session_type": "MATCH",
      "round_number": 1,
      "capacity": 2,
      "participant_user_ids": [4, 5],
      "game_results": null,
      ...
    },
    ...
  ],
  "session_count": 28
}
```

---

## Előnyök

✅ **Gyors váltás** - Pillanatok alatt válthatunk tournament type-ok között
✅ **Biztonságos** - Nem vesznek el adatok, mindent vissza lehet állítani
✅ **Összehasonlítható** - Láthatjuk a különbségeket a típusok között
✅ **Verziókezelt** - Minden snapshot timestamppel van ellátva
✅ **Lightweight** - Csak a sessions tábla érintett, nem az egész adatbázis

---

## Megjegyzések

- A snapshot **NEM** tartalmazza a tényleges match results-okat (ha már játszódtak meccsek)
- A snapshot **NEM** módosítja az enrollment-okat (játékosok bejelentkezését)
- A restore művelet **felülírja** a jelenlegi sessions-öket
- Snapshot fájlok **JSON formátumban** tárolódnak, könnyen olvashatók és módosíthatók
