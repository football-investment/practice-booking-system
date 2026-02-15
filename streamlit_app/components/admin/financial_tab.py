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
from api_helpers_financial import get_financial_summary


def _render_financial_kpi(token):
    """Render the top-level financial KPI summary bar."""
    ok, data = get_financial_summary(token)

    st.markdown("#### 📊 Pénzügyi összesítő")
    if not ok or not data:
        st.warning("Nem sikerült betölteni a pénzügyi adatokat.")
        return

    rev  = data.get("revenue",  {})
    cred = data.get("credits",  {})
    inv  = data.get("invoices", {})

    # ── Row 1: Revenue & credits ──────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="💶 Összbevétel",
            value=f"€{rev.get('total_eur', 0):,.2f}",
            help="Összes jóváhagyott invoice EUR összege",
        )
    with c2:
        st.metric(
            label="⏳ Függőben lévő befizetés",
            value=f"€{rev.get('pending_eur', 0):,.2f}",
            help="Jóváhagyásra váró invoicok EUR összege",
        )
    with c3:
        st.metric(
            label="🪙 Kiadott kreditek",
            value=f"{rev.get('total_credits_sold', 0):,} cr",
            help="Összes jóváhagyott invoice kredit összege",
        )
    with c4:
        st.metric(
            label="💼 Aktív kreditállomány",
            value=f"{cred.get('active_balance', 0):,} cr",
            help="Aktív userek credit_balance összege",
        )

    # ── Row 2: Invoice counts ─────────────────────────────────────
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("🧾 Összes invoice", inv.get("total", 0))
    with c6:
        pending = inv.get("pending", 0)
        st.metric(
            label="⏳ Jóváhagyásra vár",
            value=pending,
            delta=f"−{pending}" if pending else None,
            delta_color="inverse",
        )
    with c7:
        st.metric("✅ Jóváhagyott", inv.get("verified", 0))
    with c8:
        st.metric(
            label="👥 Kredittel rendelkező userek",
            value=cred.get("users_with_balance", 0),
        )

    st.divider()


def render_financial_tab(token, user):
    """
    Render the Financial tab with financial management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    st.markdown("### 💳 Financial Management")
    st.caption("Manage coupons, invoices, and invitation codes")

    # ── Financial KPI summary (always visible, auto-refreshes on rerun) ──
    _render_financial_kpi(token)

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
