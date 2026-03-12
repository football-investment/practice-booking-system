"""
Invoice Management Component
Handles invoice display, filtering, sorting, and verification
"""

import streamlit as st
from datetime import datetime
from api_helpers_financial import get_invoices, verify_invoice, unverify_invoice, cancel_invoice


def render_invoice_management(token: str):
    """Render the invoice management interface"""
    st.markdown("### 🧾 Invoice Management")
    st.caption("View and verify invoice requests")

    # Status filter, sort, and refresh
    col_filter, col_sort, col_refresh = st.columns([3, 3, 1])
    with col_filter:
        status_filter = st.selectbox("Filter by Status", ["all", "pending", "verified", "cancelled"], key="invoice_status_filter")
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Submitted (newest)", "Submitted (oldest)", "Student Name (A-Z)", "Amount (high-low)", "Amount (low-high)", "Verified (newest)"], key="invoice_sort")
    with col_refresh:
        st.write("")  # spacing
        if st.button("🔄", key="refresh_invoices"):
            st.rerun()

    # Get invoices
    filter_val = None if status_filter == "all" else status_filter
    success, invoices = get_invoices(token, status_filter=filter_val)

    if success and invoices:
        # Sort invoices based on selection
        if sort_by == "Submitted (newest)":
            invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_by == "Submitted (oldest)":
            invoices.sort(key=lambda x: x.get('created_at', ''))
        elif sort_by == "Student Name (A-Z)":
            invoices.sort(key=lambda x: x.get('student_name', '').lower())
        elif sort_by == "Amount (high-low)":
            invoices.sort(key=lambda x: x.get('amount_eur', 0), reverse=True)
        elif sort_by == "Amount (low-high)":
            invoices.sort(key=lambda x: x.get('amount_eur', 0))
        elif sort_by == "Verified (newest)":
            # Put verified first, then sort by verified_at
            invoices.sort(key=lambda x: (x.get('verified_at') is None, x.get('verified_at', '') or ''), reverse=True)

        st.metric("Total Invoices", len(invoices))

        # TABLE HEADER
        h1, h2, h3, h4, h5, h6 = st.columns([2, 1.5, 1, 1.5, 1.5, 2])
        with h1:
            st.markdown("**👤 Student**")
        with h2:
            st.markdown("**💶 Amount**")
        with h3:
            st.markdown("**📊 Status**")
        with h4:
            st.markdown("**🕐 Submitted**")
        with h5:
            st.markdown("**✅ Verified**")
        with h6:
            st.markdown("**⚙️ Actions**")

        st.divider()

        for inv in invoices:
            inv_id = inv.get('id')
            status = inv.get('status', 'pending')
            created_at = inv.get('created_at', 'N/A')
            verified_at = inv.get('verified_at')

            # Status color
            if status == 'verified':
                status_emoji = "✅"
            elif status == 'cancelled':
                status_emoji = "❌"
            else:
                status_emoji = "⏳"

            # 6 columns: Student | Amount | Status | Submitted | Verified | Actions
            c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1, 1.5, 1.5, 2])

            with c1:
                student_name = inv.get('student_name', 'Unknown')
                st.markdown(f"**{student_name}**")
                st.caption(f"Ref: `{inv.get('payment_reference', 'N/A')}`")

            with c2:
                st.markdown(f"**€{inv.get('amount_eur', 0):.2f}**")
                st.caption(f"{inv.get('credit_amount', 0)} credits")

            with c3:
                st.markdown(f"{status_emoji} **{status.title()}**")

            with c4:
                # Submitted column (header above identifies it)
                if created_at != 'N/A':
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%m-%d')
                        time_str = dt.strftime('%H:%M')
                        st.markdown(f"**{date_str}**")
                        st.caption(time_str)
                    except:
                        st.caption(f"{created_at}")
                else:
                    st.caption("-")

            with c5:
                # Verified column (header above identifies it)
                if status == 'verified' and verified_at:
                    try:
                        dt = datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%m-%d')
                        time_str = dt.strftime('%H:%M')
                        st.markdown(f"**{date_str}**")
                        st.caption(time_str)
                    except:
                        st.caption("-")
                else:
                    st.caption("-")

            with c6:
                if status == 'pending':
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        if st.button("✅ Verify", key=f"verify_inv_{inv_id}", use_container_width=True):
                            s, e = verify_invoice(token, inv_id)
                            if s:
                                st.success("✅ Verified!")
                                st.rerun()
                            else:
                                st.error(f"❌ {e}")
                    with ac2:
                        if st.button("🗑️", key=f"cancel_inv_{inv_id}", use_container_width=True):
                            s, e = cancel_invoice(token, inv_id)
                            if s:
                                st.rerun()
                elif status == 'verified':
                    if st.button("↩️ Unverify", key=f"unverify_inv_{inv_id}", use_container_width=True):
                        s, e = unverify_invoice(token, inv_id)
                        if s:
                            st.rerun()

            st.divider()
    elif success:
        st.info("ℹ️ No invoices found")
    else:
        st.error("❌ Failed to load invoices")
