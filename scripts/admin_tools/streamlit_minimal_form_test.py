"""
Minimal Streamlit Form Test Application

Purpose: Isolate and test form button behavior in the simplest possible context.

Test Scenarios:
1. Plain st.button() without form
2. st.form() + st.form_submit_button()
3. Handler execution verification
4. Playwright automation compatibility

Run: streamlit run streamlit_minimal_form_test.py --server.port 8502
"""

import streamlit as st
import time
from datetime import datetime

# ============================================================================
# TEST 1: Plain Button (No Form)
# ============================================================================

st.title("🧪 Streamlit Form Button Test Suite")
st.markdown("---")

st.header("Test 1: Plain st.button() (No Form)")
st.write("This tests standard button without form wrapper.")

# Counter to track clicks
if "plain_button_clicks" not in st.session_state:
    st.session_state.plain_button_clicks = 0

plain_button_clicked = st.button(
    "Plain Button - Click Me",
    key="btn_plain",
    type="primary"
)

if plain_button_clicked:
    st.session_state.plain_button_clicks += 1
    st.success(f"✅ Plain button clicked! Total clicks: {st.session_state.plain_button_clicks}")
    st.write(f"⏰ Timestamp: {datetime.now().strftime('%H:%M:%S.%f')}")
else:
    st.info(f"ℹ️ Plain button click count: {st.session_state.plain_button_clicks}")

st.markdown("---")

# ============================================================================
# TEST 2: Form Button
# ============================================================================

st.header("Test 2: st.form() + st.form_submit_button()")
st.write("This tests button wrapped in form context.")

# Counter to track form submissions
if "form_button_clicks" not in st.session_state:
    st.session_state.form_button_clicks = 0

with st.form(key="test_form", clear_on_submit=False):
    st.write("Form content area")
    st.text_input("Sample Input", key="form_input")

    form_submitted = st.form_submit_button(
        "Form Button - Click Me",
        type="primary"
    )

# Handler OUTSIDE form block (correct pattern)
if form_submitted:
    st.session_state.form_button_clicks += 1
    st.success(f"✅ Form button clicked! Total submissions: {st.session_state.form_button_clicks}")
    st.write(f"⏰ Timestamp: {datetime.now().strftime('%H:%M:%S.%f')}")
    st.write(f"📝 Input value: {st.session_state.form_input}")
else:
    st.info(f"ℹ️ Form submission count: {st.session_state.form_button_clicks}")

st.markdown("---")

# ============================================================================
# TEST 3: Debug State Display
# ============================================================================

st.header("Test 3: Debug State Display")
st.write("This shows whether handler code is executing.")

# Track if this code section runs
if "debug_render_count" not in st.session_state:
    st.session_state.debug_render_count = 0

st.session_state.debug_render_count += 1

st.write("**Script Execution Metrics:**")
st.write(f"- Total script runs: {st.session_state.debug_render_count}")
st.write(f"- Plain button variable value: `{plain_button_clicked}`")
st.write(f"- Form button variable value: `{form_submitted}`")

st.markdown("---")

# ============================================================================
# TEST 4: Complex Form with Multiple Fields
# ============================================================================

st.header("Test 4: Complex Form (Multiple Fields)")
st.write("This tests form with multiple inputs to simulate real workflow.")

if "complex_form_submissions" not in st.session_state:
    st.session_state.complex_form_submissions = []

with st.form(key="complex_test_form", clear_on_submit=False):
    name = st.text_input("Name", key="complex_name")
    age = st.number_input("Age", min_value=0, max_value=120, key="complex_age")
    option = st.selectbox("Option", ["A", "B", "C"], key="complex_option")

    complex_submitted = st.form_submit_button(
        "Submit Complex Form",
        type="primary"
    )

if complex_submitted:
    submission_data = {
        "timestamp": datetime.now().strftime('%H:%M:%S'),
        "name": st.session_state.complex_name,
        "age": st.session_state.complex_age,
        "option": st.session_state.complex_option,
    }
    st.session_state.complex_form_submissions.append(submission_data)
    st.success(f"✅ Complex form submitted! Total: {len(st.session_state.complex_form_submissions)}")
    st.json(submission_data)
