# Minimal Form Test Results - Critical Finding

**Date:** 2026-02-05 21:00 CET
**Test App:** streamlit_minimal_form_test.py (port 8502)
**Conclusion:** ✅ **Streamlit form buttons work reliably in Playwright - NOT a platform limit**

---

## Executive Summary

After creating a minimal isolated test application and running comprehensive Playwright E2E tests, we have **definitively proven** that:

1. ✅ **Streamlit buttons work in headless Playwright**
2. ✅ **st.form() + st.form_submit_button() pattern works reliably**
3. ✅ **Form buttons work in column layouts**
4. ✅ **Forms work with API call simulations**
5. ✅ **Multiple sequential button clicks all work**

**Test Results:** **5/5 tests PASSED** (100% success rate)

**Critical Conclusion:** The problem in the production code is **NOT** a Streamlit platform limitation. It is a **specific implementation issue** in the production `sandbox_workflow.py` code.

---

## Test Results

### Test 1: Plain st.button()

```python
plain_button_clicked = st.button("Plain Button - Click Me", key="btn_plain", type="primary")

if plain_button_clicked:
    st.session_state.plain_button_clicks += 1
    st.success(f"✅ Plain button clicked! Total clicks: {st.session_state.plain_button_clicks}")
```

**Playwright Test:**
```
Initial state: ℹ️ Plain button click count: 0
Clicking plain button...
✅ PASS: Plain button handler executed
PASSED in 3.61s
```

**Result:** ✅ **PASS** - Handler executes, counter increments

---

### Test 2: Form Button

```python
with st.form(key="test_form", clear_on_submit=False):
    st.write("Form content area")
    form_submitted = st.form_submit_button("Form Button - Click Me", type="primary")

# Handler OUTSIDE form block
if form_submitted:
    st.session_state.form_button_clicks += 1
    st.success(f"✅ Form button clicked! Total submissions: {st.session_state.form_button_clicks}")
```

**Playwright Test:**
```
Initial state: ℹ️ Form submission count: 0
Clicking form button...
✅ PASS: Form button handler executed
PASSED in 3.13s
```

**Result:** ✅ **PASS** - Handler executes, counter increments

---

### Test 3: Complex Form (Multiple Fields)

```python
with st.form(key="complex_test_form", clear_on_submit=False):
    name = st.text_input("Name", key="complex_name")
    age = st.number_input("Age", min_value=0, max_value=120, key="complex_age")
    option = st.selectbox("Option", ["A", "B", "C"], key="complex_option")
    complex_submitted = st.form_submit_button("Submit Complex Form", type="primary")

if complex_submitted:
    submission_data = {
        "timestamp": datetime.now().strftime('%H:%M:%S'),
        "name": st.session_state.complex_name,
        "age": st.session_state.complex_age,
        "option": st.session_state.complex_option,
    }
    st.session_state.complex_form_submissions.append(submission_data)
    st.success(f"✅ Complex form submitted!")
```

**Playwright Test:**
```
Filled name field: Test User
Filled age field: 25
Clicking complex form submit button...
✅ PASS: Complex form handler executed
PASSED
```

**Result:** ✅ **PASS** - Form data captured, handler executes

---

### Test 4: Form in Column Layout

```python
col1, col2 = st.columns(2)

with col1:
    if st.button("Regular Button in Column", key="col_regular"):
        st.success("Regular button in column clicked!")

with col2:
    with st.form(key="column_form", clear_on_submit=False):
        column_form_submitted = st.form_submit_button("Form Button in Column", type="primary")

# Handler AFTER columns close
if column_form_submitted:
    st.session_state.column_form_clicks += 1
    st.success(f"✅ Form button in column clicked! Total: {st.session_state.column_form_clicks}")
```

**Playwright Test:**
```
Clicking form button in column...
✅ PASS: Column form handler executed
PASSED
```

**Result:** ✅ **PASS** - Form button in column works

---

### Test 5: Form with Simulated API Call

