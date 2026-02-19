# 🎯 Sandbox UI Redesign - 2 Radikális Egyszerűsítési Terv

## Jelenlegi probléma
- Túl bonyolult UI (expanders, nested forms, dynamic widgets)
- Toggle switches nem látszanak/találhatók Playwright-ben
- Nem lineáris flow (görgetve kell keresni elemeket)
- Email linkek, dropdown-ok, state-függő renderelés
- **NEM ALKALMAS egyszerű E2E tesztekre!**

---

## ✅ TERV A: "Single Column Form" - Ultra-egyszerű Lineáris Nézet

### Koncepció
**Egyetlen függőleges lista minden inputtal, semmi dinamika, semmi elrejtés**

### Vizuális Layout

```
╔══════════════════════════════════════════════════════════════╗
║  🧪 SANDBOX TOURNAMENT TEST (Quick Test Mode)               ║
╚══════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────┐
│ 1️⃣ LOCATION & CAMPUS                                         │
├──────────────────────────────────────────────────────────────┤
│ Location:     [Vienna Academy (Vienna)         ▼]           │
│ Campus:       [Vienna Main Campus              ▼]           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 2️⃣ TOURNAMENT DETAILS                                        │
├──────────────────────────────────────────────────────────────┤
│ Name:         [Sandbox Test 2026-01-30        ]             │
│ Date:         [2026-01-30                      ]             │
│ Age Group:    [AMATEUR                         ▼]           │
│ Type:         [league                          ▼]           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 3️⃣ PARTICIPANTS (Select 4-16 players)                        │
├──────────────────────────────────────────────────────────────┤
│ [✓] Player 1 (test.player1@f1rstteam.hu) - ID: 5            │
│ [✓] Player 2 (test.player2@f1rstteam.hu) - ID: 6            │
│ [✓] Player 3 (test.player3@f1rstteam.hu) - ID: 7            │
│ [✓] Player 4 (test.player4@f1rstteam.hu) - ID: 13           │
│ [✓] Player 5 (test.player5@f1rstteam.hu) - ID: 14           │
│ [✓] Player 6 (test.player6@f1rstteam.hu) - ID: 15           │
│ [✓] Player 7 (test.player7@f1rstteam.hu) - ID: 16           │
│ [ ] Junior Intern (junior.intern@f1rstteam.hu) - ID: 4      │
│                                                              │
│ ✅ 7 players selected                                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 4️⃣ CONFIGURATION (Pre-filled from Game Preset)               │
├──────────────────────────────────────────────────────────────┤
│ Skills:        ☑ Passing  ☑ Shooting  ☑ Dribbling          │
│ Format:        HEAD_TO_HEAD (1v1 matches)                   │
│ Max Players:   16                                            │
│ Rewards:       1st: 100 XP | 2nd: 70 XP | 3rd: 50 XP       │
└──────────────────────────────────────────────────────────────┘

                   ┌────────────────────┐
                   │  ⚡ RUN QUICK TEST  │
                   └────────────────────┘

```

### Playwright Selector Stratégia

```python
# Location
page.locator('select[aria-label*="Location"]').select_option('Vienna Academy')

# Campus
page.locator('select[aria-label*="Campus"]').select_option('Vienna Main Campus')

# Age Group
page.locator('select[aria-label*="Age Group"]').select_option('AMATEUR')

# Participants - SIMPLE CHECKBOXES
checkboxes = page.locator('input[type="checkbox"][id^="participant_"]').all()
for i in range(7):
    checkboxes[i].check()

# Run button
page.get_by_role('button', name='RUN QUICK TEST').click()
```

### Előnyök
- ✅ Minden látható, nincs scroll/expand
- ✅ Egyszerű checkbox-ok (NO toggles, NO labels with links)
- ✅ Determinisztikus sorrend
- ✅ Statikus layout, nincs dinamikus renderelés
- ✅ Minimal Playwright selectors
- ✅ Lineáris flow: felülről lefelé

### Hátrányok
- Nem szép (de ez sandbox, nem számít!)
- Hosszú oldal (de Playwright-nek mindegy)

---

## ✅ TERV B: "API-Style Form" - Key-Value Input Mezők

### Koncepció
**JSON-szerű API request builder UI - minden mező egy key-value pair**

### Vizuális Layout

