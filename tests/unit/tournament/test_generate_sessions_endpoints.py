"""
Unit tests — tournaments/generate_sessions.py

Covers:
  _is_celery_available:
    CA-01  exception → False
    CA-02  ping success → True

  _run_generation_in_background:
    BG-01  success path → status="done"
    BG-02  exception path → status="error"
    BG-03  campus_overrides_raw provided, config found
    BG-04  campus_overrides_raw provided, config not found (no crash)

  _assert_campus_scope (SystemEvent emission branches — db provided):
    SC-01  instructor multi-campus + db → emit event + 403
    SC-02  instructor multi-override + db → emit event + 403
    SC-03  SystemEvent emit exception in campus_ids block → non-fatal, still 403
    SC-04  SystemEvent emit exception in overrides block → non-fatal, still 403

  preview_tournament_sessions:
    PV-01  no tournament_type_id → 400
    PV-02  tournament_type not found → 404
    PV-03  player_count < min_players → 400
    PV-04  invalid player_count (validate_player_count False) → 400
    PV-05  type=league → calls _generate_league_sessions
    PV-06  type=knockout → calls _generate_knockout_sessions
    PV-07  type=group_knockout → calls _generate_group_knockout_sessions
    PV-08  type=swiss → calls _generate_swiss_sessions
    PV-09  unknown type → 400

  generate_tournament_sessions:
    GS-01  campus scope 403 (instructor multi-campus)
    GS-02  can_generate False → 400
    GS-03  sync path success → sessions list
    GS-04  sync path failure → 500
    GS-05  async thread path (player_count >= threshold, no Celery)
    GS-06  campus_schedule_overrides serialized + tournament_config_obj persisted
    GS-07  async Celery path (player_count >= threshold, Celery available)

  get_generation_status:
    ST-01  Celery SUCCESS with result dict
    ST-02  Celery FAILURE → message from result
    ST-03  Celery non-PENDING (STARTED) → mapped status
    ST-04  Celery exception → thread fallback, found
    ST-05  task_id not in registry → 404
    ST-06  tournament_id mismatch → 404
    ST-07  Celery PENDING + result=None → falls through to thread registry

  get_tournament_sessions:
    TS-01  empty sessions list
    TS-02  sessions with participants, attendance found
    TS-03  participant uid=None → skipped
    TS-04  participant uid valid but not in users_by_id → skipped
    TS-05  ROUNDS_BASED session result_submitted logic
    TS-06  non-ROUNDS_BASED with game_results

  delete_generated_sessions:
    DS-01  no auto-generated sessions → early return
    DS-02  sessions exist → delete attendance + sessions + reset flags
"""
import pytest
import threading
from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace
from fastapi import HTTPException

from app.models.user import UserRole
from app.api.api_v1.endpoints.tournaments.generate_sessions import (
    _is_celery_available,
    _run_generation_in_background,
    _assert_campus_scope,
    preview_tournament_sessions,
    generate_tournament_sessions,
    get_generation_status,
    get_tournament_sessions,
    delete_generated_sessions,
    _task_registry,
    _registry_lock,
    BACKGROUND_GENERATION_THRESHOLD,
)

_BASE = "app.api.api_v1.endpoints.tournaments.generate_sessions"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _user(role=UserRole.ADMIN, uid=42):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.email = "admin@lfa.com"
    return u


def _db():
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = []
    q.first.return_value = None
    q.count.return_value = 0
    q.delete.return_value = 0
    db.query.return_value = q
    return db


def _fq(first=None, all_=None, count_val=0, delete_val=0):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.in_.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ or []
    q.count.return_value = count_val
    q.delete.return_value = delete_val
    return q


