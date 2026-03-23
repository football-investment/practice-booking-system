"""Invoice admin operations"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel

from .....database import get_db
from .....dependencies import get_current_admin_user
from .....models.user import User
from .....models.invoice_request import InvoiceRequest
from .....models.credit_transaction import CreditTransaction, TransactionType


router = APIRouter()


class InvoiceCancellationRequest(BaseModel):
    """Request body for invoice cancellation"""
    reason: str = "No reason provided"


class InvoiceRequestCreate(BaseModel):
    """Request body for creating an invoice request"""
    credit_amount: int
    amount_eur: float
    coupon_code: str | None = None



@router.post("/{invoice_id}/verify")
async def verify_invoice_payment(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Verify invoice payment and add credits to student account (Admin only) - Supports both Bearer token and cookie auth
    """
    # Get invoice
    invoice = db.query(InvoiceRequest).filter(
        InvoiceRequest.id == invoice_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if already verified
    if invoice.status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already verified"
        )

    # Check if cancelled
    if invoice.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify cancelled invoice"
        )

    # Get student
    student = db.query(User).filter(User.id == invoice.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Update invoice status
    now = datetime.now(timezone.utc)
    invoice.status = "verified"
    invoice.verified_at = now

    # Add credits to student account
    old_balance = student.credit_balance
    old_purchased = student.credit_purchased

    student.credit_balance += invoice.credit_amount
    student.credit_purchased += invoice.credit_amount

    new_balance = student.credit_balance
    new_purchased = student.credit_purchased

    ct = CreditTransaction(
        user_id=student.id,
        transaction_type=TransactionType.PURCHASE.value,
        amount=invoice.credit_amount,
        balance_after=new_balance,
        description=f"Invoice #{invoice.id} payment verified by admin (API)",
        idempotency_key=f"api-invoice-verify-{invoice.id}",
        performed_by_user_id=current_user.id,
    )
    db.add(ct)

    db.commit()
    db.refresh(invoice)
    db.refresh(student)

    print(f"✅ Invoice {invoice.id} verified by {current_user.name}. Added {invoice.credit_amount} credits to {student.name} (Balance: {old_balance} → {new_balance}, Purchased: {old_purchased} → {new_purchased})")

    return {
        "success": True,
        "message": f"Invoice payment verified! {invoice.credit_amount} credits added to {student.name}.",
        "invoice_id": invoice.id,
        "payment_reference": invoice.payment_reference,
        "student_email": student.email,
        "student_name": student.name,
        "credits_added": invoice.credit_amount,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "old_purchased": old_purchased,
        "new_purchased": new_purchased,
        "verified_by": current_user.name,
        "verified_at": invoice.verified_at
    }


@router.post("/{invoice_id}/cancel")
async def cancel_invoice(
    request: Request,
    invoice_id: int,
    cancellation_request: InvoiceCancellationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Cancel an invoice request (Admin only) - Supports both Bearer token and cookie auth
    """
    # Get invoice
    invoice = db.query(InvoiceRequest).filter(
        InvoiceRequest.id == invoice_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if already verified
    if invoice.status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel verified invoice"
        )

    # Check if already cancelled
    if invoice.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already cancelled"
        )

    # Get student
    student = db.query(User).filter(User.id == invoice.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Update invoice status
    now = datetime.now(timezone.utc)
    invoice.status = "cancelled"

    db.commit()
    db.refresh(invoice)

    print(f"❌ Invoice {invoice.id} cancelled by {current_user.name}. Reason: {cancellation_request.reason}")

    return {
        "success": True,
        "message": f"Invoice cancelled. Reason: {cancellation_request.reason}",
        "invoice_id": invoice.id,
        "payment_reference": invoice.payment_reference,
        "student_email": student.email,
        "student_name": student.name,
        "cancelled_by": current_user.name,
        "cancellation_reason": cancellation_request.reason
    }


@router.post("/{invoice_id}/unverify")
async def unverify_invoice_payment(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Unverify invoice payment and revert credits (Admin only) - Supports both Bearer token and cookie auth
    This reverses the verification: removes credits and sets status back to pending
    """
    # Get invoice
    invoice = db.query(InvoiceRequest).filter(
        InvoiceRequest.id == invoice_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if already pending
    if invoice.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already pending"
        )

    # Check if cancelled
    if invoice.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unverify cancelled invoice"
        )

    # Check if verified
    if invoice.status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must be verified to unverify"
        )

    # Get student
    student = db.query(User).filter(User.id == invoice.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Store old values
    old_balance = student.credit_balance
    old_purchased = student.credit_purchased

    # Remove credits from student account (REVERT)
    student.credit_balance -= invoice.credit_amount
    student.credit_purchased -= invoice.credit_amount

    new_balance = student.credit_balance
    new_purchased = student.credit_purchased

    # Update invoice status back to pending
    now = datetime.now(timezone.utc)
    invoice.status = "pending"
    invoice.verified_at = None  # Clear verification timestamp

    ct = CreditTransaction(
        user_id=student.id,
        transaction_type=TransactionType.ADMIN_ADJUSTMENT.value,
        amount=-invoice.credit_amount,
        balance_after=new_balance,
        description=f"Invoice #{invoice.id} unverified by admin (API) — credits removed",
        idempotency_key=f"api-invoice-unverify-{invoice.id}-{uuid.uuid4().hex[:8]}",
        performed_by_user_id=current_user.id,
    )
    db.add(ct)

    db.commit()
    db.refresh(invoice)
    db.refresh(student)

    print(f"🔄 Invoice {invoice.id} UNVERIFIED by {current_user.name}. Removed {invoice.credit_amount} credits from {student.name} (Balance: {old_balance} → {new_balance}, Purchased: {old_purchased} → {new_purchased})")

    return {
        "success": True,
        "message": f"Invoice unverified! {invoice.credit_amount} credits removed from {student.name}.",
        "invoice_id": invoice.id,
        "payment_reference": invoice.payment_reference,
        "student_email": student.email,
        "student_name": student.name,
        "credits_removed": invoice.credit_amount,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "old_purchased": old_purchased,
        "new_purchased": new_purchased,
        "unverified_by": current_user.name,
        "unverified_at": now
    }
