"""
Centralized API Client for Streamlit Components - CSRF FIXED

Uses requests.Session() for automatic cookie management (CSRF tokens).
"""

import requests
from typing import Optional, Dict, Any, List, Union
import streamlit as st


class APIError(Exception):
    """Custom exception for API errors"""

    def __init__(self, status_code: int, message: str, detail: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail or {}
        super().__init__(f"API Error {status_code}: {message}")


class APIClient:
    """
    Centralized API client with automatic CSRF token handling via cookies.

    Uses requests.Session() to persist cookies across requests.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or "http://localhost:8000"
        # Get or create session from Streamlit session state
        if "requests_session" not in st.session_state:
            st.session_state["requests_session"] = requests.Session()
        self.session = st.session_state["requests_session"]

    def _get_headers(self, include_csrf: bool = False) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Auth token — check both key names used across the codebase
        token = st.session_state.get("auth_token") or st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # CSRF token from cookie (session handles this automatically)
        if include_csrf:
            csrf_token = self.session.cookies.get("csrf_token")
            if csrf_token:
                headers["X-CSRF-Token"] = csrf_token

        return headers

    def _handle_response(self, response: requests.Response) -> Union[Dict, List]:
        """Handle API response"""
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except ValueError:
                return {}

        # Error handling
        try:
            error_data = response.json()
            # Support both FastAPI {"detail": ...} and custom {"error": {"message": ...}} formats
            if "detail" in error_data:
                message = error_data["detail"]
            elif "error" in error_data and isinstance(error_data["error"], dict):
                message = error_data["error"].get("message", str(error_data["error"]))
            else:
                message = str(error_data) if error_data else f"HTTP {response.status_code}"

            if isinstance(message, list):
                errors = [f"{err.get('loc', ['?'])[-1]}: {err.get('msg', 'Invalid')}"
                         for err in message]
                message = "; ".join(errors)
            elif isinstance(message, dict):
                message = message.get("message", str(message))

        except ValueError:
            message = response.text or f"HTTP {response.status_code}"

        raise APIError(
            status_code=response.status_code,
            message=message,
            detail=error_data if 'error_data' in locals() else None
        )

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict, List]:
        """Make GET request"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            return self._handle_response(response)

        except requests.exceptions.RequestException as e:
            raise APIError(
                status_code=0,
                message=f"Network error: {str(e)}",
                detail={"error": str(e)}
            )

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, form_data: bool = False) -> Union[Dict, List]:
        """Make POST request with automatic CSRF token"""
        url = f"{self.base_url}{endpoint}"

        headers = self._get_headers(include_csrf=True)

        try:
            if form_data:
                headers.pop("Content-Type", None)
                response = self.session.post(
                    url,
                    headers=headers,
                    data=data,
                    timeout=30
                )
            else:
                response = self.session.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
            return self._handle_response(response)

        except requests.exceptions.RequestException as e:
            raise APIError(
                status_code=0,
                message=f"Network error: {str(e)}",
                detail={"error": str(e)}
            )

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Union[Dict, List]:
        """Make PATCH request"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.patch(
                url,
                headers=self._get_headers(include_csrf=True),
                json=data,
                timeout=30
            )
            return self._handle_response(response)

        except requests.exceptions.RequestException as e:
            raise APIError(
                status_code=0,
                message=f"Network error: {str(e)}",
                detail={"error": str(e)}
            )

    def delete(self, endpoint: str) -> Union[Dict, List]:
        """Make DELETE request"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.delete(
                url,
                headers=self._get_headers(include_csrf=True),
                timeout=30
            )
            return self._handle_response(response)

        except requests.exceptions.RequestException as e:
            raise APIError(
                status_code=0,
                message=f"Network error: {str(e)}",
                detail={"error": str(e)}
            )


# Singleton instance
api_client = APIClient()
