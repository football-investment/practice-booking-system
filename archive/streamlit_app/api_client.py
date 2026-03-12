"""
Unified API Client for Practice Booking System

Consolidates 10 fragmented API helper files into a single, type-safe client.

Usage:
    from api_client import APIClient

    # New pattern (recommended)
    client = APIClient.from_config(token)
    response = client.tournaments.get_rankings(tid)
    if response.ok:
        rankings = response.data
    else:
        st.error(response.error)

    # Backward-compatible pattern (for migration)
    ok, err, data = response  # Tuple unpacking still works
"""

from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError


T = TypeVar("T")


@dataclass
class APIResponse(Generic[T]):
    """
    Unified API response wrapper with type safety and backward compatibility.

    Supports both modern attribute access and legacy tuple unpacking:
        response.ok, response.data, response.error
        ok, err, data = response  # Legacy pattern
    """
    ok: bool
    data: Optional[T]
    error: Optional[str]
    status_code: int = 0

    def __iter__(self):
        """Support legacy tuple unpacking: ok, err, data = response"""
        return iter((self.ok, self.error, self.data))

    def __bool__(self):
        """Allow: if response: ..."""
        return self.ok


class _BaseNamespace:
    """Base class for API namespaces"""
    def __init__(self, client: "APIClient"):
        self._client = client


class TournamentAPI(_BaseNamespace):
    """Tournament-related API endpoints"""

    def get_detail(self, tournament_id: int) -> APIResponse[Dict[str, Any]]:
        """Get tournament details by ID"""
        return self._client.get(f"/api/v1/tournaments/{tournament_id}")

    def get_rankings(self, tournament_id: int) -> APIResponse[List[Dict[str, Any]]]:
        """Get tournament rankings/leaderboard"""
        return self._client.get(f"/api/v1/tournaments/{tournament_id}/rankings")

    def get_sessions(self, tournament_id: int) -> APIResponse[List[Dict[str, Any]]]:
        """Get all sessions for a tournament"""
        return self._client.get(f"/api/v1/tournaments/{tournament_id}/sessions")

    def submit_result(
        self,
        tournament_id: int,
        session_id: int,
        payload: Dict[str, Any]
    ) -> APIResponse[Dict[str, Any]]:
        """Submit match result for a tournament session"""
        return self._client.post(
            f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results",
            json=payload
        )

    def distribute_rewards_v2(self, tournament_id: int) -> APIResponse[Dict[str, Any]]:
        """Distribute rewards using v2 endpoint (reward policy-based)"""
        return self._client.post(
            f"/api/v1/tournaments/{tournament_id}/distribute-rewards-v2",
            json={"tournament_id": tournament_id}
        )


class SemesterAPI(_BaseNamespace):
    """Semester-related API endpoints"""

    def get_detail(self, semester_id: int) -> APIResponse[Dict[str, Any]]:
        """Get semester details by ID"""
        return self._client.get(f"/api/v1/semesters/{semester_id}")

    def get_list(
        self,
        is_active: Optional[bool] = None,
        limit: int = 100
    ) -> APIResponse[List[Dict[str, Any]]]:
        """Get list of semesters with optional filtering"""
        params = {"limit": limit}
        if is_active is not None:
            params["is_active"] = is_active
        return self._client.get("/api/v1/semesters", params=params)


class FinancialAPI(_BaseNamespace):
    """Financial/credits-related API endpoints"""

    def get_user_balance(self, user_id: int) -> APIResponse[Dict[str, Any]]:
        """Get user's credit balance"""
        return self._client.get(f"/api/v1/users/{user_id}/credits")

    def get_transactions(
        self,
        user_id: int,
        limit: int = 50
    ) -> APIResponse[List[Dict[str, Any]]]:
        """Get user's transaction history"""
        return self._client.get(
            f"/api/v1/users/{user_id}/transactions",
            params={"limit": limit}
        )


class NotificationAPI(_BaseNamespace):
    """Notification-related API endpoints"""

    def send_notification(
        self,
        user_id: int,
        payload: Dict[str, Any]
    ) -> APIResponse[Dict[str, Any]]:
        """Send notification to a user"""
        return self._client.post(
            f"/api/v1/notifications/send/{user_id}",
            json=payload
        )


class APIClient:
    """
    Unified HTTP client for Practice Booking System API.

    Provides:
    - Centralized error handling
    - Consistent timeout/retry configuration
    - Type-safe response wrappers
    - Namespace-based endpoint organization
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """
        Initialize API client.

        Args:
            base_url: API base URL (e.g., http://localhost:8000)
            token: Bearer authentication token
            timeout: Request timeout in seconds (default: 30)
            verify_ssl: Verify SSL certificates (default: True)
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        self._session.verify = verify_ssl

        # Initialize namespaces
        self.tournaments = TournamentAPI(self)
        self.semesters = SemesterAPI(self)
        self.financial = FinancialAPI(self)
        self.notifications = NotificationAPI(self)

    @classmethod
    def from_config(cls, token: str) -> "APIClient":
        """
        Create APIClient from config.py settings.

        Args:
            token: Bearer authentication token

        Returns:
            Configured APIClient instance
        """
        try:
            from config import API_BASE_URL, API_TIMEOUT
            return cls(API_BASE_URL, token, timeout=API_TIMEOUT)
        except ImportError:
            # Fallback to defaults if config not available
            return cls("http://localhost:8000", token, timeout=30)

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """
        Send GET request.

        Args:
            path: API endpoint path (e.g., /api/v1/tournaments/123)
            params: Query parameters
            **kwargs: Additional requests arguments

        Returns:
            APIResponse with parsed JSON data
        """
        return self._request("GET", path, params=params, **kwargs)

    def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """
        Send POST request.

        Args:
            path: API endpoint path
            json: JSON payload
            **kwargs: Additional requests arguments

        Returns:
            APIResponse with parsed JSON data
        """
        return self._request("POST", path, json=json, **kwargs)

    def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Send PUT request"""
        return self._request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> APIResponse:
        """Send DELETE request"""
        return self._request("DELETE", path, **kwargs)

    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> APIResponse:
        """
        Internal request handler with centralized error handling.

        Handles:
        - Timeout errors
        - Connection errors
        - HTTP errors (4xx, 5xx)
        - JSON parsing errors
        """
        url = f"{self._base_url}{path}"

        # Set default timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = self._timeout

        try:
            response = self._session.request(method, url, **kwargs)

            # Success (2xx)
            if response.ok:
                try:
                    data = response.json()
                except ValueError:
                    # Non-JSON response (e.g., 204 No Content)
                    data = None

                return APIResponse(
                    ok=True,
                    data=data,
                    error=None,
                    status_code=response.status_code
                )

            # HTTP error (4xx, 5xx)
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", response.text)
                except ValueError:
                    error_msg = response.text

                return APIResponse(
                    ok=False,
                    data=None,
                    error=f"HTTP {response.status_code}: {error_msg}",
                    status_code=response.status_code
                )

        except Timeout:
            return APIResponse(
                ok=False,
                data=None,
                error=f"Request timeout after {kwargs.get('timeout', self._timeout)}s",
                status_code=0
            )

        except ConnectionError as e:
            return APIResponse(
                ok=False,
                data=None,
                error=f"Connection error: {str(e)}",
                status_code=0
            )

        except RequestException as e:
            return APIResponse(
                ok=False,
                data=None,
                error=f"Request failed: {str(e)}",
                status_code=0
            )

        except Exception as e:
            return APIResponse(
                ok=False,
                data=None,
                error=f"Unexpected error: {str(e)}",
                status_code=0
            )