```
╔══════════════════════════════════════════════════════════════╗
║  🧪 SANDBOX TEST - API REQUEST BUILDER                      ║
╚══════════════════════════════════════════════════════════════╝

🔧 QUICK TEST CONFIGURATION

┌─────────────────────┬────────────────────────────────────────┐
│ location_id         │ [2]                                    │
├─────────────────────┼────────────────────────────────────────┤
│ campus_id           │ [2]                                    │
├─────────────────────┼────────────────────────────────────────┤
│ tournament_name     │ [Sandbox Test 2026-01-30]              │
├─────────────────────┼────────────────────────────────────────┤
│ tournament_date     │ [2026-01-30]                           │
├─────────────────────┼────────────────────────────────────────┤
│ age_group           │ [AMATEUR]                              │
├─────────────────────┼────────────────────────────────────────┤
│ tournament_type     │ [league]                               │
├─────────────────────┼────────────────────────────────────────┤
│ user_ids            │ [5, 6, 7, 13, 14, 15, 16]              │
│                     │ (comma-separated IDs)                  │
├─────────────────────┼────────────────────────────────────────┤
│ skills              │ [passing, shooting, dribbling]         │
├─────────────────────┼────────────────────────────────────────┤
│ format              │ [HEAD_TO_HEAD]                         │
├─────────────────────┼────────────────────────────────────────┤
│ max_players         │ [16]                                   │
└─────────────────────┴────────────────────────────────────────┘

                   ┌────────────────────┐
                   │  ⚡ RUN TEST        │
                   └────────────────────┘

📋 RESPONSE PREVIEW

{
  "location_id": 2,
  "campus_id": 2,
  "tournament_name": "Sandbox Test 2026-01-30",
  "age_group": "AMATEUR",
  "tournament_type": "league",
  "user_ids": [5, 6, 7, 13, 14, 15, 16],
  "player_count": 7
}
```

### Playwright Selector Stratégia

```python
# Fill form using labels (consistent naming)
page.locator('input[aria-label="location_id"]').fill('2')
page.locator('input[aria-label="campus_id"]').fill('2')
page.locator('input[aria-label="age_group"]').fill('AMATEUR')
page.locator('input[aria-label="user_ids"]').fill('5,6,7,13,14,15,16')

# Run
page.get_by_role('button', name='RUN TEST').click()
```

### Előnyök
- ✅ **ULTRA-SIMPLE**: Csak text input-ok!
- ✅ Nincs dropdown, checkbox, toggle - csak egyszerű mezők
- ✅ Könnyen debuggolható (látszik mi megy a backend-be)
- ✅ Playwright-friendly: `fill()` minden mezőre
- ✅ Gyors kitöltés (copy-paste JSON values)
- ✅ Determinisztikus, nincs UI state

### Hátrányok
- Nem user-friendly (de ez sandbox tesztekhez!)
- User ID-kat kézzel kell írni (de tesztnél nem számít)

---

## 🎯 AJÁNLÁS: TERV A - Single Column Form

### Miért Terv A?

| Szempont                    | Terv A | Terv B |
|-----------------------------|--------|--------|
| Playwright egyszerűség      | ⭐⭐⭐   | ⭐⭐⭐⭐⭐ |
| UI megérthetőség            | ⭐⭐⭐⭐  | ⭐⭐    |
| Hibakeresés                 | ⭐⭐⭐⭐  | ⭐⭐⭐⭐⭐ |
| Gyors implementálás         | ⭐⭐⭐⭐  | ⭐⭐⭐   |
| Manual testing is lehetséges| ⭐⭐⭐⭐  | ⭐     |

**TERV A a győztes**, mert:
1. **Egyszerű checkbox-ok** könnyebben működnek mint toggle-ok
2. **Vizuális feedback** - látod hogy mi van kiválasztva
3. **Hibrid használat** - emberek is tudják használni manuálisan
4. **Gyors implementálás** - csak layout változtatás, nincs új logic

---

## 🚀 Implementációs Lépések (Terv A)

### 1. Participant Selection átalakítása

**ELŐTTE** (toggle table):
```python
for user in users:
    is_active = cols[0].toggle(
        label="",
        value=False,
        key=f"toggle_user_{user['id']}"
    )
```

**UTÁNA** (simple checkboxes):
```python
for user in users:
    is_selected = st.checkbox(
        f"[{user['id']}] {user['name']} ({user['email']})",
        value=False,
        key=f"participant_{user['id']}"
    )
```

### 2. Layout egyszerűsítés

- ❌ Eltávolítani: összes st.expander()
- ❌ Eltávolítani: összes st.columns() táblázat
- ✅ Hozzáadni: Simple sections with st.markdown headers
- ✅ Hozzáadni: Clear visual separators (st.markdown("---"))

### 3. Playwright test frissítés

```python
# Find checkboxes by ID pattern
checkboxes = page.locator('input[type="checkbox"][id*="participant_"]').all()

# Select first 7
for i in range(7):
    if checkboxes[i].is_visible():
        checkboxes[i].check()
```

---

## 📊 Összehasonlítás

| Feature                  | Jelenlegi | Terv A | Terv B |
|--------------------------|-----------|--------|--------|
| Expanders                | Sok       | 0      | 0      |
| Toggle switches          | Igen      | Nem    | Nem    |
| Simple checkboxes        | Nem       | ✅     | Nem    |
| Text inputs only         | Nem       | Nem    | ✅     |
| Playwright complexity    | Magas     | Alacsony | Nagyon alacsony |
| Manual usability         | Közepes   | Jó     | Rossz  |
| Debug-olhatóság          | Nehéz     | Könnyű | Nagyon könnyű |

---

## ✅ DÖNTÉS

**Terv A - Single Column Form** implementálása következik!

**Következő lépések:**
1. Participant Selection átalakítás checkbox-okra
2. Összes expander eltávolítása (már kész!)
3. Layout egyszerűsítés - single column
4. Playwright test frissítés checkbox selector-okkal
5. Teljes E2E teszt futtatás

**ETA:** 10-15 perc implementáció + teszt
