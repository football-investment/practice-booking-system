"""
Tournament Browse/List API Endpoint
Students can browse and view available tournaments
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.semester_enrollment import SemesterEnrollment
from app.models.session import Session as SessionModel
from app.models.license import UserLicense
from app.schemas.tournament import TournamentWithDetails
from app.services.age_category_service import (
    get_automatic_age_category,
    get_current_season_year,
    calculate_age_at_season_start
)


router = APIRouter()


@router.get("/available", response_model=List[TournamentWithDetails])
def list_available_tournaments(
    age_group: Optional[str] = None,
    location_id: Optional[int] = None,
    campus_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List available tournaments for current player (Student role only)

    **Visibility Rules:**
    - Status: READY_FOR_ENROLLMENT or ONGOING
    - Specialization: LFA_FOOTBALL_PLAYER
    - Date: end_date >= today (not expired)
    - Age Category Filtering:
      - PRE (5-13): Can only see PRE tournaments
      - YOUTH (14-18): Can see YOUTH OR AMATEUR tournaments
      - AMATEUR (18+): Can only see AMATEUR tournaments
      - PRO (18+): Can only see PRO tournaments

    **Query Parameters:**
    - age_group: Filter by specific age category (optional)
    - location_id: Filter by location city (optional)
    - campus_id: Filter by specific campus venue (optional)
    - start_date: Filter tournaments starting after this date (optional)
    - end_date: Filter tournaments ending before this date (optional)

    **Returns:**
    - List of tournaments with:
      - Tournament details (name, date, location, cost, etc.)
      - Session/game details
      - Enrollment statistics (how many enrolled)
      - User enrollment status (is_enrolled, enrollment_status)
      - Location and campus info
      - Master instructor info
    """

    # 1. Verify student role
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can browse tournaments"
        )

    # 2. Get player's age category
    if not current_user.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth not set. Please set your date of birth in your profile."
        )

    # Calculate age at current season start (July 1)
    season_year = get_current_season_year()
    age_at_season_start = calculate_age_at_season_start(current_user.date_of_birth, season_year)
    player_age_category = get_automatic_age_category(age_at_season_start)

    if not player_age_category:
        # Player is over 18 - try to get category from their enrollment history
        recent_enrollment = db.query(SemesterEnrollment).filter(
            and_(
                SemesterEnrollment.user_id == current_user.id,
                SemesterEnrollment.age_category.isnot(None)
            )
        ).order_by(SemesterEnrollment.created_at.desc()).first()

        if recent_enrollment and recent_enrollment.age_category:
            player_age_category = recent_enrollment.age_category
        else:
            # No enrollment history - cannot determine category
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Age category not assigned. Please contact an instructor to assign your category (AMATEUR or PRO)."
            )

    # 3. Determine visible tournament age groups based on player category
    # PRE: Only PRE
    # YOUTH: YOUTH or AMATEUR (NOT PRO) - Special case!
    # AMATEUR: Only AMATEUR
    # PRO: Only PRO
    visible_age_groups = []
    if player_age_category == "PRE":
        visible_age_groups = ["PRE"]
    elif player_age_category == "YOUTH":
        visible_age_groups = ["YOUTH", "AMATEUR"]  # YOUTH can "move up" to AMATEUR
    elif player_age_category in ["AMATEUR", "PRO"]:
        visible_age_groups = [player_age_category]
    else:
        # Fallback (should not happen)
        visible_age_groups = []

    # 4. Base query: Tournaments ready for enrollment + age category filter
    query = db.query(Semester).filter(
        and_(
            Semester.code.like("TOURN-%"),
            Semester.status.in_([
                SemesterStatus.READY_FOR_ENROLLMENT,
                SemesterStatus.ONGOING
            ]),
            Semester.specialization_type == "LFA_FOOTBALL_PLAYER",
            Semester.age_group.in_(visible_age_groups),  # Age category filter
            Semester.end_date >= date.today()
        )
    )

    # 5. Apply optional filters
    if age_group:
        # Optional filter (override visibility if provided)
        if age_group not in visible_age_groups:
            # User requested age group they can't enroll in
            return []  # Empty result
        query = query.filter(Semester.age_group == age_group)

    if location_id:
        query = query.filter(Semester.location_id == location_id)

    if campus_id:
        query = query.filter(Semester.campus_id == campus_id)

    if start_date:
        query = query.filter(Semester.start_date >= start_date)

    if end_date:
        query = query.filter(Semester.end_date <= end_date)

    # 6. Eager load relationships
    query = query.options(
        joinedload(Semester.location),
        joinedload(Semester.campus),
        joinedload(Semester.sessions),
        joinedload(Semester.master_instructor)
    )

    # 7. Order by start date (soonest first)
    tournaments = query.order_by(Semester.start_date.asc()).all()

    # 8. For each tournament, calculate statistics and check enrollment
    results = []
    for tournament in tournaments:
        # Count current enrollments (active only)
        enrollment_count = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.is_active == True
        ).count()

        # Check if current user already enrolled
        user_enrollment = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.user_id == current_user.id
        ).first()

        # Serialize tournament data
        tournament_dict = {
            "id": tournament.id,
            "code": tournament.code,
            "name": tournament.name,
            "start_date": tournament.start_date.isoformat(),
            "end_date": tournament.end_date.isoformat(),
            "status": tournament.status.value,
            "age_group": tournament.age_group,
            "specialization_type": tournament.specialization_type,
            "enrollment_cost": tournament.enrollment_cost or 500,
            "location_id": tournament.location_id,
            "campus_id": tournament.campus_id,
            "master_instructor_id": tournament.master_instructor_id,
            "created_at": tournament.created_at.isoformat() if tournament.created_at else None
        }

        # Serialize sessions
        sessions_list = []
        for session in tournament.sessions:
            # Count current bookings for this session
            from app.models.booking import Booking, BookingStatus
            bookings_count = db.query(Booking).filter(
                Booking.session_id == session.id,
                Booking.status == BookingStatus.CONFIRMED
            ).count()

            sessions_list.append({
                "id": session.id,
                "date": session.date_start.date().isoformat(),
                "start_time": session.date_start.strftime("%H:%M"),
                "end_time": session.date_end.strftime("%H:%M"),
                "game_type": session.game_type,
                "capacity": session.capacity,
                "current_bookings": bookings_count
            })

        # Serialize location
        location_dict = None
        if tournament.location:
            location_dict = {
                "id": tournament.location.id,
                "city": tournament.location.city,
                "address": tournament.location.address
            }

        # Serialize campus
        campus_dict = None
        if tournament.campus:
            campus_dict = {
                "id": tournament.campus.id,
                "name": tournament.campus.name
            }

        # Serialize instructor
        instructor_dict = None
        if tournament.master_instructor:
            instructor_dict = {
                "id": tournament.master_instructor.id,
                "name": tournament.master_instructor.name,
                "email": tournament.master_instructor.email
            }

        # Build response
        results.append({
            "tournament": tournament_dict,
            "enrollment_count": enrollment_count,
            "is_enrolled": user_enrollment is not None,
            "user_enrollment_status": user_enrollment.request_status.value if user_enrollment else None,
            "sessions": sessions_list,
            "location": location_dict,
            "campus": campus_dict,
            "instructor": instructor_dict
        })

    return results