else:
    st.info(f"ℹ️ Complex form submissions: {len(st.session_state.complex_form_submissions)}")

# Show submission history
if st.session_state.complex_form_submissions:
    with st.expander("📊 Submission History"):
        for i, sub in enumerate(st.session_state.complex_form_submissions, 1):
            st.write(f"**Submission {i}:**")
            st.json(sub)

st.markdown("---")

# ============================================================================
# TEST 5: Form in Column Layout
# ============================================================================

st.header("Test 5: Form in Column Layout")
st.write("This tests form button inside column context (similar to production code).")

if "column_form_clicks" not in st.session_state:
    st.session_state.column_form_clicks = 0

col1, col2 = st.columns(2)

with col1:
    st.write("**Left Column**")
    if st.button("Regular Button in Column", key="col_regular"):
        st.success("Regular button in column clicked!")

with col2:
    st.write("**Right Column**")
    with st.form(key="column_form", clear_on_submit=False):
        column_form_submitted = st.form_submit_button(
            "Form Button in Column",
            type="primary"
        )

# Handler AFTER columns close
if column_form_submitted:
    st.session_state.column_form_clicks += 1
    st.success(f"✅ Form button in column clicked! Total: {st.session_state.column_form_clicks}")
else:
    st.info(f"ℹ️ Column form clicks: {st.session_state.column_form_clicks}")

st.markdown("---")

# ============================================================================
# TEST 6: API Simulation
# ============================================================================

st.header("Test 6: Form with Simulated API Call")
st.write("This simulates the production pattern: form → API call → state update.")

if "api_calls" not in st.session_state:
    st.session_state.api_calls = []

with st.form(key="api_simulation_form", clear_on_submit=False):
    api_input = st.text_input("API Input Data", key="api_input")
    api_submitted = st.form_submit_button("Submit to API", type="primary")

if api_submitted:
    # Simulate API call
    st.write("🔄 Simulating API call...")
    time.sleep(0.5)  # Simulate network delay

    # Simulate API response
    api_response = {
        "status": "success",
        "data": st.session_state.api_input,
        "timestamp": datetime.now().isoformat(),
        "id": len(st.session_state.api_calls) + 1
    }

    st.session_state.api_calls.append(api_response)
    st.success(f"✅ API call successful! Response ID: {api_response['id']}")
    st.json(api_response)
else:
    st.info(f"ℹ️ Total API calls: {len(st.session_state.api_calls)}")

if st.session_state.api_calls:
    with st.expander("📡 API Call History"):
        for call in st.session_state.api_calls:
            st.json(call)

st.markdown("---")

# ============================================================================
# TEST RESULTS SUMMARY
# ============================================================================

st.header("📊 Test Results Summary")

summary_data = {
    "Plain Button Clicks": st.session_state.plain_button_clicks,
    "Form Button Clicks": st.session_state.form_button_clicks,
    "Complex Form Submissions": len(st.session_state.complex_form_submissions),
    "Column Form Clicks": st.session_state.column_form_clicks,
    "API Simulation Calls": len(st.session_state.api_calls),
    "Total Script Runs": st.session_state.debug_render_count,
}

for test_name, count in summary_data.items():
    st.metric(test_name, count)

# Visual indicator for handler execution
st.markdown("---")
st.markdown("### 🔍 Handler Execution Test")
st.write("If you see this section, the script is running.")
st.write("If counters increment after button clicks, handlers are executing.")
st.write("If counters DON'T increment, handlers are NOT executing.")

if sum([
    st.session_state.plain_button_clicks,
    st.session_state.form_button_clicks,
    len(st.session_state.complex_form_submissions),
    st.session_state.column_form_clicks,
    len(st.session_state.api_calls)
]) > 0:
    st.success("✅ At least one handler has executed successfully!")
else:
    st.warning("⚠️ No handlers have executed yet. Try clicking buttons above.")
