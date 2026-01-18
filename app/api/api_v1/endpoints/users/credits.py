"""
User credits and billing endpoints
Credit balance, transactions, and invoice requests
"""
from typing import Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from .....database import get_db
from .....dependencies import get_current_user, get_current_user_web
from .....models.user import User

router = APIRouter()


@router.post("/request-invoice")
async def request_invoice(
    request_data: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
) -> Any:
    """
    Request invoice for credit purchase - creates InvoiceRequest with unique payment reference (Web cookie auth)
    """
@router.get("/credit-balance")
async def get_credit_balance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
) -> Any:
    """
    Get current user's credit balance and invoice counts (for polling/auto-refresh)
    """
    from .....models.invoice_request import InvoiceRequest

    # Get invoice counts
    invoice_counts = db.query(
        InvoiceRequest.status,
        func.count(InvoiceRequest.id).label('count')
    ).filter(
        InvoiceRequest.user_id == current_user.id
    ).group_by(InvoiceRequest.status).all()

    invoice_status_counts = {
        'pending': 0,
        'verified': 0,
        'paid': 0,
        'cancelled': 0,
        'total': 0
    }

    for status, count in invoice_counts:
        invoice_status_counts[status] = count
        invoice_status_counts['total'] += count

    return {
        "credit_balance": current_user.credit_balance,
        "credit_purchased": current_user.credit_purchased,
        "credit_used": current_user.credit_purchased - current_user.credit_balance,
        "invoice_counts": invoice_status_counts
    }


@router.get("/me/credit-transactions")
def get_my_credit_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of transactions to return"),
    offset: int = Query(default=0, ge=0, description="Number of transactions to skip")
) -> Any:
    """
    Get current user's credit transaction history.

    Available for ALL users (Student, Instructor, Admin) to see their own transactions.
    Shows:
    - License renewals (credit deductions)
    - Credit purchases
    - Semester enrollments
    - Refunds
    - Admin adjustments
    """
    from .....models.credit_transaction import CreditTransaction
    from .....models.license import UserLicense

    # Get all user's licenses
    user_licenses = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id
    ).all()

    if not user_licenses:
        return {
            "transactions": [],
            "total_count": 0,
            "credit_balance": current_user.credit_balance
        }

    license_ids = [lic.id for lic in user_licenses]

    # Get transactions for all user's licenses
    transactions_query = db.query(CreditTransaction).filter(
        CreditTransaction.user_license_id.in_(license_ids)
    ).order_by(CreditTransaction.created_at.desc())

    total_count = transactions_query.count()

    transactions = transactions_query.limit(limit).offset(offset).all()

    return {
        "transactions": [tx.to_dict() for tx in transactions],
        "total_count": total_count,
        "credit_balance": current_user.credit_balance,
        "showing": len(transactions),
        "limit": limit,
        "offset": offset
    }
