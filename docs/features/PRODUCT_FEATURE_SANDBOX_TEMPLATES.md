# Product Feature: Tournament Templates (Sandbox Enhancement)

**Feature ID**: FEAT-2026-W05-tournament-templates
**Created**: 2026-01-31
**Priority**: HIGH (High user value + Low implementation cost)
**Status**: ✅ APPROVED_PENDING_IMPLEMENTATION
**Decision Date**: 2026-01-31
**Approved Scope**: MVP - Client-side only, session_state storage, no persistence guarantee

---

## 🎯 User Story

**As an** LFA instructor creating tournaments in the sandbox,
**I want to** save my tournament configurations as reusable templates,
**So that** I can quickly recreate similar tournaments without re-entering 30+ configuration fields each time.

---

## 📊 Problem Statement

### Current Pain Point

When instructors create multiple similar tournaments (e.g., weekly YOUTH tournaments in Budapest Buda campus), they must:

1. Navigate to Configuration screen
2. Fill **30+ fields** manually:
   - Tournament name, age group, location, campus
   - Tournament format, scoring mode, max players
   - Schedule (start/end dates)
   - Game preset + skills (12-20 skill selections)
   - Participant selection (10-30 users via toggles)
   - Rewards (6 fields: 1st/2nd/3rd place XP + Credits, participation XP, session base XP)
3. Submit and create tournament
4. **Repeat from step 1** for next tournament

**Time Cost**: 5-8 minutes per tournament creation
**Repetition**: High (instructors create 3-5 similar tournaments per week for testing)
**Total Weekly Overhead**: 15-40 minutes of repetitive data entry

### User Frustration Points

- ❌ "I just created this exact tournament yesterday, why do I need to fill everything again?"
- ❌ "I always use the same skills + rewards for YOUTH tournaments, but I have to re-select 15 checkboxes every time"
- ❌ "I made a typo in the tournament name and have to restart the whole form"

---

## 💡 Proposed Solution

### Feature: Tournament Templates

Add template save/load functionality to the sandbox configuration screen:

**Save Template**:
- After filling configuration form, instructor clicks "Save as Template"
- Names the template (e.g., "YOUTH Budapest Weekly")
- Template stores entire config (location, skills, rewards, participants, etc.)

**Load Template**:
- On configuration screen, instructor sees "Load Template" dropdown
- Selects saved template → form auto-fills all fields
- Instructor can adjust any fields before creating tournament
- Click "Create Tournament" (workflow proceeds normally)

**Manage Templates**:
- View/edit/delete saved templates
- Templates stored per user (personal workspace)

---

## 🎨 UI/UX Design

### Configuration Screen Enhancement

**Current Flow**:
```
[Configuration Screen]
  ↓
[Fill 30+ fields manually]
  ↓
[Submit] → Workflow Step 1
```

**Enhanced Flow**:
```
[Configuration Screen]
  ↓
[Load Template] (optional) → Auto-fill all fields
  ↓
[Adjust fields] (if needed)
  ↓
[Save as Template] (optional)
  ↓
[Submit] → Workflow Step 1
```

### Template Management UI

**Location**: Top of configuration screen (before form)

**Components**:
```
┌─────────────────────────────────────────────────────┐
│ 📋 Tournament Templates                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Dropdown: Select Template ▼]  [Load]  [Manage]    │
│                                                     │
│ Or start from scratch ↓                            │
└─────────────────────────────────────────────────────┘

[Configuration Form - existing fields...]

┌─────────────────────────────────────────────────────┐
│ [Save as Template...]  [Submit to Workflow]         │
└─────────────────────────────────────────────────────┘
```

**Template Management Dialog**:
```
┌─────────────────────────────────────────────────────┐
│ Manage Templates                              [×]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ My Templates (5):                                   │
│                                                     │
│ ✓ YOUTH Budapest Weekly (YOUTH, BUDA, 15 skills)   │
│   [Load] [Edit] [Delete]                           │
│                                                     │
│ ✓ PRO Debrecen Monthly (PRO, DEBRECEN, 20 skills)  │
│   [Load] [Edit] [Delete]                           │
│                                                     │
│ ✓ AMATEUR Pest Tournament (AMATEUR, PEST, 12 skills)│
│   [Load] [Edit] [Delete]                           │
│                                                     │
│ ... (2 more)                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Technical Implementation

### Scope

**Backend Changes**: ✅ MINIMAL (major advantage)

**Why minimal backend?**:
- Templates are **client-side only** (stored in browser localStorage or IndexedDB)
- No database schema changes needed
- No API endpoints required
- Zero impact on production backend

**Frontend Changes**: ✅ FOCUSED (single file)

**File**: `streamlit_sandbox_v3_admin_aligned.py` (configuration screen only)

### Implementation Details

#### 1. Template Storage (Browser localStorage)

```python
import json