# ─── _is_celery_available ────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestIsCeleryAvailable:
    def test_exception_returns_false(self):
        """CA-01"""
        mock_module = MagicMock()
        mock_module.celery_app.control.ping.side_effect = Exception("no redis")
        with patch.dict("sys.modules", {"app.celery_app": mock_module}):
            result = _is_celery_available()
        assert result is False

    def test_ping_success_returns_true(self):
        """CA-02"""
        mock_module = MagicMock()
        mock_module.celery_app.control.ping.return_value = [{"worker": "pong"}]
        with patch.dict("sys.modules", {"app.celery_app": mock_module}):
            result = _is_celery_available()
        assert result is True


# ─── _run_generation_in_background ───────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestRunGenerationInBackground:
    def _add_task(self, task_id, tournament_id=7):
        with _registry_lock:
            _task_registry[task_id] = {
                "status": "pending",
                "tournament_id": tournament_id,
                "player_count": 10,
                "message": None,
                "sessions_count": 0,
            }

    def test_success_path_sets_done(self):
        """BG-01"""
        task_id = "bg-test-01"
        self._add_task(task_id)
        mock_db = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate_sessions.return_value = (True, "Done", ["s1", "s2"])
        with patch(f"{_BASE}.SessionLocal", return_value=mock_db), \
             patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen):
            _run_generation_in_background(task_id, 7, 1, 90, 15, 1, None)
        with _registry_lock:
            assert _task_registry[task_id]["status"] == "done"
            assert _task_registry[task_id]["sessions_count"] == 2
        del _task_registry[task_id]

    def test_exception_sets_error(self):
        """BG-02"""
        task_id = "bg-test-02"
        self._add_task(task_id)
        mock_db = MagicMock()
        with patch(f"{_BASE}.SessionLocal", return_value=mock_db), \
             patch(f"{_BASE}.TournamentSessionGenerator",
                   side_effect=RuntimeError("crash")):
            _run_generation_in_background(task_id, 7, 1, 90, 15, 1, None)
        with _registry_lock:
            assert _task_registry[task_id]["status"] == "error"
            assert "crash" in _task_registry[task_id]["message"]
        del _task_registry[task_id]

    def test_campus_overrides_config_found(self):
        """BG-03: campus_overrides_raw provided, config found → persisted"""
        task_id = "bg-test-03"
        self._add_task(task_id)
        mock_db = MagicMock()
        mock_config = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = mock_config
        mock_db.query.return_value = q
        mock_gen = MagicMock()
        mock_gen.generate_sessions.return_value = (True, "OK", [])
        overrides = {"42": {"parallel_fields": 2}}
        with patch(f"{_BASE}.SessionLocal", return_value=mock_db), \
             patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch("app.models.tournament_configuration.TournamentConfiguration"):
            _run_generation_in_background(task_id, 7, 1, 90, 15, 1, overrides)
        assert mock_config.campus_schedule_overrides == overrides
        del _task_registry[task_id]

    def test_campus_overrides_config_not_found(self):
        """BG-04: campus_overrides_raw provided, config NOT found → no crash"""
        task_id = "bg-test-04"
        self._add_task(task_id)
        mock_db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None  # no config
        mock_db.query.return_value = q
        mock_gen = MagicMock()
        mock_gen.generate_sessions.return_value = (True, "OK", [])
        with patch(f"{_BASE}.SessionLocal", return_value=mock_db), \
             patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch("app.models.tournament_configuration.TournamentConfiguration"):
            _run_generation_in_background(task_id, 7, 1, 90, 15, 1, {"42": {}})
        with _registry_lock:
            assert _task_registry[task_id]["status"] == "done"
        del _task_registry[task_id]


