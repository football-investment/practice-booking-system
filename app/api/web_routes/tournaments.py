"""
Tournament web routes — cookie auth HTML frontend
Mirrors Streamlit Tournament_Monitor / Tournament_Manager flow.

Student routes:
    GET  /tournaments              — browse ENROLLMENT_OPEN tournaments
    POST /tournaments/{id}/enroll  — enroll (auto-approved, deducts credits)
    POST /tournaments/{id}/unenroll — withdraw (50 % refund)

Instructor routes:
    GET  /instructor/tournaments   — view assigned tournaments + participants

Admin routes:
    GET  /admin/tournaments                — all tournaments list + create form
    POST /admin/tournaments                — create new tournament
    POST /admin/tournaments/{id}/start     — ENROLLMENT_CLOSED → IN_PROGRESS
    POST /admin/tournaments/{id}/cancel    — any → CANCELLED
    POST /admin/tournaments/{id}/delete    — permanent delete
    POST /admin/tournaments/{id}/rollback  — IN_PROGRESS → ENROLLMENT_CLOSED (stuck recovery)
"""
from datetime import datetime, date
from pathlib import Path
import uuid

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_, update as sql_update
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.booking import Booking, BookingStatus
from ...models.campus import Campus
from ...models.credit_transaction import CreditTransaction
from ...models.game_preset import GamePreset
from ...models.license import UserLicense
from ...models.location import Location
from ...models.semester import Semester, SemesterStatus
from ...models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from ...models.session import Session as SessionModel
from ...models.instructor_assignment import (
    InstructorAssignment,
    InstructorAssignmentRequest,
    InstructorAvailabilityWindow,
    AssignmentRequestStatus,
    LocationMasterInstructor,
    MasterOfferStatus,
)
from ...models.tournament_type import TournamentType
from ...models.user import User, UserRole
from ...services.age_category_service import (
    calculate_age_at_season_start,
    get_automatic_age_category,
    get_current_season_year,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_player_age_category(user: User) -> str:
    """Derive AMATEUR/PRE/YOUTH/PRO age category from user DOB. Defaults to AMATEUR."""
    if not user.date_of_birth:
        return "AMATEUR"
    season_year = get_current_season_year()
    age_at = calculate_age_at_season_start(user.date_of_birth, season_year)
    return get_automatic_age_category(age_at) or "AMATEUR"


# ── Student: browse + enroll ───────────────────────────────────────────────────

@router.get("/tournaments", response_class=HTMLResponse)
async def tournaments_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Browse ENROLLMENT_OPEN / IN_PROGRESS tournaments available to the student."""
    tournaments = (
        db.query(Semester)
        .filter(
            and_(
                Semester.code.like("TOURN-%"),
                Semester.tournament_status.in_(["ENROLLMENT_OPEN", "IN_PROGRESS"]),
                Semester.specialization_type == "LFA_FOOTBALL_PLAYER",
                Semester.status != SemesterStatus.CANCELLED,
                Semester.end_date >= date.today(),
            )
        )
        .order_by(Semester.start_date.asc())
        .all()
    )

    tournament_data = []
    for t in tournaments:
        enrollment_count = (
            db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.semester_id == t.id,
                SemesterEnrollment.is_active == True,
            )
            .count()
        )
        user_enrollment = (
            db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.semester_id == t.id,
                SemesterEnrollment.user_id == user.id,
                SemesterEnrollment.is_active == True,
            )
            .first()
        )
        # Instructor info
        instructor = None
        if t.master_instructor_id:
            instructor = db.query(User).filter(User.id == t.master_instructor_id).first()

        tournament_data.append({
            "tournament": t,
            "enrollment_count": enrollment_count,
            "max_players": t.max_players or 999,
            "is_enrolled": user_enrollment is not None,
            "enrollment_status": user_enrollment.request_status.value if user_enrollment else None,
            "instructor": instructor,
        })

    return templates.TemplateResponse(
        "tournaments.html",
        {
            "request": request,
            "user": user,
            "tournaments": tournament_data,
            "flash": request.query_params.get("flash"),
            "flash_type": request.query_params.get("flash_type", "info"),
        },
    )


@router.post("/tournaments/{tournament_id}/enroll", response_class=HTMLResponse)
async def tournament_enroll(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Enroll current student in the given tournament (auto-approved, deducts credits)."""

    def _err(msg: str):
        return RedirectResponse(
            url=f"/tournaments?flash={msg}&flash_type=error", status_code=303
        )

    # 1. Fetch tournament
    tournament = db.query(Semester).filter(
        Semester.id == tournament_id, Semester.status != SemesterStatus.CANCELLED
    ).first()
    if not tournament:
        return _err("Tournament+not+found")

    # 2. Status check
    if tournament.tournament_status not in ("ENROLLMENT_OPEN", "IN_PROGRESS"):
        return _err("Tournament+not+open+for+enrollment")

    # 3. Student only
    if user.role != UserRole.STUDENT:
        return _err("Only+students+can+enroll")

    # 4. LFA_FOOTBALL_PLAYER license required
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.is_active == True,
    ).first()
    if not license:
        return _err("LFA+Football+Player+license+required")

    # 5. Not already enrolled
    existing = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.user_id == user.id,
        SemesterEnrollment.is_active == True,
    ).first()
    if existing:
        return RedirectResponse(
            url="/tournaments?flash=Already+enrolled&flash_type=info", status_code=303
        )

    # 6. Credits check
    cost = tournament.enrollment_cost if tournament.enrollment_cost is not None else 500
    if user.credit_balance < cost:
        return _err(f"Insufficient+credits+(need+{cost}%2C+have+{user.credit_balance})")

    # 7. Capacity check
    enrolled_count = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.is_active == True,
        SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
    ).count()
    max_p = tournament.max_players if tournament.max_players else 999
    if enrolled_count >= max_p:
        return _err("Tournament+is+full")

    # 8. Create enrollment (auto-approved)
    age_category = _get_player_age_category(user)
    enrollment = SemesterEnrollment(
        user_id=user.id,
        semester_id=tournament_id,
        user_license_id=license.id,
        age_category=age_category,
        request_status=EnrollmentStatus.APPROVED,
        approved_at=datetime.utcnow(),
        approved_by=user.id,
        payment_verified=True,
        is_active=True,
        enrolled_at=datetime.utcnow(),
        requested_at=datetime.utcnow(),
    )
    db.add(enrollment)
    db.flush()

    # 9. Atomic credit deduction
    result = db.execute(
        sql_update(User)
        .where(User.id == user.id, User.credit_balance >= cost)
        .values(credit_balance=User.credit_balance - cost)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        db.rollback()
        return _err("Insufficient+credits+(concurrent+update)")
    db.refresh(user)

    # 10. Credit transaction record
    db.add(CreditTransaction(
        user_license_id=license.id,
        transaction_type="TOURNAMENT_ENROLLMENT",
        amount=-cost,
        balance_after=user.credit_balance,
        description=f"Tournament enrollment: {tournament.name} ({tournament.code})",
        semester_id=tournament_id,
        enrollment_id=enrollment.id,
        idempotency_key=str(uuid.uuid4()),
    ))

    # 11. Auto-book existing tournament sessions
    sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).all()
    for s in sessions:
        db.add(Booking(
            user_id=user.id,
            session_id=s.id,
            enrollment_id=enrollment.id,
            status=BookingStatus.CONFIRMED,
            created_at=datetime.utcnow(),
        ))

    db.commit()

    tournament_name = tournament.name.replace(" ", "+")
    return RedirectResponse(
        url=f"/tournaments?flash=Successfully+enrolled+in+{tournament_name}&flash_type=success",
        status_code=303,
    )


