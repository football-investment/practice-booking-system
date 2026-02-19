# UI Refactoring Pattern - Canonical Reference

**Version**: 1.0
**Date**: 2026-01-30
**Status**: ✅ **ESTABLISHED**
**Based on**: Priority 3 Week 2 Sandbox Refactoring Success

---

## 🎯 Purpose

This document serves as the **canonical reference** for refactoring monolithic Streamlit UI files using the component library pattern.

**Use this pattern for**:
- All Streamlit UI refactoring tasks
- New Streamlit pages/screens
- Component library integration
- E2E test enablement

---

## 📋 Prerequisites

Before starting a UI refactoring:

### 1. Component Library Available ✅
- `streamlit_components/core` - API client, auth, state
- `streamlit_components/layouts` - SingleColumnForm, Card, Section
- `streamlit_components/feedback` - Loading, Success, Error

### 2. Source File Identified
- File size >500 lines (worth refactoring)
- Multiple responsibilities (needs decomposition)
- Duplicated code patterns

### 3. Backup Created
```bash
git tag -a "pre-refactor-{filename}" -m "Backup before refactoring {filename}"
```

---

## 🏗️ Refactoring Steps (Proven Pattern)

### Step 1: Analyze Current Structure

**Goal**: Understand file organization and identify extraction opportunities

**Actions**:
```bash
# Check file size
wc -l {filename}.py

# Identify major sections
grep -n "^def \|^class " {filename}.py

# Count API calls
grep -n "requests\.\|\.get(\|\.post(" {filename}.py | wc -l
```

**Document**:
- Total lines
- Number of functions
- Number of API calls
- Major UI sections

**Example** (from sandbox refactoring):
```
streamlit_sandbox_v3_admin_aligned.py:
- Total lines: 3,429
- Functions: ~40
- API calls: 18 (manual requests)
- Sections: Home, Configuration, Workflow (6 steps), History
```

---

### Step 2: Create Helper Module

**Goal**: Extract reusable API functions to separate module

**Naming Convention**:
```
{original_filename}_helpers.py
```

**Example**:
```
streamlit_sandbox_v3_admin_aligned.py → sandbox_helpers.py
tournament_list.py → tournament_list_helpers.py
```

**Pattern**:
```python
"""
{Module Name} Helper Functions

Reusable functions for the {module purpose}.
All API calls use the centralized api_client from streamlit_components.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from streamlit_components.core.api_client import api_client, APIError
from streamlit_components.feedback import Error, Success, Loading


def fetch_data(param: str) -> List[Dict]:
    """Fetch data from API"""
    try:
        return api_client.get(f"/api/v1/endpoint/{param}")
    except APIError as e:
        Error.message(f"Failed to fetch data: {e.message}")
        return []


def create_resource(data: Dict) -> Optional[Dict]:
    """Create resource via API"""
    try:
        result = api_client.post("/api/v1/resource", data=data)
        Success.message("Resource created successfully!")
        return result
    except APIError as e:
        Error.message(f"Failed to create resource: {e.message}")
        return None
```

**Guidelines**:
- ✅ All functions use `api_client` (never manual `requests`)
- ✅ Consistent error handling with `Error.message()`
- ✅ Success feedback with `Success.message()`
- ✅ Type hints for all parameters and returns
- ✅ Docstrings for all functions
- ✅ Return empty list/None on error (graceful degradation)

**Target**: 150-250 lines

---

### Step 3: Create Workflow/Screen Module (if needed)

**Goal**: Extract distinct screens or workflow steps

**Naming Convention**:
```
{original_filename}_workflow.py    # For multi-step workflows
{original_filename}_screens.py     # For distinct screens
```

**Example** (from sandbox):
```python
"""
Tournament Workflow Steps Module

Contains all 6 instructor workflow steps.
Each step uses component library for consistent UX and E2E testing.
"""

import streamlit as st
from streamlit_components.core import api_client
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error
from {helpers_module} import fetch_data, create_resource


def render_step_1():
    """
    Step 1: Description

    This step:
    - Action 1
    - Action 2
    - Moves to next step
    """
    st.markdown("### 1. Step Title")

    card = Card(title="Step Content", card_id="step1_card")
    with card.container():
        # Content here
        pass
    card.close_container()

    st.markdown("---")

    if st.button(
        "Continue",
        type="primary",
        use_container_width=True,
        key="btn_continue_step2"
    ):
        st.session_state.workflow_step = 2
        st.rerun()
```

