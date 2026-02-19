# Streamlit UI Átstrukturálás - Admin-Grade UX

**Dátum**: 2026-01-27
**Verzió**: UX Refactor v1
**Státusz**: COMPLETE - Kipróbálásra kész

---

## 🎯 Átstrukturálás Célja

A korábbi "demo logika" helyett admin mentális modellt követő UX kialakítása:
- **Logikai ütközések megszüntetése**: Player Count ÉS User Selection párhuzamos megjelenése
- **Conditional UI**: VAGY Random Pool VAGY Specific Users, soha nem egyszerre
- **Simplified Auth**: Minimalizált bejelentkezés (production-ben admin session lesz)
- **Instructor Logic**: Csak Specific Users módban elérhető

---

## ✅ Végrehajtott Változások

### 1. **Auth Screen Egyszerűsítése**
**Előtte**: Expander-ben elhelyezett auth screen, mindig látható
**Utána**: Ha nincs token → egyszerű bejelentkezési blokk megjelenik → után eltűnik

```python
# Simplified auth - csak akkor jelenik meg, ha nincs token
if "token" not in st.session_state:
    st.info("💡 **Quick Setup**: Enter your admin token or use default credentials")
    # ... login UI ...
    st.stop()  # Ne menjen tovább, amíg nincs auth
```

**Előny**: Admin-szerű élmény, nem "demo app" feeling

---

### 2. **Participant Mode Radio Button**
**Előtte**: Player Count slider mindig látható + User Selection expander külön
**Utána**: Radio button választás:
- 🎲 **Random Pool (Quick Test)** → Player Count slider megjelenik
- 👥 **Specific Users (Real Impact Analysis)** → User Selection blokk megjelenik

```python
participant_mode = st.radio(
    "Choose how to select participants:",
    options=["random_pool", "specific_users"],
    format_func=lambda x: "🎲 Random Pool (Quick Test)" if x == "random_pool" else "👥 Specific Users (Real Impact Analysis)",
    horizontal=False
)
```

**Előny**: Világos döntési pont, nem ütközik logikailag

---

### 3. **Conditional Player Count vs User Selection**

**Random Pool módban**:
```python
if participant_mode == "random_pool":
    st.markdown("#### Player Count")
    player_count = st.slider("Number of players", min_value=4, max_value=16, value=8)
    st.info(f"✅ Will use {player_count} random users from test pool")
```

**Specific Users módban**:
```python
else:  # specific_users
    st.markdown("#### Select Users")
    # Search + User list with checkboxes
    # ...
    if selected_user_ids:
        st.success(f"✅ Selected: {len(selected_user_ids)} users")
        player_count = len(selected_user_ids)  # Auto-override
```

**Előny**: Soha nem jelenik meg mindkettő egyszerre → logikai tisztaság

---

### 4. **User Selection: Expander → Dedikált Blokk**

**Előtte**: Expander-ben elrejtve, "Phase 2 - Admin-Grade" címkével
**Utána**: Ha Specific Users mode választva → teljes szélességű dedikált blokk

**Fejlesztések**:
- Search input prominens helyen
- User lista 2 oszlopos layoutban (checkbox + skill preview)
- Skill preview inline formázással: `Passing: 65 | Shooting: 58 | ...`
- License type badge megjelenítése
- Selection summary (selected count) kiemelt helyen

```python
# Checkbox with user info
col_check, col_info = st.columns([3, 1])
with col_check:
    is_selected = st.checkbox(f"**{user['name']}** ({user['email']})", key=f"user_{user['id']}")
with col_info:
    st.caption(skill_text)
    if user.get("license_type"):
        st.caption(f"📋 {user['license_type']}")
```

**Előny**: Modal-szerű megjelenés, nem "mellékszál" expander

---

### 5. **Instructor Assignment: Csak Specific Users Módban**

**Előtte**: Expander-ben mindig elérhető, függetlenül a participant mode-tól
**Utána**: Csak akkor jelenik meg, ha `participant_mode == "specific_users"`

```python
if participant_mode == "specific_users":
    # ... user selection ...

    st.markdown("#### Instructor Assignment (Optional)")
    assign_instructors = st.checkbox("Assign specific instructors to this test", value=False)

    if assign_instructors:
        # ... instructor list ...
```

**Előny**: Logikailag helyes (random pool esetén nincs értelme instructor assignment-nek)

---

### 6. **Validation Logic Frissítése**

**Új validációs szabályok**:
```python
validation_errors = []

if not skills_to_test:
    validation_errors.append("❌ Please select at least 1 skill")

if len(skills_to_test) > 4:
    validation_errors.append("❌ Maximum 4 skills allowed")

if participant_mode == "specific_users" and len(selected_user_ids) < 4:
    validation_errors.append("❌ Please select at least 4 users for testing")

if participant_mode == "specific_users" and len(selected_user_ids) > 16:
    validation_errors.append("❌ Maximum 16 users allowed")

# Run button disabled if errors exist
run_button_disabled = len(validation_errors) > 0
```

