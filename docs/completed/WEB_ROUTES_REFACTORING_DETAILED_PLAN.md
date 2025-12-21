# web_routes.py Refactoring - Detailed Implementation Plan

**Dátum:** 2025-12-20
**Típus:** 📋 P0 REFACTORING PLAN
**Fájl:** `app/api/web_routes.py` (5381 sor)
**Cél:** Bontás 6-8 moduláris fájlra

---

## 🎯 JELENLEGI HELYZET

**Fájl:** `app/api/web_routes.py`
- **Sorok:** 5381
- **Funkciók:** 64 function/class
- **Probléma:** God File anti-pattern
- **Felelősségek:** Routing + Business Logic + Template Rendering + Auth

**Pozitívum:** ✅ Spec-specific route-ok már külön fájlokban vannak!
- `app/api/routes/lfa_player_routes.py` (315 sor)
- `app/api/routes/gancuju_routes.py` (232 sor)
- `app/api/routes/internship_routes.py` (230 sor)
- `app/api/routes/lfa_coach_routes.py` (288 sor)

---

## 📊 FÁJL SZERKEZET ELEMZÉS

### Jelenlegi Route-ok Kategóriái:

| Kategória | Sorok | Route-ok száma | Példa |
|-----------|-------|----------------|-------|
| **Helper Functions** | 100-150 | 2-3 | `_update_specialization_xp()`, `get_lfa_age_category()` |
| **Auth Routes** | 150-200 | 3 | `/login`, `/logout`, `/age-verification` |
| **Dashboard Routes** | 600-800 | 2 | `/dashboard`, `/dashboard/{spec_type}` |
| **Specialization Routes** | 800-1000 | 8 | `/specialization/select`, `/specialization/unlock`, etc. |
| **Profile Routes** | 300-400 | 3 | `/profile`, `/profile/edit` |
| **Enrollment Routes** | 200-300 | 1 | `/enrollment/request` |
| **Info Pages** | 150-200 | 2 | `/about-specializations`, `/credits` |
| **Spec Includes** | 100 | 4 | `router.include_router()` calls |
| **Deprecated** | 500+ | ? | Legacy code (line 4819+) |

---

## 🗂️ ÚJ STRUKTÚRA TERV

```
app/api/web_routes/
├── __init__.py                     # Main router registry (~100 sor)
├── auth.py                         # Auth routes (~200 sor)
├── dashboard.py                    # Dashboard routes (~800 sor)
├── specialization.py               # Specialization routes (~1000 sor)
├── profile.py                      # Profile routes (~400 sor)
├── enrollment.py                   # Enrollment routes (~300 sor)
├── info_pages.py                   # Info pages (~200 sor)
└── helpers/
    ├── __init__.py
    ├── xp_calculator.py            # XP calculation (~150 sor)
    ├── age_calculator.py           # Age/category logic (~100 sor)
    └── template_utils.py           # Template helpers (~100 sor)
```

**Eredmény:**
- 8 fájl (~200-1000 sor/fájl)
- Tiszta felelősség-megosztás
- Könnyű karbantarthatóság

---

## 📝 RÉSZLETES REFACTORING LÉPÉSEK

### Step 1: Create Directory Structure (5 perc)

```bash
cd app/api
mkdir -p web_routes/helpers
touch web_routes/__init__.py
touch web_routes/auth.py
touch web_routes/dashboard.py
touch web_routes/specialization.py
touch web_routes/profile.py
touch web_routes/enrollment.py
touch web_routes/info_pages.py
touch web_routes/helpers/__init__.py
touch web_routes/helpers/xp_calculator.py
touch web_routes/helpers/age_calculator.py
touch web_routes/helpers/template_utils.py
```

---

### Step 2: Extract Helper Functions (30 perc)

#### `web_routes/helpers/xp_calculator.py`

**Lines to extract:** 32-121 (`_update_specialization_xp()`)

```python
"""
XP Calculation Helpers
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from ...models.user_progress import SpecializationProgress


def update_specialization_xp(
    db: Session,
    student_id: int,
    specialization_id: str,
    xp_earned: int,
    session_id: int,
    is_update: bool = False
):
    """
    Update or create specialization_progress record with XP

    Args:
        db: Database session
        student_id: Student user ID
        specialization_id: Specialization type (e.g., 'INTERNSHIP')
        xp_earned: XP amount to award
        session_id: Session ID for tracking
        is_update: If True, recalculate XP (don't add); if False, add new XP
    """
    # [Copy lines 48-120 from web_routes.py]
    try:
        progress = db.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == student_id,
            SpecializationProgress.specialization_id == specialization_id
        ).first()

        if not progress:
            progress = SpecializationProgress(
                student_id=student_id,
                specialization_id=specialization_id,
                total_xp=xp_earned,
                completed_sessions=1,
                current_level=1,
                last_activity=datetime.now(timezone.utc)
            )
            db.add(progress)
            db.flush()
            print(f"✨ Created new SpecializationProgress for student {student_id}")
        else:
            if is_update:
                progress.total_xp = xp_earned
                print(f"🔄 Updated SpecializationProgress XP for student {student_id}")
            else:
                progress.total_xp = (progress.total_xp or 0) + xp_earned
                progress.completed_sessions = (progress.completed_sessions or 0) + 1
                print(f"➕ Added XP for student {student_id}")

            progress.last_activity = datetime.now(timezone.utc)

        progress.current_level = max(1, (progress.total_xp or 0) // 1000)
        db.flush()

    except IntegrityError as e:
        print(f"⚠️ IntegrityError caught - rolling back XP update only...")
        # Handle error...
```

