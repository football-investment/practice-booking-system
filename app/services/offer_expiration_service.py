"""
Master Instructor Offer Expiration Service

Background job to automatically expire offers that pass their deadline.
Should be run as a cron job (hourly or daily).
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..models.instructor_assignment import LocationMasterInstructor, MasterOfferStatus


def expire_old_offers(db: Session) -> Dict[str, Any]:
    """
    Find all OFFERED contracts past deadline and mark them as EXPIRED.

    Business Logic:
    - Only affects contracts with offer_status = OFFERED
    - Checks offer_deadline < current time
    - Updates to offer_status = EXPIRED
    - Sets declined_at = current time
    - Keeps is_active = False (never activate expired offers)

    Args:
        db: Database session

    Returns:
        Dict with:
            - expired_count: Number of offers expired
            - expired_offers: List of expired offer details
    """
    now = datetime.now(timezone.utc)

    # Find all OFFERED contracts past deadline
    expired_offers = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.offer_status == MasterOfferStatus.OFFERED,
        LocationMasterInstructor.offer_deadline < now
    ).all()

    expired_details = []

    for offer in expired_offers:
        # Update status to EXPIRED
        offer.offer_status = MasterOfferStatus.EXPIRED
        offer.declined_at = now

        # Gather details for logging
        expired_details.append({
            'offer_id': offer.id,
            'location_id': offer.location_id,
            'instructor_id': offer.instructor_id,
            'contract_start': offer.contract_start.isoformat(),
            'contract_end': offer.contract_end.isoformat(),
            'offered_at': offer.offered_at.isoformat() if offer.offered_at else None,
            'offer_deadline': offer.offer_deadline.isoformat() if offer.offer_deadline else None,
            'days_overdue': (now - offer.offer_deadline).days if offer.offer_deadline else 0
        })

    # Commit all changes
    db.commit()

    return {
        'expired_count': len(expired_offers),
        'expired_offers': expired_details,
        'timestamp': now.isoformat()
    }


def get_pending_offers_summary(db: Session) -> Dict[str, Any]:
    """
    Get summary of all currently pending offers (not expired yet).

    Useful for monitoring/dashboard purposes.

    Returns:
        Dict with:
            - total_pending: Number of pending offers
            - expiring_soon: Offers expiring within 24 hours
            - pending_offers: List of pending offer summaries
    """
    now = datetime.now(timezone.utc)

    # Get all OFFERED contracts not yet expired
    pending_offers = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.offer_status == MasterOfferStatus.OFFERED,
        LocationMasterInstructor.offer_deadline >= now
    ).all()

    pending_details = []
    expiring_soon_count = 0

    for offer in pending_offers:
        days_remaining = (offer.offer_deadline - now).days if offer.offer_deadline else 0

        if days_remaining <= 1:  # Expiring within 24 hours
            expiring_soon_count += 1

        pending_details.append({
            'offer_id': offer.id,
            'location_id': offer.location_id,
            'instructor_id': offer.instructor_id,
            'offered_at': offer.offered_at.isoformat() if offer.offered_at else None,
            'offer_deadline': offer.offer_deadline.isoformat() if offer.offer_deadline else None,
            'days_remaining': days_remaining,
            'expiring_soon': days_remaining <= 1
        })

    return {
        'total_pending': len(pending_offers),
        'expiring_soon': expiring_soon_count,
        'pending_offers': pending_details,
        'timestamp': now.isoformat()
    }


def cleanup_old_declined_offers(db: Session, days_old: int = 90) -> int:
    """
    Clean up old DECLINED/EXPIRED offers from database.

    Optional maintenance task to keep database clean.
    Only removes offers that are more than `days_old` days old.

    Args:
        db: Database session
        days_old: Minimum age in days for cleanup (default 90)

    Returns:
        Number of records deleted
    """
    from datetime import timedelta

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

    # Find old DECLINED/EXPIRED offers
    old_offers = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.offer_status.in_([
            MasterOfferStatus.DECLINED,
            MasterOfferStatus.EXPIRED
        ]),
        LocationMasterInstructor.declined_at < cutoff_date
    ).all()

    count = len(old_offers)

    # Delete them
    for offer in old_offers:
        db.delete(offer)

    db.commit()

    return count
