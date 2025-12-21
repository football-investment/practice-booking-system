from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..database import Base


class SemesterStatus(str, enum.Enum):
    """Semester lifecycle phases"""
    DRAFT = "DRAFT"  # Admin created, no instructor, no sessions
    SEEKING_INSTRUCTOR = "SEEKING_INSTRUCTOR"  # Admin looking for instructor
    INSTRUCTOR_ASSIGNED = "INSTRUCTOR_ASSIGNED"  # Has instructor, no sessions yet
    READY_FOR_ENROLLMENT = "READY_FOR_ENROLLMENT"  # Has instructor + sessions, students can enroll
    ONGOING = "ONGOING"  # Past enrollment deadline, classes in progress
    COMPLETED = "COMPLETED"  # All sessions finished
    CANCELLED = "CANCELLED"  # Admin cancelled


# Many-to-many association table for additional instructors
semester_instructors = Table(
    'semester_instructors',
    Base.metadata,
    Column('semester_id', Integer, ForeignKey('semesters.id', ondelete='CASCADE'), primary_key=True),
    Column('instructor_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # "2024/1"
    name = Column(String, nullable=False)  # "2024/25 őszi félév"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Lifecycle status (new, preferred)
    status = Column(Enum(SemesterStatus, name='semester_status'), nullable=False, default=SemesterStatus.DRAFT, index=True,
                   comment="Current lifecycle phase of the semester")

    # DEPRECATED: Use 'status' instead
    is_active = Column(Boolean, default=True,
                      comment="DEPRECATED: Use status field instead. Kept for backward compatibility.")

    # 💰 CREDIT SYSTEM: Enrollment cost for this semester
    enrollment_cost = Column(Integer, nullable=False, default=500,
                            comment="Credit cost to enroll in this semester (admin adjustable)")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 🥋 Master Instructor (Grandmaster who approves enrollments)
    master_instructor_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                                  comment="Master instructor who approves enrollment requests for this semester")

    # 🎯 SPECIALIZATION & AGE GROUP FIELDS (for semester filtering)
    specialization_type = Column(String(50), nullable=True, index=True,
                                 comment="Specialization type (e.g., LFA_PLAYER_PRE, GANCUJU_PLAYER_YOUTH)")
    age_group = Column(String(20), nullable=True, index=True,
                      comment="Age group (PRE, YOUTH, AMATEUR, PRO)")
    theme = Column(String(200), nullable=True,
                  comment="Marketing theme (e.g., 'New Year Challenge', 'Q1', 'Fall')")
    focus_description = Column(String(500), nullable=True,
                              comment="Focus description (e.g., 'Újévi fogadalmak, friss kezdés')")

    # 📍 LOCATION FIELDS (for semester-level location)
    # Used for LFA_PLAYER (BUDA/PEST split), GANCUJU (city-based), INTERNSHIP (city only)
    location_city = Column(String(100), nullable=True,
                          comment="City where semester takes place (e.g., 'Budapest', 'Debrecen')")
    location_venue = Column(String(200), nullable=True,
                           comment="Venue/campus name (e.g., 'Buda Campus', 'Pest Campus')")
    location_address = Column(String(500), nullable=True,
                             comment="Full address of the primary location")

    # Relationships
    master_instructor = relationship("User", foreign_keys=[master_instructor_id],
                                    backref="mastered_semesters")
    assistant_instructors = relationship("User", secondary=semester_instructors,
                                        backref="assisted_semesters")
    groups = relationship("Group", back_populates="semester")
    sessions = relationship("Session", back_populates="semester")
    projects = relationship("Project", back_populates="semester")
    enrollments = relationship("SemesterEnrollment", back_populates="semester", cascade="all, delete-orphan")