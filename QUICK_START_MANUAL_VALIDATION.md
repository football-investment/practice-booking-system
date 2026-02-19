# 🚀 Manuális Validáció - Gyors Kezdés

## ⚡ 5 Perces Gyorsindító

### 1. Streamlit Indítás
```bash
cd practice_booking_system
source venv/bin/activate
streamlit run streamlit_app.py --server.port 8501
```

### 2. Browser DevTools
- Chrome/Firefox: `F12` vagy `Cmd+Option+I`
- **Elements** tab

### 3. Első Tournament
- Navigálj: `http://localhost:8501`
- Keress tournament ID: **466+** (Playwright által létrehozott)
- Vagy keress "PLAYWRIGHT" szöveggel

---

## 📸 Első 3 Tournament (30 perc)

### T3: 1 Winner (CRITICAL)
- **Config**: SCORE_BASED + 1 round
- **Győztes**: 1
- ✅ **Csak 1. helyezett kiemelt**
- ❌ 2-8. helyezett NEM kiemelt

### T2: 5 Winners (CRITICAL)
- **Config**: TIME_BASED + 1 round
- **Győztes**: 5
- ✅ **1-5. helyezett kiemelt**
- ❌ 6-8. helyezett NEM kiemelt

### T8: 2 Rounds, 3 Winners (HIGH)
- **Config**: ROUNDS_BASED + 2 rounds
- **Győztes**: 3
- ✅ **1-3. helyezett kiemelt**
- ❌ 4-8. helyezett NEM kiemelt

---

## 🔍 Mit Keress?

### Status Badge
- Hol van? (header/sidebar/body)
- Szöveg: "REWARDS_DISTRIBUTED"?
- CSS class/ID?

### Rankings
- Táblázat vagy lista?
- Medal icons? 🥇🥈🥉
- Győztes kiemelés? (color/border/icon)

### Rewards
- Van külön szekció?
- Credit/XP/Skill rewards?
- Hány címzett?

### Winner Highlights
- Háttérszín?
- Border?
- Icon? 🏆
- "WINNER" badge?

---

## 📝 Screenshot Elnevezés

```
t3_status.png
t3_rankings_1_winner.png
t3_rewards.png
t2_rankings_5_winners.png
t8_multi_round.png
```

---

## 📋 Következő Lépés

**Dokumentáld**: `UI_STRUCTURE_DOCUMENTATION.md`
- HTML snippets
- CSS selectors
- Screenshot-ok
- data-testid javaslatok

**Teljes terv**: [FRONTEND_UI_VALIDATION_BACKLOG.md](FRONTEND_UI_VALIDATION_BACKLOG.md)