```python
with st.form(key="api_simulation_form", clear_on_submit=False):
    api_input = st.text_input("API Input Data", key="api_input")
    api_submitted = st.form_submit_button("Submit to API", type="primary")

if api_submitted:
    st.write("🔄 Simulating API call...")
    time.sleep(0.5)  # Simulate network delay

    api_response = {
        "status": "success",
        "data": st.session_state.api_input,
        "timestamp": datetime.now().isoformat(),
        "id": len(st.session_state.api_calls) + 1
    }

    st.session_state.api_calls.append(api_response)
    st.success(f"✅ API call successful! Response ID: {api_response['id']}")
```

**Playwright Test:**
```
Filled API input: test_data_123
Clicking API submit button...
✅ PASS: API simulation handler executed
PASSED
```

**Result:** ✅ **PASS** - Form with API simulation works

---

### Test 6: Full Suite (Sequential Clicks)

**Test:** Click all 5 button types in sequence in a single test run

**Playwright Test:**
```
1. Testing plain button...
   Result: ✅ PASS

2. Testing form button...
   Result: ✅ PASS

3. Testing complex form...
   Result: ✅ PASS

4. Testing column form...
   Result: ✅ PASS

5. Testing API simulation...
   Result: ✅ PASS

Total: 5/5 tests passed
✅ ALL TESTS PASSED
```

**Result:** ✅ **PASS** - All buttons work in sequence

---

## Comparison: Minimal App vs Production Code

### What WORKS (Minimal App)

| Feature | Implementation | Playwright Result |
|---------|---------------|-------------------|
| Plain button | `st.button()` | ✅ PASS |
| Form button | `st.form()` + `st.form_submit_button()` | ✅ PASS |
| Form in columns | `with col2: with st.form():` | ✅ PASS |
| API simulation | `if submitted: api_call()` | ✅ PASS |
| Multiple fields | Complex form with 3 inputs | ✅ PASS |

### What FAILS (Production Code)

| Feature | File | Playwright Result |
|---------|------|-------------------|
| Create Tournament button | `sandbox_workflow.py:163` | ❌ FAIL |
| Form in columns | `with col2: with st.form():` | ❌ FAIL |

**Same pattern, different results!**

---

## Key Differences: Minimal vs Production

### Minimal App (WORKS)

```python
# Clean, simple structure
with st.form(key="column_form", clear_on_submit=False):
    column_form_submitted = st.form_submit_button("Form Button in Column", type="primary")

# Handler immediately after form
if column_form_submitted:
    st.session_state.column_form_clicks += 1
    st.success(f"✅ Form button in column clicked!")
```

**Characteristics:**
- ✅ No complex component wrappers
- ✅ Direct form → handler flow
- ✅ Minimal session state usage
- ✅ Simple success messages
- ✅ No API client abstractions

---

### Production Code (FAILS)

```python
# sandbox_workflow.py:160-171
with col2:
    with st.form(key="form_create_tournament", clear_on_submit=False):
        create_clicked = st.form_submit_button("Create Tournament", type="primary", use_container_width=True)

# Handler after columns close
# 🔍 DEBUG: create_clicked = {create_clicked}  # Line 172 - NEVER RENDERS
st.write(f"🔍 DEBUG: create_clicked = {create_clicked}")

if create_clicked:
    # Line 174+ - NEVER EXECUTES
    st.warning("🚀 DEBUG: Form submitted!")
    with Loading.spinner("Creating tournament..."):
        ...
```

**Characteristics:**
- ❌ Complex component wrappers (`Card`, `Loading`)
- ❌ Large session state config dict
- ❌ Heavy API orchestration (`/api/v1/sandbox/run-test`)
- ❌ Debug messages don't render (line 172)
- ❌ Handler never executes (line 174+)

---

## Hypothesis: What's Blocking the Production Code?

### Potential Issues Identified

1. **Card Component Context Corruption**
   ```python
   # Line 144: sandbox_workflow.py
   card.close_container()  # ← Might corrupt Streamlit context
   ```

   **Evidence:**
   - Debug message at line 172 (`st.write(f"🔍 DEBUG: create_clicked = ...")`) **never renders**
   - This suggests code execution stops OR context is invalid AFTER line 169 (form closes)

2. **Column Context Not Properly Closed**
   ```python
   with col2:
       with st.form(...):
           button = st.form_submit_button(...)

   # Handler here - is col2 context still active?
   if button:  # ← May not execute if context broken
       ...
   ```

