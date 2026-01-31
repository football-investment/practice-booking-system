# Implementation Plan: Tournament Templates (MVP)

**Feature**: Tournament Templates (Save/Load configuration)
**Status**: ✅ APPROVED - Awaiting GO signal
**Scope**: MVP - Client-side only, session_state storage
**Estimated Time**: 5 hours
**Risk**: 🟢 LOW

---

## 📋 MVP Scope (Approved)

### What's Included ✅

- ✅ Save current form configuration as named template
- ✅ Load template → auto-fill all form fields
- ✅ List saved templates (dropdown selector)
- ✅ Delete templates (manage dialog)
- ✅ Template metadata (name, created date)
- ✅ All 30+ configuration fields stored

### What's Excluded ❌

- ❌ **Persistence across sessions** (session_state only, lost on refresh)
- ❌ Export/Import JSON (deferred to Phase 2)
- ❌ Browser localStorage (deferred to Phase 2)
- ❌ Template editing/renaming (create new instead)
- ❌ Template validation (assume data is valid)
- ❌ Pre-made system templates (user creates own)

### MVP Limitations (Accepted Trade-offs)

⚠️ **User Experience Limitation**:
- Templates lost on browser refresh/close
- Users must recreate templates each session
- **Mitigation**: Phase 2 adds persistence (localStorage or export/import)

⚠️ **Why This Is Acceptable for MVP**:
- Proves value proposition (70-80% time savings)
- Zero technical risk (no persistence = no storage bugs)
- Fast implementation (5 hours vs 7 hours)
- Can upgrade to persistent storage after validation

---

## 🎯 Implementation Overview

### File Changes

**Single File Modified**:
- `streamlit_sandbox_v3_admin_aligned.py` (lines ~137-595, configuration screen)

**Estimated Lines Added**: ~200-250 lines
- Template storage functions: 50 lines
- Template UI components: 100 lines
- Form pre-fill logic: 50 lines
- Template management dialog: 50 lines

---

## 🔧 Technical Architecture

### Data Structure

```python
# Session state structure
st.session_state['templates'] = {
    'YOUTH Budapest Weekly': {
        'name': 'YOUTH Budapest Weekly',
        'created_at': '2026-01-31T14:30:00',
        'config': {
            'tournament_name': 'YOUTH Weekly Tournament',
            'age_group': 'YOUTH',
            'location_id': 1,
            'campus_id': 2,
            'tournament_format': 'league',
            'scoring_mode': 'INDIVIDUAL',
            'number_of_rounds': 3,
            'scoring_type': 'TIME_BASED',
            'ranking_direction': 'ASC',
            'measurement_unit': 'seconds',
            'max_players': 15,
            'start_date': '2026-02-01',
            'end_date': '2026-02-28',
            'game_preset_id': 5,
            'performance_variation': 'MEDIUM',
            'ranking_distribution': 'NORMAL',
            'skills_to_test': ['dribbling', 'passing', 'shooting', ...],
            'selected_users': [1, 2, 3, 4, 5, ...],
            'rewards': {
                'first_place': {'xp': 500, 'credits': 100},
                'second_place': {'xp': 300, 'credits': 50},
                'third_place': {'xp': 200, 'credits': 25},
                'participation': {'xp': 50, 'credits': 0},
                'session_base_xp': 20
            }
        }
    },
    'PRO Debrecen Monthly': { ... },
    ...
}
```

---

## 📝 Implementation Steps

### Phase 1: Template Storage Functions (1 hour)

**Location**: Top of `render_configuration_screen()` function (after imports)

**Functions to Add**:

```python
def get_templates() -> Dict[str, Dict]:
    """Get all saved templates from session state"""
    if 'templates' not in st.session_state:
        st.session_state['templates'] = {}
    return st.session_state['templates']

def save_template(template_name: str, config: Dict):
    """Save tournament config as template"""
    templates = get_templates()
    templates[template_name] = {
        'name': template_name,
        'created_at': datetime.now().isoformat(),
        'config': config
    }
    st.session_state['templates'] = templates

def load_template(template_name: str) -> Dict:
    """Load template config"""
    templates = get_templates()
    template = templates.get(template_name)
    return template['config'] if template else {}

def delete_template(template_name: str):
    """Delete template"""
    templates = get_templates()
    if template_name in templates:
        del templates[template_name]
        st.session_state['templates'] = templates

def list_template_names() -> List[str]:
    """Get list of template names sorted by creation date"""
    templates = get_templates()
    return sorted(templates.keys(),
                  key=lambda name: templates[name]['created_at'],
                  reverse=True)
```

