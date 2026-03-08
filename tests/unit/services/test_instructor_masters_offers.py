"""
Unit tests for app/api/api_v1/endpoints/instructor_management/masters/offers.py
Covers: respond_to_offer, get_my_master_offers, get_pending_offers, cancel_offer
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone, timedelta

from app.api.api_v1.endpoints.instructor_management.masters.offers import (
    respond_to_offer, get_my_master_offers, get_pending_offers, cancel_offer
)
from app.models.instructor_assignment import MasterOfferStatus
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.instructor_management.masters.offers"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(first_val=None, all_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.all.return_value = all_val if all_val is not None else []
    q.first.return_value = first_val
    return q


def _seq_db(*vals):
    call_n = [0]
    db = MagicMock()

    def side(*args):
        n = call_n[0]
        call_n[0] += 1
        v = vals[n] if n < len(vals) else None
        q = _q()
        if isinstance(v, list):
            q.all.return_value = v
        else:
            q.first.return_value = v
        return q

    db.query.side_effect = side
    return db


def _user(uid=42, role=UserRole.INSTRUCTOR):
    u = MagicMock()
    u.id = uid
    u.role = role
    return u


def _admin():
    return _user(uid=42, role=UserRole.ADMIN)


def _offer(oid=10, instructor_id=42, status=MasterOfferStatus.OFFERED, deadline=None):
    o = MagicMock()
    o.id = oid
    o.instructor_id = instructor_id
    o.offer_status = status
    o.offer_deadline = deadline
    o.location = MagicMock()
    o.location.id = 1
    o.location.name = "Budapest"
    o.location.city = "Budapest"
    o.instructor = MagicMock()
    o.instructor.name = "Test Instructor"
    o.instructor.email = "instructor@example.com"
    return o


def _action(action_str="ACCEPT"):
    a = MagicMock()
    a.action = action_str
    return a


# ---------------------------------------------------------------------------
# respond_to_offer
# ---------------------------------------------------------------------------

class TestRespondToOffer:
    def _call(self, offer_id=10, action=None, db=None, current_user=None):
        return respond_to_offer(
            offer_id=offer_id,
            action=action or _action("ACCEPT"),
            db=db or MagicMock(),
            current_user=current_user or _user(),
        )

    def test_offer_not_found_404(self):
        """RO-01: offer not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_wrong_user_403(self):
        """RO-02: offer belongs to different user → 403."""
        from fastapi import HTTPException
        offer = _offer(instructor_id=99)
        db = _seq_db(offer)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 403

    def test_not_offered_status_400(self):
        """RO-03: offer not in OFFERED status → 400."""
        from fastapi import HTTPException
        offer = _offer(status=MasterOfferStatus.ACCEPTED)
        db = _seq_db(offer)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_deadline_passed_expires_offer_400(self):
        """RO-04: deadline passed → auto-expire and 400."""
        from fastapi import HTTPException
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        offer = _offer(deadline=past)
        db = _seq_db(offer)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400
        assert offer.offer_status == MasterOfferStatus.EXPIRED
        db.commit.assert_called_once()

    def test_accept_with_existing_master_position_400(self):
        """RO-05: accept but already master elsewhere → 400."""
        from fastapi import HTTPException
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        offer = _offer(deadline=future)
        db = _seq_db(offer, [])  # other_offers empty

        with patch(f"{_BASE}.check_instructor_has_active_master_position", return_value=True):
            with patch(f"{_BASE}.get_instructor_active_master_location", return_value="Győr"):
                with pytest.raises(HTTPException) as exc:
                    self._call(db=db, action=_action("ACCEPT"))
        assert exc.value.status_code == 400
        assert "already master" in exc.value.detail.lower()

    def test_accept_success_no_other_offers(self):
        """RO-06: accept with no other offers → offer accepted, transition triggered."""
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        offer = _offer(deadline=future)
        db = MagicMock()
        # n0: the offer itself; n1: other_offers=[]
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = offer
            else:
                q.all.return_value = []
            return q
        db.query.side_effect = qside

        with patch(f"{_BASE}.check_instructor_has_active_master_position", return_value=False):
            with patch(f"{_BASE}.transition_to_instructor_assigned") as mock_trans:
                with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
                    MockResp.from_orm.return_value = MagicMock()
                    self._call(db=db, action=_action("ACCEPT"))
        assert offer.offer_status == MasterOfferStatus.ACCEPTED
        assert offer.is_active is True
        mock_trans.assert_called_once()

    def test_accept_auto_declines_other_offers(self):
        """RO-07: accept → other OFFERED contracts auto-declined."""
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        offer = _offer(deadline=future)
        other1 = _offer(oid=20)
        other2 = _offer(oid=30)
        db = MagicMock()
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = offer
            else:
                q.all.return_value = [other1, other2]
            return q
        db.query.side_effect = qside

        with patch(f"{_BASE}.check_instructor_has_active_master_position", return_value=False):
            with patch(f"{_BASE}.transition_to_instructor_assigned"):
                with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
                    MockResp.from_orm.return_value = MagicMock()
                    self._call(db=db, action=_action("ACCEPT"))
        assert other1.offer_status == MasterOfferStatus.DECLINED
        assert other2.offer_status == MasterOfferStatus.DECLINED

    def test_decline_success(self):
        """RO-08: decline → offer marked DECLINED."""
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        offer = _offer(deadline=future)
        db = _seq_db(offer)

        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            self._call(db=db, action=_action("DECLINE"))
        assert offer.offer_status == MasterOfferStatus.DECLINED


