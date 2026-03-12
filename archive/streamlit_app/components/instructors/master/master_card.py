"""Master Card Component - Display active master instructor with termination controls"""

import streamlit as st
from datetime import datetime, date
from typing import Dict, Any
import sys
sys.path.append('..')
from api_helpers_instructors import terminate_master_instructor


def render_master_card(master: Dict[str, Any], token: str) -> None:
    """
    Render active master instructor card with contract details and termination controls

    Args:
        master: Master instructor data dictionary
        token: Authentication token
    """
    # Parse contract dates
    contract_start_str = master.get('contract_start', '')[:10]
    contract_end_str = master.get('contract_end', '')[:10]

    try:
        contract_end = datetime.strptime(contract_end_str, '%Y-%m-%d').date()
        days_until_expiry = (contract_end - date.today()).days
    except:
        days_until_expiry = None

    # Status banner with expiry warning
    offer_status = master.get('offer_status')
    if offer_status == 'ACCEPTED':
        if days_until_expiry is not None and days_until_expiry < 30:
            st.warning(f"Contract expiring in {days_until_expiry} days!")
        else:
            st.success("Active Master Instructor (Offer Accepted)")
    elif offer_status is None:
        # Legacy contract
        if days_until_expiry is not None and days_until_expiry < 30:
            st.warning(f"Contract expiring in {days_until_expiry} days!")
        else:
            st.success("Active Master Instructor")
    else:
        st.info(f"Status: {offer_status}")

    # Master details layout
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"### {master.get('instructor_name', 'Unknown')}")
        st.caption(f"Email: {master.get('instructor_email', 'N/A')}")
        st.caption(f"Contract: {contract_start_str} to {contract_end_str}")

        if days_until_expiry is not None:
            if days_until_expiry > 0:
                st.caption(f"Days remaining: {days_until_expiry}")
            else:
                st.caption(f"Contract expired {abs(days_until_expiry)} days ago")

        # Show hiring pathway if available
        hiring_pathway = master.get('hiring_pathway')
        if hiring_pathway:
            pathway_label = "Direct Hire" if hiring_pathway == "DIRECT" else "Job Posting"
            st.caption(f"Hired via: {pathway_label}")

    with col2:
        if master.get('is_active'):
            if st.button("Terminate", key=f"terminate_master_{master['id']}", type="secondary", use_container_width=True):
                if st.session_state.get(f"confirm_terminate_{master['id']}", False):
                    _terminate_master(master['id'], token)
                else:
                    st.session_state[f"confirm_terminate_{master['id']}"] = True
                    st.rerun()

            # Confirmation message
            if st.session_state.get(f"confirm_terminate_{master['id']}", False):
                st.warning("Click again to confirm")


def _terminate_master(master_id: int, token: str) -> None:
    """
    Terminate master instructor contract

    Args:
        master_id: ID of master to terminate
        token: Authentication token
    """
    try:
        terminate_master_instructor(token, master_id)
        st.success("Master instructor terminated successfully")

        # Clear confirmation state
        if f"confirm_terminate_{master_id}" in st.session_state:
            del st.session_state[f"confirm_terminate_{master_id}"]

        st.rerun()
    except Exception as e:
        st.error(f"Error terminating master: {e}")
