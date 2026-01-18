"""
Specialization-related routes (unlock, motivation, switch)
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from datetime import datetime, timezone, date

from ...database import get_db
from ...dependencies import get_current_user_web, get_current_user_optional, get_current_user
from ...models.user import User, UserRole
from ...models.license import UserLicense
from ...models.credit_transaction import CreditTransaction, TransactionType
from ...models.specialization import SpecializationType
from .helpers import update_specialization_xp, get_lfa_age_category

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.post("/specialization/unlock")
async def specialization_unlock(
    specialization: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unlock a specialization from Streamlit (costs 100 credits)
    Uses Bearer token authentication for Streamlit frontend

    BUSINESS LOGIC:
    - All specializations are VISIBLE to all users (for motivation/future planning)
    - Age requirement is ONLY enforced at UNLOCK time
    """
    if current_user.credit_balance < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient credits. You have {current_user.credit_balance} credits, but need 100."
        )

    # Map specialization enum
    spec_mapping = {
        "LFA_PLAYER": SpecializationType.LFA_FOOTBALL_PLAYER,
        "LFA_COACH": SpecializationType.LFA_COACH,
        "INTERNSHIP": SpecializationType.INTERNSHIP,
        "GANCUJU_PLAYER": SpecializationType.GANCUJU_PLAYER
    }

    spec_type = spec_mapping.get(specialization)
    if not spec_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specialization: {specialization}"
        )

    # ✅ AGE REQUIREMENT VALIDATION (Business requirement)
    # Check if user meets age requirement for this specialization
    if not validate_specialization_for_age(specialization, current_user.age):
        # Get age requirement text for error message
        age_requirements = {
            "INTERNSHIP": "18+",
            "LFA_COACH": "14+",
            "GANCUJU_PLAYER": "5+",
            "LFA_PLAYER": "5+"
        }
        required_age = age_requirements.get(specialization, "unknown")

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Age requirement not met. This specialization requires age {required_age}. Your current age: {current_user.age or 'not set'}."
        )

    # Deduct credits (only after all validations pass)
    current_user.credit_balance -= 100

    # Create user license
    new_license = UserLicense(
        user_id=current_user.id,
        specialization_type=spec_type.value,
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.utcnow(),
        payment_verified=True,
        payment_verified_at=datetime.utcnow(),
        onboarding_completed=False,
        is_active=True
    )
    db.add(new_license)
    db.flush()  # Get the ID

    # Create credit transaction
    credit_transaction = CreditTransaction(
        user_license_id=new_license.id,
        amount=-100,
        transaction_type=TransactionType.PURCHASE.value,
        description=f"Unlocked specialization: {spec_type.value}",
        balance_after=current_user.credit_balance,
        created_at=datetime.utcnow()
    )
    db.add(credit_transaction)

    # Update user specialization
    current_user.specialization = spec_type.value

    db.commit()

    return {
        "success": True,
        "message": "Specialization unlocked successfully",
        "new_balance": current_user.credit_balance,
        "license_id": new_license.id
    }


