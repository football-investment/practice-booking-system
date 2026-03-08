"""
Sprint 30 — app/api/api_v1/endpoints/tournaments/cancellation.py
================================================================
Target: ≥85% statement, ≥70% branch

Covers:
  process_refund:
    * non-APPROVED status (PENDING, REJECTED) → None
    * APPROVED but no UserLicense found → None
    * APPROVED + license + zero enrollment_cost → None
    * APPROVED + license + positive cost → RefundDetails
    * user.name is None → user_name falls back to "Unknown"

  reject_pending_enrollment:
    * non-PENDING (APPROVED, REJECTED) → False
    * PENDING → True (mutates enrollment.request_status to REJECTED)

  cancel_tournament:
    * non-admin → 403
    * tournament not found → 404
    * COMPLETED tournament → 400
    * CANCELLED tournament → 400
    * blank reason → 400
    * success — no enrollments → 0 refunds, 0 rejections
    * success — APPROVED enrollment → refund counted
    * success — PENDING enrollment → rejected_ids populated
    * success — process_refund returns None (APPROVED, free) → no count
    * notify_participants=False → success (notify branch not entered)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.tournaments.cancellation import (
    cancel_tournament,
    process_refund,
    reject_pending_enrollment,
    CancellationRequest,
    RefundDetails,
)
from app.models.user import UserRole
from app.models.semester import SemesterStatus
from app.models.semester_enrollment import EnrollmentStatus

_BASE = "app.api.api_v1.endpoints.tournaments.cancellation"


# ── helpers ─────────────────────────────────────────────────────────────────

def _admin():
    u = MagicMock()
    u.role = UserRole.ADMIN
    u.id = 1
    u.name = "Admin"
    u.email = "admin@lfa.com"
    return u


def _student():
    u = MagicMock()
    u.role = UserRole.STUDENT
    return u


def _tournament(tstatus=SemesterStatus.ONGOING, cost=500, tid=10):
    t = MagicMock()
    t.id = tid
    t.name = "Test Cup"
    t.status = tstatus
    t.enrollment_cost = cost
    return t


def _enrollment(estatus=EnrollmentStatus.APPROVED, eid=1, lic_id=42):
    e = MagicMock()
    e.id = eid
    e.request_status = estatus
    e.user_license_id = lic_id
    e.user.id = 100
    e.user.name = "John"
    e.user.email = "john@lfa.com"
    return e


def _license(balance=200, lid=42):
    lic = MagicMock()
    lic.id = lid
    lic.credit_balance = balance
    return lic


def _q_first(val):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = val
    return q


def _q_all(vals):
    q = MagicMock()
    q.filter.return_value = q
    q.all.return_value = vals
    return q


def _seq_db(*qs):
    """n-th db.query() call returns qs[n]; safe fallback afterward."""
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return qs[idx] if idx < len(qs) else MagicMock()

    db = MagicMock()
    db.query.side_effect = _side
    return db


# ============================================================================
# process_refund
# ============================================================================

class TestProcessRefund:

    def test_pending_returns_none(self):
        """PR-01: PENDING enrollment → None (no refund without approval)."""
        e = _enrollment(estatus=EnrollmentStatus.PENDING)
        result = process_refund(MagicMock(), e, MagicMock(), MagicMock(), "reason")
        assert result is None

    def test_rejected_returns_none(self):
        """PR-02: REJECTED enrollment → None."""
        e = _enrollment(estatus=EnrollmentStatus.REJECTED)
        result = process_refund(MagicMock(), e, MagicMock(), MagicMock(), "reason")
        assert result is None

    def test_approved_no_license_returns_none(self):
        """PR-03: APPROVED but UserLicense not found → None."""
        e = _enrollment(estatus=EnrollmentStatus.APPROVED)
        db = _seq_db(_q_first(None))
        t = _tournament(cost=200)
        result = process_refund(db, e, t, MagicMock(), "reason")
        assert result is None

    def test_approved_zero_cost_returns_none(self):
        """PR-04: APPROVED + license found + enrollment_cost=0 → None (free tournament)."""
        e = _enrollment(estatus=EnrollmentStatus.APPROVED)
        lic = _license()
        db = _seq_db(_q_first(lic))
        t = _tournament(cost=0)
        result = process_refund(db, e, t, MagicMock(), "reason")
        assert result is None

    def test_approved_positive_cost_returns_refund_details(self):
        """PR-05: APPROVED + license + positive cost → RefundDetails returned."""
        e = _enrollment(estatus=EnrollmentStatus.APPROVED, eid=5, lic_id=42)
        e.user.id = 100
        e.user.name = "John Doe"
        e.user.email = "john@lfa.com"
        lic = _license(balance=100, lid=42)
        db = _seq_db(_q_first(lic))
        t = _tournament(cost=300, tid=10)

        with patch(f"{_BASE}.CreditService") as MockCS:
            MockCS.return_value.create_transaction.return_value = (MagicMock(), True)
            result = process_refund(db, e, t, MagicMock(), "Weather")

        assert isinstance(result, RefundDetails)
        assert result.enrollment_id == 5
        assert result.user_id == 100
        assert result.user_name == "John Doe"
        assert result.amount_refunded == 300

    def test_user_name_none_falls_back_to_unknown(self):
        """PR-06: user.name is None → user_name becomes 'Unknown'."""
        e = _enrollment(estatus=EnrollmentStatus.APPROVED, eid=6, lic_id=42)
        e.user.name = None
        e.user.id = 101
        e.user.email = "x@lfa.com"
        lic = _license(balance=100)
        db = _seq_db(_q_first(lic))
        t = _tournament(cost=100, tid=10)

        with patch(f"{_BASE}.CreditService") as MockCS:
            MockCS.return_value.create_transaction.return_value = (MagicMock(), True)
            result = process_refund(db, e, t, MagicMock(), "reason")

        assert result.user_name == "Unknown"


# ============================================================================
# reject_pending_enrollment
# ============================================================================

class TestRejectPendingEnrollment:

    def test_approved_returns_false(self):
        """RPE-01: APPROVED enrollment → returns False."""
        e = _enrollment(estatus=EnrollmentStatus.APPROVED)
        assert reject_pending_enrollment(MagicMock(), e) is False

    def test_rejected_returns_false(self):
        """RPE-02: REJECTED enrollment → returns False."""
        e = _enrollment(estatus=EnrollmentStatus.REJECTED)
        assert reject_pending_enrollment(MagicMock(), e) is False

    def test_pending_returns_true_and_mutates(self):
        """RPE-03: PENDING → returns True and sets status to REJECTED."""
        e = _enrollment(estatus=EnrollmentStatus.PENDING)
        result = reject_pending_enrollment(MagicMock(), e)
        assert result is True
        assert e.request_status == EnrollmentStatus.REJECTED


# ============================================================================
# cancel_tournament — validation failures
# ============================================================================

class TestCancelTournamentValidation:

    def test_non_admin_returns_403(self):
        """CAN-01: non-admin user → 403 Forbidden."""
        db = MagicMock()
        req = CancellationRequest(reason="Testing")
        with pytest.raises(HTTPException) as exc:
            cancel_tournament(
                tournament_id=1, request_data=req, db=db, current_user=_student()
            )
        assert exc.value.status_code == 403

    def test_tournament_not_found_returns_404(self):
        """CAN-02: tournament not found → 404."""
        db = _seq_db(_q_first(None))
        req = CancellationRequest(reason="Testing")
        with pytest.raises(HTTPException) as exc:
            cancel_tournament(
                tournament_id=99, request_data=req, db=db, current_user=_admin()
            )
        assert exc.value.status_code == 404
        assert "99" in str(exc.value.detail)

    def test_completed_tournament_returns_400(self):
        """CAN-03: COMPLETED tournament → 400."""
        t = _tournament(tstatus=SemesterStatus.COMPLETED)
        db = _seq_db(_q_first(t))
        req = CancellationRequest(reason="Done")
        with pytest.raises(HTTPException) as exc:
            cancel_tournament(
                tournament_id=10, request_data=req, db=db, current_user=_admin()
            )
        assert exc.value.status_code == 400
        assert "completed" in str(exc.value.detail).lower()

    def test_already_cancelled_returns_400(self):
        """CAN-04: already CANCELLED → 400."""
        t = _tournament(tstatus=SemesterStatus.CANCELLED)
        db = _seq_db(_q_first(t))
        req = CancellationRequest(reason="already done")
        with pytest.raises(HTTPException) as exc:
            cancel_tournament(
                tournament_id=10, request_data=req, db=db, current_user=_admin()
            )
        assert exc.value.status_code == 400
        assert "cancelled" in str(exc.value.detail).lower()

    def test_blank_reason_returns_400(self):
        """CAN-05: whitespace-only reason → 400."""
        t = _tournament()
        db = _seq_db(_q_first(t))
        req = CancellationRequest(reason="   ")
        with pytest.raises(HTTPException) as exc:
            cancel_tournament(
                tournament_id=10, request_data=req, db=db, current_user=_admin()
            )
        assert exc.value.status_code == 400


# ============================================================================
# cancel_tournament — success paths
# ============================================================================

class TestCancelTournamentSuccess:
    """Test the action phase of cancel_tournament with patched helpers."""

    def _run(self, t, enrollments, notify=True, reason="Bad weather",
             refund_return=None, reject_return=False):
        db = _seq_db(_q_first(t), _q_all(enrollments))
        req = CancellationRequest(reason=reason, notify_participants=notify)
        with patch(f"{_BASE}.process_refund", return_value=refund_return) as mock_pr:
            with patch(f"{_BASE}.reject_pending_enrollment",
                       return_value=reject_return) as mock_rpe:
                result = cancel_tournament(
                    tournament_id=t.id,
                    request_data=req,
                    db=db,
                    current_user=_admin()
                )
        return result, mock_pr, mock_rpe

    def test_success_no_enrollments(self):
        """CAN-06: no enrollments → success, 0 refunds, 0 rejections."""
        t = _tournament()
        result, mock_pr, mock_rpe = self._run(t, [])

        assert result["tournament_id"] == t.id
        assert result["refunds_processed"]["count"] == 0
        assert result["enrollments_rejected"]["count"] == 0
        mock_pr.assert_not_called()
        mock_rpe.assert_not_called()
        # Status updated
        assert t.status == SemesterStatus.CANCELLED
        assert t.tournament_status == "CANCELLED"

    def test_success_with_refund_processed(self):
        """CAN-07: process_refund returns RefundDetails → count+total updated."""
        t = _tournament(cost=300)
        e1 = _enrollment(estatus=EnrollmentStatus.APPROVED, eid=5)
        refund = RefundDetails(
            enrollment_id=5, user_id=100, user_name="John",
            user_email="j@lfa.com", amount_refunded=300
        )
        result, mock_pr, _ = self._run(t, [e1], refund_return=refund)

        assert result["refunds_processed"]["count"] == 1
        assert result["refunds_processed"]["total_credits_refunded"] == 300
        mock_pr.assert_called_once()

    def test_success_refund_returns_none(self):
        """CAN-08: process_refund returns None (e.g. free tournament) → not counted."""
        t = _tournament(cost=0)
        e1 = _enrollment(estatus=EnrollmentStatus.APPROVED, eid=5)
        result, mock_pr, _ = self._run(t, [e1], refund_return=None)

        assert result["refunds_processed"]["count"] == 0
        mock_pr.assert_called_once()  # called, but result discarded

    def test_success_pending_enrollment_rejected(self):
        """CAN-09: reject_pending_enrollment returns True → enrollment_id appended."""
        t = _tournament()
        e1 = _enrollment(estatus=EnrollmentStatus.PENDING, eid=7)
        result, _, mock_rpe = self._run(t, [e1], reject_return=True)

        assert result["enrollments_rejected"]["count"] == 1
        assert 7 in result["enrollments_rejected"]["enrollment_ids"]
        mock_rpe.assert_called_once()

    def test_notify_false_branch(self):
        """CAN-10: notify_participants=False → still succeeds (notify block skipped)."""
        t = _tournament()
        result, _, _ = self._run(t, [], notify=False)
        assert result["tournament_id"] == t.id

    def test_cancelled_by_includes_admin_info(self):
        """CAN-11: response.cancelled_by contains admin id/name/email."""
        t = _tournament()
        result, _, _ = self._run(t, [])

        assert result["cancelled_by"]["user_id"] == 1
        assert result["cancelled_by"]["email"] == "admin@lfa.com"
        assert "cancelled_at" in result

    def test_multiple_enrollments_mixed(self):
        """CAN-12: 1 APPROVED (refunded) + 1 PENDING (rejected) → counts correct."""
        t = _tournament(cost=200)
        e_approved = _enrollment(estatus=EnrollmentStatus.APPROVED, eid=10)
        e_pending = _enrollment(estatus=EnrollmentStatus.PENDING, eid=11)

        refund = RefundDetails(
            enrollment_id=10, user_id=200, user_name="A",
            user_email="a@lfa.com", amount_refunded=200
        )
        db = _seq_db(_q_first(t), _q_all([e_approved, e_pending]))
        req = CancellationRequest(reason="Mixed case")

        pr_results = [refund, None]  # approved gets refund, pending gets None
        rpe_results = [False, True]  # approved not rejected, pending is

        with patch(f"{_BASE}.process_refund", side_effect=pr_results):
            with patch(f"{_BASE}.reject_pending_enrollment", side_effect=rpe_results):
                result = cancel_tournament(
                    tournament_id=t.id, request_data=req, db=db, current_user=_admin()
                )

        assert result["refunds_processed"]["count"] == 1
        assert result["enrollments_rejected"]["count"] == 1
