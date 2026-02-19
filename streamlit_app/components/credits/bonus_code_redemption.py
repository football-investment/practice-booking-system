"""
Bonus Code Redemption Component
UI for redeeming BONUS_CREDITS codes (instant credit rewards, no purchase required)
"""
import streamlit as st
from api_helpers_financial import apply_coupon


def render_bonus_code_redemption(token: str) -> None:
    """
    Render bonus code redemption form for BONUS_CREDITS (instant credits, no purchase)

    Args:
        token: User authentication token
    """
    st.divider()
    st.markdown("### 🎁 Redeem Bonus Code")
    st.caption("""
    Have a **Bonus Code**? Redeem it here to instantly receive free credits!

    ✅ **Instant Credits** - No purchase required, credits added immediately
    💡 **One-time use** - Each code can only be used once per account

    ⚠️ **Note:** This is for BONUS codes only. Purchase discount coupons should be entered during checkout.
    """)

    # Coupon input form
    with st.form("bonus_code_redemption_form", clear_on_submit=False):
        coupon_code = st.text_input(
            "Bonus Code",
            placeholder="Enter your bonus code (e.g., WELCOME500)",
            help="Bonus codes instantly add credits to your account (no purchase needed)",
            key="bonus_code_input"
        )

        col1, col2 = st.columns(2)

        with col1:
            submit_btn = st.form_submit_button(
                "🎁 Redeem Code",
                type="primary",
                use_container_width=True
            )

        with col2:
            cancel_btn = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

        if cancel_btn:
            st.session_state['show_bonus_redemption'] = False
            st.rerun()

        if submit_btn:
            if not coupon_code or not coupon_code.strip():
                st.error("❌ Please enter a bonus code")
            else:
                # Apply coupon via API
                success, error, response = apply_coupon(token, coupon_code.strip().upper())

                if success:
                    # Check if it was actually a BONUS_CREDITS type
                    coupon_type = response.get("coupon_type")
                    if coupon_type and coupon_type != "BONUS_CREDITS":
                        st.error(f"""
                        ❌ Invalid code type: This is a **{coupon_type}** coupon, not a bonus code.

                        💡 **Purchase coupons** should be entered during credit purchase checkout, not here.
                        """)
                    else:
                        credits_awarded = response.get("credits_awarded", 0)
                        new_balance = response.get("new_balance", 0)

                        st.success(f"✅ Bonus code redeemed successfully! +{credits_awarded} credits")
                        st.metric("New Credit Balance", new_balance)
                        st.balloons()

                        # Update user data in session
                        from api_helpers_general import get_current_user
                        user_success, user_error, user_data = get_current_user(token)
                        if user_success:
                            from config import SESSION_USER_KEY
                            st.session_state[SESSION_USER_KEY] = user_data

                        # Close the form after success
                        st.session_state['show_bonus_redemption'] = False

                        # Wait a bit for user to see the success message
                        st.info("🔄 Refreshing page...")
                        st.rerun()
                else:
                    st.error(f"❌ Failed to redeem code: {error}")
