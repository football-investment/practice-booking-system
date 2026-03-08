"""
Contract tests — Semester schemas

Validates that SemesterBase and Semester preserve required fields, types, and
defaults. Breaks immediately on any field rename or removal in
app/schemas/semester.py without requiring a DB or server.
"""

from app.models.semester import SemesterStatus
from app.schemas.semester import Semester, SemesterBase


class TestSemesterBaseContract:
    """Contract: semester creation fields (SemesterBase schema)."""

    def test_semester_base_has_code_field(self):
        assert "code" in SemesterBase.model_fields

    def test_semester_base_has_name_field(self):
        assert "name" in SemesterBase.model_fields

    def test_semester_base_has_start_date_field(self):
        assert "start_date" in SemesterBase.model_fields

    def test_semester_base_has_end_date_field(self):
        assert "end_date" in SemesterBase.model_fields

    def test_semester_base_has_status_field(self):
        assert "status" in SemesterBase.model_fields

    def test_semester_base_has_is_active_field(self):
        assert "is_active" in SemesterBase.model_fields

    def test_semester_base_has_enrollment_cost_field(self):
        assert "enrollment_cost" in SemesterBase.model_fields

    def test_semester_base_code_is_required(self):
        assert SemesterBase.model_fields["code"].is_required()

    def test_semester_base_name_is_required(self):
        assert SemesterBase.model_fields["name"].is_required()

    def test_semester_base_start_date_is_required(self):
        assert SemesterBase.model_fields["start_date"].is_required()

    def test_semester_base_end_date_is_required(self):
        assert SemesterBase.model_fields["end_date"].is_required()

    def test_semester_base_status_defaults_to_draft(self):
        assert SemesterBase.model_fields["status"].default == SemesterStatus.DRAFT

    def test_semester_base_is_active_defaults_to_true(self):
        assert SemesterBase.model_fields["is_active"].default is True

    def test_semester_base_enrollment_cost_has_default(self):
        # Enrollment cost should have a sensible default (not required)
        assert not SemesterBase.model_fields["enrollment_cost"].is_required()


class TestSemesterResponseContract:
    """Contract: GET /api/v1/semesters/{id} response body (Semester schema)."""

    def test_semester_has_id_field(self):
        assert "id" in Semester.model_fields

    def test_semester_has_created_at_field(self):
        assert "created_at" in Semester.model_fields

    def test_semester_id_is_required(self):
        assert Semester.model_fields["id"].is_required()

    def test_semester_created_at_is_required(self):
        assert Semester.model_fields["created_at"].is_required()

    def test_semester_inherits_code_from_base(self):
        assert "code" in Semester.model_fields

    def test_semester_inherits_name_from_base(self):
        assert "name" in Semester.model_fields

    def test_semester_inherits_status_from_base(self):
        assert "status" in Semester.model_fields

    def test_semester_tournament_status_is_optional(self):
        # tournament_status is None by default (not all semesters are tournaments)
        assert not Semester.model_fields["tournament_status"].is_required()
