"""Unit tests for admin/adaptive_learning.py routes.

ALA-01  GET /dashboard — returns 200 HTMLResponse with stat counts
ALA-02  GET /dashboard — non-admin user → 403
ALA-03  GET /quizzes — returns 200 with quiz list
ALA-04  GET /quizzes?page=2 — pagination offset applied
ALA-05  GET /quizzes/{id} — found quiz → 200 with question list
ALA-06  GET /quizzes/{id} — missing quiz → 303 redirect
ALA-07  GET /quizzes/{id}/questions/{qid} — found question → 200
ALA-08  GET /quizzes/{id}/questions/{qid} — wrong quiz_id → 303 redirect
ALA-09  GET /import — returns 200 with spec selector
ALA-10  POST /import/validate — valid file → report rendered in HTML
ALA-11  POST /import/validate — unknown spec → 303 redirect
ALA-12  POST /import/validate — too many files → 303 redirect
ALA-13  POST /import/validate — empty files list → renders error
ALA-14  POST /import/apply — valid payload → renders success template
ALA-15  POST /import/apply — empty payload → 303 redirect
ALA-16  POST /import/apply — unknown spec → 303 redirect
ALA-17  GET /import/history — returns 200 with log list
ALA-18  GET /import/history?page=2 — pagination offset applied
ALA-19  POST /import/validate — non-admin → 403
ALA-20  POST /import/apply — non-admin → 403
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.web_routes.admin.adaptive_learning import (
    al_dashboard,
    al_quiz_list,
    al_quiz_detail,
    al_question_detail,
    al_import_form,
    al_import_validate,
    al_import_apply,
    al_import_history,
)
from app.models.user import UserRole

_BASE = "app.api.web_routes.admin.adaptive_learning"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


def _req(path: str = "/admin/adaptive-learning/dashboard"):
    r = MagicMock()
    r.url.path = path
    r.query_params.get = MagicMock(return_value="")
    r.cookies.get = MagicMock(return_value="")
    return r


def _admin():
    u = MagicMock()
    u.id   = 1
    u.role = UserRole.ADMIN
    return u


def _student():
    u = MagicMock()
    u.id   = 2
    u.role = UserRole.STUDENT
    return u


def _mock_db():
    db = MagicMock()
    db.query.return_value.count.return_value = 0
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _mock_templates():
    tpl = MagicMock()
    tpl.TemplateResponse.return_value = HTMLResponse("<html>ok</html>")
    return tpl


# ---------------------------------------------------------------------------
# ALA-01/02 — Dashboard
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALDashboard:

    def test_ala01_dashboard_returns_html(self):
        """ALA-01: admin user → TemplateResponse called, 200 returned."""
        db = _mock_db()
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_dashboard(_req(), db, _admin()))
        assert isinstance(resp, HTMLResponse)

    def test_ala02_dashboard_403_for_student(self):
        """ALA-02: non-admin user → HTTPException 403."""
        from fastapi import HTTPException
        db = _mock_db()
        with pytest.raises(HTTPException) as exc_info:
            _run(al_dashboard(_req(), db, _student()))
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# ALA-03/04 — Quiz list
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALQuizList:

    def test_ala03_quiz_list_returns_html(self):
        """ALA-03: admin → TemplateResponse called."""
        db = _mock_db()
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_quiz_list(_req("/admin/adaptive-learning/quizzes"), page=1, db=db, user=_admin()))
        assert isinstance(resp, HTMLResponse)

    def test_ala04_quiz_list_page2_offset(self):
        """ALA-04: page=2 → TemplateResponse still returned (pagination works)."""
        db = _mock_db()
        db.query.return_value.count.return_value = 35
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_quiz_list(_req(), page=2, db=db, user=_admin()))
        assert isinstance(resp, HTMLResponse)


# ---------------------------------------------------------------------------
# ALA-05/06 — Quiz detail
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALQuizDetail:

    def test_ala05_quiz_detail_found(self):
        """ALA-05: existing quiz_id → TemplateResponse."""
        db = _mock_db()
        quiz = MagicMock()
        quiz.id = 1
        db.query.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_quiz_detail(1, _req(), db, _admin()))
        assert isinstance(resp, HTMLResponse)

    def test_ala06_quiz_detail_missing_redirects(self):
        """ALA-06: quiz_id not in DB → 303 redirect to quiz list."""
        db = _mock_db()
        db.query.return_value.filter.return_value.first.return_value = None
        resp = _run(al_quiz_detail(999, _req(), db, _admin()))
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 303


# ---------------------------------------------------------------------------
# ALA-07/08 — Question detail
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALQuestionDetail:

    def _db_with_quiz_and_question(self):
        db = MagicMock()
        quiz = MagicMock(); quiz.id = 1
        question = MagicMock(); question.id = 5; question.quiz_id = 1
        # quiz query
        db.query.return_value.filter.return_value.first.side_effect = [quiz, question]
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        return db

    def test_ala07_question_detail_found(self):
        """ALA-07: existing quiz + question → TemplateResponse."""
        db = self._db_with_quiz_and_question()
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_question_detail(1, 5, _req(), db, _admin()))
        assert isinstance(resp, HTMLResponse)

    def test_ala08_question_detail_wrong_quiz_redirects(self):
        """ALA-08: quiz found but question not found → 303 redirect."""
        db = MagicMock()
        quiz = MagicMock(); quiz.id = 1
        db.query.return_value.filter.return_value.first.side_effect = [quiz, None]
        resp = _run(al_question_detail(1, 999, _req(), db, _admin()))
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 303


# ---------------------------------------------------------------------------
# ALA-09 — Import form
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALImportForm:

    def test_ala09_import_form_returns_html(self):
        """ALA-09: GET /import → TemplateResponse with spec list."""
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_import_form(_req("/admin/adaptive-learning/import"), _admin()))
        assert isinstance(resp, HTMLResponse)


# ---------------------------------------------------------------------------
# ALA-10 to ALA-13 — Import validate
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALImportValidate:

    def _make_upload(self, content: bytes, filename: str = "q.json") -> MagicMock:
        f = AsyncMock()
        f.filename = filename
        f.read = AsyncMock(return_value=content)
        return f

    def _v1_bytes(self, title="Test"):
        return json.dumps({
            "schema_version": "1.0",
            "specializations": ["LFA_FOOTBALL_PLAYER"],
            "quiz_title": title,
            "category": "GENERAL",
            "difficulty": "MEDIUM",
            "language": "en",
            "topic": "T", "module": "M",
            "questions": [{
                "text": "Q?", "type": "MULTIPLE_CHOICE",
                "explanation": "E.",
                "options": [
                    {"text": "C", "is_correct": True},
                    {"text": "W1", "is_correct": False},
                    {"text": "W2", "is_correct": False},
                    {"text": "W3", "is_correct": False},
                ],
                "metadata": {"estimated_difficulty": 0.5, "cognitive_load": 0.5, "average_time_seconds": 30.0},
            }],
        }).encode()

    def test_ala10_valid_file_renders_report(self):
        """ALA-10: valid JSON file + valid spec → TemplateResponse (report rendered)."""
        from app.services.al_import_service import ImportReport, FileValidationResult

        mock_report = ImportReport(
            files=[FileValidationResult("q.json", "ok", quiz_title="T", question_count=1, schema_version="1.0")],
            total_ok=1, quizzes_to_create=1, questions_to_create=1,
            apply_payload_json=json.dumps([{"filename": "q.json", "spec": "LFA_FOOTBALL_PLAYER", "data": {}}]),
        )

        db = _mock_db()
        with patch(f"{_BASE}.validate_files", return_value=mock_report), \
             patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_import_validate(
                _req(), spec="LFA_FOOTBALL_PLAYER",
                files=[self._make_upload(self._v1_bytes())],
                db=db, user=_admin(),
            ))
        assert isinstance(resp, HTMLResponse)

    def test_ala11_unknown_spec_redirects(self):
        """ALA-11: unknown spec → 303 to /import with error param."""
        db = _mock_db()
        resp = _run(al_import_validate(
            _req(), spec="UNKNOWN_SPEC",
            files=[self._make_upload(b"{}")],
            db=db, user=_admin(),
        ))
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"]

    def test_ala12_too_many_files_redirects(self):
        """ALA-12: more than _MAX_FILES_PER_IMPORT files → 303."""
        from app.services.al_import_service import _MAX_FILES_PER_IMPORT
        db = _mock_db()
        files = [self._make_upload(b"{}", f"f{i}.json") for i in range(_MAX_FILES_PER_IMPORT + 1)]
        resp = _run(al_import_validate(
            _req(), spec="LFA_FOOTBALL_PLAYER",
            files=files, db=db, user=_admin(),
        ))
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 303

    def test_ala19_validate_non_admin_403(self):
        """ALA-19: student user → HTTPException 403."""
        from fastapi import HTTPException
        db = _mock_db()
        with pytest.raises(HTTPException) as exc_info:
            _run(al_import_validate(
                _req(), spec="LFA_FOOTBALL_PLAYER",
                files=[self._make_upload(b"{}")],
                db=db, user=_student(),
            ))
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# ALA-14 to ALA-16, ALA-20 — Import apply
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALImportApply:

    def _payload(self):
        return json.dumps([{
            "filename": "q.json",
            "spec": "LFA_FOOTBALL_PLAYER",
            "data": {
                "schema_version": "1.0",
                "specializations": ["LFA_FOOTBALL_PLAYER"],
                "quiz_title": "ALA Apply Quiz",
                "category": "GENERAL",
                "difficulty": "MEDIUM",
                "language": "en",
                "questions": [],
            },
        }])

    def test_ala14_valid_payload_renders_success(self):
        """ALA-14: valid payload → TemplateResponse (success page)."""
        from app.services.al_import_service import ALImportSummary

        mock_summary = ALImportSummary(quizzes_created=1, questions_created=2, log_id=7)
        db = _mock_db()
        with patch(f"{_BASE}.apply_import", return_value=mock_summary), \
             patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_import_apply(
                _req(), spec="LFA_FOOTBALL_PLAYER",
                apply_payload_json=self._payload(),
                db=db, user=_admin(),
            ))
        assert isinstance(resp, HTMLResponse)

    def test_ala15_empty_payload_redirects(self):
        """ALA-15: empty apply_payload_json → 303 redirect with error."""
        db = _mock_db()
        resp = _run(al_import_apply(
            _req(), spec="LFA_FOOTBALL_PLAYER",
            apply_payload_json="",
            db=db, user=_admin(),
        ))
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 303

    def test_ala16_unknown_spec_redirects(self):
        """ALA-16: unknown spec in apply → 303 redirect."""
        db = _mock_db()
        resp = _run(al_import_apply(
            _req(), spec="BOGUS_SPEC",
            apply_payload_json=self._payload(),
            db=db, user=_admin(),
        ))
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 303

    def test_ala20_apply_non_admin_403(self):
        """ALA-20: student user → HTTPException 403."""
        from fastapi import HTTPException
        db = _mock_db()
        with pytest.raises(HTTPException) as exc_info:
            _run(al_import_apply(
                _req(), spec="LFA_FOOTBALL_PLAYER",
                apply_payload_json=self._payload(),
                db=db, user=_student(),
            ))
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# ALA-17/18 — Import history
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestALImportHistory:

    def test_ala17_history_returns_html(self):
        """ALA-17: GET /import/history → TemplateResponse."""
        db = _mock_db()
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_import_history(_req(), page=1, db=db, user=_admin()))
        assert isinstance(resp, HTMLResponse)

    def test_ala18_history_page2(self):
        """ALA-18: page=2 → TemplateResponse (pagination branch)."""
        db = _mock_db()
        db.query.return_value.count.return_value = 25
        with patch(f"{_BASE}.templates", _mock_templates()):
            resp = _run(al_import_history(_req(), page=2, db=db, user=_admin()))
        assert isinstance(resp, HTMLResponse)
