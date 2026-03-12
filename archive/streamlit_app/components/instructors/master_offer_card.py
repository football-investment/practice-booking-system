"""Master Instructor Offer Card - Instructor View"""

import streamlit as st
from datetime import datetime, date
from typing import Dict, Any, List
import sys
sys.path.append('..')
from api_helpers_instructors import respond_to_master_offer


def render_master_offer_card(offer: Dict[str, Any], token: str) -> None:
    """
    Render a single master instructor offer card (instructor view)

    Shows:
    - Offer details (location, contract dates, deadline)
    - Availability match warnings
    - Accept/Decline buttons
    - Countdown to deadline
    """

    offer_id = offer.get('id')
    offer_status = offer.get('offer_status', 'UNKNOWN')

    # Determine card style based on status
    if offer_status == 'OFFERED':
        _render_pending_offer_card(offer, token)
    elif offer_status == 'ACCEPTED':
        _render_accepted_offer_card(offer)
    elif offer_status == 'DECLINED':
        _render_declined_offer_card(offer)
    elif offer_status == 'EXPIRED':
        _render_expired_offer_card(offer)
    else:
        st.error(f"Unknown offer status: {offer_status}")


def _render_pending_offer_card(offer: Dict[str, Any], token: str) -> None:
    """Render pending offer (awaiting response)"""

    offer_id = offer.get('id')
    location_name = offer.get('location_name', 'Unknown Location')
    location_city = offer.get('location_city', '')

    # Parse dates
    contract_start_str = offer.get('contract_start', '')[:10]
    contract_end_str = offer.get('contract_end', '')[:10]
    offered_at_str = offer.get('offered_at', '')[:10] if offer.get('offered_at') else 'N/A'

    # Calculate deadline
    deadline_str = offer.get('offer_deadline', '')
    days_remaining = None
    deadline_display = 'N/A'

    if deadline_str:
        try:
            deadline_date = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
            days_remaining = (deadline_date - date.today()).days
            deadline_display = deadline_date.strftime('%Y-%m-%d')
        except:
            pass

    # Get availability info
    match_score = offer.get('availability_match_score', 100)
    warnings = offer.get('availability_warnings', [])

    # Container with border
    with st.container():
        # Header with status indicator
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"### 📩 Master Instructor Offer")
            if days_remaining is not None and days_remaining < 3:
                st.caption(f"⚠️ **URGENT**: Expires in {days_remaining} days")

        with col2:
            if days_remaining is not None:
                if days_remaining > 7:
                    st.success(f"✓ {days_remaining}d")
                elif days_remaining > 3:
                    st.warning(f"⏰ {days_remaining}d")
                else:
                    st.error(f"⚠️ {days_remaining}d")

        st.divider()

        # Offer details
        st.markdown(f"**Location:** {location_name}")
        if location_city:
            st.caption(f"📍 {location_city}")

        st.markdown(f"**Contract Period:**")
        st.caption(f"  📅 {contract_start_str} → {contract_end_str}")

        contract_duration = (
            datetime.strptime(contract_end_str, '%Y-%m-%d').date() -
            datetime.strptime(contract_start_str, '%Y-%m-%d').date()
        ).days
        st.caption(f"  ⏳ {contract_duration} days ({contract_duration // 365} years)")

        st.divider()

        # Timeline
        st.markdown("**Timeline:**")
        st.caption(f"  📤 Offered: {offered_at_str}")
        st.caption(f"  ⏰ Deadline: {deadline_display}")

        if days_remaining is not None:
            if days_remaining > 0:
                st.caption(f"  ⏳ **{days_remaining} days remaining to respond**")
            else:
                st.error(f"  ❌ Deadline passed {abs(days_remaining)} days ago")

        st.divider()

        # Availability match
        if match_score < 100:
            st.warning(f"⚠️ **Availability Match: {match_score}%**")

            if warnings:
                with st.expander("⚠️ Availability Warnings", expanded=True):
                    for warning in warnings:
                        st.caption(f"• {warning}")
                    st.info("💡 You can update your availability in your profile, or discuss with admin if you can adjust your schedule.")
        else:
            st.success(f"✅ **Availability Match: {match_score}%**")
            st.caption("Your availability perfectly matches the contract period!")

        st.divider()

        # Action buttons (only if deadline not passed)
        if days_remaining is None or days_remaining > 0:
            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "✅ Accept Offer",
                    key=f"accept_offer_{offer_id}",
                    type="primary",
                    use_container_width=True,
                    help="Accept this master instructor position"
                ):
                    _handle_accept_offer(offer_id, location_name, token)

            with col2:
                if st.button(
                    "❌ Decline Offer",
                    key=f"decline_offer_{offer_id}",
                    type="secondary",
                    use_container_width=True,
                    help="Decline this offer"
                ):
                    _handle_decline_offer(offer_id, location_name, token)

            # Important note
            st.caption("⚠️ **Important:** You can only be master at ONE location at a time. If you accept this offer, any other pending offers will be automatically declined.")
        else:
            st.error("⚠️ This offer has expired. You can no longer accept or decline it.")


