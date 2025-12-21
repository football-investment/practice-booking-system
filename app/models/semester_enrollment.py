"""
🎓 Semester Enrollment Model
Track student specialization enrollments per semester with payment verification
"""
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, UniqueConstraint, Index, Enum, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import enum
import hashlib

from ..database import Base


class EnrollmentStatus(enum.Enum):
    """Enrollment request status"""
    PENDING = "pending"      # Student requested, waiting for admin approval
    APPROVED = "approved"    # Admin approved, enrollment active
    REJECTED = "rejected"    # Admin rejected the request
    WITHDRAWN = "withdrawn"  # Student withdrew their request


class SemesterEnrollment(Base):
    """
    Track which specializations a student is enrolled in per semester

    Business Logic:
    - Students can have different specialization portfolios each semester
    - Payment verification is per-semester-per-specialization
    - UserLicense data (progress/levels) persists even without active enrollment
    - Students can always switch between specializations, but booking requires active enrollment

    Example Student Journey:
    - Semester 1: 4 specializations → 4 enrollment records
    - Semester 2: 2 specializations → 2 new enrollment records
    - Semester 3: 3 specializations → 3 new enrollment records
    """
    __tablename__ = "semester_enrollments"

    id = Column(Integer, primary_key=True, index=True)

    # Core relationships
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True,
                     comment="Student who is enrolled")
    semester_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"),
                        nullable=False, index=True,
                        comment="Semester for this enrollment")
    user_license_id = Column(Integer, ForeignKey("user_licenses.id", ondelete="CASCADE"),
                            nullable=False, index=True,
                            comment="Link to UserLicense (tracks progress/levels)")

    # 🆕 NEW: Enrollment request workflow (student requests → admin approves)
    request_status = Column(Enum(EnrollmentStatus), nullable=False, default=EnrollmentStatus.PENDING, index=True,
                           comment="Enrollment request status: PENDING/APPROVED/REJECTED/WITHDRAWN")
    requested_at = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc),
                         comment="When student requested enrollment")
    approved_at = Column(DateTime(timezone=True), nullable=True,
                        comment="When admin approved/rejected the request")
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True,
                        comment="Admin who approved/rejected")
    rejection_reason = Column(String, nullable=True,
                             comment="Reason for rejection (if rejected)")

    # Payment tracking (per-semester-per-specialization)
    payment_reference_code = Column(String(50), nullable=True, unique=True, index=True,
                                   comment="Unique payment reference code for bank transfer (e.g., LFA-INT-2024S1-042-A7B9)")
    payment_verified = Column(Boolean, nullable=False, default=False, index=True,
                             comment="Whether student paid for THIS specialization in THIS semester")
    payment_verified_at = Column(DateTime(timezone=True), nullable=True,
                                comment="When payment was verified")
    payment_verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                                nullable=True,
                                comment="Admin user who verified payment")

    # Status
    is_active = Column(Boolean, nullable=False, default=False, index=True,
                      comment="Whether this enrollment is currently active (auto-set when approved)")
    enrolled_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        comment="When student enrolled in this spec for this semester")
    deactivated_at = Column(DateTime(timezone=True), nullable=True,
                           comment="When enrollment was deactivated (if applicable)")

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="semester_enrollments")
    semester = relationship("Semester", back_populates="enrollments")
    user_license = relationship("UserLicense", back_populates="semester_enrollments")
    payment_verifier = relationship("User", foreign_keys=[payment_verified_by])
    approver = relationship("User", foreign_keys=[approved_by])  # 🆕 NEW

    # Constraints (defined in migration but documented here)
    __table_args__ = (
        UniqueConstraint('user_id', 'semester_id', 'user_license_id',
                        name='uq_semester_enrollments_user_semester_license'),
        Index('ix_semester_enrollments_user_id', 'user_id'),
        Index('ix_semester_enrollments_semester_id', 'semester_id'),
        Index('ix_semester_enrollments_user_license_id', 'user_license_id'),
        Index('ix_semester_enrollments_payment_verified', 'payment_verified'),
        Index('ix_semester_enrollments_is_active', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "semester_id": self.semester_id,
            "user_license_id": self.user_license_id,
            "payment_verified": self.payment_verified,
            "payment_verified_at": self.payment_verified_at.isoformat() if self.payment_verified_at else None,
            "payment_verified_by": self.payment_verified_by,
            "is_active": self.is_active,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def specialization_type(self) -> Optional[str]:
        """Get specialization type from linked UserLicense"""
        if self.user_license:
            return self.user_license.specialization_type
        return None

    @property
    def payment_status_display(self) -> str:
        """Get user-friendly payment status display"""
        if self.payment_verified:
            return "✅ Paid"
        return "❌ Not Paid"

    @property
    def status_display(self) -> str:
        """Get user-friendly enrollment status"""
        if self.request_status == EnrollmentStatus.PENDING:
            return "⏳ Pending Approval"
        elif self.request_status == EnrollmentStatus.REJECTED:
            return "❌ Rejected"
        elif self.request_status == EnrollmentStatus.WITHDRAWN:
            return "🚫 Withdrawn"
        elif self.request_status == EnrollmentStatus.APPROVED:
            if not self.is_active:
                return "🔒 Inactive"
            if self.payment_verified:
                return "✅ Active & Paid"
            return "⚠️ Active (Unpaid)"
        return "❓ Unknown"

    def verify_payment(self, admin_user_id: int) -> None:
        """Mark payment as verified"""
        self.payment_verified = True
        self.payment_verified_at = datetime.now(timezone.utc)
        self.payment_verified_by = admin_user_id

    def unverify_payment(self) -> None:
        """Mark payment as not verified"""
        self.payment_verified = False
        self.payment_verified_at = None
        self.payment_verified_by = None

    def deactivate(self) -> None:
        """Deactivate this enrollment"""
        self.is_active = False
        self.deactivated_at = datetime.now(timezone.utc)

    def reactivate(self) -> None:
        """Reactivate this enrollment"""
        self.is_active = True
        self.deactivated_at = None

    # 🆕 NEW: Enrollment request workflow methods
    def approve(self, admin_user_id: int) -> None:
        """Admin approves the enrollment request"""
        self.request_status = EnrollmentStatus.APPROVED
        self.approved_at = datetime.now(timezone.utc)
        self.approved_by = admin_user_id
        self.is_active = True  # Auto-activate when approved
        self.rejection_reason = None

    def reject(self, admin_user_id: int, reason: str = None) -> None:
        """Admin rejects the enrollment request"""
        self.request_status = EnrollmentStatus.REJECTED
        self.approved_at = datetime.now(timezone.utc)
        self.approved_by = admin_user_id
        self.is_active = False
        self.rejection_reason = reason

    def withdraw(self) -> None:
        """Student withdraws their enrollment request"""
        self.request_status = EnrollmentStatus.WITHDRAWN
        self.is_active = False

    def generate_payment_code(self) -> str:
        """
        Generate unique payment reference code for bank transfer

        Format: LFA-{SPEC_CODE}-{SEMESTER_CODE}-{USER_ID}-{CHECKSUM}
        Example: LFA-INT-2024S1-042-A7B9

        SPEC_CODE mapping:
        - INTERNSHIP → INT
        - GANCUJU_PLAYER → GCJ
        - LFA_FOOTBALL_PLAYER → LFP
        - LFA_COACH → LFC
        """
        # Get specialization code
        spec_map = {
            'INTERNSHIP': 'INT',
            'GANCUJU_PLAYER': 'GCJ',
            'LFA_FOOTBALL_PLAYER': 'LFP',
            'LFA_COACH': 'LFC'
        }
        spec_code = spec_map.get(self.specialization_type, 'UNK')

        # Get semester code (e.g., "2024S1" from semester name or ID)
        semester_code = f"S{self.semester_id}"
        if self.semester and self.semester.name:
            # Try to extract year and semester from name like "Spring 2024"
            import re
            match = re.search(r'(\d{4})', self.semester.name)
            if match:
                year = match.group(1)
                if 'Spring' in self.semester.name or 'Tavasz' in self.semester.name:
                    semester_code = f"{year}S1"
                elif 'Fall' in self.semester.name or 'Ősz' in self.semester.name:
                    semester_code = f"{year}S2"
                else:
                    semester_code = f"{year}S{self.semester_id}"

        # User ID (zero-padded to 3 digits)
        user_id_str = str(self.user_id).zfill(3)

        # Generate checksum from enrollment ID and user ID
        checksum_input = f"{self.id}-{self.user_id}-{self.semester_id}-{self.specialization_type}"
        checksum = hashlib.md5(checksum_input.encode()).hexdigest()[:4].upper()

        # Assemble payment code
        payment_code = f"LFA-{spec_code}-{semester_code}-{user_id_str}-{checksum}"

        return payment_code

    def set_payment_code(self) -> str:
        """Generate and save payment reference code"""
        if not self.payment_reference_code:
            self.payment_reference_code = self.generate_payment_code()
        return self.payment_reference_code
