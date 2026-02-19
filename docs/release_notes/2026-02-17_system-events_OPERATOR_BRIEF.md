# Operator Brief — System Events (Rendszerüzenetek) Deploy

**Date:** 2026-02-17
**Branch:** `feature/performance-card-option-a`
**Audience:** Operators, DBAs, Admin users
**Severity:** Additive (no breaking changes to existing API)

---

## TL;DR — Mit csináltok deploy után?

```bash
# 1. Migráció alkalmazása
alembic upgrade head

# 2. Ellenőrzés
alembic current    # → se002residx00 (head)

# 3. Ha valami hibát dob → rollback
alembic downgrade e7f8a9b0c1d2
```

Admin Dashboard → **🔔 Üzenetek** tab → legyen látható.

---

## Mi változott?

| Elem | Részlet |
|------|---------|
| Új DB tábla | `system_events` (8 oszlop, 10 index) |
| Új PG típus | `systemeventlevel ENUM ('INFO','WARNING','SECURITY')` |
| Új API végpontok | `GET/PATCH/POST /api/v1/system-events/…` |
| Új Admin tab | 🔔 Üzenetek (8. tab az Admin Dashboardon) |
| Napi cron | APScheduler 02:00 UTC — 90 napnál régebbi, lezárt események törlése |

**Nincs breaking change:** Minden meglévő endpoint, táblázat és API token változatlan.

---

## Deploy checklist — operátoroknak

### Előtte (staging)

- [ ] `alembic upgrade head` staging-en → nincs hiba  *(idempotent: 3× futtatva is hibamentes)*
- [ ] `alembic current` → `se002residx00 (head)`
- [ ] `python scripts/validate_system_events_deploy.py` → **SMOKE TEST PASSED — all 7 checks OK**
- [ ] Admin Dashboard → 🔔 Üzenetek tab betölt

### Éles deploy

- [ ] Maintenance window alatt: `alembic upgrade head`
- [ ] `alembic current` → `se002residx00 (head)` ellenőrzés
- [ ] Az első 15 percben: logokat figyeld (ld. Monitoring szekció)
- [ ] Admin Dashboard → 🔔 Üzenetek → Biztonság szűrő → legyen látható (vagy üres lista)

---

## Monitoring — az első deploy óra

Ezeket a log kulcsokat kell figyelni:

| Log kulcs | Súlyosság | Teendő |
|-----------|-----------|--------|
| `SYSTEM_EVENT_WRITE_FAILED` | WARNING | DB probléma — `system_events` tábla hiányzik, vagy FK hiba. Futtasd: `alembic current` |
| `SYSTEM_EVENT_PURGE_FAILED` | WARNING | APScheduler cron összeomlott. Manuális purge: `POST /api/v1/system-events/purge` |
| `relation "system_events" does not exist` | ERROR | Migráció nincs alkalmazva ezen a node-on. Futtasd: `alembic upgrade head` |

### Ha minden rendben: ezek NEM jelennek meg

Ezek a logok normálisak:
- `INFO ... system_events_purge_job scheduled at 02:00 UTC` (startup)
- `WARNING ... SECURITY: instructor multi-campus attempt blocked` (campus scope guard)

---

## Rollback protokoll

**Mikor kell rollback?** Ha `alembic upgrade head` hibát dob ÉS a hiba nem javítható az ott helyen.

```bash
# Step 1 — rollback
alembic downgrade e7f8a9b0c1d2

# Step 2 — ellenőrzés
alembic current    # → e7f8a9b0c1d2
psql $DATABASE_URL -c "SELECT to_regclass('public.system_events')"   # → NULL

# Step 3 — staging tesztek
python -m pytest tests/unit/tournament/ -q

# Step 4 — hibát bejelenteni + javítás utáni re-deploy
```

**Mit veszítünk rollback esetén?**
- A `system_events` tábla és minden benne lévő adat (deploy óta keletkezett biztonsági esemény)
- A 🔔 Üzenetek Admin tab nem működik
- Az APScheduler purge job nem fut

**Nincs** adatvesztés más táblákban. A rollback biztonságos.

---

## Ismert edge case-ek

### `type "systemeventlevel" already exists` hiba upgradekor

Ez csak akkor fordulhat elő, ha egy korábbi, megszakadt migration próbálkozás létrehozta az enum-ot de a táblát nem:

```bash
# Javítás:
psql $DATABASE_URL -c "DROP TYPE IF EXISTS systemeventlevel CASCADE"
alembic upgrade head
```

### APScheduler `jobs=[]` staging smoke testen

A scheduler csak a FastAPI app indulásakor regisztrál jobokat (lifespan event). Standalone Python scriptben ez normális. A gyártási alkalmazás startup logjában jelenik meg a `system_events_purge` job bejegyzés.

---

## Admin felhasználóknak — mi az új tab?

Az Admin Dashboard-on megjelent egy **🔔 Üzenetek** (8.) tab.

| Funkció | Leírás |
|---------|--------|
| Szűrés | SECURITY / WARNING / INFO / Összes szint |
| Resolved szűrő | Nyitott / Lezárt / Összes |
| Lapozás | 50 esemény/oldal |
| Lezárás | Soronként „Lezár" gomb |
| Karbantartás | 90 napos purge (csak lezárt eseményeket töröl) |

**Tipikus SECURITY esemény:** INSTRUCTOR szerepű felhasználó 2 campus-os tornát próbált indítani → rendszer blokkolta → SECURITY esemény keletkezett.

---

## 24-48 óra utáni ellenőrzés

24-48 órával a deploy után futtasd:

```bash
python scripts/validate_system_events_24h.py
```

Ez ellenőrzi:
- Revision még mindig `se002residx00 (head)`
- Tábla, indexek, partial index predikátum változatlan
- SECURITY event szám az utolsó 24 órában (>100 figyelmeztet)
- Nyitott esemény backlog (>500 figyelmezteti az adminokat)
- Purge job elérhetőség és eligible row count
- Partial index definíció `(resolved = false)` változatlan

---

## Kapcsolódó dokumentumok

| Dokumentum | Tartalom |
|------------|----------|
| `docs/features/ARCHITECTURE_FREEZE_2026-02-17.md` | Részletes technikai leírás, migration idempotency, monitoring |
| `docs/features/OPERATIONS_RUNBOOK_SYSTEM_EVENTS.md` | Teljes operations runbook + Quick Reference (rollback parancs) |
| `docs/release_notes/2026-02-17_system-events.md` | Release notes (migration chain, komponensek, test coverage) |
| `scripts/validate_system_events_deploy.py` | Post-deploy smoke test (7 check) |
| `scripts/validate_system_events_24h.py` | 24-48h health check (7 check + threshold warnings) |