# ─── _assert_campus_scope (SystemEvent branches) ─────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestAssertCampusScopeSystemEvent:
    """Test that SystemEvent is emitted when db is provided."""

    def _instructor(self):
        return _user(UserRole.INSTRUCTOR, uid=42)

    def test_multi_campus_with_db_emits_event_then_403(self):
        """SC-01: instructor + db + >1 campus_ids → emit + 403"""
        db = MagicMock()
        mock_svc = MagicMock()
        with patch("app.services.system_event_service.SystemEventService",
                   return_value=mock_svc), \
             patch("app.models.system_event.SystemEventLevel"), \
             patch("app.models.system_event.SystemEventType"):
            with pytest.raises(HTTPException) as ei:
                _assert_campus_scope(self._instructor(), [1, 2], None, db)
        assert ei.value.status_code == 403
        mock_svc.emit.assert_called_once()

    def test_multi_override_with_db_emits_event_then_403(self):
        """SC-02: instructor + db + >1 override keys → emit + 403"""
        db = MagicMock()
        mock_svc = MagicMock()
        with patch("app.services.system_event_service.SystemEventService",
                   return_value=mock_svc), \
             patch("app.models.system_event.SystemEventLevel"), \
             patch("app.models.system_event.SystemEventType"):
            with pytest.raises(HTTPException) as ei:
                _assert_campus_scope(
                    self._instructor(), None, {"1": {}, "2": {}}, db
                )
        assert ei.value.status_code == 403
        mock_svc.emit.assert_called_once()

    def test_emit_exception_is_non_fatal(self):
        """SC-03: SystemEvent emit raises in campus_ids block → non-fatal, still 403"""
        db = MagicMock()
        with patch("app.services.system_event_service.SystemEventService",
                   side_effect=RuntimeError("event store down")):
            with pytest.raises(HTTPException) as ei:
                _assert_campus_scope(self._instructor(), [1, 2], None, db)
        assert ei.value.status_code == 403

    def test_overrides_block_emit_exception_non_fatal(self):
        """SC-04: SystemEvent emit raises in overrides block → non-fatal, still 403"""
        db = MagicMock()
        # campus_ids=None so campus_ids check passes; overrides has >1 key
        with patch("app.services.system_event_service.SystemEventService",
                   side_effect=RuntimeError("event store down")):
            with pytest.raises(HTTPException) as ei:
                _assert_campus_scope(
                    self._instructor(), None, {"1": {}, "2": {}}, db
                )
        assert ei.value.status_code == 403
        assert "campus_schedule_overrides" in ei.value.detail