**Guidelines**:
- ✅ One function per step/screen
- ✅ Card components for organization
- ✅ Consistent button naming: `btn_{action}_{step}`
- ✅ Use session state for navigation
- ✅ Document what each step does

**Target**: 300-500 lines

---

### Step 4: Refactor Main File

**Goal**: Reduce main file to UI orchestration only

**Pattern**:
```python
"""
{Module Name} - REFACTORED

Complete restructure using streamlit_components library:
- SingleColumnForm for all forms
- api_client for all API calls
- Card components for content grouping
- data-testid attributes for E2E testing

Run: streamlit run {filename}.py --server.port {port}
"""

import streamlit as st
from streamlit_components.core import api_client, auth
from streamlit_components.layouts import SingleColumnForm, Card, PageHeader
from streamlit_components.feedback import Loading, Success, Error

# Local imports
from {helpers_module} import fetch_data, create_resource, render_display
from {workflow_module} import render_step_1, render_step_2  # if applicable

# Page config
st.set_page_config(
    page_title="{Page Title}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def render_main_screen():
    """Main screen UI"""
    # Use PageHeader
    header = PageHeader(
        title="Page Title",
        subtitle="Description",
        breadcrumbs=["Home", "Section"]
    )
    header.render()

    # Use Card for content
    card = Card(title="Content", card_id="main_card")
    with card.container():
        # Content
        pass
    card.close_container()


# Main app logic
if __name__ == "__main__":
    # Authentication check
    if not auth.is_authenticated():
        auth.show_login_form()
        st.stop()

    # Render appropriate screen
    render_main_screen()
```

**Guidelines**:
- ✅ Import component library at top
- ✅ Import local helpers
- ✅ Use PageHeader for titles
- ✅ Use Card for content grouping
- ✅ Delegate to helper functions
- ✅ Keep main file <800 lines

**Target**: 400-700 lines

---

### Step 5: Add Data-TestID Selectors

**Goal**: Enable E2E testing with Playwright

**Naming Convention**:
```
btn_{action}          # Buttons
metric_{name}         # Metrics/stats
input_{field}         # Form inputs
select_{field}        # Dropdowns
section_{name}        # Sections
card_{name}           # Cards
```

**Pattern**:
```python
# Buttons
st.button(
    "Create Tournament",
    type="primary",
    key="btn_create_tournament"  # This becomes data-testid
)

# Metrics
st.metric(
    "Total",
    value=count,
    key="metric_total"  # data-testid for E2E
)

# Form inputs (use key parameter)
st.text_input(
    "Name",
    key="input_tournament_name"
)

st.selectbox(
    "Format",
    options=formats,
    key="select_tournament_format"
)
```

**Guidelines**:
- ✅ EVERY interactive element needs a key
- ✅ Use semantic names (clear purpose)
- ✅ Follow naming convention
- ✅ Document all selectors in comment

**Target**: 15+ selectors per major screen

---

### Step 6: Create E2E Tests

**Goal**: Validate refactored UI with Playwright tests

**Naming Convention**:
```
tests/e2e/test_{module_name}.py
```

**Pattern**:
```python
"""
E2E Tests for {Module Name}

Tests the refactored {module} using data-testid selectors.

Prerequisites:
- API server running on http://localhost:8000
- {App} running on http://localhost:{port}
"""

import pytest
from playwright.sync_api import Page, expect


APP_URL = "http://localhost:{port}"


class Test{Module}Navigation:
    """Test navigation flows"""

    def test_navigate_to_section(self, page: Page):
        """Test navigation to {section}"""
        page.goto(APP_URL)
        page.wait_for_timeout(2000)

        # Click navigation button
        page.get_by_role("button", name="{Button Text}").click()
        page.wait_for_timeout(1000)

        # Verify section loaded
        expect(page.get_by_text("{Section Title}")).to_be_visible(timeout=5000)


class Test{Module}Workflow:
    """Test complete workflow"""

    @pytest.mark.slow
    def test_complete_workflow(self, page: Page):
        """Test full user workflow"""
        page.goto(APP_URL)

        # Step 1
        page.get_by_role("button", name="Start").click()
        expect(page.get_by_text("Step 1 Complete")).to_be_visible()

        # Step 2
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_text("Step 2 Complete")).to_be_visible()

        # Final verification
        expect(page.get_by_text("Workflow Complete")).to_be_visible()
```