3. **Session State Config Size**
   - Production config dict is ~50 fields
   - Minimal test config is 0-3 fields
   - Possible serialization/state corruption issue?

4. **Import/Module Scope Issue**
   - `sandbox_workflow.py` is imported in function scope (line 1038)
   - Minimal test is standalone script
   - Possible Python scoping affecting form state?

---

## Evidence: Debug Messages Don't Render

### Minimal App Debug

```python
# streamlit_minimal_form_test.py:129
st.write("**Script Execution Metrics:**")
st.write(f"- Total script runs: {st.session_state.debug_render_count}")
st.write(f"- Plain button variable value: `{plain_button_clicked}`")
st.write(f"- Form button variable value: `{form_submitted}`")
```

**Playwright page content shows:**
```
**Script Execution Metrics:**
- Total script runs: 5
- Plain button variable value: `False`  # Shows even when False
- Form button variable value: `False`   # Shows even when False
```

**Result:** ✅ Debug messages ALWAYS render

---

### Production Code Debug

```python
# sandbox_workflow.py:172
st.write(f"🔍 DEBUG: create_clicked = {create_clicked}")

# sandbox_workflow.py:175
if create_clicked:
    st.warning("🚀 DEBUG: Form submitted!")
```

**Playwright page content shows:**
```
(nothing - debug messages don't appear)
```

**Result:** ❌ Debug messages NEVER render

**Critical Finding:** Code after line 169 (form closes) either:
1. Does NOT execute at all
2. OR executes but output is suppressed/lost

---

## Recommended Next Steps

### Step 1: Isolate Card Component

**Action:** Remove `Card` wrapper from production code temporarily

```python
# BEFORE (sandbox_workflow.py:33-144)
card = Card(title="Tournament Configuration Preview", card_id="config_preview")
with card.container():
    # ... preview content ...
card.close_container()

# AFTER (test without Card)
st.subheader("Tournament Configuration Preview")
# ... preview content directly ...
# (no card.close_container() call)
```

**Test:** Does form button work without Card wrapper?

---

### Step 2: Add Explicit Flush

**Action:** Force Streamlit to flush output before form

```python
# Before form block
st.markdown("---")
st.empty()  # Force context flush

with st.form(...):
    ...
```

---

### Step 3: Move Form Outside Columns

**Action:** Test if column context is the issue

```python
# BEFORE
col1, col2 = st.columns(2)
with col2:
    with st.form(...):
        button = st.form_submit_button(...)

# AFTER
col1, col2 = st.columns(2)
# ... columns content ...

# Form AFTER columns close
with st.form(...):
    button = st.form_submit_button(...)
```

---

### Step 4: Simplify Config Object

**Action:** Test with minimal config (like minimal app)

```python
# BEFORE
config = {
    'tournament_name': ...,
    'tournament_format': ...,
    'scoring_mode': ...,
    # ... 50 fields ...
}

# AFTER (test minimal)
config = {
    'tournament_name': 'Test',
    'tournament_format': 'GROUP_KNOCKOUT',
}
```

---

## Conclusion

**The Streamlit platform is NOT the problem.**

The minimal test app proves that:
- ✅ Form buttons work reliably in Playwright
- ✅ Forms work in column layouts
- ✅ Forms work with API calls
- ✅ Multiple sequential clicks all work

**The production code has a specific implementation issue**, likely one of:

1. **Card component context corruption** (line 144: `card.close_container()`)
2. **Column context not properly closed before handler**
3. **Session state config object too large/complex**
4. **Import scope issue with function-level imports**

**Next Action:** Systematically test each hypothesis by modifying production code to match minimal app patterns.

---

## Test Files

- **Minimal App:** `streamlit_minimal_form_test.py`
- **Test Suite:** `tests/e2e_frontend/test_minimal_form.py`
- **Results:** 5/5 PASS (100% success rate)
- **Execution Time:** 11.90 seconds (all tests)

**Reproducibility:** 100% - Can run `pytest tests/e2e_frontend/test_minimal_form.py -v -s` anytime to verify.
