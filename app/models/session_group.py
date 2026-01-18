"""
Session Group Assignment Models

DYNAMIC GROUP ASSIGNMENT AT SESSION START

Workflow:
1. Session created with capacity = (head + assistants) × 4
2. Students book session
3. At session start (check-in):
   - Head coach sees who is PRESENT
   - Auto-assign or manually assign students to groups
   - Groups created based on ACTUAL attendance, not pre-defined
4. Groups saved for this specific session
5. Performance tracking per group

Example:
- Session capacity: 8 (2 instructors)
- Bookings: 7 students
- Present at check-in: 6 students
- Groups created: 2 groups × 3 students (not 4-4!)
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class SessionGroupAssignment(Base):
    """
    Dynamic group created at session start

    One session can have multiple groups (based on instructor count)
    Groups are NOT pre-defined - created when head coach starts session
    """
    __tablename__ = "session_group_assignments"

    id = Column(Integer, primary_key=True, index=True)

    # Session context
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'),
                       nullable=False, index=True,
                       comment="Session these groups belong to")

    # Group metadata
    group_number = Column(Integer, nullable=False,
                         comment="Group number within session (1, 2, 3, 4...)")

    # Instructor assignment
    instructor_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                          nullable=False,
                          comment="Instructor leading this group")

    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'),
                       nullable=True,
                       comment="Head coach who created this assignment")

    # Relationships
    session = relationship("Session", foreign_keys=[session_id],
                         backref="group_assignments")
    instructor = relationship("User", foreign_keys=[instructor_id],
                            backref="session_groups_led")
    creator = relationship("User", foreign_keys=[created_by],
                         backref="session_groups_created")
    students = relationship("SessionGroupStudent", back_populates="group",
                          cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('session_id', 'group_number', name='uq_session_group_number'),
    )

    @property
    def student_count(self):
        """Number of students in this group"""
        return len(self.students)

    @property
    def student_list(self):
        """List of student names in this group"""
        return [s.student.name for s in self.students if s.student]

    def __repr__(self):
        return (f"<SessionGroupAssignment("
                f"session_id={self.session_id}, "
                f"group={self.group_number}, "
                f"instructor_id={self.instructor_id}, "
                f"students={self.student_count})>")


class SessionGroupStudent(Base):
    """
    Student assignment to session group

    Created at session start when head coach assigns students to groups
    """
    __tablename__ = "session_group_students"

    id = Column(Integer, primary_key=True, index=True)

    # Group assignment
    session_group_id = Column(Integer, ForeignKey('session_group_assignments.id', ondelete='CASCADE'),
                             nullable=False, index=True,
                             comment="Which group this student is in")

    # Student
    student_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                       nullable=False,
                       comment="Student assigned to this group")

    # Timestamp
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    group = relationship("SessionGroupAssignment", back_populates="students")
    student = relationship("User", foreign_keys=[student_id],
                         backref="session_group_memberships")

    __table_args__ = (
        UniqueConstraint('session_group_id', 'student_id', name='uq_session_group_student'),
    )

    def __repr__(self):
        return (f"<SessionGroupStudent("
                f"group_id={self.session_group_id}, "
                f"student_id={self.student_id})>")
