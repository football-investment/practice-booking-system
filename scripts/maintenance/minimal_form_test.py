"""
Minimal reproduction: Streamlit form_submit_button + Playwright click

Tests whether Playwright .click() properly triggers st.form_submit_button callback.
"""

import streamlit as st
import time

st.title("Minimal Form Submit Test")

# Display current state
st.write(f"**Current counter:** {st.session_state.get('counter', 0)}")
st.write(f"**Last submit time:** {st.session_state.get('last_submit', 'Never')}")

# Simple form with submit button
with st.form(key="test_form"):
    st.write("Click the button below:")
    submitted = st.form_submit_button("Submit Test", type="primary")

if submitted:
    # This should execute when button is clicked
    st.session_state.counter = st.session_state.get('counter', 0) + 1
    st.session_state.last_submit = time.strftime("%H:%M:%S")
    st.success(f"✅ Form submitted! Counter: {st.session_state.counter}")
    st.rerun()