# ─── preview_tournament_sessions ─────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestPreviewTournamentSessions:
    def _make_tournament(self, type_id=1, match_dur=None, break_dur=None):
        t = MagicMock()
        t.tournament_type_id = type_id
        t.match_duration_minutes = match_dur
        t.break_duration_minutes = break_dur
        t.name = "Test Cup"
        return t

    def _make_tt(self, code="league", min_players=4):
        tt = MagicMock()
        tt.code = code
        tt.min_players = min_players
        tt.validate_player_count.return_value = (True, "")
        tt.display_name = code.capitalize()
        tt.estimate_duration.return_value = {
            "total_matches": 6, "total_rounds": 3,
            "estimated_duration_minutes": 540
        }
        return tt

    def test_no_tournament_type_id_raises_400(self):
        """PV-01"""
        t = self._make_tournament(type_id=None)
        with patch(f"{_BASE}.TournamentRepository") as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as ei:
                preview_tournament_sessions(
                    tournament_id=1, db=_db(), current_user=_user()
                )
        assert ei.value.status_code == 400

    def test_tournament_type_not_found_raises_404(self):
        """PV-02"""
        t = self._make_tournament(type_id=1)
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"):
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as ei:
                preview_tournament_sessions(
                    tournament_id=1, db=db, current_user=_user()
                )
        assert ei.value.status_code == 404

    def test_player_count_less_than_min_raises_400(self):
        """PV-03"""
        t = self._make_tournament()
        tt = self._make_tt(min_players=8)
        db = MagicMock()
        q_tt = _fq(first=tt)
        q_enroll = _fq(count_val=2)  # only 2 enrolled, min=8
        n = [0]
        def _side(*args):
            n[0] += 1
            return q_tt if n[0] == 1 else q_enroll
        db.query.side_effect = _side
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"):
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as ei:
                preview_tournament_sessions(
                    tournament_id=1, db=db, current_user=_user()
                )
        assert ei.value.status_code == 400

    def test_invalid_player_count_raises_400(self):
        """PV-04: validate_player_count returns False"""
        t = self._make_tournament()
        tt = self._make_tt()
        tt.validate_player_count.return_value = (False, "Must be power of 2")
        db = MagicMock()
        q_tt = _fq(first=tt)
        q_enroll = _fq(count_val=5)
        n = [0]
        def _side(*args):
            n[0] += 1
            return q_tt if n[0] == 1 else q_enroll
        db.query.side_effect = _side
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"):
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as ei:
                preview_tournament_sessions(
                    tournament_id=1, db=db, current_user=_user()
                )
        assert ei.value.status_code == 400

    def _setup_preview(self, type_code):
        t = self._make_tournament()
        tt = self._make_tt(code=type_code)
        db = MagicMock()
        q_tt = _fq(first=tt)
        q_enroll = _fq(count_val=4)
        n = [0]
        def _side(*args):
            n[0] += 1
            return q_tt if n[0] == 1 else q_enroll
        db.query.side_effect = _side
        return t, tt, db

    def test_league_type_calls_generate_league(self):
        """PV-05"""
        t, tt, db = self._setup_preview("league")
        mock_gen = MagicMock()
        mock_gen._generate_league_sessions.return_value = []
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"), \
             patch(f"{_BASE}.TournamentSessionGenerator",
                   return_value=mock_gen):
            MockRepo.return_value.get_or_404.return_value = t
            result = preview_tournament_sessions(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_gen._generate_league_sessions.assert_called_once()
        assert result["player_count"] == 4

    def test_knockout_type_calls_generate_knockout(self):
        """PV-06"""
        t, tt, db = self._setup_preview("knockout")
        mock_gen = MagicMock()
        mock_gen._generate_knockout_sessions.return_value = []
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"), \
             patch(f"{_BASE}.TournamentSessionGenerator",
                   return_value=mock_gen):
            MockRepo.return_value.get_or_404.return_value = t
            preview_tournament_sessions(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_gen._generate_knockout_sessions.assert_called_once()

    def test_group_knockout_type_calls_generate_group_knockout(self):
        """PV-07"""
        t, tt, db = self._setup_preview("group_knockout")
        mock_gen = MagicMock()
        mock_gen._generate_group_knockout_sessions.return_value = []
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"), \
             patch(f"{_BASE}.TournamentSessionGenerator",
                   return_value=mock_gen):
            MockRepo.return_value.get_or_404.return_value = t
            preview_tournament_sessions(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_gen._generate_group_knockout_sessions.assert_called_once()

    def test_swiss_type_calls_generate_swiss(self):
        """PV-08"""
        t, tt, db = self._setup_preview("swiss")
        mock_gen = MagicMock()
        mock_gen._generate_swiss_sessions.return_value = []
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"), \
             patch(f"{_BASE}.TournamentSessionGenerator",
                   return_value=mock_gen):
            MockRepo.return_value.get_or_404.return_value = t
            preview_tournament_sessions(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_gen._generate_swiss_sessions.assert_called_once()

    def test_unknown_type_raises_400(self):
        """PV-09"""
        t, tt, db = self._setup_preview("unknown_format")
        mock_gen = MagicMock()
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}.TournamentType"), \
             patch(f"{_BASE}.TournamentSessionGenerator",
                   return_value=mock_gen):
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as ei:
                preview_tournament_sessions(
                    tournament_id=1, db=db, current_user=_user()
                )
        assert ei.value.status_code == 400