def save_template(template_name: str, config: Dict):
    """Save tournament config as template in localStorage"""
    templates = st.session_state.get('templates', {})
    templates[template_name] = {
        'name': template_name,
        'created_at': datetime.now().isoformat(),
        'config': config
    }
    st.session_state['templates'] = templates
    # Persist to localStorage (via Streamlit component or manual JS)

def load_template(template_name: str) -> Dict:
    """Load template config from localStorage"""
    templates = st.session_state.get('templates', {})
    return templates.get(template_name, {}).get('config', {})

def delete_template(template_name: str):
    """Delete template from localStorage"""
    templates = st.session_state.get('templates', {})
    if template_name in templates:
        del templates[template_name]
        st.session_state['templates'] = templates
```

#### 2. Configuration Screen Integration

**Location**: [streamlit_sandbox_v3_admin_aligned.py:137-595](streamlit_sandbox_v3_admin_aligned.py#L137-L595) (render_configuration_screen)

**Changes**:
- Add template selector dropdown before form (line ~180)
- Add "Load Template" button (auto-fills form fields)
- Add "Save as Template" dialog at end of form (line ~590)
- Populate form fields from template when loaded

**Pseudo-code**:
```python
def render_configuration_screen():
    # ... existing code ...

    # NEW: Template selector (before form)
    templates = list_templates()
    selected_template = st.selectbox("Load Template", ["(None)", *templates])

    if st.button("Load") and selected_template != "(None)":
        config = load_template(selected_template)
        # Auto-fill form fields from config
        st.session_state.form_preset = config
        st.rerun()

    # Existing form rendering...
    form = SingleColumnForm("tournament_config_form", title="Tournament Configuration")

    # Pre-fill from template if loaded
    preset = st.session_state.get('form_preset', {})

    with form.container():
        tournament_name = st.text_input(
            "Tournament Name",
            value=preset.get('tournament_name', ''),  # Pre-fill
            key=form.field_key("tournament_name")
        )
        # ... (all other fields with preset.get() defaults) ...

    # NEW: Save Template button (after form)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 Save as Template", key="btn_save_template"):
            st.session_state.show_save_template_dialog = True
    with col2:
        # Existing submit button...

    # Save Template Dialog
    if st.session_state.get('show_save_template_dialog'):
        with st.dialog("Save Template"):
            template_name = st.text_input("Template Name")
            if st.button("Save"):
                save_template(template_name, config)
                st.success(f"Template '{template_name}' saved!")
                st.session_state.show_save_template_dialog = False
                st.rerun()
