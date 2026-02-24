"""
LFA Education Center - Streamlit Home Page

Minimal entry point for Streamlit multi-page app.
Actual pages are in streamlit_app/pages/ directory.
"""
import streamlit as st

st.set_page_config(
    page_title="LFA Education Center",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚽ LFA Education Center")
st.markdown("Welcome to the LFA Education Center platform.")

st.info("Please use the sidebar to navigate to specific pages (Admin Dashboard, Student Portal, etc.)")

# Sidebar navigation hint
with st.sidebar:
    st.markdown("### Navigation")
    st.markdown("Select a page from the sidebar above to get started.")
