# Skill Dashboard UX Test Guide

**Cél**: Valós használati tapasztalatok gyűjtése a skill dashboard-ról
**Módszer**: Irányított manuális tesztelés konkrét user szcenáriókkal
**Fókusz**: UX megértés, ne technikai validáció

---

## Előkészítés: Test User Setup

### 1. Új Player Account Létrehozása

**Lépések**:
1. Nyisd meg: http://localhost:8501
2. Registration tab → Fill form
3. Email: `ux.test.player@f1rstteam.hu`
4. Nickname: `UX Test Player`
5. Complete registration

**Elvárás**: User létrejön, onboarding flow indul

---

### 2. Onboarding: Skill Baseline Beállítása

**Szcenárió**: Junior játékos, átlagos képességekkel

**Baseline értékek** (játékos self-assessment):
- Speed: 65
- Stamina: 70
- Ball Control: 60
- Passing: 55
- Shooting: 50
- Defending: 45
- Positioning: 60

**Mit figyeljünk**:
- [ ] Skill baseline-ok mentődnek a `user_licenses.football_skills`-be
- [ ] Onboarding után skill dashboard megjelenik-e
- [ ] Baseline értékek helyesen renderelődnek-e

---

## Test Scenario 1: Első Nézet (Zero State)

**Kontextus**: User most fejezte be onboarding-ot, még nem vett részt tournamentben

### Várható UX állapot:

**Dashboard megjelenése**:
- [ ] **Radar Chart**: Baseline értékek láthatóak (hétszög forma a skills szerint)
- [ ] **Bar Chart**: Üres vagy "No skill growth yet" üzenet
- [ ] **Skill Cards**: Mind a 7 skill megjelenik tier badge-dzsel
- [ ] **Average Level**: ~58.0 (7 skill átlaga)
- [ ] **Totals**: Tournaments: 0, Assessments: 0

**UX Kérdések**:
1. Azonnal érthető-e mi a radar chart?
2. A tier emojik (🌱 BEGINNER stb.) intuitívak-e?
3. Világos-e hogy miért nincs még "growth"?
4. Motiváló-e a nulla állapot vagy elkedvetlenítő?

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Mi tetszik / mi zavaró?
- Van-e hiányzó információ?
- Túl sok / túl kevés a vizualizáció?
```

---

## Test Scenario 2: Első Tournament Után

**Kontextus**: User elvégzett egy Speed Tournament-et és helyezést ért el

### Setup lépések:

1. **Admin fiókkal** hozz létre egy Speed Tournament-et
2. Enroll `ux.test.player@f1rstteam.hu`-t
3. Generálj session-öket
4. Indítsd el a tournament-et
5. Rögzíts eredményeket (pl. 3rd place)
6. Distribute rewards

**Várható skill deltas** (ha 10 raw points speed reward):
- Speed: +1.25 (10 × 0.125 multiplier)
- Speed új értéke: 66.25 (65 baseline + 1.25 delta)

### Várható UX állapot:

**Dashboard változások**:
- [ ] **Radar Chart**: Speed érték kinőtt a baseline-ból
- [ ] **Bar Chart**: Megjelent Speed bar kék színnel (tournament)
- [ ] **Speed Skill Card**:
  - Current: 66.25
  - Delta: +1.25 (zöld szín)
  - Tier: DEVELOPING (maradt)
  - Tournament count: 1
- [ ] **Average Level**: ~58.2 (minimális emelkedés)
- [ ] **Totals**: Tournaments: 1

**UX Kérdések**:
1. Észrevehető-e a skill növekedés? (1.25 pont kicsi változás)
2. Motiváló-e látni a +1.25 deltát?
3. A bar chart segít-e megérteni a forrást (tournament vs assessment)?
4. Világos-e hogy miért csak a Speed változott?
5. Látszik-e hogy még mennyi "növekedési potenciál" van? (+13.75 maradt a 15-ös cap-ig)

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Észrevetted-e rögtön a változást?
- A +1.25 érték motiváló vagy túl kicsi?
- Igény van-e progress bar-ra a cap felé? (pl. "3.75 / 15.0 tournament points")
```

