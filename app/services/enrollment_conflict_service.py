"""
⚠️ Enrollment Conflict Detection Service
=========================================
Detects time-based conflicts between sessions across different enrollment types

Business Rules:
- Users can enroll in multiple programs (Tournament + Mini Season + Academy) simultaneously
- The ONLY restriction: Cannot be in 2 places at the same time (session time overlap)
- This service provides WARNING only - does NOT block enrollment
- Used to inform users of potential scheduling conflicts before enrollment

Conflict Types Detected:
1. Session time overlap (same date/time across different enrollments)
2. Travel time conflicts (sessions too close together at different locations)

Architecture:
- Service layer (this file) - business logic
- API layer (endpoints/enrollments/conflict_check.py) - REST API
- Frontend layer (streamlit components) - user warnings
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Dict, Optional
from datetime import datetime, timedelta, date, time

from app.models.semester_enrollment import SemesterEnrollment
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.booking import Booking
from app.models.location import Location


class EnrollmentConflictService:
    """Service for detecting and reporting enrollment conflicts"""

    # Travel time buffer between sessions at different locations (minutes)
    TRAVEL_TIME_BUFFER_MINUTES = 30

    @staticmethod
    def check_session_time_conflict(
        user_id: int,
        semester_id: int,
        db: Session
    ) -> Dict:
        """
        Check if enrolling in this semester would create session time conflicts
        with the user's existing enrollments.

        Returns:
        {
            "has_conflict": bool,
            "conflicts": [
                {
                    "conflict_type": "time_overlap" | "travel_time",
                    "existing_session": {...},
                    "new_semester_session": {...},
                    "severity": "blocking" | "warning"
                }
            ],
            "warnings": [str]
        }
        """
        result = {
            "has_conflict": False,
            "conflicts": [],
            "warnings": []
        }

        # Get target semester info
        target_semester = db.query(Semester).filter(Semester.id == semester_id).first()
        if not target_semester:
            result["warnings"].append("Target semester not found")
            return result

        # Get all user's existing active enrollments (EXCLUDING the target semester)
        existing_enrollments = db.query(SemesterEnrollment).filter(
            and_(
                SemesterEnrollment.user_id == user_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.semester_id != semester_id  # Exclude target semester
            )
        ).all()

        if not existing_enrollments:
            # No existing enrollments = no conflicts possible
            return result

        # Get all sessions for target semester (future sessions only)
        today_start = datetime.combine(date.today(), time.min)
        target_sessions = db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == semester_id,
                SessionModel.date_start >= today_start
            )
        ).all()

        if not target_sessions:
            # No future sessions in target semester = no conflicts possible
            result["warnings"].append("No future sessions found in target semester")
            return result

        # Check each target session against existing bookings
        for target_session in target_sessions:
            # Get target session's location info
            target_location = EnrollmentConflictService._get_session_location(target_session, db)

            # Find all user's bookings on the same date as this target session
            target_date = target_session.date_start.date()
            existing_bookings = db.query(Booking).join(SessionModel).filter(
                and_(
                    Booking.user_id == user_id,
                    func.date(SessionModel.date_start) == target_date,
                    SessionModel.id.in_([
                        session.id
                        for enrollment in existing_enrollments
                        for session in enrollment.semester.sessions
                    ])
                )
            ).all()

            # Check for time conflicts with each existing booking
            for booking in existing_bookings:
                existing_session = booking.session
                existing_location = EnrollmentConflictService._get_session_location(existing_session, db)

                # Check for exact time overlap
                if EnrollmentConflictService._has_time_overlap(target_session, existing_session):
                    result["has_conflict"] = True
                    result["conflicts"].append({
                        "conflict_type": "time_overlap",
                        "existing_session": {
                            "id": existing_session.id,
                            "date": existing_session.date_start.date().isoformat() if existing_session.date_start else None,
                            "start_time": existing_session.date_start.time().isoformat() if existing_session.date_start else None,
                            "end_time": existing_session.date_end.time().isoformat() if existing_session.date_end else None,
                            "semester_name": existing_session.semester.name,
                            "location": existing_location
                        },
                        "new_semester_session": {
                            "id": target_session.id,
                            "date": target_session.date_start.date().isoformat() if target_session.date_start else None,
                            "start_time": target_session.date_start.time().isoformat() if target_session.date_start else None,
                            "end_time": target_session.date_end.time().isoformat() if target_session.date_end else None,
                            "semester_name": target_semester.name,
                            "location": target_location
                        },
                        "severity": "blocking"
                    })

                # Check for travel time conflict (different locations)
                elif EnrollmentConflictService._has_travel_conflict(
                    target_session, target_location,
                    existing_session, existing_location
                ):
                    result["has_conflict"] = True
                    result["conflicts"].append({
                        "conflict_type": "travel_time",
                        "existing_session": {
                            "id": existing_session.id,
                            "date": existing_session.date_start.date().isoformat() if existing_session.date_start else None,
                            "start_time": existing_session.date_start.time().isoformat() if existing_session.date_start else None,
                            "end_time": existing_session.date_end.time().isoformat() if existing_session.date_end else None,
                            "semester_name": existing_session.semester.name,
                            "location": existing_location
                        },
                        "new_semester_session": {
                            "id": target_session.id,
                            "date": target_session.date_start.date().isoformat() if target_session.date_start else None,
                            "start_time": target_session.date_start.time().isoformat() if target_session.date_start else None,
                            "end_time": target_session.date_end.time().isoformat() if target_session.date_end else None,
                            "semester_name": target_semester.name,
                            "location": target_location
                        },
                        "severity": "warning"
                    })

        return result

    @staticmethod
    def get_user_schedule(
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        db: Session = None
    ) -> Dict:
        """
        Get complete schedule for a user across all enrollment types.

        Returns:
        {
            "enrollments": [
                {
                    "enrollment_id": int,
                    "semester_name": str,
                    "enrollment_type": str,  # "TOURNAMENT", "MINI_SEASON", "ACADEMY_SEASON"
                    "sessions": [...]
                }
            ],
            "total_sessions": int,
            "date_range": {
                "start": date,
                "end": date
            }
        }
        """
        # Default date range: today + 90 days
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = start_date + timedelta(days=90)

        # Convert date to datetime for comparison with timestamp columns
        start_datetime = datetime.combine(start_date, time.min)  # 00:00:00
        end_datetime = datetime.combine(end_date, time.max)      # 23:59:59.999999

        # Get all active enrollments for user
        enrollments = db.query(SemesterEnrollment).filter(
            and_(
                SemesterEnrollment.user_id == user_id,
                SemesterEnrollment.is_active == True
            )
        ).all()

        result = {
            "enrollments": [],
            "total_sessions": 0,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }

        for enrollment in enrollments:
            semester = enrollment.semester

            # Determine enrollment type
            enrollment_type = EnrollmentConflictService._get_enrollment_type(semester)

            # Get sessions within date range
            sessions = db.query(SessionModel).filter(
                and_(
                    SessionModel.semester_id == semester.id,
                    SessionModel.date_start >= start_datetime,
                    SessionModel.date_start <= end_datetime
                )
            ).order_by(SessionModel.date_start).all()

            # Check which sessions user has booked
            user_bookings = db.query(Booking).filter(
                and_(
                    Booking.user_id == user_id,
                    Booking.session_id.in_([s.id for s in sessions])
                )
            ).all()

            booking_session_ids = {b.session_id for b in user_bookings}

            session_list = []
            for session in sessions:
                location = EnrollmentConflictService._get_session_location(session, db)
                session_list.append({
                    "id": session.id,
                    "date": session.date_start.date().isoformat() if session.date_start else None,
                    "start_time": session.date_start.time().isoformat() if session.date_start else None,
                    "end_time": session.date_end.time().isoformat() if session.date_end else None,
                    "location": location,
                    "is_booked": session.id in booking_session_ids
                })

            result["enrollments"].append({
                "enrollment_id": enrollment.id,
                "semester_id": semester.id,
                "semester_name": semester.name,
                "enrollment_type": enrollment_type,
                "sessions": session_list
            })

            result["total_sessions"] += len(sessions)

        return result

    @staticmethod
    def validate_enrollment_request(
        user_id: int,
        semester_id: int,
        db: Session
    ) -> Dict:
        """
        Full validation before enrollment (combines conflict check + business rules)

        Returns:
        {
            "allowed": bool,
            "conflicts": [...],
            "warnings": [...],
            "recommendations": [...]
        }
        """
        result = {
            "allowed": True,  # Always allowed, but may have warnings
            "conflicts": [],
            "warnings": [],
            "recommendations": []
        }

        # Check for time conflicts
        conflict_check = EnrollmentConflictService.check_session_time_conflict(
            user_id=user_id,
            semester_id=semester_id,
            db=db
        )

        result["conflicts"] = conflict_check.get("conflicts", [])
        result["warnings"].extend(conflict_check.get("warnings", []))

        # Add warnings for blocking conflicts
        blocking_conflicts = [c for c in result["conflicts"] if c["severity"] == "blocking"]
        if blocking_conflicts:
            result["warnings"].append(
                f"FIGYELMEZTETÉS: {len(blocking_conflicts)} időbeli ütközés található a meglévő foglalásaiddal. "
                "Ezeket a konfliktusokat meg kell oldanod a sima működéshez."
            )

        # Add recommendations for travel conflicts
        travel_conflicts = [c for c in result["conflicts"] if c["conflict_type"] == "travel_time"]
        if travel_conflicts:
            result["recommendations"].append(
                "Találtunk edzéseket, amelyek szorosan követik egymást különböző helyszíneken. "
                "Kérjük, ellenőrizd az utazási időt a helyszínek között."
            )

        return result

    # ========== Private Helper Methods ==========

    @staticmethod
    def _get_enrollment_type(semester) -> str:
        """Determine enrollment type from semester specialization type and code"""
        spec_value = semester.specialization_type.value if hasattr(semester.specialization_type, 'value') else str(semester.specialization_type)

        # Academy Season: All 4 age groups (PRE, YOUTH, AMATEUR, PRO)
        if spec_value in [
            "LFA_PLAYER_PRE_ACADEMY",
            "LFA_PLAYER_YOUTH_ACADEMY",
            "LFA_PLAYER_AMATEUR_ACADEMY",
            "LFA_PLAYER_PRO_ACADEMY"
        ]:
            return "ACADEMY_SEASON"
        # Tournament vs Mini Season: Determined by semester code
        elif spec_value in ["LFA_PLAYER_PRE", "LFA_PLAYER_YOUTH", "LFA_PLAYER_AMATEUR", "LFA_PLAYER_PRO", "LFA_FOOTBALL_PLAYER"]:
            # Check semester code: TOURN- prefix = Tournament, otherwise Mini Season
            if semester.code and semester.code.startswith("TOURN-"):
                return "TOURNAMENT"
            else:
                return "MINI_SEASON"
        else:
            return "OTHER"

    @staticmethod
    def _get_session_location(session: SessionModel, db: Session) -> Optional[Dict]:
        """Get location info for a session"""
        # First check session.location string (legacy field)
        if session.location:
            return {
                "location_name": session.location
            }

        # If not found, get location from semester
        if session.semester and session.semester.location_id:
            location = db.query(Location).filter(Location.id == session.semester.location_id).first()
            if location:
                return {
                    "location_name": location.name,
                    "location_city": location.city,
                    "location_id": location.id
                }

        return None

    @staticmethod
    def _has_time_overlap(session1: SessionModel, session2: SessionModel) -> bool:
        """Check if two sessions have time overlap on the same date"""
        # Must be same date
        if not session1.date_start or not session2.date_start:
            return False
        if session1.date_start.date() != session2.date_start.date():
            return False

        # If either session missing time info, cannot determine
        if not session1.date_start or not session1.date_end:
            return False
        if not session2.date_start or not session2.date_end:
            return False

        # Check if times overlap
        # Overlap exists if: (start1 < end2) AND (start2 < end1)
        return (session1.date_start < session2.date_end and
                session2.date_start < session1.date_end)

    @staticmethod
    def _has_travel_conflict(
        session1: SessionModel, location1: Optional[Dict],
        session2: SessionModel, location2: Optional[Dict]
    ) -> bool:
        """Check if two sessions have travel time conflict (too close at different locations)"""
        # Must be same date
        if not session1.date_start or not session2.date_start:
            return False
        if session1.date_start.date() != session2.date_start.date():
            return False

        # If either session missing time or location info, cannot determine
        if not session1.date_start or not session1.date_end:
            return False
        if not session2.date_start or not session2.date_end:
            return False
        if not location1 or not location2:
            return False

        # If same location, no travel conflict
        if location1.get("location_id") == location2.get("location_id"):
            return False

        # Check if sessions are within travel buffer time
        # Session 1 ends, then session 2 starts
        time_gap_1_to_2 = EnrollmentConflictService._calculate_time_gap(
            session1.date_end.time(), session2.date_start.time()
        )

        # Session 2 ends, then session 1 starts
        time_gap_2_to_1 = EnrollmentConflictService._calculate_time_gap(
            session2.date_end.time(), session1.date_start.time()
        )

        # Conflict if gap is less than travel buffer
        min_gap = min(time_gap_1_to_2, time_gap_2_to_1)
        return 0 <= min_gap < EnrollmentConflictService.TRAVEL_TIME_BUFFER_MINUTES

    @staticmethod
    def _calculate_time_gap(end_time: time, start_time: time) -> int:
        """Calculate time gap in minutes between two times (positive if start > end, negative otherwise)"""
        # Convert to datetime for calculation
        today = date.today()
        end_dt = datetime.combine(today, end_time)
        start_dt = datetime.combine(today, start_time)

        # Handle next-day scenario (e.g., end at 23:00, start at 01:00)
        if start_dt < end_dt:
            start_dt += timedelta(days=1)

        gap = (start_dt - end_dt).total_seconds() / 60
        return int(gap)
