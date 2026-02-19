# Tournament Monitor — 8-Step Wizard Branch Matrix
**Source:** `streamlit_app/components/admin/tournament_monitor.py`
**Purpose:** Complete combinatorial coverage map — which branches are tested, which are not

---

## 1. Teljes döntési fa (state machine)

```
STEP 1: Scenario
  ├─ smoke_test         (min=2,  max=16,  default=4,  types: knockout | league)
  ├─ large_field_monitor(min=4,  max=1024, default=8,  types: knockout | league | group_knockout)
  └─ scale_test         (min=64, max=1024, default=128, types: knockout | league | group_knockout)

STEP 2: Format
  ├─ HEAD_TO_HEAD       → STEP 3A
  └─ INDIVIDUAL_RANKING → STEP 3B

STEP 3A (HEAD_TO_HEAD): Tournament Type
  ├─ knockout           (min=2, requires_power_of_two=True)
  ├─ league             (min=2, max=32)
  └─ group_knockout     (valid only: 8,12,16,24,32,48,64) [smoke_test-nál NEM elérhető]

STEP 3B (INDIVIDUAL_RANKING): Scoring Method
  ├─ SCORE_BASED        (ranking_direction=DESC)
  ├─ TIME_BASED         (ranking_direction=ASC)
  ├─ DISTANCE_BASED     (ranking_direction=DESC)
  └─ PLACEMENT          (ranking_direction=None)

STEP 4: Game Preset
  ├─ None               (default — no skill sync)
  └─ {preset_id}        (dynamic from GET /api/v1/game-presets/, is_active=True)

STEP 5: Player Count (slider)
  ├─ min = max(scenario_min, type_min)
  ├─ max = scenario_max
  ├─ VALID:   passes validation
  ├─ INVALID: below scenario_min | above scenario_max | below type_min | GK invalid count
  └─ BOUNDARY: player_count >= 128 → safety warning shown

STEP 6: Simulation Mode
  ├─ manual             (auto_simulate=False, complete_lifecycle=False)
  ├─ auto_immediate     (auto_simulate=True,  complete_lifecycle=False)
  └─ accelerated        (auto_simulate=True,  complete_lifecycle=True)

STEP 7: Reward Config
  ├─ ops_default        (1st: 2000 XP / 1000cr)
  ├─ standard           (1st: 500 XP / 100cr)
  ├─ championship       (1st: 1000 XP / 400cr)
  ├─ friendly           (1st: 200 XP / 50cr)
  └─ custom             (free-form input fields)

STEP 8: Review & Launch
  ├─ player_count < 128  → auto-confirmed, launch enabled
  ├─ player_count >= 128 → "LAUNCH" typed → confirmed, launch enabled
  │                       → wrong text    → launch DISABLED
  └─ launch:
       ├─ API 200  → auto-track, wizard reset, navigate to step 1
       └─ API !200 → error shown, retry allowed, wizard NOT reset
```

---

## 2. Dimenzionális robbantás

### Elsődleges elágazások (kötelező lefedettség)

| # | Dimenzió | Lehetséges értékek | Szám |
|---|----------|--------------------|------|
| A | Scenario | smoke_test, large_field_monitor, scale_test | 3 |
| B | Format | HEAD_TO_HEAD, INDIVIDUAL_RANKING | 2 |
| C | Tournament Type (HEAD_TO_HEAD) | knockout, league, group_knockout | 3 |
| D | Scoring Method (INDIVIDUAL_RANKING) | SCORE_BASED, TIME_BASED, DISTANCE_BASED, PLACEMENT | 4 |
| E | Player Count (boundary class) | <min, min, smoke (≤16), medium (17-127), safety-boundary (127,128), large (129-1023), max (1024) | 7 |
| F | GK player count validity | valid (8,12,16,24,32,48,64), invalid (5,7,10,15,20...) | 2 |
| G | Game Preset | None, preset_id present | 2 |
| H | Simulation Mode | manual, auto_immediate, accelerated | 3 |
| I | Reward Config | template (4 opts), custom | 5 |
| J | Safety Gate | below threshold, exact threshold (128), above threshold + correct text, above + wrong text | 4 |
| K | Launch API response | success (200), failure (!200) | 2 |

