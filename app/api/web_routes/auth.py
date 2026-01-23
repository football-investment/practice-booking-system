"""
Authentication routes for web interface
Handles login, logout, and age verification
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import timedelta, datetime

from ...database import get_db
from ...dependencies import get_current_user_web, get_current_user_optional
from ...models.user import User
from ...core.auth import create_access_token
from ...core.security import verify_password
from ...config import settings

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page - redirects to login or dashboard"""
    try:
        user = await get_current_user_optional(request, db)
        if user:
            return RedirectResponse(url="/dashboard", status_code=303)
    except:
        pass
    return RedirectResponse(url="/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login form"""
    # Find user
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"}
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Account is inactive"}
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Check if student needs age verification (first time login)
    redirect_url = "/dashboard"

    if user.role == UserRole.STUDENT and user.date_of_birth is None:
        # First time login - redirect to age verification
        redirect_url = "/age-verification"
        print(f"First-time student login: {user.email} -> redirecting to age verification")

    # Redirect with token in cookie (SECURITY: SameSite + Secure flags)
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=settings.COOKIE_HTTPONLY,  # ✅ SECURITY: Prevents XSS cookie theft
        max_age=settings.COOKIE_MAX_AGE,  # ✅ SECURITY: Explicit expiry (1 hour)
        secure=settings.COOKIE_SECURE,  # ✅ SECURITY: HTTPS only in production
        samesite=settings.COOKIE_SAMESITE,  # ✅ SECURITY FIX: "strict" prevents CSRF
        path="/"  # Make cookie available across all paths
    )
    return response


@router.get("/logout")
async def logout():
    """Logout user"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# Age Verification Routes

@router.get("/age-verification", response_class=HTMLResponse)
async def age_verification_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Age verification page for first-time students"""
    if user.role != UserRole.STUDENT:
        return RedirectResponse(url="/dashboard", status_code=303)

    # If already verified, redirect to dashboard
    if user.date_of_birth is not None:
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        "age_verification.html",
        {
            "request": request,
            "user": user,
            "today": datetime.now().date().isoformat()
        }
    )


@router.post("/age-verification")
async def age_verification_submit(
    request: Request,
    date_of_birth: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Process age verification form"""
    if user.role != UserRole.STUDENT:
        return RedirectResponse(url="/dashboard", status_code=303)

    try:
        # Parse date
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()

        # Validate date (not in future, reasonable age)
        today = date.today()
        if dob > today:
            return templates.TemplateResponse(
                "age_verification.html",
                {
                    "request": request,
                    "user": user,
                    "today": today.isoformat(),
                    "error": "Date of birth cannot be in the future",
                    "date_of_birth": date_of_birth
                }
            )

        # Calculate age
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if age < 5:
            return templates.TemplateResponse(
                "age_verification.html",
                {
                    "request": request,
                    "user": user,
                    "today": today.isoformat(),
                    "error": "You must be at least 5 years old to use this platform",
                    "date_of_birth": date_of_birth
                }
            )

        if age > 120:
            return templates.TemplateResponse(
                "age_verification.html",
                {
                    "request": request,
                    "user": user,
                    "today": today.isoformat(),
                    "error": "Please enter a valid date of birth",
                    "date_of_birth": date_of_birth
                }
            )

        # Save date of birth
        user.date_of_birth = dob
        db.commit()
        db.refresh(user)

        print(f"Age verified for {user.email}: {age} years old (born {dob})")

        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=303)

    except ValueError as e:
        return templates.TemplateResponse(
            "age_verification.html",
            {
                "request": request,
                "user": user,
                "today": date.today().isoformat(),
                "error": "Invalid date format. Please use the date picker.",
                "date_of_birth": date_of_birth
            }
        )
    except Exception as e:
        print(f"Error during age verification: {e}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "age_verification.html",
            {
                "request": request,
                "user": user,
                "today": date.today().isoformat(),
                "error": f"An error occurred: {str(e)}"
            }
        )
