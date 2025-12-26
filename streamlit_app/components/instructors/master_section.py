"""Master Instructor Section - Main Orchestrator"""

import streamlit as st
import sys
sys.path.append('..')
from api_helpers_instructors import (
    get_master_instructor_by_location,
    get_pending_offers
)
from master import (
    render_master_card,
    render_pending_offers_admin_view,
    render_hiring_interface
)
from datetime import datetime, date


def render_master_section(location_id: int, token: str) -> None:
    """
    Render master instructor section with hybrid hiring system

    Supports two pathways:
    - PATHWAY A: Direct Hire (admin invites specific instructor)
    - PATHWAY B: Job Posting (admin posts job, instructors apply)

    Shows:
    - Active master card (if exists)
    - Pending offer card (if offer sent but not accepted)
    - Dual hiring interface (if no master)

    Args:
        location_id: ID of the location
        token: Authentication token
    """

    st.subheader("Master Instructor")

    # Fetch current master
    try:
        master = get_master_instructor_by_location(token, location_id)
    except Exception as e:
        st.error(f"Error loading master instructor: {e}")
        return

    # Check for pending offers at this location
    try:
        pending_offers = get_pending_offers(token)
        location_pending_offers = [
            o for o in pending_offers
            if o.get('location_id') == location_id
        ]
    except:
        location_pending_offers = []

    # Determine what to show based on state
    if master and master.get('is_active') and master.get('offer_status') in ['ACCEPTED', None]:
        # Active master (ACCEPTED or legacy)
        render_master_card(master, token)
    elif location_pending_offers:
        # Pending offer(s) at this location
        render_pending_offers_admin_view(location_pending_offers, location_id, token)
    else:
        # No master - show hiring interface
        render_hiring_interface(location_id, token)


def get_master_status(location_id: int, token: str) -> str:
    """
    Get master instructor status for a location
    Used by Smart Matrix to show status badge

    Returns:
    - "active" - has active master
    - "pending" - has pending offer
    - "expiring" - has master but contract < 30 days
    - "no_master" - no master assigned

    Args:
        location_id: ID of the location
        token: Authentication token

    Returns:
        Status string
    """
    try:
        master = get_master_instructor_by_location(token, location_id)

        if not master or not master.get('is_active'):
            # Check for pending offers
            try:
                pending = get_pending_offers(token)
                if any(o.get('location_id') == location_id for o in pending):
                    return "pending"
            except:
                pass
            return "no_master"

        # Check if offer is still pending
        if master.get('offer_status') == 'OFFERED':
            return "pending"

        # Check contract expiration
        contract_end_str = master.get('contract_end', '')[:10]
        try:
            contract_end = datetime.strptime(contract_end_str, '%Y-%m-%d').date()
            days_until_expiry = (contract_end - date.today()).days

            if days_until_expiry < 30:
                return "expiring"
        except:
            pass

        return "active"

    except:
        return "no_master"