def _render_accepted_offer_card(offer: Dict[str, Any]) -> None:
    """Render accepted offer (historical record)"""

    location_name = offer.get('location_name', 'Unknown Location')
    contract_start_str = offer.get('contract_start', '')[:10]
    contract_end_str = offer.get('contract_end', '')[:10]
    accepted_at_str = offer.get('accepted_at', '')[:10] if offer.get('accepted_at') else 'N/A'

    with st.container():
        st.success("✅ **Offer Accepted**")

        st.markdown(f"**Location:** {location_name}")
        st.caption(f"📅 Contract: {contract_start_str} → {contract_end_str}")
        st.caption(f"✅ Accepted: {accepted_at_str}")

        st.info("You are now the master instructor at this location. You can manage semesters, post positions, and hire assistant instructors.")


def _render_declined_offer_card(offer: Dict[str, Any]) -> None:
    """Render declined offer (historical record)"""

    location_name = offer.get('location_name', 'Unknown Location')
    declined_at_str = offer.get('declined_at', '')[:10] if offer.get('declined_at') else 'N/A'

    with st.expander(f"❌ Declined Offer - {location_name}", expanded=False):
        st.caption(f"📍 Location: {location_name}")
        st.caption(f"❌ Declined: {declined_at_str}")


def _render_expired_offer_card(offer: Dict[str, Any]) -> None:
    """Render expired offer (historical record)"""

    location_name = offer.get('location_name', 'Unknown Location')
    deadline_str = offer.get('offer_deadline', '')[:10] if offer.get('offer_deadline') else 'N/A'

    with st.expander(f"⏰ Expired Offer - {location_name}", expanded=False):
        st.caption(f"📍 Location: {location_name}")
        st.caption(f"⏰ Expired: {deadline_str}")
        st.caption("You did not respond before the deadline.")


def _handle_accept_offer(offer_id: int, location_name: str, token: str) -> None:
    """Handle accept offer action"""

    # Confirmation state
    confirm_key = f"confirm_accept_{offer_id}"

    if not st.session_state.get(confirm_key, False):
        # First click - ask for confirmation
        st.session_state[confirm_key] = True
        st.warning("⚠️ Are you sure? Click 'Accept Offer' again to confirm. This will decline all other pending offers.")
        st.rerun()
    else:
        # Second click - confirmed
        try:
            with st.spinner("Accepting offer..."):
                result = respond_to_master_offer(token, offer_id, "ACCEPT")

            st.success(f"🎉 Congratulations! You are now the master instructor at {location_name}!")
            st.balloons()

            # Clear confirmation state
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]

            # Show next steps
            st.info("""
**Next Steps:**
1. Review the semesters at your location
2. Post positions for assistant instructors
3. Review applications and hire your team
4. Start managing your location's training program!
            """)

            st.rerun()

        except Exception as e:
            error_msg = str(e)

            # Parse error
            if "already has an active master" in error_msg.lower():
                st.error(f"❌ You already have an active master position at another location. Please terminate that position first.")
            elif "deadline" in error_msg.lower() or "expired" in error_msg.lower():
                st.error("❌ This offer has expired. You can no longer accept it.")
            elif "not found" in error_msg.lower():
                st.error("❌ Offer not found. It may have been cancelled.")
            else:
                st.error(f"❌ Error accepting offer: {error_msg}")

            # Clear confirmation state on error
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]


def _handle_decline_offer(offer_id: int, location_name: str, token: str) -> None:
    """Handle decline offer action"""

    # Confirmation state
    confirm_key = f"confirm_decline_{offer_id}"

    if not st.session_state.get(confirm_key, False):
        # First click - ask for confirmation
        st.session_state[confirm_key] = True
        st.warning("⚠️ Are you sure? Click 'Decline Offer' again to confirm. This action cannot be undone.")
        st.rerun()
    else:
        # Second click - confirmed
        try:
            with st.spinner("Declining offer..."):
                result = respond_to_master_offer(token, offer_id, "DECLINE")

            st.info(f"Offer from {location_name} has been declined.")

            # Clear confirmation state
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]

            st.rerun()

        except Exception as e:
            st.error(f"❌ Error declining offer: {e}")

            # Clear confirmation state on error
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]


def render_all_master_offers(token: str) -> None:
    """
    Render all master offers for the current instructor

    Shows:
    - Pending offers (OFFERED) - prominently
    - Accepted offers - as info
    - Declined/Expired - in expander
    """

    from api_helpers_instructors import get_my_master_offers

    # Fetch all offers
    try:
        all_offers = get_my_master_offers(token, include_expired=True)
    except Exception as e:
        st.error(f"Error loading offers: {e}")
        return

    if not all_offers:
        st.info("📭 No master instructor offers yet.")
        return

    # Group by status
    pending = [o for o in all_offers if o.get('offer_status') == 'OFFERED']
    accepted = [o for o in all_offers if o.get('offer_status') == 'ACCEPTED']
    declined = [o for o in all_offers if o.get('offer_status') == 'DECLINED']
    expired = [o for o in all_offers if o.get('offer_status') == 'EXPIRED']

    # Render pending offers (most important)
    if pending:
        st.markdown("### 📩 Pending Offers")
        st.caption(f"You have {len(pending)} pending offer(s) - please respond before the deadline!")

        for offer in pending:
            render_master_offer_card(offer, token)
            st.divider()

    # Render accepted offers
    if accepted:
        st.markdown("### ✅ Accepted Offers")
        for offer in accepted:
            render_master_offer_card(offer, token)

    # Render declined/expired in expander
    if declined or expired:
        with st.expander(f"📜 Past Offers ({len(declined) + len(expired)})", expanded=False):
            for offer in declined + expired:
                render_master_offer_card(offer, token)