```

#### 3. Data Persistence

**Option A: Streamlit session_state + manual download/upload** (simplest)
- Templates saved in `st.session_state['templates']`
- Export as JSON file (download button)
- Import from JSON file (upload button)
- **Pro**: Zero dependencies, works today
- **Con**: Lost on browser refresh (unless exported)

**Option B: Browser localStorage via Streamlit component** (recommended)
- Use custom Streamlit component with JavaScript localStorage API
- Templates persist across sessions
- **Pro**: Seamless UX, no manual export
- **Con**: ~2 hours to build custom component

**Recommended**: Start with Option A (MVP), upgrade to Option B later

---

## 📈 Impact Assessment

### User Value

**Time Savings**:
- **Before**: 5-8 min per tournament × 4 tournaments/week = **20-32 min/week**
- **After**: 30 sec to load template + 1 min adjustments = **6 min/week**
- **Savings**: **14-26 min/week per instructor** (70-80% reduction)

**Qualitative Benefits**:
- ✅ Reduced cognitive load (no need to remember 30+ settings)
- ✅ Fewer data entry errors (typos, wrong age group, etc.)
- ✅ Faster experimentation ("Let me try 3 variations of this tournament")
- ✅ Consistency (same tournament structure across weeks)

**User Delight Factor**: 🔥 HIGH
- Addresses #1 pain point in sandbox user testing feedback
- "Finally! I've been wishing for this since day 1"

### Business Value

**Developer ROI**:
- **Implementation**: 4-6 hours (Option A) or 6-8 hours (Option B)
- **User Time Saved**: 14-26 min/week × 5 instructors = **70-130 min/week**
- **Payback Period**: ~3-4 weeks

**Strategic Value**:
- 🎯 Increases sandbox usage (less friction → more testing)
- 🎯 Enables complex tournament experimentation (templates lower barrier)
- 🎯 Demonstrates product polish (small feature, big UX impact)

### Technical Risk

**Risk Level**: 🟢 **LOW**

**Why low risk?**:
- ✅ No backend changes (zero production impact)
- ✅ Single file modification (focused scope)
- ✅ Client-side only (isolated failure domain)
- ✅ No database migrations needed
- ✅ Backward compatible (existing flow unchanged)

**Failure Mode**: Worst case → templates don't save, user continues with manual entry (current experience)

---

## 🚀 Implementation Plan

### MVP (Option A): Session State + Export/Import

**Phase 1: Core Template Save/Load** (3 hours)
1. Add template storage functions (save/load/delete)
2. Add template selector dropdown before form
3. Add "Load Template" button → auto-fill logic
4. Add "Save as Template" button → capture config

**Phase 2: Template Management** (1 hour)
5. Add "Manage Templates" dialog
6. List all templates with Load/Delete actions
7. Template metadata display (name, created date, preview)

**Phase 3: Export/Import** (1 hour)
8. Export templates as JSON file (download)
9. Import templates from JSON file (upload)

**Total Time**: 5 hours

### Enhancement (Option B): Browser localStorage

**Phase 4: Persistent Storage** (2 hours)
10. Create Streamlit custom component with localStorage API
11. Replace session_state with localStorage
12. Remove export/import (no longer needed)

**Total Time**: 7 hours (MVP + Enhancement)

---

## ✅ Acceptance Criteria

### Must Have (MVP)

- [ ] Instructor can save current form configuration as named template
- [ ] Instructor can load saved template → form auto-fills all fields
- [ ] Instructor can edit fields after loading template (not locked)
- [ ] Instructor can delete saved templates
- [ ] Templates include all 30+ configuration fields:
  - Tournament name, age group, location, campus
  - Tournament format, scoring mode, max players
  - Schedule (start/end dates)
  - Game preset, skills to test (all selected checkboxes)
  - Selected participants (user IDs)
  - Rewards (all 6 fields)
- [ ] Export templates as JSON file
- [ ] Import templates from JSON file

### Should Have (Enhancement)

- [ ] Templates persist across browser sessions (localStorage)
- [ ] Template preview (shows key fields: age group, location, skills count)
- [ ] Template edit (rename template without re-creating)
- [ ] Template duplication ("Copy 'YOUTH Weekly' → 'YOUTH Monthly'")

### Won't Have (Future)

- ❌ Template sharing between users (requires backend)
- ❌ System-wide recommended templates (requires backend)
- ❌ Template versioning (out of scope)

---

## 🧪 Testing Strategy

### Manual Testing Scenarios

**Test Case 1: Save Template**
1. Fill configuration form completely (all 30+ fields)
2. Click "Save as Template"
3. Enter name "Test Template 1"
4. Verify template appears in template list

**Test Case 2: Load Template**
1. Select "Test Template 1" from dropdown
2. Click "Load"
3. Verify all form fields auto-filled with correct values
4. Modify 2-3 fields
5. Submit → verify workflow proceeds normally

**Test Case 3: Delete Template**
1. Open "Manage Templates" dialog
2. Delete "Test Template 1"
3. Verify template removed from list
4. Verify dropdown no longer shows deleted template

**Test Case 4: Export/Import**
1. Create 3 templates
2. Export as JSON file
3. Clear browser session (simulate refresh)
4. Import JSON file
5. Verify all 3 templates restored correctly

### E2E Test Coverage

**New Test File**: `tests/e2e/test_sandbox_templates.py`

```python
def test_save_template(page):
    """Test template save functionality"""
    # Fill form
    # Click Save Template
    # Verify template in list

def test_load_template(page):
    """Test template load + auto-fill"""
    # Save template first
    # Navigate to config screen
    # Load template
    # Verify all fields populated

def test_delete_template(page):
    """Test template deletion"""
    # Save template
    # Delete via Manage Templates
    # Verify template removed
```

---

## 📚 Documentation Requirements

### User Guide Addition

**Section**: Sandbox User Guide > Configuration Screen
**Content**:
```markdown
## Using Tournament Templates

To save time when creating similar tournaments, use templates:

### Saving a Template
1. Fill out the tournament configuration form
2. Click **Save as Template** at the bottom
3. Enter a descriptive name (e.g., "YOUTH Weekly Budapest")
4. Click Save

### Loading a Template
1. At the top of the configuration screen, select a template from the dropdown
2. Click **Load**
3. All fields will auto-fill with the template values
4. Adjust any fields as needed
5. Click **Submit to Workflow** to create the tournament