**Guidelines**:
- ✅ One test file per main UI file
- ✅ Group tests by functionality (navigation, workflow, etc.)
- ✅ Use descriptive test names
- ✅ Add docstrings explaining what's tested
- ✅ Use `@pytest.mark.slow` for long tests
- ✅ Minimum 1-2 tests per major screen

**Target**: 150-400 lines, 5-10 test methods

---

## 📊 Success Metrics

### File Size Targets

| Original Size | Target Size | Reduction |
|---------------|-------------|-----------|
| 3,000-4,000 lines | 600-800 lines | 75-80% |
| 2,000-3,000 lines | 400-600 lines | 70-75% |
| 1,000-2,000 lines | 300-500 lines | 65-70% |

### Module Breakdown

| Module | Target Lines | Purpose |
|--------|--------------|---------|
| Main UI file | 400-700 | Orchestration only |
| Helpers | 150-250 | API functions |
| Workflow/Screens | 300-500 | Step/screen logic |

### Component Usage

| Component | Minimum Usage |
|-----------|---------------|
| api_client | 100% of API calls |
| auth | All auth checks |
| Card | All content sections |
| Success/Error | All feedback |
| Loading | All async operations |

### E2E Testing

| Metric | Target |
|--------|--------|
| data-testid selectors | 15+ per screen |
| Test methods | 5-10 per file |
| Workflow coverage | 100% |

---

## ✅ Quality Checklist

Before considering refactoring complete, verify:

### Code Quality
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] No duplicated code patterns
- [ ] Consistent error handling
- [ ] No manual `requests` calls (use `api_client`)

### Component Usage
- [ ] All API calls use `api_client`
- [ ] All auth checks use `auth`
- [ ] All feedback uses `Success`/`Error`/`Loading`
- [ ] All content uses `Card` components
- [ ] All forms use `SingleColumnForm` (if applicable)

### E2E Testing
- [ ] All buttons have keys (data-testid)
- [ ] All inputs have keys
- [ ] All metrics have keys
- [ ] Test file created with 5+ tests
- [ ] Tests documented with docstrings

### Documentation
- [ ] Refactoring documented in markdown file
- [ ] Changes committed with descriptive message
- [ ] Git tag created for milestone
- [ ] Component usage documented

### Verification
- [ ] All imports work
- [ ] App runs without errors
- [ ] All functionality preserved
- [ ] E2E tests pass (or documented if blocked)

---

## 🎯 Example: Sandbox Refactoring (Reference Implementation)

### Before
```
streamlit_sandbox_v3_admin_aligned.py: 3,429 lines (monolithic)
```

### After
```
streamlit_sandbox_v3_admin_aligned.py:    626 lines (UI orchestration)
sandbox_helpers.py:                       194 lines (14 API functions)
sandbox_workflow.py:                      390 lines (6 workflow steps)
tests/e2e/test_sandbox_workflow.py:       335 lines (8 test methods)
───────────────────────────────────────────────────────────────
Total codebase:                         1,210 lines
Total with tests:                       1,545 lines
Reduction:                              -65% (code), -55% (with tests)
```

### Key Achievements
- ✅ 65% code reduction
- ✅ 3 focused, modular files
- ✅ 100% component library integration
- ✅ 18 data-testid selectors
- ✅ 8 E2E test methods
- ✅ 100% workflow coverage

### Files Created
1. `sandbox_helpers.py` - API functions
2. `sandbox_workflow.py` - 6-step workflow
3. `tests/e2e/test_sandbox_workflow.py` - E2E tests
4. `SANDBOX_REFACTORING_COMPLETE.md` - Documentation
5. `WEEK_2_SANDBOX_SUMMARY.md` - Summary
6. `E2E_TESTS_ENABLED.md` - E2E documentation

---

## 🚫 Anti-Patterns (What NOT to Do)

### ❌ Don't Create New Abstractions
```python
# BAD: Creating unnecessary abstractions
class ButtonFactory:
    def create_primary_button(self, label):
        return st.button(label, type="primary")

# GOOD: Use Streamlit directly
st.button("Create", type="primary", key="btn_create")
```

### ❌ Don't Mix Patterns
```python
# BAD: Mixing manual requests with api_client
response = requests.get(url, headers=headers)  # Manual
data = api_client.get("/endpoint")            # api_client

# GOOD: Use api_client consistently
data = api_client.get("/endpoint")
```

