"""
Centralized API Client for Streamlit Components

Provides a unified interface for making API calls with:
- Automatic token management
- Consistent error handling
- Response validation
- Type hints for better IDE support
"""

import requests
from typing import Optional, Dict, Any, List, Union
import streamlit as st
from datetime import datetime


class APIError(Exception):
    """Custom exception for API errors with detailed information"""

    def __init__(self, status_code: int, message: str, detail: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail or {}
        super().__init__(f"API Error {status_code}: {message}")


class APIClient:
    """
    Centralized API client for all backend communication.

    Usage:
        client = APIClient()
        locations = client.get("/admin/locations")
        tournament = client.post("/tournaments", data={"name": "Test"})
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client.

        Args:
            base_url: Base URL for API. Defaults to http://localhost:8000
        """
        self.base_url = base_url or "http://localhost:8000"

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication token"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Get token from session state
        token = st.session_state.get("auth_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _handle_response(self, response: requests.Response) -> Union[Dict, List]:
        """
        Handle API response with consistent error handling.

        Args:
            response: Response object from requests

        Returns:
            Parsed JSON data

        Raises:
            APIError: If response indicates an error
        """
        # Success responses (2xx)
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except ValueError:
                # Empty response or non-JSON response
                return {}

        # Error responses
        try:
            error_data = response.json()
            message = error_data.get("detail", "Unknown error")

            # Handle FastAPI validation errors
            if isinstance(message, list):
                # Format validation errors nicely
                errors = [f"{err.get('loc', ['?'])[-1]}: {err.get('msg', 'Invalid')}"
                         for err in message]
                message = "; ".join(errors)
            elif isinstance(message, dict):
                # Extract nested error messages
                message = message.get("message", str(message))

        except ValueError:
            message = response.text or f"HTTP {response.status_code}"

        raise APIError(
            status_code=response.status_code,
            message=message,
            detail=error_data if 'error_data' in locals() else None
        )

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict, List]:
        """
        Make GET request to API.

        Args:
            endpoint: API endpoint (e.g., "/admin/locations")
            params: Query parameters

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(
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

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Union[Dict, List]:
        """
        Make POST request to API.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
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
        """
        Make PATCH request to API.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.patch(
                url,
                headers=self._get_headers(),
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
        """
        Make DELETE request to API.

        Args:
            endpoint: API endpoint

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            return self._handle_response(response)

        except requests.exceptions.RequestException as e:
            raise APIError(
                status_code=0,
                message=f"Network error: {str(e)}",
                detail={"error": str(e)}
            )


# Singleton instance for easy import
api_client = APIClient()