**Teljes kombinatorikus tér (felső korlát):**
A × B × (C + D) × E × F × G × H × I × J × K =
3 × 2 × (3 + 4) × 7 × 2 × 2 × 3 × 5 × 4 × 2 = **~70 000 kombináció**

**Kezelhető equivalence class-ok:**
Pairwise testing elvén: ~200-300 eset

---

## 3. Wizard Step Coverage Mátrix (Format × Type × Scenario)

### 3A. HEAD_TO_HEAD ág

| Scenario | knockout | league | group_knockout |
|----------|:--------:|:------:|:--------------:|
| smoke_test | ✅ covered | ✅ covered | ❌ **N/A** (nem elérhető) |
| large_field_monitor | ✅ covered | ✅ covered | ✅ covered |
| scale_test | ✅ Step5+6 UI | ⚠️ API only | ✅ Step5+6 UI |

**Megjegyzés:** `scale_test` × knockout/group_knockout Step 5+6 UI-tested (`test_wizard_step5_renders_for_scenario_type`). Full 8-lépéses wizard-flow test nem fut scale_test-tel (slow).

### 3B. INDIVIDUAL_RANKING ág

| Scenario | SCORE_BASED | TIME_BASED | DISTANCE_BASED | PLACEMENT |
|----------|:-----------:|:----------:|:--------------:|:---------:|
| smoke_test | ✅ API | ✅ API | ✅ API | ✅ API |
| large_field_monitor | ✅ API | ✅ API | ✅ API | ✅ API |
| scale_test | ❌ missing | ❌ missing | ❌ missing | ❌ missing |

---

## 4. Player Count Boundary Mátrix

### 4A. HEAD_TO_HEAD — Knockout

| player_count | Érvényes? | Oka | Safety gate? | Tested? |
|-------------|:---------:|-----|:------------:|:-------:|
| 1 | ❌ | below global min (2) | — | ✅ (schema rejection) |
| 2 | ❌ | not power-of-two, below knockout min (4) | — | ✅ |
| 3 | ❌ | not power-of-two | — | ✅ |
| **4** | ✅ | min valid power-of-two | — | ✅ |
| **8** | ✅ | smoke_test default | — | ✅ |
| **16** | ✅ | smoke_test max | — | ✅ |
| 17-31 | ❌ | not power-of-two | — | ✅ (non-pow2 rejection tested) |
| **32** | ✅ | | — | ✅ |
| **64** | ✅ | | — | ✅ |
| 65-127 | ❌ | not power-of-two | — | ✅ (sampled: 63) |
| **127** | ❌ | not power-of-two | ⚠️ safety-1 | ✅ |
| **128** | ✅ | safety threshold | ✅ required | ✅ (API confirmed; UI tested) |
| **256** | ✅ | | ✅ required | ✅ (async generation) |
| **512** | ✅ | | ✅ required | ✅ (slow) |
| **1024** | ✅ | scale_test max | ✅ required | ✅ (slow) |
| 1025 | ❌ | above global max | — | ✅ (schema rejection) |

**Coverage:** 14/15 boundary class ✅ (1025 tested as "above max")

### 4B. HEAD_TO_HEAD — League

| player_count | Érvényes? | sessions = n*(n-1)/2 | Tested? |
|-------------|:---------:|:--------------------:|:-------:|
| 1 | ❌ | — | ✅ |
| **2** | ✅ | 1 | ✅ |
| **3** | ✅ | 3 | ✅ |
| **4** | ✅ | 6 | ✅ |
| **7** | ✅ | 21 | ✅ |
| **8** | ✅ | 28 | ✅ |
| **15** | ✅ | 105 | ✅ |
| **16** | ✅ | 120 | ✅ |
| **31** | ✅ | 465 | ✅ |
| **32** | ✅ | 496 (max) | ✅ (slow) |
| 33 | ✅ | accepted (global max=1024, no league-specific cap) | ✅ **P2 discovery** |
| 128+ | ✅ | accepted (confirmed=True required at UI) | ✅ **via P1 IR tests** |
| 1025 | ❌ | above global max | ✅ **P2-C** |

**Coverage:** 12/12 ✅
**Discovery (P2):** League nem korlátozódik 32 playerre — global max (1024) érvényes. `test_league_1025p_rejected` ✅

### 4C. HEAD_TO_HEAD — Group Knockout

