"""
Unit tests for app/tasks/scheduler.py

Covers:
  create_daily_snapshots_for_all_users()
    - empty user list → service not called, DB closed
    - all users processed successfully
    - per-user exception → continues for remaining users
    - critical DB error → does not propagate
    - DB always closed in finally block
    - AdaptiveLearningService instantiated with DB session

  refresh_all_recommendations()
    - empty user list → generate_recommendations not called
    - all users refreshed with refresh=True
    - per-user exception → continues for remaining users
    - critical DB error → does not propagate
    - DB always closed in finally block
    - refresh=True kwarg enforced

  start_scheduler()
    - returns BackgroundScheduler instance
    - scheduler.start() called once
    - exactly 2 jobs registered
    - daily_snapshots job id present
    - weekly_recommendations job id present
    - replace_existing=True on daily_snapshots
    - create_daily_snapshots_for_all_users is the daily job function
    - refresh_all_recommendations is the weekly job function
    - jobs added BEFORE scheduler.start()
"""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

# ──────────────────────────────────────────────────────────────────────────────
# Patch targets
# ──────────────────────────────────────────────────────────────────────────────

_PATCH_SESSION = "app.tasks.scheduler.SessionLocal"
_PATCH_SVC     = "app.tasks.scheduler.AdaptiveLearningService"
_PATCH_SCHED   = "app.tasks.scheduler.BackgroundScheduler"


def _row(user_id: int):
    """Minimal DB row with an .id attribute."""
    return SimpleNamespace(id=user_id)