#### `web_routes/helpers/age_calculator.py`

**Lines to extract:** 756-787 (`get_lfa_age_category()`)

```python
"""
Age and Category Calculation Helpers
"""
from datetime import date


def get_lfa_age_category(date_of_birth):
    """
    Determine LFA Player age category based on date of birth

    Returns:
        str: "PRE", "YOUTH", or "ADULT"
    """
    if not date_of_birth:
        return None

    today = date.today()
    age = today.year - date_of_birth.year

    # Adjust if birthday hasn't occurred this year
    if today < date(today.year, date_of_birth.month, date_of_birth.day):
        age -= 1

    # LFA Player age categories
    if 6 <= age <= 11:
        return "PRE"
    elif 12 <= age <= 18:
        return "YOUTH"
    elif age >= 14:  # Adults can start from 14
        return "ADULT"
    else:
        return None
```

---

### Step 3: Extract Auth Routes (45 perc)

#### `web_routes/auth.py`

**Lines to extract:** 134-324 (login, logout, age-verification routes)

```python
"""
Authentication and Session Management Routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone

from ...database import get_db
from ...dependencies import get_current_user_optional
from ...models.user import User
from ...core.auth import create_access_token
from ...core.security import verify_password
from ...config import settings
from ...main import templates

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_submit(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login form submission"""
    # [Copy lines 141-191 from web_routes.py]
    # Login logic...
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password"
            },
            status_code=400
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )

    # Check age verification
    if user.date_of_birth is None:
        return RedirectResponse(url="/age-verification", status_code=303)

    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
async def logout():
    """Logout and clear session"""
    # [Copy lines 193-200 from web_routes.py]
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


@router.get("/age-verification", response_class=HTMLResponse)
async def age_verification_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Display age verification page"""
    # [Copy lines 203-228 from web_routes.py]
    # Age verification logic...
    pass


@router.post("/age-verification")
async def age_verification_submit(
    request: Request,
    date_of_birth: str = Form(...),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Handle age verification submission"""
    # [Copy lines 230-323 from web_routes.py]
    # Age verification logic...
    pass
```

---

### Step 4: Extract Dashboard Routes (1 óra)

#### `web_routes/dashboard.py`

**Lines to extract:** 325-948 (dashboard routes)

```python
"""
Dashboard Routes - Main dashboard and spec-specific dashboards
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User
from ...main import templates
from .helpers.age_calculator import get_lfa_age_category

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard-fresh", response_class=HTMLResponse)  # CACHE BYPASS
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Main dashboard - shows user's active licenses and specializations

    Cache bypass route: /dashboard-fresh
    """
    # [Copy lines 327-755 from web_routes.py]
    # Dashboard logic...
    pass


@router.get("/dashboard/{spec_type}", response_class=HTMLResponse)
async def spec_dashboard(
    request: Request,
    spec_type: str,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Spec-specific dashboard (LFA_PLAYER, GANCUJU, INTERNSHIP, COACH)
    """
    # [Copy lines 789-948 from web_routes.py]
    # Spec dashboard logic...
    pass
```

---

### Step 5: Extract Specialization Routes (1.5 óra)

#### `web_routes/specialization.py`

**Lines to extract:** 949-1497 (specialization selection, unlock, motivation, onboarding)

