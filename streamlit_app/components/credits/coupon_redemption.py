"""
Coupon Redemption Component
UI for applying BONUS_CREDITS coupons (instant redemption)
"""
import streamlit as st
from api_helpers_financial import apply_coupon


def render_coupon_redemption(token: str) -> None:
    """
    Render coupon redemption form for BONUS_CREDITS

    Args:
        token: User authentication token
    """
    st.divider()
    st.header("🎁 Redeem Coupon")
    st.caption("Apply a BONUS_CREDITS coupon to instantly add credits to your account")

    # Coupon input form
    with st.form("coupon_redemption_form", clear_on_submit=False):
        coupon_code = st.text_input(
            "Coupon Code",
            placeholder="Enter your coupon code (e.g., E2E-BONUS-50-USER1)",
            help="Bonus credits coupons add credits instantly to your account",
            key="coupon_redemption_input"
        )

        col1, col2 = st.columns(2)

        with col1:
            submit_btn = st.form_submit_button(
                "🎟️ Apply Coupon",
                type="primary",
                use_container_width=True
            )

        with col2:
            cancel_btn = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

        if cancel_btn:
            st.session_state['show_coupon_redemption'] = False
            st.rerun()

        if submit_btn:
            if not coupon_code or not coupon_code.strip():
                st.error("❌ Please enter a coupon code")
            else:
                # Apply coupon via API
                success, error, response = apply_coupon(token, coupon_code.strip().upper())

                if success:
                    credits_awarded = response.get("credits_awarded", 0)
                    new_balance = response.get("new_balance", 0)

                    st.success(f"✅ Coupon applied successfully! +{credits_awarded} credits")
                    st.metric("New Credit Balance", new_balance)
                    st.balloons()

                    # Update user data in session
                    from api_helpers_general import get_current_user
                    user_success, user_error, user_data = get_current_user(token)
                    if user_success:
                        from config import SESSION_USER_KEY
                        st.session_state[SESSION_USER_KEY] = user_data

                    # Close the form after success
                    st.session_state['show_coupon_redemption'] = False

                    # Wait a bit for user to see the success message
                    st.info("🔄 Refreshing page...")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to apply coupon: {error}")