# ──────────────────────────────────────────────────────────────────────────────
# create_daily_snapshots_for_all_users
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateDailySnapshots:

    def test_empty_user_list_service_not_called(self):
        """Empty active-user list → create_daily_snapshot never called."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = []

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            mock_svc_cls.return_value.create_daily_snapshot.assert_not_called()

    def test_empty_user_list_db_closed(self):
        """DB session closed even when user list is empty."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC):
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = []

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            mock_db.close.assert_called_once()

    def test_three_users_all_processed(self):
        """3 active users → create_daily_snapshot called for each."""
        rows = [_row(1), _row(2), _row(3)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            assert mock_svc.create_daily_snapshot.call_count == 3
            mock_svc.create_daily_snapshot.assert_any_call(1)
            mock_svc.create_daily_snapshot.assert_any_call(2)
            mock_svc.create_daily_snapshot.assert_any_call(3)

    def test_partial_failure_continues_remaining_users(self):
        """User 2 raises → users 1 and 3 are still processed."""
        rows = [_row(1), _row(2), _row(3)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value
            mock_svc.create_daily_snapshot.side_effect = [
                None,
                ValueError("DB timeout for user 2"),
                None,
            ]

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()  # must not re-raise

            assert mock_svc.create_daily_snapshot.call_count == 3

    def test_partial_failure_does_not_propagate(self):
        """Per-user exception must not propagate out of the function."""
        rows = [_row(42)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc_cls.return_value.create_daily_snapshot.side_effect = RuntimeError("boom")

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()  # must not raise

    def test_critical_db_failure_does_not_propagate(self):
        """DB execute fails entirely → no exception escapes."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC):
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = Exception("DB connection failed")

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()  # must not raise

    def test_db_always_closed_on_user_error(self):
        """DB session closed even after a per-user service exception."""
        rows = [_row(7)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc_cls.return_value.create_daily_snapshot.side_effect = RuntimeError("boom")

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            mock_db.close.assert_called_once()

    def test_db_always_closed_on_critical_error(self):
        """DB session closed even after a critical DB exception."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC):
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = Exception("fatal")

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            mock_db.close.assert_called_once()

    def test_service_instantiated_with_db_session(self):
        """AdaptiveLearningService receives the session returned by SessionLocal."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = []

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            mock_svc_cls.assert_called_once_with(mock_db)

    def test_single_user_snapshot_called_with_correct_id(self):
        """create_daily_snapshot called with the user's integer id."""
        rows = [_row(99)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value

            from app.tasks.scheduler import create_daily_snapshots_for_all_users
            create_daily_snapshots_for_all_users()

            mock_svc.create_daily_snapshot.assert_called_once_with(99)


# ──────────────────────────────────────────────────────────────────────────────
# refresh_all_recommendations
# ──────────────────────────────────────────────────────────────────────────────

class TestRefreshAllRecommendations:

    def test_empty_user_list_generate_not_called(self):
        """Empty active-user list → generate_recommendations never called."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = []

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            mock_svc_cls.return_value.generate_recommendations.assert_not_called()

    def test_empty_user_list_db_closed(self):
        """DB session closed even when user list is empty."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC):
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = []

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            mock_db.close.assert_called_once()

    def test_two_users_both_refreshed(self):
        """2 users → generate_recommendations called twice."""
        rows = [_row(10), _row(20)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            assert mock_svc.generate_recommendations.call_count == 2

    def test_refresh_kwarg_is_true(self):
        """generate_recommendations always called with refresh=True."""
        rows = [_row(55)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            call_kwargs = mock_svc.generate_recommendations.call_args.kwargs
            assert call_kwargs["refresh"] is True

    def test_correct_user_ids_passed(self):
        """generate_recommendations called with the correct user_id keyword arg."""
        rows = [_row(11), _row(22)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            mock_svc.generate_recommendations.assert_any_call(user_id=11, refresh=True)
            mock_svc.generate_recommendations.assert_any_call(user_id=22, refresh=True)

    def test_partial_failure_continues_remaining_users(self):
        """User 2 raises → user 3 is still processed."""
        rows = [_row(1), _row(2), _row(3)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc = mock_svc_cls.return_value
            mock_svc.generate_recommendations.side_effect = [
                None,
                Exception("service error"),
                None,
            ]

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()  # must not raise

            assert mock_svc.generate_recommendations.call_count == 3

    def test_critical_db_failure_does_not_propagate(self):
        """Fatal DB error does not escape the function."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC):
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = Exception("DB unreachable")

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()  # must not raise

    def test_db_always_closed_on_user_error(self):
        """DB session closed after per-user service failure."""
        rows = [_row(42)]
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC) as mock_svc_cls:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = rows
            mock_svc_cls.return_value.generate_recommendations.side_effect = RuntimeError

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            mock_db.close.assert_called_once()

    def test_db_always_closed_on_critical_error(self):
        """DB session closed after critical DB failure."""
        with patch(_PATCH_SESSION) as mock_sl, patch(_PATCH_SVC):
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = Exception("fatal")

            from app.tasks.scheduler import refresh_all_recommendations
            refresh_all_recommendations()

            mock_db.close.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# start_scheduler
# ──────────────────────────────────────────────────────────────────────────────

class TestStartScheduler:

    def test_returns_scheduler_instance(self):
        """start_scheduler() returns the BackgroundScheduler created internally."""
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            result = start_scheduler()

            assert result is mock_sched

    def test_scheduler_started(self):
        """scheduler.start() is called exactly once."""
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            mock_sched.start.assert_called_once()

    def test_exactly_two_jobs_registered(self):
        """Exactly 2 jobs added to the scheduler."""
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            assert mock_sched.add_job.call_count == 2

    def test_daily_snapshots_job_id_registered(self):
        """Job id='daily_snapshots' is registered."""
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            job_ids = [c.kwargs.get("id") for c in mock_sched.add_job.call_args_list]
            assert "daily_snapshots" in job_ids

    def test_weekly_recommendations_job_id_registered(self):
        """Job id='weekly_recommendations' is registered."""
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            job_ids = [c.kwargs.get("id") for c in mock_sched.add_job.call_args_list]
            assert "weekly_recommendations" in job_ids

    def test_daily_snapshots_replace_existing_true(self):
        """Daily snapshot job registered with replace_existing=True."""
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            calls_by_id = {
                c.kwargs.get("id"): c.kwargs
                for c in mock_sched.add_job.call_args_list
            }
            assert calls_by_id["daily_snapshots"]["replace_existing"] is True

    def test_daily_snapshot_job_function_is_correct(self):
        """Daily snapshot job targets create_daily_snapshots_for_all_users."""
        from app.tasks.scheduler import create_daily_snapshots_for_all_users
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            funcs = [
                c.args[0] if c.args else c.kwargs.get("func")
                for c in mock_sched.add_job.call_args_list
            ]
            assert create_daily_snapshots_for_all_users in funcs

    def test_weekly_recommendation_job_function_is_correct(self):
        """Weekly recommendations job targets refresh_all_recommendations."""
        from app.tasks.scheduler import refresh_all_recommendations
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            funcs = [
                c.args[0] if c.args else c.kwargs.get("func")
                for c in mock_sched.add_job.call_args_list
            ]
            assert refresh_all_recommendations in funcs

    def test_jobs_added_before_start(self):
        """All add_job calls happen before scheduler.start()."""
        call_order = []
        with patch(_PATCH_SCHED) as mock_cls:
            mock_sched = mock_cls.return_value
            mock_sched.add_job.side_effect = lambda *a, **kw: call_order.append("add_job")
            mock_sched.start.side_effect = lambda: call_order.append("start")

            from app.tasks.scheduler import start_scheduler
            start_scheduler()

            add_indices = [i for i, x in enumerate(call_order) if x == "add_job"]
            start_index = call_order.index("start")
            assert all(idx < start_index for idx in add_indices)
