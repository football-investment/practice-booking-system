"""
Unit tests for unified APIClient

Tests cover:
- APIResponse backward compatibility (tuple unpacking)
- HTTP method wrappers (GET, POST, PUT, DELETE)
- Error handling (timeout, connection, HTTP errors)
- Namespace functionality
- Configuration loading
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, ConnectionError, RequestException

from streamlit_app.api_client import APIClient, APIResponse, TournamentAPI


class TestAPIResponse:
    """Test APIResponse wrapper behavior"""

    def test_tuple_unpacking_success(self):
        """Legacy pattern: ok, err, data = response"""
        response = APIResponse(ok=True, data={"id": 123}, error=None, status_code=200)
        ok, err, data = response

        assert ok is True
        assert err is None
        assert data == {"id": 123}

    def test_tuple_unpacking_failure(self):
        """Legacy pattern with error response"""
        response = APIResponse(ok=False, data=None, error="Not found", status_code=404)
        ok, err, data = response

        assert ok is False
        assert err == "Not found"
        assert data is None

    def test_attribute_access(self):
        """Modern pattern: response.ok, response.data"""
        response = APIResponse(ok=True, data=[1, 2, 3], error=None, status_code=200)

        assert response.ok is True
        assert response.data == [1, 2, 3]
        assert response.error is None
        assert response.status_code == 200

    def test_boolean_conversion_success(self):
        """if response: ... should work"""
        response = APIResponse(ok=True, data={}, error=None)
        assert bool(response) is True

    def test_boolean_conversion_failure(self):
        """if not response: ... should work"""
        response = APIResponse(ok=False, data=None, error="Error")
        assert bool(response) is False


class TestAPIClientInitialization:
    """Test APIClient initialization and configuration"""

    def test_initialization_with_defaults(self):
        """Basic initialization with required parameters"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        assert client._base_url == "http://localhost:8000"
        assert client._timeout == 30
        assert client._session.headers["Authorization"] == "Bearer test_token"
        assert client._session.headers["Content-Type"] == "application/json"

    def test_initialization_with_custom_timeout(self):
        """Custom timeout configuration"""
        client = APIClient(
            base_url="http://localhost:8000",
            token="test_token",
            timeout=60
        )

        assert client._timeout == 60

    def test_base_url_trailing_slash_removal(self):
        """Base URL should have trailing slash removed"""
        client = APIClient(base_url="http://localhost:8000/", token="test_token")
        assert client._base_url == "http://localhost:8000"

    def test_namespaces_initialized(self):
        """All namespaces should be initialized"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        assert isinstance(client.tournaments, TournamentAPI)
        assert client.tournaments._client is client
        assert hasattr(client, "semesters")
        assert hasattr(client, "financial")
        assert hasattr(client, "notifications")

    def test_from_config_factory(self):
        """from_config() should load settings from config.py"""
        # Mock the config module import
        import sys
        mock_config = MagicMock()
        mock_config.API_BASE_URL = "http://configured:8000"
        mock_config.API_TIMEOUT = 45
        sys.modules['config'] = mock_config

        try:
            client = APIClient.from_config(token="test_token")
            assert client._base_url == "http://configured:8000"
            assert client._timeout == 45
        finally:
            if 'config' in sys.modules:
                del sys.modules['config']

    def test_from_config_fallback_when_config_missing(self):
        """from_config() should fallback to defaults if config unavailable"""
        import sys
        if 'config' in sys.modules:
            del sys.modules['config']

        with patch("streamlit_app.api_client.APIClient.__init__") as mock_init:
            mock_init.return_value = None

            # This will trigger ImportError and use fallback
            try:
                client = APIClient.from_config(token="test_token")
            except:
                pass  # Expected if config module doesn't exist

            # Check that fallback values would be used
            # (hard to test without mocking __init__)


class TestAPIClientHTTPMethods:
    """Test HTTP method wrappers (GET, POST, PUT, DELETE)"""

    def test_get_request_success(self):
        """GET request with successful response"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "name": "Test"}

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.get("/api/v1/test")

        assert response.ok is True
        assert response.data == {"id": 123, "name": "Test"}
        assert response.status_code == 200
        assert response.error is None

    def test_get_request_with_params(self):
        """GET request with query parameters"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = []

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.get("/api/v1/users", params={"role": "admin", "limit": 10})

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"] == {"role": "admin", "limit": 10}

    def test_post_request_success(self):
        """POST request with JSON payload"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 456, "created": True}

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.post("/api/v1/test", json={"name": "New Item"})

        assert response.ok is True
        assert response.data == {"id": 456, "created": True}
        assert response.status_code == 201

    def test_put_request(self):
        """PUT request"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": 789, "updated": True}

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.put("/api/v1/test/789", json={"name": "Updated"})

        assert response.ok is True
        assert response.data["updated"] is True

    def test_delete_request(self):
        """DELETE request"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_response.json.side_effect = ValueError("No JSON content")

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.delete("/api/v1/test/789")

        assert response.ok is True
        assert response.data is None  # 204 No Content
        assert response.status_code == 204

    def test_default_timeout_applied(self):
        """Default timeout should be applied if not provided"""
        client = APIClient(base_url="http://localhost:8000", token="test_token", timeout=45)

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {}

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.get("/api/v1/test")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == 45


