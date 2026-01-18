"""
Student-specific feature routes (about specializations, credits, progress, achievements)
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from datetime import datetime, timezone

from ...database import get_db
from ...dependencies import get_current_user_web, get_current_user_optional
from ...models.user import User, UserRole

# Setup templates
    from datetime import date

    # Calculate user age
    from ...models.license import UserLicense
    from ...models.semester_enrollment import SemesterEnrollment
    from ...models.semester import Semester
    from ...models.invoice_request import InvoiceRequest

    from datetime import timezone as tz
    from ...services.gamification import GamificationService
    from ...models.session import Session as SessionModel
    from ...models.attendance import Attendance

    # ONLY STUDENTS can view progress - instructors TEACH, they don't learn!
        from ...models.quiz import AdaptiveLearningSession

    # Get ALL user licenses for the switcher dropdown
    from ...models.achievement import Achievement
    from ...models.gamification import UserAchievement

    # Get all achievements from database
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/about-specializations", response_class=HTMLResponse)
async def about_specializations_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """About specializations information page"""
    user_age = None
    if user.date_of_birth:
        today = date.today()
        user_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))

    return templates.TemplateResponse(
        "about_specializations.html",
        {
            "request": request,
            "user": user,
            "user_age": user_age
        }
    )


@router.get("/credits", response_class=HTMLResponse)
async def credits_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Credits management page - view balance, purchase credits, transaction history
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    # Get all user licenses (all specializations)
    user_licenses = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id
    ).all()

    # Use centralized credit balance from User model (spec-independent)
    total_credit_balance = current_user.credit_balance
    total_credit_purchased = current_user.credit_purchased
    # Credits used = purchased - balance (but never negative, since user might have bonus credits)
    total_credit_used = max(0, total_credit_purchased - total_credit_balance)

    # Get all semester enrollments with credit spending
    enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == current_user.id
    ).order_by(SemesterEnrollment.created_at.desc()).all()

    # Build transaction history
    transactions = []

    # Get all invoice requests from invoice_requests table (NEW centralized credit system)
    invoice_requests = db.query(InvoiceRequest).filter(
        InvoiceRequest.user_id == current_user.id
    ).order_by(InvoiceRequest.created_at.desc()).all()

    # Add verified invoice requests as PURCHASE transactions
    for invoice in invoice_requests:
        if invoice.status == 'verified':  # Only show verified invoices as completed purchases
            transactions.append({
                'date': invoice.verified_at or invoice.created_at,
                'type': 'purchase',
                'amount': invoice.credit_amount,
                'specialization': invoice.specialization or 'All Specializations',
                'description': f'Credit purchase via invoice ({invoice.amount_eur} EUR)',
                'status': 'verified',
                'payment_reference': invoice.payment_reference
            })

    # Add credit purchases from licenses (OLD system - for backward compatibility)
    for license in user_licenses:
        if license.credit_purchased > 0:
            # Handle specialization_type (could be enum or string)
            spec_name = 'N/A'
            if license.specialization_type:
                spec_name = license.specialization_type.value if hasattr(license.specialization_type, 'value') else str(license.specialization_type)

            transactions.append({
                'date': license.created_at,
                'type': 'purchase',
                'amount': license.credit_purchased,
                'specialization': spec_name,
                'description': f'Credit purchase for {spec_name}',
                'status': 'verified' if license.payment_verified else 'pending',
                'payment_reference': license.payment_reference_code  # Show old license-specific payment code
            })

    # Add semester enrollments (credit spending)
    for enrollment in enrollments:
        semester = db.query(Semester).filter(Semester.id == enrollment.semester_id).first()
        if semester:
            transactions.append({
                'date': enrollment.created_at,
                'type': 'enrollment',
                'amount': -semester.enrollment_cost,
                'specialization': semester.code.split('_')[0] if '_' in semester.code else semester.code,
                'description': f'Enrolled in {semester.name}',
                'status': enrollment.request_status.value
            })

    # Sort by date descending (handle None and timezone issues)
    def safe_date_key(transaction):
        date = transaction['date']
        if date is None:
            return datetime.min.replace(tzinfo=tz.utc)
        # Ensure timezone aware
        if date.tzinfo is None:
            return date.replace(tzinfo=tz.utc)
        return date

    transactions.sort(key=safe_date_key, reverse=True)

    # Get specialization color
    specialization_color = None
    if current_user.specialization:
        if current_user.specialization.value == 'INTERNSHIP':
            specialization_color = '#e74c3c'
        elif current_user.specialization.value == 'GANCUJU_PLAYER':
            specialization_color = '#8e44ad'
        elif current_user.specialization.value == 'LFA_FOOTBALL_PLAYER':
            specialization_color = '#f1c40f'
        elif current_user.specialization.value == 'LFA_COACH':
            specialization_color = '#27ae60'
        elif 'LFA_PLAYER' in current_user.specialization.value:
            specialization_color = '#3498db'

    # Check for active enrollment (for navbar navigation)
    has_active_enrollment = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == current_user.id,
        SemesterEnrollment.is_active == True
    ).first() is not None

    return templates.TemplateResponse(
        "credits.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "specialization": current_user.specialization,
            "has_active_enrollment": has_active_enrollment,
            "total_credit_balance": total_credit_balance,
            "total_credit_purchased": total_credit_purchased,
            "total_credit_used": total_credit_used,
            "user_licenses": user_licenses,
            "transactions": transactions,
            "invoice_requests": invoice_requests,
            "specialization_color": specialization_color or '#667eea',
            "today": datetime.now(timezone.utc).date()
        }
    )


@router.get("/progress", response_class=HTMLResponse)
async def progress_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Display student academic progress page with XP, level, and semester completion"""
    if user.role != UserRole.STUDENT:
        return RedirectResponse(url="/dashboard", status_code=303)

    gamification = GamificationService(db)

    # Get user stats
    stats = gamification.get_or_create_user_stats(user.id)

    # Get current semester info (SPEC-SPECIFIC)
    current_semester = None
    if user.specialization:
        # Map specialization to semester code prefix
        semester_code_prefix = {
            'LFA_PLAYER_PRE': 'LFA_PLAYER_PRE',
            'LFA_PLAYER_YOUTH': 'LFA_PLAYER_YOUTH',
            'LFA_PLAYER_AMATEUR': 'LFA_PLAYER_AMATEUR',
            'LFA_PLAYER_PRO': 'LFA_PLAYER_PRO',
            'GANCUJU_PLAYER': 'GANCUJU',
            'LFA_COACH': 'LFA_COACH',
            'INTERNSHIP': 'INTERNSHIP'
        }.get(user.specialization.value, user.specialization.value)

        current_semester = db.query(Semester).filter(
            Semester.code.like(f'{semester_code_prefix}_%'),
            Semester.start_date <= datetime.now(timezone.utc),
            Semester.end_date >= datetime.now(timezone.utc)
        ).first()

    # Calculate semester progress
    semester_data = None
    if current_semester:
        # Get all sessions in semester
        all_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == current_semester.id
        ).all()

        # Get student's attended sessions with XP earned
        attended_sessions = db.query(Attendance).filter(
            Attendance.user_id == user.id
        ).join(
            SessionModel, Attendance.session_id == SessionModel.id
        ).filter(
            SessionModel.semester_id == current_semester.id
        ).all()

        # Calculate XP from session completions
        total_available_xp = sum(s.base_xp or 50 for s in all_sessions)
        earned_session_xp = sum(a.xp_earned or 0 for a in attended_sessions)

        # Add bonus XP from Adaptive Learning sessions
        adaptive_xp = db.query(func.sum(AdaptiveLearningSession.xp_earned)).filter(
            AdaptiveLearningSession.user_id == user.id,
            AdaptiveLearningSession.started_at >= current_semester.start_date,
            AdaptiveLearningSession.started_at <= current_semester.end_date
        ).scalar() or 0

        # Total XP = session XP + adaptive learning bonus
        earned_xp = earned_session_xp + adaptive_xp

        # Progress calculation (can exceed 100% with bonus XP)
        progress_percent = (earned_xp / total_available_xp * 100) if total_available_xp > 0 else 0

        semester_data = {
            'name': current_semester.name,
            'start_date': current_semester.start_date,
            'end_date': current_semester.end_date,
            'total_sessions': len(all_sessions),
            'attended_sessions': len(attended_sessions),
            'total_available_xp': total_available_xp,
            'earned_xp': earned_xp,
            'earned_session_xp': earned_session_xp,
            'earned_bonus_xp': adaptive_xp,
            'progress_percent': progress_percent,
            'pass_xp': int(total_available_xp * 0.7),
            'good_xp': int(total_available_xp * 0.83),
            'excellence_xp': int(total_available_xp * 0.92),
            'status': 'EXCELLENCE' if progress_percent >= 92 else 'GOOD' if progress_percent >= 83 else 'PASS' if progress_percent >= 70 else 'INCOMPLETE'
        }

    # Calculate level progress to next level
    current_level = stats.level
    xp_for_current_level = (current_level - 1) * 500
    xp_for_next_level = current_level * 500
    xp_progress_in_level = stats.total_xp - xp_for_current_level
    xp_needed_for_next = xp_for_next_level - stats.total_xp
    level_progress_percent = (xp_progress_in_level / 500 * 100) if stats.total_xp < xp_for_next_level else 100

    # Get ONLY the active specialization's UserLicense
    user_licenses = db.query(UserLicense).filter(
        UserLicense.user_id == user.id
    ).all()

    # Filter by user's currently active specialization (from switcher)
    active_license = None
    if user.specialization:
        active_license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.specialization_type == user.specialization.value
        ).first()

    # Build specialization progress data for ACTIVE specialization only
    specialization_progress = None
    if active_license:
        license = active_license
        # Determine level names based on specialization type
        if license.specialization_type == 'INTERNSHIP':
            level_names = ['Junior', 'Mid-Level', 'Senior', 'Lead', 'Principal']
            max_levels = 5
            color = '#e74c3c'
        elif license.specialization_type == 'GANCUJU_PLAYER':
            level_names = [
                'Bamboo Disciple (White)', 'Dawn Dew (Yellow)', 'Flexible Reed (Green)',
                'Celestial River (Blue)', 'Strong Root (Brown)', 'Winter Moon (Grey)',
                'Midnight Guardian (Black)', 'Dragon Wisdom (Red)'
            ]
            max_levels = 8
            color = '#8e44ad'
        elif license.specialization_type == 'LFA_FOOTBALL_PLAYER':
            level_names = [
                'PRE Level 1', 'PRE Level 2', 'Youth Level 1', 'Youth Level 2',
                'Amateur Level 1', 'Amateur Level 2', 'PRO Level 1', 'PRO Level 2'
            ]
            max_levels = 8
            color = '#f1c40f'
        elif license.specialization_type == 'LFA_COACH':
            level_names = [
                'PRE Assistant Coach', 'PRE Head Coach', 'Youth Assistant Coach', 'Youth Head Coach',
                'Amateur Assistant Coach', 'Amateur Head Coach', 'PRO Assistant Coach', 'PRO Head Coach'
            ]
            max_levels = 8
            color = '#27ae60'
        else:
            level_names = [f'Level {i}' for i in range(1, 9)]
            max_levels = 8
            color = '#95a5a6'

        # Build roadmap data
        roadmap = []
        current_level_idx = license.current_level - 1
        for i in range(max_levels):
            status = 'completed' if i < license.max_achieved_level else ('current' if i == current_level_idx else 'locked')
            roadmap.append({
                'level': i + 1,
                'name': level_names[i] if i < len(level_names) else f'Level {i+1}',
                'status': status
            })

        # Store as single object (not array) since we only show one spec at a time
        specialization_progress = {
            'type': license.specialization_type,
            'current_level': license.current_level,
            'max_achieved_level': license.max_achieved_level,
            'max_levels': max_levels,
            'progress_percent': (license.current_level / max_levels * 100),
            'started_at': license.started_at,
            'last_advanced_at': license.last_advanced_at,
            'color': color,
            'roadmap': roadmap,
            'onboarding_completed': license.onboarding_completed
        }

    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "semester": semester_data,
            "level_progress": {
                'current_level': current_level,
                'next_level': current_level + 1,
                'xp_progress': xp_progress_in_level,
                'xp_needed': xp_needed_for_next,
                'progress_percent': level_progress_percent
            },
            "specialization_progress": specialization_progress,
            "user_licenses": user_licenses
        }
    )


