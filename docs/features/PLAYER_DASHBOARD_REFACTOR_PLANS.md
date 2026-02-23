# Player Dashboard Refactor - Two Design Proposals

## Problem Statement

Current player dashboard is too long and contains too much information on a single page:
- Player Information
- Skill Profile (with all 29 skills expanded)
- Tournament Achievements (badges)
- Training Programs
- Schedule
- Tournament Enrollments
- Goals & Motivation

**User needs to scroll excessively to find information.**

## Solution: Multi-Page Navigation

Split dashboard into focused pages with clear navigation.

---

## 🎨 PROPOSAL 1: Sidebar Navigation (Vertical Menu)

### Structure

```
┌─────────────────────────────────────────────────┐
│  LFA Player Dashboard - Kylian Mbappé          │
├───────────┬─────────────────────────────────────┤
│           │                                     │
│  📊 Home  │   MAIN CONTENT AREA                 │
│           │                                     │
│  ⚽ Skills │   (Changes based on selected       │
│           │    page from sidebar)               │
│  🏆 Events│                                     │
│           │                                     │
│  📅 Sched │                                     │
│           │                                     │
│  👤 Profile│                                    │
│           │                                     │
└───────────┴─────────────────────────────────────┘
```

### Pages

#### 1. 📊 Home / Overview
**Purpose**: Quick dashboard snapshot
**Content**:
- Player card (name, age, position, category)
- Credits & XP summary
- Latest achievements (3-5 most recent badges)
- Upcoming sessions (next 3-5)
- Quick stats (average skill level, total tournaments)

**Why**: Landing page with most important info at a glance

---

#### 2. ⚽ Skills & Progression
**Purpose**: Deep dive into skill development
**Content**:
- Skill profile header (average level, tournaments, assessments)
- Skills organized by category (collapsible sections)
- Skill history chart (optional - show progression over time)
- Tournament contributions highlighted

**Why**: Dedicated space for detailed skill analysis without cluttering main page

---

#### 3. 🏆 Tournaments & Events
**Purpose**: Tournament history and enrollments
**Content**:
- Active tournament enrollments
- Tournament history (past results, placements)
- Badge showcase (all earned badges)
- Tournament statistics (win rate, best finishes)

**Why**: All tournament-related info in one place

---

#### 4. 📅 Schedule
**Purpose**: Training and match calendar
**Content**:
- Calendar view or list view
- Upcoming sessions (all enrollments)
- Past sessions (attendance history)
- Check-in status

**Why**: Focused view for time management

---

#### 5. 👤 Profile & Settings
**Purpose**: Personal information and preferences
**Content**:
- Goals & Motivation
- Contact information
- License details
- Account settings

**Why**: Profile management in dedicated space

---

### Navigation Implementation

**File**: `streamlit_app/components/player_dashboard.py`

```python
# Sidebar navigation
st.sidebar.title("🎯 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📊 Home", "⚽ Skills", "🏆 Tournaments", "📅 Schedule", "👤 Profile"]
)

if page == "📊 Home":
    show_home_page()
elif page == "⚽ Skills":
    show_skills_page()
elif page == "🏆 Tournaments":
    show_tournaments_page()
elif page == "📅 Schedule":
    show_schedule_page()
elif page == "👤 Profile":
    show_profile_page()
```

### Pros
✅ Clear, always-visible navigation
✅ Familiar pattern (like Gmail, Notion)
✅ Easy to add more pages later
✅ Streamlit native component (st.sidebar)

### Cons
❌ Takes up horizontal space
❌ Sidebar might be too narrow on mobile
❌ Requires refactoring all dashboard code into separate functions

---

## 🎨 PROPOSAL 2: Tab Navigation (Horizontal Tabs)

### Structure

```
┌─────────────────────────────────────────────────┐
│  LFA Player Dashboard - Kylian Mbappé          │
├─────────────────────────────────────────────────┤
│  📊 Home | ⚽ Skills | 🏆 Events | 📅 Schedule | 👤 Profile │
├─────────────────────────────────────────────────┤
│                                                 │
│            MAIN CONTENT AREA                    │
│                                                 │
│    (Changes based on selected tab)             │
│                                                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Pages

Same 5 pages as Proposal 1:
1. 📊 Home / Overview
2. ⚽ Skills & Progression
3. 🏆 Tournaments & Events
4. 📅 Schedule
5. 👤 Profile & Settings

### Navigation Implementation

**File**: `streamlit_app/components/player_dashboard.py`

```python
# Tab navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Home",
    "⚽ Skills",
    "🏆 Tournaments",
    "📅 Schedule",
    "👤 Profile"
])

with tab1:
    show_home_page()

with tab2:
    show_skills_page()

with tab3:
    show_tournaments_page()

with tab4:
    show_schedule_page()

with tab5:
    show_profile_page()