@router.post("/tournaments/{tournament_id}/unenroll", response_class=HTMLResponse)
async def tournament_unenroll(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Withdraw student from tournament (50 % refund)."""
    enrollment = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == user.id,
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.is_active == True,
    ).first()
    if not enrollment:
        return RedirectResponse(
            url="/tournaments?flash=No+active+enrollment+found&flash_type=error",
            status_code=303,
        )

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    cost = (tournament.enrollment_cost if tournament and tournament.enrollment_cost else 500)
    refund = cost // 2

    enrollment.is_active = False
    enrollment.request_status = EnrollmentStatus.WITHDRAWN
    db.add(enrollment)

    db.execute(
        sql_update(User)
        .where(User.id == user.id)
        .values(credit_balance=User.credit_balance + refund)
        .execution_options(synchronize_session=False)
    )
    db.refresh(user)

    db.add(CreditTransaction(
        user_license_id=enrollment.user_license_id,
        transaction_type="TOURNAMENT_UNENROLL_REFUND",
        amount=refund,
        balance_after=user.credit_balance,
        description=f"Tournament unenrollment refund (50%): {tournament.name if tournament else tournament_id}",
        semester_id=tournament_id,
        enrollment_id=enrollment.id,
        idempotency_key=str(uuid.uuid4()),
    ))

    # Remove linked bookings
    db.query(Booking).filter(
        Booking.enrollment_id == enrollment.id,
        Booking.user_id == user.id,
    ).delete(synchronize_session=False)

    db.commit()

    return RedirectResponse(
        url=f"/tournaments?flash=Unenrolled.+{refund}+credits+refunded.&flash_type=info",
        status_code=303,
    )


# ── Instructor: manage assigned tournaments ────────────────────────────────────

@router.get("/instructor/tournaments", response_class=HTMLResponse)
async def instructor_tournaments(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Instructor/Admin view: list assigned tournaments with participant details."""
    if user.role not in (UserRole.INSTRUCTOR, UserRole.ADMIN):
        return RedirectResponse(url="/dashboard", status_code=303)

    tournaments = (
        db.query(Semester)
        .filter(
            and_(
                Semester.code.like("TOURN-%"),
                Semester.master_instructor_id == user.id,
                Semester.status != SemesterStatus.CANCELLED,
            )
        )
        .order_by(Semester.start_date.asc())
        .all()
    )

    tournament_data = []
    for t in tournaments:
        enrollments = (
            db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.semester_id == t.id,
                SemesterEnrollment.is_active == True,
            )
            .all()
        )

        participants = []
        for enr in enrollments:
            student = db.query(User).filter(User.id == enr.user_id).first()
            if student:
                participants.append({
                    "name": student.name,
                    "email": student.email,
                    "age_category": enr.age_category or "—",
                    "enrolled_at": enr.enrolled_at,
                    "status": enr.request_status.value,
                })

        tournament_data.append({
            "tournament": t,
            "participants": participants,
            "enrollment_count": len(participants),
            "max_players": t.max_players or "—",
        })

    return templates.TemplateResponse(
        "instructor/tournaments.html",
        {
            "request": request,
            "user": user,
            "tournaments": tournament_data,
            "flash": request.query_params.get("flash"),
            "flash_type": request.query_params.get("flash_type", "info"),
        },
    )


