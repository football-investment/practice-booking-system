"""
Coupon model for discount and bonus credit codes
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum

from ..database import Base


class CouponType(str, enum.Enum):
    """Coupon type enumeration"""
    PERCENT = "percent"  # Percentage discount (e.g., 10% off)
    FIXED = "fixed"  # Fixed amount discount (e.g., 50€ off)
    CREDITS = "credits"  # Bonus credits (e.g., +100 credits)


class Coupon(Base):
    """
    Coupon model for managing discount and bonus credit codes

    Attributes:
        id: Primary key
        code: Unique coupon code (e.g., "WELCOME10")
        type: Type of coupon (percent, fixed, credits)
        discount_value: The discount value (interpretation depends on type)
            - PERCENT: percentage (0.1 = 10%)
            - FIXED: amount in EUR (50 = 50€ off)
            - CREDITS: bonus credits (100 = +100 credits)
        description: Human-readable description
        is_active: Whether the coupon is currently active
        expires_at: Expiration date (NULL = never expires)
        max_uses: Maximum number of times this coupon can be used (NULL = unlimited)
        current_uses: Current number of times this coupon has been used
        created_at: When the coupon was created
        updated_at: When the coupon was last modified
    """
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(SQLEnum(CouponType), nullable=False)
    discount_value = Column(Float, nullable=False)
    description = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_uses = Column(Integer, nullable=True)  # NULL = unlimited
    current_uses = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Coupon(code='{self.code}', type='{self.type}', active={self.is_active})>"

    def is_valid(self) -> bool:
        """Check if coupon is currently valid"""
        # Must be active
        if not self.is_active:
            return False

        # Check expiration
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False

        # Check usage limit
        if self.max_uses and self.current_uses >= self.max_uses:
            return False

        return True

    def increment_usage(self):
        """Increment the current uses counter"""
        self.current_uses += 1