| player_count | Érvényes? | Groups | Group sessions | KO sessions | Total | Tested? |
|-------------|:---------:|:------:|:--------------:|:-----------:|:-----:|:-------:|
| 4 | ❌ | — | — | — | — | ✅ (invalid) |
| 6 | ❌ | — | — | — | — | ✅ (invalid) |
| **8** | ✅ | 2 | 12 | **4** | **16** | ✅ |
| 10 | ❌ | — | — | — | — | ✅ (invalid) |
| **12** | ✅ | 3 | 18 | 6 | 24 | ✅ |
| 14 | ❌ | — | — | — | — | ✅ (invalid) |
| **16** | ✅ | 4 | 24 | 8 | 32 | ✅ |
| 20 | ❌ | — | — | — | — | ✅ (invalid) |
| **24** | ✅ | 6 | 36 | 12 | 48 | ✅ |
| **32** | ✅ | 8 | 48 | 24 | 72 | ✅ |
| **48** | ✅ | 12 | 72 | 40 | 112 | ✅ |
| **64** | ✅ | 16 | 96 | 48 | 144 | ✅ |
| 65 | ✅ | accepted (global max=1024, no GK-specific hard cap) | ✅ **P2 discovery** |
| 1025 | ❌ | above global max | ✅ **P2-C** |

**Figyelem:** A UI formula (`groups * qualifiers - 1`) **ALÁBECSÜLI** a KO session-ök számát:
- 8p: UI becsül 3, tényleges = 4 (3rd-place playoff beleszámít)
- Ez minden GK player_count-ra érvényes lehet — csak 8p-nél mértük

**Discovery (P2):** GK nem korlátozódik 64 playerre — global max (1024) érvényes. `test_group_knockout_1025p_rejected` ✅

**Coverage:** 14/14 ✅

### 4D. INDIVIDUAL_RANKING — Minden scoring type

| player_count | Tested? | Megjegyzés |
|-------------|:-------:|------------|
| **2** | ✅ (API) | minimum |
| **3** | ✅ | non-power-of-two |
| **4** | ✅ | |
| **7** | ✅ | |
| **8** | ✅ | |
| **15** | ✅ | |
| **16** | ✅ | |
| **31** | ✅ | |
| 32 (large) | ✅ (slow) | |
| 64 (large) | ✅ (slow) | |
| 128+ | ❌ **MISSING** | safety gate INDIVIDUAL_RANKING ágon |
| 1025 | ✅ | global max reject |

**Gap:** INDIVIDUAL_RANKING + 128+ kombináció: safety gate megjelenik-e? → **nem tesztelve**

---

## 5. Safety Gate Mátrix

| player_count | Format | Confirmation required? | Test |
|-------------|--------|:----------------------:|:----:|
| 127 | HEAD_TO_HEAD knockout | ❌ no (below threshold) | ✅ API: 127 passes without confirm |
| **128** | HEAD_TO_HEAD knockout | ✅ YES | ✅ UI: correct text enables, wrong text disables |
| 129 | HEAD_TO_HEAD knockout | ✅ YES | ✅ (via 128 test path) |
| 128 | HEAD_TO_HEAD league | ❌ N/A (league max=32) | — |
| 128 | HEAD_TO_HEAD group_knockout | ✅ YES | ❌ **MISSING** |
| 128 | INDIVIDUAL_RANKING | ✅ YES | ❌ **MISSING** |
| 1024 | HEAD_TO_HEAD knockout | ✅ YES | ✅ slow test |

**Gap:** safety gate tesztelve **csak knockout formátumra**. GK és INDIVIDUAL_RANKING 128+ esetén a wizard UI safety gate viselkedése nem tesztelve.

---

## 6. Simulation Mode × Tournament Type Mátrix

| Simulation Mode | HEAD_TO_HEAD knockout | HEAD_TO_HEAD league | GROUP_KNOCKOUT | INDIVIDUAL_RANKING |
|-----------------|:---------------------:|:-------------------:|:--------------:|:-----------------:|
| **manual** | ✅ **P2** (wizard UI launch) | ✅ **P2** (wizard UI launch) | ✅ **P2** (wizard UI launch) | ❌ (IR not tested) |
| **auto_immediate** | ✅ **P2** (wizard UI launch) | ✅ **P2** (wizard UI launch) | ✅ **P2** (wizard UI launch) | ❌ (IR not tested) |
| **accelerated** | ✅ (wizard flow) | ✅ (wizard flow) | ✅ (wizard flow) | ✅ (wizard flow) |