```python
"""
Specialization Management Routes
- Specialization selection
- License unlocking
- Motivation questionnaire
- LFA Player onboarding
- Specialization switching
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User
from ...main import templates

router = APIRouter(tags=["specialization"])


@router.get("/specialization/select", response_class=HTMLResponse)
async def specialization_select_page(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """Display specialization selection page"""
    # [Copy lines 950-980 from web_routes.py]
    pass


@router.post("/specialization/select")
async def specialization_select_submit(
    request: Request,
    specialization: str = Form(...),
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """Handle specialization selection"""
    # [Copy lines 982-1083 from web_routes.py]
    pass


@router.get("/specialization/unlock", response_class=HTMLResponse)
async def specialization_unlock_get(...):
    """Display unlock page"""
    # [Copy lines 1085-1097]
    pass


@router.post("/specialization/unlock")
async def specialization_unlock(...):
    """Handle unlock request"""
    # [Copy lines 1099-1113]
    pass


@router.get("/specialization/motivation", response_class=HTMLResponse)
async def student_motivation_questionnaire_page(...):
    """Display motivation questionnaire"""
    # [Copy lines 1115-1151]
    pass


@router.post("/specialization/motivation-submit")
async def student_motivation_questionnaire_submit(...):
    """Handle motivation questionnaire submission"""
    # [Copy lines 1153-1268]
    pass


@router.get("/specialization/lfa-player/onboarding", response_class=HTMLResponse)
async def lfa_player_onboarding_page(...):
    """LFA Player specific onboarding"""
    # [Copy lines 1270-1307]
    pass


@router.get("/specialization/lfa-player/onboarding-cancel")
async def lfa_player_onboarding_cancel(...):
    """Cancel LFA Player onboarding"""
    # [Copy lines 1309-1357]
    pass


@router.post("/specialization/lfa-player/onboarding-submit")
async def lfa_player_onboarding_submit(...):
    """Handle LFA Player onboarding submission"""
    # [Copy lines 1359-1446]
    pass


@router.post("/specialization/switch")
async def specialization_switch(...):
    """Switch between specializations"""
    # [Copy lines 1448-1497]
    pass
```

---

### Step 6: Extract Profile Routes (30 perc)

#### `web_routes/profile.py`

**Lines to extract:** 1639-1909 (profile view, profile edit)

```python
"""
User Profile Routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User
from ...main import templates

router = APIRouter(tags=["profile"])


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """Display user profile"""
    # [Copy lines 1640-1750 from web_routes.py]
    pass


@router.get("/profile/edit", response_class=HTMLResponse)
async def profile_edit_page(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """Display profile edit form"""
    # [Copy lines 1752-1775 from web_routes.py]
    pass


@router.post("/profile/edit")
async def profile_edit_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """Handle profile edit submission"""
    # [Copy lines 1777-1909 from web_routes.py]
    pass
```

---

### Step 7: Extract Other Routes (30 perc)

#### `web_routes/enrollment.py`

**Lines to extract:** 1498-1638

```python
"""
Enrollment Request Routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User

router = APIRouter(tags=["enrollment"])


@router.post("/enrollment/request")
async def enrollment_request(
    request: Request,
    semester_id: int = Form(...),
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """Handle semester enrollment request"""
    # [Copy lines 1499-1638 from web_routes.py]
    pass
```

#### `web_routes/info_pages.py`

**Lines to extract:** 1910-2000+

```python
"""
Informational Pages
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_optional
from ...models.user import User
from ...main import templates

router = APIRouter(tags=["info"])


@router.get("/about-specializations", response_class=HTMLResponse)
async def about_specializations_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Display specializations information page"""
    # [Copy lines 1911-1934 from web_routes.py]
    pass


@router.get("/credits", response_class=HTMLResponse)
async def credits_page(request: Request):
    """Display credits/about page"""
    # [Copy lines 1935-? from web_routes.py]
    pass
```

---

### Step 8: Update Main Router (30 perc)

#### `web_routes/__init__.py`

```python
"""
Web Routes Main Router

Modular web routes for HTML template rendering.
Previously monolithic file (5381 lines) now split into:
- auth.py: Authentication routes
- dashboard.py: Dashboard routes
- specialization.py: Specialization management
- profile.py: User profile
- enrollment.py: Enrollment requests
- info_pages.py: Informational pages
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...main import templates

# Import modular routers
from . import auth, dashboard, specialization, profile, enrollment, info_pages

# Import spec-specific routers (already modular)
from ..routes import lfa_player_routes, gancuju_routes, internship_routes, lfa_coach_routes

# Main router
router = APIRouter(tags=["web"])


# Home route (keep simple routes in main file)
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page"""
    return templates.TemplateResponse("home.html", {"request": request})


# Include all modular routers
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(specialization.router)
router.include_router(profile.router)
router.include_router(enrollment.router)
router.include_router(info_pages.router)

# Include spec-specific routers
router.include_router(
    lfa_player_routes.router,
    tags=["lfa_player", "skills"]
)

router.include_router(
    gancuju_routes.router,
    tags=["gancuju", "belts"]
)

router.include_router(
    internship_routes.router,
    tags=["internship", "xp", "levels"]
)

router.include_router(
    lfa_coach_routes.router,
    tags=["lfa_coach", "certifications"]
)
```

---

### Step 9: Update Main App Import (5 perc)

#### `app/main.py`

