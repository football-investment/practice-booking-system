"""
Unit tests for app/api/api_v1/endpoints/licenses/admin.py
Covers: get_desync_issues, sync_user_progress_license, sync_user_all_specializations, sync_all_users
All endpoints are async → asyncio.run()
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.licenses.admin import (
    get_desync_issues,
    sync_user_progress_license,
    sync_user_all_specializations,
    sync_all_users,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.licenses.admin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(uid=42, role=UserRole.ADMIN):
    u = MagicMock()
    u.id = uid
    u.role = role
    return u


def _sync_svc():
    """Mock ProgressLicenseSyncService."""
    svc = MagicMock()
    svc.find_desync_issues.return_value = []
    svc.sync_progress_to_license.return_value = {"success": True}
    svc.sync_license_to_progress.return_value = {"success": True}
    svc.sync_user_all_specializations.return_value = {"synced": 0}
    svc.auto_sync_all.return_value = {"synced": 0}
    return svc


# ---------------------------------------------------------------------------
# get_desync_issues
# ---------------------------------------------------------------------------

class TestGetDesyncIssues:

    def _call(self, current_user=None, specialization=None, db=None):
        return asyncio.run(get_desync_issues(
            specialization=specialization,
            current_user=current_user or _user(role=UserRole.ADMIN),
            db=db or MagicMock(),
        ))

    def test_gdi01_student_403(self):
        """GDI-01: student role → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=_user(role=UserRole.STUDENT))
        assert exc.value.status_code == 403

    def test_gdi02_admin_success(self):
        """GDI-02: admin → calls find_desync_issues and returns result."""
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(current_user=_user(role=UserRole.ADMIN))
        svc.find_desync_issues.assert_called_once_with(None)
        assert result == []

    def test_gdi03_instructor_with_specialization(self):
        """GDI-03: instructor + specialization filter → passed through."""
        svc = _sync_svc()
        svc.find_desync_issues.return_value = [{"user_id": 99}]
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(
                current_user=_user(role=UserRole.INSTRUCTOR),
                specialization="COACH",
            )
        svc.find_desync_issues.assert_called_once_with("COACH")
        assert result == [{"user_id": 99}]


# ---------------------------------------------------------------------------
# sync_user_progress_license
# ---------------------------------------------------------------------------

class TestSyncUserProgressLicense:

    def _call(self, user_id=42, data=None, current_user=None, db=None):
        if data is None:
            data = {"specialization": "PLAYER", "direction": "progress_to_license"}
        return asyncio.run(sync_user_progress_license(
            user_id=user_id,
            data=data,
            current_user=current_user or _user(role=UserRole.ADMIN),
            db=db or MagicMock(),
        ))

    def test_sul01_student_403(self):
        """SUL-01: student role → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=_user(role=UserRole.STUDENT))
        assert exc.value.status_code == 403

    def test_sul02_missing_specialization_400(self):
        """SUL-02: no 'specialization' in data → 400."""
        with pytest.raises(HTTPException) as exc:
            self._call(data={"direction": "progress_to_license"})
        assert exc.value.status_code == 400
        assert "specialization" in exc.value.detail

    def test_sul03_bad_direction_400(self):
        """SUL-03: invalid direction value → 400."""
        with pytest.raises(HTTPException) as exc:
            self._call(data={"specialization": "PLAYER", "direction": "invalid_dir"})
        assert exc.value.status_code == 400
        assert "progress_to_license" in exc.value.detail

    def test_sul04_progress_to_license(self):
        """SUL-04: direction=progress_to_license → sync_progress_to_license called."""
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(
                user_id=42,
                data={"specialization": "PLAYER", "direction": "progress_to_license"},
            )
        svc.sync_progress_to_license.assert_called_once_with(
            user_id=42, specialization="PLAYER", synced_by=42
        )
        assert result["success"] is True

    def test_sul05_license_to_progress(self):
        """SUL-05: direction=license_to_progress → sync_license_to_progress called."""
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(
                user_id=99,
                data={"specialization": "COACH", "direction": "license_to_progress"},
                current_user=_user(uid=1, role=UserRole.ADMIN),
            )
        svc.sync_license_to_progress.assert_called_once_with(
            user_id=99, specialization="COACH"
        )

    def test_sul06_default_direction_is_progress_to_license(self):
        """SUL-06: no direction key → defaults to progress_to_license."""
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(
                data={"specialization": "PLAYER"},  # no direction key
            )
        svc.sync_progress_to_license.assert_called_once()


# ---------------------------------------------------------------------------
# sync_user_all_specializations
# ---------------------------------------------------------------------------

class TestSyncUserAllSpecializations:

    def _call(self, user_id=42, data=None, current_user=None, db=None):
        if data is None:
            data = {"direction": "progress_to_license"}
        return asyncio.run(sync_user_all_specializations(
            user_id=user_id,
            data=data,
            current_user=current_user or _user(role=UserRole.ADMIN),
            db=db or MagicMock(),
        ))

    def test_sua01_student_403(self):
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=_user(role=UserRole.STUDENT))
        assert exc.value.status_code == 403

    def test_sua02_bad_direction_400(self):
        with pytest.raises(HTTPException) as exc:
            self._call(data={"direction": "sideways"})
        assert exc.value.status_code == 400

    def test_sua03_progress_to_license(self):
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(user_id=42, data={"direction": "progress_to_license"})
        svc.sync_user_all_specializations.assert_called_once_with(42, "progress_to_license")

    def test_sua04_license_to_progress(self):
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(user_id=99, data={"direction": "license_to_progress"})
        svc.sync_user_all_specializations.assert_called_once_with(99, "license_to_progress")


# ---------------------------------------------------------------------------
# sync_all_users
# ---------------------------------------------------------------------------

class TestSyncAllUsers:

    def _call(self, data=None, current_user=None, db=None):
        if data is None:
            data = {"direction": "progress_to_license", "dry_run": True}
        return asyncio.run(sync_all_users(
            data=data,
            current_user=current_user or _user(role=UserRole.ADMIN),
            db=db or MagicMock(),
        ))

    def test_sau01_instructor_403(self):
        """SAU-01: INSTRUCTOR is not allowed (only ADMIN)."""
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=_user(role=UserRole.INSTRUCTOR))
        assert exc.value.status_code == 403

    def test_sau02_student_403(self):
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=_user(role=UserRole.STUDENT))
        assert exc.value.status_code == 403

    def test_sau03_bad_direction_400(self):
        with pytest.raises(HTTPException) as exc:
            self._call(data={"direction": "backwards"})
        assert exc.value.status_code == 400

    def test_sau04_admin_progress_to_license_dry_run(self):
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(data={"direction": "progress_to_license", "dry_run": True})
        svc.auto_sync_all.assert_called_once_with(
            sync_direction="progress_to_license", dry_run=True
        )

    def test_sau05_license_to_progress(self):
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(data={"direction": "license_to_progress", "dry_run": False})
        svc.auto_sync_all.assert_called_once_with(
            sync_direction="license_to_progress", dry_run=False
        )

    def test_sau06_default_dry_run_true(self):
        """No dry_run in data → defaults to True."""
        svc = _sync_svc()
        with patch(f"{_BASE}.ProgressLicenseSyncService", return_value=svc):
            result = self._call(data={"direction": "progress_to_license"})
        _, kwargs = svc.auto_sync_all.call_args
        assert kwargs["dry_run"] is True