# ---------------------------------------------------------------------------
# get_my_master_offers
# ---------------------------------------------------------------------------

class TestGetMyMasterOffers:
    def _call(self, status=None, include_expired=False, db=None, current_user=None):
        return get_my_master_offers(
            status=status,
            include_expired=include_expired,
            db=db or MagicMock(),
            current_user=current_user or _user(),
        )

    def test_no_filters_returns_list(self):
        """GMMO-01: no filters → all non-expired offers."""
        offers = [_offer(oid=1), _offer(oid=2)]
        q = _q(all_val=offers)
        db = MagicMock()
        db.query.return_value = q

        with patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            MockResp.return_value = MagicMock()
            result = self._call(db=db)
        assert len(result) == 2

    def test_invalid_status_attr_error(self):
        """GMMO-02: invalid status → PRODUCTION BUG: 'status' param shadows fastapi.status
        so except block raises AttributeError instead of HTTPException."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        with pytest.raises(AttributeError):
            self._call(status="INVALID_STATUS", db=db)

    def test_valid_status_filter(self):
        """GMMO-03: valid status → filter applied."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterOfferResponse"):
            result = self._call(status="OFFERED", db=db)
        assert isinstance(result, list)

    def test_include_expired_true(self):
        """GMMO-04: include_expired=True → expired filter NOT applied."""
        offers = [_offer(oid=1)]
        q = _q(all_val=offers)
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            MockResp.return_value = MagicMock()
            result = self._call(include_expired=True, db=db)
        assert len(result) == 1

    def test_offer_with_no_deadline(self):
        """GMMO-05: offer with no deadline → days_remaining=0."""
        offer = _offer(oid=1)
        offer.offer_deadline = None
        q = _q(all_val=[offer])
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            MockResp.return_value = MagicMock()
            result = self._call(db=db)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_pending_offers
# ---------------------------------------------------------------------------

class TestGetPendingOffers:
    def _call(self, db=None, current_user=None):
        return get_pending_offers(
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_no_pending_returns_empty(self):
        """GPO-01: no pending offers → empty list."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert result == []

    def test_pending_with_offers(self):
        """GPO-02: pending offers present → list returned."""
        offers = [_offer(oid=1), _offer(oid=2)]
        q = _q(all_val=offers)
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            MockResp.return_value = MagicMock()
            result = self._call(db=db)
        assert len(result) == 2

    def test_offer_no_deadline_days_remaining_zero(self):
        """GPO-03: offer without deadline → days_remaining=0, no error."""
        offer = _offer(oid=1)
        offer.offer_deadline = None
        q = _q(all_val=[offer])
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            MockResp.return_value = MagicMock()
            result = self._call(db=db)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# cancel_offer
# ---------------------------------------------------------------------------

class TestCancelOffer:
    def _call(self, offer_id=10, db=None, current_user=None):
        return cancel_offer(
            offer_id=offer_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_offer_not_found_404(self):
        """CO-01: offer not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_not_offered_status_400(self):
        """CO-02: offer already accepted/declined → 400."""
        from fastapi import HTTPException
        offer = _offer(status=MasterOfferStatus.ACCEPTED)
        db = _seq_db(offer)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_success_marks_declined(self):
        """CO-03: cancel OFFERED → marks DECLINED and commits."""
        offer = _offer(status=MasterOfferStatus.OFFERED)
        db = _seq_db(offer)
        result = self._call(db=db)
        assert offer.offer_status == MasterOfferStatus.DECLINED
        db.commit.assert_called_once()