---

## Test Scenario 3: Több Tournament Után (Growth Tracking)

**Kontextus**: User 3 különböző tournament-en vett részt

### Setup:
1. **Speed Tournament**: 3rd place → +1.25 speed
2. **Stamina Tournament**: 2nd place → +2.0 stamina
3. **Hybrid Tournament** (multi-skill): 4th place → +0.5 speed, +0.5 ball_control, +0.3 passing

**Várható összesített deltas**:
- Speed: +1.75 (1.25 + 0.5)
- Stamina: +2.0
- Ball Control: +0.5
- Passing: +0.3

### Várható UX állapot:

**Dashboard**:
- [ ] **Radar Chart**: 4 skill "kinőtt", aszimmetrikus hétszög forma
- [ ] **Bar Chart**: 4 skill látszik sorrendben (stamina, speed, ball_control, passing)
- [ ] **Skill Cards**: 4 skill mutat növekedést, 3 maradt baseline-on
- [ ] **Average Level**: ~59.1
- [ ] **Totals**: Tournaments: 3

**UX Kérdések**:
1. A radar chart aszimmetrikus formája segít-e megérteni a profilt?
2. Látszik-e trend? (pl. "gyorsasági specialista vagyok")
3. A bar chart sorrendje (legnagyobb delta elől) logikus-e?
4. Van-e túl sok információ egyszerre?
5. Igény van-e filter-re? (pl. "csak tournament deltas" látsszon)

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Melyik chart a leghasznosabb?
- Melyik chart redundáns / zavaró?
- Hiányzik valami ami segítene a döntéshozatalban? (pl. "melyik tournamentre menjek legközelebb?")
```

---

## Test Scenario 4: Assessment Hozzáadása

**Kontextus**: Instructor skill assessment-et végez a játékoson

### Setup:
1. **Admin/Instructor fiókkal** hozz létre manual assessment-et
2. Értékeld a következő skilleket:
   - Ball Control: 8.0 raw → +1.6 (8.0 × 0.20)
   - Passing: 7.5 raw → +1.5
   - Defending: 6.0 raw → +1.2

### Várható UX állapot:

**Dashboard változások**:
- [ ] **Bar Chart**: 3 új skill megjelenik ZÖLD assessment bar-ral (tournament kék, assessment zöld)
- [ ] **Skill Cards - Ball Control**:
  - Current: 62.1 (60 baseline + 0.5 tournament + 1.6 assessment)
  - Tournament: +0.5 (1 tournament)
  - Assessment: +1.6 (1 assessment)
  - Breakdown látható az expander-ben
- [ ] **Totals**: Tournaments: 3, Assessments: 1

**UX Kérdések**:
1. Egyértelmű-e a különbség tournament (kék) vs assessment (zöld) között?
2. A stacked bar chart segít-e megérteni hogy **2 forrásból** jön a növekedés?
3. Az assessment multiplier (0.20 vs 0.125) észrevehető-e? Logikus-e hogy nagyobb?
4. A detailed breakdown (expander) használható-e vagy túl részletes?

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Világos-e hogy assessment > tournament súlyú?
- Igény van-e külön "assessment history" nézetre?
- Segít-e a color coding (kék vs zöld) vagy zavaró?
```

---

## Test Scenario 5: Cap Közelítése

**Kontextus**: User sokat gyakorolta a Speed-et, közel a 15-ös tournament cap-hez

### Setup:
Vegyél részt 10+ Speed Tournament-en amíg speed tournament_delta ~14.5

### Várható UX állapot:

**Dashboard**:
- [ ] **Speed Skill Card**:
  - Current: ~79.5 (65 + 14.5)
  - Tournament: +14.5 / 15.0 (cap közel!)
  - Tier: INTERMEDIATE (70-84)
  - Breakdown: "Tournament remaining: +0.5"
