"""
Coupon model for discount and bonus credit codes
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum

from ..database import Base


class CouponType(str, enum.Enum):
    """
    Coupon type enumeration

    Three types with different behaviors:
    1. BONUS_CREDITS: Instant free credits (no purchase/invoice required)
    2. PURCHASE_DISCOUNT_PERCENT: Percentage discount on credit package purchase (requires invoice + admin approval)
    3. PURCHASE_BONUS_CREDITS: Bonus credits after credit package purchase (requires invoice + admin approval)
    """
    BONUS_CREDITS = "BONUS_CREDITS"  # Instant free credits (e.g., +500 credits immediately)
    PURCHASE_DISCOUNT_PERCENT = "PURCHASE_DISCOUNT_PERCENT"  # % discount on purchase (e.g., 20% off)
    PURCHASE_BONUS_CREDITS = "PURCHASE_BONUS_CREDITS"  # Bonus credits after purchase (e.g., buy 1000cr, get +500cr bonus)

    # Legacy types (for backwards compatibility during migration)
    PERCENT = "PERCENT"  # DEPRECATED: Will be migrated to BONUS_CREDITS
    FIXED = "FIXED"  # DEPRECATED: Will be migrated to BONUS_CREDITS
    CREDITS = "CREDITS"  # DEPRECATED: Will be migrated to BONUS_CREDITS


class Coupon(Base):
    """
    Coupon model for managing discount and bonus credit codes

    Attributes:
        id: Primary key
        code: Unique coupon code (e.g., "WELCOME10")
        type: Type of coupon (bonus_credits, purchase_discount_percent, purchase_bonus_credits)
        discount_value: The discount value (interpretation depends on type)
            - BONUS_CREDITS: direct credits (500 = +500 credits immediately)
            - PURCHASE_DISCOUNT_PERCENT: percentage (0.2 = 20% discount on purchase)
            - PURCHASE_BONUS_CREDITS: bonus credits (500 = +500 credits after purchase)
        description: Human-readable description
        is_active: Whether the coupon is currently active
        expires_at: Expiration date (NULL = never expires)
        max_uses: Maximum number of times this coupon can be used (NULL = unlimited)
        current_uses: Current number of times this coupon has been used
        requires_purchase: Whether this coupon can only be used during credit purchase
        requires_admin_approval: Whether this coupon requires admin approval after purchase
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

    # New fields for purchase-based coupons
    requires_purchase = Column(Boolean, default=False, nullable=False,
                               comment="True if coupon can only be used during credit purchase")
    requires_admin_approval = Column(Boolean, default=False, nullable=False,
                                    comment="True if coupon requires admin approval after purchase")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Coupon(code='{self.code}', type='{self.type}', active={self.is_active})>"

    def set_flags_based_on_type(self):
        """
        Automatically set requires_purchase and requires_admin_approval based on coupon type
        Should be called before saving to database
        """
        if self.type == CouponType.BONUS_CREDITS:
            self.requires_purchase = False
            self.requires_admin_approval = False
        elif self.type == CouponType.PURCHASE_DISCOUNT_PERCENT:
            self.requires_purchase = True
            self.requires_admin_approval = True
        elif self.type == CouponType.PURCHASE_BONUS_CREDITS:
            self.requires_purchase = True
            self.requires_admin_approval = True
        # Legacy types (treat as BONUS_CREDITS)
        elif self.type in [CouponType.PERCENT, CouponType.FIXED, CouponType.CREDITS]:
            self.requires_purchase = False
            self.requires_admin_approval = False

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


class CouponUsage(Base):
    """
    Tracks coupon usage by users

    Prevents users from using the same coupon multiple times
    and provides audit trail of coupon redemptions.
    """
    __tablename__ = "coupon_usages"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey('coupons.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    credits_awarded = Column(Integer, nullable=False, comment="Amount of credits awarded from this coupon")
    used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    coupon = relationship("Coupon", backref="usages")
    user = relationship("User", backref="coupon_usages")

    def __repr__(self):
        return f"<CouponUsage(coupon_id={self.coupon_id}, user_id={self.user_id}, credits={self.credits_awarded})>"