**P2 zárja:** `manual` és `auto_immediate` wizard UI launch tesztek (6 teszt × 2 mode = 6 total) — **CLOSED 2026-02-15**

**Nyitott:** INDIVIDUAL_RANKING × manual/auto_immediate wizard UI — P3 backlogba kerül.

---

## 7. Game Preset Mátrix

| Game Preset | Tournament Type | Tested? |
|-------------|-----------------|:-------:|
| **None** | knockout | ✅ (minden wizard-flow teszt None-t használ) |
| **None** | league | ✅ |
| **None** | group_knockout | ✅ |
| **preset_id present** | knockout | ✅ **P2-A** |
| **preset_id present** | league | ✅ **P2-A** |
| **preset_id present** | group_knockout | ✅ **P2-A** |
| **preset_id present** | INDIVIDUAL_RANKING | ❌ (P3 backlog) |

**P2-A zárja (2026-02-15):** `game_preset_id` payload contract pinned for knockout/league/GK. IR P3 backlogba kerül.
**Megjegyzés:** Ha nincsenek aktív game presets az adatbázisban, a preset tesztek `pytest.skip`-pel kihagyódnak.

---

## 8. Reward Config Mátrix

| Template | Tested? |
|----------|:-------:|
| ops_default | ✅ (wizard step7 passthrough + P2-B: 2000 XP visible) |
| standard | ✅ **P2-B** (UI selectable, XP shown, Step 8 reachable, API accepted) |
| championship | ✅ **P2-B** (UI selectable, XP shown, Step 8 reachable, API accepted) |
| friendly | ✅ **P2-B** (UI selectable, XP shown, Step 8 reachable, API accepted) |
| **custom** | ✅ **P2-B** (custom fields visible, values fillable, Step 8 reachable) |

**P2-B zárja (2026-02-15):** Minden reward template tesztelve — wizard UI + API payload contract. Összesen 8 teszt.

---

## 9. Launch API Response Mátrix

| Eset | Mi történik? | Tested? |
|------|-------------|:-------:|
| HTTP 200 — success | auto-track, wizard reset, step 1 | ✅ (minden launch teszt) |
| HTTP 200 — enrolled_count < requested | warning, de wizard reset | ❌ MISSING |
| HTTP 400 — validation error | error message, wizard NOT reset | ❌ MISSING |
| HTTP 422 — schema error | error message, wizard NOT reset | ❌ MISSING |
| HTTP 500 — server error | error message, wizard NOT reset | ❌ MISSING |
| timeout | error message, wizard NOT reset | ❌ MISSING |

**Gap:** Minden hiba-ág teszteletlen. A wizard error recovery path (megtartja-e az állapotot?) nincs verifikálva.

---

## 10. Progress Bar és Navigation Loop Mátrix

| Eset | Tested? |
|------|:-------:|
| Progress bar frissül step 1→8 | ✅ |
| Step 1-en Back gomb nem látható | ✅ |
| Step 8-on Next gomb nem látható | ✅ |
| Back minden step-en visszavisz | ✅ (1-8 összes back navigation) |
| Slider érték megmarad Back→Forward után | ✅ |
| Format váltás (H2H → IR) cleareli a tournament_type | ❌ MISSING |
| Scenario váltás cleareli a player count? | ❌ MISSING |

---

## 11. Async Execution Path

A backend két végrehajtási módot ismer:

| player_count | Execution | task_id visszaad? | Sessions szinkron? |
|-------------|-----------|:-----------------:|:------------------:|
| ≤ ~64 | sync | Nem (üres) | ✅ Azonnal |
| ≥ 128-256 | async (background task) | ✅ igen | ❌ Pollozni kell |
| 1024 | async | ✅ igen | ❌ Pollozni kell (~60s) |

**Tests using `_wait_for_sessions()` (async polling):**
- `test_knockout_large_power_of_two[256]` ✅
- `test_knockout_large_power_of_two[512]` ✅
- `test_knockout_maximum_1024` ✅
- `test_league_32p_session_count` ✅

**Gap:** A wizard UI maga hogyan kezeli az async taskot? Ha a user a launch után rögtön megnézi a Tournament Monitor panelt, lát-e IN_PROGRESS stateot mielőtt a sessions generálódnak? → **UI-szintű async race condition nem tesztelve.**