# ─── generate_tournament_sessions ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGenerateTournamentSessions:
    def _make_request(self, campus_ids=None, overrides=None):
        req = MagicMock()
        req.campus_ids = campus_ids
        req.campus_schedule_overrides = overrides
        req.parallel_fields = 1
        req.session_duration_minutes = 90
        req.break_minutes = 15
        req.number_of_rounds = 1
        return req

    def _make_tournament(self):
        t = MagicMock()
        t.match_duration_minutes = None
        t.break_duration_minutes = None
        t.parallel_fields = None
        t.number_of_rounds = None
        t.tournament_config_obj = None
        t.name = "Test Cup"
        return t

    def test_campus_scope_403_instructor_multi_campus(self):
        """GS-01"""
        req = self._make_request(campus_ids=[1, 2])
        with pytest.raises(HTTPException) as ei:
            generate_tournament_sessions(
                tournament_id=1, request=req, db=_db(),
                current_user=_user(UserRole.INSTRUCTOR)
            )
        assert ei.value.status_code == 403

    def test_can_generate_false_raises_400(self):
        """GS-02"""
        req = self._make_request()
        mock_gen = MagicMock()
        mock_gen.can_generate_sessions.return_value = (False, "Not ready")
        # SemesterEnrollment/EnrollmentStatus are lazy imports inside function body
        with patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen):
            with pytest.raises(HTTPException) as ei:
                generate_tournament_sessions(
                    tournament_id=1, request=req, db=_db(), current_user=_user()
                )
        assert ei.value.status_code == 400
        assert "Not ready" in ei.value.detail

    def test_sync_path_success(self):
        """GS-03: player_count < threshold → sync"""
        req = self._make_request()
        t = self._make_tournament()
        mock_gen = MagicMock()
        mock_gen.can_generate_sessions.return_value = (True, "")
        mock_gen.generate_sessions.return_value = (True, "OK", ["s1", "s2"])
        db = MagicMock()
        q_enroll = _fq(count_val=4)  # < threshold
        db.query.return_value = q_enroll
        with patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch(f"{_BASE}.TournamentRepository") as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = generate_tournament_sessions(
                tournament_id=1, request=req, db=db, current_user=_user()
            )
        assert result["success"] is True
        assert result["async"] is False
        assert result["sessions_generated_count"] == 2

    def test_sync_path_failure_raises_500(self):
        """GS-04"""
        req = self._make_request()
        t = self._make_tournament()
        mock_gen = MagicMock()
        mock_gen.can_generate_sessions.return_value = (True, "")
        mock_gen.generate_sessions.return_value = (False, "Generation failed", [])
        db = MagicMock()
        q_enroll = _fq(count_val=4)
        db.query.return_value = q_enroll
        with patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch(f"{_BASE}.TournamentRepository") as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as ei:
                generate_tournament_sessions(
                    tournament_id=1, request=req, db=db, current_user=_user()
                )
        assert ei.value.status_code == 500

    def test_async_thread_path(self):
        """GS-05: player_count >= threshold, Celery unavailable → thread"""
        req = self._make_request()
        t = self._make_tournament()
        mock_gen = MagicMock()
        mock_gen.can_generate_sessions.return_value = (True, "")
        db = MagicMock()
        q_enroll = _fq(count_val=BACKGROUND_GENERATION_THRESHOLD)  # >= threshold
        db.query.return_value = q_enroll
        mock_thread = MagicMock()
        with patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}._is_celery_available", return_value=False), \
             patch(f"{_BASE}.threading") as mock_threading:
            mock_threading.Thread.return_value = mock_thread
            mock_threading.Lock.return_value = _registry_lock
            MockRepo.return_value.get_or_404.return_value = t
            result = generate_tournament_sessions(
                tournament_id=1, request=req, db=db, current_user=_user()
            )
        assert result["success"] is True
        assert result["async"] is True
        assert "task_id" in result
        assert result["async_backend"] == "thread"

    def test_campus_overrides_serialized_and_config_persisted(self):
        """GS-06: campus_schedule_overrides is not None + tournament_config_obj truthy → persisted"""
        override_cfg = MagicMock()
        override_cfg.model_dump.return_value = {"parallel_fields": 2}
        req = self._make_request(overrides={"42": override_cfg})
        t = self._make_tournament()
        t.tournament_config_obj = MagicMock()  # truthy → trigger persist branch
        mock_gen = MagicMock()
        mock_gen.can_generate_sessions.return_value = (True, "")
        mock_gen.generate_sessions.return_value = (True, "OK", [])
        db = MagicMock()
        q_enroll = _fq(count_val=4)  # sync path
        db.query.return_value = q_enroll
        with patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch(f"{_BASE}.TournamentRepository") as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = generate_tournament_sessions(
                tournament_id=1, request=req, db=db, current_user=_user()
            )
        assert result["success"] is True
        assert result["async"] is False
        # campus_schedule_overrides was serialized and persisted
        assert t.tournament_config_obj.campus_schedule_overrides == {"42": {"parallel_fields": 2}}
        db.flush.assert_called_once()

    def test_async_celery_path(self):
        """GS-07: player_count >= threshold, Celery available → Celery task"""
        req = self._make_request()
        t = self._make_tournament()
        mock_gen = MagicMock()
        mock_gen.can_generate_sessions.return_value = (True, "")
        db = MagicMock()
        q_enroll = _fq(count_val=BACKGROUND_GENERATION_THRESHOLD)
        db.query.return_value = q_enroll
        mock_celery_result = MagicMock()
        mock_celery_result.id = "celery-task-id-abc"
        mock_task = MagicMock()
        mock_task.apply_async.return_value = mock_celery_result
        with patch(f"{_BASE}.TournamentSessionGenerator", return_value=mock_gen), \
             patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch(f"{_BASE}._is_celery_available", return_value=True), \
             patch.dict("sys.modules", {
                 "app.tasks.tournament_tasks": MagicMock(
                     generate_sessions_task=mock_task
                 ),
             }):
            MockRepo.return_value.get_or_404.return_value = t
            result = generate_tournament_sessions(
                tournament_id=1, request=req, db=db, current_user=_user()
            )
        assert result["success"] is True
        assert result["async"] is True
        assert result["task_id"] == "celery-task-id-abc"
        assert result["async_backend"] == "celery"
        mock_task.apply_async.assert_called_once()


