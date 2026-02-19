# 🎯 Sandbox UI Refactor - 3 Konkrét Terv

## Jelenlegi probléma
- Túl sok expander, dolgok el vannak rejtve
- Checkboxok nem működnek Playwright-tel
- UI nem lineáris, nehéz automatizálni
- Email linkek megnyílnak checkbox kattintáskor

---

## ✅ TERV 1: Egyszerű Táblázatos Nézet (AJÁNLOTT)

### Struktúra (minden látható, nincs expander):

```
🧪 Sandbox Tournament Test (Admin-Aligned)
═══════════════════════════════════════════════

🎯 Test Mode
  ○ ⚡ Quick Test (Auto-complete)
  ○ 👨‍🏫 Instructor Workflow

─────────────────────────────────────────────────

0️⃣ Game Type Selection
  Preset: [Quick Test Default Preset ▼]
  ✅ Loaded: Quick Test Default Preset

─────────────────────────────────────────────────

1️⃣ Location & Campus
  Location: [Vienna Academy (Vienna) ▼]
  Campus: [Vienna Main Campus ▼]

─────────────────────────────────────────────────

2️⃣ Tournament Details
  Tournament Type: [league ▼]
  Tournament Name: [Sandbox Test 2026-01-30]
  Tournament Date: [2026/01/30]

─────────────────────────────────────────────────

3️⃣ Tournament Format
  Age Group: [AMATEUR ▼]
  Format: [HEAD_TO_HEAD (1v1 matches) ▼]
  Assignment Type: [OPEN_ASSIGNMENT ▼]
  Max Players: [16]
  Price: [50]

─────────────────────────────────────────────────

4️⃣ Skill Configuration
  Skills to Test: ☑ Passing  ☑ Shooting  ☑ Dribbling

─────────────────────────────────────────────────

5️⃣ Reward Configuration
  💡 Pre-filled from Game Preset - do not modify

  1st Place: 🥇 100 XP + 🏅 Gold Badge
  2nd Place: 🥈 70 XP + 🏅 Silver Badge
  3rd Place: 🥉 50 XP + 🏅 Bronze Badge

─────────────────────────────────────────────────

6️⃣ Participant Selection
  💡 Select users to enroll. Toggle ON/OFF for each.

  | Active | Name                  | Email                          | ID |
  |--------|-----------------------|--------------------------------|----|
  | [○]    | Junior Intern         | junior.intern@f1rstteam.hu     | 4  |
  | [●]    | Test Player 1         | test.player1@f1rstteam.hu      | 5  |
  | [●]    | Test Player 2         | test.player2@f1rstteam.hu      | 6  |
  | [●]    | Test Player 3         | test.player3@f1rstteam.hu      | 7  |
  | [●]    | Test Player 4         | test.player4@f1rstteam.hu      | 13 |
  | [●]    | Test Player 5         | test.player5@f1rstteam.hu      | 14 |
  | [●]    | Test Player 6         | test.player6@f1rstteam.hu      | 15 |
  | [●]    | Test Player 7         | test.player7@f1rstteam.hu      | 16 |

  ✅ Selected: 7 users → IDs: [5,6,7,13,14,15,16]

─────────────────────────────────────────────────

                  [⚡ Run Quick Test]
```

### Előnyök:
- ✅ Minden látható, semmi nincs elrejtve
- ✅ Toggle kapcsolók egyszerűbbek mint checkboxok
- ✅ Táblázat jól strukturált
- ✅ Playwright könnyen találja a toggle-okat
- ✅ Nincs email link kattintási probléma

---

## ✅ TERV 2: Kártyás Layout (Alternatíva)

### Struktúra:

```
🧪 Sandbox Tournament Test
═══════════════════════════════════════════════

┌─────────────────────────────────────────────┐
│ 🎯 Test Mode                                │
│   • Quick Test (Auto-complete)              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 0️⃣ Game Preset                              │
│   Preset: Quick Test Default Preset         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 1️⃣ Location & Campus                        │
│   Location: Vienna Academy (Vienna)         │
│   Campus: Vienna Main Campus                │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 2️⃣ Tournament Details                       │
│   Type: league                              │
│   Name: Sandbox Test 2026-01-30             │
│   Date: 2026/01/30                          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 3️⃣ Format & Settings                        │
│   Age: AMATEUR                              │
│   Format: HEAD_TO_HEAD                      │
│   Max Players: 16                           │
│   Price: 50                                 │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 4️⃣ Skills                                   │
│   ☑ Passing  ☑ Shooting  ☑ Dribbling       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 5️⃣ Rewards (from preset)                    │
│   1st: 100 XP + Gold Badge                  │
│   2nd: 70 XP + Silver Badge                 │
│   3rd: 50 XP + Bronze Badge                 │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 6️⃣ Participants (7 selected)                │
│   ● Test Player 1 (test.player1@...)        │
│   ● Test Player 2 (test.player2@...)        │
│   ● Test Player 3 (test.player3@...)        │
│   ○ Junior Intern (junior.intern@...)       │
│   (toggle ON/OFF each participant)          │
└─────────────────────────────────────────────┘

                [⚡ Run Quick Test]
```

### Előnyök:
- ✅ Vizuálisan szeparált szekciók
- ✅ Kompakt nézet
- ✅ Minden látható

---

## ✅ TERV 3: Két Oszlopos Layout (Haladó)

### Struktúra:

```
🧪 Sandbox Tournament Test
═══════════════════════════════════════════════

┌────────────────────────┬────────────────────┐
│ LEFT PANEL             │ RIGHT PANEL        │
├────────────────────────┼────────────────────┤
│ 🎯 Test Mode           │ 6️⃣ Participants    │
│   • Quick Test         │                    │
│                        │ 🔍 Search: [____]  │
│ 0️⃣ Game Preset         │                    │
│   [Preset dropdown]    │ Active | Name      │
│                        │ ──────┼────────    │
│ 1️⃣ Location            │  [●]  Player 1     │
│   [Vienna ▼]           │  [●]  Player 2     │
│   [Main Campus ▼]      │  [●]  Player 3     │
│                        │  [●]  Player 4     │
│ 2️⃣ Tournament          │  [●]  Player 5     │
│   Type: league         │  [●]  Player 6     │
│   Name: [______]       │  [●]  Player 7     │
│   Date: [______]       │  [○]  Junior       │
│                        │                    │
│ 3️⃣ Format              │ ✅ 7 selected      │
│   Age: AMATEUR         │                    │
│   Format: H2H          │                    │
│   Max: 16              │                    │
│   Price: 50            │                    │
│                        │                    │
│ 4️⃣ Skills              │                    │
│   ☑ Passing            │                    │
│   ☑ Shooting           │                    │
│   ☑ Dribbling          │                    │
│                        │                    │
│ 5️⃣ Rewards             │                    │
│   1st: 100 XP          │                    │
│   2nd: 70 XP           │                    │
│   3rd: 50 XP           │                    │
└────────────────────────┴────────────────────┘

            [⚡ Run Quick Test]
```

### Előnyök:
- ✅ Hatékony helykihasználás
- ✅ Participants mindig látható jobb oldalon
- ✅ Config bal oldalon lineárisan

---

## 🎯 AJÁNLÁS: TERV 1

**Miért?**
1. Legegyszerűbb implementálni
2. Legjobban működik Playwright-tel
3. Minden látható, lineáris flow
4. Toggle kapcsolók egyértelműek
5. Táblázat tiszta struktúra

**Következő lépések:**
1. Implementálom TERV 1-et
2. Frissítem Playwright tesztet toggle-okhoz
3. Teljes E2E teszt futtatás
4. Dokumentálom a változásokat

---

**Kérdés:** Melyik tervet részesíted előnyben? (1, 2, vagy 3)