**Testing**:
- Create template → verify in `st.session_state['templates']`
- Load template → verify config returned
- Delete template → verify removed from state

---

### Phase 2: Template Selector UI (2 hours)

**Location**: `render_configuration_screen()`, before form rendering (line ~180)

**UI Component**:

```python
def render_template_selector():
    """Render template selector at top of config screen"""
    st.markdown("### 📋 Tournament Templates")

    template_names = list_template_names()

    if not template_names:
        st.info("No saved templates. Fill out the form below and save it as a template.")
        return None

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        selected_template = st.selectbox(
            "Select a template to load",
            options=["(None)", *template_names],
            key="template_selector",
            help="Choose a saved template to auto-fill the configuration form"
        )

    with col2:
        load_disabled = selected_template == "(None)"
        if st.button(
            "Load Template",
            disabled=load_disabled,
            key="btn_load_template",
            use_container_width=True
        ):
            config = load_template(selected_template)
            st.session_state['loaded_template_config'] = config
            Success.toast(f"Template '{selected_template}' loaded!")
            st.rerun()

    with col3:
        if st.button(
            "Manage",
            key="btn_manage_templates",
            use_container_width=True
        ):
            st.session_state['show_manage_templates'] = True
            st.rerun()

    st.markdown("---")

    return selected_template if selected_template != "(None)" else None
```

**Integration**:
```python
def render_configuration_screen():
    st.title("Sandbox Tournament Test (Admin-Aligned)", anchor=False)

    # ... auth check ...

    # NEW: Template selector (before form)
    render_template_selector()

    # Existing form rendering...
    form = SingleColumnForm("tournament_config_form", ...)
    # ...
```

**Testing**:
- No templates → shows info message
- 3 templates → dropdown shows all 3
- Select + Load → verify `st.session_state['loaded_template_config']` populated
- Manage button → opens dialog

---

### Phase 3: Form Pre-fill Logic (1 hour)

**Location**: `render_configuration_screen()`, within form field definitions

**Pattern (apply to ALL 30+ fields)**:

```python
# Check if template was loaded
loaded_config = st.session_state.get('loaded_template_config', {})

# Example: Tournament Name field
tournament_name = st.text_input(
    "Tournament Name",
    value=loaded_config.get('tournament_name', ''),  # Pre-fill from template
    key=form.field_key("tournament_name")
)

# Example: Age Group dropdown
age_group = st.selectbox(
    "Age Group",
    AGE_GROUPS,
    index=AGE_GROUPS.index(loaded_config['age_group']) if loaded_config.get('age_group') in AGE_GROUPS else 0,
    key=form.field_key("age_group")
)

# Example: Skills checkboxes (complex)
skills_to_test = []
for category_name, skill_keys in SKILL_CATEGORIES.items():
    st.markdown(f"**{category_name}**")
    for skill_key in skill_keys:
        # Pre-check if skill is in loaded template
        default_checked = skill_key in loaded_config.get('skills_to_test', [])

        is_checked = st.checkbox(
            skill_key,
            value=default_checked,  # Pre-fill from template
            key=form.field_key(f"skill_{skill_key}")
        )
        if is_checked:
            skills_to_test.append(skill_key)

# Example: Participant toggles (complex)
if "participant_toggles" not in st.session_state:
    # Pre-populate from loaded template
    st.session_state.participant_toggles = {
        user_id: user_id in loaded_config.get('selected_users', [])
        for user_id in [user['id'] for user in user_list]
    }
```

**Fields to Pre-fill** (all 30+):
1. Tournament name (text)
2. Age group (dropdown)
3. Location ID (dropdown)
4. Campus ID (dropdown)
5. Tournament format (dropdown)
6. Scoring mode (dropdown)
7. Number of rounds (number input, conditional)
8. Scoring type (dropdown, conditional)
9. Ranking direction (dropdown, conditional)
10. Measurement unit (text, conditional)
11. Max players (number input)
12. Start date (date picker)
13. End date (date picker)
14. Game preset ID (dropdown)
15. Performance variation (dropdown)
16. Ranking distribution (dropdown)
17-30. Skills checkboxes (12-20 skills)
31-60. Participant toggles (10-30 users)
61. First place XP (number input)
62. First place credits (number input)
63. Second place XP (number input)
64. Second place credits (number input)
65. Third place XP (number input)
66. Third place credits (number input)
67. Participation XP (number input)
68. Session base XP (number input)