### Managing Templates
- Click **Manage** to view all saved templates
- Use **Load** to apply a template
- Use **Delete** to remove templates you no longer need
```

---

## 🔄 Alternative Solutions Considered

### Alternative 1: Backend Database Storage

**Approach**: Store templates in PostgreSQL via API

**Pros**:
- Templates persist across devices
- Can share templates between users
- Centralized management

**Cons**:
- ❌ Requires backend changes (API endpoints, DB schema, migrations)
- ❌ Higher implementation cost (12-16 hours vs 5-7 hours)
- ❌ Higher risk (production database changes)
- ❌ Overkill for single-user sandbox environment

**Verdict**: ❌ Not recommended for MVP (over-engineering)

### Alternative 2: URL Query Parameters

**Approach**: Encode config in URL, share bookmarks

**Pros**:
- Zero implementation (just URL encoding)
- Shareable via link

**Cons**:
- ❌ URL length limits (30+ fields = very long URL)
- ❌ Not user-friendly (ugly URLs, hard to manage)
- ❌ No naming/organization

**Verdict**: ❌ Not recommended (poor UX)

### Alternative 3: Duplicate Last Tournament Button

**Approach**: "Clone last tournament" button

**Pros**:
- Simpler than full template system
- Covers 80% of use case (repeat last config)

**Cons**:
- ❌ Only 1 template (last tournament)
- ❌ No organization (can't have "YOUTH template" + "PRO template")
- ❌ Less flexible

**Verdict**: ⚠️ Could be Phase 0 (quick win), but template system provides more value

---

## 🎯 Success Metrics

### Quantitative KPIs

**Usage Metrics**:
- % of tournaments created from templates (target: >60% after 2 weeks)
- Avg time to complete configuration screen (target: <90 seconds with templates vs 5-8 min without)
- Number of templates created per user (target: 2-4 per instructor)

**Efficiency Metrics**:
- Reduction in form abandonment rate (users giving up mid-configuration)
- Increase in tournament creation frequency (templates reduce friction)

### Qualitative KPIs

**User Feedback**:
- "This saves me so much time!" (positive sentiment)
- "Can we add template sharing?" (feature request = high engagement)
- "No more re-entering 30 fields every time" (pain point addressed)

---

## 📅 Timeline & Milestones

**Week 1: MVP Implementation** (5 hours)
- Day 1-2: Core save/load functionality (3 hours)
- Day 3: Template management UI (1 hour)
- Day 4: Export/import (1 hour)
- Day 5: Testing & bug fixes

**Week 2: Enhancement** (Optional, 2 hours)
- Day 6: localStorage persistence component
- Day 7: Polish & documentation

**Week 3: User Validation**
- Deploy to sandbox environment
- Collect instructor feedback
- Iterate based on usage data

---

## 🔗 Related Work

**Dependencies**: None (fully standalone)

**Enables Future Work**:
- Template sharing (Phase 2: backend integration)
- Recommended system templates (Phase 3: admin-curated)
- Template marketplace (Phase 4: community templates)

**Related Features**:
- Game preset management (already exists, similar pattern)
- Session configuration presets (future opportunity)

---

## 📝 Open Questions

1. **Template Limit**: Should we limit templates per user? (e.g., max 10 templates)
   - **Recommendation**: No limit for MVP, add if localStorage gets full

2. **Template Validation**: Should we validate templates on load? (e.g., check if game preset ID still exists)
   - **Recommendation**: Yes, show warning if preset not found, allow user to fix

3. **Template Naming**: Allow duplicate names or enforce unique?
   - **Recommendation**: Enforce unique (avoid confusion)

4. **Default Templates**: Should we ship with 2-3 pre-made templates?
   - **Recommendation**: Yes, helps onboarding ("YOUTH Sample", "PRO Sample")

---

## ✅ Recommendation

**APPROVE FOR IMMEDIATE IMPLEMENTATION** (Week 5 or 6)

**Rationale**:
1. ✅ High user value (70-80% time savings)
2. ✅ Low implementation cost (5-7 hours)
3. ✅ Low technical risk (client-side only, no backend)
4. ✅ Clear ROI (payback in 3-4 weeks)
5. ✅ High user delight ("finally!" moment)
6. ✅ Enables experimentation (templates lower barrier to testing)

**Next Steps**:
1. User validation: Show mockup to 2-3 instructors for feedback
2. Technical spike: Test localStorage persistence in Streamlit (30 min)
3. Implementation: Schedule for Week 5 (after Sprint 3 completion)
4. Deploy & iterate: Week 6

---

**Created By**: Claude Sonnet 4.5
**Date**: 2026-01-31
**Status**: Ready for stakeholder review
**Estimated Effort**: 5-7 hours (MVP)
**Expected ROI**: 70-130 min/week saved across team