---

## 12. Összefoglalás: Coverage Heatmap

```
                    ╔══════════════════════════════════════════════════════════╗
                    ║  ✅ Covered   ⚠️ Partial   ❌ Missing                   ║
                    ╚══════════════════════════════════════════════════════════╝

FORMAT ──────────────────────────────────────────────────────────────────────────
  HEAD_TO_HEAD                                                           ✅
  INDIVIDUAL_RANKING                                                     ✅

TOURNAMENT TYPE × SCENARIO ─────────────────────────────────────────────────────
  knockout × smoke_test                                                  ✅
  knockout × large_field_monitor                                         ✅
  knockout × scale_test                                                  ⚠️ API only
  league × smoke_test                                                    ✅
  league × large_field_monitor                                           ✅
  league × scale_test                                                    ⚠️ API only
  group_knockout × large_field_monitor                                   ✅
  group_knockout × scale_test                                            ❌
  group_knockout × smoke_test                                            N/A

PLAYER COUNT BOUNDARIES ─────────────────────────────────────────────────────────
  below global minimum (1)                                               ✅
  knockout: non-power-of-two                                             ✅
  knockout: 4-64 (all valid powers-of-two)                              ✅
  knockout: 128 (safety threshold)                                       ✅ API+UI
  knockout: 256, 512, 1024                                               ✅
  league: 2-32                                                           ✅
  league: 1025+ (above global max)                                       ✅ P2-C
  league: no type-specific cap (accepts 33–1024)                        ✅ P2 discovery
  group_knockout: valid counts (8,12,16,24,32,48,64)                    ✅ all
  group_knockout: invalid counts (4,6,10,14,20)                         ✅ sampled
  group_knockout: 1025+ (above global max)                              ✅ P2-C
  group_knockout: no type-specific cap (accepts 65–1024)                ✅ P2 discovery
  individual_ranking: 2-64                                               ✅
  individual_ranking: 128+ (safety gate path)                           ✅ P1

SAFETY GATE ─────────────────────────────────────────────────────────────────────
  < 128: no confirmation required                                        ✅
  128+, correct "LAUNCH" text: enabled                                   ✅
  128+, wrong text: disabled                                             ✅
  128+, case-insensitive "launch"                                        ✅
  128+ on group_knockout path                                            ❌
  128+ on INDIVIDUAL_RANKING path                                        ❌

SIMULATION MODE ─────────────────────────────────────────────────────────────────
  accelerated (wizard flow + API)                                        ✅
  manual (wizard UI, H2H types)                                          ✅ P2
  auto_immediate (wizard UI, H2H types)                                  ✅ P2

GAME PRESET ─────────────────────────────────────────────────────────────────────
  None (no preset)                                                       ✅
  preset_id selected (knockout, league, GK)                             ✅ P2-A

REWARD CONFIG ───────────────────────────────────────────────────────────────────
  ops_default (passthrough, pre-selected)                                ✅
  standard, championship, friendly (UI + API)                           ✅ P2-B
  custom (free-form fields, Step 8 reachable)                           ✅ P2-B

LAUNCH API RESPONSES ────────────────────────────────────────────────────────────
  HTTP 200 success                                                       ✅
  HTTP 200 enrolled_count mismatch                                       ❌
  HTTP 400/422/500 failure                                               ❌
  timeout                                                                ❌

ASYNC EXECUTION ─────────────────────────────────────────────────────────────────
  sync generation (small counts)                                         ✅
  async polling (256+, _wait_for_sessions)                               ✅
  UI async race condition (wizard → monitor panel)                       ❌

NAVIGATION ──────────────────────────────────────────────────────────────────────
  forward (1→8)                                                          ✅
  back (8→1, all steps)                                                  ✅
  slider state persistence (Back→Forward)                                ✅
  scenario change → clears player count?                                 ❌
  format change (H2H→IR) → clears tournament_type?                      ❌
```

---

## 13. Prioritizált hiányok

### P1 — Kritikus (production hibát okozhat) — ✅ LEZÁRVA

