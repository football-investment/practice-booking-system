"""
Invoice Success Display Component
Shows payment reference and bank transfer instructions
"""
import streamlit as st
from typing import Dict, Any


def render_invoice_success(response: Dict[str, Any], amount_eur: float) -> None:
    """
    Display invoice creation success with payment instructions

    Args:
        response: API response with invoice_id and payment_reference
        amount_eur: Amount in EUR to transfer
    """
    payment_ref = response.get('payment_reference')
    invoice_id = response.get('invoice_id')

    st.success(f"Invoice created! Invoice ID: #{invoice_id}")

    st.info(
        f"**Payment Reference:** `{payment_ref}`\n\n"
        f"**Amount to transfer:** €{amount_eur}\n\n"
        f"**Bank transfer instructions:**\n"
        f"1. Transfer €{amount_eur} to: [BANK_ACCOUNT]\n"
        f"2. Include reference: `{payment_ref}` in transfer note\n"
        f"3. Wait for admin verification (usually 24h)\n"
        f"4. Check your credit balance here\n\n"
        f"Invoice status: PENDING"
    )