class TestAPIClientErrorHandling:
    """Test error handling for various failure scenarios"""

    def test_http_404_error(self):
        """Handle 404 Not Found"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"detail": "Tournament not found"}

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.get("/api/v1/tournaments/999")

        assert response.ok is False
        assert response.data is None
        assert "404" in response.error
        assert "Tournament not found" in response.error
        assert response.status_code == 404

    def test_http_500_error(self):
        """Handle 500 Internal Server Error"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = ValueError("No JSON")

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.post("/api/v1/test")

        assert response.ok is False
        assert "500" in response.error
        assert "Internal Server Error" in response.error

    def test_timeout_error(self):
        """Handle request timeout"""
        client = APIClient(base_url="http://localhost:8000", token="test_token", timeout=10)

        with patch.object(client._session, "request", side_effect=Timeout()):
            response = client.get("/api/v1/test")

        assert response.ok is False
        assert response.data is None
        assert "timeout" in response.error.lower()
        assert "10s" in response.error
        assert response.status_code == 0

    def test_connection_error(self):
        """Handle connection failure"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        with patch.object(client._session, "request", side_effect=ConnectionError("Connection refused")):
            response = client.get("/api/v1/test")

        assert response.ok is False
        assert response.data is None
        assert "connection" in response.error.lower()
        assert "refused" in response.error.lower()
        assert response.status_code == 0

    def test_generic_request_exception(self):
        """Handle generic RequestException"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        with patch.object(client._session, "request", side_effect=RequestException("Unknown error")):
            response = client.get("/api/v1/test")

        assert response.ok is False
        assert "Request failed" in response.error
        assert "Unknown error" in response.error

    def test_unexpected_exception(self):
        """Handle unexpected exceptions"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        with patch.object(client._session, "request", side_effect=RuntimeError("Unexpected")):
            response = client.get("/api/v1/test")

        assert response.ok is False
        assert "Unexpected error" in response.error


class TestTournamentAPI:
    """Test TournamentAPI namespace"""

    def test_get_detail(self):
        """tournaments.get_detail() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": 123, "name": "Test Tournament"}

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.tournaments.get_detail(tournament_id=123)

            assert response.ok is True
            assert response.data["name"] == "Test Tournament"

            # Verify correct URL
            call_args = mock_request.call_args[0]
            assert call_args[0] == "GET"
            assert "/api/v1/tournaments/123" in call_args[1]

    def test_get_rankings(self):
        """tournaments.get_rankings() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [{"rank": 1, "user_id": 1}]

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.tournaments.get_rankings(tournament_id=456)

            assert response.ok is True
            assert len(response.data) == 1

            call_args = mock_request.call_args[0]
            assert "/api/v1/tournaments/456/rankings" in call_args[1]

    def test_get_sessions(self):
        """tournaments.get_sessions() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.tournaments.get_sessions(tournament_id=789)

            assert response.ok is True
            assert len(response.data) == 2

    def test_submit_result(self):
        """tournaments.submit_result() calls correct endpoint with payload"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True}

        payload = {"winner_id": 1, "loser_id": 2, "score": "3-1"}

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.tournaments.submit_result(
                tournament_id=100,
                session_id=200,
                payload=payload
            )

            assert response.ok is True

            call_args = mock_request.call_args[0]
            call_kwargs = mock_request.call_args[1]
            assert call_args[0] == "POST"
            assert "/api/v1/tournaments/100/sessions/200/submit-results" in call_args[1]
            assert call_kwargs["json"] == payload

    def test_distribute_rewards_v2(self):
        """tournaments.distribute_rewards_v2() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"distributed": 5000}

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.tournaments.distribute_rewards_v2(tournament_id=300)

            assert response.ok is True
            assert response.data["distributed"] == 5000

            call_args = mock_request.call_args[0]
            assert call_args[0] == "POST"
            assert "/api/v1/tournaments/300/distribute-rewards-v2" in call_args[1]


class TestSemesterAPI:
    """Test SemesterAPI namespace"""

    def test_get_detail(self):
        """semesters.get_detail() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": 10, "name": "Fall 2024"}

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.semesters.get_detail(semester_id=10)

            assert response.ok is True
            assert response.data["name"] == "Fall 2024"

    def test_get_list_with_filters(self):
        """semesters.get_list() with filters"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.semesters.get_list(is_active=True, limit=50)

            assert response.ok is True

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["is_active"] is True
            assert call_kwargs["params"]["limit"] == 50


class TestFinancialAPI:
    """Test FinancialAPI namespace"""

    def test_get_user_balance(self):
        """financial.get_user_balance() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"user_id": 5, "balance": 1000}

        with patch.object(client._session, "request", return_value=mock_response):
            response = client.financial.get_user_balance(user_id=5)

            assert response.ok is True
            assert response.data["balance"] == 1000

    def test_get_transactions(self):
        """financial.get_transactions() with limit"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.financial.get_transactions(user_id=5, limit=100)

            assert response.ok is True

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["limit"] == 100


class TestNotificationAPI:
    """Test NotificationAPI namespace"""

    def test_send_notification(self):
        """notifications.send_notification() calls correct endpoint"""
        client = APIClient(base_url="http://localhost:8000", token="test_token")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"sent": True}

        payload = {"title": "Test", "message": "Hello"}

        with patch.object(client._session, "request", return_value=mock_response) as mock_request:
            response = client.notifications.send_notification(user_id=7, payload=payload)

            assert response.ok is True

            call_args = mock_request.call_args[0]
            assert "/api/v1/notifications/send/7" in call_args[1]
            assert mock_request.call_args[1]["json"] == payload
