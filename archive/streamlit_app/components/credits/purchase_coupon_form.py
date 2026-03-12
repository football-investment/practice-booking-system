"""
Purchase Coupon Form Component
UI for applying PURCHASE discount coupons during credit purchase
"""
import streamlit as st


def render_purchase_coupon_form() -> tuple[bool, str, dict]:
    """
    Render purchase coupon input form (for PURCHASE_DISCOUNT_PERCENT and PURCHASE_BONUS_CREDITS)

    Returns:
        tuple: (has_coupon, coupon_code, coupon_validation_result)
            - has_coupon: Whether user wants to apply a coupon
            - coupon_code: The coupon code entered (uppercase, stripped)
            - coupon_validation_result: API validation response (if validated)
    """
    st.divider()
    st.markdown("### 🎟️ Have a Purchase Coupon?")
    st.caption("""
    Apply a discount coupon to get:
    • **Percentage Discount** - Pay less for your credit package (e.g., 20% off)
    • **Bonus Credits** - Receive extra credits with your purchase (e.g., +500 bonus credits)

    ⚠️ **Note:** Purchase coupons require invoice generation and admin approval after payment.
    """)

    # Toggle to show/hide coupon input
    apply_coupon = st.checkbox(
        "I have a purchase coupon code",
        key="apply_purchase_coupon_toggle",
        help="Check this if you have a discount or bonus coupon for credit purchases"
    )

    if not apply_coupon:
        return False, "", {}

    # Coupon code input
    coupon_code = st.text_input(
        "Coupon Code",
        placeholder="Enter your purchase coupon code (e.g., SUMMER25-DISCOUNT)",
        help="Enter a valid PURCHASE_DISCOUNT_PERCENT or PURCHASE_BONUS_CREDITS coupon code",
        key="purchase_coupon_input"
    ).strip().upper()

    if not coupon_code:
        st.info("💡 Enter your coupon code above to see the discount/bonus details")
        return True, "", {}

    # Validate coupon button
    if st.button("🔍 Validate Coupon", key="validate_purchase_coupon_btn", type="secondary"):
        # Import here to avoid circular dependency
        from api_helpers_financial import validate_coupon
        from config import SESSION_TOKEN_KEY

        token = st.session_state.get(SESSION_TOKEN_KEY)
        if not token:
            st.error("❌ Authentication required")
            return True, coupon_code, {}

        # Validate coupon via API
        success, error, response = validate_coupon(token, coupon_code)

        if success:
            coupon_type = response.get("type")
            discount_value = response.get("discount_value", 0)

            # Check if it's a PURCHASE coupon type
            if coupon_type not in ["PURCHASE_DISCOUNT_PERCENT", "PURCHASE_BONUS_CREDITS"]:
                st.error(f"❌ Invalid coupon type: This is a {coupon_type} coupon. Please use a PURCHASE discount or bonus coupon here.")
                st.info("💡 **Bonus Credits coupons** should be redeemed in the Specialization Hub or bonus redemption section.")
                return True, coupon_code, {}

            # Display coupon details
            st.success(f"✅ Valid purchase coupon: **{coupon_code}**")

            if coupon_type == "PURCHASE_DISCOUNT_PERCENT":
                discount_percent = int(discount_value * 100)
                st.info(f"""
                🎉 **{discount_percent}% Discount Applied!**

                You'll pay **{discount_percent}% less** for your selected credit package.

                **Example:**
                - Package: 1000 credits = €100
                - With {discount_percent}% discount: €{100 * (1 - discount_value):.2f}
                - You save: €{100 * discount_value:.2f}
                """)

            elif coupon_type == "PURCHASE_BONUS_CREDITS":
                bonus_credits = int(discount_value)
                st.info(f"""
                🎁 **+{bonus_credits} Bonus Credits!**

                After your purchase is approved, you'll receive **+{bonus_credits} extra credits** on top of your package.

                **Example:**
                - Package: 1000 credits = €100
                - Bonus: +{bonus_credits} credits
                - **Total credits:** {1000 + bonus_credits} credits
                """)

            # Store validated coupon in session state
            st.session_state['validated_purchase_coupon'] = {
                'code': coupon_code,
                'type': coupon_type,
                'discount_value': discount_value,
                'response': response
            }

            return True, coupon_code, response
        else:
            st.error(f"❌ Invalid coupon: {error}")
            return True, coupon_code, {}

    # Check if we have a previously validated coupon
    validated_coupon = st.session_state.get('validated_purchase_coupon', {})
    if validated_coupon.get('code') == coupon_code:
        coupon_type = validated_coupon.get('type')
        discount_value = validated_coupon.get('discount_value', 0)

        st.success(f"✅ Coupon **{coupon_code}** is validated and ready to use")

        if coupon_type == "PURCHASE_DISCOUNT_PERCENT":
            discount_percent = int(discount_value * 100)
            st.caption(f"💰 {discount_percent}% discount will be applied to your purchase")
        elif coupon_type == "PURCHASE_BONUS_CREDITS":
            bonus_credits = int(discount_value)
            st.caption(f"🎁 +{bonus_credits} bonus credits will be awarded after approval")

        return True, coupon_code, validated_coupon.get('response', {})

    return True, coupon_code, {}


def clear_validated_purchase_coupon():
    """Helper function to clear validated coupon from session state"""
    if 'validated_purchase_coupon' in st.session_state:
        del st.session_state['validated_purchase_coupon']