# ── Admin: tournament management ───────────────────────────────────────────────

def _admin_only(user: User):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/admin/tournaments", response_class=HTMLResponse)
async def admin_tournaments_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: list all tournaments (all statuses) + create form."""
    _admin_only(user)

    tournaments = (
        db.query(Semester)
        .filter(
            or_(
                Semester.code.like("TOURN-%"),
                Semester.code.like("OPS-%"),
            )
        )
        .order_by(Semester.start_date.desc())
        .all()
    )

    tournament_info = []
    for t in tournaments:
        enroll_count = (
            db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.semester_id == t.id,
                SemesterEnrollment.is_active == True,
            )
            .count()
        )
        session_count = (
            db.query(SessionModel)
            .filter(SessionModel.semester_id == t.id)
            .count()
        )
        instructor = None
        if t.master_instructor_id:
            instructor = db.query(User).filter(User.id == t.master_instructor_id).first()
        tournament_info.append({
            "tournament": t,
            "enrollment_count": enroll_count,
            "session_count": session_count,
            "instructor": instructor,
        })

    locations = db.query(Location).filter(Location.is_active == True).all()
    campuses = db.query(Campus).filter(Campus.is_active == True).all()

    return templates.TemplateResponse(
        "admin/tournaments.html",
        {
            "request": request,
            "user": user,
            "tournament_info": tournament_info,
            "locations": locations,
            "campuses": campuses,
            "flash": request.query_params.get("flash"),
            "flash_type": request.query_params.get("flash_type", "success"),
            "error": request.query_params.get("error"),
            "active_tab": request.query_params.get("tab", "list"),
        },
    )


@router.post("/admin/tournaments", response_class=RedirectResponse)
async def admin_create_tournament(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
    name: str = Form(...),
    code: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    age_group: str = Form("AMATEUR"),
    enrollment_cost: int = Form(0),
    location_id: str = Form(""),
    campus_id: str = Form(""),
    assignment_type: str = Form("OPEN_ASSIGNMENT"),
):
    """Admin: create a new tournament."""
    _admin_only(user)

    code = code.strip().upper()
    if not code.startswith("TOURN-") and not code.startswith("OPS-"):
        code = f"TOURN-{code}"

    if db.query(Semester).filter(Semester.code == code).first():
        return RedirectResponse(
            url=f"/admin/tournaments?error=Code+{code}+already+exists&tab=create",
            status_code=303,
        )

    t = Semester(
        code=code,
        name=name.strip(),
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        status=SemesterStatus.DRAFT,
        tournament_status="DRAFT",
        specialization_type="LFA_FOOTBALL_PLAYER",
        age_group=age_group,
        enrollment_cost=enrollment_cost,
        location_id=int(location_id) if location_id.strip() else None,
        campus_id=int(campus_id) if campus_id.strip() else None,
    )
    db.add(t)
    db.commit()

    return RedirectResponse(
        url=f"/admin/tournaments?flash=Tournament+{code}+created+successfully",
        status_code=303,
    )


@router.post("/admin/tournaments/{tournament_id}/start", response_class=RedirectResponse)
async def admin_start_tournament(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: advance ENROLLMENT_CLOSED → IN_PROGRESS."""
    _admin_only(user)

    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        return RedirectResponse(url="/admin/tournaments?error=Tournament+not+found", status_code=303)
    if t.tournament_status != "ENROLLMENT_CLOSED":
        return RedirectResponse(
            url=f"/admin/tournaments?error=Tournament+must+be+ENROLLMENT_CLOSED+to+start+(current:+{t.tournament_status})",
            status_code=303,
        )

    t.tournament_status = "IN_PROGRESS"
    t.status = SemesterStatus.ONGOING
    db.commit()

    return RedirectResponse(
        url=f"/admin/tournaments?flash=Tournament+{t.code}+started+(IN_PROGRESS)",
        status_code=303,
    )