- [ ] **Growth Potential**: Figyelmeztetés hogy közel a cap?

**UX Kérdések**:
1. Látszik-e előre hogy közel a cap?
2. Igény van-e progress bar-ra? (pl. "14.5 / 15.0 ███████████░ 97%")
3. Van-e UI feedback hogy "már nem sok maradt ebből a skill-ből tournamentben"?
4. Világos-e hogy assessment-tel még lehet növelni? (+10 assessment cap külön)

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Mikor vesszük észre hogy elérjük a cap-et?
- Igény van-e előre látható figyelmeztetésre?
- Segítene-e egy "recommended action" (pl. "Try assessments for more Speed growth")
```

---

## Test Scenario 6: Tier Upgrade (DEVELOPING → INTERMEDIATE)

**Kontextus**: Skill átlépi a 70-es küszöböt

### Setup:
User speed skillé elér 70.0-t (tier change: DEVELOPING → INTERMEDIATE)

### Várható UX állapot:

**Dashboard változások**:
- [ ] **Tier Badge**: 📈 → ⚡ (emoji változik)
- [ ] **Color**: Blue → Orange
- [ ] **Radar Chart**: Skill vizuálisan "kilóg" a többiből

**UX Kérdések**:
1. Észrevehető-e a tier upgrade?
2. Van-e "congratulations" vagy celebration moment?
3. Motiváló-e látni a következő tier-t? (INTERMEDIATE → ADVANCED at 85)
4. Segítene-e progress bar tier-ek között? (pl. "70/85 to ADVANCED")

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Érdemes-e gamification? (pl. badge unlock notification)
- A tier emoji-k elég motiválóak? (🌱→📈→⚡→🔥→💎)
- Igény van-e tier history timeline-ra?
```

---

## Test Scenario 7: Comparative View (Jövőbeli Feature)

**Kontextus**: User szeretné látni hogy áll más játékosokhoz képest

### UX Brainstorming Kérdések:

1. **Cohort Comparison**:
   - Van-e értelme "same specialization" átlag?
   - Pl. "Your Speed: 79.5 | Cohort avg: 72.3"

2. **Skill Balance Indicator**:
   - Segítene-e egy "unbalanced profile" warning?
   - Pl. "Your speed is 30 points higher than defending - consider balanced training"

3. **Tournament Recommendation**:
   - Igény van-e smart suggestion-re?
   - Pl. "Based on your profile, try Hybrid tournaments for balanced growth"

4. **Historical Trend**:
   - Segítene-e line chart "skill over time"?
   - Pl. 6 hónapos speed growth curve

**Jegyzet hely**:
```
[IDE JEGYZETELJ!]
- Melyik jövőbeli feature lenne a leghasznosabb?
- Van-e túl sok információ veszélye?
- Mi a minimális hasznos vizualizáció vs "nice to have"?
```

---

## UX Összegzés Sablon

Minden teszt scenario után töltsd ki:

### Mi működik jól? ✅
```
1. [pl. Radar chart intuitív a skill profil megértéséhez]
2. ...
```

### Mi zavaró / nem egyértelmű? ⚠️
```
1. [pl. Bar chart színkódolás nem egyértelmű első ránézésre]
2. ...
```

### Hiányzó feature-ök / információk? 💡
```
1. [pl. Progress bar a cap-ekhez]
2. ...
```

### Iterációs ötletek? 🔄
```
1. [pl. Tier upgrade animation hozzáadása]
2. ...
```

---

## Következő Lépések (UX Tesztek Után)

1. **UX jegyzet review** → Prioritizált feature lista
2. **Dashboard iteráció** alapján a tanulságokra
3. **Második UX test kör** a változásokkal
4. **Csak ezután**: Végleges dokumentáció

**NE DOKUMENTÁLJ MOST** - Várj a valós használati tapasztalatokra!
