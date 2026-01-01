"""
My Credits - Student Credit Management Page
Purchase credits, view transaction history, track invoices
"""

import streamlit as st
from datetime import datetime
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY
from api_helpers_general import get_current_user, get_credit_transactions, get_my_invoices
from components.credits.credit_purchase_form import render_credit_purchase_form

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - My Credits",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Authentication check
if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("Not authenticated. Please login first.")
    st.stop()

# Check student role
user = st.session_state[SESSION_USER_KEY]
if user.get('role') != 'student':
    st.error("Access denied. Student role required.")
    st.stop()

# Get token
token = st.session_state[SESSION_TOKEN_KEY]

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Student')}!")
    st.caption(f"Role: **Student**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    # Credits display
    st.markdown("**Credit Balance**")
    st.metric("Current Balance", user.get('credit_balance', 0))
    st.caption(f"Purchased: {user.get('credit_purchased', 0)}")

    st.markdown("---")

    # Logout and Refresh buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True, help="Reload credit data"):
            # Refresh user data from API
            from api_helpers_general import get_current_user
            success, error, updated_user = get_current_user(token)
            if success:
                st.session_state[SESSION_USER_KEY] = updated_user
            st.rerun()
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("🏠_Home.py")

# Header
st.title("My Credits")
st.caption("Manage your credits, view history, and track invoices")

# Main tabs
tab1, tab2, tab3 = st.tabs(["Purchase Credits", "Transaction History", "My Invoices"])

# ========================================
# TAB 1: PURCHASE CREDITS
# ========================================
with tab1:
    st.markdown("### Purchase Credits")
    st.caption("Select a package and request an invoice for payment")

    # Show current balance
    st.info(f"**Current Balance:** {user.get('credit_balance', 0)} credits")

    # Reuse existing credit purchase form component
    render_credit_purchase_form(token)

# ========================================
# TAB 2: TRANSACTION HISTORY
# ========================================
with tab2:
    st.markdown("### Transaction History")
    st.caption("All credit purchases, uses, and adjustments")

    # Fetch transactions
    success, data = get_credit_transactions(token, limit=50, offset=0)

    if success and data:
        transactions = data.get('transactions', [])
        total_count = data.get('total_count', 0)

        st.metric("Total Transactions", total_count)
        st.divider()

        if transactions:
            # Table header
            h1, h2, h3, h4 = st.columns([2, 3, 2, 2])
            with h1:
                st.markdown("**Date**")
            with h2:
                st.markdown("**Description**")
            with h3:
                st.markdown("**Amount**")
            with h4:
                st.markdown("**Type**")

            st.divider()

            # Transaction rows
            for txn in transactions:
                c1, c2, c3, c4 = st.columns([2, 3, 2, 2])

                with c1:
                    date_str = txn.get('created_at', 'N/A')
                    # Format date
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        st.markdown(f"**{dt.strftime('%Y-%m-%d')}**")
                        st.caption(dt.strftime('%H:%M'))
                    except:
                        st.caption(date_str)

                with c2:
                    st.markdown(txn.get('description', 'N/A'))

                with c3:
                    amount = txn.get('amount', 0)
                    color = "" if amount > 0 else ""
                    sign = "+" if amount > 0 else ""
                    st.markdown(f"{color} **{sign}{amount}**")

                with c4:
                    txn_type = txn.get('transaction_type', 'N/A')
                    st.caption(txn_type.upper())

                st.divider()

            # Pagination
            if total_count > 50:
                if st.button("Load More...", use_container_width=True):
                    # TODO: Implement pagination logic
                    st.info("Pagination coming soon")
        else:
            st.info("No transactions found")
    else:
        st.warning("Failed to load transaction history")

# ========================================
# TAB 3: MY INVOICES
# ========================================
with tab3:
    st.markdown("### My Invoices")
    st.caption("Track your credit purchase requests")

    # Fetch user's invoices
    success, invoices = get_my_invoices(token)

    if success and invoices:
        for inv in invoices:
            status = inv.get('status', 'pending')

            # Status emoji
            if status == 'verified':
                emoji = ""
                status_text = "VERIFIED"
            elif status == 'cancelled':
                emoji = ""
                status_text = "CANCELLED"
            else:
                emoji = ""
                status_text = "PENDING"

            with st.expander(f"{emoji} Invoice #{inv.get('id')} - {status_text}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Amount", f"€{inv.get('amount_eur', 0):.2f}")
                    st.caption(f"{inv.get('credit_amount', 0)} credits")

                with col2:
                    st.markdown(f"**Payment Reference:**")
                    st.code(inv.get('payment_reference', 'N/A'))

                with col3:
                    created_at = inv.get('created_at', 'N/A')
                    st.markdown(f"**Created:**")
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        st.caption(dt.strftime('%Y-%m-%d %H:%M'))
                    except:
                        st.caption(created_at)

                    if status == 'verified':
                        verified_at = inv.get('verified_at', 'N/A')
                        st.markdown(f"**Verified:**")
                        try:
                            dt = datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                            st.caption(dt.strftime('%Y-%m-%d %H:%M'))
                        except:
                            st.caption(verified_at)
    elif success:
        st.info("No invoices found")
    else:
        st.warning("Failed to load invoices - endpoint may not exist yet")

# Footer Navigation
st.divider()
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    if st.button("🏠 Back to Hub", use_container_width=True):
        # Navigate to appropriate dashboard based on specialization
        specialization = user.get('specialization')
        if specialization == 'LFA_FOOTBALL_PLAYER':
            st.switch_page("pages/LFA_Player_Dashboard.py")
        elif specialization in ['LFA_COACH', 'LFA_INTERNSHIP']:
            st.switch_page("pages/Specialization_Hub.py")
        else:
            # Fallback to generic hub
            st.switch_page("pages/Specialization_Hub.py")

with footer_col2:
    if st.button("👤 Profile", use_container_width=True):
        st.switch_page("pages/My_Profile.py")

with footer_col3:
    if st.button("💳 Credits", disabled=True, use_container_width=True):
        pass  # Already on credits page
