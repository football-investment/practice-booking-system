"""
Onboarding routes for student specialization selection and questionnaires
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone

from ...database import get_db
from ...dependencies import get_current_user_web, get_current_user
from ...models.user import User

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/specialization/select", response_class=HTMLResponse)
async def specialization_select_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Display specialization selection page - only show active specializations"""
    active_specializations = {
        "INTERNSHIP": {"has_instructor": True, "max_students": 30},
        "LFA_FOOTBALL_PLAYER": {"has_instructor": True, "max_students": 25},
        "LFA_COACH": {"has_instructor": True, "max_students": 20},
        "GANCUJU_PLAYER": {"has_instructor": True, "max_students": 25}
    }

    # Get user's existing licenses
    user_licenses = db.query(UserLicense).filter(UserLicense.user_id == user.id).all()
    user_specialization_types = [license.specialization_type for license in user_licenses]

    return templates.TemplateResponse(
        "specialization_select.html",
        {
            "request": request,
            "user": user,
            "active_specializations": active_specializations,
            "user_specialization_types": user_specialization_types
        }
    )


@router.post("/specialization/select")
async def specialization_select_submit(
    request: Request,
    specialization: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Process specialization selection and complete onboarding"""
    try:
        # Validate specialization type
        try:
            spec_type = SpecializationType[specialization]
        except KeyError:
            print(f"Invalid specialization value: {specialization}")
            return templates.TemplateResponse(
                "specialization_select.html",
                {"request": request, "user": user, "error": f"Invalid specialization: {specialization}"}
            )

        # NEW LOGIC: Check if user already has a license (already unlocked)
        user_license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.specialization_type == spec_type.value
        ).first()

        # If NO license exists, this is a NEW unlock -> costs 100 credits
        if not user_license:
            SPEC_UNLOCK_COST = 100  # Cost to unlock a new specialization

            # Check if user has enough credits
            if user.credit_balance < SPEC_UNLOCK_COST:
                print(f"User {user.email} has insufficient credits ({user.credit_balance}) to unlock {spec_type.value} (needs {SPEC_UNLOCK_COST})")
                # Redirect back to dashboard with error message
                error_msg = f"Insufficient credits! Unlocking {spec_type.value.replace('_', ' ')} requires {SPEC_UNLOCK_COST} credits. You have {user.credit_balance} credits."
                return RedirectResponse(url=f"/dashboard?error={error_msg}", status_code=303)

            # DEDUCT credits and create the license
            print(f"Deducting {SPEC_UNLOCK_COST} credits from user {user.email} (balance: {user.credit_balance} → {user.credit_balance - SPEC_UNLOCK_COST})")
            user.credit_balance -= SPEC_UNLOCK_COST

            # Create the UserLicense (unlock specialization)
            user_license = UserLicense(
                user_id=user.id,
                specialization_type=spec_type.value,
                current_level=1,
                started_at=datetime.now(),  # Required field!
                payment_verified=True,  # Paid via credits
                payment_verified_at=datetime.now(),
                created_at=datetime.now()
            )
            db.add(user_license)
            db.flush()  # Flush to get the user_license.id

            # Log credit transaction
            credit_transaction = CreditTransaction(
                user_license_id=user_license.id,  # Fixed: use user_license_id, not user_id
                amount=-SPEC_UNLOCK_COST,
                transaction_type=TransactionType.PURCHASE.value,  # Fixed: use .value for enum
                description=f"Unlocked specialization: {spec_type.value.replace('_', ' ')}",
                balance_after=user.credit_balance,
                created_at=datetime.now()
            )
            db.add(credit_transaction)

            print(f"User {user.email} unlocked {spec_type.value} for {SPEC_UNLOCK_COST} credits")

        print(f"Setting specialization {spec_type} for user {user.email}")

        # Update user's specialization BUT DO NOT mark onboarding as completed yet
        # Student needs to fill out motivation questionnaire first
        user.specialization = spec_type
        # onboarding_completed will be set to True AFTER motivation questionnaire

        db.flush()  # Flush to catch any DB errors before commit
        db.commit()
        db.refresh(user)  # Refresh to get updated values

        print(f"User {user.email} selected specialization: {spec_type.value}, redirecting to onboarding")

        # Redirect based on specialization type
        if spec_type == SpecializationType.LFA_FOOTBALL_PLAYER:
            # LFA Player gets specialized onboarding questionnaire
            return RedirectResponse(url=f"/specialization/lfa-player/onboarding", status_code=303)
        else:
            # Other specializations get standard motivation questionnaire
            return RedirectResponse(url=f"/specialization/motivation?spec={spec_type.value}", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"Error during specialization selection: {e}")
        print(traceback.format_exc())
        # Redirect back to dashboard with error message (instead of showing old 4-card page)
        return RedirectResponse(url=f"/dashboard?error={str(e)}", status_code=303)


@router.get("/specialization/lfa-player/onboarding", response_class=HTMLResponse)
async def lfa_player_onboarding_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    LFA Player specialized onboarding questionnaire
    Multi-step: Position -> Self-Assessment -> Motivation
    """
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
    ).first()

    if not license:
        print(f"User {user.email} tried to access LFA Player onboarding without license")
        return RedirectResponse(url="/dashboard", status_code=303)

    # If already completed onboarding, redirect to dashboard
    if license.onboarding_completed:
        print(f"User {user.email} already completed LFA Player onboarding")
        return RedirectResponse(url="/dashboard", status_code=303)

    print(f"User {user.email} starting LFA Player onboarding questionnaire")

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

        print(f"Refunded {REFUND_AMOUNT} credits to {user.email} (cancelled onboarding)")
        return RedirectResponse(url="/dashboard?success=Onboarding cancelled. 100 credits refunded.", status_code=303)
    else:
        return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/specialization/lfa-player/onboarding-submit")
