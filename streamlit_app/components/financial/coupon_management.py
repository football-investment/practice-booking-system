"""
Coupon Management Component
Handles coupon creation, display, and activation/deactivation
"""

import streamlit as st
from datetime import datetime, timedelta
from api_helpers_financial import get_coupons, create_coupon, update_coupon


def render_coupon_management(token: str):
    """Render the coupon management interface"""
    st.markdown("### 🎫 Coupon Management")
    st.caption("Create and manage discount coupons")

    # Refresh and Create buttons
    col_refresh, col_create = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄", key="refresh_coupons"):
            st.rerun()

    with col_create:
        if st.button("➕ Create Coupon", key="create_coupon_btn", use_container_width=True):
            st.session_state.show_create_coupon_modal = True
            st.rerun()

    st.divider()

    # Get coupons
    success, coupons = get_coupons(token)

    if success and coupons:
        st.metric("Total Coupons", len(coupons))
        st.divider()

        # Display coupons with usage info
        for coupon in coupons:
            cid = coupon.get('id')
            current_uses = coupon.get('current_uses', 0)
            max_uses = coupon.get('max_uses')

            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1.5, 2])

                with c1:
                    st.markdown(f"**{coupon.get('code')}**")
                    if coupon.get('description'):
                        st.caption(coupon['description'])

                with c2:
                    dtype = coupon.get('type', 'BONUS_CREDITS')
                    dval = coupon.get('discount_value', 0)

                    # Display value based on type
                    if dtype == 'BONUS_CREDITS':
                        st.markdown(f"**+{int(dval)} cr**")
                        st.caption("Instant")
                    elif dtype == 'PURCHASE_DISCOUNT_PERCENT':
                        st.markdown(f"**{int(dval * 100)}% off**")
                        st.caption("Purchase")
                    elif dtype == 'PURCHASE_BONUS_CREDITS':
                        st.markdown(f"**+{int(dval)} cr**")
                        st.caption("Purchase")
                    # Legacy types (backwards compatibility - should not appear after migration)
                    elif dtype == 'PERCENT':
                        st.markdown(f"**{int(dval * 100)}%**")
                        st.caption("Legacy")
                    elif dtype == 'FIXED':
                        st.markdown(f"**€{dval}**")
                        st.caption("Legacy")
                    elif dtype == 'CREDITS':
                        st.markdown(f"**+{int(dval)} cr**")
                        st.caption("Legacy")
                    else:
                        st.markdown(f"**{dval}**")

                with c3:
                    if coupon.get('is_active'):
                        st.success("Active")
                    else:
                        st.error("Inactive")

                with c4:
                    # Usage statistics
                    if max_uses:
                        st.markdown(f"**{current_uses}/{max_uses}**")
                        st.caption("Uses")
                    else:
                        st.markdown(f"**{current_uses}**")
                        st.caption("Uses (∞)")

                with c5:
                    # Only Activate/Deactivate buttons (Edit removed - can't change discount after use)
                    if coupon.get('is_active'):
                        if st.button("🔴 Deactivate", key=f"deact_c_{cid}", use_container_width=True):
                            s, e, _ = update_coupon(token, cid, {"is_active": False})
                            if s:
                                st.rerun()
                    else:
                        if st.button("🟢 Activate", key=f"act_c_{cid}", use_container_width=True):
                            s, e, _ = update_coupon(token, cid, {"is_active": True})
                            if s:
                                st.rerun()
                st.divider()

    elif success:
        st.info("No coupons yet")
    else:
        st.error("Failed to load coupons")

    # CREATE MODAL
    if st.session_state.get('show_create_coupon_modal'):
        _render_create_coupon_modal(token)


