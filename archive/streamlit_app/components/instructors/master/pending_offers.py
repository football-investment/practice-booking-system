"""Pending Offers Component - Display pending offers in admin view"""

import streamlit as st
from datetime import datetime, date
from typing import Dict, Any, List
import sys
sys.path.append('..')
from api_helpers_instructors import cancel_offer


def render_pending_offers_admin_view(offers: List[Dict[str, Any]], location_id: int, token: str) -> None:
    """
    Render pending offers for location in admin view

    Shows:
    - Offer recipient details
    - Offered date and deadline
    - Availability match score
    - Cancel offer button

    Args:
        offers: List of pending offer dictionaries
        location_id: ID of the location
        token: Authentication token
    """

    st.info(f"**{len(offers)} Pending Offer(s)**\n\nWaiting for instructor response")

    for offer in offers:
        with st.container():
            st.divider()

            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### Offer to: {offer.get('instructor_name', 'Unknown')}")
                st.caption(f"Email: {offer.get('instructor_email', 'N/A')}")

                offered_at = offer.get('offered_at', '')[:10] if offer.get('offered_at') else 'N/A'
                deadline = offer.get('offer_deadline', '')[:10] if offer.get('offer_deadline') else 'N/A'

                st.caption(f"Offered: {offered_at}")
                st.caption(f"Deadline: {deadline}")

                # Calculate days remaining
                try:
                    deadline_date = datetime.fromisoformat(offer.get('offer_deadline', '').replace('Z', '+00:00'))
                    days_left = (deadline_date.date() - date.today()).days
                    if days_left > 0:
                        st.caption(f"Days remaining: {days_left}")
                    else:
                        st.caption(f"Deadline passed ({abs(days_left)} days ago)")
                except:
                    pass

                # Show availability match if available
                match_score = offer.get('availability_match_score', 0)
                if match_score < 100:
                    st.warning(f"Availability Match: {match_score}%")
                else:
                    st.success(f"Availability Match: {match_score}%")

            with col2:
                if st.button("Cancel Offer", key=f"cancel_offer_{offer['id']}", type="secondary", use_container_width=True):
                    try:
                        cancel_offer(token, offer['id'])
                        st.success("Offer cancelled")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
