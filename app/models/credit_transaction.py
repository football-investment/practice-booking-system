"""
💰 Credit Transaction Model
Tracks all credit-related transactions (purchases, enrollments, refunds)
"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Dict, Any

from ..database import Base


class TransactionType(enum.Enum):
    """Credit transaction types"""
    PURCHASE = "PURCHASE"           # User purchased credits (500/1000/2000 EUR)
    ENROLLMENT = "ENROLLMENT"       # Credits deducted for semester enrollment
    REFUND = "REFUND"              # Credits refunded (enrollment withdrawal before approval)
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"  # Manual admin adjustment
    EXPIRATION = "EXPIRATION"      # Credits expired (2 year limit)


class CreditTransaction(Base):
    """Track all credit balance changes with full audit trail"""
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_license_id = Column(Integer, ForeignKey("user_licenses.id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # Transaction details
    transaction_type = Column(String(50), nullable=False)  # PURCHASE, ENROLLMENT, REFUND, etc.
    amount = Column(Integer, nullable=False)               # +1000 or -250 (negative for deductions)
    balance_after = Column(Integer, nullable=False)        # Balance snapshot after transaction
    description = Column(Text, nullable=True)              # Human-readable description

    # Related entities (optional)
    semester_id = Column(Integer, ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True)
    enrollment_id = Column(Integer, ForeignKey("semester_enrollments.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user_license = relationship("UserLicense", back_populates="credit_transactions")
    semester = relationship("Semester")
    enrollment = relationship("SemesterEnrollment")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_license_id": self.user_license_id,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "description": self.description,
            "semester_id": self.semester_id,
            "enrollment_id": self.enrollment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
