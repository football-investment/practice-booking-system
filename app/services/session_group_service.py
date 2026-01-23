"""
Session Group Assignment Service

Handles dynamic group creation at session start based on actual attendance.

Workflow:
1. Students book session
2. At session start, head coach sees who checked in (PRESENT)
3. Auto-assign algorithm distributes students evenly across instructors
4. Head coach can manually adjust
5. Groups saved for this session
"""

from sqlalchemy.orm import Session
from typing import List, Dict

from app.models import (
    SessionGroupAssignment,
    SessionGroupStudent,
    Session as SessionModel,
    Attendance,
    AttendanceStatus,
    User
)


class SessionGroupService:
    """Service for managing dynamic session group assignments"""

    @staticmethod
    def get_present_students(db: Session, session_id: int) -> List[User]:
        """
        Get all students who checked in as PRESENT for this session

        Returns list of User objects
        """
        attendances = db.query(Attendance).filter(
            Attendance.session_id == session_id,
            Attendance.status == AttendanceStatus.PRESENT
        ).all()

        return [att.user for att in attendances if att.user]

    @staticmethod
    def get_available_instructors(db: Session, session_id: int) -> List[User]:
        """
        Get all instructors assigned to this session

        Includes:
        - Session instructor (head coach)
        - Any assistant instructors who checked in

        Returns list of User objects
        """
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            return []

        instructors = []

        # Add session instructor (head coach)
        if session.instructor:
            instructors.append(session.instructor)

        # TODO: Add assistant instructors
        # For now, just return head coach

        return instructors

    @staticmethod
    def auto_assign_groups(
        db: Session,
        session_id: int,
        created_by_user_id: int
    ) -> List[SessionGroupAssignment]:
        """
        Auto-assign students to groups based on actual attendance

        Algorithm:
        1. Get present students
        2. Get available instructors
        3. Calculate optimal group size
        4. Distribute students evenly across instructors

        Example:
        - 2 instructors (head + assistant)
        - 6 students present
        - Result: 2 groups × 3 students

        Returns: List of created SessionGroupAssignment objects
        """
        # Get present students
        students = SessionGroupService.get_present_students(db, session_id)
        student_count = len(students)

        if student_count == 0:
            raise ValueError("No students checked in yet. Cannot create groups.")

        # Get available instructors
        instructors = SessionGroupService.get_available_instructors(db, session_id)
        instructor_count = len(instructors)

        if instructor_count == 0:
            raise ValueError("No instructors available for this session.")

        # Calculate distribution
        # Example: 6 students, 2 instructors → [3, 3]
        # Example: 7 students, 2 instructors → [4, 3]
        base_size = student_count // instructor_count
        remainder = student_count % instructor_count

        group_sizes = []
        for i in range(instructor_count):
            size = base_size + (1 if i < remainder else 0)
            group_sizes.append(size)

        # Clear existing groups (if re-assigning)
        existing_groups = db.query(SessionGroupAssignment).filter(
            SessionGroupAssignment.session_id == session_id
        ).all()
        for group in existing_groups:
            db.delete(group)
        db.flush()

        # Create groups
        created_groups = []
        student_index = 0

        for group_number, (instructor, group_size) in enumerate(zip(instructors, group_sizes), start=1):
            # Create group
            group = SessionGroupAssignment(
                session_id=session_id,
                group_number=group_number,
                instructor_id=instructor.id,
                created_by=created_by_user_id
            )
            db.add(group)
            db.flush()  # Get group ID

            # Assign students to this group
            for _ in range(group_size):
                if student_index < len(students):
                    student = students[student_index]
                    student_assignment = SessionGroupStudent(
                        session_group_id=group.id,
                        student_id=student.id
                    )
                    db.add(student_assignment)
                    student_index += 1

            db.flush()
            db.refresh(group)
            created_groups.append(group)

        db.commit()
        return created_groups

    @staticmethod
    def get_session_groups(db: Session, session_id: int) -> List[SessionGroupAssignment]:
        """Get all groups for a session"""
        return db.query(SessionGroupAssignment).filter(
            SessionGroupAssignment.session_id == session_id
        ).order_by(SessionGroupAssignment.group_number).all()

    @staticmethod
    def move_student_to_group(
        db: Session,
        student_id: int,
        from_group_id: int,
        to_group_id: int
    ) -> bool:
        """
        Move a student from one group to another

        Used for manual adjustments by head coach
        """
        # Remove from old group
        old_assignment = db.query(SessionGroupStudent).filter(
            SessionGroupStudent.session_group_id == from_group_id,
            SessionGroupStudent.student_id == student_id
        ).first()

        if not old_assignment:
            return False

        db.delete(old_assignment)

        # Add to new group
        new_assignment = SessionGroupStudent(
            session_group_id=to_group_id,
            student_id=student_id
        )
        db.add(new_assignment)

        db.commit()
        return True

    @staticmethod
    def get_group_summary(db: Session, session_id: int) -> Dict:
        """
        Get summary of group assignments for display

        Returns:
        {
            "session_id": 123,
            "total_students": 6,
            "total_instructors": 2,
            "groups": [
                {
                    "group_number": 1,
                    "instructor_name": "Maria García",
                    "student_count": 3,
                    "students": ["Alice", "Bob", "Charlie"]
                },
                {
                    "group_number": 2,
                    "instructor_name": "John Doe",
                    "student_count": 3,
                    "students": ["David", "Emma", "Frank"]
                }
            ]
        }
        """
        groups = SessionGroupService.get_session_groups(db, session_id)

        group_data = []
        total_students = 0

        for group in groups:
            students = [s.student.name for s in group.students if s.student]
            total_students += len(students)

            group_data.append({
                "group_number": group.group_number,
                "instructor_name": group.instructor.name if group.instructor else "Unknown",
                "instructor_id": group.instructor_id,
                "student_count": len(students),
                "students": students,
                "student_ids": [s.student_id for s in group.students]
            })

        return {
            "session_id": session_id,
            "total_students": total_students,
            "total_instructors": len(groups),
            "groups": group_data
        }

    @staticmethod
    def delete_all_groups(db: Session, session_id: int) -> bool:
        """Delete all groups for a session (reset)"""
        groups = db.query(SessionGroupAssignment).filter(
            SessionGroupAssignment.session_id == session_id
        ).all()

        for group in groups:
            db.delete(group)

        db.commit()
        return True