**Testing**:
- Load template → all fields auto-filled correctly
- Adjust 2-3 fields → verify changes preserved
- Submit → verify config includes both template + manual changes

---

### Phase 4: Save Template Dialog (1 hour)

**Location**: End of `render_configuration_screen()`, after form submit button

**UI Component**:

```python
def render_save_template_button_and_dialog(config: Dict):
    """Render save template button and dialog"""
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "💾 Save as Template",
            key="btn_save_template",
            use_container_width=True,
            help="Save current configuration as a reusable template"
        ):
            st.session_state['show_save_template_dialog'] = True
            st.rerun()

    with col2:
        # Existing submit button
        # ... (unchanged)

    # Save Template Dialog
    if st.session_state.get('show_save_template_dialog', False):
        with st.dialog("💾 Save as Template"):
            st.markdown("Save the current tournament configuration as a reusable template.")

            template_name = st.text_input(
                "Template Name",
                placeholder="e.g., YOUTH Budapest Weekly",
                key="input_template_name",
                help="Choose a descriptive name for this template"
            )

            # Name validation
            existing_names = list_template_names()
            name_exists = template_name in existing_names

            if name_exists:
                Error.message(f"Template '{template_name}' already exists. Choose a different name.")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Cancel", key="btn_cancel_save_template", use_container_width=True):
                    st.session_state['show_save_template_dialog'] = False
                    st.rerun()

            with col2:
                save_disabled = not template_name or name_exists
                if st.button(
                    "Save Template",
                    type="primary",
                    disabled=save_disabled,
                    key="btn_confirm_save_template",
                    use_container_width=True
                ):
                    save_template(template_name, config)
                    Success.message(f"Template '{template_name}' saved!")
                    st.session_state['show_save_template_dialog'] = False
                    st.rerun()
```

**Integration**:
```python
# At end of render_configuration_screen(), before form.close_container()

# Collect all config fields into dict
config = {
    'tournament_name': tournament_name,
    'age_group': age_group,
    # ... all 30+ fields ...
}

# Render save template button + dialog
render_save_template_button_and_dialog(config)

# Existing submit button logic...
if form.submit_button("Submit to Workflow"):
    # ... existing code ...
```

**Testing**:
- Click "Save as Template" → dialog opens
- Enter duplicate name → error shown, save button disabled
- Enter unique name + Save → template saved, dialog closes
- Re-open config screen → new template appears in dropdown

---

### Phase 5: Template Management Dialog (1 hour)

**Location**: Triggered by "Manage" button in template selector

**UI Component**:

```python
def render_manage_templates_dialog():
    """Render template management dialog"""
    if not st.session_state.get('show_manage_templates', False):
        return

    with st.dialog("📋 Manage Templates", width="large"):
        st.markdown("View and manage your saved tournament templates.")

        templates = get_templates()
        template_names = list_template_names()

        if not template_names:
            st.info("No templates saved yet.")
        else:
            st.markdown(f"**Total Templates**: {len(template_names)}")
            st.markdown("---")

            for template_name in template_names:
                template = templates[template_name]
                config = template['config']
                created_at = template['created_at']

                # Template card
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(f"**{template_name}**")
                    st.caption(
                        f"Age: {config.get('age_group', 'N/A')} | "
                        f"Format: {config.get('tournament_format', 'N/A')} | "
                        f"Skills: {len(config.get('skills_to_test', []))} | "
                        f"Created: {created_at[:10]}"
                    )

                with col2:
                    if st.button(
                        "Load",
                        key=f"btn_load_{template_name}",
                        use_container_width=True
                    ):
                        st.session_state['loaded_template_config'] = config
                        st.session_state['show_manage_templates'] = False
                        Success.toast(f"Template '{template_name}' loaded!")
                        st.rerun()

                with col3:
                    if st.button(
                        "Delete",
                        key=f"btn_delete_{template_name}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        delete_template(template_name)
                        Success.toast(f"Template '{template_name}' deleted")
                        st.rerun()

                # Expandable details
                with st.expander("View Details"):
                    st.json(config)

                st.markdown("---")

        # Close button
        if st.button("Close", key="btn_close_manage_templates", use_container_width=True):
            st.session_state['show_manage_templates'] = False
            st.rerun()
```

