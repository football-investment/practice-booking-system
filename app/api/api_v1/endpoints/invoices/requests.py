"""Invoice request management"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_user_web, get_current_admin_user
from .....models.user import User
from .....models.invoice_request import InvoiceRequest
from .....models.coupon import Coupon


router = APIRouter()


class InvoiceRequestCreate(BaseModel):
    """Request body for creating an invoice request"""
    credit_amount: int
    amount_eur: float
    coupon_code: str | None = None



@router.post("/request")
async def create_invoice_request(
    invoice_data: InvoiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new invoice request for credit purchase.
    Student can request invoice with optional coupon code.
    """

    # Validate credit amount
    if invoice_data.credit_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit amount must be positive"
        )

    # Validate amount in EUR
    if invoice_data.amount_eur <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount in EUR must be positive"
        )

    # Validate and increment coupon usage if provided
    if invoice_data.coupon_code:
        coupon = db.query(Coupon).filter(Coupon.code == invoice_data.coupon_code.upper()).first()

        if coupon:
            if not coupon.is_valid():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Coupon is not valid or has expired"
                )
            # Increment usage
            coupon.increment_usage()
            db.add(coupon)

    # Generate payment reference code (6 digits)
    import random
    payment_reference = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # Check if reference already exists (unlikely but possible)
    while db.query(InvoiceRequest).filter(
        InvoiceRequest.payment_reference == payment_reference
    ).first():
        payment_reference = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # Create invoice request
    now = datetime.now(timezone.utc)
    invoice = InvoiceRequest(
        user_id=current_user.id,
        credit_amount=invoice_data.credit_amount,
        amount_eur=invoice_data.amount_eur,
        coupon_code=invoice_data.coupon_code,
        payment_reference=payment_reference,
        status="pending",
        created_at=now
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    print(f"💳 Invoice request created: {invoice.id} for {current_user.name} ({invoice_data.credit_amount} credits, {invoice_data.amount_eur} EUR, ref: {payment_reference})")

    return {
        "success": True,
        "message": "Invoice request created successfully!",
        "invoice_id": invoice.id,
        "payment_reference": payment_reference,
        "credit_amount": invoice_data.credit_amount,
        "amount_eur": invoice_data.amount_eur,
        "status": "pending",
        "created_at": invoice.created_at
    }


@router.get("/list")
async def list_invoices(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    status: str | None = None,
    limit: int = 50
) -> Any:
    """
    List all invoice requests (Admin only) - Supports both Bearer token and cookie auth

    Query parameters:
    - status: Filter by status (pending, verified, cancelled)
    - limit: Maximum number of results (default: 50)
    """
    query = db.query(InvoiceRequest).join(User, InvoiceRequest.user_id == User.id)

    if status:
        query = query.filter(InvoiceRequest.status == status)

    invoices = query.order_by(InvoiceRequest.created_at.desc()).limit(limit).all()

    # Build response with student info
    result = []
    for invoice in invoices:
        student = db.query(User).filter(User.id == invoice.user_id).first()
        result.append({
            "id": invoice.id,
            "user_id": invoice.user_id,
            "student_name": student.name if student else "Unknown",
            "student_email": student.email if student else "Unknown",
            "credit_amount": invoice.credit_amount,
            "amount_eur": invoice.amount_eur,
            "coupon_code": invoice.coupon_code,
            "payment_reference": invoice.payment_reference,
            "status": invoice.status,
            "created_at": invoice.created_at,
            "verified_at": invoice.verified_at
        })

    return result


@router.get("/count")
async def get_invoice_count(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Any:
    """
    Get invoice request counts by status (Admin only - for polling)
    """
    from sqlalchemy import func

    counts = db.query(
        InvoiceRequest.status,
        func.count(InvoiceRequest.id).label('count')
    ).group_by(InvoiceRequest.status).all()

    result = {
        'pending': 0,
        'verified': 0,
        'paid': 0,
        'cancelled': 0,
        'total': 0
    }

    for status, count in counts:
        result[status] = count
        result['total'] += count

    return result


@router.get("/summary")
async def get_financial_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Financial summary for admin dashboard (Admin only).
    Returns aggregated revenue, credit, and invoice statistics.
    """
    from sqlalchemy import func

    # ── Invoice aggregates ────────────────────────────────────────
    agg = db.query(
        InvoiceRequest.status,
        func.count(InvoiceRequest.id).label("cnt"),
        func.coalesce(func.sum(InvoiceRequest.amount_eur), 0).label("eur_sum"),
        func.coalesce(func.sum(InvoiceRequest.credit_amount), 0).label("credit_sum"),
    ).group_by(InvoiceRequest.status).all()

    inv_counts  = {"pending": 0, "verified": 0, "cancelled": 0, "paid": 0, "total": 0}
    eur_by_status   = {"pending": 0.0, "verified": 0.0}
    credit_by_status = {"pending": 0, "verified": 0}

    for row in agg:
        s = row.status
        inv_counts[s]     = row.cnt
        inv_counts["total"] += row.cnt
        if s in eur_by_status:
            eur_by_status[s]    = float(row.eur_sum)
            credit_by_status[s] = int(row.credit_sum)

    # ── Active credit balance across all users ────────────────────
    balance_row = db.query(
        func.coalesce(func.sum(User.credit_balance), 0).label("total_balance"),
        func.coalesce(func.sum(User.credit_purchased), 0).label("total_purchased"),
        func.count().filter(User.credit_balance > 0).label("users_with_balance"),
    ).filter(User.is_active == True).one()

    return {
        "revenue": {
            "total_eur":          round(eur_by_status["verified"], 2),
            "pending_eur":        round(eur_by_status["pending"], 2),
            "total_credits_sold": credit_by_status["verified"],
            "pending_credits":    credit_by_status["pending"],
        },
        "credits": {
            "active_balance":     int(balance_row.total_balance),
            "total_purchased":    int(balance_row.total_purchased),
            "users_with_balance": int(balance_row.users_with_balance),
        },
        "invoices": inv_counts,
    }


@router.get("/my-invoices")
async def get_my_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ✅ Changed to Bearer token auth (Streamlit uses Bearer, not cookies)
) -> Any:
    """
    Get current user's invoice requests

    Returns list of invoices for the authenticated user, ordered by created_at desc
    Student can view their own invoice history without admin privileges
    """

    invoices = db.query(InvoiceRequest).filter(
        InvoiceRequest.user_id == current_user.id
    ).order_by(InvoiceRequest.created_at.desc()).all()

    # Build response
    result = []
    for invoice in invoices:
        result.append({
            "id": invoice.id,
            "credit_amount": invoice.credit_amount,
            "amount_eur": invoice.amount_eur,
            "coupon_code": invoice.coupon_code,
            "payment_reference": invoice.payment_reference,
            "status": invoice.status,
            "created_at": invoice.created_at,
            "verified_at": invoice.verified_at
        })

    return result


class InvoiceCancellationRequest(BaseModel):
    """Request body for invoice cancellation"""
    reason: str = "No reason provided"


