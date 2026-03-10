"""
Admin panel routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone, date

import re
from collections import defaultdict

from sqlalchemy.orm import joinedload

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User, UserRole
from ...models.semester import Semester
from ...models.license import UserLicense
from ...models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from ...models.specialization import SpecializationType
from ...models.invoice_request import InvoiceRequest
from ...models.coupon import Coupon
from ...models.invitation_code import InvitationCode
from ...models.session import Session as SessionModel
from ...models.booking import Booking
from ...services.audit_service import AuditService
from ...models.audit_log import AuditAction
from ...services.tournament.session_generation import get_tournament_venue

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: User management page"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all users
    all_users = db.query(User).order_by(User.id).all()
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": user,
            "all_users": all_users
        }
    )


@router.get("/admin/semesters", response_class=HTMLResponse)
async def admin_semesters_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Semester management page"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all semesters
    semesters = db.query(Semester).order_by(Semester.start_date.desc()).all()
    
    return templates.TemplateResponse(
        "admin/semesters.html",
        {
            "request": request,
            "user": user,
            "semesters": semesters
        }
    )


@router.get("/admin/enrollments", response_class=HTMLResponse)
async def admin_enrollments_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Unified Semester Enrollment Management page (replaces /admin/payments)"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all semesters (for dropdown)
    semesters = db.query(Semester).order_by(Semester.start_date.desc()).all()

    # Get all students with their licenses
    students = db.query(User).filter(User.role == UserRole.STUDENT).order_by(User.name).all()

    # Attach user licenses to each student
    for student in students:
        student.all_licenses = db.query(UserLicense).filter(
            UserLicense.user_id == student.id
        ).all()
        # For specialization management section (moved from /admin/payments)
        student.active_specializations = student.all_licenses

    # Get ALL truly active semesters (running TODAY - between start_date and end_date)
    today = date.today()

    active_semesters = db.query(Semester).filter(
        Semester.is_active == True,
        Semester.start_date <= today,
        Semester.end_date >= today
    ).order_by(Semester.code, Semester.start_date.desc()).all()

    # Add specialization_type and extract location from code
    for semester in active_semesters:
        # Extract specialization and location from code
        # Examples:
        #   "LFA_PLAYER_PRE_2025_JAN_BUDA" -> spec: "LFA_PLAYER_PRE", location: "Buda"
        #   "LFA_PLAYER_PRO_2025-26_PEST" -> spec: "LFA_PLAYER_PRO", location: "Pest"
        #   "GANCUJU_WINTER_2025_BUDAPEST" -> spec: "GANCUJU_PLAYER", location: "Budapest"
        #   "INTERNSHIP_FALL_2025_BUDAPEST" -> spec: "INTERNSHIP", location: "Budapest"

        code = semester.code

        # Extract location suffix (BUDA, PEST, BUDAPEST, city names)
        location_match = re.search(r'_(BUDA|PEST|BUDAPEST|DEBRECEN|SZEGED|MISKOLC|GYOR)$', code, re.IGNORECASE)
        if location_match:
            # Remove location suffix for specialization extraction
            code_without_location = code[:location_match.start()]
        else:
            code_without_location = code

        # Remove year patterns (4 digits, or YYYY-YY format, or Q1/Q2/Q3/Q4, or month names)
        code_clean = re.sub(r'_\d{4}(-\d{2})?(_[A-Z]{3,6})?$', '', code_without_location)
        code_clean = re.sub(r'_\d{4}_Q\d$', '', code_clean)

        # Special case: GANCUJU should become GANCUJU_PLAYER
        if code_clean.startswith('GANCUJU'):
            semester.specialization_type = 'GANCUJU_PLAYER'
        else:
            semester.specialization_type = code_clean if code_clean else None

    # Get ALL enrollments for ALL active semesters
    all_enrollments = []
    if active_semesters:
        semester_ids = [s.id for s in active_semesters]
        all_enrollments = (
            db.query(SemesterEnrollment)
            .options(
                joinedload(SemesterEnrollment.user),
                joinedload(SemesterEnrollment.user_license),
                joinedload(SemesterEnrollment.semester)
            )
            .filter(SemesterEnrollment.semester_id.in_(semester_ids))
            .order_by(SemesterEnrollment.requested_at.desc())
            .all()
        )

    # Group enrollments by specialization + location
    specialization_groups = {}
    for spec_type in SpecializationType:
        spec_enrollments = [e for e in all_enrollments if e.user_license.specialization_type == spec_type.value]

        # Get all active semesters for this specialization type
        spec_semesters = [s for s in active_semesters if s.specialization_type == spec_type.value]

        # Group by venue within this specialization (using helper function)
        location_groups = defaultdict(list)

        # Eager load location relationships for helper function
        for semester in spec_semesters:
            db.refresh(semester, ['location', 'campus'])

        # First, add enrollments to their locations
        for enrollment in spec_enrollments:
            # Get venue using helper function with fallback chain
            db.refresh(enrollment.semester, ['location', 'campus'])
            location_key = get_tournament_venue(enrollment.semester)
            location_groups[location_key].append(enrollment)

        # Then, ensure EVERY active semester location has a group (even if empty)
        for semester in spec_semesters:
            location_key = get_tournament_venue(semester)
            if location_key not in location_groups:
                location_groups[location_key] = []

        # Create a group for each location
        spec_location_groups = {}
        for location_venue, enrollments in location_groups.items():
            # Separate pending and active
            pending = [e for e in enrollments if e.request_status == EnrollmentStatus.PENDING]
            active = [e for e in enrollments if e.request_status != EnrollmentStatus.PENDING]

            spec_location_groups[location_venue] = {
                'pending': pending,
                'active': active,
                'total_count': len(enrollments),
                'location_venue': location_venue
            }

        specialization_groups[spec_type.value] = spec_location_groups

    # 💳 NEW: Get all UserLicenses that DON'T have any SemesterEnrollment yet
    # These are "newcomers" who selected specializations but haven't enrolled yet
    # Admin needs to see these to verify payment BEFORE student can request enrollment
    enrollment_license_ids = [e.user_license_id for e in all_enrollments]

    newcomer_licenses = (
        db.query(UserLicense)
        .options(joinedload(UserLicense.user))
        .filter(
            UserLicense.id.notin_(enrollment_license_ids) if enrollment_license_ids else True,
            UserLicense.payment_reference_code.isnot(None)
        )
        .order_by(UserLicense.started_at.desc())
        .all()
    )

    # Group newcomer licenses by specialization
    newcomer_groups = {}
    for spec_type in SpecializationType:
        newcomer_groups[spec_type.value] = [
            lic for lic in newcomer_licenses
            if lic.specialization_type == spec_type.value
        ]

    print(f"📋 Admin Enrollments: {len(all_enrollments)} enrollments, {len(newcomer_licenses)} newcomer licenses")

    return templates.TemplateResponse(
        "admin/enrollments.html",
        {
            "request": request,
            "user": user,
            "semesters": semesters,
            "students": students,
            "active_semesters": active_semesters,  # CHANGED: Multiple active semesters
            "specialization_groups": specialization_groups,  # NEW: Grouped by spec
            "newcomer_groups": newcomer_groups,  # NEW: Licenses awaiting first payment verification
            "SpecializationType": SpecializationType  # For template iteration
        }
    )


@router.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Payment Management page (invoice requests + license payment verification)"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all invoice requests (ordered by most recent first)
    invoice_requests = (
        db.query(InvoiceRequest)
        .options(joinedload(InvoiceRequest.user))
        .order_by(InvoiceRequest.created_at.desc())
        .all()
    )

    # Get all UserLicenses that DON'T have any SemesterEnrollment yet
    # These are "newcomers" who selected specializations but haven't enrolled yet
    all_enrollments = db.query(SemesterEnrollment).all()
    enrollment_license_ids = [e.user_license_id for e in all_enrollments]

    newcomer_licenses = (
        db.query(UserLicense)
        .options(joinedload(UserLicense.user))
        .filter(
            UserLicense.id.notin_(enrollment_license_ids) if enrollment_license_ids else True,
            UserLicense.payment_reference_code.isnot(None)
        )
        .order_by(UserLicense.started_at.desc())
        .all()
    )

    # Group newcomer licenses by specialization
    newcomer_groups = {}
    for spec_type in SpecializationType:
        newcomer_groups[spec_type.value] = [
            lic for lic in newcomer_licenses
            if lic.specialization_type == spec_type.value
        ]

    print(f"💳 Admin Payments: {len(invoice_requests)} invoice requests, {len(newcomer_licenses)} newcomer licenses")

    return templates.TemplateResponse(
        "admin/payments.html",
        {
            "request": request,
            "user": user,
            "invoice_requests": invoice_requests,
            "newcomer_groups": newcomer_groups,
            "SpecializationType": SpecializationType
        }
    )


@router.get("/admin/coupons", response_class=HTMLResponse)
async def admin_coupons_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Coupon Management page"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all coupons (ordered by creation date)
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()

    # Add validity status
    for coupon in coupons:
        coupon.is_currently_valid = coupon.is_valid()

    print(f"🎟️ Admin Coupons: {len(coupons)} coupons")

    return templates.TemplateResponse(
        "admin/coupons.html",
        {
            "request": request,
            "user": user,
            "coupons": coupons,
            "today": datetime.now(timezone.utc)
        }
    )


@router.get("/admin/invitation-codes", response_class=HTMLResponse)
async def admin_invitation_codes_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Partner Invitation Codes Management page"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all invitation codes (ordered by creation date)
    codes = db.query(InvitationCode).order_by(InvitationCode.created_at.desc()).all()

    # Enrich with user names
    for code in codes:
        if code.used_by_user_id:
            used_by_user = db.query(User).filter(User.id == code.used_by_user_id).first()
            code.used_by_name = used_by_user.name if used_by_user else None
        else:
            code.used_by_name = None

        if code.created_by_admin_id:
            admin = db.query(User).filter(User.id == code.created_by_admin_id).first()
            code.created_by_name = admin.name if admin else None
        else:
            code.created_by_name = None

    print(f"🎁 Admin Invitation Codes: {len(codes)} codes")

    return templates.TemplateResponse(
        "admin/invitation_codes.html",
        {
            "request": request,
            "user": user,
            "codes": codes,
            "now": datetime.now(timezone.utc)
        }
    )


# ============================================================================
# ADMIN USER CRUD
# ============================================================================

@router.post("/admin/users/{user_id}/toggle-status")
async def admin_toggle_user_status(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Toggle a user's is_active status"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety: admin cannot deactivate themselves
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot toggle your own account status")

    target.is_active = not target.is_active
    db.commit()
    print(f"Admin {user.email} toggled user {target.email} → is_active={target.is_active}")
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def admin_edit_user_page(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Edit user form"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        "admin/user_edit.html",
        {"request": request, "user": user, "target": target, "UserRole": UserRole}
    )


@router.post("/admin/users/{user_id}/edit")
async def admin_edit_user_submit(
    user_id: int,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Save user edits"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate role
    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    # Check email uniqueness (if changed)
    new_email = email.lower().strip()
    if new_email != target.email:
        existing = db.query(User).filter(User.email == new_email).first()
        if existing:
            return templates.TemplateResponse(
                "admin/user_edit.html",
                {
                    "request": request, "user": user, "target": target,
                    "UserRole": UserRole,
                    "error": f"Email {new_email} is already in use."
                }
            )

    target.name = name.strip()
    target.email = new_email
    target.role = new_role
    db.commit()
    print(f"Admin {user.email} edited user {target.email}: name={target.name}, role={target.role}")
    return RedirectResponse(url="/admin/users", status_code=303)


# ============================================================================
# ADMIN SEMESTER CRUD
# ============================================================================

@router.get("/admin/semesters/new", response_class=HTMLResponse)
async def admin_new_semester_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Create semester form"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR, User.is_active == True).all()
    return templates.TemplateResponse(
        "admin/semester_new.html",
        {
            "request": request, "user": user,
            "instructors": instructors,
            "today": date.today().isoformat()
        }
    )


@router.post("/admin/semesters/new")
async def admin_new_semester_submit(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    enrollment_cost: int = Form(500),
    specialization_type: str = Form(""),
    master_instructor_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Create new semester"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR, User.is_active == True).all()

    def form_error(msg: str):
        return templates.TemplateResponse(
            "admin/semester_new.html",
            {
                "request": request, "user": user,
                "error": msg, "instructors": instructors,
                "today": date.today().isoformat(),
                "form": {
                    "code": code, "name": name, "start_date": start_date,
                    "end_date": end_date, "enrollment_cost": enrollment_cost,
                    "specialization_type": specialization_type
                }
            }
        )

    # Validate dates
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return form_error("Invalid date format.")

    if ed <= sd:
        return form_error("End date must be after start date.")

    # Check code uniqueness
    existing = db.query(Semester).filter(Semester.code == code.strip()).first()
    if existing:
        return form_error(f"Semester code '{code}' already exists.")

    instructor_id = int(master_instructor_id) if master_instructor_id.strip() else None

    new_sem = Semester(
        code=code.strip(),
        name=name.strip(),
        start_date=sd,
        end_date=ed,
        enrollment_cost=enrollment_cost,
        specialization_type=specialization_type.strip() or None,
        master_instructor_id=instructor_id,
        is_active=True,
    )
    db.add(new_sem)
    db.commit()
    print(f"Admin {user.email} created semester {new_sem.code}")
    return RedirectResponse(url="/admin/semesters", status_code=303)


@router.post("/admin/semesters/{semester_id}/delete")
async def admin_delete_semester(
    semester_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Soft-delete a semester (set is_active=False)"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    sem = db.query(Semester).filter(Semester.id == semester_id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester not found")

    # Check if semester has active enrollments
    active_count = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == semester_id,
        SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
    ).count()

    if active_count > 0:
        # Don't delete — just deactivate
        sem.is_active = False
        db.commit()
        print(f"Admin {user.email} deactivated semester {sem.code} ({active_count} active enrollments)")
    else:
        db.delete(sem)
        db.commit()
        print(f"Admin {user.email} deleted semester {sem.code}")

    return RedirectResponse(url="/admin/semesters", status_code=303)


@router.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin-only: Analytics and reports page"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get platform statistics
    total_users = db.query(User).count()
    total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    total_instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR).count()
    total_sessions = db.query(SessionModel).count()
    total_bookings = db.query(Booking).count()
    
    stats = {
        "total_users": total_users,
        "total_students": total_students,
        "total_instructors": total_instructors,
        "total_sessions": total_sessions,
        "total_bookings": total_bookings
    }
    
    return templates.TemplateResponse(
        "admin/analytics.html",
        {
            "request": request,
            "user": user,
            "stats": stats
        }
    )


# ============================================================================
# MOTIVATION ASSESSMENT ROUTES - Admin/Instructor evaluate student motivation
# ============================================================================

@router.get("/admin/students/{student_id}/motivation/{specialization}", response_class=HTMLResponse)
async def motivation_assessment_page(
    request: Request,
    student_id: int,
    specialization: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin/Instructor-only: Motivation assessment page for a student's specialization"""
    if user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(status_code=403, detail="Admin or Instructor access required")

    # Get student
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get student's license for this specialization
    license = db.query(UserLicense).filter(
        UserLicense.user_id == student_id,
        UserLicense.specialization_type == specialization
    ).first()

    if not license:
        raise HTTPException(status_code=404, detail=f"Student does not have {specialization} license")

    # Format specialization name for display
    specialization_display = specialization.replace('_', ' ').title()

    # Check if there are existing scores
    existing_scores = license.motivation_scores is not None

    return templates.TemplateResponse(
        "admin/motivation_assessment.html",
        {
            "request": request,
            "user": user,
            "student": student,
            "license": license,
            "specialization": specialization,
            "specialization_display": specialization_display,
            "existing_scores": existing_scores
        }
    )


