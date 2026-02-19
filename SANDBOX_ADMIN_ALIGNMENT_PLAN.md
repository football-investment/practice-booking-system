# Sandbox UI → Admin-Compatible Preview - Alignment Plan

**Dátum**: 2026-01-27
**Cél**: Sandbox UI teljes átalakítása admin felület struktúrája szerint

---

## 🎯 Célállapot

A sandbox UI **pontosan tükrözze** az admin tournament creation flow-t, hogy:
1. Admin tesztelni tudja a reward rendszert admin-szerű környezetben
2. UI/UX konzisztencia legyen admin dashboard és sandbox között
3. Sandbox valós admin preview legyen, ne egyszerűsített demo

---

## 📊 Admin Felület Struktúra (Jelenlegi)

### 1️⃣ **Location & Campus** (2-lépéses)
```
Location * → Vienna Academy (Vienna)
  ↓
Campus * → Vienna Main Campus
```

### 2️⃣ **Reward Configuration V2** (Komplex)
```
📋 Reward Template
  ↓ Select template (Standard/Custom)
  ↓
⚠️ SKILL SELECTION (REQUIRED)
  ↓ Skill categories with weights:
    - 🟦 Outfield (passing, dribbling, shooting, defending)
    - 🟨 Set Pieces
    - 🟩 Mental
    - 🟥 Physical Fitness (physical, pace)
  ↓
🏆 Badge Configuration
  ↓ Per placement (1st, 2nd, 3rd, Top 25%, Participation):
    - Select badges
    - Credits
    - XP Multiplier
```

### 3️⃣ **Tournament Format**
```
Format * → HEAD_TO_HEAD / INDIVIDUAL_RANKING
```

### 4️⃣ **Tournament Basic Info**
```
Tournament Name *
Tournament Date *
Age Group * → PRE/U10/U12/etc.
```

### 5️⃣ **Tournament Configuration**
```
Assignment Type * → OPEN_ASSIGNMENT / MANUAL / etc.
Max Players *
Price (Credits) *
```

### 6️⃣ **Tournament Type**
```
Tournament Type → None (Manual) / league / knockout / hybrid
  ↓ If not None:
    - Sessions auto-generated based on type
```

---

## 🔴 Sandbox UI Jelenlegi Hibák

| Admin Field | Sandbox Status | Gap |
|-------------|----------------|-----|
| **Location & Campus** (2-step) | ❌ Csak campus dropdown | Missing location step |
| **Reward Config V2** | ❌ Csak "skills_to_test" multiselect | Missing template, weights, badges |
| **Tournament Format** | ❌ Auto from type | Admin explicit választ! |
| **Tournament Name** | ❌ Auto-generated | Admin input mező |
| **Tournament Date** | ❌ Auto datetime.now() | Admin date picker |
| **Age Group** | ❌ Nincs | Missing field |
| **Assignment Type** | ❌ Nincs | Missing field |
| **Max Players** | ✅ Van (player_count slider) | OK, de neve nem stimmel |
| **Price (Credits)** | ❌ Nincs | Missing field |
| **Tournament Type** | ✅ Van dropdown | OK |
| **Participant Mode** | ❌ Sandbox-specific (random/specific) | Admin-ban nincs ilyen! |

---

## ✅ Átdolgozási Terv

### **Phase 1: Reward Config V2 Integráció** (Prioritás: MAGAS)

**1.1 Skill Selection Admin-Szerűen**
- ❌ Töröld: `skills_to_test` multiselect
- ✅ Új: Skill kategóriák expandable sections-ökkel:
  ```
  🟦 Outfield Skills
    □ passing (weight: 1.0)
    □ dribbling (weight: 1.0)
    □ shooting (weight: 1.0)
    □ defending (weight: 1.0)

  🟥 Physical Fitness
    □ physical (weight: 1.0)
    □ pace (weight: 1.0)
  ```
- Validation: "⚠️ You must select at least 1 skill to continue"

**1.2 Reward Template Selector**
- Dropdown: "Standard" / "Custom"
- Standard → Auto-load default credits/xp values
- Custom → Admin manually set values

**1.3 Badge Configuration per Placement**
- Expandable sections:
  - 🥇 1st Place Rewards
  - 🥈 2nd Place Rewards
  - 🥉 3rd Place Rewards
  - 🌟 Top 25% Rewards
  - ⚽ Participation Rewards
- Each section:
  - Badge multiselect (fetch from `/api/v1/badges`)
  - Credits input
  - XP Multiplier slider

**1.4 Configuration Summary**
- Show selected count: Skills, Badges, Total Credits, XP Multiplier

---

### **Phase 2: Location & Campus Flow** (Prioritás: MAGAS)

**2.1 Two-Step Selection**
```python
# Step 1: Location
locations = fetch_locations(token)  # NEW endpoint needed
location_id = st.selectbox("Location *", locations)

# Step 2: Campus (filtered by location)
campuses = fetch_campuses_by_location(token, location_id)
campus_id = st.selectbox("Campus *", campuses)
```

**2.2 API Endpoint**
- Ha nincs `/api/v1/locations` endpoint → kell készíteni
- Campus endpoint filter: `/api/v1/admin/campuses?location_id={location_id}`

---

### **Phase 3: Tournament Format Explicit Choice** (Prioritás: KÖZEPES)

