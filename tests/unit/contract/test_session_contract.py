"""
Contract tests — Session schemas

Validates that SessionBase and Session preserve required fields, types, and
defaults. Breaks immediately on any field rename or removal in
app/schemas/session.py without requiring a DB or server.
"""

from app.models.session import SessionType
from app.schemas.session import Session, SessionBase


class TestSessionBaseContract:
    """Contract: session creation fields (SessionBase schema)."""

    def test_session_base_has_title_field(self):
        assert "title" in SessionBase.model_fields

    def test_session_base_has_date_start_field(self):
        assert "date_start" in SessionBase.model_fields

    def test_session_base_has_date_end_field(self):
        assert "date_end" in SessionBase.model_fields

    def test_session_base_has_semester_id_field(self):
        assert "semester_id" in SessionBase.model_fields

    def test_session_base_has_capacity_field(self):
        assert "capacity" in SessionBase.model_fields

    def test_session_base_has_session_type_field(self):
        assert "session_type" in SessionBase.model_fields

    def test_session_base_title_is_required(self):
        assert SessionBase.model_fields["title"].is_required()

    def test_session_base_date_start_is_required(self):
        assert SessionBase.model_fields["date_start"].is_required()

    def test_session_base_date_end_is_required(self):
        assert SessionBase.model_fields["date_end"].is_required()

    def test_session_base_semester_id_is_required(self):
        assert SessionBase.model_fields["semester_id"].is_required()

    def test_session_base_capacity_defaults_to_20(self):
        assert SessionBase.model_fields["capacity"].default == 20

    def test_session_base_session_type_defaults_to_on_site(self):
        assert SessionBase.model_fields["session_type"].default == SessionType.on_site


class TestSessionResponseContract:
    """Contract: GET /api/v1/sessions/{id} response body (Session schema)."""

    def test_session_has_id_field(self):
        assert "id" in Session.model_fields

    def test_session_has_created_at_field(self):
        assert "created_at" in Session.model_fields

    def test_session_id_is_required(self):
        assert Session.model_fields["id"].is_required()

    def test_session_created_at_is_required(self):
        assert Session.model_fields["created_at"].is_required()

    def test_session_inherits_title_from_base(self):
        assert "title" in Session.model_fields

    def test_session_inherits_semester_id_from_base(self):
        assert "semester_id" in Session.model_fields