**Előny**: Participant mode-specifikus validáció, Run button disable/enable dinamikusan

---

### 7. **Progress Screen Frissítése**

**Új config display**:
```python
with col1:
    st.write(f"**Tournament Type:** {config['tournament_type'].upper()}")
    st.write(f"**Player Count:** {config['player_count']}")
    if config.get('user_ids'):
        st.write(f"**Mode:** Specific Users ({len(config['user_ids'])} selected)")
    else:
        st.write(f"**Mode:** Random Pool")
```

**Előny**: Admin látja, melyik módot választotta (Random vs Specific)

---

## 📊 UX Flow Összehasonlítás

### **Régi Flow (Demo Logic)**
```
1. Auth Expander (mindig látható)
2. Tournament Config
3. Player Count Slider (mindig látható)
4. Skills Multiselect
5. Advanced Options (collapsed)
6. User Selection Expander (collapsed, külön opció)
   └─ User checkboxes
   └─ Instructor checkboxes (mindig)
7. Run Button
```
**Probléma**: Player Count + User Selection ütközik logikailag

---

### **Új Flow (Admin-Grade)**
```
1. Auth (csak ha nincs token, utána eltűnik)
   ↓
2. 1️⃣ Tournament Configuration
   - Tournament Type dropdown
   - Skills multiselect
   ↓
3. 2️⃣ Participant Selection Mode
   - Radio: Random Pool vs Specific Users
   ↓
   ├─ Ha Random Pool:
   │  └─ Player Count Slider
   │     └─ Info: "Will use X random users"
   │
   └─ Ha Specific Users:
      ├─ Search + User List (checkboxes, skill preview)
      ├─ Selection Summary
      └─ Instructor Assignment (optional checkbox)
         └─ Instructor List (csak ha enabled)
   ↓
4. 3️⃣ Advanced Options (collapsed)
   - Performance Variation
   - Ranking Distribution
   ↓
5. Validation Errors (ha van)
   ↓
6. Run Button (disabled ha van hiba)
```
**Előny**: Döntési fa logika, soha nem ütközik

---

## 🧪 Tesztelési Útmutató

### **Random Pool Mode Teszt**
1. Auth: `admin@lfa.com` / `admin123`
2. Tournament Type: League
3. Skills: Passing, Shooting
4. **Participant Mode: Random Pool**
5. Player Count: 8
6. Run Test
7. **Elvárt**: 8 random user, nincs user_ids paraméter az API hívásban

---

### **Specific Users Mode Teszt**
1. Auth: `admin@lfa.com` / `admin123`
2. Tournament Type: League
3. Skills: Passing, Dribbling
4. **Participant Mode: Specific Users**
5. Search: (üres, all users látszik)
6. Select: 4-8 user checkboxolva
7. Instructor Assignment: (optional) 1-2 instructor checkboxolva
8. Run Test
9. **Elvárt**: API hívás `user_ids` és `instructor_ids` paraméterrel

---

## 🔍 Változások Lokációja (Kód)

| Funkció | Fájl | Sor | Változás Típusa |
|---------|------|-----|----------------|
| Auth simplification | `streamlit_sandbox.py` | 125-143 | Modified |
| Participant mode radio | `streamlit_sandbox.py` | 174-180 | New |
| Conditional player count | `streamlit_sandbox.py` | 188-198 | New |
| Conditional user selection | `streamlit_sandbox.py` | 200-258 | Modified |
| Conditional instructor | `streamlit_sandbox.py` | 260-301 | Modified |
| Validation logic | `streamlit_sandbox.py` | 325-343 | Modified |
| Progress config display | `streamlit_sandbox.py` | 377-390 | Modified |

---

## ✅ Tesztelési Checklist

- [x] Streamlit UI elindult: http://localhost:8502
- [x] Backend API elérhető: http://localhost:8000
- [x] Auth működik (admin@lfa.com / admin123)
- [x] Participant mode radio megjelenik
- [x] Random Pool mode → Player Count slider látszik
- [x] Specific Users mode → User Selection blokk látszik
- [x] Instructor Assignment csak Specific Users módban
- [x] Validation errors megfelelően jelennek meg
- [x] Run button disable/enable dinamikus

---

## 🚀 Következő Lépések (Admin Döntésre Vár)

1. **Kipróbálás**: http://localhost:8502
2. **Feedback**: UX flow helyes-e admin szemmel?
3. **Döntés**:
   - ✅ Elfogadva → integráció admin dashboard-ba
   - 🔄 Finomhangolás → konkrét visszajelzés alapján
   - ❌ Visszatérés korábbi verzióhoz

---

**Status**: ✅ READY FOR REVIEW

Streamlit UI fut: http://localhost:8502
Backend API fut: http://localhost:8000
Awaiting admin feedback...
