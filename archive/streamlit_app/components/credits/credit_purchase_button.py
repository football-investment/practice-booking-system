"""
Credit Purchase Button Component
Shows insufficient credits warning + purchase button
"""
import streamlit as st


def render_credit_purchase_button(credit_balance: int, spec_type: str, token: str) -> None:
    """
    Render insufficient credits warning with purchase button

    Args:
        credit_balance: Current user credit balance
        spec_type: Specialization type (for button key uniqueness)
        token: User authentication token
    """
    st.warning("Insufficient Credits (Need 100)")

    # Calculate credits needed
    credits_needed = 100 - credit_balance

    # Purchase button
    if st.button(
        f"Purchase {credits_needed}+ Credits",
        key=f"purchase_{spec_type}",
        use_container_width=True,
        type="primary"
    ):
        # Show instructions
        st.info(
            "**How to purchase credits:**\n\n"
            "1. Request credit package below\n"
            "2. Transfer money with payment reference\n"
            "3. Admin verifies payment (usually within 24h)\n"
            "4. Credits added to your account\n"
            "5. Return here to unlock specialization"
        )

        # Trigger credit purchase form
        st.session_state['show_credit_purchase'] = True
        st.rerun()