async def lfa_player_onboarding_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Process LFA Player onboarding questionnaire
    Saves: date_of_birth, position, self-assessment skills, motivation
    """
    try:
        form = await request.form()

        # Get form data
        position = form.get("position")
        motivation = form.get("motivation", "")
        goals = form.get("goals", "")
        date_of_birth_str = form.get("date_of_birth")  # ✅ NEW: Get birth date

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

        # ❌ REMOVED: date_of_birth is NO LONGER updated here!
        # It should already exist in user profile from /auth/register-with-invitation
        # If it doesn't exist, the frontend will show an error and redirect to My Profile

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
        print(f"Error processing LFA Player onboarding: {e}")
        print(traceback.format_exc())
        return templates.TemplateResponse(
            "lfa_player_onboarding.html",
            {
                "request": request,
                "user": user,
                "error": f"An error occurred: {str(e)}"
            }
        )


@router.get("/onboarding/start", response_class=HTMLResponse)
async def onboarding_start(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    New onboarding flow:
    1. Collect date of birth (if not set)
    2. Show age-filtered specializations
    3. Student selects spec(s)
    4. Auto-create UserLicense(s)
    5. Show payment info
    """
    today = date.today().isoformat()

    # Get available specializations based on age
    available_specs = []
    if user.age is not None:
        available_specs = get_available_specializations(user.age)

    return templates.TemplateResponse(
        "student/onboarding_new.html",
        {
            "request": request,
            "user": user,
            "today": today,
            "available_specs": available_specs
        }
    )


@router.post("/onboarding/set-birthdate")
async def onboarding_set_birthdate(
    request: Request,
    date_of_birth: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Set user's date of birth and continue onboarding"""
    try:
        # Parse date
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()

        # Validate age (must be at least 5 years old)
        today = datetime.now().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if age < 5:
            raise HTTPException(status_code=400, detail="You must be at least 5 years old to register")

        # Update user
        user.date_of_birth = dob
        db.commit()

        print(f"Set date of birth for {user.email}: {dob} (age: {age})")

        # Redirect back to onboarding to show spec selection
        return RedirectResponse(url="/onboarding/start", status_code=303)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