**Change:**
```python
# OLD:
from .api.web_routes import router as web_router

# NEW:
from .api.web_routes import router as web_router  # Now points to __init__.py in web_routes/
```

**No change needed if using package import!** ✅

---

### Step 10: Testing Checklist (1-2 óra)

#### Test Plan:

```bash
# 1. Syntax check
python3 -m py_compile app/api/web_routes/*.py
python3 -m py_compile app/api/web_routes/helpers/*.py

# 2. Import test
python3 -c "from app.api.web_routes import router; print('✅ Router import OK')"

# 3. Start server
./start_backend.sh

# 4. Test routes manually:
curl http://localhost:8000/
curl http://localhost:8000/login
curl http://localhost:8000/about-specializations

# 5. Browser testing:
# - Login flow
# - Dashboard access
# - Specialization selection
# - Profile edit
# - Each route from old file
```

#### Critical Routes to Test:

- [ ] `/` (home)
- [ ] `/login` GET & POST
- [ ] `/logout`
- [ ] `/age-verification` GET & POST
- [ ] `/dashboard`
- [ ] `/dashboard/{spec_type}`
- [ ] `/specialization/select` GET & POST
- [ ] `/specialization/unlock` GET & POST
- [ ] `/specialization/motivation` GET & POST
- [ ] `/specialization/lfa-player/onboarding` GET & POST
- [ ] `/profile` GET
- [ ] `/profile/edit` GET & POST
- [ ] `/enrollment/request` POST
- [ ] `/about-specializations`
- [ ] `/credits`

---

## ⏱️ IDŐBECSLÉS RÉSZLETEZVE

| Step | Leírás | Időigény |
|------|--------|----------|
| Step 1 | Directory structure | 5 perc |
| Step 2 | Extract helpers | 30 perc |
| Step 3 | Extract auth routes | 45 perc |
| Step 4 | Extract dashboard routes | 1 óra |
| Step 5 | Extract specialization routes | 1.5 óra |
| Step 6 | Extract profile routes | 30 perc |
| Step 7 | Extract other routes | 30 perc |
| Step 8 | Update main router | 30 perc |
| Step 9 | Update imports | 5 perc |
| Step 10 | Testing | 1-2 óra |
| **ÖSSZESEN** | | **5-6 óra** |

---

## 🎯 EREDMÉNY UTÁN

### Előtte:
```
app/api/
└── web_routes.py                   # 5381 sor ❌
```

### Utána:
```
app/api/
└── web_routes/
    ├── __init__.py                 # 100 sor ✅
    ├── auth.py                     # 200 sor ✅
    ├── dashboard.py                # 800 sor ✅
    ├── specialization.py           # 1000 sor ✅
    ├── profile.py                  # 400 sor ✅
    ├── enrollment.py               # 300 sor ✅
    ├── info_pages.py               # 200 sor ✅
    └── helpers/
        ├── __init__.py             # 10 sor ✅
        ├── xp_calculator.py        # 150 sor ✅
        ├── age_calculator.py       # 100 sor ✅
        └── template_utils.py       # 100 sor ✅
```

**Összesen:** 11 fájl, átlag ~350 sor/fájl ✅

---

## 📝 NOTES & TIPS

### Common Pitfalls:

1. **Import path changes:** Update all `from ..` to correct levels
2. **Circular imports:** Helpers should NOT import from routes
3. **Template paths:** Ensure templates are found from new locations
4. **Dependency injection:** Keep `Depends(get_db)` in route signatures

### Best Practices:

1. **Test after each step:** Don't wait until end
2. **Git commits:** Commit after each successful step
3. **Keep deprecated code:** Don't delete old file until 100% working
4. **Documentation:** Update API docs if needed

### Rollback Plan:

```bash
# If something breaks:
git stash  # Stash new changes
git checkout app/api/web_routes.py  # Restore old file
./start_backend.sh  # Verify old version works
# Debug issue, then retry
```

---

## ✅ COMPLETION CHECKLIST

- [ ] Step 1: Directory structure created
- [ ] Step 2: Helper functions extracted and tested
- [ ] Step 3: Auth routes extracted and tested
- [ ] Step 4: Dashboard routes extracted and tested
- [ ] Step 5: Specialization routes extracted and tested
- [ ] Step 6: Profile routes extracted and tested
- [ ] Step 7: Other routes extracted and tested
- [ ] Step 8: Main router updated
- [ ] Step 9: Imports updated
- [ ] Step 10: All routes tested manually
- [ ] Step 10: Automated tests pass
- [ ] Old `web_routes.py` backed up
- [ ] Old `web_routes.py` deleted
- [ ] Documentation updated
- [ ] Git commit created

---

**状态:** READY TO EXECUTE 🚀

**Következő lépés:** Execute Step 1 (Directory structure)
