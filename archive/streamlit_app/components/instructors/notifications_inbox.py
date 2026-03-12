"""
Notifications Inbox Component
Displays system notifications (job offers, alerts, etc.) with read/unread tracking
"""

import streamlit as st
from typing import Dict, Any, List
from datetime import datetime
import sys
sys.path.append('.')
from api_helpers_notifications import (
    get_unread_notifications,
    get_all_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read
)


def render_notifications_inbox(token: str) -> None:
    """
    Render system notifications inbox with read/unread tracking

    Args:
        token: Authentication token
    """
    st.markdown("### 🔔 System Notifications")
    st.caption("Job offers, alerts, and important updates")

    # Tabs for Unread vs All
    notif_tab1, notif_tab2 = st.tabs(["📬 Unread", "📁 All Notifications"])

    # === TAB 1: UNREAD NOTIFICATIONS ===
    with notif_tab1:
        success, error, data = get_unread_notifications(token)

        if not success:
            st.error(f"❌ Failed to load notifications: {error}")
            return

        notifications = data.get("notifications", [])
        unread_count = data.get("unread_count", 0)

        if unread_count == 0:
            st.info("✅ No unread notifications")
        else:
            st.warning(f"🔔 You have **{unread_count}** unread notifications")

            # Mark all as read button
            if st.button("✅ Mark All as Read", key="mark_all_read_unread"):
                mark_success, mark_error = mark_all_notifications_as_read(token)
                if mark_success:
                    st.success("✅ All notifications marked as read")
                    st.rerun()
                else:
                    st.error(f"❌ Failed: {mark_error}")

            st.divider()

            # Render each notification
            for notification in notifications:
                render_notification_card(notification, token)

    # === TAB 2: ALL NOTIFICATIONS ===
    with notif_tab2:
        success, error, data = get_all_notifications(token, page=1, size=50)

        if not success:
            st.error(f"❌ Failed to load notifications: {error}")
            return

        notifications = data.get("notifications", [])
        total = data.get("total", 0)

        if total == 0:
            st.info("📭 No notifications yet")
        else:
            st.caption(f"Total: {total} notifications")

            # Mark all as read button
            if st.button("✅ Mark All as Read", key="mark_all_read_all"):
                mark_success, mark_error = mark_all_notifications_as_read(token)
                if mark_success:
                    st.success("✅ All notifications marked as read")
                    st.rerun()
                else:
                    st.error(f"❌ Failed: {mark_error}")

            st.divider()

            # Render each notification
            for notification in notifications:
                render_notification_card(notification, token)


def render_notification_card(notification: Dict[str, Any], token: str) -> None:
    """
    Render a single notification card

    Args:
        notification: Notification data from API
        token: Authentication token
    """
    notif_id = notification.get("id")
    notif_type = notification.get("type", "GENERAL")
    title = notification.get("title", "Notification")
    message = notification.get("message", "")
    is_read = notification.get("is_read", False)
    created_at = notification.get("created_at", "")
    link = notification.get("link")

    # Format timestamp
    try:
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        time_str = dt.strftime("%Y-%m-%d %H:%M")
    except:
        time_str = "N/A"

    # Type emoji
    type_emoji = get_notification_type_emoji(notif_type)

    # Read/Unread indicator
    read_indicator = "📭" if is_read else "📬"

    # Card container
    with st.container():
        # Header row
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"**{read_indicator} {type_emoji} {title}**")

        with col2:
            st.caption(f"🕐 {time_str}")

        with col3:
            if not is_read:
                if st.button("✅ Read", key=f"read_{notif_id}", use_container_width=True):
                    mark_success, mark_error = mark_notification_as_read(token, notif_id)
                    if mark_success:
                        st.rerun()
                    else:
                        st.error(f"❌ {mark_error}")

        # Message body
        st.markdown(f"<div style='padding-left: 10px; margin-bottom: 10px;'>{message}</div>", unsafe_allow_html=True)

        # Action link (if any)
        if link:
            # Extract tab from link (e.g., ?tab=inbox)
            if "tab=" in link:
                tab_name = link.split("tab=")[1].split("&")[0]
                st.caption(f"🔗 [Go to {tab_name.capitalize()}]({link})")

        st.divider()


def get_notification_type_emoji(notif_type: str) -> str:
    """
    Get emoji icon for notification type

    Args:
        notif_type: Notification type string

    Returns:
        Emoji string
    """
    emoji_map = {
        "JOB_OFFER": "💼",
        "OFFER_ACCEPTED": "✅",
        "OFFER_DECLINED": "❌",
        "BOOKING_CONFIRMED": "📅",
        "BOOKING_CANCELLED": "🚫",
        "SESSION_REMINDER": "⏰",
        "SESSION_CANCELLED": "❌",
        "WAITLIST_PROMOTED": "⬆️",
        "GENERAL": "📢"
    }
    return emoji_map.get(notif_type, "📬")
