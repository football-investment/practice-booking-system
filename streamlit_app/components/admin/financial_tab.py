"""
Admin Dashboard - Financial Tab Component
Financial management with coupons, invoices, and invitation codes
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Financial components (modular)
from components.financial.coupon_management import render_coupon_management
from components.financial.invoice_management import render_invoice_management
from components.financial.invitation_management import render_invitation_management


def render_financial_tab(token, user):
    """
    Render the Financial tab with financial management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    st.markdown("### 💳 Financial Management")
    st.caption("Manage coupons, invoices, and invitation codes")

    # Sub-tabs for financial sections
    financial_tab1, financial_tab2, financial_tab3 = st.tabs([
        "🎫 Coupons",
        "🧾 Invoices",
        "🎟️ Invitation Codes"
    ])

    # ========================================
    # COUPONS SUB-TAB
    # ========================================
    with financial_tab1:
        render_coupon_management(token)

    # ========================================
    # INVOICES SUB-TAB
    # ========================================
    with financial_tab2:
        render_invoice_management(token)

    # ========================================
    # INVITATION CODES SUB-TAB
    # ========================================
    with financial_tab3:
        render_invitation_management(token)