### ❌ Don't Skip Type Hints
```python
# BAD: No type hints
def fetch_data(id):
    return api_client.get(f"/api/v1/data/{id}")

# GOOD: Type hints present
def fetch_data(id: int) -> Optional[Dict]:
    """Fetch data by ID"""
    try:
        return api_client.get(f"/api/v1/data/{id}")
    except APIError as e:
        Error.message(f"Failed: {e.message}")
        return None
```

### ❌ Don't Forget Error Handling
```python
# BAD: No error handling
def create_item(data):
    return api_client.post("/items", data=data)

# GOOD: Consistent error handling
def create_item(data: Dict) -> Optional[Dict]:
    """Create item via API"""
    try:
        result = api_client.post("/items", data=data)
        Success.message("Item created!")
        return result
    except APIError as e:
        Error.message(f"Failed to create item: {e.message}")
        return None
```

### ❌ Don't Skip Data-TestID Selectors
```python
# BAD: No key for E2E testing
st.button("Submit")

# GOOD: Key for E2E testing
st.button("Submit", key="btn_submit_form")
```

---

## 📚 Component Library Quick Reference

### Core Components

```python
# API Client
from streamlit_components.core import api_client, APIError

data = api_client.get("/endpoint")
result = api_client.post("/endpoint", data={...})
result = api_client.patch("/endpoint/{id}", data={...})
api_client.delete("/endpoint/{id}")

# Authentication
from streamlit_components.core import auth

auth.require_auth()  # Require login
auth.require_role("ADMIN")  # Require specific role
if auth.is_admin():  # Check role
    ...
auth.show_user_info()  # Display in sidebar
```

### Layout Components

```python
# Page Header
from streamlit_components.layouts import PageHeader

header = PageHeader(
    title="Page Title",
    subtitle="Description",
    breadcrumbs=["Home", "Section"]
)
header.render()

# Card
from streamlit_components.layouts import Card

card = Card(title="Content", card_id="main_card")
with card.container():
    st.write("Content here")
card.close_container()

# Section
from streamlit_components.layouts import Section, Divider

section = Section("Section Title", description="Description")
section.render()

Divider.horizontal()
```

### Feedback Components

```python
# Success
from streamlit_components.feedback import Success

Success.message("Operation successful!")
Success.toast("Saved!")

# Error
from streamlit_components.feedback import Error

Error.message("Operation failed")
try:
    api_client.post("/endpoint", data={...})
except APIError as e:
    Error.api_error(e, show_details=True)

# Loading
from streamlit_components.feedback import Loading

with Loading.spinner("Processing..."):
    # Long operation
    process_data()
```

---

## 🎓 Best Practices Summary

### 1. Always Follow the Pattern
- ✅ Same structure every time
- ✅ Same naming conventions
- ✅ Same component usage

### 2. Modularize Appropriately
- ✅ Helpers for API functions
- ✅ Workflow/screens for distinct steps
- ✅ Main file for orchestration only

### 3. Component Library First
- ✅ Use api_client for ALL API calls
- ✅ Use auth for ALL auth checks
- ✅ Use feedback components consistently

### 4. E2E Testing Mindset
- ✅ Add keys to EVERYTHING interactive
- ✅ Follow naming conventions
- ✅ Write tests DURING refactoring

### 5. Document Everything
- ✅ Docstrings for all functions
- ✅ Type hints for all parameters
- ✅ Markdown docs for refactoring
- ✅ Test documentation

---

## 🔄 Next File Refactoring Template

When starting a new refactoring, use this checklist:

```markdown
# {Filename} Refactoring

## Before
- Lines: {count}
- Functions: {count}
- API calls: {count}

## Plan
1. Create {filename}_helpers.py ({target} lines)
2. Create {filename}_workflow.py ({target} lines, if needed)
3. Refactor main file to {target} lines
4. Add {target}+ data-testid selectors
5. Create tests/e2e/test_{filename}.py
6. Document in {FILENAME}_REFACTORING_COMPLETE.md

## Checkpoints
- [ ] Git tag created: pre-refactor-{filename}
- [ ] Helpers created
- [ ] Workflow created (if applicable)
- [ ] Main file refactored
- [ ] Selectors added
- [ ] Tests created
- [ ] Documentation complete
- [ ] Git commit with summary
```

---

**This is the canonical reference. Follow this pattern for ALL Streamlit UI refactoring.**

---

**Created by**: Claude Code
**Date**: 2026-01-30
**Version**: 1.0
**Status**: ✅ **ESTABLISHED**
**Based on**: Sandbox refactoring (65% reduction, 100% success)
