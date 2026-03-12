"""
User Licenses Module

Provides API wrapper functions for license operations:
- User license retrieval
- Badge display support
"""

import requests
from typing import List, Dict, Any
from config import API_BASE_URL


def get_api_url() -> str:
    """Get base API URL from config"""
    return f"{API_BASE_URL}/api/v1"


def get_headers(token: str) -> dict:
    """Build authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# User License API (for badge display)
# ============================================================================

def get_user_licenses(token: str, user_id: int) -> List[Dict[str, Any]]:
    """
    Get all licenses for a specific user

    Args:
        token: Auth token
        user_id: User ID

    Returns:
        List of license dictionaries
    """
    try:
        url = f"{get_api_url()}/licenses/user/{user_id}"
        print(f"DEBUG: Fetching licenses from: {url}")

        response = requests.get(
            url,
            headers=get_headers(token),
            timeout=10
        )

        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response body: {response.text[:200]}")

        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: Returned {len(data)} licenses")
            return data
        else:
            print(f"DEBUG: Non-200 status, returning []")
            return []

    except Exception as e:
        print(f"Error fetching user licenses: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
