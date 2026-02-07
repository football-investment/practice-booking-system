# Import Shadowing Validation - Evidence Report

**Date:** 2026-02-05 20:49 CET
**Validation Method:** Visual marker injection + headless E2E test
**Result:** ✅ **CONFIRMED** - Import shadowing bug validated with 100% certainty

---

## Hypothesis

The application has TWO implementations of `render_step_create_tournament()`:
1. **streamlit_sandbox_workflow_steps.py** - Imported at line 34 (module-level)
2. **sandbox_workflow.py** - Imported at line 1038 (function-level, SHADOWS line 34)

**Predicted behavior:** sandbox_workflow.py executes due to Python's local scope shadowing.

---

## Validation Method

### Step 1: Inject Unique Visual Markers

**File: streamlit_sandbox_workflow_steps.py (line 75)**
```python
def render_step_create_tournament(config: Dict[str, Any]):
    """Step 1: Create Tournament"""
    st.title("Step 1: Create Tournament")

    # 🔵 VALIDATION MARKER: streamlit_sandbox_workflow_steps.py IS EXECUTING
    st.info("🔵 **VALIDATION**: Using `streamlit_sandbox_workflow_steps.py` implementation")
```

**File: sandbox_workflow.py (line 31)**
```python
def render_step_create_tournament(config: Dict):
    """Step 1: Create tournament with configuration"""
    st.markdown("### 1. Create Tournament")

    # 🟠 VALIDATION MARKER: sandbox_workflow.py IS EXECUTING
    st.warning("🟠 **VALIDATION**: Using `sandbox_workflow.py` implementation")
```

### Step 2: Run Headless E2E Test

**Command:**
```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
pytest tests/e2e_frontend/test_group_knockout_7_players.py::test_group_knockout_7_players_golden_path_ui -v -s
```

**Test navigates to Step 1 and captures page content.**

---

## Evidence: Page Content Captured by Test

```
Page content:
Sandbox Controls

Workflow: Step 1/6

Refresh Page

Back to Home

Quick Tips:

Refresh Page: reload current step
Back to Home: return to start

Sandbox v3 | Screen: instructor_workflow

keyboard_double_arrow_right
Deploy
Step 1 of 6
1. Create Tournament

🟠 VALIDATION: Using sandbox_workflow.py implementation
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tournament Configuration Preview
📋 Basic Information

Tournament Name

LFA Sandbox Tournament
...
```

---

## Conclusion

**✅ CONFIRMED: `sandbox_workflow.py` is executing, NOT `streamlit_sandbox_workflow_steps.py`**

**Evidence:**
- Page shows: `🟠 VALIDATION: Using sandbox_workflow.py implementation`
- Expected if streamlit_sandbox_workflow_steps.py ran: `🔵 VALIDATION: Using streamlit_sandbox_workflow_steps.py implementation`

**Root cause validated:**
- The import at line 1038 (inside `render_instructor_workflow()`) shadows the import at line 34
- Python's local scope takes precedence
- All modifications to streamlit_sandbox_workflow_steps.py (including st.form() pattern) are invisible

**Impact:**
- The st.form() pattern we implemented is in the UNUSED file
- The ACTIVE implementation (sandbox_workflow.py) still uses plain st.button()
- This explains why button clicks are unreliable (no form wrapper)

---

## Next Steps

1. ✅ **Evidence documented**
2. ⏭️ **Execute minimal fix:**
   - Remove import shadowing at line 1038
   - Update line 34 to import from sandbox_workflow
   - Add st.form() to sandbox_workflow.py (the ACTIVE file)
3. ⏭️ **Re-test and validate fix**

---

## Files Affected

- `streamlit_sandbox_v3_admin_aligned.py:34` - Module-level import (unused)
- `streamlit_sandbox_v3_admin_aligned.py:1038` - Function-level import (active, shadows line 34)
- `streamlit_sandbox_workflow_steps.py` - Contains st.form() but never executes
- `sandbox_workflow.py` - Actually executes, needs st.form() added
