from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..database import Base


class InvoiceRequestStatus(str, enum.Enum):
    """Invoice request status enum"""
    PENDING = "pending"
    PAID = "paid"
    VERIFIED = "verified"
    CANCELLED = "cancelled"


class InvoiceRequest(Base):
    """Invoice Request model - each invoice request has a unique payment reference"""
    __tablename__ = "invoice_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Unique payment reference for THIS specific invoice
    # Format: LFA-YYYYMMDD-HHMMSS-ID-HASH (e.g., LFA-20251203-143052-00001-A3F2)
    # Max 30 characters (SWIFT limit is 35 characters)
    # Only alphanumeric characters + hyphen (SWIFT compatible)
    # Components ensure NO duplication even with 1000 invoices/day for 1000+ years:
    # - LFA: Prefix (4 chars)
    # - YYYYMMDD: Date (8 chars)
    # - HHMMSS: Time in seconds (6 chars)
    # - ID: Sequential auto-increment ID (5 chars)
    # - HASH: 4-char random hash from timestamp+id+user (4 chars)
    # - Separators: 3x hyphen (3 chars)
    # Total: 30 characters
    payment_reference = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique payment reference: LFA-YYYYMMDD-HHMMSS-ID-HASH (max 30 chars, SWIFT compatible)"
    )

    # Invoice details
    amount_eur = Column(Float, nullable=False, comment="Amount in EUR")
    credit_amount = Column(Integer, nullable=False, comment="Credit amount")
    specialization = Column(String(50), nullable=True, comment="Specialization type")
    coupon_code = Column(String(50), nullable=True, comment="Applied coupon code (if any)")

    # Status tracking
    # Using String instead of SQLEnum to avoid automatic enum conversion issues
    status = Column(
        String(20),
        default="pending",
        nullable=False
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True, comment="When payment was made")
    verified_at = Column(DateTime(timezone=True), nullable=True, comment="When admin verified payment")

    # Relationships
    user = relationship("User", back_populates="invoice_requests")

    def __repr__(self):
        return f"<InvoiceRequest(id={self.id}, user_id={self.user_id}, payment_ref={self.payment_reference}, amount={self.amount_eur} EUR, status={self.status})>"
