"""
Dashboard routes for student, instructor, and admin dashboards
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone, date
import re

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User, UserRole
from .helpers import get_lfa_age_category

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard-fresh", response_class=HTMLResponse)  # CACHE BYPASS ROUTE
async def dashboard(
    request: Request,
    spec: str = None,  # Query param for spec switching
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Dashboard page with multi-spec support"""
    from ...models.user import UserRole

    # 🆕 STUDENT DASHBOARD: Unified hub showing ALL specializations (locked + unlocked)
    if user.role == UserRole.STUDENT:
        from ...models.license import UserLicense
        from ...utils.age_requirements import get_available_specializations
        from datetime import date

        # Calculate user age
        user_age = None
        if user.date_of_birth:
            today = date.today()
            user_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))

        # Get user's existing licenses (unlocked specializations)
        user_licenses = db.query(UserLicense).filter(UserLicense.user_id == user.id).all()
        unlocked_specs = {lic.specialization_type for lic in user_licenses}

        # Get age-appropriate specializations
        available_specs_list = get_available_specializations(user_age)

        # Build specialization data with unlock status (ALWAYS SHOW ALL)
        specializations_data = []
        for spec_item in available_specs_list:
            is_unlocked = spec_item["type"] in unlocked_specs
            specializations_data.append({
                "type": spec_item["type"],
                "name": spec_item["name"],
                "icon": spec_item["icon"],
                "color": spec_item["color"],
                "description": spec_item["description"],
                "age_requirement": spec_item["age_requirement"],
                "is_unlocked": is_unlocked,  # ✅ NEW: Mark as unlocked if user has license
                "is_available": True
            })

        print(f"🎓 Dashboard for {user.email}: {len(unlocked_specs)} unlocked, {len(specializations_data)} total specs")

        # ALWAYS show specialization hub (no auto-redirect)
        return templates.TemplateResponse(
            "hub_specializations.html",  # SPECIALIZATIONS HUB
            {
                "request": request,
                "user": user,
                "user_age": user_age or "N/A",
                "available_specializations": specializations_data,
                "unlocked_count": len(unlocked_specs)  # For displaying stats
            }
        )
    else:
        # Not a student or no special multi-spec handling needed
        specialization = None

    # 📅 Get active semesters (for ADMIN dashboard)
    active_semesters = []
    if user.role == UserRole.ADMIN:
        from ...models.semester import Semester
        from datetime import date
        import re

        today = date.today()
        active_semesters = db.query(Semester).filter(
            Semester.is_active == True,
            Semester.start_date <= today,
            Semester.end_date >= today
        ).order_by(Semester.code, Semester.start_date.desc()).all()

        # Add specialization_type and extract location from code
        for semester in active_semesters:
            code = semester.code

            # Extract location suffix (BUDA, PEST, BUDAPEST, city names)
            location_match = re.search(r'_(BUDA|PEST|BUDAPEST|DEBRECEN|SZEGED|MISKOLC|GYOR)$', code, re.IGNORECASE)
            if location_match:
                location_suffix = location_match.group(1)
                # Set location_venue if not already set in DB
                if not semester.location_venue:
                    if location_suffix.upper() in ['BUDA', 'PEST']:
                        semester.location_venue = f"{location_suffix.capitalize()} Campus"
                        semester.location_city = "Budapest"
                    else:
                        semester.location_city = location_suffix.capitalize()

                # Remove location suffix for specialization extraction
                code_without_location = code[:location_match.start()]
            else:
                code_without_location = code

            # Remove year patterns
            code_clean = re.sub(r'_\d{4}(-\d{2})?(_[A-Z]{3,6})?$', '', code_without_location)
            code_clean = re.sub(r'_\d{4}_Q\d$', '', code_clean)

            # Special case: GANCUJU should become GANCUJU_PLAYER
            if code_clean.startswith('GANCUJU'):
                semester.specialization_type = 'GANCUJU_PLAYER'
            else:
                semester.specialization_type = code_clean if code_clean else None

    # Get user's specialization (if not already set by multi-spec logic above)
    if user.role != UserRole.STUDENT or not specialization:
        specialization = user.specialization if hasattr(user, 'specialization') and user.specialization else None

    # 🔄 REDIRECT: Check if student has incomplete onboarding on any UserLicense
    if user.role == UserRole.STUDENT:
        from ...models.license import UserLicense

        # Check all user licenses for incomplete onboarding
        incomplete_license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.onboarding_completed == False
        ).first()

        if incomplete_license:
            print(f"⚠️ Student {user.email} has incomplete onboarding for {incomplete_license.specialization_type} - redirecting to onboarding")

            # Redirect to specialization-specific onboarding page
            if incomplete_license.specialization_type == "LFA_FOOTBALL_PLAYER":
                return RedirectResponse(url="/specialization/lfa-player/onboarding", status_code=303)
            elif incomplete_license.specialization_type == "GANCUJU_PLAYER":
                return RedirectResponse(url="/specialization/gancuju-player/onboarding", status_code=303)
            elif incomplete_license.specialization_type == "LFA_COACH":
                return RedirectResponse(url="/specialization/lfa-coach/onboarding", status_code=303)
            else:
                # For INTERNSHIP and others without specialized onboarding, mark as completed
                incomplete_license.onboarding_completed = True
                db.commit()

    # REDIRECT: If student has specialization but hasn't completed onboarding (motivation questionnaire)
    if user.role == UserRole.STUDENT and specialization and not user.onboarding_completed:
        print(f"⚠️ Student {user.email} has specialization {specialization.value} but onboarding incomplete - redirecting to motivation questionnaire")
        return RedirectResponse(url=f"/specialization/motivation?spec={specialization.value}", status_code=303)

    # Check if user is instructor
    is_instructor = user.role == UserRole.INSTRUCTOR

    # Get instructor teaching qualifications
    teaching_specializations = []
    all_teaching_specializations = []
    if is_instructor:
        teaching_specializations = user.get_teaching_specializations()  # Active only
        all_teaching_specializations = user.get_all_teaching_specializations()  # Active + Inactive

    # Get XP data from user_stats (ONLY for students)
    xp_data = {
        "total_xp": 0,
        "level": 1,
        "level_progress": 0
    }

    # Get user licenses and specialization color (for students)
    user_licenses = []
    specialization_color = None
    pending_enrollments = []
    has_active_enrollment = False  # Default to False for non-students
    current_license = None  # Initialize for all users
    available_semesters = []
    current_semester = None
    next_semester = None

    if user.role == UserRole.STUDENT:
        from ...models.gamification import UserStats
        from ...models.license import UserLicense
        from ...models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
        from sqlalchemy.orm import joinedload

        user_stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()
        if user_stats:
            xp_data = {
                "total_xp": user_stats.total_xp or 0,
                "level": user_stats.level or 1,
                "level_progress": ((user_stats.total_xp or 0) % 1000) / 10  # % to next level
            }

        # Get all user licenses for the specialization switcher
        user_licenses = db.query(UserLicense).filter(UserLicense.user_id == user.id).all()

        # Generate payment codes for any licenses that don't have them
        from datetime import datetime
        import secrets
        for lic in user_licenses:
            if not lic.payment_reference_code:
                spec_short = {
                    'INTERNSHIP': 'INT',
                    'GANCUJU_PLAYER': 'GCJ',
                    'LFA_FOOTBALL_PLAYER': 'FBL',
                    'LFA_COACH': 'COA'
                }.get(lic.specialization_type, 'LIC')
                year = datetime.now().year
                random_code = secrets.token_hex(2).upper()
                lic.payment_reference_code = f"{spec_short}-{year}-{user.id:03d}-{random_code}"
                print(f"✅ Generated payment code for {user.email} → {lic.specialization_type}: {lic.payment_reference_code}")
        if user_licenses:
            db.commit()

        # Get all enrollments for this user (to show enrollment status)
        pending_enrollments = (
            db.query(SemesterEnrollment)
            .options(
                joinedload(SemesterEnrollment.semester),
                joinedload(SemesterEnrollment.user_license)
            )
            .filter(
                SemesterEnrollment.user_id == user.id
            )
            .order_by(SemesterEnrollment.requested_at.desc())
            .all()
        )

        # Generate payment codes for any enrollments that don't have them
        for enrollment in pending_enrollments:
            if not enrollment.payment_reference_code:
                enrollment.set_payment_code()
        if pending_enrollments:
            db.commit()

        print(f"📋 DEBUG: User {user.email} has {len(pending_enrollments)} pending enrollments:")
        for enr in pending_enrollments:
            print(f"   - {enr.semester.name} (Status: {enr.request_status.value}, License: {enr.user_license.specialization_type})")

        print(f"🔍 DEBUG: User {user.email} has {len(user_licenses)} licenses:")
        for lic in user_licenses:
            print(f"   - {lic.specialization_type} (level {lic.current_level})")
        print(f"🔍 DEBUG: user_licenses type: {type(user_licenses)}")
        print(f"🔍 DEBUG: user_licenses bool: {bool(user_licenses)}")
        print(f"🔍 DEBUG: user_licenses len: {len(user_licenses)}")

        # Get color for current specialization (for welcome box gradient)
        specialization_colors = {
            "GANCUJU_PLAYER": "#8e44ad",       # Purple (unique purple for GānCuju)
            "LFA_PLAYER_PRE": "#f1c40f",       # Yellow (for LFA Player PRE)
            "LFA_PLAYER_YOUTH": "#f1c40f",     # Yellow (for LFA Player Youth)
            "LFA_PLAYER_AMATEUR": "#f1c40f",   # Yellow (for LFA Player Amateur)
            "LFA_PLAYER_PRO": "#f1c40f",       # Yellow (for LFA Player PRO)
            "LFA_FOOTBALL_PLAYER": "#f1c40f",  # Yellow (Legacy)
            "LFA_COACH": "#27ae60",            # Green (for LFA Coach)
            "INTERNSHIP": "#e74c3c"            # Red (keep as is)
        }
        if specialization:
            specialization_color = specialization_colors.get(specialization.value, "#3498db")

        # Check if user has an ACTIVE, APPROVED enrollment
        has_active_enrollment = False
        if specialization:
            active_enrollment = (
                db.query(SemesterEnrollment)
                .filter(
                    SemesterEnrollment.user_id == user.id,
                    SemesterEnrollment.user_license_id.in_([lic.id for lic in user_licenses if lic.specialization_type == specialization.value]),
                    SemesterEnrollment.is_active == True,
                    SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
                )
                .first()
            )
            has_active_enrollment = active_enrollment is not None
            print(f"🔍 User {user.email} has active enrollment: {has_active_enrollment}")

        # Get upcoming sessions from APPROVED semesters (for "Next Session" card)
        upcoming_sessions = []
        if has_active_enrollment:
            from ...models.session import Session as SessionModel
            approved_enrollments = db.query(SemesterEnrollment).filter(
                SemesterEnrollment.user_id == user.id,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
                SemesterEnrollment.is_active == True
            ).all()

            approved_semester_ids = [e.semester_id for e in approved_enrollments]
            print(f"🔍 DEBUG: Approved semester IDs: {approved_semester_ids}")

            if approved_semester_ids:
                from datetime import datetime as dt
                now = dt.now()
                upcoming_sessions = db.query(SessionModel).filter(
                    SessionModel.semester_id.in_(approved_semester_ids),
                    SessionModel.date_start >= now
                ).order_by(SessionModel.date_start.asc()).limit(3).all()
                print(f"🔍 DEBUG: Found {len(upcoming_sessions)} upcoming sessions for {user.email}")

        # Get active semesters and check which ones user can enroll in
        from ...models.semester import Semester
        from datetime import date

        # Get current license for current specialization (to check payment_verified)
        if specialization:
            current_license = next((lic for lic in user_licenses if lic.specialization_type == specialization.value), None)

        # Check which semesters user already enrolled in
        existing_enrollments = (
            db.query(SemesterEnrollment)
            .filter(SemesterEnrollment.user_id == user.id)
            .all()
        )
        enrolled_semester_ids = {e.semester_id for e in existing_enrollments}

        # 💰 Get credit balance from User (centralized, spec-independent)
        credit_balance = user.credit_balance
        credit_purchased = user.credit_purchased

        # Get relevant semesters based on specialization
        if specialization:
            today = date.today()

            # Map specialization to semester code prefix
            semester_code_prefix = {
                'LFA_PLAYER_PRE': 'LFA_PLAYER_PRE',
                'LFA_PLAYER_YOUTH': 'LFA_PLAYER_YOUTH',
                'LFA_PLAYER_AMATEUR': 'LFA_PLAYER_AMATEUR',
                'LFA_PLAYER_PRO': 'LFA_PLAYER_PRO',
                'LFA_FOOTBALL_PLAYER': 'LFA_PLAYER',  # Legacy: Match ALL LFA_PLAYER_* semesters
                'GANCUJU_PLAYER': 'GANCUJU',  # GANCUJU_PLAYER → GANCUJU_*
                'LFA_COACH': 'LFA_COACH',
                'INTERNSHIP': 'INTERNSHIP'
            }.get(specialization.value, specialization.value)

            # Get all semesters for this track
            track_semesters = (
                db.query(Semester)
                .filter(
                    Semester.code.like(f'{semester_code_prefix}_%'),
                    Semester.is_active == True
                )
                .order_by(Semester.start_date)
                .all()
            )

            # Find current and next semester
            for sem in track_semesters:
                if sem.start_date <= today <= sem.end_date:
                    current_semester = sem
                elif sem.start_date > today and not next_semester:
                    next_semester = sem

            # Available semesters are those not yet enrolled and payment is verified
            # Show NEXT 6 semesters for advance booking (user can plan ahead)
            if current_license and current_license.payment_verified:
                available_semesters = [
                    sem for sem in track_semesters
                    if sem.id not in enrolled_semester_ids and sem.start_date >= today
                ][:6]  # Show max 6 upcoming semesters for advance booking

            print(f"🔍 DEBUG: current_license={current_license}, payment_verified={current_license.payment_verified if current_license else None}")
            print(f"🔍 DEBUG: track_semesters count={len(track_semesters)}")
            print(f"🔍 DEBUG: available_semesters count={len(available_semesters)}")

    # ⚽ Get football skills for LFA Player specializations
    football_skills = None
    skills_updated_by_name = None
    if user.role == UserRole.STUDENT and specialization and current_license:
        if specialization.value.startswith("LFA_PLAYER_"):
            football_skills = current_license.football_skills
            if current_license.skills_updated_by:
                updater = db.query(User).filter(User.id == current_license.skills_updated_by).first()
                if updater:
                    skills_updated_by_name = updater.name

    # ========================================
    # ROLE-BASED TEMPLATE ROUTING (3 Separate Templates)
    # ========================================

    if user.role == UserRole.ADMIN:
        # ADMIN Dashboard
        print(f"🎯 ROUTING: Using dashboard_admin.html for {user.email}")
        from ...models.user import User as UserModel
        stats = {
            "total_users": db.query(UserModel).count(),
            "active_students": db.query(UserModel).filter(UserModel.role == UserRole.STUDENT).count(),
            "instructors": db.query(UserModel).filter(UserModel.role == UserRole.INSTRUCTOR).count(),
        }

        response = templates.TemplateResponse(
            "dashboard_admin.html",
            {
                "request": request,
                "user": user,
                "active_semesters": active_semesters,
                "stats": stats
            }
        )
    elif user.role == UserRole.INSTRUCTOR:
        # INSTRUCTOR Dashboard
        print(f"🎯 ROUTING: Using dashboard_instructor.html for {user.email}")
        response = templates.TemplateResponse(
            "dashboard_instructor.html",
            {
                "request": request,
                "user": user,
                "teaching_specializations": teaching_specializations,
                "all_teaching_specializations": all_teaching_specializations,
            }
        )
    else:
        # STUDENT Dashboard
        print(f"🎯 ROUTING: Using dashboard_student_new.html for {user.email}")
        response = templates.TemplateResponse(
            "dashboard_student_new.html",
            {
                "request": request,
                "user": user,
                "specialization": specialization,
                "xp_data": xp_data,
                "user_licenses": user_licenses,
                "specialization_color": specialization_color,
                "pending_enrollments": pending_enrollments,
                "has_active_enrollment": has_active_enrollment,
                "current_license": current_license,
                "available_semesters": available_semesters,
                "current_semester": current_semester,
                "next_semester": next_semester,
                "football_skills": football_skills,
                "skills_updated_by_name": skills_updated_by_name,
                "upcoming_sessions": upcoming_sessions,
                "credit_balance": credit_balance,
                "credit_purchased": credit_purchased
            }
        )
    # Disable caching to ensure fresh data
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def get_lfa_age_category(date_of_birth):
    """
    Determine LFA Player age category based on date of birth.

    Returns tuple: (category_code, category_name, age_range, description)

    Categories:
    - PRE (5-13 years): Foundation Years - Monthly semesters
    - YOUTH (14-18 years): Technical Development - Quarterly semesters
    - AMATEUR (14+ years): Competitive Play - Bi-annual semesters (instructor assigned)
    - PRO (14+ years): Professional Track - Annual semesters (instructor assigned)
    """
    from datetime import date

    if not date_of_birth:
        return None, None, None, "Date of birth not set"

    today = date.today()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

    if 5 <= age <= 13:
        return "PRE", "PRE (Foundation Years)", "5-13 years", f"Age {age} - Monthly training blocks"
    elif 14 <= age <= 18:
        return "YOUTH", "YOUTH (Technical Development)", "14-18 years", f"Age {age} - Quarterly programs"
    elif age > 18:
        # For 18+ students, category must be assigned by instructor (AMATEUR or PRO)
        return None, None, None, f"Age {age} - Category assigned by instructor (AMATEUR or PRO)"
    else:
        return None, None, None, f"Age {age} - Below minimum age requirement (5 years)"