def _render_create_coupon_modal(token: str):
    """Render the create coupon modal (internal function)"""
    @st.dialog("Create Coupon")
    def create_coupon_modal():
        # Initialize coupon type in session state if not present
        if 'coupon_type_select' not in st.session_state:
            st.session_state.coupon_type_select = "BONUS_CREDITS"

        # Type selection OUTSIDE form to enable dynamic field updates
        dtype = st.selectbox(
            "Type *",
            ["BONUS_CREDITS", "PURCHASE_DISCOUNT_PERCENT", "PURCHASE_BONUS_CREDITS"],
            key="coupon_type_select",
            format_func=lambda x: {
                "BONUS_CREDITS": "🎁 Bonus Credits (Instant)",
                "PURCHASE_DISCOUNT_PERCENT": "💰 Purchase Discount (%)",
                "PURCHASE_BONUS_CREDITS": "🎉 Purchase Bonus Credits"
            }[x],
            help="""
            - Bonus Credits: Immediately awarded when coupon is redeemed (no purchase required)
            - Purchase Discount %: Percentage discount when buying credit packages (requires invoice + admin approval)
            - Purchase Bonus Credits: Extra credits awarded after credit package purchase (requires invoice + admin approval)
            """
        )

        st.divider()

        # Now render the form with dynamic fields based on selected type
        with st.form("create_coupon_f"):
            code = st.text_input("Code *", placeholder="SUMMER25", help="Unique coupon code (uppercase)")
            desc = st.text_area("Description", placeholder="Describe what this coupon does")

            # Value input with validation based on type
            if dtype == "BONUS_CREDITS":
                dval = st.number_input(
                    "Bonus Credits *",
                    min_value=1.0,
                    step=10.0,
                    help="Enter bonus credits. Example: 500 = +500 credits immediately upon redemption"
                )
                st.info("✅ Credits will be awarded IMMEDIATELY upon redemption (no purchase or approval required)")

            elif dtype == "PURCHASE_DISCOUNT_PERCENT":
                dval = st.number_input(
                    "Discount Percentage *",
                    min_value=1.0,
                    max_value=100.0,
                    step=1.0,
                    help="Enter percentage (1-100). Example: 20 = 20% discount on credit package purchase"
                )
                st.warning("⚠️ Requires invoice generation and admin approval")
                st.caption("Example: User buys 1000cr package (€100) with 20% discount → Pays €80 → Admin approves → User receives 1000cr")

            elif dtype == "PURCHASE_BONUS_CREDITS":
                dval = st.number_input(
                    "Bonus Credits *",
                    min_value=1.0,
                    step=10.0,
                    help="Enter bonus credits. Example: 500 = +500 bonus credits after purchase"
                )
                st.warning("⚠️ Requires invoice generation and admin approval")
                st.caption("Example: User buys 1000cr package (€100) → Pays €100 → Admin approves → User receives 1000cr + 500cr bonus = 1500cr total")

            # Optional settings
            c1, c2 = st.columns(2)
            with c1:
                max_uses = st.number_input(
                    "Max Uses",
                    min_value=0,
                    value=0,
                    step=1,
                    help="0 = unlimited uses"
                )
            with c2:
                expires_days = st.number_input(
                    "Expires in (days)",
                    min_value=0,
                    value=0,
                    step=1,
                    help="0 = never expires"
                )

            cs, cc = st.columns(2)
            with cs:
                sub = st.form_submit_button("Create", use_container_width=True, type="primary")
            with cc:
                can = st.form_submit_button("Cancel", use_container_width=True)

            if can:
                st.session_state.show_create_coupon_modal = False
                # Clean up coupon type selection
                if 'coupon_type_select' in st.session_state:
                    del st.session_state.coupon_type_select
                st.rerun()

            if sub:
                # Validation
                if not code:
                    st.error("Code is required!")
                    return

                if dval <= 0:
                    st.error("Value must be greater than 0!")
                    return

                # Convert value based on type
                if dtype == "PURCHASE_DISCOUNT_PERCENT":
                    # Convert percentage to decimal (20 → 0.2)
                    backend_value = dval / 100.0
                else:
                    # For bonus credits types, use value directly
                    backend_value = dval

                # Calculate expiration date
                expires_at = None
                if expires_days > 0:
                    expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

                coupon_data = {
                    "code": code.upper().strip(),
                    "description": desc.strip() if desc else f"{code} coupon",
                    "type": dtype,
                    "discount_value": backend_value,
                    "is_active": True
                }

                if max_uses > 0:
                    coupon_data["max_uses"] = max_uses

                if expires_at:
                    coupon_data["expires_at"] = expires_at

                s, e, _ = create_coupon(token, coupon_data)
                if s:
                    st.success(f"✅ Coupon '{code.upper()}' created!")
                    st.session_state.show_create_coupon_modal = False
                    # Clean up coupon type selection
                    if 'coupon_type_select' in st.session_state:
                        del st.session_state.coupon_type_select
                    st.rerun()
                else:
                    st.error(f"❌ Failed: {e}")

    create_coupon_modal()