@router.post("/admin/tournaments/{tournament_id}/cancel", response_class=RedirectResponse)
async def admin_cancel_tournament(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: cancel tournament."""
    _admin_only(user)

    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        return RedirectResponse(url="/admin/tournaments?error=Tournament+not+found", status_code=303)
    if t.tournament_status in ("COMPLETED", "CANCELLED"):
        return RedirectResponse(
            url=f"/admin/tournaments?error=Cannot+cancel+{t.tournament_status}+tournament",
            status_code=303,
        )

    t.tournament_status = "CANCELLED"
    t.status = SemesterStatus.CANCELLED
    db.commit()

    return RedirectResponse(
        url=f"/admin/tournaments?flash=Tournament+{t.code}+cancelled",
        status_code=303,
    )


@router.post("/admin/tournaments/{tournament_id}/delete", response_class=RedirectResponse)
async def admin_delete_tournament(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: permanently delete tournament."""
    _admin_only(user)

    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        return RedirectResponse(url="/admin/tournaments?error=Tournament+not+found", status_code=303)

    code = t.code
    db.delete(t)
    db.commit()

    return RedirectResponse(
        url=f"/admin/tournaments?flash=Tournament+{code}+permanently+deleted",
        status_code=303,
    )


@router.post("/admin/tournaments/{tournament_id}/rollback", response_class=RedirectResponse)
async def admin_rollback_tournament(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: rollback stuck IN_PROGRESS → ENROLLMENT_CLOSED for re-generation."""
    _admin_only(user)

    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        return RedirectResponse(url="/admin/tournaments?error=Tournament+not+found", status_code=303)
    if t.tournament_status != "IN_PROGRESS":
        return RedirectResponse(
            url=f"/admin/tournaments?error=Rollback+only+available+for+IN_PROGRESS+tournaments",
            status_code=303,
        )

    t.tournament_status = "ENROLLMENT_CLOSED"
    t.status = SemesterStatus.READY_FOR_ENROLLMENT
    db.commit()

    return RedirectResponse(
        url=f"/admin/tournaments?flash=Tournament+{t.code}+rolled+back+to+ENROLLMENT_CLOSED",
        status_code=303,
    )


# ── Tournament Edit Page ────────────────────────────────────────────────────────

@router.get("/admin/tournaments/{tournament_id}/edit", response_class=HTMLResponse)
async def admin_tournament_edit_page(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: tournament edit page — all lifecycle management in one place."""
    _admin_only(user)

    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        return RedirectResponse(url="/admin/tournaments?error=Tournament+not+found", status_code=303)

    # Enrollments with user details
    enrollments = (
        db.query(SemesterEnrollment)
        .filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
        )
        .all()
    )
    enrolled_user_ids = [e.user_id for e in enrollments]
    enrolled_users = {}
    if enrolled_user_ids:
        for u in db.query(User).filter(User.id.in_(enrolled_user_ids)).all():
            enrolled_users[u.id] = u

    # Sessions generated
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tournament_id)
        .order_by(SessionModel.date_start)
        .limit(10)
        .all()
    )
    session_count = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tournament_id)
        .count()
    )

    # Reference data for dropdowns
    game_presets = db.query(GamePreset).filter(GamePreset.is_active == True).all()
    tournament_types = db.query(TournamentType).all()
    campuses = db.query(Campus).filter(Campus.is_active == True).all()
    locations = db.query(Location).filter(Location.is_active == True).all()

    # Schedule config (from tournament_config_obj)
    cfg = t.tournament_config_obj
    schedule = {
        "match_duration_minutes": cfg.match_duration_minutes if cfg else None,
        "break_duration_minutes": cfg.break_duration_minutes if cfg else None,
        "parallel_fields": cfg.parallel_fields if cfg else 1,
    }

    # Reward config summary
    reward_cfg = t.reward_config  # property → dict or None

    # Game preset info (for session gen guard)
    game_cfg = t.game_config_obj
    preset = None
    preset_min_players = None
    if game_cfg and game_cfg.game_preset_id:
        preset = db.query(GamePreset).filter(GamePreset.id == game_cfg.game_preset_id).first()
        if preset:
            preset_min_players = preset.game_config.get("metadata", {}).get("min_players")

    checked_in_count = sum(
        1 for e in enrollments if e.tournament_checked_in_at is not None
    )

    return templates.TemplateResponse(
        "admin/tournament_edit.html",
        {
            "request": request,
            "user": user,
            "t": t,
            "cfg": cfg,
            "schedule": schedule,
            "reward_cfg": reward_cfg,
            "game_cfg": game_cfg,
            "preset": preset,
            "preset_min_players": preset_min_players,
            "enrollments": enrollments,
            "enrolled_users": enrolled_users,
            "checked_in_count": checked_in_count,
            "sessions": sessions,
            "session_count": session_count,
            "game_presets": game_presets,
            "tournament_types": tournament_types,
            "campuses": campuses,
            "locations": locations,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


# ── Instructor Management Pages ─────────────────────────────────────────────────

@router.get("/admin/instructors", response_class=HTMLResponse)
async def admin_instructors_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
) -> HTMLResponse:
    """Admin instructor list — all users with role=INSTRUCTOR."""
    _admin_only(user)

    instructors = (
        db.query(User)
        .filter(User.role == UserRole.INSTRUCTOR)
        .order_by(User.name)
        .all()
    )

    # Per-instructor counts (batch — avoid N+1)
    instructor_ids = [i.id for i in instructors]

    license_counts: dict[int, int] = {}
    active_assignment_counts: dict[int, int] = {}
    master_location_counts: dict[int, int] = {}

    if instructor_ids:
        from sqlalchemy import func as sqlfunc
        for row in (
            db.query(UserLicense.user_id, sqlfunc.count(UserLicense.id))
            .filter(UserLicense.user_id.in_(instructor_ids), UserLicense.is_active == True)
            .group_by(UserLicense.user_id)
            .all()
        ):
            license_counts[row[0]] = row[1]

        for row in (
            db.query(InstructorAssignment.instructor_id, sqlfunc.count(InstructorAssignment.id))
            .filter(
                InstructorAssignment.instructor_id.in_(instructor_ids),
                InstructorAssignment.is_active == True,
            )
            .group_by(InstructorAssignment.instructor_id)
            .all()
        ):
            active_assignment_counts[row[0]] = row[1]

        for row in (
            db.query(LocationMasterInstructor.instructor_id, sqlfunc.count(LocationMasterInstructor.id))
            .filter(
                LocationMasterInstructor.instructor_id.in_(instructor_ids),
                LocationMasterInstructor.is_active == True,
            )
            .group_by(LocationMasterInstructor.instructor_id)
            .all()
        ):
            master_location_counts[row[0]] = row[1]

    stats = {
        "total": len(instructors),
        "active": sum(1 for i in instructors if i.is_active),
        "with_assignments": sum(1 for i in instructors if active_assignment_counts.get(i.id, 0) > 0),
        "masters": sum(1 for i in instructors if master_location_counts.get(i.id, 0) > 0),
    }

    return templates.TemplateResponse(
        request,
        "admin/instructors.html",
        {
            "instructors": instructors,
            "license_counts": license_counts,
            "active_assignment_counts": active_assignment_counts,
            "master_location_counts": master_location_counts,
            "stats": stats,
        },
    )


@router.get("/admin/instructors/{instructor_id}", response_class=HTMLResponse)
async def admin_instructor_detail_page(
    instructor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
) -> HTMLResponse:
    """Admin instructor detail — licenses, assignments, availability, requests."""
    _admin_only(user)

    instructor = db.query(User).filter(
        User.id == instructor_id, User.role == UserRole.INSTRUCTOR
    ).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    # Licenses
    licenses = (
        db.query(UserLicense)
        .filter(UserLicense.user_id == instructor_id)
        .order_by(UserLicense.is_active.desc(), UserLicense.started_at.desc())
        .all()
    )

    # Active assignments
    assignments = (
        db.query(InstructorAssignment)
        .filter(
            InstructorAssignment.instructor_id == instructor_id,
            InstructorAssignment.is_active == True,
        )
        .order_by(InstructorAssignment.year.desc(), InstructorAssignment.time_period_start)
        .all()
    )
    # Enrich with location names
    assignment_locations: dict[int, str] = {}
    loc_ids = {a.location_id for a in assignments}
    if loc_ids:
        for loc in db.query(Location).filter(Location.id.in_(loc_ids)).all():
            assignment_locations[loc.id] = loc.name

    # Availability windows (last 2 years)
    from datetime import date as _date
    current_year = _date.today().year
    availability = (
        db.query(InstructorAvailabilityWindow)
        .filter(
            InstructorAvailabilityWindow.instructor_id == instructor_id,
            InstructorAvailabilityWindow.year >= current_year - 1,
        )
        .order_by(InstructorAvailabilityWindow.year.desc(), InstructorAvailabilityWindow.time_period)
        .all()
    )

    # Assignment requests (last 20, all statuses)
    requests = (
        db.query(InstructorAssignmentRequest)
        .filter(InstructorAssignmentRequest.instructor_id == instructor_id)
        .order_by(InstructorAssignmentRequest.created_at.desc())
        .limit(20)
        .all()
    )
    # Enrich requests with semester names
    sem_ids = {r.semester_id for r in requests}
    semester_names: dict[int, str] = {}
    if sem_ids:
        for sem in db.query(Semester).filter(Semester.id.in_(sem_ids)).all():
            semester_names[sem.id] = sem.name

    # Master locations
    master_contracts = (
        db.query(LocationMasterInstructor)
        .filter(LocationMasterInstructor.instructor_id == instructor_id)
        .order_by(LocationMasterInstructor.is_active.desc(), LocationMasterInstructor.created_at.desc())
        .all()
    )
    master_loc_ids = {m.location_id for m in master_contracts}
    master_location_names: dict[int, str] = {}
    if master_loc_ids:
        for loc in db.query(Location).filter(Location.id.in_(master_loc_ids)).all():
            master_location_names[loc.id] = loc.name

    return templates.TemplateResponse(
        request,
        "admin/instructor_detail.html",
        {
            "instructor": instructor,
            "licenses": licenses,
            "assignments": assignments,
            "assignment_locations": assignment_locations,
            "availability": availability,
            "requests": requests,
            "semester_names": semester_names,
            "master_contracts": master_contracts,
            "master_location_names": master_location_names,
            "AssignmentRequestStatus": AssignmentRequestStatus,
            "MasterOfferStatus": MasterOfferStatus,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )
