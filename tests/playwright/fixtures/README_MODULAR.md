# Modular JSON Fixture System

## Overview

A rugalmas, komponensekre bontott tesztelési adatrendszer, amely lehetővé teszi:

- ✅ **Szelektív adatbetöltés** - csak azt töltsd be, amire szükséged van
- ✅ **Gyors iteráció** - ne várj a teljes dataset betöltésére
- ✅ **Rugalmas kombináció** - keverj egyszerű és komplex tournamenteket
- ✅ **Backward compatibility** - a régi single-file fixtures továbbra is működnek

---

## File Structure

```
tests/playwright/fixtures/
├── users.json                  # User accounts (admin, instructors, students)
├── locations.json              # Locations + campuses
├── tournaments_simple.json     # Simple YOUTH tournaments (NO workflow)
├── tournaments_full.json       # Full workflow tournaments (APPLICATION_BASED, statuses)
├── coupons.json                # Enrollment coupons
├── seed_data_simple.json       # Legacy: all-in-one simple fixture
└── seed_data.json              # Legacy: all-in-one full fixture
```

---

## Module Contents

### `users.json`
- 1 admin: `admin@lfa.com`
- 1 grandmaster instructor: `grandmaster@lfa.com` (LFA_COACH level 8, LFA_FOOTBALL_PLAYER level 8, INTERNSHIP level 5)
- 3 onboarded students with **complete** profile and onboarding data:
  - Profile: first_name, last_name, nickname, date_of_birth, phone, address
  - Onboarding: position (MIDFIELDER/STRIKER/DEFENDER), skills (6 scores: heading, shooting, passing, dribbling, defending, physical), goals, motivation

**Dependencies:** None

### `locations.json`
- 3 locations:
  - Budapest Sports Complex (Main Campus, Youth Training Center)
  - Debrecen Training Facility (Stadium Campus)
  - Győr Sports Arena (West Campus)

**Dependencies:** None

### `tournaments_simple.json`
- 3 YOUTH tournaments at different locations/dates
- **Minimal workflow fields:**
  - 2x APPLICATION_BASED + SEEKING_INSTRUCTOR
  - 1x OPEN_ASSIGNMENT + READY_FOR_ENROLLMENT + assigned instructor
- Perfect for testing basic tournament creation with required fields

**Dependencies:** `locations.json`, `users.json` (for OPEN_ASSIGNMENT instructor)

### `tournaments_full.json`
- 3 tournaments with FULL workflow fields:
  - APPLICATION_BASED with SEEKING_INSTRUCTOR status
  - OPEN_ASSIGNMENT with READY_FOR_ENROLLMENT + assigned instructor
  - PRE age_group tournament
- Tests complete tournament lifecycle

**Dependencies:** `locations.json`, `users.json` (for instructor assignment)

### `coupons.json`
- 3 player-specific coupons (500 credits each)
- 1 general coupon (WELCOME500, 100 uses)

**Dependencies:** `users.json` (for assignment)

---

## Usage

### Single Fixture (Backward Compatible)

```bash
# Load complete dataset from single file
DATABASE_URL="postgresql://..." python scripts/seed_modular.py --fixture=seed_data_simple
```

### Modular Loading

```bash
# Minimal: just simple tournaments
DATABASE_URL="postgresql://..." python scripts/seed_modular.py \
  --modules users locations tournaments_simple

# Full workflow: complex tournaments with coupons
DATABASE_URL="postgresql://..." python scripts/seed_modular.py \
  --modules users locations tournaments_full coupons

# Only locations (for testing location management)
DATABASE_URL="postgresql://..." python scripts/seed_modular.py \
  --modules locations

# Mix: simple tournaments + coupons
DATABASE_URL="postgresql://..." python scripts/seed_modular.py \
  --modules users locations tournaments_simple coupons
```

---

## Common Scenarios

### 1. Test Basic Tournament Creation (Stable Baseline)

**Goal:** Verify JSON → seed script → DB → UI pipeline works

```bash
python scripts/seed_modular.py --modules users locations tournaments_simple
```

**What you get:**
- 3 YOUTH tournaments with TOURN- prefix
- 2x APPLICATION_BASED (instructors can apply)
- 1x OPEN_ASSIGNMENT (instructor pre-assigned)
- Visible in admin UI
- All required workflow fields populated

### 2. Test Tournament Instructor Assignment Workflow

**Goal:** Test APPLICATION_BASED and OPEN_ASSIGNMENT workflows

```bash
python scripts/seed_modular.py --modules users locations tournaments_full
```

**What you get:**
- APPLICATION_BASED tournament in SEEKING_INSTRUCTOR status
- OPEN_ASSIGNMENT tournament with pre-assigned instructor
- Ready to test instructor application/assignment flows

### 3. Test Enrollment with Coupons

**Goal:** Test player enrollment with coupon redemption

```bash
python scripts/seed_modular.py --modules users locations tournaments_simple coupons
```

**What you get:**
- 3 simple tournaments
- 3 player accounts with 500 credit coupons
- Ready to test enrollment flow

### 4. Fresh Start

**Goal:** Rebuild entire test dataset from scratch

```bash
# Option 1: Modular
python scripts/seed_modular.py --modules users locations tournaments_full coupons

# Option 2: Single fixture
python scripts/seed_modular.py --fixture=seed_data
```

---

## Dependency Graph

```
tournaments_simple ─┐
                    ├─→ locations
tournaments_full ───┤
                    └─→ users (for instructor assignment)

coupons ───→ users (for assignment)

users ──→ (no dependencies)
locations ──→ (no dependencies)
```

**Rule:** Always load dependencies BEFORE dependent modules.

---

## Idempotent Seeding

All seed functions check for existing records:

```python
existing = db.query(Semester).filter(Semester.name == tour_name).first()
if existing:
    print(f"⚠️  Tournament '{tour_name}' already exists, skipping")
    continue
```

**Benefit:** Re-running the seeder is safe - it only creates missing entities.

---

## Creating New Modules

### 1. Create JSON File

```json
// tests/playwright/fixtures/my_custom_data.json
{
  "tournaments": [
    {
      "code": "TOURN-CUSTOM-001",
      "name": "My Custom Tournament",
      "age_group": "YOUTH",
      "location": "Budapest Sports Complex",
      "campus": "Main Campus",
      "max_players": 10,
      "enrollment_cost": 0,
      "start_date": "2026-05-01",
      "end_date": "2026-05-01"
    }
  ]
}
```

### 2. Use It

```bash
python scripts/seed_modular.py --modules users locations my_custom_data
```

---

## Validation

### Check Tournaments in Admin UI

1. Open: http://localhost:8501
2. Login: `admin@lfa.com` / `admin123`
3. Navigate: **Admin Dashboard** → **🏆 Tournaments**
4. Verify: All tournaments with `TOURN-` prefix are visible

### Check via API

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lfa.com","password":"admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/v1/semesters/ \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys, json; \
    data = json.load(sys.stdin); \
    tournaments = [s for s in data.get('semesters', []) if s.get('code', '').startswith('TOURN-')]; \
    print(f'Tournaments: {len(tournaments)}'); \
    [print(f\"  - {t['code']}: {t['name']}\") for t in tournaments]"
```

### Check Database

```bash
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c \
  "SELECT id, code, name, age_group, tournament_status, assignment_type
   FROM semesters WHERE code LIKE 'TOURN-%' ORDER BY id;"
```

---

## Migration from Single-File Fixtures

**Old way:**
```bash
python scripts/seed_from_json.py --fixture=seed_data_simple
```

**New way (equivalent):**
```bash
python scripts/seed_modular.py --modules users locations tournaments_simple coupons
```

**Advantage:** Now you can skip coupons if you don't need them:
```bash
python scripts/seed_modular.py --modules users locations tournaments_simple
```

---

## Best Practices

1. **Start simple** - Use `tournaments_simple` to validate baseline
2. **Add complexity incrementally** - Switch to `tournaments_full` when ready
3. **Load only what you need** - Faster iteration during development
4. **Keep modules focused** - Don't mix simple and full workflows in same module
5. **Document dependencies** - Always list required modules in comments

---

## Troubleshooting

### "Location/Campus not found"

**Cause:** Trying to load tournaments without locations

**Fix:**
```bash
# ❌ Missing dependency
python scripts/seed_modular.py --modules tournaments_simple

# ✅ Include dependency
python scripts/seed_modular.py --modules locations tournaments_simple
```

### "Instructor not found"

**Cause:** `tournaments_full` references instructor, but users not loaded

**Fix:**
```bash
# ❌ Missing users
python scripts/seed_modular.py --modules locations tournaments_full

# ✅ Include users
python scripts/seed_modular.py --modules users locations tournaments_full
```

### Tournaments not visible in admin UI

**Cause:** Tournament code doesn't start with `TOURN-`

**Fix:** Update JSON:
```json
{
  "code": "TOURN-MY-TOURNAMENT"  // ✅ Correct prefix
}
```

---

## See Also

- [README.md](README.md) - Original fixture system documentation
- [seed_modular.py](../../scripts/seed_modular.py) - Seeder script source code
- [E2E_CONFIDENCE_REPORT.md](../../docs/E2E_CONFIDENCE_REPORT.md) - E2E test validation