@router.post("/admin/students/{student_id}/motivation/{specialization}")
async def motivation_assessment_submit(
    request: Request,
    student_id: int,
    specialization: str,
    goal_clarity: int = Form(...),
    commitment_level: int = Form(...),
    engagement: int = Form(...),
    progress_mindset: int = Form(...),
    initiative: int = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Admin/Instructor-only: Save motivation assessment"""
    if user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(status_code=403, detail="Admin or Instructor access required")

    # Validate scores (1-5)
    scores = [goal_clarity, commitment_level, engagement, progress_mindset, initiative]
    for score in scores:
        if score < 1 or score > 5:
            raise HTTPException(status_code=400, detail="Scores must be between 1 and 5")

    # Get student's license
    license = db.query(UserLicense).filter(
        UserLicense.user_id == student_id,
        UserLicense.specialization_type == specialization
    ).first()

    if not license:
        raise HTTPException(status_code=404, detail=f"Student does not have {specialization} license")

    # Create motivation scores JSON
    motivation_data = {
        "goal_clarity": goal_clarity,
        "commitment_level": commitment_level,
        "engagement": engagement,
        "progress_mindset": progress_mindset,
        "initiative": initiative,
        "notes": notes,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "assessed_by_id": user.id,
        "assessed_by_name": user.name
    }

    # Calculate average
    average_score = sum(scores) / len(scores)

    # Update license
    license.motivation_scores = motivation_data
    license.average_motivation_score = average_score
    license.motivation_last_assessed_at = datetime.now(timezone.utc)
    license.motivation_assessed_by = user.id

    db.commit()

    print(f"✅ {user.name} assessed {student_id}'s motivation for {specialization}: {average_score:.1f}/5.0")

    # Redirect back to student details or payments page
    return RedirectResponse(url=f"/admin/payments", status_code=303)


# ============================================================================
# 🎓 SEMESTER ENROLLMENT REQUEST WORKFLOW (Student-initiated, Admin-approved)
# ============================================================================

