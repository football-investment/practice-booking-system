"""
API Helper Functions for Notifications

Handles all notification-related API calls:
- Get unread notifications
- Get all notifications
- Mark notifications as read
- Get unread count (for badge)
"""

import requests
from typing import Tuple, Optional, Dict, Any
from config import API_BASE_URL as BASE_URL


def get_unread_notifications(token: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Get unread notifications for current user

    Args:
        token: Authentication token

    Returns:
        Tuple of (success, error_message, data)
        data contains: {"notifications": [...], "total": int, "unread_count": int}
    """
    url = f"{BASE_URL}/api/v1/notifications/me?unread_only=true"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return True, None, response.json()
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e.response.status_code} - {e.response.text}", None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


def get_all_notifications(token: str, page: int = 1, size: int = 50) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Get all notifications (read + unread) for current user

    Args:
        token: Authentication token
        page: Page number (default 1)
        size: Page size (default 50)

    Returns:
        Tuple of (success, error_message, data)
    """
    url = f"{BASE_URL}/api/v1/notifications/me?page={page}&size={size}"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return True, None, response.json()
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e.response.status_code} - {e.response.text}", None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


def mark_notification_as_read(token: str, notification_id: int) -> Tuple[bool, Optional[str]]:
    """
    Mark a single notification as read

    Args:
        token: Authentication token
        notification_id: ID of notification to mark as read

    Returns:
        Tuple of (success, error_message)
    """
    url = f"{BASE_URL}/api/v1/notifications/mark-read"

    try:
        response = requests.put(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"notification_ids": [notification_id]}
        )
        response.raise_for_status()
        return True, None
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def mark_all_notifications_as_read(token: str) -> Tuple[bool, Optional[str]]:
    """
    Mark all user's notifications as read

    Args:
        token: Authentication token

    Returns:
        Tuple of (success, error_message)
    """
    url = f"{BASE_URL}/api/v1/notifications/mark-all-read"

    try:
        response = requests.put(
            url,
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return True, None
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def get_unread_notification_count(token: str) -> int:
    """
    Get count of unread notifications (for badge display)

    Args:
        token: Authentication token

    Returns:
        Count of unread notifications (0 if error)
    """
    success, error, data = get_unread_notifications(token)

    if success and data:
        return data.get("unread_count", 0)

    return 0