**Integration**:
```python
def render_configuration_screen():
    # ... existing code ...

    # NEW: Render manage templates dialog (if open)
    render_manage_templates_dialog()

    # ... rest of screen ...
```

**Testing**:
- Click "Manage" → dialog opens with all templates
- Each template shows: name, metadata (age group, format, skills count), created date
- Click "Load" from dialog → config loaded, dialog closes, form pre-filled
- Click "Delete" → template removed, dialog refreshes
- Click "View Details" → full JSON shown

---

## 🚨 Edge Cases & Error Handling

### Edge Case 1: Name Collision

**Scenario**: User tries to save template with existing name

**Handling**:
```python
# In save template dialog
if template_name in existing_names:
    Error.message(f"Template '{template_name}' already exists. Choose a different name.")
    # Disable save button
```

**User Action**: Must choose different name (no overwrite option in MVP)

---

### Edge Case 2: Empty Template Name

**Scenario**: User clicks "Save Template" without entering name

**Handling**:
```python
# In save template dialog
save_disabled = not template_name or name_exists
if st.button("Save Template", disabled=save_disabled, ...):
    # Button disabled if name is empty
```

**User Action**: Must enter name to enable save button

---

### Edge Case 3: Template Load + Form Reset

**Scenario**: User loads template, edits fields, then loads different template

**Handling**:
```python
# When Load button clicked
if st.button("Load Template", ...):
    config = load_template(selected_template)
    st.session_state['loaded_template_config'] = config
    # Clear any previous manual edits
    st.session_state['participant_toggles'] = {}  # Will be repopulated from template
    st.rerun()
```

**User Experience**: Loading new template overwrites current form (expected behavior)

---

### Edge Case 4: Invalid Field Values in Template

**Scenario**: Template contains location_id that no longer exists (location deleted from DB)

**Handling** (MVP - No Validation):
```python
# Form will render with invalid value
# Dropdowns will show blank or error
# User must manually select valid value
```

**Future Enhancement**: Add validation on load, show warning if data is stale

---

### Edge Case 5: Session State Lost on Refresh

**Scenario**: User refreshes browser, loses all templates

**Handling** (MVP - Accept Limitation):
```python
# No handling - templates lost
# User must recreate templates each session
```

**User Warning**: Add info banner at top of config screen
```python
st.info("⚠️ Templates are stored in this browser session only. They will be lost on refresh. "
        "Persistence coming in next release!")
```

**Future Enhancement**: Phase 2 adds localStorage or export/import

---

### Edge Case 6: Partial Form Fill + Template Load

**Scenario**: User fills 10 fields, then loads template

**Handling**:
```python
# Template load triggers st.rerun()
# Form re-renders with template values
# Manual edits LOST (overwritten by template)
```

**User Experience**: Expected (loading template = reset form to template values)

**Future Enhancement**: Show confirmation dialog: "Loading template will overwrite your current changes. Continue?"

---

### Edge Case 7: Delete While Viewing in Manage Dialog

**Scenario**: User deletes last template in manage dialog

**Handling**:
```python
# After delete_template(), st.rerun() triggers
# Dialog re-renders with updated template list
# If no templates, shows "No templates saved yet" message
```

**User Experience**: Dialog updates smoothly, no error

---

### Edge Case 8: Save Template Button Clicked Before Form Filled

**Scenario**: User clicks "Save as Template" with empty form

**Handling** (MVP - Allow Empty Templates):
```python
# No validation - allow saving empty/partial config
# User gets template with default values (empty strings, 0s, etc.)
```

**Rationale**: Simple implementation, user learns not to save empty forms

**Future Enhancement**: Add validation: "Please fill at least Tournament Name before saving"

---

## 🧪 Testing Checklist

### Manual Testing Scenarios

**Test 1: Save Template - Happy Path**
- [ ] Fill all 30+ form fields with valid data
- [ ] Click "Save as Template"
- [ ] Enter name "Test Template 1"
- [ ] Click "Save Template"
- [ ] Verify success message
- [ ] Verify template appears in dropdown