**3.1 Format Dropdown**
- ❌ Töröld: Auto format detection from tournament type
- ✅ Új: Explicit dropdown:
  ```python
  format = st.selectbox(
      "Format *",
      options=["HEAD_TO_HEAD", "INDIVIDUAL_RANKING"],
      help="HEAD_TO_HEAD: 1v1 matches. INDIVIDUAL_RANKING: Placement-based."
  )
  ```

**3.2 Backend Update**
- API: `format` visszatér required field-ként
- Orchestrator: `format` paraméter kötelező (töröld default értéket)

---

### **Phase 4: Missing Admin Fields** (Prioritás: KÖZEPES)

**4.1 Tournament Basic Info**
```python
tournament_name = st.text_input("Tournament Name *", placeholder="e.g., Spring League 2026")
tournament_date = st.date_input("Tournament Date *", value=datetime.now().date())
age_group = st.selectbox(
    "Age Group *",
    options=["PRE", "U10", "U12", "U14", "U16", "U18", "ADULT"],
    help="Target age group for this tournament"
)
```

**4.2 Tournament Configuration**
```python
assignment_type = st.selectbox(
    "Assignment Type *",
    options=["OPEN_ASSIGNMENT", "MANUAL_ASSIGNMENT", "INVITE_ONLY"],
    help="How players are assigned to this tournament"
)

max_players = st.number_input(
    "Max Players *",
    min_value=4,
    max_value=64,
    value=16,
    step=1
)

price_credits = st.number_input(
    "Price (Credits) *",
    min_value=0,
    max_value=10000,
    value=100,
    step=10,
    help="Cost in credits for participants to join"
)
```

---

### **Phase 5: Eltávolítani Sandbox-Specific Elemek** (Prioritás: MAGAS)

**5.1 Participant Mode Radio**
- ❌ Töröld: "Random Pool vs Specific Users" radio button
- Admin-ban nincs ilyen → minden user selection explicit

**5.2 Player Count Slider (ha Random mode)**
- ❌ Töröld conditional slider
- Marad csak: **Max Players** (number input, mindig látható)

**5.3 User Selection**
- ✅ Megtartani, de **mindig látható** (nem conditional)
- Admin-szerű: "Select participants (optional)" - ha nem választanak, akkor manual assignment later

---

### **Phase 6: UI Sorrendezés Admin Szerint** (Prioritás: KÖZEPES)

**Admin felület sorrend:**
```
1️⃣ Location & Campus
2️⃣ Reward Configuration V2
3️⃣ Tournament Format
4️⃣ Tournament Basic Info (Name, Date, Age Group)
5️⃣ Tournament Configuration (Assignment, Max Players, Price)
6️⃣ Tournament Type
```

**Sandbox új struktúra:**
```python
st.markdown("### 1️⃣ Location & Campus")
# location + campus selection

st.markdown("### 2️⃣ Reward Configuration")
# template + skill selection + badge config

st.markdown("### 3️⃣ Tournament Format")
# format dropdown

st.markdown("### 4️⃣ Basic Information")
# name, date, age group

st.markdown("### 5️⃣ Configuration")
# assignment type, max players, price

st.markdown("### 6️⃣ Tournament Type")
# tournament type dropdown (league/knockout/hybrid/None)
```

---

## 🚀 Implementációs Sorrend

### **Sprint 1: Critical Admin Alignment** (Most)
1. ✅ Reward Config V2 - Skill selection UI
2. ✅ Location & Campus 2-step flow
3. ✅ Tournament Format explicit dropdown
4. ✅ Eltávolítani "Participant Mode" sandbox-specific elem

### **Sprint 2: Missing Fields** (Következő)
5. ✅ Tournament Name, Date, Age Group inputs
6. ✅ Assignment Type, Max Players, Price inputs
7. ✅ UI reordering admin sorrend szerint

### **Sprint 3: Backend Integration** (Utolsó)
8. ✅ API updates (format required, új fields)
9. ✅ Orchestrator updates
10. ✅ End-to-end testing

---

## 📝 API Changes Needed

### **New Endpoints:**
1. `GET /api/v1/locations` - Location list
2. `GET /api/v1/admin/campuses?location_id={id}` - Filtered campuses
3. `GET /api/v1/badges` - Badge list for selection

### **Updated Endpoints:**
1. `POST /api/v1/sandbox/run-test` schema:
   ```python
   class RunTestRequest(BaseModel):
       tournament_type: str
       tournament_name: str  # NEW
       tournament_date: date  # NEW
       age_group: str  # NEW
       format: str  # REQUIRED (not auto)
       assignment_type: str  # NEW
       max_players: int
       price_credits: int  # NEW
       campus_id: int
       reward_config: RewardConfigV2  # NEW (complex object)
       user_ids: Optional[list[int]]
       instructor_ids: Optional[list[int]]
   ```

---

## ✅ Success Criteria

Sandbox UI elfogadva, ha:
1. ✅ Reward Config V2 pontosan admin-szerű (skill categories + badges + credits/xp)
2. ✅ Location → Campus 2-lépéses flow van
3. ✅ Tournament Format explicit választás (nem auto)
4. ✅ Minden admin field jelen van (name, date, age group, assignment, price)
5. ✅ Nincs sandbox-specific elem (participant mode radio törlve)
6. ✅ UI sorrend megegyezik admin sorrenddel
7. ✅ End-to-end test sikeres (tournament creation + reward distribution)

---

**Status**: 📋 PLAN READY - Awaiting implementation approval