# ─── get_generation_status ───────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGetGenerationStatus:
    def test_celery_success_with_result_dict(self):
        """ST-01"""
        mock_ar = MagicMock()
        mock_ar.state = "SUCCESS"
        mock_ar.result = {
            "sessions_count": 28,
            "message": "done",
            "generation_duration_ms": 100,
            "db_write_time_ms": 50,
            "queue_wait_time_ms": 10,
        }
        with patch.dict("sys.modules", {
            "celery.result": MagicMock(AsyncResult=MagicMock(return_value=mock_ar)),
            "app.celery_app": MagicMock(),
        }):
            result = get_generation_status(
                tournament_id=7, task_id="abc123",
                current_user=_user()
            )
        assert result["status"] == "done"
        assert result["sessions_count"] == 28
        assert result["backend"] == "celery"

    def test_celery_failure_returns_error_message(self):
        """ST-02"""
        mock_ar = MagicMock()
        mock_ar.state = "FAILURE"
        mock_ar.result = Exception("worker crashed")
        with patch.dict("sys.modules", {
            "celery.result": MagicMock(AsyncResult=MagicMock(return_value=mock_ar)),
            "app.celery_app": MagicMock(),
        }):
            result = get_generation_status(
                tournament_id=7, task_id="abc123",
                current_user=_user()
            )
        assert result["status"] == "error"
        assert "crashed" in result["message"]

    def test_celery_started_maps_to_running(self):
        """ST-03"""
        mock_ar = MagicMock()
        mock_ar.state = "STARTED"
        mock_ar.result = None
        with patch.dict("sys.modules", {
            "celery.result": MagicMock(AsyncResult=MagicMock(return_value=mock_ar)),
            "app.celery_app": MagicMock(),
        }):
            result = get_generation_status(
                tournament_id=7, task_id="abc123",
                current_user=_user()
            )
        assert result["status"] == "running"

    def test_celery_exception_falls_through_to_thread_registry(self):
        """ST-04: celery import raises → fall through to thread registry"""
        task_id = "thread-task-01"
        with _registry_lock:
            _task_registry[task_id] = {
                "status": "done",
                "tournament_id": 7,
                "message": "All good",
                "sessions_count": 5,
            }
        with patch.dict("sys.modules", {
            "celery.result": None,
            "app.celery_app": None,
        }):
            result = get_generation_status(
                tournament_id=7, task_id=task_id,
                current_user=_user()
            )
        assert result["status"] == "done"
        del _task_registry[task_id]

    def test_task_not_found_raises_404(self):
        """ST-05"""
        with patch.dict("sys.modules", {"celery.result": None, "app.celery_app": None}):
            with pytest.raises(HTTPException) as ei:
                get_generation_status(
                    tournament_id=7, task_id="nonexistent-xyz",
                    current_user=_user()
                )
        assert ei.value.status_code == 404

    def test_tournament_id_mismatch_raises_404(self):
        """ST-06"""
        task_id = "thread-task-02"
        with _registry_lock:
            _task_registry[task_id] = {
                "status": "done",
                "tournament_id": 999,  # different tournament
            }
        with patch.dict("sys.modules", {"celery.result": None, "app.celery_app": None}):
            with pytest.raises(HTTPException) as ei:
                get_generation_status(
                    tournament_id=7,  # mismatch!
                    task_id=task_id,
                    current_user=_user()
                )
        assert ei.value.status_code == 404
        del _task_registry[task_id]

    def test_celery_pending_no_result_falls_through_to_thread(self):
        """ST-07: Celery state=PENDING + result=None → False branch at 602, falls to thread registry"""
        task_id = "thread-task-03"
        with _registry_lock:
            _task_registry[task_id] = {
                "status": "pending",
                "tournament_id": 7,
                "message": None,
                "sessions_count": 0,
            }
        mock_ar = MagicMock()
        mock_ar.state = "PENDING"
        mock_ar.result = None  # condition: state=="PENDING" AND result is None → False → fall through
        with patch.dict("sys.modules", {
            "celery.result": MagicMock(AsyncResult=MagicMock(return_value=mock_ar)),
            "app.celery_app": MagicMock(),
        }):
            result = get_generation_status(
                tournament_id=7, task_id=task_id,
                current_user=_user()
            )
        assert result["status"] == "pending"
        del _task_registry[task_id]


