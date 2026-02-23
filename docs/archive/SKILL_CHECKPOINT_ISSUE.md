# Skill Selection Not Persisting - DIAGNOSIS 🔍

**Dátum**: 2026-01-28
**Probléma**: User kiválasztott 16 skill-t, de csak 8 lett elmentve
**Státusz**: 🟡 INVESTIGATING

---

## 🔴 Tünetek

1. User kiv álaszt 16 skill-t a UI-ban
2. Megnyomja a "Create Sandbox Tournament" gombot
3. Csak 8 skill lett tesztelve a tournament-ben

### Database Evidence:
```sql
SELECT id, reward_config->'skill_mappings' FROM semesters WHERE id = 137;
```

**Eredmény**: Csak 8 skill volt mentve:
- ball_control
- crossing
- passing
- positioning_off
- tactical_awareness
- acceleration
- sprint_speed
- agility

**Expected**: 16 skill

---

## 🔍 Root Cause Analysis

### Theory 1: Streamlit Checkbox State Loss ❌
**Hipotézis**: A checkboxes elveszítik a state-et amikor `st.rerun()` fut.

**Teszt**:
```python
# streamlit_sandbox_v3_admin_aligned.py:213
is_selected = st.checkbox(
    skill.capitalize(),
    key=f"skill_{skill}",  # <-- Key van, tehát megőrzi a state-et
    value=False
)
```

**Eredmény**: A `key=` paraméter **kellene** hogy megőrizze a state-et.

### Theory 2: selected_skills Lista Újra Épül ✅ (LIKELY)
**Hipotézis**: Amikor `st.rerun()` fut (button click után), a `selected_skills` lista **üres lesz**, mert a loop újra fut MIELŐTT a checkboxes újratöltődnének.

**Kód flow**:
```python
# Lines 205-219
selected_skills = []  # <-- Új lista minden rerun-nál

for category, skills in SKILL_CATEGORIES.items():
    for skill in skills:
        is_selected = st.checkbox(...)  # <-- Ez még FALSE az első render-nél?
        if is_selected:
            selected_skills.append(skill)
```

**Probléma**: A `st.rerun()` után a checkpoint state-ek még nincsenek load-olva amikor a lista épül!

---

## 🛠️ Javasolt Megoldás

### Option 1: Save Config BEFORE Button Click
**Streamlit Best Practice**: Use `st.form()` to batch all inputs together.

```python
with st.form("tournament_config_form"):
    # All checkboxes and inputs here

    submit = st.form_submit_button("Create Sandbox Tournament")

    if submit:
        # NOW selected_skills will have all values
        tournament_config = {...}
```

### Option 2: Store Skills in session_state
```python
if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = []

# On checkbox change, update session state
if is_selected:
    if skill not in st.session_state.selected_skills:
        st.session_state.selected_skills.append(skill)
else:
    if skill in st.session_state.selected_skills:
        st.session_state.selected_skills.remove(skill)

# Use session_state.selected_skills for config
```

---

## 📊 Next Steps

1. **Implement st.form()** wrapper around configuration screen
2. Test with 16 skills again
3. Verify all 16 skills are saved to database

---

**Status**: 🟡 FIX IN PROGRESS
