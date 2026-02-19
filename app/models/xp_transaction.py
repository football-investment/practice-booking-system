"""
XP Transaction Model
Tracks XP (Experience Points) rewards and history for users
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from app.database import Base


class XPTransaction(Base):
    """
    XP Transaction Model - Tracks XP rewards history

    Similar to CreditTransaction but for Experience Points
    """
    __tablename__ = "xp_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # R06: Idempotency key prevents duplicate XP grants on concurrent reward distribution.
    # Nullable for legacy rows; unique partial index enforced by migration rw01concurr00.
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=False, index=True)
    semester_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="xp_transactions")
    semester = relationship("Semester")

    def __repr__(self):
        return f"<XPTransaction(id={self.id}, user_id={self.user_id}, type={self.transaction_type}, amount={self.amount})>"
