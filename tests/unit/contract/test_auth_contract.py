"""
Contract tests — Authentication schemas

Validates that the API response schema for auth endpoints preserves
required fields, types, and defaults. Any field rename or removal in
app/schemas/auth.py causes immediate failure here (no DB/server needed).
"""

from app.schemas.auth import ChangePassword, Login, Token


class TestTokenContract:
    """Contract: POST /api/v1/auth/login response body."""

    def test_token_has_access_token_field(self):
        assert "access_token" in Token.model_fields

    def test_token_has_refresh_token_field(self):
        assert "refresh_token" in Token.model_fields

    def test_token_has_token_type_field(self):
        assert "token_type" in Token.model_fields

    def test_access_token_is_required(self):
        assert Token.model_fields["access_token"].is_required()

    def test_refresh_token_is_required(self):
        assert Token.model_fields["refresh_token"].is_required()

    def test_token_type_has_bearer_default(self):
        t = Token(access_token="abc123", refresh_token="def456")
        assert t.token_type == "bearer"

    def test_token_instantiation_succeeds_with_minimal_data(self):
        t = Token(access_token="x", refresh_token="y")
        assert t.access_token == "x"
        assert t.refresh_token == "y"


class TestLoginContract:
    """Contract: POST /api/v1/auth/login request body."""

    def test_login_has_email_field(self):
        assert "email" in Login.model_fields

    def test_login_has_password_field(self):
        assert "password" in Login.model_fields

    def test_login_email_is_required(self):
        assert Login.model_fields["email"].is_required()

    def test_login_password_is_required(self):
        assert Login.model_fields["password"].is_required()


class TestChangePasswordContract:
    """Contract: POST /api/v1/auth/change-password request body."""

    def test_change_password_has_old_password_field(self):
        assert "old_password" in ChangePassword.model_fields

    def test_change_password_has_new_password_field(self):
        assert "new_password" in ChangePassword.model_fields

    def test_old_password_is_required(self):
        assert ChangePassword.model_fields["old_password"].is_required()

    def test_new_password_is_required(self):
        assert ChangePassword.model_fields["new_password"].is_required()