```

### Pros
✅ More horizontal space for content
✅ Modern, clean look
✅ Better for mobile (tabs can scroll horizontally)
✅ Streamlit native component (st.tabs)
✅ All tabs visible at once (easier to switch)

### Cons
❌ Tabs might be hidden if too many (need scrolling)
❌ Less familiar pattern for some users
❌ Harder to add "nested" navigation later

---

## 📋 Comparison Table

| Feature | Sidebar (Proposal 1) | Tabs (Proposal 2) |
|---------|---------------------|-------------------|
| **Space Efficiency** | ⭐⭐⭐ (sidebar takes space) | ⭐⭐⭐⭐⭐ (full width) |
| **Mobile Friendly** | ⭐⭐⭐ (sidebar might hide) | ⭐⭐⭐⭐⭐ (tabs scroll) |
| **Scalability** | ⭐⭐⭐⭐⭐ (easy to add pages) | ⭐⭐⭐ (tabs get crowded) |
| **Familiarity** | ⭐⭐⭐⭐⭐ (common pattern) | ⭐⭐⭐⭐ (less common) |
| **Implementation** | ⭐⭐⭐⭐ (standard sidebar) | ⭐⭐⭐⭐⭐ (simpler code) |
| **Visual Appeal** | ⭐⭐⭐⭐ (professional) | ⭐⭐⭐⭐⭐ (modern, clean) |

---

## 🎯 Recommended Approach: **PROPOSAL 2 (Tabs)**

### Reasons:
1. **Better space utilization** - Full width for content, especially important for skill tables
2. **Mobile-friendly** - Tabs work better on smaller screens
3. **Simpler implementation** - Less code refactoring needed
4. **Modern UX** - Matches current web app trends (GitHub, Notion, etc.)
5. **Streamlit native** - Uses `st.tabs()` which is well-supported

### Implementation Plan:

1. **Phase 1**: Create tab structure in `player_dashboard.py`
2. **Phase 2**: Extract each section into separate functions:
   - `show_home_page()`
   - `show_skills_page()`
   - `show_tournaments_page()`
   - `show_schedule_page()`
   - `show_profile_page()`
3. **Phase 3**: Refactor existing code into appropriate functions
4. **Phase 4**: Test and polish each tab

### Estimated Effort:
- **Small refactor**: 2-3 hours (keeping existing UI, just reorganizing)
- **With improvements**: 4-6 hours (adding better layouts, charts, etc.)

---

## 📐 Detailed Tab Content Specs

### Tab 1: 📊 Home
```
┌─────────────────────────────────────────┐
│ 👋 Welcome, Kylian Mbappé               │
│ ⚽ STRIKER | 🎯 AMATEUR | 27 years      │
├─────────────────────────────────────────┤
│ Quick Stats                             │
│ ├─ 💰 20,490 credits                   │
│ ├─ ⭐ 11,049 XP                         │
│ ├─ 📈 Avg Skill: 67.3                  │
│ └─ 🏆 3 tournaments                     │
├─────────────────────────────────────────┤
│ 🎉 Recent Achievements (3 latest)      │
│ [Badge cards...]                        │
├─────────────────────────────────────────┤
│ 📅 Next Sessions (5 upcoming)          │
│ [Session list...]                       │
└─────────────────────────────────────────┘
```

### Tab 2: ⚽ Skills
```
┌─────────────────────────────────────────┐
│ ⚡ Your Skill Profile                   │
│ 📈 67.3 DEVELOPING | 3 tournaments     │
├─────────────────────────────────────────┤
│ 🟦 Outfield (Avg: 61.5/100) [Expand ▼] │
│ 🟨 Set Pieces (Avg: 50.0/100) [▶]     │
│ 🟩 Mental (Avg: 75.0/100) [▶]         │
│ 🟥 Physical (Avg: 75.0/100) [▶]       │
└─────────────────────────────────────────┘
```

### Tab 3: 🏆 Tournaments
```
┌─────────────────────────────────────────┐
│ 🏆 Badge Showcase (9 total)            │
│ [Badge grid...]                         │
├─────────────────────────────────────────┤
│ 📋 Active Enrollments (3)              │
│ [Tournament cards...]                   │
├─────────────────────────────────────────┤
│ 📊 Tournament History                   │
│ [Past results table...]                 │
└─────────────────────────────────────────┘
```

### Tab 4: 📅 Schedule
```
┌─────────────────────────────────────────┐
│ 📅 Your Training Schedule               │
│ [Calendar or list view]                 │
├─────────────────────────────────────────┤
│ 🎯 Upcoming (17 sessions)              │
│ [Detailed session list...]              │
└─────────────────────────────────────────┘
```

### Tab 5: 👤 Profile
```
┌─────────────────────────────────────────┐
│ 👤 Personal Information                 │
│ [Editable fields...]                    │
├─────────────────────────────────────────┤
│ 🎯 Goals & Motivation                   │
│ [Text areas...]                         │
├─────────────────────────────────────────┤
│ ⚙️ Settings                             │
│ [Preferences...]                        │
└─────────────────────────────────────────┘
```

---

## 🚀 Next Steps

1. **User review this document** and choose preferred proposal
2. **Create implementation plan** with detailed file changes
3. **Refactor player_dashboard.py** into modular tab structure
4. **Test thoroughly** on different screen sizes
5. **Deploy and gather feedback**

---

**Created**: 2026-01-26
**Author**: Claude Code
**Status**: PROPOSAL - Awaiting user decision