@router.get("/specialization/motivation", response_class=HTMLResponse)
async def student_motivation_questionnaire_page(
    request: Request,
    spec: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Student self-assessment motivation questionnaire (part of onboarding)"""
    try:
        spec_type = SpecializationType(spec)
    except ValueError:
        return RedirectResponse(url="/specialization/select", status_code=303)

    # Create display name
    spec_display_map = {
        SpecializationType.GANCUJU_PLAYER: "GānCuju Player",
        SpecializationType.LFA_FOOTBALL_PLAYER: "LFA Football Player",
        SpecializationType.LFA_COACH: "LFA Coach",
        SpecializationType.INTERNSHIP: "Internship"
    }
    specialization_display = spec_display_map.get(spec_type, spec_type.value.replace('_', ' '))

    print(f"📊 Student {user.email} accessing motivation questionnaire for {spec_type.value}")

    return templates.TemplateResponse(
        "student_motivation_questionnaire.html",
        {
            "request": request,
            "user": user,
            "specialization": spec_type.value,
            "specialization_display": specialization_display
        }
    )


@router.post("/specialization/motivation-submit")
async def student_motivation_questionnaire_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Process student's motivation self-assessment and complete onboarding"""
    try:
        # Parse form data
        form = await request.form()
        specialization = form.get("specialization")

        # Validate specialization
        try:
            spec_type = SpecializationType(specialization)
        except ValueError:
            return RedirectResponse(url="/specialization/select", status_code=303)

        # Get the 5 motivation scores
        goal_clarity = int(form.get("goal_clarity", 0))
        commitment_level = int(form.get("commitment_level", 0))
        engagement = int(form.get("engagement", 0))
        progress_mindset = int(form.get("progress_mindset", 0))
        initiative = int(form.get("initiative", 0))
        notes = form.get("notes", "").strip()

        # Validate scores (must be 1-5)
        scores = [goal_clarity, commitment_level, engagement, progress_mindset, initiative]
        if any(score < 1 or score > 5 for score in scores):
            return templates.TemplateResponse(
                "student_motivation_questionnaire.html",
                {
                    "request": request,
                    "user": user,
                    "specialization": spec_type.value,
                    "specialization_display": spec_type.value.replace('_', ' '),
                    "error": "All scores must be between 1 and 5"
                }
            )

        # Calculate average
        average_score = sum(scores) / len(scores)

        # Create motivation data object (student self-assessment)
        motivation_data = {
            "self_assessment": {
                "goal_clarity": goal_clarity,
                "commitment_level": commitment_level,
                "engagement": engagement,
                "progress_mindset": progress_mindset,
                "initiative": initiative,
                "average": round(average_score, 2),
                "notes": notes,
                "assessed_at": datetime.now(timezone.utc).isoformat(),
                "assessed_by": "student"
            }
        }

        # Find or create UserLicense for this specialization
        license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.specialization_type == spec_type.value
        ).first()

        if not license:
            # Should not happen if admin verified payment properly, but create if missing
            license = UserLicense(
                user_id=user.id,
                specialization_type=spec_type.value,
                current_level=1,
                max_achieved_level=1,
                started_at=datetime.now(timezone.utc)
            )
            db.add(license)

        # Update motivation scores
        license.motivation_scores = motivation_data
        license.average_motivation_score = average_score
        license.motivation_last_assessed_at = datetime.now(timezone.utc)
        license.motivation_assessed_by = user.id  # Student self-assessment

        # Mark onboarding as completed (BOTH user AND license)
        user.onboarding_completed = True  # User-level: "has completed at least ONE specialization onboarding"
        license.onboarding_completed = True  # License-level: "THIS specialization onboarding completed"
        license.onboarding_completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(user)
        db.refresh(license)

        print(f"✅ Student {user.email} completed motivation questionnaire for {spec_type.value} - Average: {average_score:.2f}")

        # Redirect to dashboard - onboarding complete!
        return RedirectResponse(url="/dashboard", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"❌ Error processing motivation questionnaire: {e}")
        print(traceback.format_exc())
        return templates.TemplateResponse(
            "student_motivation_questionnaire.html",
            {
                "request": request,
                "user": user,
                "specialization": specialization if 'specialization' in locals() else "",
                "specialization_display": "",
                "error": f"An error occurred: {str(e)}"
            }
        )


# ==================== LFA PLAYER ONBOARDING ====================

@router.get("/specialization/lfa-player/onboarding", response_class=HTMLResponse)
async def lfa_player_onboarding_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    LFA Player specialized onboarding questionnaire
    Multi-step: Position → Self-Assessment → Motivation
    """
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
    ).first()

    if not license:
        print(f"❌ User {user.email} tried to access LFA Player onboarding without license")
        return RedirectResponse(url="/dashboard", status_code=303)

    # If already completed onboarding, redirect to dashboard
    if license.onboarding_completed:
        print(f"ℹ️ User {user.email} already completed LFA Player onboarding")
        return RedirectResponse(url="/dashboard", status_code=303)

    print(f"⚽ User {user.email} starting LFA Player onboarding questionnaire")

    return templates.TemplateResponse(
        "lfa_player_onboarding.html",
        {
            "request": request,
            "user": user,
            "license": license
        }
    )


@router.get("/specialization/lfa-player/onboarding-cancel")
async def lfa_player_onboarding_cancel(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Cancel LFA Player onboarding and refund credits
    """
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.onboarding_completed == False  # Only incomplete onboarding
    ).first()

    if license:
        REFUND_AMOUNT = 100

        # Refund the credits
        user.credit_balance += REFUND_AMOUNT

        # Log the refund transaction
        refund_transaction = CreditTransaction(
            user_license_id=license.id,
            amount=REFUND_AMOUNT,
            transaction_type=TransactionType.REFUND.value,
            description=f"Refund for cancelled LFA Football Player onboarding",
            balance_after=user.credit_balance,
            created_at=datetime.now()
        )
        db.add(refund_transaction)

        # Delete the license
        db.delete(license)

        # Reset user's specialization
        user.specialization = None

        db.commit()

        print(f"💰 Refunded {REFUND_AMOUNT} credits to {user.email} (cancelled onboarding)")
        return RedirectResponse(url="/dashboard?success=Onboarding cancelled. 100 credits refunded.", status_code=303)
    else:
        return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/specialization/lfa-player/onboarding-submit")
