"""
Credit Purchase Form Component
Handles credit package selection and invoice request
"""
import streamlit as st
from typing import Optional
from api_helpers_general import request_invoice
from .invoice_success_display import render_invoice_success


def render_credit_purchase_form(token: str) -> None:
    """
    Render credit purchase form with package selection

    Args:
        token: User authentication token
    """
    st.divider()
    st.header("Purchase Credits")

    st.info(
        "**Credit packages available:**\n\n"
        "- 100 credits = €10\n"
        "- 500 credits = €45 (10% discount)\n"
        "- 1000 credits = €80 (20% discount)"
    )

    # Credit packages
    credit_packages = [
        {"credits": 100, "price": 10.0, "discount": ""},
        {"credits": 500, "price": 45.0, "discount": "10% discount"},
        {"credits": 1000, "price": 80.0, "discount": "20% discount"}
    ]

    # Package selection
    selected_idx = st.selectbox(
        "Select Package",
        options=range(len(credit_packages)),
        format_func=lambda i: (
            f"{credit_packages[i]['credits']} credits - "
            f"€{credit_packages[i]['price']} "
            f"{credit_packages[i]['discount']}"
        )
    )

    package = credit_packages[selected_idx]

    # ============================================================================
    # COUPON CODE INPUT
    # ============================================================================

    st.divider()

    st.markdown("### 🎟️ Have a Coupon Code?")

    col1_coupon, col2_coupon = st.columns([3, 1])

    with col1_coupon:
        coupon_input = st.text_input(
            "Coupon Code",
            placeholder="Enter coupon code (optional)",
            key="coupon_code_input",
            help="Enter a valid coupon code to get a discount"
        )

    with col2_coupon:
        st.markdown("<br>", unsafe_allow_html=True)  # Vertical spacing
        validate_btn = st.button("🔍 Validate", use_container_width=True, key="validate_coupon_btn")

    # Coupon validation state
    if "coupon_validated" not in st.session_state:
        st.session_state["coupon_validated"] = False
    if "coupon_data" not in st.session_state:
        st.session_state["coupon_data"] = {}

    # Validate coupon when button clicked
    if validate_btn and coupon_input:
        from api_helpers_financial import validate_coupon

        success, error, coupon_data = validate_coupon(token, coupon_input.strip().upper())

        if success:
            st.session_state["coupon_validated"] = True
            st.session_state["coupon_data"] = coupon_data
            st.success(f"✅ Coupon '{coupon_input.upper()}' is valid!")

            # Show discount info
            if coupon_data.get("type") == "PERCENTAGE":
                st.info(f"💰 Discount: {coupon_data.get('discount_value')}% off")
            elif coupon_data.get("type") == "FIXED_AMOUNT":
                st.info(f"💰 Discount: €{coupon_data.get('discount_value')} off")

        else:
            st.session_state["coupon_validated"] = False
            st.session_state["coupon_data"] = {}
            st.error(f"❌ {error}")

    # Show validated coupon info
    if st.session_state.get("coupon_validated") and st.session_state.get("coupon_data"):
        coupon_data = st.session_state["coupon_data"]

        st.success(f"✅ **Active Coupon:** {coupon_data.get('code')}")

        # Calculate discount preview
        original_price = package["price"]

        if coupon_data.get("type") == "PERCENTAGE":
            discount_amount = original_price * (coupon_data.get("discount_value") / 100)
            final_price = original_price - discount_amount
            st.metric(
                "Final Price",
                f"€{final_price:.2f}",
                delta=f"-€{discount_amount:.2f} ({coupon_data.get('discount_value')}% off)"
            )
        elif coupon_data.get("type") == "FIXED_AMOUNT":
            discount_amount = coupon_data.get("discount_value")
            final_price = max(0, original_price - discount_amount)
            st.metric(
                "Final Price",
                f"€{final_price:.2f}",
                delta=f"-€{discount_amount:.2f}"
            )

        # Clear coupon button
        if st.button("🗑️ Remove Coupon", key="clear_coupon_btn"):
            st.session_state["coupon_validated"] = False
            st.session_state["coupon_data"] = {}
            st.rerun()

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Request Invoice", type="primary", use_container_width=True):
            # Get coupon code if validated
            coupon_code = None
            if st.session_state.get("coupon_validated") and st.session_state.get("coupon_data"):
                coupon_code = st.session_state["coupon_data"].get("code")

            # Call API with coupon code
            success, error, response = request_invoice(
                token,
                package['credits'],
                package['price'],
                coupon_code=coupon_code  # ✅ Pass coupon code
            )

            if success:
                # Show success (delegate to separate component)
                render_invoice_success(response, package['price'])
                st.session_state['show_credit_purchase'] = False
            else:
                st.error(f"Failed to create invoice: {error}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state['show_credit_purchase'] = False
            st.rerun()
