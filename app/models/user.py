from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from typing import Optional

from ..database import Base
from .specialization import SpecializationType


class UserRole(enum.Enum):
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    nickname = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    phone = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    medical_notes = Column(String, nullable=True)
    interests = Column(String, nullable=True)  # JSON string of interests array
    position = Column(String, nullable=True)  # Football position (goalkeeper, defender, midfielder, forward, coach)
    
    # 🎓 NEW: Specialization field (nullable for backward compatibility)
    specialization = Column(
        Enum(SpecializationType), 
        nullable=True,
        comment="User's chosen specialization track (Player/Coach)"
    )
    
    # 💰 NEW: Payment verification fields
    payment_verified = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Whether student has paid semester fees"
    )
    payment_verified_at = Column(
        DateTime, 
        nullable=True,
        comment="Timestamp when payment was verified"
    )
    payment_verified_by = Column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True,
        comment="Admin who verified the payment"
    )
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = relationship("User", remote_side=[id], foreign_keys=[created_by], post_update=True)
    created_users = relationship("User", foreign_keys=[created_by], remote_side=[created_by], overlaps="creator", post_update=True)
    
    # 💰 NEW: Payment verification relationships
    payment_verifier = relationship("User", remote_side=[id], foreign_keys=[payment_verified_by], post_update=True)
    groups = relationship("Group", secondary="group_users", back_populates="users")
    bookings = relationship("Booking", back_populates="user")
    attendances = relationship("Attendance", foreign_keys="Attendance.user_id", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    taught_sessions = relationship("Session", back_populates="instructor")
    marked_attendances = relationship("Attendance", foreign_keys="Attendance.marked_by", back_populates="marker")
    
    # Project relationships
    instructed_projects = relationship("Project", back_populates="instructor")
    project_enrollments = relationship("ProjectEnrollment", back_populates="user")
    
    # Gamification relationships (will be added after UserAchievement/UserStats are defined)
    
    # Message relationships
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("Message", back_populates="recipient", foreign_keys="Message.recipient_id")
    
    # 🎓 NEW: Specialization helper properties and methods
    @property
    def specialization_display(self) -> str:
        """Get user-friendly specialization display name"""
        return SpecializationType.get_display_name(self.specialization)
    
    @property
    def specialization_icon(self) -> str:
        """Get specialization emoji icon"""
        return SpecializationType.get_icon(self.specialization)
    
    @property
    def has_specialization(self) -> bool:
        """Check if user has chosen a specialization"""
        return self.specialization is not None
    
    # 🎓 NEW: Session access logic with specialization (preserves Mbappé logic)
    def can_access_session(self, session) -> bool:
        """
        Check if user can access session based on specialization
        ⚠️ CRITICAL: This preserves Mbappé cross-semester logic
        """
        # Cross-semester logic for Mbappé (preserve existing logic)
        if self.email == "mbappe@lfa.com":
            return True  # Mbappé can access ALL sessions
        
        # If user has no specialization, allow access (backward compatibility)
        if not self.specialization:
            return True
            
        # If session has no specialization requirement, allow access
        if not hasattr(session, 'target_specialization') or not session.target_specialization:
            return True
            
        # If session is mixed specialization, allow access
        if hasattr(session, 'mixed_specialization') and session.mixed_specialization:
            return True
            
        # Check specialization match
        return session.target_specialization == self.specialization
    
    # 🎓 NEW: Project access logic with specialization  
    def can_enroll_in_project(self, project) -> bool:
        """Check if user can enroll in project based on specialization"""
        # If user has no specialization, allow enrollment (backward compatibility)
        if not self.specialization:
            return True
            
        # If project has no specialization requirement, allow enrollment
        if not hasattr(project, 'target_specialization') or not project.target_specialization:
            return True
            
        # If project is mixed specialization, allow enrollment
        if hasattr(project, 'mixed_specialization') and project.mixed_specialization:
            return True
            
        # Check specialization match
        return project.target_specialization == self.specialization
    
    # 💰 NEW: Payment verification helper methods
    @property
    def payment_status_display(self) -> str:
        """Get user-friendly payment status display"""
        if self.payment_verified:
            return "✅ Verified"
        return "❌ Not Verified"
    
    @property
    def can_enroll_in_semester(self) -> bool:
        """Check if user can enroll in semester content based on payment"""
        # Admins and instructors can always enroll
        if self.role in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
            return True
        
        # Students must have payment verified
        return self.payment_verified
    
    def verify_payment(self, admin_user: 'User') -> None:
        """Mark payment as verified by admin"""
        self.payment_verified = True
        self.payment_verified_at = datetime.now(timezone.utc)
        self.payment_verified_by = admin_user.id
    
    def unverify_payment(self) -> None:
        """Mark payment as not verified"""
        self.payment_verified = False
        self.payment_verified_at = None
        self.payment_verified_by = None