async def lfa_player_onboarding_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Process LFA Player onboarding questionnaire
    Saves: position, self-assessment skills, motivation
    """
    try:
        form = await request.form()

        # Get form data
        position = form.get("position")
        motivation = form.get("motivation", "")
        goals = form.get("goals", "")

        # Self-assessment scores (0-10)
        skills = {
            "heading": int(form.get("skill_heading", 5)),
            "shooting": int(form.get("skill_shooting", 5)),
            "passing": int(form.get("skill_passing", 5)),
            "dribbling": int(form.get("skill_dribbling", 5)),
            "defending": int(form.get("skill_defending", 5)),
            "physical": int(form.get("skill_physical", 5))
        }

        # Validate position
        valid_positions = ["STRIKER", "MIDFIELDER", "DEFENDER", "GOALKEEPER"]
        if position not in valid_positions:
            raise ValueError(f"Invalid position: {position}")

        # Get user's LFA Player license
        license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
        ).first()

        if not license:
            raise ValueError("LFA Player license not found")

        # Calculate initial average skill level (convert to percentage)
        average_skill = sum(skills.values()) / len(skills) / 10 * 100  # Convert 0-10 to 0-100%

        # Store position, goals, and initial self-assessment in motivation_scores JSON field
        license.motivation_scores = {
            "position": position,
            "goals": goals,
            "motivation": motivation,
            "initial_self_assessment": skills,
            "average_skill_level": round(average_skill, 1),
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
        }
        license.average_motivation_score = average_skill
        license.motivation_last_assessed_at = datetime.now(timezone.utc)
        license.motivation_assessed_by = user.id

        # Mark onboarding as completed
        user.onboarding_completed = True
        license.onboarding_completed = True
        license.onboarding_completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(user)
        db.refresh(license)

        print(f"✅ LFA Player onboarding completed for {user.email}: Position={position}, Avg Skill={average_skill:.1f}%")

        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"❌ Error processing LFA Player onboarding: {e}")
        print(traceback.format_exc())
        return templates.TemplateResponse(
            "lfa_player_onboarding.html",
            {
                "request": request,
                "user": user,
                "error": f"An error occurred: {str(e)}"
            }
        )


@router.post("/specialization/switch")
async def specialization_switch(
    request: Request,
    specialization: str = Form(...),
    return_url: str = Form(None),  # 🔄 NEW: Optional return URL
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Switch student's active specialization (with onboarding check for new specs)"""
    redirect_url = return_url if return_url else "/dashboard"

    try:
        # Validate specialization type
        try:
            spec_type = SpecializationType(specialization)
        except ValueError:
            return RedirectResponse(url=redirect_url, status_code=303)

        # SECURITY: Check if user has a license for this specialization
        license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.specialization_type == spec_type.value
        ).first()

        if not license:
            print(f"❌ User {user.email} attempted to switch to UNAUTHORIZED specialization: {spec_type.value}")
            return RedirectResponse(url=redirect_url, status_code=303)

        print(f"🔄 User {user.email} switching to {spec_type.value}")

        # Update user's current specialization
        user.specialization = spec_type
        db.commit()
        db.refresh(user)

        # Redirect back to the page they came from (or dashboard)
        print(f"✅ Switched to {spec_type.value}, redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)

    except Exception as e:
        db.rollback()
        print(f"❌ Error during specialization switch: {e}")
        print(traceback.format_exc())
        return RedirectResponse(url=redirect_url, status_code=303)

