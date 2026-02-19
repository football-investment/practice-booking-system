from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import secrets
import string

from ..database import Base


class InvitationCode(Base):
    """
    Invitation Code model - for partner/promotional one-time use codes

    Admin can generate unique invitation codes that give bonus credits.
    Each code can only be used once and optionally restricted to a specific email.
    """
    __tablename__ = "invitation_codes"

    id = Column(Integer, primary_key=True, index=True)

    # Unique invitation code (auto-generated)
    # Format: INV-YYYYMMDD-XXXXXX (e.g., INV-20251204-A3F2E8)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique invitation code"
    )

    # Partner/recipient information
    invited_name = Column(
        String(200),
        nullable=False,
        comment="Name of the person/organization receiving the code"
    )
    invited_email = Column(
        String(200),
        nullable=True,
        comment="Optional: Email restriction - only this email can use the code"
    )

    # Code value
    bonus_credits = Column(
        Integer,
        nullable=False,
        comment="Bonus credits to grant when code is used"
    )

    # Usage tracking
    is_used = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the code has been used"
    )
    used_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who redeemed this code"
    )
    used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the code was redeemed"
    )

    # Creation tracking
    created_by_admin_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin who created this code"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Expiration
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional expiration date"
    )

    # Admin notes
    notes = Column(
        Text,
        nullable=True,
        comment="Admin notes about this invitation code"
    )

    # Relationships
    used_by_user = relationship(
        "User",
        foreign_keys=[used_by_user_id],
        back_populates="redeemed_invitation_codes"
    )
    created_by_admin = relationship(
        "User",
        foreign_keys=[created_by_admin_id],
        back_populates="created_invitation_codes"
    )

    @staticmethod
    def generate_code() -> str:
        """
        Generate a unique invitation code
        Format: INV-YYYYMMDD-XXXXXX
        Example: INV-20251204-A3F2E8
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime('%Y%m%d')

        # Generate 6-character random alphanumeric string (uppercase)
        random_str = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

        return f"INV-{date_str}-{random_str}"

    def is_valid(self) -> bool:
        """Check if the invitation code is valid and can be used"""
        if self.is_used:
            return False

        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False

        return True

    def can_be_used_by_email(self, email: str) -> bool:
        """
        Check if this code can be used by the given email
        Returns True if no email restriction or email matches
        """
        if not self.invited_email:
            return True  # No email restriction

        return self.invited_email.lower() == email.lower()

    def __repr__(self):
        return f"<InvitationCode(code={self.code}, name={self.invited_name}, used={self.is_used}, credits={self.bonus_credits})>"