@router.get("/achievements", response_class=HTMLResponse)
async def achievements_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Display achievements page - using REAL database data"""
    all_achievements_query = db.query(Achievement).filter(
        Achievement.is_active == True
    ).all()

    # Get user's unlocked achievements
    user_achievements = db.query(UserAchievement).filter(
        UserAchievement.user_id == user.id
    ).all()

    # Create a set of unlocked achievement IDs
    unlocked_ids = {ua.achievement_id for ua in user_achievements if ua.achievement_id}

    # Build achievements list with unlocked status
    all_achievements_list = []
    for ach in all_achievements_query:
        user_ach = next((ua for ua in user_achievements if ua.achievement_id == ach.id), None)
        all_achievements_list.append({
            'id': ach.id,
            'name': ach.name,
            'description': ach.description,
            'icon': ach.icon,
            'xp_reward': ach.xp_reward,
            'category': ach.category,
            'unlocked': ach.id in unlocked_ids,
            'earned_at': user_ach.earned_at if user_ach else None
        })

    # Get recent achievements (last 3)
    recent = [a for a in all_achievements_list if a['unlocked']]
    recent.sort(key=lambda x: x['earned_at'] or '', reverse=True)
    recent_achievements = recent[:3]

    # Calculate stats
    unlocked_count = len([a for a in all_achievements_list if a['unlocked']])
    total_achievements = len(all_achievements_list)
    total_xp = sum(a['xp_reward'] for a in all_achievements_list if a['unlocked'])
    completion_rate = int((unlocked_count / total_achievements * 100)) if total_achievements > 0 else 0

    return templates.TemplateResponse(
        "achievements.html",
        {
            "request": request,
            "user": user,
            "all_achievements": all_achievements_list,
            "recent_achievements": recent_achievements,
            "unlocked_count": unlocked_count,
            "total_achievements": total_achievements,
            "total_xp": total_xp,
            "completion_rate": completion_rate
        }
    )