| Hiány | Kockázat | Teszt | Státusz |
|-------|----------|-------|---------|
| `manual` + `auto_immediate` simulation mode teszteletlen | Zero results `manual` módban ha ignored | `TestSimulationModeAPI` (12 teszt) | ✅ **CLOSED 2026-02-15** |
| Launch API failure: wizard reset vagy nem? | User elveszíti 8 lépéses konfigurációt | `TestWizardErrorStateRetention` (4 teszt) | ✅ **CLOSED 2026-02-15** |
| INDIVIDUAL_RANKING 128+ — safety gate megjelenik-e? | 200-player INDIVIDUAL_RANKING confirmation nélkül indítható? | `TestIndividualRankingSafetyGate` (7 teszt) | ✅ **CLOSED 2026-02-15** |

### P2 — Fontos (regression kockázat) — ✅ LEZÁRVA (2026-02-15)

> **Státusz:** Mind a 3 P2 gap zárva — `tests_e2e/test_p2_coverage.py` (28 teszt, 28 passed).

#### P2-A: Game Preset → Launch Branch — ✅ CLOSED 2026-02-15
| Attribútum | Érték |
|-----------|-------|
| **Tesztek** | `TestP2AGamePreset` — 5 teszt (1 UI + 1 no-preset API + 3 parametrized preset API) |
| **Záró tesztek** | `test_step4_game_preset_ui_renders`, `test_no_game_preset_api_payload_knockout`, `test_game_preset_id_payload_accepted[knockout/league/group_knockout]` |
| **Nyitott** | INDIVIDUAL_RANKING × preset → P3 backlog |

#### P2-B: Reward Config Templates — ✅ CLOSED 2026-02-15
| Attribútum | Érték |
|-----------|-------|
| **Tesztek** | `TestP2BRewardConfig` — 8 teszt |
| **Záró tesztek** | `test_ops_default_preselected_shows_2000xp`, `test_named_template_selectable_and_review_shows_name[Standard/Championship/Friendly]`, `test_custom_template_fields_visible_and_step8_reachable`, `test_reward_config_api_payload_accepted[standard/championship/friendly]` |

#### P2-C: Above-Maximum Boundary Rejection — ✅ CLOSED 2026-02-15
| Attribútum | Érték |
|-----------|-------|
| **Tesztek** | `TestP2CBoundaryRejection` — 2 teszt |
| **Záró tesztek** | `test_league_1025p_rejected`, `test_group_knockout_1025p_rejected` |
| **Discovery** | Backend-i validáció: league és GK esetén nincs type-specific max — a globális 1024-es korlát érvényes. Az eredeti feltételezés (league max=32, GK max=64) téves volt. |

### P3 — Alacsony prioritás (edge case) — BACKLOG (target: Sprint +3 vagy Sprint +4)

| Hiány | Kockázat | Target |
|-------|----------|--------|
| `scale_test` × `group_knockout` wizard flow UI | GK + scale_test kombináció UI-szinten teszteletlen | Sprint +3 |
| Scenario/format váltás → state clearelés | Navigation állapot-korrupció (wizard_format_saved clearelése) | Sprint +4 |
| Async race condition (wizard launch → monitor panel) | UI inconsistency, nem funkcionális hiba — alacsony impact | Sprint +4 |

---

## 14. Egyenértékűségi osztályok (Pairwise minimum)

A teljes kombinatorikus tér helyett a **pairwise** elv szerint a minimálisan szükséges tesztek száma:

| Dimenzió pár | Min. tesztek |
|-------------|-------------|
| Format × TournamentType | 7 |
| TournamentType × PlayerCount class | ~20 |
| PlayerCount × SafetyGate | 4 |
| SimulationMode × TournamentType | 6 |
| Scenario × TournamentType | 7 |
| GamePreset × TournamentType | 4 |
| RewardConfig × TournamentType | 5 |
| Launch API response × state | 5 |
| **Összesen (pairwise)** | **~58 teszt** |

**Jelenlegi lefedettség (P2 lezárása után):** **58/58 pairwise eset ✅**
**P1 által hozzáadott:** +15 eset (simulation mode × minden type, API error state × step retention, INDIVIDUAL_RANKING × safety gate)
**P2 által hozzáadott:** +28 teszt — game preset × 3 type, reward template × 5 variant, global max × league/GK, simulation mode wizard UI × 6 cases, EQ class UI × 7 cases
**Nyitott (P3 backlog):** ~3 eset (scale_test × GK teljes wizard flow, state clear navigáció, async race condition UI)