# ─── get_tournament_sessions ─────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGetTournamentSessions:
    def _session_db(self, sessions):
        """DB mock: first query=sessions, then users, then attendances."""
        db = MagicMock()
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.in_.return_value = q
            q.all.return_value = sessions if n[0] == 1 else []
            return q
        db.query.side_effect = _side
        return db

    def test_empty_sessions_returns_empty_list(self):
        """TS-01"""
        # User and Attendance are lazy imports — no patch needed with mocked db
        result = get_tournament_sessions(
            tournament_id=7, db=self._session_db([]), current_user=_user()
        )
        assert result == []

    def test_session_with_participants_and_attendance(self):
        """TS-02"""
        user = MagicMock()
        user.id = 42
        user.name = "Player One"
        user.nickname = None
        user.email = "p1@lfa.com"
        attendance = MagicMock()
        attendance.status.value = "present"
        attendance.session_id = 1
        attendance.user_id = 42
        session = MagicMock()
        session.id = 1
        session.participant_user_ids = [42]
        session.game_results = {"winner": 42}
        session.rounds_data = None
        session.scoring_type = "PLACEMENT"
        session.date_start = MagicMock()
        session.date_start.isoformat.return_value = "2026-03-01T09:00:00"
        session.date_end = MagicMock()
        session.date_end.isoformat.return_value = "2026-03-01T10:30:00"
        db = MagicMock()
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.in_.return_value = q
            if n[0] == 1:
                q.all.return_value = [session]
            elif n[0] == 2:
                q.all.return_value = [user]
            else:
                q.all.return_value = [attendance]
            return q
        db.query.side_effect = _side
        result = get_tournament_sessions(
            tournament_id=7, db=db, current_user=_user()
        )
        assert len(result) == 1
        assert result[0]["participants"][0]["id"] == 42

    def test_participant_uid_none_skipped(self):
        """TS-03"""
        session = MagicMock()
        session.id = 1
        session.participant_user_ids = [None, None]
        session.game_results = {}
        session.rounds_data = None
        session.scoring_type = "PLACEMENT"
        session.date_start = None
        session.date_end = None
        result = get_tournament_sessions(
            tournament_id=7, db=self._session_db([session]), current_user=_user()
        )
        assert result[0]["participants"] == []

    def test_participant_uid_not_in_users_by_id_skipped(self):
        """TS-04: uid present in participant_user_ids but not fetched from DB → skipped"""
        session = MagicMock()
        session.id = 1
        session.participant_user_ids = [99]  # uid=99 not in users_by_id
        session.game_results = {}
        session.rounds_data = None
        session.scoring_type = "PLACEMENT"
        session.date_start = None
        session.date_end = None
        # second db.query returns empty user list → users_by_id = {}
        db = MagicMock()
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.in_.return_value = q
            if n[0] == 1:
                q.all.return_value = [session]
            else:
                q.all.return_value = []  # no users, no attendance
            return q
        db.query.side_effect = _side
        result = get_tournament_sessions(
            tournament_id=7, db=db, current_user=_user()
        )
        assert result[0]["participants"] == []

    def test_rounds_based_result_submitted_logic(self):
        """TS-05: ROUNDS_BASED with completed_rounds >= total_rounds → True"""
        session = MagicMock()
        session.id = 1
        session.participant_user_ids = []
        session.game_results = None
        session.rounds_data = {"completed_rounds": 3, "total_rounds": 3}
        session.scoring_type = "ROUNDS_BASED"
        session.date_start = None
        session.date_end = None
        result = get_tournament_sessions(
            tournament_id=7, db=self._session_db([session]), current_user=_user()
        )
        assert result[0]["result_submitted"] is True

    def test_non_rounds_based_with_game_results(self):
        """TS-06"""
        session = MagicMock()
        session.id = 1
        session.participant_user_ids = []
        session.game_results = {"score": [3, 1]}
        session.rounds_data = None
        session.scoring_type = "PLACEMENT"
        session.date_start = None
        session.date_end = None
        result = get_tournament_sessions(
            tournament_id=7, db=self._session_db([session]), current_user=_user()
        )
        assert result[0]["result_submitted"] is True