**Test 2: Load Template - Happy Path**
- [ ] Select "Test Template 1" from dropdown
- [ ] Click "Load Template"
- [ ] Verify all form fields auto-filled correctly
- [ ] Modify 2-3 fields (e.g., tournament name, max players)
- [ ] Click "Submit to Workflow"
- [ ] Verify workflow receives mixed data (template + manual edits)

**Test 3: Delete Template**
- [ ] Click "Manage" button
- [ ] Click "Delete" next to "Test Template 1"
- [ ] Verify success message
- [ ] Verify template removed from list
- [ ] Close dialog
- [ ] Verify dropdown no longer shows deleted template

**Test 4: Name Collision**
- [ ] Save template "Duplicate Test"
- [ ] Fill form differently
- [ ] Try to save as "Duplicate Test" again
- [ ] Verify error message shown
- [ ] Verify save button disabled
- [ ] Change name to "Duplicate Test 2"
- [ ] Verify save succeeds

**Test 5: Multiple Templates**
- [ ] Create 5 different templates with distinct names
- [ ] Verify all 5 appear in dropdown (sorted by creation date)
- [ ] Load each template one by one
- [ ] Verify each loads correct config

**Test 6: Session Refresh (Limitation)**
- [ ] Create 3 templates
- [ ] Refresh browser (F5 or Cmd+R)
- [ ] Return to config screen
- [ ] Verify templates LOST (dropdown empty)
- [ ] Verify info message shown about session-only storage

**Test 7: Empty Template Name**
- [ ] Click "Save as Template"
- [ ] Leave name field empty
- [ ] Verify save button disabled
- [ ] Enter name
- [ ] Verify save button enabled

**Test 8: Template with Complex Fields**
- [ ] Fill form with:
  - 15 skills selected (across 3 categories)
  - 20 participants toggled on
  - INDIVIDUAL scoring mode with all sub-fields
  - Custom rewards (non-default values)
- [ ] Save as "Complex Template"
- [ ] Reload page to clear form
- [ ] Load "Complex Template"
- [ ] Verify ALL complex fields restored:
  - All 15 skills checked
  - All 20 participants toggled
  - Scoring mode + sub-fields correct
  - Rewards match saved values

---

## 📊 Success Criteria

### Functional Requirements

- [ ] User can save tournament config as named template
- [ ] User can load template → form auto-fills
- [ ] User can delete templates
- [ ] User can view all templates in manage dialog
- [ ] Templates include all 30+ configuration fields
- [ ] Duplicate names prevented (error shown)
- [ ] Empty names prevented (save button disabled)

### Non-Functional Requirements

- [ ] Implementation time: ≤5 hours
- [ ] No backend changes (client-side only)
- [ ] No database changes
- [ ] No API endpoint changes
- [ ] No production risk (isolated to sandbox config screen)
- [ ] Code follows existing patterns (SingleColumnForm, Card, Success/Error feedback)

### User Experience

- [ ] Template selector visible at top of config screen
- [ ] Load template takes <2 seconds (instant UI update)
- [ ] Save template dialog intuitive (clear labels, validation feedback)
- [ ] Manage templates dialog shows useful metadata
- [ ] Error messages clear and actionable
- [ ] Warning shown about session-only storage

---

## 📅 Implementation Timeline

**Total Time**: 5 hours (when GO signal given)

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Template storage functions | 1h | ⏳ Awaiting GO |
| 2 | Template selector UI | 2h | ⏳ Awaiting GO |
| 3 | Form pre-fill logic | 1h | ⏳ Awaiting GO |
| 4 | Save template dialog | 0.5h | ⏳ Awaiting GO |
| 5 | Manage templates dialog | 0.5h | ⏳ Awaiting GO |

**Buffer**: No buffer in MVP (tight scope)

---

## 🚦 Ready to Implement

**Status**: ✅ **PLAN APPROVED - Awaiting GO Signal**

**What happens when GO is given**:
1. Create feature branch: `feature/sandbox-templates-mvp`
2. Implement Phase 1-5 (5 hours)
3. Manual testing (1 hour)
4. Commit + push for review
5. Deploy to sandbox environment
6. User validation

**Blocked on**: Explicit "GO" command from stakeholder

---

**Created By**: Claude Sonnet 4.5
**Date**: 2026-01-31
**Status**: Implementation-ready, awaiting approval
**Estimated Delivery**: Same day as GO (5 hours from start)