@router.get("/dashboard/{spec_type}", response_class=HTMLResponse)
async def spec_dashboard(
    request: Request,
    spec_type: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Spec-specific dashboard for unlocked specializations"""
    from ...models.user import UserRole
    from ...models.license import UserLicense
    from ...models.semester_enrollment import SemesterEnrollment
    from ...models.semester import Semester
    from datetime import date, timezone

    # Convert URL format to enum format (e.g., "lfa-football-player" → "LFA_FOOTBALL_PLAYER")
    spec_enum = spec_type.upper().replace("-", "_")

    # Verify user has access to this specialization
    user_license = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == spec_enum
    ).first()

    if not user_license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have access to {spec_type}. Please unlock it first."
        )

    # Simple spec config (no external config file needed)
    spec_configs = {
        "LFA_FOOTBALL_PLAYER": {"name": "LFA Football Player", "icon": "⚽", "color": "#2ecc71"},
        "GANCUJU_PLAYER": {"name": "GanCuju Player", "icon": "🥋", "color": "#e74c3c"},
        "JUNIOR_INTERNSHIP": {"name": "Junior Internship", "icon": "💼", "color": "#3498db"},
        "SENIOR_INTERNSHIP": {"name": "Senior Internship", "icon": "🎓", "color": "#9b59b6"},
    }

    spec_config = spec_configs.get(spec_enum, {
        "name": spec_type.replace("-", " ").title(),
        "icon": "🎓",
        "color": "#667eea"
    })

    # Get active enrollment for this spec
    has_active_enrollment = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == user.id,
        SemesterEnrollment.user_license_id == user_license.id,
        SemesterEnrollment.is_active == True
    ).first() is not None

    # Get available semesters for this spec
    today = date.today()

    # For LFA_FOOTBALL_PLAYER, determine age-based category
    age_category = None
    age_category_name = None
    age_range = None
    age_description = None
    user_age = None

    if spec_enum == 'LFA_FOOTBALL_PLAYER':
        age_category, age_category_name, age_range, age_description = get_lfa_age_category(user.date_of_birth)

        # Calculate user_age for template display
        if user.date_of_birth:
            user_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))

        print(f"⚽ LFA PLAYER AGE CHECK: {user.email} → {age_category} ({age_description}) - Age: {user_age}")

        if not age_category:
            # User doesn't meet age requirements
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=age_description
            )

    # Map specialization to semester code prefix
    semester_code_prefix = {
        'LFA_PLAYER_PRE': 'LFA_PLAYER_PRE',
        'LFA_PLAYER_YOUTH': 'LFA_PLAYER_YOUTH',
        'LFA_PLAYER_AMATEUR': 'LFA_PLAYER_AMATEUR',
        'LFA_PLAYER_PRO': 'LFA_PLAYER_PRO',
        'LFA_FOOTBALL_PLAYER': f'LFA_PLAYER_{age_category}' if age_category else 'LFA_PLAYER',  # Age-based filtering!
        'GANCUJU_PLAYER': 'GANCUJU',  # GANCUJU_PLAYER → GANCUJU_*
        'LFA_COACH': 'LFA_COACH',
        'INTERNSHIP': 'INTERNSHIP'
    }.get(spec_enum, spec_enum)

    print(f"🔍 SEMESTER PREFIX: {semester_code_prefix} (searching for: {semester_code_prefix}_*)")

    # Get all track semesters
    track_semesters = db.query(Semester).filter(
        Semester.code.like(f'{semester_code_prefix}_%'),
        Semester.is_active == True
    ).order_by(Semester.start_date).all()

    print(f"📚 FOUND {len(track_semesters)} semesters for prefix '{semester_code_prefix}'")
    if track_semesters:
        for sem in track_semesters[:3]:  # Show first 3
            print(f"  - {sem.code} ({sem.start_date} to {sem.end_date})")

    # Check which semesters user already enrolled in
    existing_enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == user.id
    ).all()
    enrolled_semester_ids = {e.semester_id for e in existing_enrollments}

    # Available semesters = all semesters not yet enrolled (show upcoming and current, max 6)
    # Filter: not enrolled AND (current semester OR future semester)
    available_semesters = [
        sem for sem in track_semesters
        if sem.id not in enrolled_semester_ids and sem.end_date >= today
    ][:6]

    print(f"✅ AVAILABLE SEMESTERS: {len(available_semesters)} (after filtering enrolled + ended)")

    # Get current semester if enrolled
    current_semester = None
    if has_active_enrollment:
        enrollment = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.user_id == user.id,
            SemesterEnrollment.user_license_id == user_license.id,
            SemesterEnrollment.is_active == True
        ).first()
        if enrollment:
            current_semester = enrollment.semester

    # Get all pending enrollments for this user
    pending_enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == user.id
    ).order_by(SemesterEnrollment.requested_at.desc()).all()

    # Get user credit balance
    credit_balance = user.credit_balance if hasattr(user, 'credit_balance') else 0

    return templates.TemplateResponse(
        "dashboard_student_new.html",
        {
            "request": request,
            "user": user,
            "specialization": spec_enum,
            "spec_config": spec_config,
            "user_license": user_license,
            "current_license": user_license,  # For payment_verified check
            "has_active_enrollment": has_active_enrollment,
            "available_semesters": available_semesters,
            "current_semester": current_semester,
            "specialization_color": spec_config.get("color", "#667eea"),
            "pending_enrollments": pending_enrollments,
            "credit_balance": credit_balance,
            "credit_purchased": user.credit_purchased if hasattr(user, 'credit_purchased') else 0,
            # LFA Player age category info
            "age_category": age_category,
            "age_category_name": age_category_name,
            "age_range": age_range,
            "age_description": age_description,
            "user_age": user_age
        }
    )