# ─── delete_generated_sessions ───────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestDeleteGeneratedSessions:
    def test_no_sessions_to_delete_returns_early(self):
        """DS-01"""
        t = MagicMock()
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = []  # no auto-generated sessions
        db.query.return_value = q
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch("app.models.session.Session"), \
             patch("app.models.attendance.Attendance"):
            MockRepo.return_value.get_or_404.return_value = t
            result = delete_generated_sessions(
                tournament_id=7, db=db, current_user=_user()
            )
        assert result["success"] is True
        assert result["deleted_count"] == 0
        db.commit.assert_not_called()

    def test_sessions_exist_delete_and_reset(self):
        """DS-02"""
        t = MagicMock()
        t.sessions_generated = True
        t.sessions_generated_at = "2026-03-01"
        mock_session = MagicMock()
        mock_session.id = 99
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = [mock_session]
        q.delete.return_value = 1
        db.query.return_value = q
        with patch(f"{_BASE}.TournamentRepository") as MockRepo, \
             patch("app.models.session.Session"), \
             patch("app.models.attendance.Attendance"):
            MockRepo.return_value.get_or_404.return_value = t
            result = delete_generated_sessions(
                tournament_id=7, db=db, current_user=_user()
            )
        assert result["success"] is True
        assert result["deleted_count"] == 1
        assert t.sessions_generated is False
        assert t.sessions_generated_at is None
        db.commit.assert_called_once()
